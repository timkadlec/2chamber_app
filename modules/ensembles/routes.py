from flask import render_template, flash, redirect, url_for, session, request, jsonify
from .forms import EnsembleForm
from utils.nav import navlink
from models import db, Ensemble, EnsembleSemester, Player, Student, EnsemblePlayer, EnsembleInstrumentation, \
    KomorniHraStud, Instrument, StudentSubjectEnrollment, Semester
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
        ensemble.name = form.name.data
        db.session.commit()
        flash("Soubor byl úspěšně přidán aktualizován.", "success")
        return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble.id, ))
    return render_template("ensemble_form.html", form=form, ensemble=ensemble, )


@ensemble_bp.route("/<int:ensemble_id>/detail", methods=["GET", "POST"])
def ensemble_detail(ensemble_id):
    ensemble = Ensemble.query.filter_by(id=ensemble_id).first_or_404()

    instrumentations = ensemble.instrumentation_entries
    player_links = sorted(
        ensemble.player_links,
        key=lambda ep: (
            ep.ensemble_instrumentation.instrument.weight if ep.ensemble_instrumentation and ep.ensemble_instrumentation.instrument else 9999)
    )

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
    available_instruments = Instrument.query.filter_by(is_primary=True).order_by(Instrument.weight).all()

    return render_template(
        "ensemble_detail.html",
        ensemble=ensemble,
        instrumentations=instrumentations,
        player_links=player_links,
        available_students=available_students,
        available_instruments=available_instruments
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


@ensemble_bp.route("/<int:ensemble_id>/player/<int:ensemble_instrumentation_id>/add-student", methods=["GET", "POST"])
def add_student_to_ensemble(ensemble_id, ensemble_instrumentation_id):
    ensemble = Ensemble.query.get(ensemble_id)
    instrumentation = EnsembleInstrumentation.query.get(ensemble_instrumentation_id)
    current_semester = Semester.query.filter_by(id=session.get("semester_id")).first()
    if request.method == "GET":
        available_students = (
            db.session.query(Student)
            .filter(Student.active.is_(True))
            .filter(Student.instrument_id == instrumentation.instrument_id)
            .join(StudentSubjectEnrollment, StudentSubjectEnrollment.student_id == Student.id)
            .filter(StudentSubjectEnrollment.semester_id == current_semester.id)
            .options(
                selectinload(Student.instrument),
                selectinload(Student.player),
            )
            .order_by(Student.last_name, Student.first_name)
            .all()
        )
        print(available_students)
        return render_template("ensemble_add_student.html", ensemble=ensemble, instrumentation=instrumentation,
                               available_students=available_students)

    if request.method == "POST":
        selected_student_id = request.form.get("selected_student")
        student = Student.query.get(selected_student_id)

        if not student:
            flash("Student nebyl nalezen.", "danger")
            return redirect(url_for("ensemble.add_student_to_ensemble",
                                    ensemble_id=ensemble.id,
                                    ensemble_instrumentation_id=instrumentation.id))
        current_assignment = (
            db.session.query(EnsemblePlayer)
            .filter_by(
                ensemble_id=ensemble.id,
                ensemble_instrumentation_id=ensemble_instrumentation_id
            )
            .first()
        )

        if current_assignment:
            # update existing
            current_assignment.player_id = student.player.id
        else:
            # create new assignment
            current_assignment = EnsemblePlayer(
                ensemble_id=ensemble.id,
                ensemble_instrumentation_id=ensemble_instrumentation_id,
                player_id=student.player.id
            )
            db.session.add(current_assignment)

        db.session.commit()


        flash("Hráč byl úspěšně přidán", "success")
        return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble.id))


@ensemble_bp.route("/<int:ensemble_id>/players/add-empty", methods=["POST"])
def add_empty_player(ensemble_id):
    data = request.get_json(silent=True) or request.form or {}
    inst_id = data.get("instrument_id")

    # Validate ensemble
    ensemble = db.session.get(Ensemble, ensemble_id)
    if not ensemble:
        return jsonify({"message": "Ansámbl neexistuje"}), 404

    if not inst_id:
        return jsonify({"message": "Chybí instrument_id"}), 400

    # 1) Create new instrumentation seat for this ensemble/instrument
    new_epi = EnsembleInstrumentation(
        ensemble_id=ensemble.id,
        instrument_id=int(inst_id),
        position=len(ensemble.instrumentation_entries) + 1
    )
    db.session.add(new_epi)
    db.session.flush()  # get new_epi.id

    # 2) Create empty player linked to this new part
    empty_player = EnsemblePlayer(
        ensemble_id=ensemble.id,
        ensemble_instrumentation_id=new_epi.id,
        player_id=None
    )
    db.session.add(empty_player)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"message": f"Chyba při přidávání hráče: {e.orig}"}), 409

    flash("Prázdný hráč byl úspěšně přidán", "success")
    return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble.id))


@ensemble_bp.route("/<int:ensemble_id>/players/remove", methods=["POST"])
def delete_ensemble_player(ensemble_id):
    data = request.get_json(silent=True) or request.form or {}
    ep_id = data.get("ensemble_player_id")

    # Validate ensemble
    ensemble = db.session.get(Ensemble, ensemble_id)
    if not ensemble:
        return jsonify({"message": "Ansámbl neexistuje"}), 404

    # Validate target player entry
    if not ep_id:
        return jsonify({"message": "Chybí ensemble_player_id"}), 400

    ep = db.session.get(EnsemblePlayer, int(ep_id))
    if not ep or ep.ensemble_id != ensemble.id:
        return jsonify({"message": "Neplatný hráč"}), 400

    epi_id = ep.ensemble_instrumentation_id
    epi = db.session.get(EnsembleInstrumentation, int(epi_id))
    # Delete the record
    try:
        db.session.delete(ep)
        db.session.delete(epi)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"message": f"Chyba při odebírání hráče: {e.orig}"}), 409

    flash("Hráč byl úspěšně odebrán", "success")
    return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble.id))


@ensemble_bp.route("/<int:ensemble_id>/delete", methods=["POST"])
def ensemble_delete(ensemble_id):
    ensemble_to_delete = Ensemble.query.get_or_404(ensemble_id)
    db.session.delete(ensemble_to_delete)
    db.session.commit()
    flash("Soubor byl úspěšně smazán.", "success")
    return redirect(url_for("ensemble.all_ensembles"))
