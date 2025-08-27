from flask import Blueprint
from utils.decorators import roles_required
from flask_login import login_required

library_bp = Blueprint(
    'library',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes
