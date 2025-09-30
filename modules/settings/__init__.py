from flask import Blueprint
from flask_login import login_required

settings_bp = Blueprint(
    'settings',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes
