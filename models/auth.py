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

    # portal links — at most one should be set
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="SET NULL"), nullable=True, unique=True)
    student = relationship("Student", foreign_keys=[student_id])

    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, unique=True)
    teacher = relationship("Teacher", foreign_keys=[teacher_id])

    @property
    def portal_type(self):
        if self.student_id:
            return "student"
        if self.teacher_id:
            return "teacher"
        return "admin"

    def has_role(self, role_name: str) -> bool:
        return self.role and self.role.name == role_name

    def has_any_role(self, roles: list[str]) -> bool:
        return self.role and self.role.name in roles

    def has_permission(self, code: str) -> bool:
        return self.role and self.role.has_permission(code)

    passkey_credentials = relationship("PasskeyCredential", back_populates="user", cascade="all, delete-orphan")


class PasskeyCredential(db.Model):
    __tablename__ = "passkey_credentials"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    credential_id = db.Column(db.LargeBinary, unique=True, nullable=False)
    public_key = db.Column(db.LargeBinary, nullable=False)
    sign_count = db.Column(db.Integer, default=0, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="passkey_credentials")
