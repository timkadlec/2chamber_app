from flask_wtf import FlaskForm
from wtforms import SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional


class UserEditForm(FlaskForm):
    role_id = SelectField("Role", coerce=int, validators=[DataRequired()])
    is_active = BooleanField("Aktivní účet")
    # coerce=lambda x: int(x) if x else None lets the "no link" option pass as None
    student_id = SelectField("Propojit se studentem", coerce=lambda x: int(x) if x else None, validators=[Optional()])
    teacher_id = SelectField("Propojit s pedagogem", coerce=lambda x: int(x) if x else None, validators=[Optional()])
    submit = SubmitField("Uložit změny")
