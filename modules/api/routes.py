from . import api_bp
from flask import jsonify, session, abort, redirect, request
from models import db
from models.core import Semester
from models.ensembles import Ensemble, EnsembleSemester, EnsemblePlayer, EnsembleTeacher, EnsembleInstrumentation
from models.students import StudentSubjectEnrollment
from models.players import Player
from models.core import Instrument
from sqlalchemy.orm import joinedload
from utils.decorators import permission_required

def _get_current_semester_or_400():
    current_semester_id = session.get("semester_id")
    if not current_semester_id:
        abort(400, description="No semester_id in session")
    return Semester.query.get_or_404(current_semester_id)


def _get_upcoming_semester(current_semester: Semester):
    return (
        Semester.query
        .filter(Semester.start_date > current_semester.end_date)
        .order_by(Semester.start_date.asc())
        .first()
    )

def _get_previous_semester(current_semester: Semester):
    return (
        Semester.query
        .filter(Semester.end_date < current_semester.start_date)
        .order_by(Semester.end_date.desc())
        .first()
    )


@api_bp.route('/ensemble/<int:ensemble_id>/get-semester-move-info', methods=['GET'])
def get_ensemble_semester_move_info(ensemble_id):
    ensemble = Ensemble.query.get_or_404(ensemble_id)

    current_semester = _get_current_semester_or_400()
    upcoming_semester = _get_upcoming_semester(current_semester)

    if not upcoming_semester:
        return jsonify({
            "ensemble_id": ensemble.id,
            "current_semester": {"id": current_semester.id, "name": current_semester.name},
            "upcoming_semester": None,
            "players": [],
            "message": "No upcoming semester found."
        }), 200

    is_in_current_semester = (
        db.session.query(EnsembleSemester.id)
        .filter(
            EnsembleSemester.ensemble_id == ensemble.id,
            EnsembleSemester.semester_id == current_semester.id
        )
        .first()
        is not None
    )

    players = []
    if is_in_current_semester:
        players = (
            db.session.query(Player)
            .options(
                joinedload(Player.instrument).joinedload(Instrument.instrument_section),
                joinedload(Player.instrument).joinedload(Instrument.instrument_group),
            )
            .join(EnsemblePlayer, EnsemblePlayer.player_id == Player.id)
            .filter(
                EnsemblePlayer.ensemble_id == ensemble.id,
                EnsemblePlayer.semester_id == current_semester.id,
            )
            .order_by(Player.last_name.asc(), Player.first_name.asc())
            .all()
        )

    # Bulk-check "has any subject enrollment in upcoming semester"
    student_ids = [p.student_id for p in players if p.student_id]
    active_student_ids = set()
    if student_ids:
        active_student_ids = set(
            r[0] for r in (
                db.session.query(StudentSubjectEnrollment.student_id)
                .filter(
                    StudentSubjectEnrollment.semester_id == upcoming_semester.id,
                    StudentSubjectEnrollment.student_id.in_(student_ids)
                )
                .distinct()
                .all()
            )
        )

    payload_players = []
    for p in players:
        instr = p.instrument
        payload_players.append({
            "player_id": p.id,
            "full_name": p.full_name,
            "is_guest": p.is_guest,
            "student_id": p.student_id,

            "instrument": None if not instr else {
                "id": instr.id,
                "name": instr.name,
                "name_en": instr.name_en,
                "abbr": instr.abbreviation,
                "normalized_abbr": instr.normalized_abbr,
                "section": None if not instr.instrument_section else {
                    "id": instr.instrument_section.id,
                    "name": instr.instrument_section.name,
                },
                "group": None if not instr.instrument_group else {
                    "id": instr.instrument_group.id,
                    "name": instr.instrument_group.name,
                },
            },

            "has_active_subject_in_upcoming_semester": bool(
                p.student_id and p.student_id in active_student_ids
            ),
        })

    return jsonify({
        "ensemble_id": ensemble.id,
        "current_semester": {"id": current_semester.id, "name": current_semester.name},
        "upcoming_semester": {"id": upcoming_semester.id, "name": upcoming_semester.name},
        "ensemble_is_in_current_semester": is_in_current_semester,
        "players": payload_players
    }), 200


@api_bp.route('/ensemble/<int:ensemble_id>/deactivate', methods=['POST'])
@permission_required("ens_deactivate")
def deactivate_ensemble(ensemble_id):
    ensemble = Ensemble.query.get_or_404(ensemble_id)

    try:
        ensemble.active = False
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 400

    return jsonify({"success": True}), 200


from models.teachers import Teacher  # adjust import to your project

@api_bp.route('/ensemble/<int:ensemble_id>/teachers/semester/<int:semester_id>', methods=['GET'])
def get_ensemble_teachers_for_semester(ensemble_id, semester_id):
    ensemble = Ensemble.query.get_or_404(ensemble_id)

    rows = (
        db.session.query(EnsembleTeacher)
        .join(Teacher, Teacher.id == EnsembleTeacher.teacher_id)
        .filter(
            EnsembleTeacher.ensemble_id == ensemble.id,
            EnsembleTeacher.semester_id == semester_id,
        )
        .order_by(Teacher.last_name.asc(), Teacher.first_name.asc())
        .all()
    )


    payload = []
    for link in rows:
        t = link.teacher
        payload.append({
            "assignment_id": link.id,
            "teacher_id": t.id if t else None,
            "full_name": t.full_name if t else "—",
            "hour_donation": link.hour_donation,
        })

        print(payload)

    return jsonify({
        "ensemble_id": ensemble.id,
        "semester_id": semester_id,
        "teachers": payload,
    }), 200


