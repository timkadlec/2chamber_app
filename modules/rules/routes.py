from flask import render_template, request, flash, redirect, url_for, jsonify
from utils.nav import navlink
from modules.rules import rules_bp


@rules_bp.route('/')
@navlink("Pravidla")
def index():
    return render_template("rules.html")
