from flask import flash, redirect, url_for, jsonify, render_template, request, session
from flask_login import current_user
from .forms import EnsembleForm, TeacherForm, NoteForm
from utils.nav import navlink
from models import db, Ensemble, EnsembleSemester, Player, Student, EnsemblePlayer, EnsembleInstrumentation, Instrument, \
    StudentSubjectEnrollment, Semester, EnsembleTeacher, Teacher, EnsembleNote, Department, Permission, Composition, \
    EnsembleRepertoire, Composer, CompositionInstrumentation
from . import ensemble_bp
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from models import EnsembleInstrumentation, EnsemblePlayer
from utils.decorators import permission_required
from sqlalchemy import or_, func, select
from utils.export_helpers import render_pdf
from utils.filter_helpers import get_common_filters, apply_common_filters
from utils.session_helpers import get_or_set_current_semester, get_or_set_current_semester_id


@ensemble_bp.route("/all")
@navlink("Soubory", weight=10)
def index():
    current_semester_id = get_or_set_current_semester_id()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # --- Collect and apply filters (shared helper) ---
    filters = get_common_filters()
    ensembles = db.session.query(Ensemble).filter(
        Ensemble.semester_links.any(EnsembleSemester.semester_id == current_semester_id)
    )
    ensembles = apply_common_filters(ensembles, filters, current_semester_id)

    # --- Sorting ---
    sort_by = request.args.get("sort_by", "name")
    sort_order = request.args.get("sort_order", "asc")

    if sort_by == "name":
        order_column = Ensemble.name
    elif sort_by == "teacher":
        # Sort by first teacher’s last name for the semester
        order_column = func.lower(
            select(Teacher.last_name)
            .join(EnsembleTeacher)
            .where(
                EnsembleTeacher.ensemble_id == Ensemble.id,
                EnsembleTeacher.semester_id == current_semester_id,
            )
            .limit(1)
            .correlate(Ensemble)
            .scalar_subquery()
        )
    elif sort_by == "health":
        order_column = Ensemble.health_check_label
    elif sort_by == "complete":
        order_column = Ensemble.is_complete
    else:
        order_column = Ensemble.name

    if sort_order == "desc":
        order_column = order_column.desc()

    # --- Pagination ---
    pagination = (
        ensembles.order_by(order_column)
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    ensembles = pagination.items

    # --- Render ---
    return render_template(
        "all_ensembles.html",
        ensembles=ensembles,
        pagination=pagination,
        instruments=Instrument.query.order_by(Instrument.weight)
        .filter_by(is_primary=True)
        .all(),
        teachers=Teacher.query.order_by(Teacher.last_name, Teacher.first_name).all(),
        departments=Department.query.order_by(Department.name).all(),
        selected_instrument_ids=filters["instrument_ids"],
        selected_teacher_ids=filters["teacher_ids"],
        selected_department_ids=filters["department_ids"],
        search_query=filters["search_query"],
        health_filter=filters["health_filter"],
        incomplete_filter=filters["incomplete_filter"],
        sort_by=sort_by,
        sort_order=sort_order,
    )


@ensemble_bp.route("/end-semester", methods=['GET'])
@permission_required("ens_end_semester")
def end_semester():
    current_semester_id = get_or_set_current_semester_id()
    current_semester = Semester.query.get_or_404(current_semester_id)

    upcoming_semester = (
        Semester.query
        .filter(Semester.start_date > current_semester.end_date)
        .order_by(Semester.start_date.asc())
        .first()
    )

    upcoming_semester_id = upcoming_semester.id if upcoming_semester else None
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # --- Collect and apply filters (shared helper) ---
    filters = get_common_filters()
    ensembles = db.session.query(Ensemble).filter(
        # must be in current semester
        Ensemble.semester_links.any(EnsembleSemester.semester_id == current_semester_id)
    )

    # if upcoming exists, exclude ensembles already linked there (already moved)
    if upcoming_semester_id:
        ensembles = ensembles.filter(
            ~Ensemble.semester_links.any(EnsembleSemester.semester_id == upcoming_semester_id)
        )

    ensembles = apply_common_filters(ensembles, filters, current_semester_id)

    # --- Sorting ---
    sort_by = request.args.get("sort_by", "name")
    sort_order = request.args.get("sort_order", "asc")

    if sort_by == "name":
        order_column = Ensemble.name
    elif sort_by == "teacher":
        # Sort by first teacher’s last name for the semester
        order_column = func.lower(
            select(Teacher.last_name)
            .join(EnsembleTeacher)
            .where(
                EnsembleTeacher.ensemble_id == Ensemble.id,
                EnsembleTeacher.semester_id == current_semester_id,
            )
            .limit(1)
            .correlate(Ensemble)
            .scalar_subquery()
        )
    elif sort_by == "health":
        order_column = Ensemble.health_check_label
    elif sort_by == "complete":
        order_column = Ensemble.is_complete
    else:
        order_column = Ensemble.name

    if sort_order == "desc":
        order_column = order_column.desc()

    # --- Pagination ---
    pagination = (
        ensembles.order_by(order_column)
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    ensembles = pagination.items

    # --- Render ---
    return render_template(
        "end_semester.html",
        ensembles=ensembles,
        pagination=pagination,
        instruments=Instrument.query.order_by(Instrument.weight)
        .filter_by(is_primary=True)
        .all(),
        teachers=Teacher.query.order_by(Teacher.last_name, Teacher.first_name).all(),
        departments=Department.query.order_by(Department.name).all(),
        selected_instrument_ids=filters["instrument_ids"],
        selected_teacher_ids=filters["teacher_ids"],
        selected_department_ids=filters["department_ids"],
        search_query=filters["search_query"],
        health_filter=filters["health_filter"],
        incomplete_filter=filters["incomplete_filter"],
        sort_by=sort_by,
        sort_order=sort_order,
    )


@ensemble_bp.route("/all/pdf")
@permission_required('ens_export_pdf')
def export_pdf():
    current_semester_id = get_or_set_current_semester_id()
    filters = get_common_filters()

    # Base query
    ensembles = db.session.query(Ensemble).filter(
        Ensemble.semester_links.any(EnsembleSemester.semester_id == current_semester_id)
    )
    ensembles = apply_common_filters(ensembles, filters, current_semester_id)
    ensembles = ensembles.order_by(Ensemble.name).all()

    # --- Enrich filters with human-readable labels ---
    # (resolve IDs into names for the PDF header)
    if filters["instrument_ids"]:
        from models import Instrument
        filters["instrument_names"] = [
            i.name for i in Instrument.query.filter(Instrument.id.in_(filters["instrument_ids"])).all()
        ]
    else:
        filters["instrument_names"] = []

    if filters["teacher_ids"]:
        from models import Teacher
        filters["teacher_names"] = [
            t.full_name if hasattr(t, "full_name") else f"{t.first_name} {t.last_name}"
            for t in Teacher.query.filter(Teacher.id.in_(filters["teacher_ids"])).all()
        ]
    else:
        filters["teacher_names"] = []

    if filters["department_ids"]:
        from models import Department
        filters["department_names"] = [
            d.name for d in Department.query.filter(Department.id.in_(filters["department_ids"])).all()
        ]
    else:
        filters["department_names"] = []

    # Prepare context
    context = {
        "ensembles": ensembles,
        "current_semester": Semester.query.get(current_semester_id),
        "filters": filters,
    }

    return render_pdf("pdf_export/all_ensembles.html", context, "SKH_KomorniSoubory_vse")


@ensemble_bp.route("/by_teacher/pdf")
@permission_required('ens_export_pdf')
def export_pdf_by_teacher():
    current_semester_id = get_or_set_current_semester_id()
    filters = get_common_filters()

    teachers = (
        Teacher.query.join(EnsembleTeacher)
        .filter(EnsembleTeacher.semester_id == current_semester_id)
        .distinct()
    )
    if filters["teacher_ids"]:
        teachers = teachers.filter(Teacher.id.in_(filters["teacher_ids"]))
    if filters["department_ids"]:
        teachers = teachers.filter(Teacher.department_id.in_(filters["department_ids"]))
    teachers = teachers.order_by(Teacher.last_name, Teacher.first_name).all()

    filtered_teachers = []
    for teacher in teachers:
        q = db.session.query(Ensemble).join(EnsembleTeacher).filter(
            EnsembleTeacher.semester_id == current_semester_id,
            EnsembleTeacher.teacher_id == teacher.id,
        )
        q = apply_common_filters(q, filters, current_semester_id)
        ensembles = q.order_by(Ensemble.name).all()
        if ensembles:
            teacher.filtered_ensembles = ensembles
            filtered_teachers.append(teacher)

    return render_pdf(
        "pdf_export/ensemble_by_teacher.html",
        {
            "teachers": filtered_teachers,
            "current_semester": Semester.query.get(current_semester_id),
        },
        "SKH_KomorniSoubory_dle_pedagogu",
    )


@ensemble_bp.route("/teacher-hours/pdf")
@permission_required('ens_export_pdf')
def export_pdf_teacher_hours():
    current_semester_id = get_or_set_current_semester_id()
    filters = get_common_filters()

    # --- Query teachers for current semester ---
    teachers = (
        Teacher.query.join(EnsembleTeacher)
        .filter(EnsembleTeacher.semester_id == current_semester_id)
        .distinct()
    )

    if filters["teacher_ids"]:
        teachers = teachers.filter(Teacher.id.in_(filters["teacher_ids"]))
    if filters["department_ids"]:
        teachers = teachers.filter(Teacher.department_id.in_(filters["department_ids"]))

    teachers = teachers.order_by(Teacher.department_id, Teacher.last_name, Teacher.first_name).all()

    # --- Build filtered list with ensembles per teacher ---
    filtered_teachers = []
    for teacher in teachers:
        q = (
            db.session.query(Ensemble)
            .join(EnsembleTeacher)
            .filter(
                EnsembleTeacher.semester_id == current_semester_id,
                EnsembleTeacher.teacher_id == teacher.id,
            )
        )
        q = apply_common_filters(q, filters, current_semester_id)
        ensembles = q.order_by(Ensemble.name).all()

        if ensembles:
            teacher.filtered_ensembles = ensembles
            filtered_teachers.append(teacher)

    # --- Group teachers by department ---
    grouped = {}
    for t in filtered_teachers:
        dept = t.department.name if t.department else "Neurčeno"
        grouped.setdefault(dept, []).append(t)

    return render_pdf(
        "pdf_export/ensemble_teacher_hours.html",
        {
            "grouped_teachers": grouped,  # 👈 main change
            "current_semester": Semester.query.get(current_semester_id),
        },
        "SKH_Uvazky",
    )


@ensemble_bp.route("/add", methods=["GET", "POST"])
@permission_required('ens_add')
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
@permission_required('ens_edit')
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
@permission_required('ens_detail')
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
    db.session.flush()
    return epi, True


@ensemble_bp.route("/<int:ensemble_id>/player/<int:ensemble_instrumentation_id>/<mode>", methods=["GET", "POST"])
@permission_required('ens_player_assign')
def add_player_to_ensemble(ensemble_id, ensemble_instrumentation_id, mode="student"):
    ensemble = Ensemble.query.get(ensemble_id)
    instrumentation = EnsembleInstrumentation.query.get(ensemble_instrumentation_id)
    current_semester = get_or_set_current_semester()
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


@ensemble_bp.route("/<int:ensemble_id>/player/add-empty", methods=["POST"])
@permission_required('ens_player_add')
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
@permission_required('ens_preset_add')
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


@ensemble_bp.route("/<int:ensemble_id>/player/remove", methods=["POST"])
@permission_required('ens_player_remove')
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
@permission_required('ens_delete')
def ensemble_delete(ensemble_id):
    ensemble_to_delete = Ensemble.query.get_or_404(ensemble_id)
    db.session.delete(ensemble_to_delete)
    db.session.commit()
    flash("Soubor byl úspěšně smazán.", "success")
    return redirect(url_for("ensemble.index"))


def count_hour_donation_for_semester(ensemble_id: int, semester_id: int) -> float:
    cnt = (
        db.session.query(func.count(EnsembleTeacher.id))
        .filter(
            EnsembleTeacher.ensemble_id == ensemble_id,
            EnsembleTeacher.semester_id == semester_id
        )
        .scalar()
    )
    return (1 / cnt) if cnt else 0.0


@ensemble_bp.route("/<int:ensemble_id>/teacher/assign", methods=["POST"])
@permission_required('ens_teacher_assign')
def ensemble_assign_teacher(ensemble_id):
    ensemble = Ensemble.query.get_or_404(ensemble_id)
    teacher_form = TeacherForm()
    current_semester = get_or_set_current_semester()

    if teacher_form.validate_on_submit():
        teacher_id = teacher_form.teacher.data.id

        existing = (
            EnsembleTeacher.query
            .filter_by(
                teacher_id=teacher_id,
                ensemble_id=ensemble.id,
                semester_id=current_semester.id
            )
            .first()
        )

        if existing:
            flash("Tento pedagog je již přiřazen k souboru v aktuálním semestru.", "warning")
            return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble.id))

        db.session.add(EnsembleTeacher(
            teacher_id=teacher_id,
            ensemble_id=ensemble.id,
            semester_id=current_semester.id
        ))
        db.session.flush()

        # Recompute donation ONLY for current semester links
        links_current = (
            EnsembleTeacher.query
            .filter_by(ensemble_id=ensemble.id, semester_id=current_semester.id)
            .all()
        )

        donation = 1 / len(links_current) if links_current else 0.0
        for link in links_current:
            link.hour_donation = donation

        db.session.commit()
        flash("Pedagog byl úspěšně přiřazen k souboru", "success")

    return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble.id))


@ensemble_bp.route("/teacher_assignment/<int:assignment_id>/remove", methods=["POST"])
@permission_required('ens_teacher_remove')
def ensemble_remove_teacher(assignment_id):
    assignment = EnsembleTeacher.query.get_or_404(assignment_id)

    ensemble_id = assignment.ensemble_id
    semester_id = assignment.semester_id

    db.session.delete(assignment)
    db.session.flush()

    # Recompute donation ONLY for the same semester as the removed assignment
    links_remaining = (
        EnsembleTeacher.query
        .filter_by(ensemble_id=ensemble_id, semester_id=semester_id)
        .all()
    )

    donation = 1 / len(links_remaining) if links_remaining else 0.0
    for link in links_remaining:
        link.hour_donation = donation

    db.session.commit()
    flash("Pedagog byl úspěšně odebrán ze souboru", "success")

    return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble_id))


@ensemble_bp.route("/<int:ensemble_id>/add_note", methods=["POST"])
@permission_required('ens_notes')
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
@permission_required('ens_notes')
def delete_note(ensemble_id, note_id):
    note = EnsembleNote.query.filter_by(id=note_id, ensemble_id=ensemble_id).first_or_404()
    db.session.delete(note)
    db.session.commit()
    flash("Poznámka byla smazána.", "info")
    return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble_id))


@ensemble_bp.route("/<int:ensemble_id>/add_composition", methods=["GET", "POST"])
def add_composition_to_ensemble(ensemble_id):
    ensemble = Ensemble.query.get_or_404(ensemble_id)
    current_semester = get_or_set_current_semester()

    if request.method == "POST":
        comp_id = int(request.form["selected_composition_id"])
        composition = Composition.query.get_or_404(comp_id)

        existing = EnsembleRepertoire.query.filter_by(
            ensemble_id=ensemble.id,
            composition_id=composition.id,
            semester_id=current_semester.id
        ).first()

        if not existing:
            db.session.add(EnsembleRepertoire(
                ensemble_id=ensemble.id,
                composition_id=composition.id,
                semester_id=current_semester.id
            ))
            db.session.commit()
            flash(f"Skladba '{composition.name}' byla přidána do souboru {ensemble.name}.", "success")

        return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble.id))

    # === Filtering ===
    q = request.args.get("q", "").strip()
    instrument_filter = request.args.getlist("instrument_ids", type=int)

    query = Composition.query.join(Composer).outerjoin(CompositionInstrumentation)

    if q:
        ilike = f"%{q}%"
        query = query.filter(
            db.or_(
                Composition.name.ilike(ilike),
                Composer.first_name.ilike(ilike),
                Composer.last_name.ilike(ilike),
            )
        )

    if instrument_filter:
        query = query.filter(CompositionInstrumentation.instrument_id.in_(instrument_filter))

    query = query.order_by(Composer.last_name, Composition.name)
    available_compositions = query.all()

    instruments = Instrument.query.order_by(Instrument.weight).all()

    return render_template(
        "add_composition_to_ensemble.html",
        ensemble=ensemble,
        current_semester=current_semester,
        available_compositions=available_compositions,
        instruments=instruments,
        q=q,
        instrument_filter=instrument_filter,
    )


@ensemble_bp.route("/<int:ensemble_id>/remove_composition/<int:composition_id>/<int:semester_id>", methods=["POST"])
def remove_composition_from_ensemble(ensemble_id, composition_id, semester_id):
    link = EnsembleRepertoire.query.filter_by(
        ensemble_id=ensemble_id,
        composition_id=composition_id,
        semester_id=semester_id
    ).first_or_404()

    db.session.delete(link)
    db.session.commit()
    flash("Skladba byla odebrána ze souboru.", "info")

    return redirect(url_for("ensemble.ensemble_detail", ensemble_id=ensemble_id))
