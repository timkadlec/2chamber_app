from . import db
from sqlalchemy.orm import relationship
from models.ensembles import Ensemble, EnsembleSemester, EnsemblePlayer
from sqlalchemy import func

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

    @property
    def full_name(self):
        if self.student_id:
            return f"{self.student.last_name} {self.student.first_name}"
        else:
            return f"{self.last_name} {self.first_name}"

    @property
    def is_guest(self):
        return self.student_id is None

    def ensembles_in_semester(self, semester_id: int):
        """
        Return all ensembles where this player is assigned in the given semester.
        Uses DISTINCT because the player can occupy multiple slots (doublings) in one ensemble.
        """
        return (
            db.session.query(Ensemble)
            .join(EnsemblePlayer, EnsemblePlayer.ensemble_id == Ensemble.id)
            .join(EnsembleSemester,
                  EnsembleSemester.ensemble_id == Ensemble.id)  # safety: ensure ensemble is linked to semester
            .filter(
                EnsemblePlayer.player_id == self.id,
                EnsemblePlayer.semester_id == semester_id,
                EnsembleSemester.semester_id == semester_id,
            )
            .distinct()
            .all()
        )

    def ensemble_count_in_semester(self, semester_id: int) -> int:
        """
        Return number of DISTINCT ensembles this player is assigned to in the given semester.
        (Not number of EnsemblePlayer rows.)
        """
        return (
                db.session.query(func.count(func.distinct(EnsemblePlayer.ensemble_id)))
                .join(EnsembleSemester, EnsembleSemester.ensemble_id == EnsemblePlayer.ensemble_id)  # safety
                .filter(
                    EnsemblePlayer.player_id == self.id,
                    EnsemblePlayer.semester_id == semester_id,
                    EnsembleSemester.semester_id == semester_id,
                )
                .scalar()
                or 0
        )
