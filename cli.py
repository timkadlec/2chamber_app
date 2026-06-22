import click
import re
import os
import uuid
import random
from flask.cli import with_appcontext
from models import db, KomorniHraStud, StudentSubjectEnrollment, KomorniHraUcitel, Subject, Student
from utils.import_oracle import (get_or_create_academic_year, get_or_create_semester, get_or_create_subject, \
                                 get_or_create_student, get_or_create_player_from_student, student_subject_enrollment,
                                 get_or_create_teacher,
                                 status_allows_enrollment, student_semester_enrollment)
from sqlalchemy.exc import IntegrityError, DBAPIError
from collections import defaultdict
from flask import current_app

def require_oracle_enabled():
    """Abort CLI command if Oracle is disabled/unavailable."""
    if not current_app.config.get("ORACLE_ENABLED", False):
        click.echo(
            "Oracle is disabled (missing Instant Client / ORACLE_DRIVER / init failed). "
            "Run without Oracle or configure Instant Client.",
            err=True,
        )
        raise SystemExit(2)



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
    require_oracle_enabled()
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
    require_oracle_enabled()
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
    require_oracle_enabled()
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


@click.command("sync-permissions")
@click.option("--dry-run", is_flag=True, help="Report only; do not write to the database.")
@with_appcontext
def cli_sync_permissions(dry_run):
    """
    Scan the project source for every permission code referenced via
    @permission_required(...) or has_permission(...) and ensure each one
    exists in the permissions table.  Orphaned DB entries (codes that no
    longer appear in the source) are reported but never deleted automatically.
    """
    from models import Permission

    # Regex matches both single- and double-quoted codes in either call form
    pattern = re.compile(r"""(?:permission_required|has_permission)\(\s*['"]([^'"]+)['"]\s*""")

    project_root = os.path.dirname(os.path.abspath(__file__))
    scan_dirs = [
        os.path.join(project_root, "modules"),
        os.path.join(project_root, "utils"),
        os.path.join(project_root, "templates"),
    ]

    found_codes: set[str] = set()
    for scan_dir in scan_dirs:
        for dirpath, _, filenames in os.walk(scan_dir):
            if "__pycache__" in dirpath:
                continue
            for filename in filenames:
                if not filename.endswith((".py", ".html")):
                    continue
                filepath = os.path.join(dirpath, filename)
                with open(filepath, encoding="utf-8", errors="ignore") as fh:
                    for code in pattern.findall(fh.read()):
                        found_codes.add(code)

    click.echo(f"🔍 Found {len(found_codes)} permission code(s) in source.")

    existing = {p.code: p for p in Permission.query.all()}
    existing_codes = set(existing.keys())

    missing = sorted(found_codes - existing_codes)
    orphaned = sorted(existing_codes - found_codes)

    if missing:
        click.echo(f"\n➕ Missing from DB ({len(missing)}) — will {'skip (dry-run)' if dry_run else 'create'}:")
        for code in missing:
            click.echo(f"   {code}")
            if not dry_run:
                db.session.add(Permission(code=code))
        if not dry_run:
            db.session.commit()
            click.echo("   ✅ Created.")
    else:
        click.echo("✅ All source permissions already exist in DB.")

    if orphaned:
        click.echo(f"\n⚠️  In DB but not found in source ({len(orphaned)}) — review manually:")
        for code in orphaned:
            p = existing[code]
            click.echo(f"   {code}  (id={p.id}, name={p.name or '—'})")
    else:
        click.echo("✅ No orphaned permissions in DB.")

    if dry_run:
        click.echo("\n(dry-run — no changes written)")


@click.command("oracle-teachers")
@with_appcontext
def cli_oracle_teachers():
    """Show distinct teachers currently present in Oracle view."""
    require_oracle_enabled()
    oracle_teachers = db.session.query(KomorniHraUcitel).all()
    for teacher in oracle_teachers:
        new_teacher = get_or_create_teacher(teacher)
    db.session.commit()


@click.command("seed-portal-roles")
@with_appcontext
def cli_seed_portal_roles():
    """Ensure 'student' and 'teacher' roles exist in the database."""
    from models.auth import Role

    created = []
    for name, description in [
        ("student", "Přístup pouze do studentského portálu"),
        ("teacher", "Přístup pouze do pedagogického portálu"),
    ]:
        if not Role.query.filter_by(name=name).first():
            db.session.add(Role(name=name, description=description))
            created.append(name)

    if created:
        db.session.commit()
        click.echo(f"✅ Created role(s): {', '.join(created)}")
    else:
        click.echo("✅ Roles 'student' and 'teacher' already exist.")


@click.command("seed-test-students")
@click.option("--count", default=5, show_default=True, help="Number of student accounts to create.")
@click.option("--reset", is_flag=True, help="Delete previously seeded test accounts first.")
@with_appcontext
def cli_seed_test_students(count, reset):
    """
    Create dev-only User accounts for random active students (one per instrument).
    Accounts use the 'viewer' role and are linked via student_id.
    Only works when DEV_LOGIN is enabled.
    """
    from models.auth import User, Role
    from flask import current_app

    if not current_app.config.get("DEV_LOGIN"):
        click.echo("❌  DEV_LOGIN is not enabled — refusing to seed test accounts.", err=True)
        raise SystemExit(1)

    TEST_OID_PREFIX = "dev-test-student-"

    if reset:
        deleted = User.query.filter(User.oid.like(f"{TEST_OID_PREFIX}%")).delete(synchronize_session=False)
        db.session.commit()
        click.echo(f"🗑️  Deleted {deleted} existing test account(s).")

    student_role = Role.query.filter_by(name="student").first()
    if not student_role:
        click.echo("❌  Role 'student' not found — run `flask seed-portal-roles` first.", err=True)
        raise SystemExit(1)

    # Active students that don't already have a linked User
    linked_student_ids = db.session.query(User.student_id).filter(User.student_id.isnot(None))
    candidates = (
        Student.query
        .filter(Student.active.is_(True))
        .filter(Student.id.notin_(linked_student_ids))
        .all()
    )

    if not candidates:
        click.echo("⚠️  No unlinked active students found.", err=True)
        raise SystemExit(0)

    # Pick one student per instrument (shuffle for randomness), up to `count`
    by_instrument: dict = {}
    random.shuffle(candidates)
    for s in candidates:
        key = s.instrument_id or 0
        if key not in by_instrument:
            by_instrument[key] = s
        if len(by_instrument) >= count:
            break

    selected = list(by_instrument.values())

    created = []
    for student in selected:
        oid = f"{TEST_OID_PREFIX}{student.id}"
        email = student.email or f"test.student.{student.id}@dev.local"

        # Skip if a user with this oid or email already exists
        if User.query.filter((User.oid == oid) | (User.email == email)).first():
            click.echo(f"⏭️  Skipping {student.full_name} — account already exists.")
            continue

        user = User(
            oid=oid,
            tid="dev-tenant",
            display_name=student.full_name,
            email=email,
            upn=email,
            provider="dev",
            student_id=student.id,
            role_id=student_role.id,
        )
        db.session.add(user)
        created.append((student, email))

    db.session.commit()

    click.echo(f"\n✅ Created {len(created)} test student account(s):\n")
    for student, email in created:
        instr = student.instrument.name if student.instrument else "—"
        click.echo(f"   {student.full_name:<30}  instrument: {instr:<20}  email: {email}")

    click.echo("\nLog in via /auth/dev-login and pick the account you want to test.")
