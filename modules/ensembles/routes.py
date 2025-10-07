from flask import render_template, flash, redirect, url_for, session, request, jsonify, current_app
from flask_login import current_user
from .forms import EnsembleForm, TeacherForm, NoteForm
from utils.nav import navlink
from models import db, Ensemble, EnsembleSemester, Player, Student, EnsemblePlayer, EnsembleInstrumentation, \
    KomorniHraStud, Instrument, StudentSubjectEnrollment, Semester, EnsembleTeacher, Teacher, EnsembleNote
from . import ensemble_bp
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
import unicodedata
from sqlalchemy import exists, select, or_
from models import EnsembleInstrumentation, EnsemblePlayer
from sqlalchemy.sql import func

incomplete_subq = (
    select(EnsembleInstrumentation.ensemble_id)
    .outerjoin(
        EnsemblePlayer,
        EnsemblePlayer.ensemble_instrumentation_id == EnsembleInstrumentation.id
    )
    .group_by(EnsembleInstrumentation.ensemble_id, EnsembleInstrumentation.id)
    # Having: no player assigned (either none exist or all have player_id IS NULL)
    .having(func.count(EnsemblePlayer.player_id) == 0)
    .scalar_subquery()
)


@ensemble_bp.route("/all")
@navlink("Soubory", weight=10)
def index():
    current_semester = session["semester_id"]
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # --- filters from GET ---
    instrument_ids = request.args.getlist("instrument_id", type=int)
    teacher_ids = request.args.getlist("teacher_id", type=int)
    search_query = request.args.get("q", "").strip()
    health_filter = request.args.get("health", "").strip()
    incomplete_filter = request.args.get("incomplete", "").strip()

    def strip_diacritics(s: str) -> str:
        return "".join(
            c for c in unicodedata.normalize("NFD", s)
            if unicodedata.category(c) != "Mn"
        )

    search = strip_diacritics(search_query).lower()

    # --- base query restricted to current semester ---
    ensembles = Ensemble.query.filter(
        Ensemble.semester_links.any(EnsembleSemester.semester_id == current_semester)
    )

    # --- instrument filter ---
    if instrument_ids:
        ensembles = ensembles.join(Ensemble.instrumentation_entries).filter(
            EnsembleInstrumentation.instrument_id.in_(instrument_ids)
        )

    # --- teacher filter ---
    if teacher_ids:
        ensembles = ensembles.join(Ensemble.teacher_links).filter(
            EnsembleTeacher.teacher_id.in_(teacher_ids),
            EnsembleTeacher.semester_id == current_semester
        )

    # --- incomplete / complete filter ---
    if incomplete_filter in ("1", "0"):
        incomplete_subq = (
            db.select(EnsembleInstrumentation.ensemble_id)
            .outerjoin(
                EnsemblePlayer,
                EnsemblePlayer.ensemble_instrumentation_id == EnsembleInstrumentation.id
            )
            .group_by(EnsembleInstrumentation.ensemble_id, EnsembleInstrumentation.id)
            .having(func.count(EnsemblePlayer.player_id) == 0)
            .scalar_subquery()
        )

        if incomplete_filter == "1":
            ensembles = ensembles.filter(Ensemble.is_complete.is_(False))  # incomplete
        else:
            ensembles = Ensemble.query.filter(Ensemble.is_complete.is_(True))  # incomplete

    # --- player or ensemble search ---
    if search_query:
        search_pattern = f"%{search}%"
        ensembles = (
            ensembles
            .outerjoin(Ensemble.player_links)
            .outerjoin(EnsemblePlayer.player)
            .filter(
                or_(
                    func.unaccent(func.lower(Player.first_name)).like(search_pattern),
                    func.unaccent(func.lower(Player.last_name)).like(search_pattern),
                    func.unaccent(func.lower(Ensemble.name)).like(search_pattern),
                )
            )
        )

    # --- health check filter ---
    if health_filter:
        ensembles = ensembles.filter(Ensemble.health_check_label == health_filter)

    # --- distinct + order + pagination ---
    pagination = ensembles.distinct().order_by(Ensemble.name).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    ensembles = pagination.items

    return render_template(
        "all_ensembles.html",
        ensembles=ensembles,
        pagination=pagination,
        instruments=Instrument.query.order_by(Instrument.weight).filter_by(is_primary=True).all(),
        teachers=Teacher.query.order_by(Teacher.last_name, Teacher.first_name).all(),
        selected_instrument_ids=instrument_ids,
        selected_teacher_ids=teacher_ids,
        search_query=search_query,
        health_filter=health_filter,
        incomplete_filter=incomplete_filter,  # 👈 Pass to template
    )


