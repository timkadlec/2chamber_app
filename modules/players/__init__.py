from flask import Blueprint
from utils.decorators import admin_required
from flask_login import login_required

players_bp = Blueprint(
    'players',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes
