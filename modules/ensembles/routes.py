from flask import render_template, request, flash, redirect, url_for
from .forms import CompositionForm, ComposerForm, CompositionFilterForm
from utils.nav import navlink
from modules.library import library_bp
from models import db, Composition, Composer
from orchestration_parser import process_chamber_instrumentation_line


@library_bp.route("/composers")
@navlink("Skladatelé", weight=110, group="Knihovna")
def composers():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Adjust as needed
    pagination = Composer.query.order_by(Composer.last_name).paginate(page=page, per_page=per_page, error_out=False)
    composers = pagination.items
    return render_template("library_composers.html", composers=composers, pagination=pagination)


def is_duplicate_composer(composer):
    duplicate = Composer.query.filter(
        Composer.first_name == composer.first_name,
        Composer.last_name == composer.last_name,
    ).first()

    return bool(duplicate)


@library_bp.route('/composer/add', methods=["POST", "GET"])
def composer_add():
    form = ComposerForm(mode="add")
    if form.validate_on_submit():
        nc = Composer()
        form.populate_obj(nc)
        if is_duplicate_composer(nc):
            flash("Tento skladatel již existuje", "danger")
            db.session.rollback()
        else:
            db.session.add(nc)
            db.session.commit()
            flash("Skladatel úspěšně vytvořen", "success")
            return redirect(url_for("library.composer_detail", composer_id=nc.id))

    return render_template("composer_form.html", form=form)


@library_bp.route("/composer/<int:composer_id>/edit", methods=["POST", "GET"])
def composer_edit(composer_id):
    composer = Composer.query.get_or_404(composer_id)
    form = ComposerForm(obj=composer, mode="edit")
    if form.validate_on_submit():
        form.populate_obj(composer)
        db.session.commit()
        flash("Skladatel úspěšně upraven", "success")
        return redirect(url_for('library.composers'))
    return render_template("composer_form.html", form=form, composer=composer)


@library_bp.route("/composer/<int:composer_id>/detail")
def composer_detail(composer_id):
    composer = Composer.query.get_or_404(composer_id)
    return render_template("composer_detail.html", composer=composer)


@library_bp.route("/composer/<int:composer_id>/delete", methods=["POST"])
def composer_delete(composer_id):
    composer = Composer.query.get_or_404(composer_id)
    try:
        db.session.delete(composer)
        db.session.commit()
        flash("Skladatel úspěšně odebrán", "success")
        return redirect(url_for("library.composers"))
    except Exception as e:
        flash(f"Vyskytla se chyba: {e}", "danger")
        return redirect(url_for("library.composers"))


@library_bp.route('/compositions')
@navlink("Skladby", weight=110, group="Knihovna")
def compositions():
    form = CompositionFilterForm(request.args)

    query = Composition.query

    if form.project_id.data:
        query = query.filter(Composition.project_id == int(form.project_id.data))

    if form.composer.data:
        query = query.filter(Composition.composer_id.in_([composer.id for composer in form.composer.data]))

    if form.type.data:
        query = query.filter(Composition.type == form.type.data)

    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Composition.name).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        "library_compositions.html",
        compositions=pagination.items,
        pagination=pagination,
        form=form
    )


def is_duplicate_composition(composition):
    if not composition.composer.id:
        return False  # or raise an error if this should never happen

    duplicate = Composition.query.filter(
        Composition.name == composition.name,
        Composition.composer_id == composition.composer_id,
        Composition.id != composition.id  # exclude self if updating
    ).first()

    return bool(duplicate)


@library_bp.route('/composition/add', methods=["GET", "POST"])
def composition_add():
    composer_id = request.args.get("composer_id", type=int)
    selected_composer = Composer.query.get(composer_id) if composer_id else None

    form = CompositionForm(mode="add")

    if request.method == "GET" and selected_composer:
        form.composer.data = selected_composer  # Preselect in dropdown

    if form.validate_on_submit():
        nc = Composition()
        form.populate_obj(nc)

        if is_duplicate_composition(nc):
            flash("Tato kompozice již existuje", "danger")
            db.session.rollback()
        else:
            db.session.add(nc)
            db.session.commit()
            process_chamber_instrumentation_line(nc.id, form.instrumentation.data)
            flash("Skladba úspěšně vytvořena", "success")
            return redirect(url_for("library.composition_detail", composition_id=nc.id))

    return render_template("composition_form.html", form=form)


@library_bp.route("/composition/<int:composition_id>/detail")
def composition_detail(composition_id):
    composition = Composition.query.get_or_404(composition_id)
    return render_template("composition_detail.html", composition=composition)


@library_bp.route("/composition/<int:composition_id>/edit", methods=["POST", "GET"])
def composition_edit(composition_id):
    composition = Composition.query.get_or_404(composition_id)
    form = CompositionForm(obj=composition, mode="edit")
    form.instrumentation.data = composition.chamber_instrumentation
    if form.validate_on_submit():
        form.populate_obj(composition)
        process_chamber_instrumentation_line(composition.id, form.instrumentation.data)
        db.session.commit()
        flash("Skladba úspěšně upravena", "success")
        return redirect(url_for('library.compositions'))
    return render_template("composition_form.html", form=form, composition=composition)


@library_bp.route("/composition/<int:composition_id>/delete", methods=["POST"])
def composition_delete(composition_id):
    composition = Composition.query.get_or_404(composition_id)
    try:
        db.session.delete(composition)
        db.session.commit()
        flash("Skladba úspěšně odebrána", "success")
        if request.args.get("nav_type") == "from_composer":
            return redirect(url_for("library.composer_detail", composer_id=composition.composer_id))
        else:
            return redirect(url_for("library.compositions"))
    except Exception as e:
        flash(f"Vyskytla se chyba: {e}", "danger")
        return redirect(url_for("library.compositions"))
