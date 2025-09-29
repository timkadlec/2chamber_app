from flask import render_template, request, flash, redirect, url_for, session
from utils.nav import navlink
from modules.chamber_applications import chamber_applications_bp
from models import db, StudentChamberApplication, StudentChamberApplicationPlayers, StudentChamberApplicationStatus
from .forms import StudentChamberApplicationForm
from flask_login import current_user


@chamber_applications_bp.route("/")
@navlink("Žádosti")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 20

    pagination = StudentChamberApplication.query \
        .order_by(StudentChamberApplication.created_at.desc()) \
        .filter_by(semester_id=session.get("semester_id")) \
        .paginate(page=page, per_page=per_page, error_out=False)

    applications = pagination.items
    return render_template(
        "all_chamber_applications.html",
        applications=applications,
        pagination=pagination
    )


@chamber_applications_bp.route("/<int:application_id>/detail")
def application_detail(application_id):
    application = StudentChamberApplication.query.get_or_404(application_id)
    return render_template("chamber_application_detail.html", application=application)


@chamber_applications_bp.route("/new", methods=["GET", "POST"])
def new_application():
    form = StudentChamberApplicationForm()

    if form.validate_on_submit():
        application = StudentChamberApplication(
            student=form.student.data,
            semester_id=session.get("semester_id"),
            created_by=current_user,
            submission_date=form.submission_date.data,
            notes=form.notes.data,
            status_id=1,
        )

        for player in form.players.data:
            app_player = StudentChamberApplicationPlayers(player=player)
            application.players.append(app_player)

        db.session.add(application)
        db.session.commit()

        flash("Žádost byla úspěšně vytvořena!", "success")
        return redirect(url_for("chamber_applications.index"))

    return render_template("new_chamber_application.html", form=form)


def get_status_by_name(name: str):
    """Helper to fetch a status row by its name."""
    return StudentChamberApplicationStatus.query.filter_by(name=name).first()


@chamber_applications_bp.route("/<int:application_id>/approve", methods=["POST"])
def approve(application_id):
    app = StudentChamberApplication.query.get_or_404(application_id)

    approved_status = get_status_by_name("approved")
    if not approved_status:
        flash("Chybí status 'approved' v databázi!", "danger")
        return redirect(url_for("chamber_applications.detail", application_id=application_id))

    app.status = approved_status
    db.session.commit()

    flash(f"Žádost č. {app.id} byla schválena.", "success")
    return redirect(url_for("chamber_applications.detail", application_id=application_id))


@chamber_applications_bp.route("/<int:application_id>/reject", methods=["POST"])
def reject(application_id):
    app = StudentChamberApplication.query.get_or_404(application_id)

    rejected_status = get_status_by_name("rejected")
    if not rejected_status:
        flash("Chybí status 'rejected' v databázi!", "danger")
        return redirect(url_for("chamber_applications.detail", application_id=application_id))

    reason = request.form.get("reason")
    app.status = rejected_status
    if reason:  # optional note
        if app.notes:
            app.notes += f"\n\n[Důvod zamítnutí] {reason}"
        else:
            app.notes = f"[Důvod zamítnutí] {reason}"

    db.session.commit()

    flash(f"Žádost č. {app.id} byla zamítnuta.", "warning")
    return redirect(url_for("chamber_applications.detail", application_id=application_id))


@chamber_applications_bp.route("/<int:application_id>/delete", methods=["POST"])
def delete_application(application_id):
    application = StudentChamberApplication.query.get_or_404(application_id)
    db.session.delete(application)
    db.session.commit()
    flash(f"Žádost byla úspěšně smazána", "success")
    return redirect(url_for("chamber_applications.index"))
