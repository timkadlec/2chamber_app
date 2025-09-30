from flask import Blueprint
from flask_login import login_required

ui_bp = Blueprint(
    'ui',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes
