from modules.auth import auth_bp
from modules.auth.forms import LoginForm
from models import User, Notification
from werkzeug.security import check_password_hash
from flask import flash, redirect, url_for, render_template, request, jsonify, session
from models import db
from flask_login import login_user, logout_user, current_user, login_required


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('library.compositions'))
    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.email_or_username.data
        password = form.password.data
        remember = form.remember_me.data

        user = User.query.filter_by(email=identifier).first()

        if not user:
            user = User.query.filter_by(username=identifier).first()

        if user and check_password_hash(user.password_hash, password):
            if not user.active:
                flash("Účet je deaktivovaný.", "error")
                return redirect(url_for('auth.login'))

            login_user(user, remember=remember)
            flash('Úspěšně přihlášeno!', 'success')
            return redirect(url_for('library.compositions'))  # replace with your main page route
        else:
            flash('Nesprávné přihlašovací údaje.', 'error')

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
def logout():
    logout_user()
    session.clear()
    print(session)
    flash("Byl jste úspěšně odhlášen.", "success")
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/mark-read', methods=['POST'])
@login_required
def mark_read():
    notif_id = request.json.get('notif_id')
    notif = Notification.query.get(notif_id)
    if not notif or notif.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    notif.is_read = True
    db.session.commit()

    return jsonify({'status': 'success', 'notif_id': notif.id})
