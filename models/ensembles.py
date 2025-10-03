from sqlalchemy.orm import relationship, column_property
from models import db
from models.core import Instrumentation, Semester
from datetime import date
from collections import defaultdict
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import case, func


def format_ensemble_instrumentation(instrumentation_entries):
    counter = defaultdict(int)
    order = []

    sorted_entries = sorted(
        instrumentation_entries,
        key=lambda x: (
            x.instrument.weight if x.instrument else 9999,
            x.position or 0
        )
    )

    for entry in sorted_entries:
        abbr = entry.instrument.abbreviation or entry.instrument.name
        abbr = abbr.strip()

        if abbr not in counter:
            order.append(abbr)
        counter[abbr] += 1

    formatted = []
    for abbr in order:
        count = counter[abbr]
        formatted.append(f"{count}{abbr}" if count > 1 else abbr)

    return ", ".join(formatted)


# --- Ensemble ---
class Ensemble(db.Model):
    __tablename__ = 'ensembles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, unique=False)
    active = db.Column(db.Boolean, default=True)

    exception_id = db.Column(db.Integer, db.ForeignKey('student_chamber_application_exceptions.id', ondelete="CASCADE"))
    exception = relationship("StudentChamberApplicationException", back_populates="ensemble", uselist=False)

    semester_links = db.relationship(
        "EnsembleSemester",
        back_populates="ensemble",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    instrumentation_entries = db.relationship(
        "EnsembleInstrumentation",
        back_populates="ensemble",
        cascade="all, delete-orphan",
        order_by="EnsembleInstrumentation.position",
        passive_deletes=True,
    )

    player_links = db.relationship(
        "EnsemblePlayer",
        back_populates="ensemble",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="EnsemblePlayer.player_sort_key"
    )

    teacher_links = db.relationship(
        "EnsembleTeacher",
        back_populates="ensemble",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="EnsembleTeacher.semester_id"
    )

    ensemble_notes = db.relationship(
        "EnsembleNote",
        back_populates="ensemble",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="EnsembleNote.created_at"
    )

    @property
    def semesters(self):
        return sorted((link.semester for link in self.semester_links),
                      key=lambda s: s.start_date or date.min)

    @property
    def semester_ids(self):
        return [link.semester_id for link in self.semester_links]

    def semester_teacher(self, semester_id):
        teacher = EnsembleTeacher.query.filter_by(ensemble_id=self.id, semester_id=semester_id).first()
        return teacher if teacher else None

    @property
    def players(self):
        return [ep.player for ep in self.player_links]

    @property
    def instrumentation(self):
        return format_ensemble_instrumentation(self.instrumentation_entries)

    @property
    def student_count(self):
        return sum(1 for ep in self.player_links if ep.player and ep.player.student is not None)

    @property
    def external_count(self):
        return sum(1 for ep in self.player_links if not ep.player or ep.player.student is None)

    @property
    def health_check(self):
        total = len(self.player_links)
        if total <= 2:
            return "Soubor nesplňuje kritérium minima hráčů."
        percentage_students = round((self.student_count / total) * 100, 2)
        if percentage_students > 50:
            return "OK"
        else:
            return "Soubor obsahuej vysoké procento hostů."

    @hybrid_property
    def health_check_label(self):
        return self.health_check

    @health_check_label.expression
    def health_check_label(cls):
        from models import Player
        # count all players
        total = (
            db.select(func.count(EnsemblePlayer.id))
            .where(EnsemblePlayer.ensemble_id == cls.id)
            .correlate(cls)
            .scalar_subquery()
        )

        # count student players (player.student_id not null)
        student_count = (
            db.select(func.count(EnsemblePlayer.id))
            .join(Player, EnsemblePlayer.player_id == Player.id)
            .where(EnsemblePlayer.ensemble_id == cls.id)
            .where(Player.student_id.isnot(None))
            .correlate(cls)
            .scalar_subquery()
        )

        return case(
            (
                total <= 2,
                "Soubor nesplňuje kritérium minima hráčů."
            ),
            (
                (student_count * 100.0 / func.nullif(total, 0)) > 50,
                "OK"
            ),
            else_="Soubor obsahuej vysoké procento hostů."
        )


class EnsembleInstrumentation(Instrumentation):
    __tablename__ = 'ensemble_instrumentations'
    id = db.Column(db.Integer, db.ForeignKey('instrumentations.id', ondelete="CASCADE"), primary_key=True)

    ensemble_id = db.Column(db.Integer, db.ForeignKey('ensembles.id', ondelete="CASCADE"), nullable=False)
    ensemble = relationship("Ensemble", back_populates="instrumentation_entries")

    # NEW: reverse link to assignments
    player_links = db.relationship(
        "EnsemblePlayer",
        back_populates="ensemble_instrumentation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __mapper_args__ = {
        'polymorphic_identity': 'ensemble_instrumentation',
    }


class EnsembleSemester(db.Model):
    __tablename__ = 'ensemble_semesters'
    id = db.Column(db.Integer, primary_key=True)

    ensemble_id = db.Column(
        db.Integer,
        db.ForeignKey('ensembles.id', ondelete="CASCADE"),  # <-- add ondelete
        nullable=False
    )
    semester_id = db.Column(
        db.Integer,
        db.ForeignKey('semesters.id', ondelete="CASCADE"),  # optional: also cascade if a Semester is removed
        nullable=False
    )

    ensemble = db.relationship("Ensemble", back_populates="semester_links")
    semester = db.relationship("Semester", back_populates="ensemble_links")

    __table_args__ = (
        db.UniqueConstraint('ensemble_id', 'semester_id', name='uq_ensemble_semester'),
    )


class EnsemblePlayer(db.Model):
    __tablename__ = 'ensemble_players'
    id = db.Column(db.Integer, primary_key=True)

    player_id = db.Column(db.Integer, db.ForeignKey('players.id', ondelete='CASCADE'), nullable=True, index=True)
    ensemble_id = db.Column(db.Integer, db.ForeignKey('ensembles.id', ondelete='CASCADE'), nullable=False, index=True)

    ensemble_instrumentation_id = db.Column(
        db.Integer,
        db.ForeignKey('ensemble_instrumentations.id', ondelete='CASCADE'),
        nullable=True,
        index=True
    )

    player = db.relationship("Player", back_populates="ensemble_links")
    ensemble = db.relationship("Ensemble", back_populates="player_links")
    ensemble_instrumentation = db.relationship("EnsembleInstrumentation", back_populates="player_links")

    @hybrid_property
    def player_sort_key(self):
        # Python-level: works when you access ensemble.player_links
        return self.player.instrument.weight if self.player and self.player.instrument else 9999

    @player_sort_key.expression
    def player_sort_key(cls):
        from models import Player, Instrument
        return (
            db.select(Instrument.weight)
            .join(Player, Player.instrument_id == Instrument.id)
            .where(Player.id == cls.player_id)
            .correlate(cls)
            .scalar_subquery()
        )


class EnsembleNote(db.Model):
    __tablename__ = 'ensemble_notes'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    ensemble_id = db.Column(
        db.Integer,
        db.ForeignKey('ensembles.id', ondelete='CASCADE'),
        nullable=False
    )
    ensemble = db.relationship("Ensemble", back_populates="ensemble_notes")

    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    created_by_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_by = db.relationship(
        "User",
        foreign_keys=[created_by_id]
    )



class EnsembleTeacher(db.Model):
    __tablename__ = 'ensemble_teachers'
    id = db.Column(db.Integer, primary_key=True)

    hour_donation = db.Column(db.Float)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id', ondelete='CASCADE'), nullable=True, index=True)
    ensemble_id = db.Column(db.Integer, db.ForeignKey('ensembles.id', ondelete='CASCADE'), nullable=False, index=True)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id', ondelete='CASCADE'), nullable=False, index=True)

    teacher = db.relationship("Teacher", back_populates="ensemble_links")
    ensemble = db.relationship("Ensemble", back_populates="teacher_links")
    semester = db.relationship("Semester")
