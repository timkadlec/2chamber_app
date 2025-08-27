from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from models import db
from models.core import Instrumentation


# -----------------------------------------
# Library
# -----------------------------------------

class Composer(db.Model):
    __tablename__ = 'composers'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(256), nullable=False)
    last_name = db.Column(db.String(256), nullable=False)

    compositions = relationship(
        'Composition',
        back_populates='composer',
        order_by='Composition.name',
        cascade='all, delete-orphan'
    )

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def composition_count(self):
        return len(self.compositions)


def format_chamber_instrumentation(instrumentation_entries):
    from collections import defaultdict

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


class Composition(db.Model):
    __tablename__ = 'compositions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    type = db.Column(db.String(100), nullable=True)
    year = db.Column(db.Integer)
    durata = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    composer_id = db.Column(db.Integer, ForeignKey('composers.id'), nullable=False)

    composer = relationship('Composer', back_populates='compositions')
    instrumentation_entries = relationship(
        "CompositionInstrumentation",
        back_populates="composition",
        cascade="all, delete-orphan"
    )

    @property
    def chamber_instrumentation(self):
        if not self.instrumentation_entries:
            return ""
        return format_chamber_instrumentation(self.instrumentation_entries)


class CompositionInstrumentation(Instrumentation):
    __tablename__ = 'composition_instrumentations'
    id = db.Column(db.Integer, db.ForeignKey('instrumentations.id'), primary_key=True)

    composition_id = db.Column(db.Integer, db.ForeignKey('compositions.id'), nullable=False)

    composition = relationship("Composition", back_populates="instrumentation_entries")

    __mapper_args__ = {
        'polymorphic_identity': 'composition_instrumentation',
    }
