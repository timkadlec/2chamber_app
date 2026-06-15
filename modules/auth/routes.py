from flask import Blueprint, session, url_for, redirect, flash, request, current_app, render_template, abort
from flask_login import login_user, logout_user, login_required
from datetime import datetime
from models import db, User
from app import oauth
import os
from flask_login import current_user
from . import auth_bp
from urllib.parse import urlparse, urljoin

TENANT = os.environ.get("OAUTH_TENANT_ID")
AUTH_BASE = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0"


@auth_bp.route("/login")
def login():
    if current_app.config.get("DEV_LOGIN"):
        return redirect(url_for("auth.dev_login"))
    return oauth.entra.authorize_redirect(
        redirect_uri=url_for("auth.auth_callback", _external=True)
    )


@auth_bp.route("/dev-login", methods=["GET", "POST"])
def dev_login():
    if not current_app.config.get("DEV_LOGIN"):
        abort(404)

    users = User.query.order_by(User.display_name).all()

    if request.method == "POST":
        user_id = request.form.get("user_id")
        user = User.query.get_or_404(user_id)
        login_user(user, remember=True)
        session["user"] = {
            "name": user.display_name,
            "oid": user.oid,
            "preferred_username": user.upn,
        }
        if user.portal_type == "student":
            return redirect(url_for("student_portal.dashboard"))
        return redirect(url_for("index"))

    return render_template("dev_login.html", users=users)


def is_safe_url(target):
    # Prevent open redirect attacks — only allow local URLs
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@auth_bp.route("/callback")
def auth_callback():
    token = oauth.entra.authorize_access_token()

    claims = token.get("id_token_claims") or token.get("userinfo") or {}

    oid = claims.get("oid") or claims.get("sub")
    tid = claims.get("tid")
    name = claims.get("name")
    upn = claims.get("preferred_username") or claims.get("email")
    email = claims.get("email") or upn

    current_app.logger.info(
        "🧍 Extracted user info: oid=%s tid=%s name=%s upn=%s email=%s",
        oid, tid, name, upn, email
    )

    if not oid or not tid:
        flash("Přihlášení selhalo: chyba oid/tid.", "danger")
        return redirect(url_for("ensemble.index"))

    user = User.query.filter_by(oid=oid).first()
    if user:
        user.display_name = name or user.display_name
        user.email = email or user.email
        user.upn = upn or user.upn
        user.last_login_at = datetime.utcnow()
    else:
        user = User(
            oid=oid,
            tid=tid,
            display_name=name,
            email=email,
            upn=upn,
            last_login_at=datetime.utcnow(),
            role_id=4, # by default assign viewer role
        )
        db.session.add(user)

    db.session.commit()

    login_user(user, remember=True)

    session["user"] = {
        "name": user.display_name,
        "oid": user.oid,
        "preferred_username": user.upn,
    }

    flash("Úspěšně přihlášený.", "success")
    if user.portal_type == "student":
        return redirect(url_for("student_portal.dashboard"))
    return redirect(url_for("index"))


@auth_bp.route("/logout")
def logout():
    logout_user()  # let Flask-Login handle session + remember cookie
    post_logout = url_for("library.composers", _external=True)
    return redirect(f"{AUTH_BASE}/logout?post_logout_redirect_uri={post_logout}")
