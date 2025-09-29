from flask import render_template, request, flash, redirect, url_for, session
from utils.nav import navlink
from modules.chamber_applications import chamber_applications_bp
from models import db, Ensemble, EnsembleSemester, EnsemblePlayer, EnsembleInstrumentation, Semester, \
    StudentChamberApplication, StudentChamberApplicationPlayers, StudentChamberApplicationStatus, Student, Instrument
from .forms import StudentChamberApplicationForm, EmptyForm
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
import unicodedata
from datetime import datetime
from sqlalchemy import func, or_


def normalize(s: str) -> str:
    if not s:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    ).lower()


@chamber_applications_bp.route("/")
@navlink("Žádosti")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 20
    q = request.args.get("q", "").strip()
    hide_approved = request.args.get("hide_approved")
    status_filter = request.args.get("status")
    health_filter = request.args.get("health")
    instrument_filter = request.args.getlist("instrument_ids", type=int)

    # base query: always filter by semester
    base_query = (
        StudentChamberApplication.query
        .join(Student)
        .filter(StudentChamberApplication.semester_id == session.get("semester_id"))
    )

    # hide approved toggle
    if hide_approved:
        base_query = (
            base_query.join(StudentChamberApplicationStatus)
            .filter(StudentChamberApplicationStatus.code != "approved")
        )

    # filter by instrument (SQL-level, not Python)
    if instrument_filter:
        base_query = base_query.filter(Student.instrument_id.in_(instrument_filter))

    # sort newest first
    base_query = base_query.order_by(StudentChamberApplication.submission_date.desc())
    all_apps = base_query.all()

    # --- Status filter ---
    if status_filter:
        all_apps = [
            app for app in all_apps
            if app.status and app.status.code == status_filter
        ]

    # --- Health filter ---
    if health_filter:
        all_apps = [
            app for app in all_apps
            if (
                (health_filter == "ok" and "OK" in app.health_check)
                or (health_filter == "minimum" and "minimum" in app.health_check)
                or (health_filter == "guests" and "vysoké procento hostů" in app.health_check)
            )
        ]

    # --- Search filter ---
    if q:
        norm_q = normalize(q)
        filtered = []
        for app in all_apps:
            if norm_q in normalize(app.student.first_name) or norm_q in normalize(app.student.last_name):
                filtered.append(app)
                continue
            for entry in app.players:
                pl = entry.player
                if not pl:
                    continue
                if pl.student:
                    if norm_q in normalize(pl.student.first_name) or norm_q in normalize(pl.student.last_name):
                        filtered.append(app)
                        break
                else:
                    if norm_q in normalize(pl.full_name):
                        filtered.append(app)
                        break
        all_apps = filtered

    # manual pagination
    total = len(all_apps)
    start = (page - 1) * per_page
    end = start + per_page
    items = all_apps[start:end]

    class Pagination:
        def __init__(self, page, per_page, total, items):
            self.page, self.per_page, self.total, self.items = page, per_page, total, items
        @property
        def pages(self): return (self.total + self.per_page - 1) // self.per_page
        @property
        def has_prev(self): return self.page > 1
        @property
        def has_next(self): return self.page < self.pages
        @property
        def prev_num(self): return self.page - 1
        @property
        def next_num(self): return self.page + 1

    pagination = Pagination(page, per_page, total, items)

    # load instruments for dropdown
    instruments = db.session.query(Instrument).filter_by(is_primary=True).order_by(Instrument.weight).all()

    return render_template(
        "all_chamber_applications.html",
        applications=items,
        pagination=pagination,
        q=q,
        hide_approved=hide_approved,
        status_filter=status_filter,
        health_filter=health_filter,
        instrument_filter=instrument_filter,
        instruments=instruments,
    )


@chamber_applications_bp.route("/<int:application_id>/detail")
def detail(application_id):
    application = StudentChamberApplication.query.get_or_404(application_id)
    form = EmptyForm()
    return render_template("chamber_application_detail.html", application=application, form=form)


@chamber_applications_bp.route("/new", methods=["GET", "POST"])
def new():
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

    return render_template("chamber_application_form.html", form=form)


@chamber_applications_bp.route("/<int:application_id>/edit", methods=["GET", "POST"])
def edit(application_id):
    application = StudentChamberApplication.query.get_or_404(application_id)
    form = StudentChamberApplicationForm(obj=application, mode="edit")

    # Ensure players populate correctly
    if request.method == "GET":
        form.players.data = [link.player for link in application.players]

    if form.validate_on_submit():
        application.notes = form.notes.data
        application.submission_date = form.submission_date.data

        # Update players
        application.players.clear()
        for player in form.players.data:
            link = StudentChamberApplicationPlayers(player=player, application=application)
            application.players.append(link)

        db.session.commit()
        flash(f"Žádost č. {application.id} byla upravena.", "success")
        return redirect(url_for("chamber_applications.detail", application_id=application.id))

    return render_template("chamber_application_form.html", form=form, application=application)


def get_status_by_code(code: str):
    """Helper to fetch a status row by its name."""
    return StudentChamberApplicationStatus.query.filter_by(code=code).first()


