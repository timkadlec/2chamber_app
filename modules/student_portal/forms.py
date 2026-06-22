from flask_wtf import FlaskForm
from wtforms import IntegerField, BooleanField, TextAreaField, SubmitField, DateField
from wtforms.validators import Optional, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from models import Teacher, Player, Ensemble


def teacher_query():
    return Teacher.query.order_by(Teacher.last_name, Teacher.first_name)


def player_query():
    return Player.query.order_by(Player.last_name, Player.first_name)


def teacher_label(t):
    return t.full_name


def player_label(p):
    base = p.student.full_name if p.student else p.full_name
    inst = f" ({p.instrument.name})" if p.instrument else ""
    prefix = "" if p.student_id else "[Host] "
    return f"{prefix}{base}{inst}"


class ChamberEnrollmentRequestForm(FlaskForm):
    future_year = IntegerField(
        "Budoucí ročník",
        validators=[Optional(), NumberRange(min=1, max=9)],
        render_kw={"class": "form-control", "placeholder": "např. 3"},
    )

    teacher = QuerySelectField(
        "Preferovaný pedagog komorní hry",
        query_factory=teacher_query,
        get_label=teacher_label,
        allow_blank=True,
        blank_text="— Není domluveno —",
        validators=[Optional()],
    )

    wants_to_stay = BooleanField("Přeji si setrvat ve stávajícím souboru")

    stay_ensemble = QuerySelectField(
        "Soubor, ve kterém chci setrvat",
        query_factory=lambda: [],
        get_label="name",
        allow_blank=True,
        blank_text="— Vyberte soubor —",
        validators=[Optional()],
    )

    players = QuerySelectMultipleField(
        "Navržení spoluhráči",
        query_factory=player_query,
        get_label=player_label,
        validators=[Optional()],
    )

    notes = TextAreaField(
        "Poznámka",
        validators=[Optional()],
        render_kw={"class": "form-control", "rows": 3,
                   "placeholder": 'Uveďte "Nezařazen/a" a nástrojové složení souboru, pokud spoluhráče neuvádíte.'},
    )

    submit = SubmitField("Podat přihlášku")
