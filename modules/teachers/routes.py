from . import teachers_bp
from utils.nav import navlink
from collections import defaultdict
from flask import render_template
from sqlalchemy.orm import joinedload
from models import Teacher
from models.ensembles import EnsembleTeacher
from utils.session_helpers import get_or_set_current_semester_id
from models.core import Semester

@teachers_bp.route('/all')
@navlink("Pedagogové", group="Lidé", weight=150)
def index():
    teachers = Teacher.query.order_by(Teacher.last_name).all()
    return render_template("all_teachers.html", teachers=teachers)

@teachers_bp.route("/teacher/<int:teacher_id>")
def teacher_detail(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    current_semester_id = get_or_set_current_semester_id()
    return render_template(
        "teacher_detail.html",
        teacher=teacher,
        current_semester_id=current_semester_id
    )



@teachers_bp.route("/workloads")
def workloads():
    current_semester_id = get_or_set_current_semester_id()
    current_semester = Semester.query.get(current_semester_id)

    # Teachers that are linked in the current semester (same idea as your PDF export)
    teachers = (
        Teacher.query
        .join(EnsembleTeacher, EnsembleTeacher.teacher_id == Teacher.id)
        .filter(EnsembleTeacher.semester_id == current_semester_id)
        .options(
            joinedload(Teacher.department),  # if relationship exists
        )
        .distinct()
        .order_by(Teacher.department_id, Teacher.last_name, Teacher.first_name)
        .all()
    )

    # Attach pdf_rows = list of EnsembleTeacher links for this semester (with ensembles)
    # so the existing PDF-based template structure works unchanged.
    for t in teachers:
        t.pdf_rows = (
            EnsembleTeacher.query
            .filter(
                EnsembleTeacher.semester_id == current_semester_id,
                EnsembleTeacher.teacher_id == t.id,
            )
            .options(joinedload(EnsembleTeacher.ensemble))
            .order_by(EnsembleTeacher.id)
            .all()
        )

    # Group by department name (string key matches your PDF template)
    grouped = defaultdict(list)
    for t in teachers:
        dept_name = (t.department.name if getattr(t, "department", None) else "Bez katedry")
        grouped[dept_name].append(t)

    grouped_teachers = dict(grouped)

    return render_template(
        "workloads.html",
        current_semester=current_semester,
        grouped_teachers=grouped_teachers,
    )
