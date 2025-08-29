from flask import Blueprint
from utils.decorators import admin_required
from flask_login import login_required

subject_bp = Blueprint(
    'subject',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes
