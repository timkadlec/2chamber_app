from flask import render_template, request, flash, redirect, url_for, jsonify
from utils.nav import navlink
from modules.settings import settings_bp
from models import db, User, Role, Permission
from sqlalchemy.orm import joinedload
from flask import abort
from utils.decorators import role_required


@settings_bp.route('/users', methods=["GET"])
@navlink("Uživatelé", weight=110, group="Nastavení", roles=["admin"])
@role_required("admin")
def users():
    users = User.query.all()
    return render_template('settings_users.html', users=users)


# --- Role list ---
@settings_bp.route("/roles")
def roles():
    roles = Role.query.order_by(Role.name).all()
    return render_template("settings_roles.html", roles=roles)


@settings_bp.route("/role/<int:role_id>", methods=["GET", "POST"])
def role_detail(role_id):
    role = Role.query.options(joinedload(Role.permissions)).get(role_id)
    if not role:
        abort(404)

    # --- POST: save updated permissions ---
    if request.method == "POST":
        selected_codes = request.form.getlist("permissions")

        # Fetch all Permission objects by their code
        new_permissions = Permission.query.filter(Permission.code.in_(selected_codes)).all()

        # Update role permissions
        role.permissions = new_permissions
        db.session.commit()

        flash("Oprávnění role byla úspěšně aktualizována.", "success")
        return redirect(url_for("settings.role_detail", role_id=role.id))

    # --- GET: show grouped permissions ---
    permissions = Permission.query.order_by(Permission.category, Permission.code).all()

    grouped = {}
    for perm in permissions:
        category = perm.category or "Ostatní"
        grouped.setdefault(category, []).append({
            "id": perm.id,
            "code": perm.code,
            "name": perm.name or perm.code,
            "description": perm.description or "",
            "granted": any(p.id == perm.id for p in role.permissions),
        })

    return render_template(
        "settings_role_detail.html",
        role=role,
        permissions_grouped=grouped
    )
