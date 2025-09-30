from sqlalchemy import func, case


def build_ensemble_health_case(Student, EnsemblePlayer):
    """Health status for Ensemble based on EnsemblePlayer links."""
    total_players = func.count(EnsemblePlayer.id)
    student_count = func.sum(
        case((Student.id != None, 1), else_=0)
    )

    return case(
        (total_players <= 2, "minimum"),
        ((student_count * 1.0 / total_players) > 0.5, "ok"),
        else_="guests"
    ).label("health_status")


def build_chamber_health_case(Student, ChamberApplicationPlayer):
    """Health status for ChamberApplication based on ChamberApplicationPlayer links."""
    total_players = func.count(ChamberApplicationPlayer.id)
    student_count = func.sum(
        case((Student.id != None, 1), else_=0)
    )

    return case(
        (total_players <= 2, "minimum"),
        ((student_count * 1.0 / total_players) > 0.5, "ok"),
        else_="guests"
    ).label("health_status")
