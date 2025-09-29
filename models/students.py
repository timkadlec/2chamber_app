from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.orm import relationship, object_session
from models import db
from sqlalchemy.ext.hybrid import hybrid_method


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

    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id', ondelete='SET NULL'))
    instrument = relationship('Instrument')

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

    status_id = db.Column(db.Integer, db.ForeignKey('student_chamber_application_statuses.id', ondelete='SET NULL'))
    status = relationship('StudentChamberApplicationStatus')

    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='SET NULL'))
    semester = relationship('Semester')

    notes = db.Column(db.Text)
    submission_date = db.Column(db.Date)

    created_by_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_by = relationship('User')
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    players = relationship(
        'StudentChamberApplicationPlayers',
        back_populates='application',
        cascade='all, delete-orphan'
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


class StudentChamberApplicationPlayers(db.Model):
    __tablename__ = 'student_chamber_application_players'
    id = db.Column(db.Integer, primary_key=True)

    application_id = db.Column(db.Integer, db.ForeignKey('student_chamber_applications.id', ondelete='CASCADE'),
                               nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id', ondelete='CASCADE'), nullable=False)

    application = relationship('StudentChamberApplication', back_populates='players')
    player = relationship('Player')


class StudentChamberApplicationStatus(db.Model):
    __tablename__ = 'student_chamber_application_statuses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=True)
    description = db.Column(db.String(255))
