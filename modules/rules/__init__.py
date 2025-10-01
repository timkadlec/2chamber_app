from flask import Blueprint
from flask_login import login_required

rules_bp = Blueprint(
    'rules',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes
