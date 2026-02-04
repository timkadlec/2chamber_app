from sqlalchemy import or_, func, select, exists
from flask import request

from models import (
    Ensemble,
    EnsembleTeacher,
    EnsembleInstrumentation,
    Player,
    Student,
    EnsemblePlayer,
    Teacher,
)

def norm(expr):
    """Lower + unaccent (Postgres)."""
    return func.lower(func.unaccent(expr))

def get_common_filters():
    return {
        "instrument_ids": request.args.getlist("instrument_id", type=int),
        "teacher_ids": request.args.getlist("teacher_id", type=int),
        "department_ids": request.args.getlist("department_id", type=int),
        "search_query": request.args.get("q", "").strip(),
        "health_filter": request.args.get("health", "").strip(),
        "incomplete_filter": request.args.get("incomplete", "").strip(),
    }

def apply_common_filters(query, filters, current_semester_id: int):
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
                EnsembleTeacher.semester_id == current_semester_id,
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
            .join(Teacher, Teacher.id == EnsembleTeacher.teacher_id)
            .where(
                EnsembleTeacher.ensemble_id == Ensemble.id,
                EnsembleTeacher.semester_id == current_semester_id,
                Teacher.department_id.in_(department_ids),
            )
            .correlate(Ensemble)
            .exists()
        )
        query = query.filter(subq)

    # --- Incomplete / complete filter ---
    if incomplete_filter in ("1", "0"):
        query = query.filter(
            Ensemble.is_complete_in(current_semester_id).is_(False)
            if incomplete_filter == "1"
            else Ensemble.is_complete_in(current_semester_id).is_(True)
        )

    # --- Search filter ---
    if search_query:
        # normalize input to ascii-ish (so "Novak" finds "Novák")
        try:
            from unidecode import unidecode
            needle = unidecode(search_query).lower()
        except Exception:
            needle = search_query.lower()

        like_needle = f"%{needle}%"

        ens_name_match = norm(Ensemble.name).ilike(like_needle)

        last = func.coalesce(Student.last_name, Player.last_name)
        first = func.coalesce(Student.first_name, Player.first_name)

        name_lf = func.concat_ws(" ", last, first)
        name_fl = func.concat_ws(" ", first, last)

        player_match_exists = exists(
            select(1)
            .select_from(EnsemblePlayer)
            .join(Player, Player.id == EnsemblePlayer.player_id)
            .outerjoin(Student, Student.id == Player.student_id)
            .where(
                EnsemblePlayer.ensemble_id == Ensemble.id,
                EnsemblePlayer.semester_id == current_semester_id,
                EnsemblePlayer.player_id.isnot(None),
                or_(
                    norm(name_lf).ilike(like_needle),
                    norm(name_fl).ilike(like_needle),
                ),
            )
        )

        query = query.filter(or_(ens_name_match, player_match_exists))

    # --- Health filter ---
    if health_filter:
        query = query.filter(Ensemble.health_check_in(current_semester_id) == health_filter)

    return query
