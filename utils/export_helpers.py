from weasyprint import HTML
from flask import make_response, render_template, current_app
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path


# ------------------------------
#   PDF RENDERING
# ------------------------------
def render_pdf(template_name, context, filename_prefix):
    """
    Render a WeasyPrint PDF with shared layout and metadata.
    Ensures consistent logo, date, time, and filename.
    """
    # --- logo and metadata ---
    logo_path = Path(current_app.static_folder) / "images" / "hamu_logo.png"
    logo_url = logo_path.resolve().as_uri()

    context.setdefault("logo_url", logo_url)

    # --- timestamp (Europe/Prague) ---
    tz = ZoneInfo("Europe/Prague")
    now = datetime.now(tz)
    context.setdefault("today", now.date())

    # --- render PDF ---
    html = render_template(template_name, **context)
    pdf = HTML(string=html, base_url=str(Path(current_app.root_path).resolve())).write_pdf()

    # --- response setup ---
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"

    # Include date + time in filename, RFC 5987 encoded
    filename = f"{filename_prefix}_{now:%Y%m%d_%H%M}.pdf"
    response.headers["Content-Disposition"] = (
        f"attachment; filename={filename}; filename*=UTF-8''{filename}"
    )

    return response