def create_ensemble_from_application(application):
    """
    Create an Ensemble based on a StudentChamberApplication.
    Includes both the applicant and the co-players.
    """

    if not application.semester:
        raise ValueError("Application has no semester assigned.")

    # Build ensemble name: applicant + instruments
    base_name = application.student.full_name
    instrumentation_str = ", ".join(
        [p.player.instrument.abbreviation or p.player.instrument.name for p in application.players]
        + [(application.student.instrument.abbreviation or application.student.instrument.name)
           if application.student.instrument else []]
    )
    name = f"{base_name} ({instrumentation_str})"

    ensemble = Ensemble(name=name, active=True)

    # Link to semester
    db.session.add(EnsembleSemester(ensemble=ensemble, semester=application.semester))

    # --- Add applicant ---
    applicant_instrument = application.student.instrument
    if not applicant_instrument:
        raise ValueError(f"Applicant {application.student.full_name} has no instrument assigned.")

    applicant_inst_entry = EnsembleInstrumentation(
        ensemble=ensemble,
        instrument=applicant_instrument,
        position=1,
    )
    db.session.add(applicant_inst_entry)

    db.session.add(EnsemblePlayer(
        ensemble=ensemble,
        player=application.student.player,
        ensemble_instrumentation=applicant_inst_entry,
    ))

    # --- Add co-players ---
    for idx, app_player in enumerate(application.players, start=2):
        instrument = app_player.player.instrument

        inst_entry = EnsembleInstrumentation(
            ensemble=ensemble,
            instrument=instrument,
            position=idx,
        )
        db.session.add(inst_entry)

        db.session.add(EnsemblePlayer(
            ensemble=ensemble,
            player=app_player.player,
            ensemble_instrumentation=inst_entry,
        ))

    # Update application status → approved
    approved_status = StudentChamberApplicationStatus.query.filter_by(code="approved").first()
    if approved_status:
        application.status = approved_status

    db.session.add(ensemble)
    db.session.add(application)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise

    return ensemble


@chamber_applications_bp.route("/<int:application_id>/approve", methods=["POST"])
def approve(application_id):
    app = StudentChamberApplication.query.get_or_404(application_id)
    current_semester = Semester.query.get(session.get("semester_id"))

    approved_status = get_status_by_code("approved")
    if not approved_status:
        flash("Chybí status 'approved' v databázi!", "danger")
        return redirect(url_for("chamber_applications.detail", application_id=application_id))

    # Collect this application + all related ones
    related_apps = app.related_applications
    all_apps = [app] + related_apps

    # Set status = approved for all
    for a in all_apps:
        a.status = approved_status
        a.reviewed_at = datetime.now()
        a.reviewed_by = current_user
        a.review_comment = request.form.get("comment")

    # Create one ensemble from the "main" application
    new_ensemble = create_ensemble_from_application(app)

    # Optional: link ensemble_id back to applications if you want traceability
    # (Add ensemble_id FK to StudentChamberApplication if not already there)

    db.session.commit()

    flash(
        f"Žádosti {[a.id for a in all_apps]} byly schváleny a vytvořen soubor č. {new_ensemble.id}.",
        "success"
    )
    return redirect(url_for("ensemble.ensemble_detail", ensemble_id=new_ensemble.id))


@chamber_applications_bp.route("/<int:application_id>/reject", methods=["POST"])
def reject(application_id):
    app = StudentChamberApplication.query.get_or_404(application_id)

    rejected_status = get_status_by_code("rejected")
    if not rejected_status:
        flash("Chybí status 'rejected' v databázi!", "danger")
        return redirect(url_for("chamber_applications.detail", application_id=application_id))

    # Collect this application + all related ones
    related_apps = app.related_applications
    all_apps = [app] + related_apps

    reason = request.form.get("reason")

    for a in all_apps:
        a.status = rejected_status
        a.reviewed_by = current_user
        a.reviewed_at = datetime.now()
        a.review_comment = reason

        # Optional: also append to notes for traceability
        if reason:
            if a.notes:
                a.notes += f"\n\n[Důvod zamítnutí] {reason}"
            else:
                a.notes = f"[Důvod zamítnutí] {reason}"

    db.session.commit()

    flash(
        f"Žádosti {[a.id for a in all_apps]} byly zamítnuty.",
        "warning"
    )
    return redirect(url_for("chamber_applications.detail", application_id=application_id))


@chamber_applications_bp.route("/<int:application_id>/reset", methods=["POST"])
def reset(application_id):
    app = StudentChamberApplication.query.get_or_404(application_id)

    # Either set to None or a "pending" status if you have one
    pending_status = get_status_by_code("pending")
    app.status = pending_status if pending_status else None

    db.session.commit()
    flash(f"Žádost č. {app.id} byla resetována.", "info")
    return redirect(url_for("chamber_applications.detail", application_id=application_id))


@chamber_applications_bp.route("/<int:application_id>/delete", methods=["POST"])
def delete(application_id):
    application = StudentChamberApplication.query.get_or_404(application_id)
    db.session.delete(application)
    db.session.commit()
    flash(f"Žádost byla úspěšně smazána", "success")
    return redirect(url_for("chamber_applications.index"))
