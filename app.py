from cli import (
    cli_format_academic_year,
    cli_get_or_create_academic_year,
    cli_oracle_ping,
    cli_get_or_create_semester,
    cli_get_or_create_subject,
    cli_oracle_students_update,
    cli_oracle_semesters,
    cli_oracle_teachers
)
from flask import Flask, url_for, request, redirect, render_template, session
from config import ProductionConfig
from models import db, User
import os
import oracledb
from utils.session_helpers import get_or_set_current_semester, get_or_set_current_semester_id
from extensions import login_manager, oauth, migrate
from modules.library import library_bp
from modules.auth import auth_bp
from modules.settings import settings_bp
from modules.students import students_bp
from modules.ui import ui_bp
from modules.ensembles import ensemble_bp
from modules.subject import subject_bp
from modules.guests import guest_bp
from modules.chamber_applications import chamber_applications_bp
from modules.teachers import teachers_bp
from modules.exceptions import exceptions_bp
from modules.rules import rules_bp
from collections import defaultdict
from utils.error_handlers import register_error_handlers
from sqlalchemy.orm import selectinload
from sqlalchemy import func, select, exists, case  # <-- needed
from models import AcademicYear, Semester
from utils.dashboard_helper import get_dashboard_data
from models import (
    Ensemble, EnsembleSemester, EnsembleTeacher, EnsembleInstrumentation,
    EnsemblePlayer, Player, Teacher, Instrument
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
    app.register_blueprint(guest_bp, url_prefix="/guests")
    app.register_blueprint(chamber_applications_bp, url_prefix="/chamber_applications")
    app.register_blueprint(teachers_bp, url_prefix="/teachers")
    app.register_blueprint(exceptions_bp, url_prefix="/exceptions")
    app.register_blueprint(rules_bp, url_prefix="/rules")

    app.cli.add_command(cli_format_academic_year)
    app.cli.add_command(cli_get_or_create_academic_year)
    app.cli.add_command(cli_oracle_ping)
    app.cli.add_command(cli_get_or_create_semester)
    app.cli.add_command(cli_get_or_create_subject)
    app.cli.add_command(cli_oracle_students_update)
    app.cli.add_command(cli_oracle_semesters)
    app.cli.add_command(cli_oracle_teachers)
    with app.app_context():
        db.create_all(bind_key=None)
        # seed_instruments()
        # seed_chamber_application_statuses()
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

    from datetime import datetime, timedelta
    from flask import request, session, redirect, url_for
    from flask_login import current_user

    SESSION_TIMEOUT_MINUTES = 60  # 1 hour inactivity timeout

    # -----------------------------------------------------
    # 1. Require login for all web routes (except auth/static)
    # -----------------------------------------------------
    @app.before_request
    def restrict_web_only_to_logged_in():
        endpoint = request.endpoint
        if not endpoint:
            return  # ignore favicon.ico, 404s, etc.

        # Allow static files and auth routes
        if request.blueprint == "auth" or endpoint.startswith("static"):
            return

        # Enforce login
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))

    # -----------------------------------------------------
    # 2. Auto-logout after inactivity
    # -----------------------------------------------------
    @app.before_request
    def enforce_session_timeout():
        endpoint = request.endpoint
        if not endpoint:
            return

        # Skip auth & static routes to avoid recursion
        if endpoint in ("auth.login", "auth.logout") or endpoint.startswith("static"):
            return

        now = datetime.utcnow()
        last_activity = session.get("last_activity")

        if last_activity:
            try:
                last_activity = datetime.fromisoformat(last_activity)
            except ValueError:
                # corrupted or old format
                last_activity = now

            if now - last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
                app.logger.info(
                    f"Session expired for user {current_user.get_id() if current_user.is_authenticated else 'anonymous'}"
                )
                session.clear()
                return redirect(url_for("auth.logout"))

        # Update last activity timestamp
        session["last_activity"] = now.isoformat()

    @app.context_processor
    def inject_nav_links():
        groups = defaultdict(list)
        flat_links = []

        for rule in app.url_map.iter_rules():
            view_func = app.view_functions[rule.endpoint]

            if hasattr(view_func, "_nav_title"):
                # --- Permission-based filtering ---
                required_permission = getattr(view_func, "_nav_permission", None)
                if required_permission and (
                        not current_user.is_authenticated or not current_user.has_permission(required_permission)
                ):
                    continue  # skip if no permission

                # --- Role-based filtering ---
                required_roles = getattr(view_func, "_nav_roles", None)
                if required_roles and (
                        not current_user.is_authenticated or not current_user.has_any_role(required_roles)
                ):
                    continue  # skip if role mismatch

                entry = {
                    "name": view_func._nav_title,
                    "url": url_for(rule.endpoint),
                    "weight": getattr(view_func, "_nav_weight", 100),
                }

                group = getattr(view_func, "_nav_group", None)
                if group:
                    groups[group].append(entry)
                else:
                    flat_links.append(entry)

        # --- Grouped nav entries ---
        nav_links = []
        for group_name, children in groups.items():
            nav_links.append({
                "name": group_name,
                "url": "#",
                "weight": min(child["weight"] for child in children),
                "children": sorted(children, key=lambda x: x["weight"]),
            })

        # --- Flat links ---
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
        current = get_or_set_current_semester()

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

    @app.context_processor
    def inject_permissions():
        return dict(
            has_permission=lambda code: (
                    current_user.is_authenticated and current_user.has_permission(code)
            )
        )

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    @app.route("/")
    def index():
        current_sem = get_or_set_current_semester_id()
        data = get_dashboard_data(current_sem)
        return render_template("dashboard.html", **data)

    # ------------------------------
    # LOGGING CONFIGURATION
    # ------------------------------
    import logging
    from logging.handlers import RotatingFileHandler
    from flask import got_request_exception

    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "app.log")

    # Log rotation: keeps last 10 logs of up to 1 MB
    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=10)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Set level (INFO in production, DEBUG for development)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    # Also send Flask's own logs to this handler
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info("✅ Application startup complete.")

    # Capture *all* unhandled exceptions and log them
    def log_exception(sender, exception, **extra):
        sender.logger.exception("Unhandled Exception: %s", exception)

    got_request_exception.connect(log_exception, app)

    return app
