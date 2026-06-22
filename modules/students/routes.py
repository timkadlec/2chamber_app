from flask import render_template, flash, redirect, url_for, session, request
from utils.nav import navlink
from models import Student, StudentSubjectEnrollment, Instrument, Subject, Player, EnsemblePlayer, Ensemble, \
    EnsembleSemester, db, Semester, Department, StudentChamberApplication, StudentChamberApplicationStatus
from modules.students import students_bp
from sqlalchemy import and_, func, exists
from .forms import EnrollmentForm
from utils.decorators import role_required, permission_required
from utils.session_helpers import get_or_set_current_semester
from sqlalchemy import or_
from datetime import date


@students_bp.route("/", methods=["GET"])
@navlink("Studenti", group="Lidé", weight=100)
@permission_required("st_can_view")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # --- Semester handling ---
    semester_ids = request.args.getlist("semester_id", type=int)
    semester_all = request.args.get("semester_all") == "1"

    if not semester_all and not semester_ids and session.get("semester_id"):
        semester_ids = [session["semester_id"]]

    query = Student.query

    # --- Instrument filter ---
    instrument_ids = request.args.getlist("instrument_id", type=int)
    if instrument_ids:
        query = query.filter(Student.instrument_id.in_(instrument_ids))

    # --- Subject / semester filters ---
    subject_ids = request.args.getlist("subject_id", type=int)

    if semester_ids or subject_ids:
        query = query.join(StudentSubjectEnrollment)

        if semester_ids:
            query = query.filter(StudentSubjectEnrollment.semester_id.in_(semester_ids))

        if subject_ids:
            query = query.filter(StudentSubjectEnrollment.subject_id.in_(subject_ids))

    # --- Search filter (by first_name OR last_name) ---
    search_query = request.args.get("q", "").strip()
    if search_query:
        search = search_query.lower()
        query = query.filter(
            or_(
                func.unaccent(func.lower(Student.first_name)).like(f"%{search}%"),
                func.unaccent(func.lower(Student.last_name)).like(f"%{search}%"),
            )
        )

    # --- Department filter ---
    department_ids = request.args.getlist("department_id", type=int)
    if department_ids:
        query = query.filter(Student.department_id.in_(department_ids))

    # --- Classification filters ---
    has_classification = request.args.get("has_classification")

    if has_classification in ("0", "1") and semester_ids:
        classification_exists = (
            db.session.query(StudentSubjectEnrollment.id)
            .filter(StudentSubjectEnrollment.student_id == Student.id)
            .filter(StudentSubjectEnrollment.semester_id.in_(semester_ids))
            .filter(StudentSubjectEnrollment.classification.isnot(None))
            .correlate(Student)
            .exists()
        )

        if has_classification == "1":
            query = query.filter(classification_exists)
        else:
            query = query.filter(~classification_exists)

    # --- Ensemble filter ---
    has_ensemble = request.args.get("has_ensemble")
    if has_ensemble in ("0", "1"):
        query = query.outerjoin(Player, Student.player).outerjoin(
            EnsemblePlayer, Player.id == EnsemblePlayer.player_id
        ).outerjoin(
            Ensemble, Ensemble.id == EnsemblePlayer.ensemble_id
        ).outerjoin(
            EnsembleSemester, Ensemble.id == EnsembleSemester.ensemble_id
        )

        if has_ensemble == "1":
            query = query.filter(EnsembleSemester.semester_id.in_(semester_ids))
        else:  # has_ensemble == "0"
            # students with no ensembles in the selected semester(s)
            query = query.filter(
                ~Student.id.in_(
                    db.session.query(Student.id)
                    .join(Player)
                    .join(EnsemblePlayer)
                    .join(Ensemble)
                    .join(EnsembleSemester)
                    .filter(EnsembleSemester.semester_id.in_(semester_ids))
                )
            )

    # --- Chamber application filter ---
    has_pending_application = request.args.get("has_pending_application")
    if has_pending_application in ("0", "1"):
        current_semester = get_or_set_current_semester()
        subq = (
            db.session.query(StudentChamberApplication.id)
            .filter(StudentChamberApplication.student_id == Student.id)
            .filter(StudentChamberApplication.semester_id == current_semester.id)
            .correlate(Student)
        )
        app_exists = subq.exists()
        if has_pending_application == "1":
            query = query.filter(app_exists)
        else:
            query = query.filter(~app_exists)

    # --- Sort by name ---
    query = query.order_by(Student.last_name, Student.first_name)

    # --- Pagination ---
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # --- Render ---
    return render_template(
        "all_students.html",
        students=pagination.items,
        pagination=pagination,
        subjects=Subject.query.order_by(Subject.weight).all(),
        instruments=Instrument.query.filter_by(is_primary=True).order_by(Instrument.weight).all(),
        semesters=Semester.query.order_by(Semester.start_date.desc()).all(),
        departments=Department.query.order_by(Department.name).all(),
        selected_semester_ids=semester_ids,
        selected_instrument_ids=instrument_ids,
        selected_subject_ids=subject_ids,
        selected_has_ensemble=has_ensemble,
        selected_department_ids=department_ids,
        search_query=search_query,
        selected_has_classification=has_classification,
        selected_has_pending_application=has_pending_application,
    )


