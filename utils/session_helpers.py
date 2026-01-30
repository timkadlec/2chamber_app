from flask import session
from models import Semester, db


def get_or_set_current_semester():
    sid = session.get("semester_id")
    if sid:
        current = Semester.query.get(sid)
        return current
    current = Semester.query.order_by(Semester.start_date.desc()).first()
    if current:
        session["semester_id"] = current.id
        return current
    return None


def get_or_set_current_semester_id():
    sid = session.get("semester_id")
    if sid:
        return sid
    current = Semester.query.order_by(Semester.start_date.desc()).first()
    if current:
        session["semester_id"] = current.id
        return current.id
    return None

def get_or_set_previous_semester_id():
    current_id = session.get("semester_id")
    if not current_id:
        return None

    # if cached and still valid, reuse
    cached = session.get("previous_semester_id")
    if cached:
        return cached

    current = Semester.query.get(current_id)
    if not current or not current.start_date:
        return None

    previous = (
        Semester.query
        .filter(
            Semester.end_date.isnot(None),
            Semester.end_date < current.start_date
        )
        .order_by(Semester.end_date.desc())
        .first()
    )

    if previous:
        session["previous_semester_id"] = previous.id
        return previous.id

    return None

