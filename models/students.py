from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.orm import relationship
from models import db


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(256), nullable=False, index=True)
    first_name = db.Column(db.String(256), nullable=False)
    phone_number = db.Column(db.String(256))
    email = db.Column(db.String(256))
    osobni_cislo = db.Column(db.String(256), unique=True)
    active = db.Column(db.Boolean, default=True, index=True)

    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id', ondelete='SET NULL'), nullable=True)
    instrument = relationship('Instrument')

    players = relationship(
        'Player',
        back_populates='student',
        passive_deletes=True  # works with SET NULL on FK
        # NO delete-orphan, because Player can live independently
    )

    # NEW: relationships to enrollment rows
    semester_enrollments = relationship(
        'StudentSemesterEnrollment',
        back_populates='student',
        cascade='all, delete-orphan'
    )
    subject_enrollments = relationship(
        'StudentSubjectEnrollment',
        back_populates='student',
        cascade='all, delete-orphan'
    )

    @property
    def full_name(self): return f"{self.last_name} {self.first_name}"

    @property
    def main_instrument(self): return self.instrument


class StudentSemesterEnrollment(db.Model):
    __tablename__ = 'student_semester_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='CASCADE'), nullable=False)

    student = relationship('Student', back_populates='semester_enrollments')
    semester = relationship('Semester', back_populates='student_enrollments')

    __table_args__ = (
        UniqueConstraint('student_id', 'semester_id', name='uq_student_semester'),
        Index('ix_sse_semester_student', 'semester_id', 'student_id'),
    )


class StudentSubjectEnrollment(db.Model):
    __tablename__ = 'student_subject_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)

    student = relationship('Student', back_populates='subject_enrollments')
    semester = relationship('Semester', back_populates='subject_enrollments')
    subject = relationship('Subject', back_populates='student_enrollments')

    __table_args__ = (
        UniqueConstraint('student_id', 'semester_id', 'subject_id', name='uq_student_semester_subject'),
        Index('ix_sse_subject_semester', 'subject_id', 'semester_id'),
        Index('ix_sse_student_semester', 'student_id', 'semester_id'),
    )
