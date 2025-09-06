import click
from flask.cli import with_appcontext
from models import db, KomorniHraStud
from utils.import_oracle import get_or_create_academic_year, get_or_create_semester, get_or_create_subject, \
    get_or_create_student, get_or_create_player_from_student, student_subject_enrollment
from sqlalchemy.exc import IntegrityError, DBAPIError


@click.command("format-academic-year")
@click.argument("code")
@with_appcontext
def cli_format_academic_year(code: str):
    """Format semester code YYYYSS into academic year YY/YY."""
    year = int(code[:4])
    short = year % 100
    next_short = (year + 1) % 100
    click.echo(f"{short:02d}/{next_short:02d}")


@click.command("get-or-create-academic-year")
@click.argument("semester_id")
@with_appcontext
def cli_get_or_create_academic_year(semester_id: str):
    ay = get_or_create_academic_year(semester_id)  # returns only the object
    click.echo(f"Academic Year: {getattr(ay, 'name', ay)} was created or already exists.")


@click.command("get-or-create-semester")
@click.argument("semester_id")
@with_appcontext
def cli_get_or_create_semester(semester_id: str):
    s = get_or_create_semester(semester_id)  # returns only the object
    click.echo(f"Academic Year: {getattr(s, 'name', s)} was created or already exists.")


@click.command("get-or-create-subject")
@click.argument("subject_name")
@click.argument("subject_code")
@with_appcontext
def cli_get_or_create_subject(subject_name: str, subject_code: str):
    s = get_or_create_subject(subject_name, subject_code)
    click.echo(f"Subject: {s.name} (code: {s.code}) was created or already exists.")


@click.command("oracle-ping")
@with_appcontext
def cli_oracle_ping():
    """Check Oracle connection by fetching one record."""
    try:
        exists = db.session.query(KomorniHraStud).first()
        click.echo("Oracle OK" if exists else "Oracle connected but no rows")
    except Exception as e:
        click.echo(f"Oracle NOT OK: {e}", err=True)
        raise SystemExit(1)


@click.command("oracle-student-update")
@with_appcontext
def cli_oracle_students_update():
    created_students = created_players = created_enrollments = 0
    skipped = 0

    oracle_students = db.session.query(KomorniHraStud).all()

    for ors in oracle_students:
        # student
        student = get_or_create_student(ors)
        db.session.commit()
        if not student:
            skipped += 1
            click.echo(f"Skipped (no instrument or error): {ors}", err=True)

        # player
        get_or_create_player_from_student(student)
        db.session.commit()
        if get_or_create_player_from_student(student):
            created_players += 1

        # semester + subject
        ay = get_or_create_academic_year(ors.SEMESTR_ID)
        sem = get_or_create_semester(ors.SEMESTR_ID)
        subj = get_or_create_subject(ors.PREDMET_NAZEV, ors.PREDMET_KOD)
        click.echo(f"Subject: {subj}", err=True)
        if not (ay and sem and subj):
            skipped += 1
            click.echo(f"Skipped (semester/subject error): {sem}", err=True)
            continue
        if student_subject_enrollment(student.id, subj.id, sem.id):
            created_enrollments += 1
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        click.echo("Commit failed; rolled back.", err=True)
        raise SystemExit(1)

    click.echo(
        f"Done. Created players: {created_players}, enrollments: {created_enrollments}, skipped: {skipped}"
    )
