# ui/routes.py (or wherever your blueprint lives)
from flask import redirect, request, session, url_for, render_template
from models import Semester, Subject
from . import subject_bp
from utils.nav import navlink


@subject_bp.route('/all-subjects')
@navlink("Předměty", weight=40)
def all_subjects():
    subjects = Subject.query.all()
    return render_template("all_subjects.html", subjects=subjects)