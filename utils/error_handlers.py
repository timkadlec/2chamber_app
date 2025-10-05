from flask import render_template

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(500)
    def internal_error(error):
        # You can also log the error here if needed
        app.logger.exception("Internal Server Error: %s", error)
        return render_template("errors/500.html", error=error), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html", error=error), 403
