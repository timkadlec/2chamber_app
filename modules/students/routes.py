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

    instrument_ids = request.args.getlist("instrument_id", type=int)
    subject_ids = request.args.getlist("subject_id", type=int)

    # Instrument filter
    if instrument_ids:
        query = query.filter(Student.instrument_id.in_(instrument_ids))

    # Subject / semester filters
    if semester_id or subject_ids:
        query = query.join(StudentSubjectEnrollment)

        if semester_id:
            query = query.filter(StudentSubjectEnrollment.semester_id == semester_id)

        if subject_ids:
            query = query.filter(StudentSubjectEnrollment.subject_id.in_(subject_ids))

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
        selected_instrument_ids=instrument_ids,
        selected_subject_ids=subject_ids,
        selected_active=active,
        search_query=search_query,
    )
