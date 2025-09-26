from flask import render_template, request, flash, redirect, url_for, session, request
from utils.nav import navlink
from models import Student, StudentSubjectEnrollment, Instrument
from modules.students import students_bp


@students_bp.route("/", methods=["GET"])
@navlink("Studenti")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 20
    semester_id = session.get("semester_id")

    query = Student.query

    # Filter by semester
    if semester_id:
        query = query.join(StudentSubjectEnrollment).filter(
            StudentSubjectEnrollment.semester_id == semester_id
        )

    # Filter by instrument
    instrument_id = request.args.get("instrument_id", type=int)
    if instrument_id:
        query = query.filter(Student.instrument_id == instrument_id)

    # Filter by active status
    active = request.args.get("active")
    if active in ("0", "1"):
        query = query.filter(Student.active == (active == "1"))

    # Sort by name
    query = query.order_by(Student.last_name, Student.first_name)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "all_students.html",
        students=pagination.items,
        pagination=pagination,
        instruments=Instrument.query.filter_by(is_primary=True).order_by(Instrument.weight).all(),
        selected_instrument_id=instrument_id,
    )
