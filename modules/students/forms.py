from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField

class EnrollmentForm(FlaskForm):
    erasmus = BooleanField("Erasmus+")
    submit = SubmitField("Uložit")
