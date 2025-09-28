from flask import Blueprint
from utils.decorators import roles_required
from flask_login import login_required

chamber_applications_bp = Blueprint(
    'chamber_applications',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes
