from flask import Blueprint, session, url_for, redirect, flash, request, current_app, render_template, abort, jsonify
from sqlalchemy import func
from flask_login import login_user, logout_user, login_required
from datetime import datetime
from models import db, User, Student, Teacher, PasskeyCredential
from models.auth import Role
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

# Roles that only grant portal access — not management-app access
PORTAL_ONLY_ROLES = {"viewer", "student", "teacher"}


def _auto_link_portal(user, email: str) -> bool:
    """
    On every login:
    1. Try to link the user to a student/teacher record if not already linked.
    2. If the user is currently viewer (or has no role), upgrade to the matching
       portal role ("student" / "teacher").  Management roles are never touched.
    Returns True if anything was changed (so the caller knows to commit).
    """
    if not email:
        return False

    changed = False
    current_role = user.role.name if user.role else None

    if not user.student_id:
        student = Student.query.filter_by(email=email).first()
        if student and not User.query.filter(User.student_id == student.id, User.id != user.id).first():
            user.student_id = student.id
            changed = True

    if not user.teacher_id:
        teacher = _find_teacher_by_email(email)
        if teacher and not User.query.filter(User.teacher_id == teacher.id, User.id != user.id).first():
            user.teacher_id = teacher.id
            changed = True

    # Role upgrade runs on every login — not just when a link was just found.
    # This catches users who were linked before the portal roles were seeded.
    # Management roles (creator, reviewer, admin, …) are never downgraded.
    if current_role in (None, "viewer"):
        target_name = "teacher" if user.teacher_id else ("student" if user.student_id else None)
        if target_name:
            role = Role.query.filter_by(name=target_name).first()
            if role and user.role_id != role.id:
                user.role_id = role.id
                changed = True

    return changed


def _find_teacher_by_email(email: str):
    """
    Match a Teacher whose email equals the given address.
    Checks the manual Teacher.email override first, then falls back to the
    constructed formula (unaccent strips diacritics so e.g. 'Štěpán JEŽEK'
    → 'stepan.jezek@hamu.cz').
    """
    if not email:
        return None
    email_lower = email.lower()

    # Manual override takes priority (handles edge cases like name collisions)
    teacher = Teacher.query.filter(
        func.lower(Teacher.email) == email_lower
    ).first()
    if teacher:
        return teacher

    # Constructed formula: firstname.lastname@hamu.cz with diacritics stripped
    email_expr = (
        func.unaccent(func.lower(Teacher.first_name)) + "." +
        func.unaccent(func.lower(Teacher.last_name)) + "@hamu.cz"
    )
    return Teacher.query.filter(email_expr == email_lower).first()


def _post_login_url(user):
    """
    Return the URL the user should be sent to after login, or None if access is denied.

    Role logic:
      "student"           → student portal (denied if no active student link)
      "teacher"           → teacher portal (denied if no teacher link)
      management role     → landing if they also have a portal, otherwise index
      "viewer" / no role  → portal if one exists, otherwise denied
    """
    role_name = user.role.name if user.role else None
    student_active = bool(user.student_id and user.student and user.student.active)
    teacher_linked = bool(user.teacher_id and user.teacher)

    if role_name == "student":
        return url_for("student_portal.dashboard") if student_active else None

    if role_name == "teacher":
        return url_for("teacher_portal.dashboard") if teacher_linked else None

    has_mgmt_role = bool(role_name and role_name not in PORTAL_ONLY_ROLES)
    if has_mgmt_role:
        if teacher_linked or student_active:
            return url_for("auth.landing")
        return url_for("index")

    # viewer / no role — route to portal if one exists
    if student_active:
        return url_for("student_portal.dashboard")
    if teacher_linked:
        return url_for("teacher_portal.dashboard")

    # viewer with no portal link = administration worker, let them into the app
    if role_name == "viewer":
        return url_for("index")

    return None  # no role at all → deny


def _redirect_after_login(user):
    """Redirect the user to the right destination, or deny and log them out."""
    destination = _post_login_url(user)
    if destination:
        return redirect(destination)

    flash("Přístup zamítnut: Váš účet není aktivní nebo nebyl nalezen v systému.", "danger")
    logout_user()
    return redirect(url_for("auth.login"))


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
        if _auto_link_portal(user, user.email):
            db.session.commit()
        login_user(user, remember=True)
        session["user"] = {
            "name": user.display_name,
            "oid": user.oid,
            "preferred_username": user.upn,
        }
        return _redirect_after_login(user)

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
        if _auto_link_portal(user, email):
            pass  # changes will be committed below
        db.session.commit()
    else:
        # New user — must match a student or teacher, otherwise deny access
        user = User(
            oid=oid,
            tid=tid,
            display_name=name,
            email=email,
            upn=upn,
            last_login_at=datetime.utcnow(),
        )
        db.session.add(user)
        _auto_link_portal(user, email)

        if not user.student_id and not user.teacher_id:
            db.session.rollback()
            flash("Přístup zamítnut: Váš účet nebyl nalezen v systému.", "danger")
            return redirect(url_for("auth.login"))

        db.session.commit()

    login_user(user, remember=True)

    session["user"] = {
        "name": user.display_name,
        "oid": user.oid,
        "preferred_username": user.upn,
    }

    flash("Úspěšně přihlášený.", "success")
    return _redirect_after_login(user)


@auth_bp.route("/landing")
@login_required
def landing():
    role_name = current_user.role.name if current_user.role else None
    if not role_name or role_name in PORTAL_ONLY_ROLES:
        return _redirect_after_login(current_user)
    return render_template("landing.html")


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

    user = stored.user
    stored.sign_count = verification.new_sign_count
    user.last_login_at = datetime.utcnow()
    _auto_link_portal(user, user.email)
    db.session.commit()

    login_user(user, remember=True)
    session["user"] = {
        "name": user.display_name,
        "oid": user.oid,
        "preferred_username": user.upn,
    }
    return jsonify({"ok": True, "redirect": _post_login_url(user) or url_for("auth.login")})


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
