import traceback
from flask import render_template, got_request_exception


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html", error=error), 403

    # Capture full traceback for later use
    last_traceback = {"text": None}

    def capture_exception(sender, exception, **extra):
        last_traceback["text"] = traceback.format_exc()

    got_request_exception.connect(capture_exception, app)

    @app.errorhandler(500)
    def internal_error(error):
        tb = last_traceback.get("text")
        app.logger.error(f"Internal Server Error: {tb}")
        return render_template("errors/500.html", error=error, traceback=tb), 500
