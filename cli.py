import click
from flask.cli import with_appcontext
from models import db, KomorniHraStud, StudentSubjectEnrollment, KomorniHraUcitel, Subject, Student
from utils.import_oracle import (get_or_create_academic_year, get_or_create_semester, get_or_create_subject, \
                                 get_or_create_student, get_or_create_player_from_student, student_subject_enrollment,
                                 get_or_create_teacher,
                                 status_allows_enrollment, student_semester_enrollment)
from sqlalchemy.exc import IntegrityError, DBAPIError
from collections import defaultdict


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
@click.option("--dry-run", is_flag=True, help="Simulate the import without committing any DB changes.")
@with_appcontext
def cli_oracle_students_update(dry_run):
    """
    Sync students & enrollments from Oracle view, enrolling only statuses S/K,
    skipping P, and cleaning up stale enrollments per (semester, subject).
    """
    created_students = 0
    created_players = 0
    created_sse = 0  # StudentSemesterEnrollment (per-semester)
    created_sse_subject = 0  # StudentSubjectEnrollment (per-subject)
    skipped_no_instrument = 0
    skipped_status_p = 0
    row_errors = 0

    click.echo("🔍 Fetching Oracle students...", err=True)
    oracle_rows = db.session.query(KomorniHraStud).all()
    click.echo(f"Found {len(oracle_rows)} rows in Oracle view.", err=True)

    # (sem_id, subj_id) -> set(student_id) that MUST remain enrolled
    active_by_sem_subj: dict[tuple[int, int], set[int]] = defaultdict(set)

    # De-dup rows (some views return duplicates)
    seen = set()  # key = (ID_STUDIA, SEMESTR_ID, PREDMET_KOD)

    for idx, ors in enumerate(oracle_rows, start=1):
        key = (ors.ID_STUDIA, ors.SEMESTR_ID, ors.PREDMET_KOD)
        if key in seen:
            click.echo(f"↩️  [{idx}] Duplicate row skipped: {ors}", err=True)
            continue
        seen.add(key)

        try:
            status = (ors.STUDUJE or "").strip().upper()
            click.echo(f"\n➡️ [{idx}] {ors} | status={status}", err=True)

            # 1) Ensure Semester + Subject exist (log exact failures)
            sem = get_or_create_semester(ors.SEMESTR_ID)
            subj = get_or_create_subject(ors.PREDMET_NAZEV, ors.PREDMET_KOD)
            if not sem or not subj:
                click.echo(f"⚠️ [{idx}] Skipped: semester/subject missing (sem={sem}, subj={subj})", err=True)
                row_errors += 1
                continue

            # 2) Create/update Student (also sets active based on status)
            student = get_or_create_student(ors)
            db.session.flush()
            if not student:
                skipped_no_instrument += 1
                click.echo(f"⚠️ [{idx}] Skipped: student unresolved (likely instrument mapping).", err=True)
                continue

            created_students += 1
            click.echo(f"✅ [{idx}] Student mapped: id={student.id} name={student.full_name}", err=True)

            # 3) Ensure Player
            player = get_or_create_player_from_student(student)
            db.session.flush()
            if player:
                created_players += 1
                click.echo(f"🎻 [{idx}] Player mapped: id={player.id}", err=True)
            else:
                click.echo(f"ℹ️ [{idx}] Player not created (already exists or error).", err=True)

            # 4) Track active enrollment intent only for S/K (not P)
            if status_allows_enrollment(status):
                active_by_sem_subj[(sem.id, subj.id)].add(student.id)
            else:
                skipped_status_p += 1
                click.echo(f"🚫 [{idx}] Status=P (aborted) — will not enroll; may be removed in cleanup.", err=True)

            # 5) Ensure StudentSemesterEnrollment (optional but useful)
            sse, sse_created = student_semester_enrollment(student.id, sem.id)
            if sse_created:
                created_sse += 1
                click.echo(f"🗓️  [{idx}] SemesterEnrollment created (student={student.id}, sem={sem.id})", err=True)

            # 6) Ensure StudentSubjectEnrollment only for S/K
            if status_allows_enrollment(status):
                existing = StudentSubjectEnrollment.query.filter_by(
                    student_id=student.id, subject_id=subj.id, semester_id=sem.id
                ).first()
                if not existing:
                    new_enr = StudentSubjectEnrollment(
                        student_id=student.id,
                        subject_id=subj.id,
                        semester_id=sem.id,
                        erasmus=False,  # adjust if you propagate this
                    )
                    db.session.add(new_enr)
                    db.session.flush()
                    created_sse_subject += 1
                    click.echo(f"📝 [{idx}] SubjectEnrollment created "
                               f"(student={student.id}, subject={subj.id}, sem={sem.id})", err=True)
                else:
                    click.echo(f"✔️  [{idx}] SubjectEnrollment already exists "
                               f"(student={student.id}, subject={subj.id}, sem={sem.id})", err=True)
            else:
                click.echo(f"⏭️ [{idx}] SubjectEnrollment skipped due to status={status}", err=True)

        except IntegrityError as e:
            db.session.rollback()
            row_errors += 1
            click.echo(f"❌ [{idx}] IntegrityError; rolled back: {e}", err=True)
        except Exception as e:
            db.session.rollback()
            row_errors += 1
            click.echo(f"💥 [{idx}] Unexpected error; rolled back: {e}", err=True)

    # 7) Cleanup: remove stale enrollments ONLY for (semester, subject) pairs reported by Oracle
    removal_stats = defaultdict(lambda: {"kept": 0, "removed": 0, "removed_students": []})
    click.echo("\n🔄 Cleanup: removing stale enrollments per (semester, subject)…", err=True)

    for (sem_id, subj_id), active_student_ids in active_by_sem_subj.items():
        existing = (
            db.session.query(StudentSubjectEnrollment)
            .filter(
                StudentSubjectEnrollment.semester_id == sem_id,
                StudentSubjectEnrollment.subject_id == subj_id,
            )
            .all()
        )
        for enr in existing:
            if enr.student_id in active_student_ids:
                removal_stats[(sem_id, subj_id)]["kept"] += 1
            else:
                removal_stats[(sem_id, subj_id)]["removed"] += 1
                removal_stats[(sem_id, subj_id)]["removed_students"].append(enr.student_id)
                if not dry_run:
                    db.session.delete(enr)
                click.echo(
                    f"{'❌' if not dry_run else '🟡 DRY-RUN'} "
                    f"Removed enrollment: student={enr.student_id}, "
                    f"subject={subj_id}, semester={sem_id}",
                    err=True,
                )

    # 8) Commit (or rollback in dry-run)
    if dry_run:
        db.session.rollback()
        click.echo("\n🟡 Dry-run mode: no changes committed.", err=True)
    else:
        try:
            db.session.commit()
            click.echo("💾 Commit successful.", err=True)
        except IntegrityError as e:
            db.session.rollback()
            click.echo(f"❌ Commit failed, rolled back. Error: {e}", err=True)
            raise SystemExit(1)

    # 9) Summaries
    removed_enrollments = sum(d["removed"] for d in removal_stats.values())
    subj_name_cache: dict[int, str] = {}

    def subj_label(sid: int) -> str:
        if sid not in subj_name_cache:
            s = Subject.query.get(sid)
            subj_name_cache[sid] = f"{s.name} ({s.code})" if s else f"Subject {sid}"
        return subj_name_cache[sid]

    click.echo("\n📊 Enrollment cleanup summary:", err=True)
    if removal_stats:
        for (sem_id, subj_id), stats in sorted(removal_stats.items()):
            label = subj_label(subj_id)
            click.echo(
                f"\n   Semester={sem_id}, Subject={subj_id} {label}: "
                f"kept={stats['kept']}, removed={stats['removed']}",
                err=True,
            )
            if stats["removed_students"]:
                click.echo("      Removed students:", err=True)
                for sid in stats["removed_students"]:
                    st = Student.query.get(sid)
                    name = st.full_name if st else f"ID {sid}"
                    click.echo(f"         - {name} (id={sid})", err=True)
    else:
        click.echo("   (no (semester,subject) pairs were processed from Oracle)", err=True)

    click.echo(
        "\n✅ Done.\n"
        f"   Students mapped/created: {created_students}\n"
        f"   Players mapped/created:  {created_players}\n"
        f"   Semester enrollments:    +{created_sse}\n"
        f"   Subject enrollments:     +{created_sse_subject}\n"
        f"   Removed enrollments:     -{removed_enrollments}\n"
        f"   Skipped (no instrument): {skipped_no_instrument}\n"
        f"   Skipped (status P):      {skipped_status_p}\n"
        f"   Row errors:              {row_errors}",
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
