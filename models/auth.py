from sqlalchemy.orm import relationship
from models import db
from flask_login import UserMixin
from datetime import datetime
import uuid


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))

    role_permissions = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        overlaps="permissions"
    )
    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        overlaps="role_permissions"
    )
    users = relationship("User", back_populates="role")

    def has_permission(self, code: str) -> bool:
        return any(p.code == code for p in self.permissions)


class RolePermission(db.Model):
    __tablename__ = "role_permissions"
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)

    role = relationship("Role", back_populates="role_permissions", overlaps="permissions")
    permission = relationship("Permission", back_populates="role_permissions", overlaps="roles")


class Permission(db.Model):
    __tablename__ = "permissions"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(64))
    description = db.Column(db.String(255))
    category = db.Column(db.String(64))

    # 🔧 this was missing before
    role_permissions = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
        overlaps="roles"
    )
    roles = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        overlaps="role_permissions"
    )


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), autoincrement=False)
    oid = db.Column(db.String(64), unique=True, index=True)
    tid = db.Column(db.String(64), index=True)
    email = db.Column(db.String(255), unique=True, index=True)
    upn = db.Column(db.String(255), index=True)
    display_name = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    provider = db.Column(db.String(32), default="entra")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)

    active = db.Column(db.Boolean, default=True)

    # one role per user
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="SET NULL"))
    role = relationship("Role", back_populates="users")

    def has_role(self, role_name: str) -> bool:
        return self.role and self.role.name == role_name

    def has_any_role(self, roles: list[str]) -> bool:
        return self.role and self.role.name in roles

    def has_permission(self, code: str) -> bool:
        return self.role and self.role.has_permission(code)
