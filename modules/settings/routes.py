from flask import render_template, request, flash, redirect, url_for, jsonify
from utils.nav import navlink
from modules.settings import settings_bp
from models import db, User
from utils.decorators import role_required


@settings_bp.route('/users', methods=["GET"])
@navlink("Uživatelé", weight=110, group="Nastavení", roles=["admin"])
@role_required("admin")
def users():
    users = User.query.all()
    return render_template('settings_users.html', users=users)
