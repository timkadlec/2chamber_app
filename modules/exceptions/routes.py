from . import exceptions_bp
from flask import render_template, request, flash, redirect, url_for
from flask_login import current_user
from utils.nav import navlink
from utils.decorators import roles_required, permission_required
from models import db, ChamberException
from modules.chamber_applications.routes import approve_applications, get_status_by_code
from datetime import datetime


# ---------------------------------------------------------
#   INDEX – view all exceptions
# ---------------------------------------------------------
@exceptions_bp.route("/", methods=["GET"])
@navlink("Výjimky", weight=100, permission='exc_can_view_all')
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 20

    pagination = ChamberException.query.order_by(
        ChamberException.id.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "exceptions_index.html",
        exceptions=pagination.items,
        pagination=pagination
    )


# ---------------------------------------------------------
#   DETAIL – inspect specific exception
# ---------------------------------------------------------
@exceptions_bp.route("/<int:exception_id>")
@permission_required("exc_can_view_detail")
def detail(exception_id):
    exception = ChamberException.query.get_or_404(exception_id)
    return render_template("exception_detail.html", exception=exception)


# ---------------------------------------------------------
#   READ-ONLY PUBLIC VIEW (optional)
# ---------------------------------------------------------
@exceptions_bp.route("/<int:exception_id>/view")
@permission_required("exc_can_view_detail")
def view(exception_id):
    exception = ChamberException.query.get_or_404(exception_id)
    return render_template("exception_view.html", exception=exception)


def approve_exception(exc: ChamberException, reviewer, comment=None):
    """
    Approve a ChamberException and run normal application approval.
    """
    if exc.status == "approved":
        raise ValueError("Exception is already approved.")

    # update exception
    exc.status = "approved"
    exc.reviewer_comment = comment
    exc.reviewed_at = datetime.utcnow()
    exc.reviewed_by = reviewer

    # approve the related application(s) using your existing logic
    new_ensemble, all_apps = approve_applications(exc.application, reviewer, comment)

    # 🔗 link the ensemble back to the exception
    new_ensemble.exception = exc
    db.session.add(new_ensemble)

    db.session.add(exc)
    db.session.commit()

    return exc, new_ensemble, all_apps


def reject_applications(application, reviewer, comment=None):
    """
    Reject a StudentChamberApplication and all its related applications.
    """
    rejected_status = get_status_by_code("rejected")
    if not rejected_status:
        raise ValueError("Status 'rejected' missing in database")

    related_apps = application.related_applications
    all_apps = [application] + related_apps

    for a in all_apps:
        a.status = rejected_status
        a.reviewed_at = datetime.utcnow()
        a.reviewed_by = reviewer
        a.review_comment = comment

    db.session.add_all(all_apps)
    db.session.commit()
    return all_apps


# ---------------------------------------------------------
#   DECISION – approve / reject exception
# ---------------------------------------------------------
@exceptions_bp.route("/<int:exception_id>/decision", methods=["POST"])
@permission_required("exc_can_decide")
def exception_decision(exception_id):
    exc = ChamberException.query.get_or_404(exception_id)
    decision = request.form.get("decision")
    comment = request.form.get("comment")

    if decision not in ["approved", "rejected"]:
        flash("Neplatné rozhodnutí.", "danger")
        return redirect(url_for("exceptions.detail", exception_id=exception_id))

    if decision == "approved":
        try:
            exc, new_ensemble, all_apps = approve_exception(exc, current_user, comment)
            flash(
                f"Výjimka č. {exc.id} byla schválena. "
                f"Žádosti {[a.id for a in all_apps]} schváleny a vytvořen soubor č. {new_ensemble.id}.",
                "success"
            )
            return redirect(url_for("ensemble.ensemble_detail", ensemble_id=new_ensemble.id))
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("exceptions.detail", exception_id=exception_id))

    elif decision == "rejected":
        exc.status = "rejected"
        exc.reviewer_comment = comment
        exc.reviewed_at = datetime.utcnow()
        exc.reviewed_by = current_user
        try:
            all_apps = reject_applications(exc.application, current_user, comment)
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("exceptions.detail", exception_id=exception_id))
        flash(
            f"Výjimka č. {exc.id} byla zamítnuta. "
            f"Žádosti {[a.id for a in all_apps]} byly označeny jako zamítnuté.",
            "warning"
        )
        return redirect(url_for("exceptions.detail", exception_id=exception_id))


@exceptions_bp.route("/delete/<int:exception_id>", methods=["POST"])
@permission_required("exc_can_delete")
def exception_delete(exception_id):
    exc = ChamberException.query.get_or_404(exception_id)
    try:
        db.session.delete(exc)
        db.session.commit()
        flash("Výjimka byla úspěšně smazána", "success")
        return redirect(url_for("exceptions.index"))
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("exceptions.detail", exception_id=exception_id))
