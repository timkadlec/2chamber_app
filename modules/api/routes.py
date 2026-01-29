from . import api_bp
from flask import jsonify, session, abort
from models import db
from models.core import Semester
from models.ensembles import Ensemble, EnsembleSemester, EnsemblePlayer
from models.students import StudentSubjectEnrollment
from models.players import Player
from models.core import Instrument
from sqlalchemy.orm import joinedload

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
            .filter(EnsemblePlayer.ensemble_id == ensemble.id)
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


@api_bp.route('/ensemble/<int:ensemble_id>/move-to-upcoming-semester', methods=['POST'])
def move_ensemble_to_upcoming_semester(ensemble_id):
    ensemble = Ensemble.query.get_or_404(ensemble_id)

    current_semester = _get_current_semester_or_400()
    upcoming_semester = _get_upcoming_semester(current_semester)

    if not upcoming_semester:
        return jsonify({
            "success": False,
            "message": "No upcoming semester found.",
        }), 400

    # Optional but sensible: ensure ensemble is in current semester
    is_in_current = (
        db.session.query(EnsembleSemester.id)
        .filter(
            EnsembleSemester.ensemble_id == ensemble.id,
            EnsembleSemester.semester_id == current_semester.id
        )
        .first()
        is not None
    )
    if not is_in_current:
        return jsonify({
            "success": False,
            "message": "Ensemble is not linked to the current semester.",
        }), 400

    exists_in_upcoming = (
        db.session.query(EnsembleSemester.id)
        .filter(
            EnsembleSemester.ensemble_id == ensemble.id,
            EnsembleSemester.semester_id == upcoming_semester.id
        )
        .first()
        is not None
    )

    if not exists_in_upcoming:
        link = EnsembleSemester(
            ensemble_id=ensemble.id,
            semester_id=upcoming_semester.id
        )
        db.session.add(link)
        db.session.commit()

    return jsonify({
        "success": True,
        "ensemble_id": ensemble.id,
        "current_semester": {"id": current_semester.id, "name": current_semester.name},
        "upcoming_semester": {"id": upcoming_semester.id, "name": upcoming_semester.name},
        "created_link": (not exists_in_upcoming),
        "message": "Ensemble moved to upcoming semester." if not exists_in_upcoming else "Ensemble already linked to upcoming semester."
    }), 200

@api_bp.route('/ensemble/<int:ensemble_id>/deactivate', methods=['POST'])
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
