from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.orm import relationship, object_session
from models import db
from models.core import Subject, Semester, Department, Instrument
from sqlalchemy.ext.hybrid import hybrid_method
from flask import session
from sqlalchemy import CheckConstraint

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(256), nullable=False, index=True)
    first_name = db.Column(db.String(256), nullable=False)
    phone_number = db.Column(db.String(256))
    email = db.Column(db.String(256))
    osobni_cislo = db.Column(db.String(256), unique=True)
    active = db.Column(db.Boolean, default=True, index=True)
    id_studia = db.Column(db.Integer())

    state = db.Column(db.String(256))

    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id', ondelete='SET NULL'))
    instrument = relationship('Instrument')

    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    department = db.relationship("Department")

    player = relationship(
        'Player',
        back_populates='student',
        uselist=False,
        passive_deletes=True
    )

    semester_enrollments = relationship(
        'StudentSemesterEnrollment',
        back_populates='student',
        cascade='all, delete-orphan'
    )
    subject_enrollments = relationship(
        'StudentSubjectEnrollment',
        back_populates='student',
        cascade='all, delete-orphan',
        order_by="desc(StudentSubjectEnrollment.semester_id)"
    )

    chamber_applications = relationship(
        'StudentChamberApplication',
        back_populates='student',
        cascade='all, delete-orphan'
    )

    requests = relationship(
        "StudentRequest",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="desc(StudentRequest.request_date)",
    )

    @property
    def current_semester_id(self):
        # keep your existing fallback if you want
        return session.get("semester_id") or session.get("current_semester")

    @property
    def enrolled_subjects_current(self):
        """
        Return Subject objects the student is enrolled in for the current semester (from Flask session).
        Efficient: uses a DB query if the instance is attached to a session; otherwise falls back to in-memory list.
        """
        semester_id = self.current_semester_id
        if not semester_id:
            return []

        sa_sess = object_session(self)

        # If attached to SQLAlchemy session, do an efficient query
        if sa_sess is not None:
            return (
                sa_sess.query(Subject)
                .join(StudentSubjectEnrollment, StudentSubjectEnrollment.subject_id == Subject.id)
                .filter(StudentSubjectEnrollment.student_id == self.id)
                .filter(StudentSubjectEnrollment.semester_id == semester_id)
                .order_by(Subject.weight.asc().nullslast(), Subject.name.asc())
                .all()
            )

        # Fallback: use already-loaded relationship list (may be less efficient)
        enrollments = [e for e in (self.subject_enrollments or []) if e.semester_id == semester_id]
        subjects = [e.subject for e in enrollments if e.subject is not None]
        subjects.sort(key=lambda s: ((s.weight if s.weight is not None else 10 ** 9), s.name))
        return subjects

    @property
    def full_name(self): return f"{self.last_name} {self.first_name}"

    @property
    def main_instrument(self): return self.instrument

    @hybrid_method
    def has_erasmus_in_semester(self, semester_id):
        return any(
            se.erasmus and se.semester_id == semester_id
            for se in self.subject_enrollments
        )

    @has_erasmus_in_semester.expression
    def has_erasmus_in_semester(cls, semester_id):
        return db.session.query(StudentSubjectEnrollment.id).filter(
            StudentSubjectEnrollment.student_id == cls.id,
            StudentSubjectEnrollment.semester_id == semester_id,
            StudentSubjectEnrollment.erasmus.is_(True)
        ).exists()

    @property
    def ensembles_in_semester(self):
        from models import Ensemble, EnsemblePlayer, EnsembleSemester
        sid = session.get("semester_id")
        if not sid or not self.player:
            return []
        return (
            Ensemble.query
            .join(EnsemblePlayer, EnsemblePlayer.ensemble_id == Ensemble.id)
            .join(EnsembleSemester, EnsembleSemester.ensemble_id == Ensemble.id)
            .filter(EnsemblePlayer.player_id == self.player.id)
            .filter(EnsembleSemester.semester_id == sid)
            .all()
        )


    def ensembles_for_semester(self, semester_id: int):
        """
        Return ensembles where this student's Player is assigned in the given semester.
        Safe: does not depend on Flask session.
        """
        if not semester_id or not self.player:
            return []

        sa_sess = object_session(self) or db.session

        from models import Ensemble, EnsemblePlayer, EnsembleSemester

        return (
            sa_sess.query(Ensemble)
            .join(EnsemblePlayer, EnsemblePlayer.ensemble_id == Ensemble.id)
            .join(EnsembleSemester, EnsembleSemester.ensemble_id == Ensemble.id)
            .filter(EnsemblePlayer.player_id == self.player.id)
            .filter(EnsemblePlayer.semester_id == semester_id)  # ✅ IMPORTANT
            .filter(EnsembleSemester.semester_id == semester_id)  # ✅ keep if you want "must be linked"
            .distinct()
            .order_by(Ensemble.name.asc())
            .all()
        )

    @property
    def subject_enrollments_current(self):
        """Return all subject enrollments for the current semester (from session)."""
        current_semester = session.get('semester_id') or session.get('current_semester')
        if not current_semester:
            return []

        return [
            se for se in self.subject_enrollments
            if se.semester_id == current_semester
        ]


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

    erasmus = db.Column(db.Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('student_id', 'semester_id', 'subject_id', name='uq_student_semester_subject'),
        Index('ix_sse_subject_semester', 'subject_id', 'semester_id'),
        Index('ix_sse_student_semester', 'student_id', 'semester_id'),
    )


