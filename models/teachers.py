from . import db
from sqlalchemy import Index


class Teacher(db.Model):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))  # fixed typo
    last_name = db.Column(db.String(100))

    full_name = db.Column(db.String(200))

    teacher_subjects = db.relationship(
        "TeacherSubject",
        back_populates="teacher",
        cascade="all, delete-orphan"
    )

    subjects = db.relationship(
        "Subject",
        secondary="teacher_subjects",
        back_populates="teachers"
    )

    ensemble_links = db.relationship(
        "EnsembleTeacher",
        back_populates="teacher",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Teacher {self.id} {self.full_name or (self.first_name or '') + ' ' + (self.last_name or '')}>"


class TeacherSubject(db.Model):
    __tablename__ = "teacher_subjects"

    id = db.Column(db.Integer, primary_key=True)

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    semester_id = db.Column(
        db.Integer,
        db.ForeignKey("semesters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # optional metadata for the assignment
    role = db.Column(db.String(80))  # e.g., "guarantor", "assistant"
    notes = db.Column(db.Text)

    teacher = db.relationship("Teacher", back_populates="teacher_subjects")
    subject = db.relationship("Subject", back_populates="subject_teachers")
    semester = db.relationship("Semester", back_populates="teacher_subjects")

    __table_args__ = (
        # prevent duplicates within the same semester
        db.UniqueConstraint("teacher_id", "subject_id", "semester_id",
                            name="uq_teacher_subject_semester"),
        # handy for queries like “all teachers for subject X in semester Y”
        Index("ix_tsubj_subject_sem", "subject_id", "semester_id"),
        Index("ix_tsubj_teacher_sem", "teacher_id", "semester_id"),
    )

    def __repr__(self):
        return f"<TeacherSubject t={self.teacher_id} s={self.subject_id} sem={self.semester_id}>"
