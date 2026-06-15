from flask_wtf import FlaskForm
from wtforms import SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired


class UserEditForm(FlaskForm):
    role_id = SelectField("Role", coerce=int, validators=[DataRequired()])
    is_active = BooleanField("Aktivní účet")
    submit = SubmitField("Uložit změny")
