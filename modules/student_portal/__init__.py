from flask import Blueprint

student_portal_bp = Blueprint(
    'student_portal',
    __name__,
    template_folder='templates',
    url_prefix='/portal/student',
)

from . import routes
