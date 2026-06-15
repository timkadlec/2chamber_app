from flask import render_template, redirect, url_for, abort, request
from flask_login import current_user
from modules.student_portal import student_portal_bp
from models import (
    Semester, StudentSemesterEnrollment,
    EnsemblePlayer, EnsembleTeacher, Player,
)
from utils.session_helpers import get_or_set_current_semester


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

    return render_template(
        "student_dashboard.html",
        student=student,
        semester=semester,
        student_semesters=student_semesters,
        ensembles=ensembles,
        enrollments=enrollments,
        ensemble_details=ensemble_details,
    )
