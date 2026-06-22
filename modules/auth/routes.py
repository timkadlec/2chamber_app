from flask import Blueprint, session, url_for, redirect, flash, request, current_app, render_template, abort, jsonify
from sqlalchemy import func
from flask_login import login_user, logout_user, login_required
from datetime import datetime
from models import db, User, Student, Teacher, PasskeyCredential
from app import oauth
import os
import base64
import webauthn
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
)
from webauthn.helpers.exceptions import InvalidCBORData, InvalidAuthenticatorDataStructure
from flask_login import current_user
from extensions import csrf
from . import auth_bp
from urllib.parse import urlparse, urljoin

TENANT = os.environ.get("OAUTH_TENANT_ID")
AUTH_BASE = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0"


def _find_teacher_by_email(email: str):
    """Match a Teacher whose constructed email (first.last@hamu.cz) equals the given address."""
    if not email:
        return None
    email_expr = (
        func.lower(Teacher.first_name) + "." +
        func.lower(Teacher.last_name) + "@hamu.cz"
    )
    return Teacher.query.filter(email_expr == email.lower()).first()


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
        if user.portal_type == "teacher":
            return redirect(url_for("teacher_portal.dashboard"))
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
        db.session.commit()

        # Try to auto-link if not yet linked to any portal
        if not user.student_id and not user.teacher_id and email:
            student = Student.query.filter_by(email=email).first()
            if student and not User.query.filter(User.student_id == student.id, User.id != user.id).first():
                user.student_id = student.id
                db.session.commit()
            else:
                teacher = _find_teacher_by_email(email)
                if teacher and not User.query.filter(User.teacher_id == teacher.id, User.id != user.id).first():
                    user.teacher_id = teacher.id
                    db.session.commit()
    else:
        # New user — must match a student or teacher, otherwise deny access
        matched_student = None
        matched_teacher = None
        if email:
            matched_student = Student.query.filter_by(email=email).first()
            if not matched_student:
                matched_teacher = _find_teacher_by_email(email)

        if not matched_student and not matched_teacher:
            flash("Přístup zamítnut: Váš účet nebyl nalezen v systému.", "danger")
            return redirect(url_for("auth.login"))

        user = User(
            oid=oid,
            tid=tid,
            display_name=name,
            email=email,
            upn=upn,
            last_login_at=datetime.utcnow(),
        )
        if matched_student:
            user.student_id = matched_student.id
        else:
            user.teacher_id = matched_teacher.id
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
    if user.portal_type == "teacher":
        return redirect(url_for("teacher_portal.dashboard"))
    return redirect(url_for("index"))


@auth_bp.route("/logout")
def logout():
    logout_user()  # let Flask-Login handle session + remember cookie
    post_logout = url_for("library.composers", _external=True)
    return redirect(f"{AUTH_BASE}/logout?post_logout_redirect_uri={post_logout}")


# ---------------------------------------------------------------------------
# Passkey (WebAuthn) – login flow
# ---------------------------------------------------------------------------

@auth_bp.route("/passkey-login")
def passkey_login():
    return render_template("passkey_login.html")


@auth_bp.route("/passkey/login/begin", methods=["POST"])
@csrf.exempt
def passkey_login_begin():
    rp_id = current_app.config["WEBAUTHN_RP_ID"]
    options = webauthn.generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=[],
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    session["webauthn_auth_challenge"] = base64.b64encode(options.challenge).decode()
    return current_app.response_class(
        webauthn.options_to_json(options),
        mimetype="application/json",
    )


