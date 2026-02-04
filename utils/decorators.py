from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
from flask import abort


def roles_required(*roles):
    """
    Decorator to check if the current user has one of the required roles.
    If no roles are given, it does nothing special beyond login check.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Musíte se přihlásit.", "danger")
                return redirect(url_for("auth.login"))
            if roles and not current_user.has_any_role(roles):
                flash("Nemáte oprávnění pro přístup k této sekci.", "danger")
                return redirect(url_for("home"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.role or current_user.role.name != role_name:
                abort(403)
            return f(*args, **kwargs)

        # attach metadata for nav filtering
        f._required_role = role_name
        return decorated_function

    return decorator


def permission_required(permission_code, flash_message=True, redirect_home=True):
    """
    Decorator to ensure the current user has a given permission.
    Permissions are assigned to roles, and users have exactly one role.
    - `permission_code`: str, required permission code to access the route.
    - If the user is not authenticated → abort 401.
    - If the user lacks permission → abort 403 (or redirect if flash enabled).
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Not logged in → unauthorized
            if not current_user.is_authenticated:
                if redirect_home:
                    flash("Musíte se přihlásit.", "danger")
                    return redirect(url_for("auth.login"))
                abort(401)

            # Lacks permission → forbidden
            if not current_user.has_permission(permission_code):
                if flash_message and redirect_home:
                    flash("Nemáte oprávnění k této akci.", "danger")
                    return redirect(url_for("index"))
                abort(403)

            return f(*args, **kwargs)

        # Attach metadata for optional UI filtering (navigation etc.)
        f._required_permission = permission_code
        return decorated_function

    return decorator

import os
from functools import wraps
from flask import request, abort, current_app

def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("API_KEY") or os.getenv("API_KEY")
        if not expected:
            abort(500, description="API_KEY not configured")
        provided = request.headers.get("X-API-Key")
        if provided != expected:
            abort(401, description="Invalid API key")
        return fn(*args, **kwargs)
    return wrapper