@students_bp.route("/detail/<int:student_id>", methods=["GET"])
@permission_required("st_can_view")
def student_detail(student_id):
    current_semester = get_or_set_current_semester()
    student = Student.query.get_or_404(student_id)
    form = EnrollmentForm()
    chamber_applications = (
        StudentChamberApplication.query
        .filter_by(student_id=student_id)
        .order_by(StudentChamberApplication.semester_id.desc(), StudentChamberApplication.submission_date.desc())
        .all()
    )
    return render_template(
        "student_detail.html",
        student=student,
        form=form,
        current_semester=current_semester,
        chamber_applications=chamber_applications,
    )


@students_bp.route("/edit-enrollment/<int:enrollment_id>", methods=["POST"])
@permission_required("st_can_edit")
def edit_enrollment(enrollment_id):
    enrollment = StudentSubjectEnrollment.query.get_or_404(enrollment_id)
    form = EnrollmentForm(obj=enrollment)

    if form.validate_on_submit():
        enrollment.erasmus = form.erasmus.data
        db.session.commit()
        flash("Zápis předmětu byl aktualizován.", "success")
        return redirect(url_for("students.student_detail", student_id=enrollment.student_id))


@students_bp.route("/detail/<int:student_id>/requests/ensemble-selection", methods=["GET"])
@permission_required("st_requests")
def request_ensemble_selection(student_id):
    student = Student.query.filter_by(id=student_id).first()
    ensembles = student.ensembles_in_semester
    return render_template("request_ensemble_selection.html", student=student, ensembles=ensembles)


@students_bp.route("/<int:student_id>/classify", methods=["POST"])
@permission_required("st_can_classify")
def classify_student(student_id):
    enrollment_id = request.form.get("enrollment_id", type=int)
    classification = request.form.get("classification")
    classification_basis = request.form.get("classification_basis")

    enrollment = StudentSubjectEnrollment.query.get_or_404(enrollment_id)

    if enrollment.student_id != student_id:
        flash("Neplatný zápis předmětu pro tohoto studenta.", "danger")
        return redirect(request.referrer or url_for("students.index"))

    enrollment.classification = classification
    enrollment.classification_basis = classification_basis
    enrollment.classification_date = date.today()

    db.session.commit()

    flash("Klasifikace byla uložena.", "success")
    return redirect(request.referrer or url_for("students.index"))


@students_bp.route("/<int:student_id>/clear-classification", methods=["POST"])
@permission_required("st_can_classify")
def clear_classification(student_id):
    enrollment_id = request.form.get("enrollment_id", type=int)

    enrollment = StudentSubjectEnrollment.query.get_or_404(enrollment_id)

    if enrollment.student_id != student_id:
        flash("Neplatný zápis předmětu pro tohoto studenta.", "danger")
        return redirect(request.referrer or url_for("students.index"))

    enrollment.classification = None
    enrollment.classification_basis = None
    enrollment.classification_date = None

    db.session.commit()

    flash("Klasifikace byla odstraněna.", "success")
    return redirect(request.referrer or url_for("students.index"))
