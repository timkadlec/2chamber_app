import click
from flask.cli import with_appcontext
from models import db, KomorniHraStud, StudentSubjectEnrollment, KomorniHraUcitel
from utils.import_oracle import get_or_create_academic_year, get_or_create_semester, get_or_create_subject, \
    get_or_create_student, get_or_create_player_from_student, student_subject_enrollment, get_or_create_teacher
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

    click.echo("🔍 Fetching Oracle students...", err=True)
    oracle_students = db.session.query(KomorniHraStud).all()
    click.echo(f"Found {len(oracle_students)} rows in Oracle view.", err=True)

    # semester -> set(student_id) that should stay
    active_students_by_semester = {}

    for idx, ors in enumerate(oracle_students, start=1):
        click.echo(f"\n➡️ Processing row {idx}: {ors}", err=True)

        # student
        student = get_or_create_student(ors)
        db.session.flush()
        if not student:
            skipped += 1
            click.echo(f"⚠️ Skipped (no instrument or error) for row {idx}: {ors}", err=True)
            continue
        else:
            created_students += 1
            click.echo(f"✅ Student mapped/created: {student}", err=True)

        # track this student as active for this semester
        active_students_by_semester.setdefault(ors.SEMESTR_ID, set()).add(student.id)

        # player
        player = get_or_create_player_from_student(student)
        db.session.flush()
        if player:
            created_players += 1
            click.echo(f"🎻 Player created/mapped: {player}", err=True)
        else:
            click.echo(f"⚠️ No player created for student {student}", err=True)

        # semester + subject
        ay = get_or_create_academic_year(ors.SEMESTR_ID)
        sem = get_or_create_semester(ors.SEMESTR_ID)
        subj = get_or_create_subject(ors.PREDMET_NAZEV, ors.PREDMET_KOD)
        click.echo(f"📚 Semester {sem}, Subject {subj}", err=True)

        if not (ay and sem and subj):
            skipped += 1
            click.echo(f"⚠️ Skipped (semester/subject error) for student {student}", err=True)
            continue

        if student_subject_enrollment(student.id, subj.id, sem.id):
            created_enrollments += 1
            click.echo(f"📝 Enrollment created: student={student.id}, subject={subj.id}, semester={sem.id}", err=True)
        else:
            click.echo(f"ℹ️ Enrollment already exists for student={student.id}, subject={subj.id}, semester={sem.id}", err=True)

    # ⚡ Remove enrollments of students that disappeared from the view
    click.echo("\n🔄 Checking for stale enrollments to remove...", err=True)
    for sem_id, active_student_ids in active_students_by_semester.items():
        existing_enrollments = (
            db.session.query(StudentSubjectEnrollment)
            .filter(StudentSubjectEnrollment.semester_id == sem_id)
            .all()
        )
        for enr in existing_enrollments:
            if enr.student_id not in active_student_ids:
                click.echo(
                    f"❌ Removing stale enrollment: student {enr.student_id}, semester {sem_id}",
                    err=True,
                )
                db.session.delete(enr)

    try:
        db.session.commit()
        click.echo("💾 Commit successful.", err=True)
    except IntegrityError as e:
        db.session.rollback()
        click.echo(f"❌ Commit failed, rolled back. Error: {e}", err=True)
        raise SystemExit(1)

    click.echo(
        f"\n✅ Done. Created students: {created_students}, players: {created_players}, enrollments: {created_enrollments}, skipped: {skipped}",
        err=True
    )

@click.command("oracle-semesters")
@with_appcontext
def cli_oracle_semesters():
    """Show distinct semesters currently present in Oracle view."""
    semesters = (
        db.session.query(KomorniHraStud.SEMESTR_ID)
        .distinct()
        .order_by(KomorniHraStud.SEMESTR_ID)
        .all()
    )

    if not semesters:
        click.echo("⚠️ No semesters found in Oracle view.", err=True)
        return

    click.echo("📚 Semesters present in Oracle view:")
    for sem_id, in semesters:
        click.echo(f" - {sem_id}")

@click.command("oracle-teachers")
@with_appcontext
def cli_oracle_teachers():
    """Show distinct teachers currently present in Oracle view."""
    oracle_teachers = db.session.query(KomorniHraUcitel).all()
    for teacher in oracle_teachers:
        new_teacher = get_or_create_teacher(teacher)
    db.session.commit()