from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.validators import DataRequired, Optional, Email

from models import Instrument


def instrument_query():
    return Instrument.query.filter_by(is_primary=True).order_by(Instrument.weight)


class PlayerForm(FlaskForm):
    first_name = StringField("Jméno", validators=[DataRequired()])
    last_name = StringField("Příjmení", validators=[DataRequired()])
    instrument = QuerySelectField(
        "Nástroj",
        query_factory=instrument_query,
        get_label=lambda s: s.name,
        validators=[DataRequired()]
    )
    phone = StringField("Telefon", validators=[Optional()])
    email = StringField("Email", validators=[Optional(), Email()])
    submit = SubmitField("Přidat hráče")

    def __init__(self, *args, **kwargs):
        # Use "mode" to control the submit label
        self.mode = kwargs.pop("mode", "add")
        super().__init__(*args, **kwargs)

        if self.mode == "add":
            self.submit.label.text = "Vytvořit hráče"
            self.title = "Přidat nového hráče"
        elif self.mode == "edit":
            self.submit.label.text = "Uložit změny"
            self.title = "Úprava stávajícího hráče"