def _get_assignments_for_semester(ensemble_id: int, semester_id: int):
    """Return EnsemblePlayer rows for a semester keyed by instrumentation id."""
    rows = (
        db.session.query(EnsemblePlayer)
        .options(
            joinedload(EnsemblePlayer.player).joinedload(Player.instrument),
            joinedload(EnsemblePlayer.ensemble_instrumentation).joinedload(EnsembleInstrumentation.instrument),
        )
        .filter(
            EnsemblePlayer.ensemble_id == ensemble_id,
            EnsemblePlayer.semester_id == semester_id,
        )
        .all()
    )
    return {r.ensemble_instrumentation_id: r for r in rows if r.ensemble_instrumentation_id}


@api_bp.route('/ensemble/<int:ensemble_id>/move-to-upcoming-semester', methods=['POST'])
@permission_required("ens_move_ensemble_upcoming_s")
def move_ensemble_to_upcoming_semester(ensemble_id):
    ensemble = Ensemble.query.get_or_404(ensemble_id)

    current_semester = _get_current_semester_or_400()
    upcoming_semester = _get_upcoming_semester(current_semester)
    if not upcoming_semester:
        return jsonify({"success": False, "message": "No upcoming semester found."}), 400

    data = request.get_json(silent=True) or {}
    copy_teachers = bool(data.get("copy_teachers", True))
    carry_students = bool(data.get("carry_students", True))
    carry_guests = bool(data.get("carry_guests", False))

    # must be in current
    is_in_current = db.session.query(EnsembleSemester.id).filter(
        EnsembleSemester.ensemble_id == ensemble.id,
        EnsembleSemester.semester_id == current_semester.id
    ).first() is not None
    if not is_in_current:
        return jsonify({"success": False, "message": "Ensemble is not linked to the current semester."}), 400

    created_link = False
    exists_in_upcoming = db.session.query(EnsembleSemester.id).filter(
        EnsembleSemester.ensemble_id == ensemble.id,
        EnsembleSemester.semester_id == upcoming_semester.id
    ).first() is not None

    if not exists_in_upcoming:
        db.session.add(EnsembleSemester(ensemble_id=ensemble.id, semester_id=upcoming_semester.id))
        created_link = True

    # --- TEACHERS ---
    copied_teachers = 0
    if copy_teachers:
        upcoming_has_teachers = db.session.query(EnsembleTeacher.id).filter(
            EnsembleTeacher.ensemble_id == ensemble.id,
            EnsembleTeacher.semester_id == upcoming_semester.id
        ).first() is not None

        if not upcoming_has_teachers:
            current_teachers = db.session.query(EnsembleTeacher).filter(
                EnsembleTeacher.ensemble_id == ensemble.id,
                EnsembleTeacher.semester_id == current_semester.id
            ).all()

            for tlink in current_teachers:
                db.session.add(EnsembleTeacher(
                    ensemble_id=ensemble.id,
                    semester_id=upcoming_semester.id,
                    teacher_id=tlink.teacher_id,
                    hour_donation=tlink.hour_donation,
                ))
                copied_teachers += 1

    # --- PLAYERS / SLOTS ---
    # Ensure upcoming semester has one EnsemblePlayer row per instrumentation slot.
    instrumentations = (
        db.session.query(EnsembleInstrumentation)
        .filter(EnsembleInstrumentation.ensemble_id == ensemble.id)
        .all()
    )

    current_by_slot = _get_assignments_for_semester(ensemble.id, current_semester.id)

    existing_upcoming_slot_ids = set(
        r[0] for r in db.session.query(EnsemblePlayer.ensemble_instrumentation_id).filter(
            EnsemblePlayer.ensemble_id == ensemble.id,
            EnsemblePlayer.semester_id == upcoming_semester.id,
            EnsemblePlayer.ensemble_instrumentation_id.isnot(None)
        ).all()
    )

    # precompute which students are active in upcoming semester (subject enrollment)
    student_ids = []
    for ep in current_by_slot.values():
        if ep.player and ep.player.student_id:
            student_ids.append(ep.player.student_id)

    active_student_ids = set()
    if student_ids:
        active_student_ids = set(
            sid for (sid,) in db.session.query(StudentSubjectEnrollment.student_id).filter(
                StudentSubjectEnrollment.semester_id == upcoming_semester.id,
                StudentSubjectEnrollment.student_id.in_(student_ids)
            ).distinct().all()
        )

    created_slot_rows = 0
    carried_players = 0

    for instr in instrumentations:
        if instr.id in existing_upcoming_slot_ids:
            continue  # already prepared

        source_ep = current_by_slot.get(instr.id)
        carry_player_id = None

        if source_ep and source_ep.player_id:
            p = source_ep.player

            if p and p.student_id:
                if carry_students and (p.student_id in active_student_ids):
                    carry_player_id = p.id
            else:
                # guest
                if carry_guests:
                    carry_player_id = source_ep.player_id

        db.session.add(EnsemblePlayer(
            ensemble_id=ensemble.id,
            semester_id=upcoming_semester.id,
            ensemble_instrumentation_id=instr.id,
            player_id=carry_player_id
        ))
        created_slot_rows += 1
        if carry_player_id:
            carried_players += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400

    return jsonify({
        "success": True,
        "ensemble_id": ensemble.id,
        "current_semester": {"id": current_semester.id, "name": current_semester.name},
        "upcoming_semester": {"id": upcoming_semester.id, "name": upcoming_semester.name},
        "created_link": created_link,
        "copied_teachers": copied_teachers,
        "created_slot_rows": created_slot_rows,
        "carried_players": carried_players,
        "message": "Ensemble prepared for upcoming semester.",
    }), 200
