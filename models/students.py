from models import db


class StudentInstrument(db.Model):
    __tablename__ = 'student_instrument'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)

    student = db.relationship('Student', back_populates='student_instruments')
    instrument = db.relationship('Instrument')


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(256), nullable=False)
    phone_number = db.Column(db.String(256), nullable=True)
    email = db.Column(db.String(256), nullable=True)
    osobni_cislo = db.Column(db.String(256), unique=True)
    active = db.Column(db.Boolean, default=True)

    student_instruments = db.relationship('StudentInstrument', back_populates='student', cascade='all, delete-orphan',
                                          lazy='joined')

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def main_instrument(self):
        mi = self.student_instruments.filter_by(is_primary=True).first()
        return mi.instrument if mi else None
