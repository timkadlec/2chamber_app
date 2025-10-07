from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from models import Semester, db, AcademicYear, StudentSubjectEnrollment, Subject, Instrument, Student, Player, Teacher, \
    Department
import re
import click


def get_or_create_department(department_name: str):
    lookup = Department.query.filter_by(name=department_name).first()
    if lookup:
        return lookup
    try:
        new_department = Department(name=department_name)
        db.session.add(new_department)
        db.session.commit()
        return new_department
    except IntegrityError:
        db.session.rollback()
        return None


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
    sem_id = int(semester_id)
    lookup = Semester.query.get(sem_id)
    if lookup:
        return lookup
    try:
        academic_year = get_or_create_academic_year(semester_id)
        name = _get_semester_name(semester_id)
        new_semester = Semester(
            id=sem_id,
            name=name,
            academic_year_id=academic_year.id if academic_year else None,
        )
        db.session.add(new_semester)
        db.session.commit()
        return new_semester
    except IntegrityError:
        db.session.rollback()
        return None


def get_or_create_subject(subject_name: str, subject_code: str):
    try:
        subj = Subject.query.filter_by(code=subject_code).first()
        if subj:
            if subj.name != subject_name and subject_name:
                old = subj.name
                subj.name = subject_name
                try:
                    db.session.commit()
                    click.echo(f"🔄 Updated subject name {old} -> {subject_name} (code={subject_code})", err=True)
                except IntegrityError as e:
                    db.session.rollback()
                    click.echo(f"⚠️ Failed to update subject {subject_code}: {e}", err=True)
            return subj

        subj = Subject(name=subject_name, code=subject_code)
        db.session.add(subj)
        db.session.flush()
        click.echo(f"✅ Created new subject {subject_name} ({subject_code})", err=True)
        return subj

    except IntegrityError as e:
        db.session.rollback()
        click.echo(f"❌ IntegrityError creating subject {subject_code}: {e}", err=True)
        return None


def find_instrument_by_name(name: str):
    if not name:
        return None

    # try exact matches (CZ or EN)
    instr = Instrument.query.filter(
        or_(
            Instrument.name.ilike(name.strip()),
            Instrument.name_en.ilike(name.strip())
        )
    ).first()
    if instr:
        return instr

    # fallback: basic normalization (e.g. singular/plural, capitalization)
    name_lower = name.lower().strip()
    return Instrument.query.filter(
        or_(
            Instrument.name.ilike(f"%{name_lower}%"),
            Instrument.name_en.ilike(f"%{name_lower}%")
        )
    ).first()


def get_or_create_student(oracle_student_model):
    lookup = Student.query.filter_by(id_studia=oracle_student_model.ID_STUDIA).first()
    if not lookup:
        lookup = Student.query.filter_by(osobni_cislo=str(oracle_student_model.CISLO_OSOBY)).first()

    instrument = find_instrument_by_name(oracle_student_model.KATEDRA_NAZEV)

    if not instrument:
        click.echo(
            f"⚠️ No instrument found for {oracle_student_model.JMENO} {oracle_student_model.PRIJMENI} "
            f"(osobni_cislo={oracle_student_model.CISLO_OSOBY}, id_studia={oracle_student_model.ID_STUDIA}, "
            f"katedra={oracle_student_model.KATEDRA_NAZEV})",
            err=True,
        )
        return None

    department = get_or_create_department(oracle_student_model.PROGRAM_NAZEV)
    if not department:
        click.echo(
            f"⚠️ No department found for {oracle_student_model.JMENO} {oracle_student_model.PRIJMENI} "
            f"(osobni_cislo={oracle_student_model.CISLO_OSOBY}, id_studia={oracle_student_model.ID_STUDIA}, "
            f"katedra={oracle_student_model.DEPARTMENT})",
            err=True,
        )
        return None

    if lookup:
        lookup.osobni_cislo = oracle_student_model.CISLO_OSOBY
        lookup.id_studia = oracle_student_model.ID_STUDIA
        lookup.last_name = oracle_student_model.PRIJMENI
        lookup.first_name = oracle_student_model.JMENO
        lookup.instrument_id = instrument.id
        lookup.email = oracle_student_model.EMAIL
        lookup.state = oracle_student_model.STUDUJE
        lookup.department_id = department.id
        if getattr(oracle_student_model, "STUDUJE", None) in ("P", "K"):
            lookup.active = False
        else:
            lookup.active = True

        return lookup

    try:
        new_student = Student(
            osobni_cislo=oracle_student_model.CISLO_OSOBY,
            id_studia=oracle_student_model.ID_STUDIA,
            last_name=oracle_student_model.PRIJMENI,
            first_name=oracle_student_model.JMENO,
            instrument_id=instrument.id,
            email=oracle_student_model.EMAIL,
            active=(getattr(oracle_student_model, "STUDUJE", None) not in ("P", "K")),
            state=oracle_student_model.STUDUJE,
            department_id=department.id,
        )
        db.session.add(new_student)
        db.session.flush()
        return new_student
    except IntegrityError as e:
        db.session.rollback()
        click.echo(
            f"❌ IntegrityError creating student (osobni_cislo={oracle_student_model.CISLO_OSOBY}, "
            f"id_studia={oracle_student_model.ID_STUDIA}): {e}",
            err=True,
        )
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


def student_semester_enrollment(student_id: int, semester_id: int):
    from models import StudentSemesterEnrollment
    sse = StudentSemesterEnrollment.query.filter_by(
        student_id=student_id, semester_id=semester_id
    ).first()
    if sse:
        return sse, False
    sse = StudentSemesterEnrollment(student_id=student_id, semester_id=semester_id)
    db.session.add(sse)
    db.session.flush()
    return sse, True


def status_allows_enrollment(status: str) -> bool:
    # S = studying, K = finished (keep), P = aborted (exclude)
    return status in ("S", "K")


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
    db.session.flush()
    return sse


def get_or_create_teacher(oracle_teacher_model):
    lookup = Teacher.query.filter_by(osobni_cislo=oracle_teacher_model.OSOBNI_CISLO).first()
    if lookup:
        return lookup
    try:
        new_teacher = Teacher(
            osobni_cislo=oracle_teacher_model.OSOBNI_CISLO,
            last_name=oracle_teacher_model.PRIJMENI,
            first_name=oracle_teacher_model.JMENO,
            full_name=oracle_teacher_model.JMENO_UCITELE,
        )
        db.session.add(new_teacher)
        db.session.flush()
        return new_teacher
    except IntegrityError:
        db.session.rollback()
        return None
