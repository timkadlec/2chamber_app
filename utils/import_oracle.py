from sqlite3 import IntegrityError

from models import Semester, db, AcademicYear, StudentSubjectEnrollment, Subject
import re


def _get_or_create_academic_year(semester_id):
    year = int(semester_id[:4])  # 2025
    short = year % 100
    next_short = short + 1
    year_name = f"{short:02d}/{next_short:02d}"
    lookup = AcademicYear.query.filter_by(name=year_name).first()
    if lookup:
        return lookup
    try:
        new_academic_year = AcademicYear(name=year_name)
        db.session.add(new_academic_year)
        db.session.commit()
        return new_academic_year
    except IntegrityError:
        db.session.rollback()
        return None


def _get_semester_name(semester_id):
    pattern_winter = re.compile(r"^\d*1$")
    pattern_summer = re.compile(r"^\d*2$")
    if pattern_winter.match(semester_id):
        return "ZS"
    elif pattern_summer.match(semester_id):
        return "LS"
    else:
        return None


def _get_or_create_semester(semester_id):
    lookup = Semester.query.filter_by(id=semester_id).first()
    if lookup:
        return lookup
    try:
        new_semester = Semester(id=semester_id, name=_get_semester_name(semester_id))
        db.session.add(new_semester)
        db.session.commit()
        return new_semester
    except IntegrityError:
        db.session.rollback()
        return None


def _get_or_create_subject(subject_name, subject_code):
    """Function that find or creates a Subject object and returns it."""
    lookup = Subject.query.filter_by(name=subject_name, code=subject_code).first()
    if lookup:
        return lookup

    try:
        new_subject = Subject(name=subject_name,
                              code=subject_code)
        db.session.add(new_subject)
        db.session.commit()
        return new_subject

    except IntegrityError:
        db.session.rollback()
        return None


def _student_subject_enrollment(student_id, subject_code, semester_id):
    lookup = StudentSubjectEnrollment.query.filter_by(student_id=student_id, subject_id=subject_code,
                                                      semester_id=semester_id).first()
    if lookup:
        return lookup
    else:
        StudentSubjectEnrollment(
            student_id=student_id,
            subject_id=subject_code,
            semester_id=semester_id,
        )
        db.session.commit()
        return lookup