@ensemble_bp.route("/all/pdf")
def export_pdf():
    import datetime
    from flask import render_template_string, make_response, session, request
    from weasyprint import HTML
    from pathlib import Path

    current_semester = session["semester_id"]

    # same filters as index()
    instrument_ids = request.args.getlist("instrument_id", type=int)
    teacher_ids = request.args.getlist("teacher_id", type=int)
    search_query = request.args.get("q", "").strip()
    health_filter = request.args.get("health", "").strip()

    ensembles = Ensemble.query.filter(
        Ensemble.semester_links.any(EnsembleSemester.semester_id == current_semester)
    )
    if instrument_ids:
        ensembles = ensembles.join(Ensemble.instrumentation_entries).filter(
            EnsembleInstrumentation.instrument_id.in_(instrument_ids))
    if teacher_ids:
        ensembles = ensembles.join(Ensemble.teacher_links).filter(
            EnsembleTeacher.teacher_id.in_(teacher_ids),
            EnsembleTeacher.semester_id == current_semester)
    if search_query:
        pattern = f"%{search_query.lower()}%"
        ensembles = (ensembles.outerjoin(Ensemble.player_links)
        .outerjoin(EnsemblePlayer.player)
        .filter(or_(
            func.unaccent(func.lower(Player.first_name)).like(pattern),
            func.unaccent(func.lower(Player.last_name)).like(pattern),
            func.unaccent(func.lower(Ensemble.name)).like(pattern)
        )))
    if health_filter:
        ensembles = ensembles.filter(Ensemble.health_check_label == health_filter)
    ensembles = ensembles.distinct().order_by(Ensemble.name).all()

    logo_path = Path(current_app.static_folder) / "images" / "hamu_logo.png"
    logo_url = logo_path.resolve().as_uri()

    # HTML template
    html = render_template('pdf_export/all_ensembles.html', ensembles=ensembles,
                           current_semester=Semester.query.get(current_semester),
                           today=datetime.date.today(),
                           logo_url=logo_url,)

    pdf = HTML(string=html).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = \
        f'attachment; filename=ensembles_{datetime.date.today():%Y%m%d}.pdf'
    return response


@ensemble_bp.route("/by_teacher/pdf")
def export_pdf_by_teacher():
    import datetime
    from pathlib import Path
    from flask import render_template, make_response, session, current_app
    from weasyprint import HTML

    current_semester_id = session["semester_id"]
    current_semester = Semester.query.get(current_semester_id)

    teachers = (
        Teacher.query.join(EnsembleTeacher)
        .filter(EnsembleTeacher.semester_id == current_semester_id)
        .distinct()
        .order_by(Teacher.last_name, Teacher.first_name)
        .all()
    )

    # ✅ build absolute file:// path to logo for WeasyPrint
    logo_path = Path(current_app.static_folder) / "images" / "hamu_logo.png"
    logo_url = logo_path.resolve().as_uri()  # -> file:///srv/www/.../static/images/hamu_logo.png

    html = render_template(
        "pdf_export/ensemble_by_teacher.html",
        teachers=teachers,
        current_semester=current_semester,
        today=datetime.date.today(),
        logo_url=logo_url,  # pass full absolute URI to template
    )

    # base_url not strictly required for file://, but harmless
    pdf = HTML(string=html, base_url=str(Path(current_app.root_path).resolve())).write_pdf()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers[
        "Content-Disposition"
    ] = f'attachment; filename=ensembles_by_teacher_{datetime.date.today():%Y%m%d}.pdf'
    return response


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
        return redirect(url_for("ensemble.ensemble_detail", ensemble_id=new_ensemble.id, ))
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

    teacher_form = TeacherForm()
    note_form = NoteForm()

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
        available_instruments=available_instruments,
        teacher_form=teacher_form,
        note_form=note_form,
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


