from flask import render_template, request, flash, redirect, url_for, session, request
from utils.nav import navlink
from models import Student, StudentSubjectEnrollment, Instrument, Subject, Player
from modules.players import players_bp
from sqlalchemy import and_

from sqlalchemy import or_


@players_bp.route("/", methods=["GET"])
@navlink("Hráči")
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
