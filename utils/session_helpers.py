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