@ensemble_bp.route("/<int:ensemble_id>/player/<int:ensemble_instrumentation_id>/<mode>", methods=["GET", "POST"])
def add_player_to_ensemble(ensemble_id, ensemble_instrumentation_id, mode="student"):
    ensemble = Ensemble.query.get(ensemble_id)
    instrumentation = EnsembleInstrumentation.query.get(ensemble_instrumentation_id)
    current_semester = Semester.query.filter_by(id=session.get("semester_id")).first()
    if request.method == "GET":
        if mode == "student":
            available_players = (
                db.session.query(Player)
                .join(Student, Player.student)  # only players linked to students
                .join(StudentSubjectEnrollment, StudentSubjectEnrollment.student_id == Student.id)
                .filter(Student.active.is_(True))
                .filter(Player.instrument_id == instrumentation.instrument_id)
                .filter(StudentSubjectEnrollment.semester_id == current_semester.id)
                .options(
                    selectinload(Player.instrument),
                    selectinload(Player.student).selectinload(Student.instrument),
                )
                .order_by(Student.last_name, Student.first_name)
                .all()
            )
        else:
            available_players = (
                db.session.query(Player)
                .filter(Player.student_id.is_(None))
                .filter(Player.instrument_id == instrumentation.instrument_id)
                .options(
                    selectinload(Player.instrument),
                )
                .all()
            )

        return render_template("ensemble_add_player.html", ensemble=ensemble, instrumentation=instrumentation,
                               available_players=available_players)

    if request.method == "POST":
        selected_player_id = int(request.form.get("selected_player_id"))
        player = Player.query.get(selected_player_id)

        if not player:
            flash("Hráč nebyl nalezen.", "danger")
            return redirect(url_for("ensemble.add_player_to_ensemble",
                                    ensemble_id=ensemble.id,
                                    ensemble_instrumentation_id=instrumentation.id,
                                    mode="student"))
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
            current_assignment.player_id = player.id
        else:
            # create new assignment
            current_assignment = EnsemblePlayer(
                ensemble_id=ensemble.id,
                ensemble_instrumentation_id=ensemble_instrumentation_id,
                player_id=player.id
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


@ensemble_bp.route("/<int:ensemble_id>/add-preset", methods=["POST"])
def add_preset_ensemble(ensemble_id):
    """Quickly create a predefined ensemble structure."""
    ensemble = Ensemble.query.get_or_404(ensemble_id)
    preset_key = request.form.get("preset")

    # Define instrument templates by name
    presets = {
        "2flutes_piano": ["Flétna", "Flétna", "Klavír"],
        "wind_trio": ["Hoboj", "Klarinet", "Fagot"],
        "wind_quintet": ["Flétna", "Hoboj", "Klarinet", "Fagot", "Lesní roh"],
        "string_quartet": ["Housle", "Housle", "Viola", "Violoncello"],
        "piano_trio": ["Housle", "Violoncello", "Klavír"],
        "piano_quartet": ["Housle", "Viola", "Violoncello", "Klavír"],
        "brass_quintet": ["Trubka", "Trubka", "Lesní roh", "Pozoun", "Tuba"],
        "guitar_duo": ["Kytara", "Kytara"]
    }

    instruments = presets.get(preset_key)
    if not instruments:
        flash("Neznámý preset souboru.", "danger")
        return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble.id))

    created_names = []

    # Create instrumentations + empty player slots
    for position, name in enumerate(instruments, start=1):
        instrument = db.session.query(
            db.inspect(EnsembleInstrumentation).mapper.class_.instrument.property.mapper.class_).filter_by(
            name=name).first()
        # Or simpler if you have direct Instrument model import:
        # from models import Instrument
        # instrument = Instrument.query.filter_by(name=name).first()

        if not instrument:
            flash(f"Nástroj „{name}“ nebyl nalezen.", "warning")
            continue

        new_instr = EnsembleInstrumentation(
            ensemble_id=ensemble.id,
            instrument_id=instrument.id,
            position=position
        )
        db.session.add(new_instr)
        db.session.flush()

        empty_slot = EnsemblePlayer(
            ensemble_id=ensemble.id,
            ensemble_instrumentation_id=new_instr.id,
            player_id=None
        )
        db.session.add(empty_slot)
        created_names.append(name)

    db.session.commit()

    if created_names:
        flash(f"Přidán preset: {', '.join(created_names)}", "success")
    else:
        flash("Nebyl přidán žádný nástroj.", "warning")

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
    return redirect(url_for("ensemble.index"))


