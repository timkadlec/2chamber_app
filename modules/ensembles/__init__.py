from flask import Blueprint

library_bp = Blueprint(
    'library',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes
