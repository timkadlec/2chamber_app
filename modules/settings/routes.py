from flask import render_template, request, flash, redirect, url_for, jsonify
from utils.nav import navlink
from modules.settings import settings_bp


@settings_bp.route('/settings')
@navlink("Nastavení", weight=110, group="Nastavení")
def settings():
    return render_template("settings_base.html")
