from datetime import date, timedelta
from sqlalchemy import func, select, exists, case
from models import (
    db,
    Ensemble,
    EnsembleSemester,
    EnsembleTeacher,
    EnsembleInstrumentation,
    EnsemblePlayer,
    Player,
    Teacher,
    Instrument,
)


def get_dashboard_data(current_sem):
    """Compute all dashboard metrics for the given semester ID."""

    # --- Base ensembles query ---
    ens_q = db.session.query(Ensemble).filter(
        Ensemble.semester_links.any(EnsembleSemester.semester_id == current_sem)
    )

    # === KPIs ===
    total_ensembles = ens_q.count()
    incomplete_count = ens_q.filter(Ensemble.is_complete_in(current_sem).is_(False)).count()

    min_fail_count = ens_q.filter(
        Ensemble.health_check_in(current_sem) == "Soubor nesplňuje kritérium minima hráčů."
    ).count()

    high_guests_count = ens_q.filter(
        Ensemble.health_check_in(current_sem) == "Soubor obsahuej vysoké procento hostů."
    ).count()

    teachers_involved = (
                            db.session.query(func.count(func.distinct(EnsembleTeacher.teacher_id)))
                            .filter(
                                EnsembleTeacher.semester_id == current_sem,
                                EnsembleTeacher.ensemble_id.in_(ens_q.with_entities(Ensemble.id)),
                            )
                            .scalar()
                        ) or 0

    # --- Average players per ensemble ---
    players_per_ensemble = (
        db.session.query(
            Ensemble.id,
            func.count(EnsemblePlayer.id).label("cnt")
        )
        .join(EnsemblePlayer, EnsemblePlayer.ensemble_id == Ensemble.id, isouter=True)
        .filter(Ensemble.id.in_(ens_q.with_entities(Ensemble.id)))
        .group_by(Ensemble.id)
        .subquery()
    )
    avg_players = (db.session.query(func.avg(players_per_ensemble.c.cnt)).scalar() or 0)

    # --- Student coverage ---
    student_counts = (
        db.session.query(
            func.sum(case((func.coalesce(Player.student_id, 0) != 0, 1), else_=0)).label("students"),
            func.count(EnsemblePlayer.id).label("total"),
        )
        .join(EnsemblePlayer, EnsemblePlayer.player_id == Player.id)
        .filter(EnsemblePlayer.ensemble_id.in_(ens_q.with_entities(Ensemble.id)))
        .one_or_none()
    )
    if student_counts and student_counts.total:
        student_coverage_pct = round(100 * (student_counts.students or 0) / student_counts.total, 1)
    else:
        student_coverage_pct = 0.0

    # === Alerts ===
    ensembles_no_teacher = (
        ens_q.filter(~Ensemble.teacher_links.any(EnsembleTeacher.semester_id == current_sem))
        .order_by(Ensemble.name)
        .limit(10)
        .all()
    )

    try:
        from models import ChamberException
        exceptions_pending = (
            db.session.query(Ensemble)
            .join(ChamberException, ChamberException.id == Ensemble.exception_id)
            .join(EnsembleSemester, EnsembleSemester.ensemble_id == Ensemble.id)
            .filter(
                EnsembleSemester.semester_id == current_sem,
                ChamberException.status == "pending",
            )
            .order_by(Ensemble.name)
            .limit(10)
            .all()
        )
    except Exception:
        exceptions_pending = []

    # --- Unassigned instrumentation ---
    unassigned = (
        db.session.query(
            Instrument.abbreviation.label("abbr"),
            func.count(EnsembleInstrumentation.id).label("cnt"),
        )
        .select_from(EnsembleInstrumentation)
        .join(Ensemble, Ensemble.id == EnsembleInstrumentation.ensemble_id)
        .join(EnsembleSemester, EnsembleSemester.ensemble_id == Ensemble.id)
        .join(Instrument, Instrument.id == EnsembleInstrumentation.instrument_id)
        .outerjoin(
            EnsemblePlayer,
            EnsemblePlayer.ensemble_instrumentation_id == EnsembleInstrumentation.id,
        )
        .filter(EnsembleSemester.semester_id == current_sem)
        .filter(
            ~exists(
                select(1)
                .where(
                    EnsemblePlayer.ensemble_instrumentation_id == EnsembleInstrumentation.id,
                    EnsemblePlayer.player_id.isnot(None),
                )
                .correlate(EnsembleInstrumentation)
            )
        )

        .group_by(Instrument.abbreviation)
        .order_by(func.count(EnsembleInstrumentation.id).desc())
        .limit(5)
        .all()
    )

    # --- Events (next 14 days) ---
    from models import Event
    today = date.today()
    soon = today + timedelta(days=14)
    next_events = (
        db.session.query(Event)
        .filter(Event.date_start >= today, Event.date_start <= soon)
        .order_by(Event.date_start, Event.time_start)
        .limit(12)
        .all()
    )

    # --- Top teachers by hours ---
    top_teachers = (
        db.session.query(
            Teacher.id,
            Teacher.full_name,
            func.coalesce(func.sum(EnsembleTeacher.hour_donation), 0.0).label("hours"),
        )
        .join(EnsembleTeacher, EnsembleTeacher.teacher_id == Teacher.id)
        .filter(EnsembleTeacher.semester_id == current_sem)
        .group_by(Teacher.id, Teacher.full_name)
        .order_by(func.sum(EnsembleTeacher.hour_donation).desc(), Teacher.last_name, Teacher.first_name)
        .limit(10)
        .all()
    )

    return dict(
        total_ensembles=total_ensembles,
        incomplete_count=incomplete_count,
        min_fail_count=min_fail_count,
        high_guests_count=high_guests_count,
        teachers_involved=teachers_involved,
        avg_players=avg_players,
        student_coverage_pct=student_coverage_pct,
        ensembles_no_teacher=ensembles_no_teacher,
        exceptions_pending=exceptions_pending,
        unassigned=unassigned,
        next_events=next_events,
        top_teachers=top_teachers,
    )
