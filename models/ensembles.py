from sqlalchemy.orm import relationship
from models import db
from models.core import Instrumentation, Semester


class EnsembleSemester(db.Model):
    __tablename__ = 'ensemble_semesters'
    id = db.Column(db.Integer, primary_key=True)

    ensemble_id = db.Column(db.Integer, db.ForeignKey('ensembles.id'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)

    ensemble = db.relationship("Ensemble", back_populates="semester_links")
    semester = db.relationship("Semester", back_populates="ensemble_links")


class Ensemble(db.Model):
    __tablename__ = 'ensembles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, unique=True)
    active = db.Column(db.Boolean, default=True)

    semester_links = db.relationship(
        "EnsembleSemester",
        back_populates="ensemble",
        cascade="all, delete-orphan"
    )

    instrumentation_entries = db.relationship(
        "EnsembleInstrumentation",
        back_populates="ensemble",
        cascade="all, delete-orphan",
        order_by="EnsembleInstrumentation.position",
        passive_deletes=True,
    )

    @property
    def semesters(self):
        return [link.semester for link in self.semester_links]


class EnsembleInstrumentation(Instrumentation):
    __tablename__ = 'ensemble_instrumentations'
    id = db.Column(db.Integer, db.ForeignKey('instrumentations.id', ondelete="CASCADE"), primary_key=True)

    ensemble_id = db.Column(db.Integer, db.ForeignKey('ensembles.id', ondelete="CASCADE"), nullable=False)
    ensemble = relationship("Ensemble", back_populates="instrumentation_entries")

    __mapper_args__ = {
        'polymorphic_identity': 'ensemble_instrumentation',
    }
