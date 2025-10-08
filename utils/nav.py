from functools import wraps
from flask import flash, abort, redirect, url_for, request, render_template
from flask_login import current_user


def navlink(title, weight=100, roles=None, group=None, permission=None):
    """
    Register a route for navigation and optionally enforce permission/roles.
    - title: name shown in navbar
    - weight: sorting order
    - roles: optional roles list
    - group: optional group name in navbar
    - permission: optional permission code
    """

    def decorator(f):
        # attach navigation metadata
        f._nav_title = title
        f._nav_weight = weight
        f._nav_roles = roles
        f._nav_group = group
        f._nav_permission = permission

        @wraps(f)
        def wrapper(*args, **kwargs):
            # ---- PERMISSION CHECK ----
            if permission:
                if not current_user.is_authenticated:
                    flash("Musíte se přihlásit.", "danger")
                    return redirect(url_for("auth.login", next=request.url))
                if not current_user.has_permission(permission):
                    abort(403)

            # ---- ROLE CHECK ----
            if roles:
                if not current_user.is_authenticated or not current_user.has_any_role(roles):
                    abort(403)

            return f(*args, **kwargs)

        return wrapper

    return decorator
