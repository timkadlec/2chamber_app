from sqlalchemy.orm import relationship
from models import db
from flask_login import UserMixin


class Permissions:
    PLANNER_ACCESS = 1
    PLANNER_EDIT = 2
    CREATE_USER = 4
    SETTINGS = 8
    CAN_APPLY = 16
    CAN_NOMINATE = 32


class SettingsCategories:
    INSTRUMENTS = "instruments"
    VENUES = "venues"
    USERS = "users"
    PROJECTS = "projects"


class SettingsScope(db.Model):
    __tablename__ = 'settings_scopes'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(100))

    user = relationship('User', back_populates='settings_scopes')


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(50), nullable=False, unique=True)
    permissions = db.Column(db.Integer, default=0)

    users = relationship("User", back_populates="role")

    def get_permission_labels(self, permissions_dict):
        return [label for perm, label in permissions_dict.items() if self.permissions & perm]


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), nullable=False, unique=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    role = relationship("Role", back_populates="users")

    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    settings_scopes = relationship('SettingsScope', back_populates='user')

    extra_permissions = db.Column(db.Integer, default=0)
    denied_permissions = db.Column(db.Integer, default=0)

    notifications = db.relationship('Notification', back_populates='user', cascade='all')

    def has_permission(self, permission):
        # Explicitly denied permissions take precedence
        if (self.denied_permissions & permission) == permission:
            return False

        # Explicitly granted permissions override role
        if (self.extra_permissions & permission) == permission:
            return True

        # Fallback to role-based
        return self.role and (self.role.permissions & permission) == permission

    def has_any_role(self, roles):
        return self.role in roles  # assuming 'role' is a single string. Adjust if it’s a list or set.

    @property
    def unread_notifications(self):
        notifications = Notification.query.filter_by(user_id=self.id, is_read=False).order_by(
            Notification.created_at.desc()).all()
        if notifications:
            return notifications
        else:
            return False

    @property
    def unread_notifications_count(self):
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    message = db.Column(db.String(512))
    type = db.Column(db.String(50), default='info')  # e.g., 'info', 'warning', 'success'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship('User', back_populates='notifications')
