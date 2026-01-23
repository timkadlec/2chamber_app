import os
import logging
from logging.handlers import RotatingFileHandler
from flask import got_request_exception


def configure_logging(app):
    """
    Dev -> console
    Prod -> rotating file
    Also logs unhandled exceptions via got_request_exception.
    """

    # Prevent duplicate handlers when app is created multiple times
    app.logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    if app.debug:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)

        app.logger.addHandler(handler)

        werkzeug_logger = logging.getLogger("werkzeug")
        werkzeug_logger.handlers.clear()
        werkzeug_logger.addHandler(handler)

        app.logger.setLevel(logging.DEBUG)
        werkzeug_logger.setLevel(logging.DEBUG)

    else:
        logs_dir = os.environ.get(
            "LOG_DIR",
            os.path.join(os.path.dirname(app.root_path), "logs")
        )
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, "app.log")

        handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=10)
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)

        app.logger.addHandler(handler)

        werkzeug_logger = logging.getLogger("werkzeug")
        werkzeug_logger.addHandler(handler)

        app.logger.setLevel(logging.INFO)
        werkzeug_logger.setLevel(logging.INFO)

    app.logger.info("✅ Application startup complete.")

    def log_exception(sender, exception, **extra):
        sender.logger.exception("Unhandled Exception: %s", exception)

    got_request_exception.connect(log_exception, app)
