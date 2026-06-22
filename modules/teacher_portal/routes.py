from flask import render_template, redirect, url_for, abort, request
from flask_login import current_user
from modules.teacher_portal import teacher_portal_bp
from models import Semester, EnsembleTeacher, EnsemblePlayer, db
from utils.session_helpers import get_or_set_current_semester
from sqlalchemy.orm import joinedload


@teacher_portal_bp.before_request
def require_teacher():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.portal_type != "teacher":
        abort(403)


@teacher_portal_bp.route("/")
def dashboard():
    teacher = current_user.teacher

    # All semesters this teacher has been linked to an ensemble, newest first
    teacher_semesters = (
        Semester.query
        .join(EnsembleTeacher, EnsembleTeacher.semester_id == Semester.id)
        .filter(EnsembleTeacher.teacher_id == teacher.id)
        .distinct()
        .order_by(Semester.start_date.desc())
        .all()
    )

    semester_id = request.args.get("semester_id", type=int)
    if semester_id:
        semester = Semester.query.get_or_404(semester_id)
    elif teacher_semesters:
        semester = teacher_semesters[0]
    else:
        semester = get_or_set_current_semester()

    # Ensembles this teacher is assigned to in the selected semester
    ensemble_links = (
        EnsembleTeacher.query
        .filter_by(teacher_id=teacher.id, semester_id=semester.id if semester else None)
        .options(joinedload(EnsembleTeacher.ensemble))
        .all()
    ) if semester else []

    # Players per ensemble for this semester
    ensemble_details = {}
    for link in ensemble_links:
        ensemble = link.ensemble
        ensemble_details[ensemble.id] = EnsemblePlayer.query.filter_by(
            ensemble_id=ensemble.id,
            semester_id=semester.id,
        ).options(joinedload(EnsemblePlayer.player)).all()

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        semester=semester,
        teacher_semesters=teacher_semesters,
        ensemble_links=ensemble_links,
        ensemble_details=ensemble_details,
    )
