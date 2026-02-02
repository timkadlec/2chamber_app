from weasyprint import HTML
from flask import make_response, render_template, current_app
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from collections import defaultdict
from sqlalchemy.orm import selectinload
from models import db
from models.ensembles import EnsemblePlayer, EnsembleTeacher
from models.players import Player


def build_ensemble_semester_pdf_maps(ensemble_ids: list[int], semester_id: int):
    """
    Returns dicts keyed by ensemble_id so templates can render semester-correct counts,
    teachers, and (optionally) players without leaking other semesters.
    """
    if not ensemble_ids:
        return {
            "player_links_by_ensemble": {},
            "student_count_by_ensemble": {},
            "external_count_by_ensemble": {},
            "teachers_by_ensemble": {},
        }

    # --- players in THIS semester only ---
    eps = (
        db.session.query(EnsemblePlayer)
        .filter(
            EnsemblePlayer.ensemble_id.in_(ensemble_ids),
            EnsemblePlayer.semester_id == semester_id,
        )
        .options(
            selectinload(EnsemblePlayer.player).selectinload(Player.student),
        )
        .all()
    )

    player_links_by_ensemble = defaultdict(list)
    student_count_by_ensemble = defaultdict(int)
    external_count_by_ensemble = defaultdict(int)

    for ep in eps:
        player_links_by_ensemble[ep.ensemble_id].append(ep)
        if ep.player_id and ep.player:
            if ep.player.student_id is not None:
                student_count_by_ensemble[ep.ensemble_id] += 1
            else:
                external_count_by_ensemble[ep.ensemble_id] += 1

    # --- teachers in THIS semester only ---
    et_rows = (
        db.session.query(EnsembleTeacher)
        .filter(
            EnsembleTeacher.ensemble_id.in_(ensemble_ids),
            EnsembleTeacher.semester_id == semester_id,
        )
        .options(selectinload(EnsembleTeacher.teacher))
        .all()
    )

    teachers_by_ensemble = defaultdict(list)
    for row in et_rows:
        if row.teacher:
            teachers_by_ensemble[row.ensemble_id].append(row)

    # ensure keys exist for ensembles with no rows
    for eid in ensemble_ids:
        player_links_by_ensemble.setdefault(eid, [])
        student_count_by_ensemble.setdefault(eid, 0)
        external_count_by_ensemble.setdefault(eid, 0)
        teachers_by_ensemble.setdefault(eid, [])

    return {
        "player_links_by_ensemble": dict(player_links_by_ensemble),
        "student_count_by_ensemble": dict(student_count_by_ensemble),
        "external_count_by_ensemble": dict(external_count_by_ensemble),
        "teachers_by_ensemble": dict(teachers_by_ensemble),
    }


# ------------------------------
#   PDF RENDERING
# ------------------------------
def render_pdf(template_name, context, filename_prefix):
    """
    Render a WeasyPrint PDF with shared layout and metadata.
    Ensures consistent logo, date, time, and filename.
    """
    # --- logo and metadata ---
    logo_path = Path(current_app.static_folder) / "images" / "hamu_logo.png"
    logo_url = logo_path.resolve().as_uri()

    context.setdefault("logo_url", logo_url)

    # --- timestamp (Europe/Prague) ---
    tz = ZoneInfo("Europe/Prague")
    now = datetime.now(tz)
    context.setdefault("today", now.date())

    # --- render PDF ---
    html = render_template(template_name, **context)
    pdf = HTML(string=html, base_url=str(Path(current_app.root_path).resolve())).write_pdf()

    # --- response setup ---
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"

    # Include date + time in filename, RFC 5987 encoded
    filename = f"{filename_prefix}_{now:%Y%m%d_%H%M}.pdf"
    response.headers["Content-Disposition"] = (
        f"attachment; filename={filename}; filename*=UTF-8''{filename}"
    )

    return response