def count_hour_donation(ensemble):
    count_of_teachers = len(ensemble.teacher_links)
    return 1 / (count_of_teachers)


@ensemble_bp.route("/<int:ensemble_id>/teacher/assign", methods=["POST"])
def ensemble_assign_teacher(ensemble_id):
    ensemble = Ensemble.query.get_or_404(ensemble_id)
    teacher_form = TeacherForm()
    current_semester = Semester.query.filter_by(id=session.get("semester_id")).first()

    if teacher_form.validate_on_submit():
        # Check if assignment already exists
        existing = EnsembleTeacher.query.filter_by(
            teacher_id=teacher_form.teacher.data.id,
            ensemble_id=ensemble.id,
            semester_id=current_semester.id
        ).first()

        if existing:
            flash("Tento pedagog je již přiřazen k souboru v aktuálním semestru.", "warning")
        else:
            assignment = EnsembleTeacher(
                teacher_id=teacher_form.teacher.data.id,
                ensemble_id=ensemble.id,
                semester_id=current_semester.id
            )
            db.session.add(assignment)
            db.session.flush()  # ensure new assignment is included in teacher_links

            # update all teachers
            for teacher in ensemble.teacher_links:
                teacher.hour_donation = count_hour_donation(ensemble)

            db.session.commit()
            flash("Pedagog byl úspěšně přiřazen k souboru", "success")

    return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble.id))


@ensemble_bp.route("/teacher_assignment/<int:assignment_id>/remove", methods=["POST"])
def ensemble_remove_teacher(assignment_id):
    assignment = EnsembleTeacher.query.get_or_404(assignment_id)
    ensemble = Ensemble.query.get_or_404(assignment.ensemble_id)

    db.session.delete(assignment)
    db.session.flush()

    # update all remaining teachers
    for teacher in ensemble.teacher_links:
        teacher.hour_donation = count_hour_donation(ensemble)

    db.session.commit()
    flash("Pedagog byl úspěšně odebrán ze souboru", "success")
    return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble.id))


@ensemble_bp.route("/<int:ensemble_id>/add_note", methods=["POST"])
def add_note(ensemble_id):
    form = NoteForm()
    if form.validate_on_submit():
        note = EnsembleNote(
            text=form.text.data,
            ensemble_id=ensemble_id,
            created_by=current_user
        )
        db.session.add(note)
        db.session.commit()
        flash("Poznámka byla přidána.", "success")
    else:
        flash("Nepodařilo se přidat poznámku.", "danger")
    return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble_id))


@ensemble_bp.route("/<int:ensemble_id>/notes/<int:note_id>/delete", methods=["POST"])
def delete_note(ensemble_id, note_id):
    note = EnsembleNote.query.filter_by(id=note_id, ensemble_id=ensemble_id).first_or_404()
    db.session.delete(note)
    db.session.commit()
    flash("Poznámka byla smazána.", "info")
    return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble_id))
