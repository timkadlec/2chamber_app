from flask import Blueprint
from flask_login import login_required

teachers_bp = Blueprint(
    'teachers',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes
