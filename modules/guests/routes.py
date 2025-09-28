from flask import render_template, request, flash, redirect, url_for, session, request
from modules.guests.forms import PlayerForm
from utils.nav import navlink
from models import db, Student, StudentSubjectEnrollment, Instrument, Subject, Player
from modules.guests import guest_bp
from sqlalchemy import and_
from sqlalchemy import or_


@guest_bp.route("/", methods=["GET"])
@navlink("Hosté", group="Lidé", weight=200)
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 20

    query = Player.query

    # Instrument filter
    instrument_id = request.args.get("instrument_id", type=int)
    if instrument_id:
        query = query.filter(Player.instrument_id == instrument_id)

        # Search filter (by first_name OR last_name)
    search_query = request.args.get("q", "").strip()
    if search_query:
        query = query.filter(
            or_(
                Player.first_name.ilike(f"%{search_query}%"),
                Player.last_name.ilike(f"%{search_query}%"),
            )
        )

        # Sort by name
    query = query.order_by(Player.last_name, Player.first_name).filter_by(student_id=None)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "all_players.html",
        players=pagination.items,
        pagination=pagination,
        instruments=Instrument.query.filter_by(is_primary=True).order_by(Instrument.weight).all(),
        selected_instrument_id=instrument_id,
        search_query=search_query,
    )


def is_duplicate_player(player):
    duplicate_p = Player.query.filter_by(first_name=player.first_name, last_name=player.last_name,
                                         instrument_id=player.instrument_id).first()
    return bool(duplicate_p)


@guest_bp.route("/add", methods=["GET", "POST"])
def player_add():
    form = PlayerForm(mode="add")
    if request.method == "POST":
        first_name = form.first_name.data
        last_name = form.last_name.data
        instrument = form.instrument.data
        email = form.email.data
        phone = form.phone.data

        new_player = Player(first_name=first_name, last_name=last_name, instrument_id=instrument.id, email=email,
                            phone=phone)

        if not is_duplicate_player(new_player):
            db.session.add(new_player)
            db.session.commit()
            flash("Nový hráč byl přidán", "success")
            return redirect(url_for("guests.index"))
        else:
            flash("Takový hráč již existuje", "danger")
            return redirect(url_for("guests.player_add"))

    return render_template("player_form.html", form=form)


@guest_bp.route("/<int:player_id>/edit", methods=["GET", "POST"])
def player_edit(player_id):
    player = Player.query.get_or_404(player_id)
    form = PlayerForm(obj=player)
    form.mode = "edit"

    if form.validate_on_submit():
        form.populate_obj(player)
        db.session.commit()
        flash("Hráč byl úspěšně upraven", "success")
        return redirect(url_for("guests.index"))

    return render_template("player_form.html", form=form, player=player)


@guest_bp.route("/delete/<int:player_id>", methods=["POST"])
def player_delete(player_id):
    player = Player.query.get_or_404(player_id)
    db.session.delete(player)
    db.session.commit()
    flash("Hráč byl úspěšně smazán", "success")
    return redirect(url_for("guests.index"))
