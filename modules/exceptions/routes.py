from . import exceptions_bp
from flask_login import login_required
from utils.nav import navlink
from flask import render_template, request
from utils.decorators import role_required
from models import db, StudentChamberApplicationException


@exceptions_bp.route("/", methods=["GET"])
@navlink("Výjimky", weight=100, roles=["admin"])
@role_required("admin")
def index():
    # Get page from querystring (default = 1)
    page = request.args.get("page", 1, type=int)
    per_page = 20  # adjust to your needs

    pagination = StudentChamberApplicationException.query.order_by(
        StudentChamberApplicationException.id.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "exceptions_index.html",
        exceptions=pagination.items,
        pagination=pagination
    )


@exceptions_bp.route("/<int:exception_id>")
def detail(exception_id):
    exception = StudentChamberApplicationException.query.get_or_404(exception_id)
    return render_template("exception_detail.html", exception=exception)
