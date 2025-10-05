import traceback
from flask import render_template

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(500)
    def internal_error(error):
        # Log full traceback to console / log file
        app.logger.exception("Internal Server Error")

        # Build detailed info for template
        tb = traceback.format_exc()
        return render_template(
            "errors/500.html",
            error=error,
            traceback=tb
        ), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html", error=error), 403
