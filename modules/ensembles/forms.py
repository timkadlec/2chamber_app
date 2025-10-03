from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from models import Composer, Teacher
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


def all_teachers_query():
    teachers = Teacher.query.order_by(Teacher.last_name).all()
    return teachers


def teacher_label(teacher):
    return teacher.full_name


class EnsembleForm(FlaskForm):
    name = StringField("Název", validators=[Optional()], render_kw={"placeholder": "Zadejte název souboru"})
    submit = SubmitField()

    def __init__(self, *args, **kwargs):
        # Use "mode" to control the submit label
        self.mode = kwargs.pop("mode", "add")
        super().__init__(*args, **kwargs)

        if self.mode == "add":
            self.submit.label.text = "Vytvořit soubor"
            self.form_title = "Přidat nový soubor"
        elif self.mode == "edit":
            self.submit.label.text = "Uložit změny"
            self.form_title = "Úprava stávajícího souboru"


class TeacherForm(FlaskForm):
    teacher = QuerySelectField(
        "Pedagog",
        query_factory=all_teachers_query,
        get_label=teacher_label,
        get_pk=lambda obj: obj.id,
        allow_blank=True,  # <- allow empty selection
        blank_text="",  # <- no dummy text inside the list
        default=None  # <- start with nothing selected
    )
    submit = SubmitField("Přiřadit pedagoga")


class NoteForm(FlaskForm):
    text = TextAreaField("Text poznámky", validators=[DataRequired()])
    submit = SubmitField("Uložit")
