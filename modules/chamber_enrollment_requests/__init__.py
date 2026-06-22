from flask import Blueprint

chamber_enrollment_requests_bp = Blueprint(
    'chamber_enrollment_requests',
    __name__,
    template_folder='templates',
)

from . import routes
