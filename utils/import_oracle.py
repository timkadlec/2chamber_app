from sqlalchemy.exc import IntegrityError
from models import Semester, db, AcademicYear, StudentSubjectEnrollment, Subject, Instrument, Student, Player
import re


def get_or_create_academic_year(semester_id: str):
    year = int(semester_id[:4])  # e.g., "2025"
    short = year % 100
    next_short = (year + 1) % 100
    year_name = f"{short:02d}/{next_short:02d}"

    lookup = AcademicYear.query.filter_by(id=year).first()
    if lookup:
        return lookup
    try:
        new_academic_year = AcademicYear(id=year,
                                         name=year_name)
        db.session.add(new_academic_year)
        db.session.commit()
        return new_academic_year
    except IntegrityError:
        db.session.rollback()
        return None


def _get_semester_name(semester_id: str):
    if re.fullmatch(r"\d+1", semester_id):
        return "ZS"
    if re.fullmatch(r"\d+2", semester_id):
        return "LS"
    return None


def get_or_create_semester(semester_id: str):
    lookup = Semester.query.filter_by(id=semester_id).first()
    if lookup:
        return lookup
    else:
        try:
            academic_year = get_or_create_academic_year(semester_id)
            name = _get_semester_name(semester_id)
            new_semester = Semester(
                id=semester_id,
                name=name,
                academic_year_id=academic_year.id,
            )
            db.session.add(new_semester)
            db.session.commit()
            return new_semester
        except IntegrityError:
            db.session.rollback()
            return None


from sqlalchemy.exc import IntegrityError


def get_or_create_subject(subject_name: str, subject_code: str):
    # Look up by code only (code should be unique)
    subj = Subject.query.filter_by(code=subject_code).first()
    if subj:
        # Optionally keep the local name in sync with Oracle
        if subj.name != subject_name and subject_name:
            subj.name = subject_name
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                # keep old name if update fails
        return subj

    # Not found → create
    try:
        subj = Subject(name=subject_name, code=subject_code)
        db.session.add(subj)
        db.session.flush()
        return subj
    except IntegrityError:
        db.session.rollback()
        return None


def get_or_create_student(oracle_student_model):
    lookup = Student.query.filter_by(id_studia=oracle_student_model.ID_STUDIA).first()
    if lookup:
        return lookup
    try:
        instrument = Instrument.query.filter_by(name=oracle_student_model.KATEDRA_NAZEV).first()
        if not instrument:
            return None  # instrument unknown; caller should log/skip

        new_student = Student(
            id_studia=oracle_student_model.ID_STUDIA,
            last_name=oracle_student_model.PRIJMENI,
            first_name=oracle_student_model.JMENO,
            instrument_id=instrument.id,
        )
        db.session.add(new_student)
        db.session.flush()
        return new_student
    except IntegrityError:
        db.session.rollback()
        return None


def get_or_create_player_from_student(student_model):
    player = Player.query.filter_by(student_id=student_model.id).first()
    if player:
        return player
    player = Player(
        first_name=student_model.first_name,
        last_name=student_model.last_name,
        student_id=student_model.id,
        instrument_id=student_model.instrument_id,
    )
    try:
        db.session.add(player)
        db.session.flush()
        return player
    except IntegrityError:
        db.session.rollback()
        return None


def student_subject_enrollment(student_id: int, subject_id: int, semester_id: str):
    sse = (StudentSubjectEnrollment.query
           .filter_by(student_id=student_id,
                      subject_id=subject_id,
                      semester_id=semester_id)
           .first())
    if sse:
        return sse

    sse = StudentSubjectEnrollment(
        student_id=student_id,
        subject_id=subject_id,
        semester_id=semester_id,
    )
    db.session.add(sse)
    db.session.flush()  # assigns PKs if any
    return sse

