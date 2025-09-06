from flask import render_template, flash, redirect, url_for, session, request, jsonify
from .forms import EnsembleForm
from utils.nav import navlink
from models import db, Ensemble, EnsembleSemester, Player, Student, EnsemblePlayer, EnsembleInstrumentation, KomorniHraStud
from . import ensemble_bp
from sqlalchemy.orm import selectinload
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError


@ensemble_bp.route("/all")
@navlink("Soubory", weight=10)
def all_ensembles():
    current_semester = session["semester_id"]
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = Ensemble.query.filter(
        Ensemble.semester_links.any(EnsembleSemester.semester_id == current_semester)).order_by(Ensemble.name).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    ensembles = pagination.items
    return render_template("all_ensembles.html", ensembles=ensembles, pagination=pagination)


@ensemble_bp.route("/add", methods=["GET", "POST"])
def ensemble_add():
    form = EnsembleForm(mode="add")
    if form.validate_on_submit():
        new_ensemble = Ensemble(
            name=form.name.data,
        )
        db.session.add(new_ensemble)
        db.session.commit()
        ensemble_semester = EnsembleSemester(
            ensemble_id=new_ensemble.id,
            semester_id=session["semester_id"]
        )
        db.session.add(ensemble_semester)
        db.session.commit()
        flash("Byl úspěšně přidán soubor.", "success")
        return redirect(url_for("ensemble.all_ensembles"))
    return render_template("ensemble_form.html", form=form)


@ensemble_bp.route("/<int:ensemble_id>/edit", methods=["GET", "POST"])
def ensemble_edit(ensemble_id):
    form = EnsembleForm(mode="edit")
    ensemble = Ensemble.query.filter_by(id=ensemble_id).first_or_404()
    if request.method == "GET":
        form.name.data = ensemble.name
    if form.validate_on_submit():
        ensemble.name = form.name
        db.session.commit()
        flash("Soubor byl úspěšně přidán aktualizován.", "success")
        return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble.id, ))
    return render_template("ensemble_form.html", form=form, ensemble=ensemble, )


@ensemble_bp.route("/<int:ensemble_id>/detail", methods=["GET", "POST"])
def ensemble_detail(ensemble_id):
    ensemble = Ensemble.query.filter_by(id=ensemble_id).first_or_404()

    instrumentations = ensemble.instrumentation_entries
    player_links = ensemble.player_links

    assigned_player_ids_sq = (db.session.query(EnsemblePlayer.player_id)
                              .filter(EnsemblePlayer.ensemble_id == ensemble.id)
                              .subquery())

    available_students = (db.session.query(Student)
                          .outerjoin(Player, Player.student_id == Student.id)
                          .options(
        selectinload(Student.instrument),
        selectinload(Student.player)  # one-to-one
    )
                          .filter(Student.active.is_(True))
                          .filter(
        or_(Player.id.is_(None),
            ~Player.id.in_(select(assigned_player_ids_sq)))
    )
                          .order_by(Student.last_name, Student.first_name)
                          .all())

    return render_template(
        "ensemble_detail.html",
        ensemble=ensemble,
        instrumentations=instrumentations,
        player_links=player_links,
        available_students=available_students
    )


def _get_or_create_player_for_student(student):
    player = getattr(student, "player", None)
    if player:
        return player

    player = Player(
        first_name=student.first_name,
        last_name=student.last_name,
        email=student.email,
        phone=getattr(student, "phone_number", None),
        instrument_id=student.instrument_id,
        student=student,
    )
    db.session.add(player)
    db.session.flush()
    return player


def _get_or_create_ensemble_instrumentation_by_ids(ensemble_id: int, instrument_id: int, position: int | None = None):
    epi = (EnsembleInstrumentation.query
           .filter_by(ensemble_id=ensemble_id, instrument_id=instrument_id, position=position)
           .first())
    if epi:
        return epi, False
    epi = EnsembleInstrumentation(
        ensemble_id=ensemble_id,
        instrument_id=instrument_id,
        separate=False,
        concertmaster=False,
        comment=None,
    )
    db.session.add(epi)
    db.session.flush()  # get epi.id
    return epi, True


@ensemble_bp.route("/<int:ensemble_id>/players/add-student", methods=["POST"])
def add_student_to_ensemble(ensemble_id):
    data = request.get_json(silent=True) or request.form or {}
    student_id = data.get("student_id", type=int) if hasattr(data, "get") else data.get("student_id")
    epi_id = data.get("ensemble_instrumentation_id") or None

    if not student_id:
        return jsonify({"message": "student_id je povinné"}), 400

    ensemble = db.session.get(Ensemble, ensemble_id)
    if not ensemble:
        return jsonify({"message": "Ansámbl neexistuje"}), 404

    student = db.session.get(Student, student_id)
    if not student or not student.active:
        return jsonify({"message": "Student neexistuje nebo není aktivní"}), 404

    if epi_id:
        epi = db.session.get(EnsembleInstrumentation, int(epi_id))
        if not epi or epi.ensemble_id != ensemble.id:
            return jsonify({"message": "Neplatný part"}), 400
    else:
        player = getattr(student, "player", None)
        instrument_id = (player.instrument_id if player and player.instrument_id
                         else student.instrument_id)
        if not instrument_id:
            return jsonify({"message": "Student/hráč nemá přiřazený nástroj; není možné vytvořit part."}), 400

        epi, _created = _get_or_create_ensemble_instrumentation_by_ids(
            ensemble_id=ensemble.id,
            instrument_id=instrument_id,
        )
        epi_id = epi.id

    # Ensure a Player exists for this Student (after we maybe used it above)
    player = _get_or_create_player_for_student(student)

    ep = EnsemblePlayer(
        ensemble_id=ensemble.id,
        player_id=player.id,
        ensemble_instrumentation_id=epi_id
    )
    db.session.add(ep)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Hráč už je v ansámblu / na daném partu."}), 409

    return jsonify(
        {"ok": True, "player_id": player.id, "ensemble_player_id": ep.id, "ensemble_instrumentation_id": epi_id})


@ensemble_bp.route("/<int:ensemble_id>/delete", methods=["POST"])
def ensemble_delete(ensemble_id):
    ensemble_to_delete = Ensemble.query.get_or_404(ensemble_id)
    db.session.delete(ensemble_to_delete)
    db.session.commit()
    flash("Soubor byl úspěšně smazán.", "success")
    return redirect(url_for("ensemble.all_ensembles"))
