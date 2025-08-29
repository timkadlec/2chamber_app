from flask import render_template, request, flash, redirect, url_for, session
from .forms import CompositionForm, ComposerForm, CompositionFilterForm, EnsembleForm
from utils.nav import navlink
from modules.library import library_bp
from models import db, Composition, Composer, Ensemble, EnsembleSemester
from orchestration_parser import process_chamber_instrumentation_line
from . import ensemble_bp


@ensemble_bp.route("/all")
@navlink("Soubory", weight=10)
def all_ensembles():
    current_semester = session["semester_id"]
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Adjust as needed
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
    return render_template("ensemble_form.html", form=form, ensemble=ensemble,)


@ensemble_bp.route("/<int:ensemble_id>/detail", methods=["GET", "POST"])
def ensemble_detail(ensemble_id):
    ensemble = Ensemble.query.filter_by(id=ensemble_id).first_or_404()
    return render_template("ensemble_detail.html", ensemble=ensemble)


@ensemble_bp.route("/<int:ensemble_id>/delete", methods=["POST"])
def ensemble_delete(ensemble_id):
    ensemble_to_delete = Ensemble.query.get_or_404(ensemble_id)
    db.session.delete(ensemble_to_delete)
    db.session.commit()
    flash("Soubor byl úspěšně smazán.", "success")
    return redirect(url_for("ensemble.all_ensembles"))
