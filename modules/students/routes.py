from flask import render_template, request, flash, redirect, url_for, session, request
from utils.nav import navlink
from models import Student, StudentSubjectEnrollment, Instrument, Subject, Player, EnsemblePlayer, Ensemble, \
    EnsembleSemester, db, Semester
from modules.students import students_bp
from sqlalchemy import and_, func
from .forms import EnrollmentForm

from sqlalchemy import or_


@students_bp.route("/", methods=["GET"])
@navlink("Studenti", group="Lidé", weight=100)
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
        selected_semester_ids=semester_ids,
        selected_instrument_ids=instrument_ids,
        selected_subject_ids=subject_ids,
        selected_has_ensemble=has_ensemble,
        search_query=search_query,
    )


@students_bp.route("/detail/<int:student_id>", methods=["GET"])
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)
    form = EnrollmentForm()  # basic form object
    return render_template("student_detail.html", student=student, form=form)


@students_bp.route("/edit-enrollment/<int:enrollment_id>", methods=["POST"])
def edit_enrollment(enrollment_id):
    enrollment = StudentSubjectEnrollment.query.get_or_404(enrollment_id)
    form = EnrollmentForm(obj=enrollment)

    if form.validate_on_submit():
        enrollment.erasmus = form.erasmus.data
        db.session.commit()
        flash("Zápis předmětu byl aktualizován.", "success")
        return redirect(url_for("students.student_detail", student_id=enrollment.student_id))
