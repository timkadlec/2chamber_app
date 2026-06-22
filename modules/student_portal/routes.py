from flask import render_template, redirect, url_for, abort, request, flash, session
from flask_login import current_user
from modules.student_portal import student_portal_bp
from modules.student_portal.forms import ChamberEnrollmentRequestForm
from models import (
    Semester, StudentSemesterEnrollment,
    EnsemblePlayer, EnsembleTeacher, Player,
    ChamberEnrollmentRequest, ChamberEnrollmentRequestPlayer, db,
)
from utils.session_helpers import get_or_set_current_semester
from datetime import date


@student_portal_bp.before_request
def require_student():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.portal_type != "student":
        abort(403)


@student_portal_bp.route("/")
def dashboard():
    student = current_user.student

    # All semesters this student has been enrolled in, newest first
    student_semesters = (
        Semester.query
        .join(StudentSemesterEnrollment, StudentSemesterEnrollment.semester_id == Semester.id)
        .filter(StudentSemesterEnrollment.student_id == student.id)
        .order_by(Semester.start_date.desc())
        .all()
    )

    # Resolve which semester to display
    semester_id = request.args.get("semester_id", type=int)
    if semester_id:
        semester = Semester.query.get_or_404(semester_id)
    elif student_semesters:
        semester = student_semesters[0]
    else:
        semester = get_or_set_current_semester()

    ensembles = student.ensembles_for_semester(semester.id) if semester else []

    enrollments = [
        e for e in student.subject_enrollments
        if semester and e.semester_id == semester.id
    ]

    # Players and teachers per ensemble for this semester
    ensemble_details = {}
    for ensemble in ensembles:
        ensemble_details[ensemble.id] = {
            "players": (
                EnsemblePlayer.query
                .filter_by(ensemble_id=ensemble.id, semester_id=semester.id)
                .all()
            ),
            "teachers": (
                EnsembleTeacher.query
                .filter_by(ensemble_id=ensemble.id, semester_id=semester.id)
                .all()
            ),
        }

    enrollment_request = ChamberEnrollmentRequest.query.filter_by(
        student_id=student.id,
        semester_id=semester.id if semester else None,
    ).order_by(ChamberEnrollmentRequest.created_at.desc()).first()

    return render_template(
        "student_dashboard.html",
        student=student,
        semester=semester,
        student_semesters=student_semesters,
        ensembles=ensembles,
        enrollments=enrollments,
        ensemble_details=ensemble_details,
        enrollment_request=enrollment_request,
    )


@student_portal_bp.route("/prihlaska-komorni-hry/<int:request_id>")
def chamber_enrollment_detail(request_id):
    student = current_user.student
    enrollment_request = ChamberEnrollmentRequest.query.get_or_404(request_id)
    if enrollment_request.student_id != student.id:
        abort(403)
    return render_template(
        "chamber_enrollment_detail.html",
        student=student,
        enrollment_request=enrollment_request,
    )


@student_portal_bp.route("/prihlaska-komorni-hry", methods=["GET", "POST"])
def chamber_enrollment():
    student = current_user.student

    # 1. Get the CURRENT semester for the "stay in ensemble" dropdown
    current_semester = get_or_set_current_semester()
    print(current_semester)
    current_ensembles = student.ensembles_for_semester(current_semester.id) if current_semester else []

    # 2. Query the UPCOMING semester globally to safely cross academic year boundaries
    upcoming_semester = Semester.query.filter(
        Semester.start_date > date.today()
    ).order_by(Semester.start_date.asc()).first()

    form = ChamberEnrollmentRequestForm()
    form.stay_ensemble.query_factory = lambda: current_ensembles

    if form.validate_on_submit():
        enrollment_request = ChamberEnrollmentRequest(
            student_id=student.id,
            semester_id=current_semester.id if current_semester else None,
            future_year=form.future_year.data,
            teacher=form.teacher.data,
            wants_to_stay=form.wants_to_stay.data,
            stay_ensemble=form.stay_ensemble.data if form.wants_to_stay.data else None,
            notes=form.notes.data,
            submission_date=date.today(),
            status="pending",
            created_by_id=current_user.id,
        )

        for player in form.players.data:
            enrollment_request.players.append(
                ChamberEnrollmentRequestPlayer(player=player)
            )

        db.session.add(enrollment_request)
        db.session.commit()

        flash("Přihláška byla úspěšně podána. Děkujeme!", "success")
        return redirect(url_for("student_portal.dashboard"))

    return render_template(
        "chamber_enrollment_form.html",
        form=form,
        student=student,
        current_semester=current_semester,
        upcoming_semester=upcoming_semester, # Pass this so the template can display the target semester name
        current_ensembles=current_ensembles,
    )
