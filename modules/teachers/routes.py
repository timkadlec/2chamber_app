# ui/routes.py (or wherever your blueprint lives)
from flask import redirect, request, session, url_for, render_template
from models import Semester, Teacher
from . import teachers_bp
from utils.nav import navlink


@teachers_bp.route('/all')
@navlink("Pedagogové", group="Lidé", weight=150)
def index():
    teachers = Teacher.query.order_by(Teacher.last_name).all()
    return render_template("all_teachers.html", teachers=teachers)