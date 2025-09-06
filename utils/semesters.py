from datetime import datetime
from models import Semester, db, AcademicYear
import re


def get_current_or_upcoming_semester():
    now = datetime.utcnow()  # safer if DB is UTC
    current = Semester.query.filter(
        Semester.start_date <= now,
        Semester.end_date >= now
    ).first()
    if current:
        return current

    return (Semester.query
            .filter(Semester.start_date > now)
            .order_by(Semester.start_date.asc())
            .first())

