from flask_wtf import FlaskForm
from wtforms import SelectField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired,Optional
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from models import Student, Ensemble, Player


def student_query():
    return Student.query.order_by(Student.last_name, Student.first_name)


def ensemble_query():
    return Ensemble.query.order_by(Ensemble.name)


def player_query():
    return Player.query.order_by(Player.last_name, Player.first_name)


class StudentChamberApplicationForm(FlaskForm):
    student = QuerySelectField(
        "Student (applicant)",
        query_factory=student_query,
        allow_blank=True,
        get_label=lambda s: s.full_name,
        validators=[DataRequired()]
    )

    players = QuerySelectMultipleField(
        "Spluhráči",
        query_factory=player_query,
        get_label=lambda p: f"{p.student.full_name if p.student else p.full_name}",
        validators=[Optional()]
    )

    submit = SubmitField("Založi žádost")
