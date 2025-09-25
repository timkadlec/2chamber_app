from flask import Flask, url_for, request, redirect, g
from flask_migrate import Migrate
from config import ProductionConfig
from models import db, User, Student, KomorniHraStud
import locale
from db_core_entries import seed_instruments, seed_composers, seed_basic_compositions
import os
import oracledb
from extensions import login_manager, oauth, migrate
from flask_login import current_user
from modules.library import library_bp
from modules.auth import auth_bp
from modules.settings import settings_bp
from modules.students import students_bp
from modules.ui import ui_bp
from modules.ensembles import ensemble_bp
from modules.subject import subject_bp
from collections import defaultdict
from utils.error_handlers import register_error_handlers
from flask import session
from sqlalchemy.orm import selectinload
from models import AcademicYear, Semester
from cli import (
    cli_format_academic_year,
    cli_get_or_create_academic_year,
    cli_oracle_ping,
    cli_get_or_create_semester,
    cli_get_or_create_subject,
    cli_oracle_students_update
)


def create_app():
    app = Flask(__name__)

    config_class = ProductionConfig
    app.config.from_object(config_class)

    db.init_app(app)
    oracledb.init_oracle_client(lib_dir=os.environ.get("ORACLE_DRIVER"))
    migrate.init_app(app, db)
    oauth.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    app.register_blueprint(library_bp, url_prefix="/library")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    app.register_blueprint(students_bp, url_prefix="/students")
    app.register_blueprint(ui_bp, url_prefix="/ui")
    app.register_blueprint(ensemble_bp, url_prefix="/ensembles")
    app.register_blueprint(subject_bp, url_prefix="/subjects")

    app.cli.add_command(cli_format_academic_year)
    app.cli.add_command(cli_get_or_create_academic_year)
    app.cli.add_command(cli_oracle_ping)
    app.cli.add_command(cli_get_or_create_semester)
    app.cli.add_command(cli_get_or_create_subject)
    app.cli.add_command(cli_oracle_students_update)

    with app.app_context():
        db.create_all(bind_key=None)
        seed_instruments()
        # seed_roles_and_admin()
        # seed_composers()
        # seed_basic_compositions()
        # seed_mock_notification()
        register_error_handlers(app)

    def is_allowed(link):
        if not hasattr(link, "_nav_roles") or link._nav_roles is None:
            return True
        if not current_user.is_authenticated:
            return False
        return current_user.role and current_user.role.name in link._nav_roles

    @app.before_request
    def restrict_web_only_to_logged_in():
        # Allow static and auth routes to be accessed without login
        if request.endpoint is None:
            return

        if request.blueprint == "auth" or request.endpoint.startswith("static"):
            return

        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))

    @app.context_processor
    def inject_nav_links():
        groups = defaultdict(list)
        flat_links = []

        for rule in app.url_map.iter_rules():
            view_func = app.view_functions[rule.endpoint]

            if hasattr(view_func, "_nav_title") and is_allowed(view_func):
                entry = {
                    "name": view_func._nav_title,
                    "url": url_for(rule.endpoint),
                    "weight": getattr(view_func, "_nav_weight", 100)
                }

                group = getattr(view_func, "_nav_group", None)
                if group:
                    groups[group].append(entry)
                else:
                    flat_links.append(entry)

        nav_links = []

        for group_name, children in groups.items():
            nav_links.append({
                "name": group_name,
                "url": "#",
                "weight": min(child["weight"] for child in children),  # For sorting parent
                "children": sorted(children, key=lambda x: x["weight"])
            })

        nav_links += flat_links
        nav_links = sorted(nav_links, key=lambda x: x["weight"])

        return {"nav_links": nav_links}

    TENANT = os.environ["OAUTH_TENANT_ID"]
    SCOPES = os.environ.get("OAUTH_SCOPES", "openid profile email")
    oauth.register(
        name="entra",
        client_id=os.environ["OAUTH_CLIENT_ID"],
        client_secret=os.environ["OAUTH_CLIENT_SECRET"],
        server_metadata_url=f"https://login.microsoftonline.com/{TENANT}/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": SCOPES},
    )

    @app.context_processor
    def inject_semester_context():
        current = None
        if (sid := session.get('semester_id')):
            current = Semester.query.get(sid)

        if not current:
            # fallback if table empty or session value stale
            current = (
                Semester.query
                .order_by(Semester.start_date.desc())
                .first()
            )
            if current:
                # >>> TADY nastavíme defaultní semestr do session
                session['semester_id'] = current.id

        years = (
            AcademicYear.query
            .options(selectinload(AcademicYear.semesters))
            .order_by(AcademicYear.start_date.desc())
            .all()
        )

        return dict(
            current_semester=current,
            semester_id=current.id if current else None,
            academic_years=years
        )

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    return app
