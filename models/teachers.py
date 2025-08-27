from models import db


class Teacher(db.Model):
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    import_name = db.Column(db.String(256), unique=True, nullable=False)

    @property
    def full_name(self):
        if self.academic_position:
            return f"{self.academic_position.shortcut} {self.name}"
        else:
            return self.name
