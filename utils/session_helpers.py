from flask import session
from datetime import date
from models import Semester


# ---------------------------------------------------------
# CURRENT SEMESTER
# ---------------------------------------------------------

def get_or_set_current_semester():
    sid = session.get("semester_id")
    if sid:
        current = Semester.query.get(sid)
        if current:
            return current

    today = date.today()

    # 1. Ideal Match: Look for the semester that strictly contains today's date
    current = Semester.query.filter(
        Semester.start_date <= today,
        Semester.end_date >= today
    ).first()

    # 2. Fallback: If we are exactly between semesters, grab the most recently started one
    if not current:
        current = Semester.query.filter(
            Semester.start_date <= today
        ).order_by(Semester.start_date.desc()).first()

    # 3. Ultimate Fallback: If no past/current semesters exist, get the very first upcoming one
    if not current:
        current = Semester.query.order_by(Semester.start_date.asc()).first()

    if current:
        session["semester_id"] = current.id
        return current

    return None


def get_or_set_current_semester_id():
    # Reuse the main function to avoid repeating the DB logic
    current = get_or_set_current_semester()
    return current.id if current else None


# ---------------------------------------------------------
# PREVIOUS SEMESTER
# ---------------------------------------------------------

def get_or_set_previous_semester():
    """
    Returns the semester object immediately preceding the current semester.
    Maintains the get_or_set naming convention.
    """
    current_id = get_or_set_current_semester_id()
    if not current_id:
        return None

    current = Semester.query.get(current_id)
    if not current or not current.start_date:
        return None

    # Check cache first
    cached_id = session.get("previous_semester_id")
    if cached_id:
        previous = Semester.query.get(cached_id)
        # Ensure it actually precedes the current one
        if previous and previous.end_date and previous.end_date < current.start_date:
            return previous
        else:
            session.pop("previous_semester_id", None)

    # Database query fallback
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
        return previous

    return None


def get_or_set_previous_semester_id():
    """Returns the ID of the previous semester."""
    previous = get_or_set_previous_semester()
    return previous.id if previous else None


# ---------------------------------------------------------
# UPCOMING SEMESTER
# ---------------------------------------------------------

def get_upcoming_semester():
    """
    Fetches the next chronological semester starting after today.
    """
    today = date.today()

    cached_id = session.get("upcoming_semester_id")
    if cached_id:
        upcoming = Semester.query.get(cached_id)
        if upcoming and upcoming.start_date and upcoming.start_date > today:
            return upcoming
        else:
            session.pop("upcoming_semester_id", None)

    upcoming = (
        Semester.query
        .filter(Semester.start_date > today)
        .order_by(Semester.start_date.asc())
        .first()
    )

    if upcoming:
        session["upcoming_semester_id"] = upcoming.id
        return upcoming

    return None


def get_upcoming_semester_id():
    """Returns the ID of the upcoming semester."""
    upcoming = get_upcoming_semester()
    return upcoming.id if upcoming else None