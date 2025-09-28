from flask import render_template, request, flash, redirect, url_for, session, request
from utils.nav import navlink
from models import Student, StudentSubjectEnrollment, Instrument, Subject
from modules.students import students_bp
from sqlalchemy import and_

from sqlalchemy import or_


@students_bp.route("/", methods=["GET"])
@navlink("Studenti", group="Lidé", weight=100)
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 20
    semester_id = session.get("semester_id")

    query = Student.query

    # Instrument filter
    instrument_id = request.args.get("instrument_id", type=int)
    if instrument_id:
        query = query.filter(Student.instrument_id == instrument_id)

    # Subject / semester filters
    selected_subject_id = request.args.get("subject_id", type=int)
    if semester_id or selected_subject_id:
        query = query.join(StudentSubjectEnrollment)

        if semester_id:
            query = query.filter(StudentSubjectEnrollment.semester_id == semester_id)

        if selected_subject_id:
            query = query.filter(StudentSubjectEnrollment.subject_id == selected_subject_id)

    # Active filter
    active = request.args.get("active")
    if active in ("0", "1"):
        query = query.filter(Student.active == (active == "1"))

    # Search filter (by first_name OR last_name)
    search_query = request.args.get("q", "").strip()
    if search_query:
        query = query.filter(
            or_(
                Student.first_name.ilike(f"%{search_query}%"),
                Student.last_name.ilike(f"%{search_query}%"),
            )
        )

    # Sort by name
    query = query.order_by(Student.last_name, Student.first_name)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "all_students.html",
        students=pagination.items,
        pagination=pagination,
        subjects=Subject.query.order_by(Subject.weight).all(),
        instruments=Instrument.query.filter_by(is_primary=True).order_by(Instrument.weight).all(),
        selected_instrument_id=instrument_id,
        selected_subject_id=selected_subject_id,
        selected_active=active,
        search_query=search_query,
    )