@auth_bp.route("/passkey/login/complete", methods=["POST"])
@csrf.exempt
def passkey_login_complete():
    raw_challenge = session.pop("webauthn_auth_challenge", None)
    if not raw_challenge:
        return jsonify({"ok": False, "error": "No challenge in session"}), 400

    expected_challenge = base64.b64decode(raw_challenge)
    rp_id = current_app.config["WEBAUTHN_RP_ID"]
    expected_origin = current_app.config["WEBAUTHN_ORIGIN"]

    try:
        credential = webauthn.helpers.parse_authentication_credential_json(request.get_data(as_text=True))
    except Exception as e:
        return jsonify({"ok": False, "error": f"Parse error: {e}"}), 400

    stored = PasskeyCredential.query.filter_by(credential_id=credential.raw_id).first()
    if not stored:
        return jsonify({"ok": False, "error": "Unknown credential"}), 403

    try:
        verification = webauthn.verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp_id,
            expected_origin=expected_origin,
            credential_public_key=stored.public_key,
            credential_current_sign_count=stored.sign_count,
            require_user_verification=True,
        )
    except Exception as e:
        return jsonify({"ok": False, "error": f"Verification failed: {e}"}), 403

    stored.sign_count = verification.new_sign_count
    stored.user.last_login_at = datetime.utcnow()
    db.session.commit()

    login_user(stored.user, remember=True)
    session["user"] = {
        "name": stored.user.display_name,
        "oid": stored.user.oid,
        "preferred_username": stored.user.upn,
    }
    return jsonify({"ok": True, "redirect": url_for("index")})


# ---------------------------------------------------------------------------
# Passkey (WebAuthn) – registration (admin only, must be logged in)
# ---------------------------------------------------------------------------

@auth_bp.route("/passkey/register/begin", methods=["POST"])
@login_required
@csrf.exempt
def passkey_register_begin():
    if not current_user.has_role("admin"):
        return jsonify({"ok": False, "error": "Admin only"}), 403

    rp_id = current_app.config["WEBAUTHN_RP_ID"]
    rp_name = current_app.config["WEBAUTHN_RP_NAME"]

    existing = [
        webauthn.helpers.structs.PublicKeyCredentialDescriptor(id=c.credential_id)
        for c in current_user.passkey_credentials
    ]

    options = webauthn.generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=current_user.id.encode(),
        user_name=current_user.email or current_user.display_name,
        user_display_name=current_user.display_name or current_user.email,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=existing,
    )
    session["webauthn_reg_challenge"] = base64.b64encode(options.challenge).decode()
    return current_app.response_class(
        webauthn.options_to_json(options),
        mimetype="application/json",
    )


@auth_bp.route("/passkey/register/complete", methods=["POST"])
@login_required
@csrf.exempt
def passkey_register_complete():
    if not current_user.has_role("admin"):
        return jsonify({"ok": False, "error": "Admin only"}), 403

    raw_challenge = session.pop("webauthn_reg_challenge", None)
    if not raw_challenge:
        return jsonify({"ok": False, "error": "No challenge in session"}), 400

    expected_challenge = base64.b64decode(raw_challenge)
    rp_id = current_app.config["WEBAUTHN_RP_ID"]
    expected_origin = current_app.config["WEBAUTHN_ORIGIN"]

    body = request.get_data(as_text=True)
    try:
        credential = webauthn.helpers.parse_registration_credential_json(body)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Parse error: {e}"}), 400

    try:
        verification = webauthn.verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp_id,
            expected_origin=expected_origin,
            require_user_verification=True,
        )
    except Exception as e:
        return jsonify({"ok": False, "error": f"Verification failed: {e}"}), 400

    name = request.args.get("name") or "Passkey"
    passkey = PasskeyCredential(
        user_id=current_user.id,
        credential_id=verification.credential_id,
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
        name=name,
    )
    db.session.add(passkey)
    db.session.commit()
    return jsonify({"ok": True})


@auth_bp.route("/passkey/delete/<int:cred_id>", methods=["POST"])
@login_required
def passkey_delete(cred_id):
    if not current_user.has_role("admin"):
        abort(403)
    cred = PasskeyCredential.query.filter_by(id=cred_id, user_id=current_user.id).first_or_404()
    db.session.delete(cred)
    db.session.commit()
    flash("Passkey byl odstraněn.", "success")
    return redirect(url_for("settings.passkeys"))
