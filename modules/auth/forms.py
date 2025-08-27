from flask_wtf import FlaskForm
from wtforms import (StringField, SelectMultipleField, SubmitField,
                     PasswordField, SelectField, BooleanField, widgets)
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.validators import Optional, Length, DataRequired
from models import Permissions, Role


class RoleForm(FlaskForm):
    name = StringField("Role Name")
    permissions = SelectMultipleField("Permissions", choices=[
        (Permissions.PLANNER_ACCESS, "Planner Access"),
        (Permissions.PLANNER_EDIT, "Planner Edit"),
        (Permissions.CREATE_USER, "Create User"),
        (Permissions.SETTINGS, "Settings"),
    ], coerce=int)

    submit = SubmitField("Save")


def all_roles_query():
    roles = Role.query.all()

    if not roles:
        return [Role(name="No roles available", id=None)]
    print(f"Roles: {roles}")  # Add a placeholder if no roles are found
    return roles


def role_label(role):
    return role.name


PERMISSIONS = {
    1: "Access Planner",
    2: "Edit Planner",
    4: "Create User",
    8: "Access Settings",
    16: "Apply for Projects",
    32: "Nominate Players"
}


class LoginForm(FlaskForm):
    email_or_username = StringField('Email nebo uživatelské jméno', validators=[
        DataRequired(message="Vyplňte prosím email nebo uživatelské jméno."),
        Length(max=120)
    ])
    password = PasswordField('Heslo', validators=[
        DataRequired(message="Vyplňte prosím heslo.")
    ])
    remember_me = BooleanField('Zapamatovat si mě')
    submit = SubmitField('Přihlásit se')


class UserForm(FlaskForm):
    username = StringField("Username")
    email = StringField("Email")
    password = PasswordField("Password", validators=[Optional()])  # Optional password field
    role = QuerySelectField("Role",
                            query_factory=all_roles_query,
                            get_label=role_label,
                            get_pk=lambda obj: obj.id,
                            blank_text="— Vyberte roli —")
    active = BooleanField("Active", default=1)
    permissions = SelectMultipleField(
        'Extra Permissions',
        choices=[(str(perm), label) for perm, label in PERMISSIONS.items()],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False)
    )

    generate_password = SubmitField("Generate New Password")  # New button for generating password
    submit = SubmitField()

    def __init__(self, *args, **kwargs):
        # Use "mode" to control the submit label
        self.mode = kwargs.pop("mode", "add")
        super().__init__(*args, **kwargs)

        if self.mode == "add":
            self.submit.label.text = "Vytvořit uživatele"
            self.form_title = "Přidat uživatele"
        elif self.mode == "edit":
            self.submit.label.text = "Uložit změny"
            self.form_title = "Editace uživatele"


class NominationScopeForm(FlaskForm):
    instrument_section_id = SelectField("Section", coerce=int, choices=...)
    instrument_group_id = SelectField("Group", coerce=int, choices=...)
    instrument_id = SelectField("Instrument", coerce=int, choices=...)

    submit = SubmitField("Add Scope")
