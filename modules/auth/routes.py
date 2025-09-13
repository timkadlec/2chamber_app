from flask import Blueprint, session, url_for, redirect, flash, request
from flask_login import login_user, logout_user, login_required
from datetime import datetime
from models import db, User
from app import oauth
import os
from flask import jsonify
from flask_login import current_user
from . import auth_bp
from urllib.parse import urlparse, urljoin
from flask import request, current_app
import json

TENANT = os.environ["OAUTH_TENANT_ID"]
AUTH_BASE = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0"


@auth_bp.route("/login")
def login():
    return oauth.entra.authorize_redirect(
        redirect_uri=url_for("auth.auth_callback", _external=True)
    )


def is_safe_url(target):
    # Prevent open redirect attacks — only allow local URLs
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc



@auth_bp.route("/callback")
def auth_callback():
    current_app.logger.info("⚡ auth_callback hit")

    # Get token from Entra
    token = oauth.entra.authorize_access_token()
    current_app.logger.info("🔑 Raw token: %s", json.dumps(token, indent=2))

    # Extract claims
    claims = token.get("id_token_claims") or token.get("userinfo") or {}
    current_app.logger.info("📋 Claims: %s", json.dumps(claims, indent=2))

    oid = claims.get("oid") or claims.get("sub")
    tid = claims.get("tid")
    name = claims.get("name")
    upn = claims.get("preferred_username") or claims.get("email")
    email = claims.get("email") or upn

    current_app.logger.info(
        "🧍 Extracted user info: oid=%s tid=%s name=%s upn=%s email=%s",
        oid, tid, name, upn, email
    )

    # Error if no oid/tid
    if not oid or not tid:
        current_app.logger.warning("❌ Missing oid or tid, login failed")
        flash("Přihlášení selhalo: chyba oid/tid.", "danger")
        return redirect(url_for("ensembles.all_ensembles"))

    # Find or create user
    user = User.query.filter_by(oid=oid).first()
    if user:
        current_app.logger.info("✅ Existing user found: %s", user.id)
        user.display_name = name or user.display_name
        user.email = email or user.email
        user.upn = upn or user.upn
        user.last_login_at = datetime.utcnow()
    else:
        current_app.logger.info("🆕 Creating new user")
        user = User(
            oid=oid,
            tid=tid,
            display_name=name,
            email=email,
            upn=upn,
            last_login_at=datetime.utcnow(),
        )
        db.session.add(user)

    db.session.commit()
    current_app.logger.info("💾 User saved to DB: id=%s", user.id)

    login_user(user, remember=True)
    current_app.logger.info("🔓 User logged in with Flask-Login")

    session["user"] = {
        "name": user.display_name,
        "oid": user.oid,
        "preferred_username": user.upn,
    }
    current_app.logger.info("💼 Session user set: %s", session["user"])

    flash("Úspěšně přihlášený.", "success")
    return redirect(url_for("ensembles.all_ensembles"))


@auth_bp.route("/logout")
def logout():
    logout_user()  # let Flask-Login handle session + remember cookie
    post_logout = url_for("index", _external=True)
    return redirect(f"{AUTH_BASE}/logout?post_logout_redirect_uri={post_logout}")

