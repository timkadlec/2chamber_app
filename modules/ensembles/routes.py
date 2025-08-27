from flask import render_template, request, flash, redirect, url_for
from .forms import CompositionForm, ComposerForm, CompositionFilterForm
from utils.nav import navlink
from modules.library import library_bp
from models import db, Composition, Composer
from orchestration_parser import process_chamber_instrumentation_line


@library_bp.route("/all")
@navlink("Skladatelé", weight=110, group="Knihovna")
def all_ensembles():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Adjust as needed
    pagination = Composer.query.order_by(Composer.last_name).paginate(page=page, per_page=per_page, error_out=False)
    composers = pagination.items
    return render_template("library_composers.html", ensembles=ensembles, pagination=pagination)
