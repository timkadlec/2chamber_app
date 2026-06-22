from flask import render_template, request, flash, redirect, url_for, session
from flask_login import current_user
from utils.nav import navlink
from utils.decorators import permission_required
from modules.chamber_enrollment_requests import chamber_enrollment_requests_bp
from models import (
    db, ChamberEnrollmentRequest, Semester, Student,
    Ensemble, EnsembleSemester, EnsemblePlayer, EnsembleInstrumentation, EnsembleTeacher,
)
from datetime import datetime
from sqlalchemy.exc import IntegrityError


@chamber_enrollment_requests_bp.route("/")
@navlink("Přihlášky KH", permission="cer_can_view")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 25

    semester_id = request.args.get("semester_id", type=int) or session.get("semester_id")
    status_filter = request.args.get("status", "")

    query = ChamberEnrollmentRequest.query

    if semester_id:
        query = query.filter(ChamberEnrollmentRequest.semester_id == semester_id)

    if status_filter:
        query = query.filter(ChamberEnrollmentRequest.status == status_filter)

    query = query.join(Student).order_by(Student.last_name, Student.first_name)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "all_enrollment_requests.html",
        requests=pagination.items,
        pagination=pagination,
        semesters=Semester.query.order_by(Semester.start_date.desc()).all(),
        selected_semester_id=semester_id,
        selected_status=status_filter,
    )


@chamber_enrollment_requests_bp.route("/<int:request_id>")
@permission_required("cer_can_view")
def detail(request_id):
    enrollment_request = ChamberEnrollmentRequest.query.get_or_404(request_id)

    current_semester_id = session.get("semester_id")
    current_semester = Semester.query.get(current_semester_id) if current_semester_id else None

    future_semesters = Semester.query.filter(
        Semester.start_date > (current_semester.start_date if current_semester else db.func.now())
    ).order_by(Semester.start_date.asc()).all()

    ensembles = Ensemble.query.filter_by(active=True).order_by(Ensemble.name).all()

    return render_template(
        "enrollment_request_detail.html",
        req=enrollment_request,
        future_semesters=future_semesters,
        ensembles=ensembles,
    )


def _add_semester_to_ensemble(ensemble, semester):
    already = EnsembleSemester.query.filter_by(
        ensemble_id=ensemble.id,
        semester_id=semester.id,
    ).first()
    if not already:
        db.session.add(EnsembleSemester(ensemble=ensemble, semester=semester))


def _create_ensemble_from_cer(cer, target_semester):
    student = cer.student
    applicant_player = student.player

    instruments = []
    if student.instrument:
        instruments.append(student.instrument.abbreviation or student.instrument.name)
    for cerp in cer.players:
        if cerp.player.instrument:
            instruments.append(cerp.player.instrument.abbreviation or cerp.player.instrument.name)

    name = f"{student.full_name} ({', '.join(instruments)})" if instruments else student.full_name

    ensemble = Ensemble(name=name, active=True)
    db.session.add(ensemble)
    db.session.add(EnsembleSemester(ensemble=ensemble, semester=target_semester))

    # Applicant
    if applicant_player and student.instrument:
        inst_entry = EnsembleInstrumentation(ensemble=ensemble, instrument=student.instrument, position=1)
        db.session.add(inst_entry)
        db.session.add(EnsemblePlayer(
            ensemble=ensemble,
            player=applicant_player,
            ensemble_instrumentation=inst_entry,
            semester_id=target_semester.id,
        ))

    # Co-players
    for idx, cerp in enumerate(cer.players, start=2):
        instrument = cerp.player.instrument
        inst_entry = None
        if instrument:
            inst_entry = EnsembleInstrumentation(ensemble=ensemble, instrument=instrument, position=idx)
            db.session.add(inst_entry)
        db.session.add(EnsemblePlayer(
            ensemble=ensemble,
            player=cerp.player,
            ensemble_instrumentation=inst_entry,
            semester_id=target_semester.id,
        ))

    # Teacher
    if cer.teacher:
        db.session.add(EnsembleTeacher(
            ensemble=ensemble,
            teacher=cer.teacher,
            semester_id=target_semester.id,
        ))

    db.session.flush()
    return ensemble


@chamber_enrollment_requests_bp.route("/<int:request_id>/approve", methods=["POST"])
@permission_required("cer_can_edit")
def approve(request_id):
    cer = ChamberEnrollmentRequest.query.get_or_404(request_id)

    target_semester_id = request.form.get("target_semester_id", type=int)
    ensemble_mode = request.form.get("ensemble_mode", "new")
    existing_ensemble_id = request.form.get("existing_ensemble_id", type=int)
    comment = request.form.get("comment", "").strip() or None

    target_semester = Semester.query.get(target_semester_id) if target_semester_id else None

    result_ensemble = None

    try:
        if target_semester:
            if ensemble_mode == "stay" and cer.stay_ensemble:
                _add_semester_to_ensemble(cer.stay_ensemble, target_semester)
                result_ensemble = cer.stay_ensemble
            elif ensemble_mode == "existing" and existing_ensemble_id:
                existing = Ensemble.query.get_or_404(existing_ensemble_id)
                _add_semester_to_ensemble(existing, target_semester)
                result_ensemble = existing
            else:
                result_ensemble = _create_ensemble_from_cer(cer, target_semester)

        cer.status = "approved"
        cer.reviewed_by = current_user
        cer.reviewed_at = datetime.now()
        cer.review_comment = comment
        cer.target_semester = target_semester
        cer.result_ensemble = result_ensemble

        db.session.commit()
    except (ValueError, IntegrityError) as e:
        db.session.rollback()
        flash(f"Chyba při schvalování: {e}", "danger")
        return redirect(url_for("chamber_enrollment_requests.detail", request_id=request_id))

    if result_ensemble:
        flash(
            f"Přihláška č. {cer.id} schválena. Soubor: {result_ensemble.name}.",
            "success",
        )
    else:
        flash(f"Přihláška č. {cer.id} byla schválena (bez přiřazení souboru).", "success")

    return redirect(url_for("chamber_enrollment_requests.detail", request_id=request_id))


@chamber_enrollment_requests_bp.route("/<int:request_id>/reject", methods=["POST"])
@permission_required("cer_can_edit")
def reject(request_id):
    cer = ChamberEnrollmentRequest.query.get_or_404(request_id)
    reason = request.form.get("reason", "").strip() or None

    cer.status = "rejected"
    cer.reviewed_by = current_user
    cer.reviewed_at = datetime.now()
    cer.review_comment = reason

    db.session.commit()
    flash(f"Přihláška č. {cer.id} byla zamítnuta.", "warning")
    return redirect(url_for("chamber_enrollment_requests.detail", request_id=request_id))
