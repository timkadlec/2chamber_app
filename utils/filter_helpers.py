import unicodedata
from sqlalchemy import or_, func, select
from flask import request
from models import (
    Ensemble,
    EnsembleTeacher,
    EnsembleInstrumentation,
    Player,
    Teacher,
)


# ------------------------------
#   BASIC UTILITIES
# ------------------------------
def strip_diacritics(s: str) -> str:
    """Remove diacritics from a string for consistent searching."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def get_common_filters():
    """Extract and normalize all common filters from the request."""
    return {
        "instrument_ids": request.args.getlist("instrument_id", type=int),
        "teacher_ids": request.args.getlist("teacher_id", type=int),
        "department_ids": request.args.getlist("department_id", type=int),
        "search_query": request.args.get("q", "").strip(),
        "health_filter": request.args.get("health", "").strip(),
        "incomplete_filter": request.args.get("incomplete", "").strip(),
    }


# ------------------------------
#   FILTER APPLICATION
# ------------------------------
def apply_common_filters(query, filters, current_semester):
    """
    Apply shared filtering logic to an Ensemble query.
    Safe to reuse in routes and PDF exports.
    """
    instrument_ids = filters["instrument_ids"]
    teacher_ids = filters["teacher_ids"]
    department_ids = filters["department_ids"]
    search_query = filters["search_query"]
    health_filter = filters["health_filter"]
    incomplete_filter = filters["incomplete_filter"]

    # --- Instrument filter ---
    if instrument_ids:
        subq = (
            select(EnsembleInstrumentation.id)
            .where(
                EnsembleInstrumentation.ensemble_id == Ensemble.id,
                EnsembleInstrumentation.instrument_id.in_(instrument_ids),
            )
            .correlate(Ensemble)
            .exists()
        )
        query = query.filter(subq)

    # --- Teacher filter ---
    if teacher_ids:
        subq = (
            select(EnsembleTeacher.id)
            .where(
                EnsembleTeacher.ensemble_id == Ensemble.id,
                EnsembleTeacher.semester_id == current_semester,
                EnsembleTeacher.teacher_id.in_(teacher_ids),
            )
            .correlate(Ensemble)
            .exists()
        )
        query = query.filter(subq)

    # --- Department filter ---
    if department_ids:
        subq = (
            select(EnsembleTeacher.id)
            .join(Teacher)
            .where(
                EnsembleTeacher.ensemble_id == Ensemble.id,
                EnsembleTeacher.semester_id == current_semester,
                Teacher.department_id.in_(department_ids),
            )
            .correlate(Ensemble)
            .exists()
        )
        query = query.filter(subq)

    # --- Incomplete / complete filter ---
    if incomplete_filter in ("1", "0"):
        query = query.filter(
            Ensemble.is_complete.is_(False)
            if incomplete_filter == "1"
            else Ensemble.is_complete.is_(True)
        )

    # --- Search filter ---
    if search_query:
        search = strip_diacritics(search_query).lower()
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                func.unaccent(func.lower(Ensemble.name)).like(pattern),
                Ensemble.player_links.any(
                    or_(
                        func.unaccent(func.lower(Player.first_name)).like(pattern),
                        func.unaccent(func.lower(Player.last_name)).like(pattern),
                    )
                ),
            )
        )

    # --- Health filter ---
    if health_filter:
        query = query.filter(Ensemble.health_check_label == health_filter)

    return query

