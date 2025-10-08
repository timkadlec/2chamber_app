import datetime
from pathlib import Path
from flask import current_app


# ------------------------------
#   PDF RENDERING
# ------------------------------
def render_pdf(template_name, context, filename_prefix):
    """
    Render a WeasyPrint PDF with shared layout and metadata.
    Ensures consistent logo, date, and filename.
    """
    from weasyprint import HTML
    from flask import make_response, render_template

    logo_path = Path(current_app.static_folder) / "images" / "hamu_logo.png"
    logo_url = logo_path.resolve().as_uri()

    context.setdefault("logo_url", logo_url)
    context.setdefault("today", datetime.date.today())

    html = render_template(template_name, **context)
    pdf = HTML(string=html, base_url=str(Path(current_app.root_path).resolve())).write_pdf()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers[
        "Content-Disposition"
    ] = f'attachment; filename={filename_prefix}_{datetime.date.today():%Y%m%d}.pdf'
    return response
