from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from models import Composer
from flask_wtf import FlaskForm
from wtforms import (StringField, SelectMultipleField, SubmitField,
                     PasswordField, SelectField, BooleanField, widgets, TextAreaField, IntegerField)
from wtforms.validators import InputRequired, Optional, Length, Email, DataRequired


def all_composers_query():
    composers = Composer.query.order_by(Composer.last_name).all()

    if not composers:
        return [Composer(first_name="Dostupný", last_name="Žádný", id=None)]
    return composers


def composer_label(composer):
    return composer.full_name


class CompositionForm(FlaskForm):
    name = StringField("Název", validators=[DataRequired()], render_kw={"placeholder": "Zadejte název skladby"})
    type = SelectField("Typ kompozice", choices=[["chamber", "Komorní"], ["orchestral", "Orchestrální"]])
    year = IntegerField("Rok", validators=[DataRequired()], render_kw={"placeholder": "Rok kompozice"})
    durata = IntegerField("Durata", validators=[DataRequired()])
    description = TextAreaField("Popis", validators=[Optional()])
    composer = QuerySelectField("Skladatel",
                                query_factory=all_composers_query,
                                get_label=composer_label,
                                get_pk=lambda obj: obj.id,
                                blank_text="— Vyberte skladatele —")
    instrumentation = StringField("Instrumentace", validators=[DataRequired()])

    submit = SubmitField()

    def __init__(self, *args, **kwargs):
        # Use "mode" to control the submit label
        self.mode = kwargs.pop("mode", "add")
        super().__init__(*args, **kwargs)

        if self.mode == "add":
            self.submit.label.text = "Vytvořit skladbu"
            self.form_title = "Přidat novou skladbu"
        elif self.mode == "edit":
            self.submit.label.text = "Uložit změny"
            self.form_title = "Úprava stávající skladby"


class CompositionFilterForm(FlaskForm):
    project_id = SelectField("Projekt", choices=[], validators=[Optional()])
    composer = QuerySelectMultipleField("Skladatel",
                                        query_factory=all_composers_query,
                                        get_label=composer_label,
                                        get_pk=lambda obj: obj.id,
                                        blank_text="— Vyberte skladatele —")
    type = SelectField("Typ", choices=[
        ('', 'Všechny typy'),
        ('chamber', 'Komorní'),
        ('orchestral', 'Orchestrální')
    ], validators=[Optional()])
    submit = SubmitField("Filtrovat")


class ComposerForm(FlaskForm):
    first_name = StringField("Jméno", validators=[DataRequired()])
    last_name = StringField("Příjmení", validators=[DataRequired()])

    submit = SubmitField()

    def __init__(self, *args, **kwargs):
        # Use "mode" to control the submit label
        self.mode = kwargs.pop("mode", "add")
        super().__init__(*args, **kwargs)

        if self.mode == "add":
            self.submit.label.text = "Vytvořit skladatele"
            self.form_title = "Přidat nového skladatele"
        elif self.mode == "edit":
            self.submit.label.text = "Uložit změny"
            self.form_title = "Úprava stávajícího skladatele"
