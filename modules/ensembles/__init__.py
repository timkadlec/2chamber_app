from flask import Blueprint

ensemble_bp = Blueprint(
    'ensemble',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes
