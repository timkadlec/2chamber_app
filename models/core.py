from sqlalchemy.orm import relationship
from collections import defaultdict
from models import db
from datetime import datetime
from sqlalchemy import UniqueConstraint, CheckConstraint, Index


class AcademicYear(db.Model):
    __tablename__ = 'academic_years'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    semesters = db.relationship(
        "Semester",
        back_populates="academic_year",
        cascade="all, delete-orphan",
        order_by="Semester.start_date"
    )

    __table_args__ = (
        CheckConstraint('start_date <= end_date', name='chk_ay_dates'),
        Index('ix_ay_start_end', 'start_date', 'end_date'),
    )

    @property
    def current_semester(self):
        today = datetime.now().date()
        return next((s for s in self.semesters if s.start_date <= today <= s.end_date), None)

    @property
    def upcoming_semester(self):
        today = datetime.now().date()
        future = [s for s in self.semesters if s.start_date > today]
        return min(future, key=lambda s: s.start_date) if future else None


class Semester(db.Model):
    __tablename__ = "semesters"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date    )

    academic_year_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_years.id", ondelete="SET NULL")
    )
    academic_year = db.relationship("AcademicYear", back_populates="semesters")

    ensemble_links = db.relationship(
        "EnsembleSemester", back_populates="semester", cascade="all, delete-orphan"
    )

    student_enrollments = db.relationship(
        "StudentSemesterEnrollment", back_populates="semester", cascade="all, delete-orphan"
    )
    subject_enrollments = db.relationship(
        "StudentSubjectEnrollment", back_populates="semester", cascade="all, delete-orphan"
    )

    teacher_subjects = db.relationship(
        "TeacherSubject", back_populates="semester", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint("start_date <= end_date", name="chk_semester_dates"),
        db.UniqueConstraint("academic_year_id", "name", name="uq_semester_name_in_year"),
        Index("ix_semester_start_end", "start_date", "end_date"),
    )

    @property
    def ensembles(self):
        return [link.ensemble for link in self.ensemble_links]


class Subject(db.Model):
    __tablename__ = "subjects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    code = db.Column(db.String(100))

    # Enrollment relation (assumes you have this model elsewhere)
    student_enrollments = db.relationship(
        "StudentSubjectEnrollment",
        back_populates="subject",
        cascade="all, delete-orphan"
    )

    # Association objects to teachers
    subject_teachers = db.relationship(
        "TeacherSubject",
        back_populates="subject",
        cascade="all, delete-orphan"
    )

    # Convenience: direct many-to-many view (through the association table)
    teachers = db.relationship(
        "Teacher",
        secondary="teacher_subjects",
        back_populates="subjects"
    )

    def enrolled_count(self, semester_id=None):
        if semester_id:
            return sum(1 for e in self.student_enrollments if e.semester_id == semester_id)
        return len(self.student_enrollments)

    def __repr__(self):
        return f"<Subject {self.id} {self.name!r}>"


# ------------------------
# Users, Roles, Permissions (GLOBAL USER SYSTEM)
# ------------------------


class InstrumentSection(db.Model):
    __tablename__ = 'instrument_sections'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    instrument_groups = relationship('InstrumentGroup', back_populates='instrument_section',
                                     cascade="all, delete-orphan")
    instruments = relationship('Instrument', back_populates='instrument_section', cascade="all, delete-orphan")

    weight = db.Column(db.Integer, default=0)


class InstrumentGroup(db.Model):
    __tablename__ = 'instrument_groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    instrument_section_id = db.Column(db.Integer, db.ForeignKey('instrument_sections.id'))
    instrument_section = relationship('InstrumentSection', back_populates='instrument_groups')

    instruments = relationship('Instrument', back_populates='instrument_group', cascade="all, delete-orphan")

    weight = db.Column(db.Integer, default=0)


class Instrument(db.Model):
    __tablename__ = 'instruments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    abbreviation = db.Column(db.String(20))

    instrument_section_id = db.Column(db.Integer, db.ForeignKey('instrument_sections.id'))
    instrument_section = relationship('InstrumentSection', back_populates='instruments')

    instrument_group_id = db.Column(db.Integer, db.ForeignKey('instrument_groups.id'))
    instrument_group = relationship('InstrumentGroup', back_populates='instruments')

    weight = db.Column(db.Integer, default=0)

    @property
    def normalized_abbr(self):
        return self.abbreviation.lower()


class PercussionInstrument(db.Model):
    __tablename__ = 'percussion_instruments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)


# -----------------------------------------
# Instrumentation (Now Instruments exist)
# -----------------------------------------
class Instrumentation(db.Model):
    __tablename__ = 'instrumentations'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))

    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)
    separate = db.Column(db.Boolean, default=False)
    comment = db.Column(db.String(255), nullable=True)
    concertmaster = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, nullable=True)

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'instrumentation',
        'with_polymorphic': '*'
    }

    instrument = relationship('Instrument', foreign_keys=[instrument_id])

    doublings = relationship('DoublingInstrumentation', back_populates='instrumentation', cascade="all, delete-orphan")


class DoublingInstrumentation(db.Model):
    __tablename__ = 'doubling_instrumentations'
    id = db.Column(db.Integer, primary_key=True)

    instrumentation_id = db.Column(db.Integer, db.ForeignKey('instrumentations.id'), nullable=False)
    doubling_instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)

    separate = db.Column(db.Boolean, default=False)  # e.g. separate +piccolo, +cor anglais

    instrumentation = relationship('Instrumentation', back_populates='doublings')
    doubling_instrument = relationship('Instrument')


class ProjectInstrumentation(Instrumentation):
    __tablename__ = 'project_instrumentations'
    id = db.Column(db.Integer, db.ForeignKey('instrumentations.id'), primary_key=True)

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    project = db.relationship("Project", back_populates="instrumentation_entries")

    player_assignments = relationship("ProjectPlayerAssignment", back_populates="instrumentation",
                                      cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_identity': 'project_instrumentation',
    }


class EventProjectInstrumentation(db.Model):
    __tablename__ = 'event_project_instrumentations'
    id = db.Column(db.Integer, primary_key=True)

    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    project_instrumentation_id = db.Column(db.Integer, db.ForeignKey('project_instrumentations.id'), nullable=False)

    included = db.Column(db.Boolean, default=True)

    event = relationship('Event', back_populates='project_instrumentation_links')
    project_instrumentation = relationship('ProjectInstrumentation')


class EventPercussionGear(db.Model):
    __tablename__ = 'event_percussion_gear'
    id = db.Column(db.Integer, primary_key=True)

    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    percussion_instrument_id = db.Column(db.Integer, db.ForeignKey('percussion_instruments.id'), nullable=False)

    count = db.Column(db.Integer, default=1)

    note = db.Column(db.String(256))

    event = relationship("Event", backref="percussion_gear")
    instrument = relationship("PercussionInstrument")


# -----------------------------------------
# Core Models (Projects and Events)
# -----------------------------------------

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    conductor = db.Column(db.String(100))
    programme = db.Column(db.Text)  # Changed from db.String to db.Text
    instrumentation_comment = db.Column(db.String(256))
    color = db.Column(db.String(50))

    application_mode = db.Column(db.String(20), default="project")

    nomination_active = db.Column(db.Boolean, default=False)

    events = relationship('Event', back_populates='project', cascade="all, delete-orphan")
    instrumentation_entries = relationship("ProjectInstrumentation", back_populates="project",
                                           cascade="all, delete-orphan")

    state_id = db.Column(db.Integer, db.ForeignKey("project_states.id", ondelete="SET NULL"), nullable=True)
    state = relationship('ProjectState', back_populates="projects")

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    @property
    def instrumentation(self):
        if not self.instrumentation_entries:
            return ""

        return format_instrumentation(self.instrumentation_entries, self.instrumentation_comment)

    @property
    def instrumentation_by_section(self):
        entries = sorted(self.instrumentation_entries, key=lambda e: (
            e.instrument.instrument_section.weight,
            e.instrument.instrument_group.weight,
            e.instrument.weight,
            e.position or 0
        ))

        result = defaultdict(lambda: defaultdict(list))

        for entry in entries:
            section = entry.instrument.instrument_section
            group = entry.instrument.instrument_group

            # Build doubling info
            doublings = entry.doublings
            if doublings:
                doubling_list = []
                doubling_counter = defaultdict(int)
                for d in doublings:
                    abbr = d.doubling_instrument.abbreviation or d.doubling_instrument.name
                    doubling_counter[abbr] += 1

                doubling_text = ", ".join(
                    f"{v}{abbr}" if v > 1 else f"{abbr}" for abbr, v in doubling_counter.items()
                )
            else:
                doubling_text = ""

            result[section][group].append({
                "entry": entry,
                "doubling": doubling_text
            })

        sorted_result = []
        for section in sorted(result.keys(), key=lambda s: s.weight):
            groups = result[section]
            sorted_groups = []
            for group in sorted(groups.keys(), key=lambda g: g.weight):
                sorted_entries = sorted(groups[group], key=lambda e: e["entry"].position or 0)
                sorted_groups.append((group, sorted_entries))

            sorted_result.append((section, sorted_groups))

        return sorted_result


class ProjectState(db.Model):
    __tablename__ = 'project_states'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)

    projects = relationship("Project", back_populates='state')


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    date_start = db.Column(db.Date, nullable=False)
    time_start = db.Column(db.Time)
    date_end = db.Column(db.Date)
    time_end = db.Column(db.Time)

    place = db.Column(db.String(100))
    purpose = db.Column(db.String(100))
    conductor = db.Column(db.String(100))

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    project = relationship('Project', back_populates='events')

    event_type_id = db.Column(db.Integer, db.ForeignKey('event_types.id'))
    event_type = relationship('EventType', back_populates='events')

    project_instrumentation_links = relationship('EventProjectInstrumentation', back_populates='event',
                                                 cascade="all, delete-orphan")

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    @property
    def instrumentation(self):
        if not self.project_instrumentation_links:
            return None

        included_instrumentations = [
            link.project_instrumentation
            for link in self.project_instrumentation_links
            if link.included
        ]

        if not included_instrumentations:
            return None

        return format_instrumentation(included_instrumentations)


class EventType(db.Model):
    __tablename__ = 'event_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    abbr = db.Column(db.String(100), nullable=False)

    events = relationship('Event', back_populates='event_type')


# -----------------------------------------
# Player System (after core)
# -----------------------------------------

# --- Player ---
class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(100))
    email = db.Column(db.String(100))

    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='SET NULL'),
                           unique=True, nullable=True, index=True)
    student = relationship('Student', back_populates='player')

    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id', ondelete='SET NULL'))
    instrument = relationship('Instrument')

    ensemble_links = db.relationship(
        "EnsemblePlayer",
        back_populates="player",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PlayerAssignment(db.Model):
    __tablename__ = 'player_assignments'
    id = db.Column(db.Integer, primary_key=True)

    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    type = db.Column(db.String(50))

    player = relationship('Player')

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'player_assignment'
    }


class PlayerApplication(db.Model):
    __tablename__ = "player_applications"
    id = db.Column(db.Integer, primary_key=True)

    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)

    # Project or Event target (nullable if not both)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)

    player = relationship("Player")
    project = relationship("Project")
    event = relationship("Event")

    # Status: pending / approved / rejected
    status = db.Column(db.String(20), default="pending")

    # Requested instrument (optional override, e.g. "piccolo", "cor anglais")
    requested_instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id'))
    requested_instrument = relationship('Instrument')

    note = db.Column(db.String(255))  # optional note from player (e.g. "I'm free only on Friday")

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewer = db.Column(db.String(100))  # Optional (e.g. who approved/rejected)


class ProjectPlayerAssignment(PlayerAssignment):
    __tablename__ = 'project_player_assignments'
    id = db.Column(db.Integer, db.ForeignKey('player_assignments.id'), primary_key=True)
    instrumentation_id = db.Column(db.Integer, db.ForeignKey('project_instrumentations.id'), nullable=False)

    instrumentation = relationship('ProjectInstrumentation', back_populates='player_assignments')

    __mapper_args__ = {
        'polymorphic_identity': 'project',
    }


class EventPlayerAssignment(PlayerAssignment):
    __tablename__ = 'event_player_assignments'
    id = db.Column(db.Integer, db.ForeignKey('player_assignments.id'), primary_key=True)
    event_project_instrumentation_id = db.Column(db.Integer, db.ForeignKey('event_project_instrumentations.id'),
                                                 nullable=False)

    event_project_instrumentation = relationship('EventProjectInstrumentation')

    __mapper_args__ = {
        'polymorphic_identity': 'event',
    }
