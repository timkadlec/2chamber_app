from sqlalchemy.orm import relationship
from models import db
from flask_login import UserMixin
from datetime import datetime
import uuid


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
