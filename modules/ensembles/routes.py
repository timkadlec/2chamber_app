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
        Ensemble.semester_links.any(EnsembleSemester.semester_id == current_semester)).paginate(page=page,
                                                                                                per_page=per_page,
                                                                                                error_out=False)
    ensembles = pagination.items
    return render_template("all_ensembles.html", ensembles=ensembles, pagination=pagination)


@ensemble_bp.route("/add", methods=["GET", "POST"])
def ensemble_add():
    form = EnsembleForm()
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
