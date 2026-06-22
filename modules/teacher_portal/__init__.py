from flask import Blueprint

teacher_portal_bp = Blueprint(
    "teacher_portal",
    __name__,
    url_prefix="/teacher",
    template_folder="templates",
)

from . import routes  # noqa: F401, E402
