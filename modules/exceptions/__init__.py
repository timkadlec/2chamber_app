from flask import Blueprint
from flask_login import login_required

exceptions_bp = Blueprint(
    'exceptions',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes
