from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


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


def admin_required(f):
    return roles_required('admin')(f)
