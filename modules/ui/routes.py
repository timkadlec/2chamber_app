# ui/routes.py (or wherever your blueprint lives)
from flask import redirect, request, session, url_for
from models import Semester
from . import ui_bp


@ui_bp.route('/set-semester/<int:semester_id>')
def set_semester(semester_id):
    sem = Semester.query.get_or_404(semester_id)
    session['semester_id'] = sem.id
    next_url = request.args.get('next') or request.referrer or url_for('index')
    return redirect(next_url)
