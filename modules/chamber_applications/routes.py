from flask import render_template, request, flash, redirect, url_for
from utils.nav import navlink
from modules.chamber_applications import chamber_applications_bp
from models import Composition, Composer
from models import db, StudentChamberApplication, StudentChamberApplicationPlayers
from .forms import StudentChamberApplicationForm
from flask_login import current_user
from orchestration_parser import process_chamber_instrumentation_line


@chamber_applications_bp.route("/")
@navlink("Žádosti")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 20

    pagination = StudentChamberApplication.query \
        .order_by(StudentChamberApplication.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    applications = pagination.items

    return render_template(
        "all_chamber_applications.html",
        applications=applications,
        pagination=pagination
    )


@chamber_applications_bp.route("/new", methods=["GET", "POST"])
def new_application():
    form = StudentChamberApplicationForm()

    if form.validate_on_submit():
        application = StudentChamberApplication(
            student=form.student.data,
            created_by=current_user
        )

        for player in form.players.data:
            app_player = StudentChamberApplicationPlayers(player=player)
            application.players.append(app_player)

        db.session.add(application)
        db.session.commit()

        flash("Application created successfully!", "success")
        return redirect(url_for("bp.applications_list"))

    return render_template("new_chamber_application.html", form=form)
