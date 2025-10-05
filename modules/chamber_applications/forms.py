from flask_wtf import FlaskForm
from wtforms import SelectField, SelectMultipleField, SubmitField, DateField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Optional
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from models import Student, Ensemble, Player, Teacher


def student_query():
    return Student.query.order_by(Student.last_name, Student.first_name)


def ensemble_query():
    return Ensemble.query.order_by(Ensemble.name)


def player_query():
    return Player.query.order_by(Player.last_name, Player.first_name)


def teacher_query():
    return Teacher.query.order_by(Teacher.last_name)


def player_label(p):
    base = p.student.full_name if p.student else p.full_name
    label = f"{base} ({p.instrument.name})"
    if not p.student_id:
        label = f"[Host] {label}"
    return label


def student_label(s):
    base = s.full_name if s else ""
    label = f"{base} ({s.instrument.name})" if s.instrument else base
    return label


def teacher_label(t):
    return t.full_name


class StudentChamberApplicationForm(FlaskForm):
    student = QuerySelectField(
        "Student (žadatel)",
        query_factory=student_query,
        get_label=student_label,
        validators=[DataRequired()]
    )

    players = QuerySelectMultipleField(
        "Spoluhráči",
        query_factory=player_query,
        get_label=player_label,
        validators=[Optional()]
    )

    teachers = QuerySelectMultipleField(
        "Pedagog",
        query_factory=teacher_query,
        get_label=teacher_label,
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

    def __init__(self, *args, **kwargs):
        # Use "mode" to control the submit label
        self.mode = kwargs.pop("mode", "add")
        super().__init__(*args, **kwargs)

        if self.mode == "add":
            self.submit.label.text = "Založit žádost"
            self.form_title = "Přidat"
        elif self.mode == "edit":
            self.submit.label.text = "Uložit změny"
            self.form_title = "Upravit stávající žádost"


class EmptyForm(FlaskForm):
    pass


class ExceptionRequestForm(FlaskForm):
    reason = TextAreaField("Odůvodnění",
                           validators=[DataRequired()],
                           render_kw={"rows": 3, "class": "form-control"})
    submit = SubmitField("Zažádat")