class StudentChamberApplication(db.Model):
    __tablename__ = 'student_chamber_applications'
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    student = relationship('Student', back_populates='chamber_applications')

    teachers = relationship(
        'StudentChamberApplicationTeacher',
        back_populates='application',
        cascade='all, delete-orphan'
    )

    status_id = db.Column(db.Integer, db.ForeignKey('student_chamber_application_statuses.id', ondelete='SET NULL'))
    status = relationship('StudentChamberApplicationStatus')

    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='SET NULL'))
    semester = relationship('Semester')

    exception = relationship("ChamberException", uselist=False,
                             back_populates="application",
                             cascade="all, delete-orphan")

    notes = db.Column(db.Text)
    submission_date = db.Column(db.Date)

    review_comment = db.Column(db.Text)

    reviewed_by_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='SET NULL'))
    reviewed_by = relationship(
        'User',
        foreign_keys=[reviewed_by_id]
    )
    reviewed_at = db.Column(db.DateTime)

    created_by_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_by = relationship(
        'User',
        foreign_keys=[created_by_id]
    )
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    players = relationship(
        'StudentChamberApplicationPlayers',
        back_populates='application',
        cascade='all, delete-orphan'
    )

    ensemble_link = db.relationship(
        "EnsembleApplication",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    @property
    def all_player_ids(self):
        """Return a set of all player IDs (applicant + co-players)."""
        ids = {self.student.player.id} if self.student and self.student.player else set()
        ids |= {p.player_id for p in self.players if p.player_id}
        return ids

    @property
    def related_applications(self):
        """Return other applications with the exact same set of players in the same semester."""
        session = object_session(self)
        if not session or not self.semester_id:
            return []

        my_players = self.all_player_ids

        # load other apps in same semester (excluding self)
        candidates = (
            session.query(StudentChamberApplication)
            .filter(
                StudentChamberApplication.semester_id == self.semester_id,
                StudentChamberApplication.id != self.id,
            )
            .all()
        )

        related = []
        for app in candidates:
            if app.all_player_ids == my_players:
                related.append(app)

        return related

    @property
    def student_count(self):
        """Applicant + co-players that are real students."""
        count = 1 if self.student and self.student.player else 0
        count += sum(1 for p in self.players if p.player and p.player.student)
        return count

    @property
    def external_count(self):
        """Applicant + co-players that are externals (no linked Student)."""
        count = 1 if self.student and (self.student.player and not self.student.player.student) else 0
        count += sum(1 for p in self.players if not (p.player and p.player.student))
        return count

    @property
    def health_check(self):
        total = self.student_count + self.external_count
        if total <= 2:
            return "Soubor nesplňuje kritérium minima hráčů."
        percentage_students = round((self.student_count / total) * 100, 2)
        if percentage_students > 50:
            return "OK"
        else:
            return "Soubor obsahuje vysoké procento hostů."

class StudentRequest(db.Model):
    __tablename__ = 'student_requests'
    id = db.Column(db.Integer, primary_key=True)

    performance_type = db.Column(db.String(255))
    performance_date = db.Column(db.DateTime)
    suggested_mark = db.Column(db.String(255))
    request_date = db.Column(db.Date, nullable=False)

    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    student = relationship('Student', back_populates='requests')
    ensemble_id = db.Column(db.Integer, db.ForeignKey('ensembles.id', ondelete='CASCADE'), nullable=False)
    ensemble = relationship("Ensemble")
    status = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    created_by_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_by = relationship(
        'User',
        foreign_keys=[created_by_id]
    )

    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','rejected')", name="ck_student_request_status"),
        UniqueConstraint("student_id", "ensemble_id", "performance_date", "performance_type",
                         name="uq_student_request_unique"),
        Index("ix_student_requests_student_date", "student_id", "request_date"),
        Index("ix_student_requests_ensemble_date", "ensemble_id", "request_date"),
        Index("ix_student_requests_status", "status"),
    )

class ChamberException(db.Model):
    __tablename__ = 'chamber_exceptions'
    id = db.Column(db.Integer, primary_key=True)

    application_id = db.Column(db.Integer, db.ForeignKey('student_chamber_applications.id', ondelete='CASCADE'))
    application = relationship("StudentChamberApplication", back_populates="exception")
    reason = db.Column(db.String(255))

    status = db.Column(db.String(255), default="pending")

    ensemble = relationship("Ensemble", back_populates="exception", uselist=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    created_by_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_by = relationship(
        'User',
        foreign_keys=[created_by_id]
    )

    reviewer_comment = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='SET NULL'))
    reviewed_by = relationship(
        'User',
        foreign_keys=[reviewed_by_id]
    )


class StudentChamberApplicationPlayers(db.Model):
    __tablename__ = 'student_chamber_application_players'
    id = db.Column(db.Integer, primary_key=True)

    application_id = db.Column(db.Integer, db.ForeignKey('student_chamber_applications.id', ondelete='CASCADE'),
                               nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id', ondelete='CASCADE'), nullable=False)

    application = relationship('StudentChamberApplication', back_populates='players')
    player = relationship('Player')


class StudentChamberApplicationTeacher(db.Model):
    __tablename__ = 'student_chamber_application_teachers'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('student_chamber_applications.id', ondelete='CASCADE'),
                               nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id', ondelete='CASCADE'), nullable=False)
    application = relationship('StudentChamberApplication', back_populates='teachers')
    teacher = relationship('Teacher')


class StudentChamberApplicationStatus(db.Model):
    __tablename__ = 'student_chamber_application_statuses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=True)
    description = db.Column(db.String(255))
