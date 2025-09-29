from flask_wtf import FlaskForm
from wtforms import SelectField, SelectMultipleField, SubmitField, DateField, TextAreaField
from wtforms.validators import DataRequired,Optional
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from models import Student, Ensemble, Player


def student_query():
    return Student.query.order_by(Student.last_name, Student.first_name)


def ensemble_query():
    return Ensemble.query.order_by(Ensemble.name)


def player_query():
    return Player.query.order_by(Player.last_name, Player.first_name)

def player_label(p):
    base = p.student.full_name if p.student else p.full_name
    label = f"{base} ({p.instrument.name})"
    if not p.student_id:
        label = f"[Host] {label}"
    return label


class StudentChamberApplicationForm(FlaskForm):
    student = QuerySelectField(
        "Student (žadatel)",
        query_factory=student_query,
        allow_blank=True,
        get_label=lambda s: s.full_name,
        validators=[DataRequired()]
    )

    players = QuerySelectMultipleField(
        "Spoluhráči",
        query_factory=player_query,
        get_label=player_label,
        validators=[Optional()]
    )

    notes = TextAreaField("Poznámky",
                          render_kw={"rows": 3, "class": "form-control"},
                          validators=[Optional()]
                          )

    submission_date = DateField("Datum podání",
                                format="%Y-%m-%d",
                                validators=[Optional()],
                                )

    submit = SubmitField("Založi žádost")
