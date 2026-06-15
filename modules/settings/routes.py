from flask import render_template, request, flash, redirect, url_for
from utils.nav import navlink
from modules.settings import settings_bp
from models import db, User, Role, Permission, Student, PasskeyCredential
from sqlalchemy.orm import joinedload
from flask import abort
from flask_login import current_user, login_required
from utils.decorators import role_required
from modules.settings.forms import UserEditForm


@settings_bp.route('/users', methods=["GET"])
@navlink("Uživatelé", weight=110, group="Nastavení", roles=["admin"])
@role_required("admin")
def users():
    users = User.query.all()
    return render_template('settings_users.html', users=users)


# --- Role list ---
@settings_bp.route("/roles")
@role_required("admin")
def roles():
    roles = Role.query.order_by(Role.name).all()
    return render_template("settings_roles.html", roles=roles)


@settings_bp.route("/role/<int:role_id>", methods=["GET", "POST"])
@role_required("admin")
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


@settings_bp.route("/user/<user_id>")
@role_required("admin")
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("settings_user_detail.html", user=user)


@settings_bp.route("/user/<user_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)
    form.role_id.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name).all()]

    # Students not already linked to another user (plus current user's student)
    linked_ids = {
        u.student_id for u in User.query.filter(
            User.student_id.isnot(None), User.id != user_id
        ).with_entities(User.student_id)
    }
    available_students = Student.query.filter(
        ~Student.id.in_(linked_ids)
    ).order_by(Student.last_name, Student.first_name).all()
    form.student_id.choices = [("", "— Žádný —")] + [
        (s.id, f"{s.full_name} ({s.osobni_cislo or s.id})") for s in available_students
    ]

    if form.validate_on_submit():
        user.role_id = form.role_id.data
        user.is_active = form.is_active.data
        user.student_id = form.student_id.data
        db.session.commit()
        flash("Uživatel byl úspěšně upraven.", "success")
        return redirect(url_for("settings.user_detail", user_id=user.id))

    return render_template("settings_user_edit.html", user=user, form=form)


@settings_bp.route("/passkeys")
@navlink("Passkeys", weight=115, group="Nastavení", roles=["admin"])
@role_required("admin")
def passkeys():
    passkeys = PasskeyCredential.query.filter_by(user_id=current_user.id).order_by(PasskeyCredential.created_at).all()
    return render_template("settings_passkeys.html", passkeys=passkeys)
