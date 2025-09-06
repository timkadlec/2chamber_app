# models/komorni.py
from . import db


class _ReadOnly:
    def __setattr__(self, k, v):
        if k.startswith("_sa_"):  # allow SQLAlchemy internals
            return super().__setattr__(k, v)
        raise AttributeError("This Oracle model is read-only")


class KomorniHraStud(_ReadOnly, db.Model):
    __bind_key__ = "oracle"  # tells SQLAlchemy to use the Oracle bind
    __tablename__ = "SA_APP_KOMORNI_HRA_STUD_TEST"
    __table_args__ = {"info": {"omit_from_migrations": True}}

    ID_STUDIA = db.Column(db.BigInteger, primary_key=True)
    SEMESTR_ID = db.Column(db.String(6), primary_key=True)

    PRIJMENI = db.Column(db.String(128))
    JMENO = db.Column(db.String(128))
    JMENO_STUDENTA = db.Column(db.String(260))

    ROCNIK = db.Column(db.Integer)
    PROGRAM_TYP = db.Column(db.String(32))  # B nebo N

    FORMA_STUDIA = db.Column(db.String(1))  # 'P'
    STUDUJE = db.Column(db.String(1))  # 'S'

    PROGRAM_KOD = db.Column(db.String(32))
    PROGRAM_NAZEV = db.Column(db.String(256))

    KATEDRA_ID = db.Column(db.Integer)
    KATEDRA_NAZEV = db.Column(db.String(256))

    NAZEV_CS_PRG = db.Column(db.String(256))
    PROGRAM_STARY_NOVY = db.Column(db.String(32))

    OBORST_ID_SPEC = db.Column(db.BigInteger)
    JE_SPECIALIZACE = db.Column(db.String(3))

    PREDMET_KOD = db.Column(db.String(32), primary_key=True)
    PREDMET_NAZEV = db.Column(db.String(256))

    def __repr__(self):
        return f"<KomorniHraStud {self.ID_STUDIA} {self.PREDMET_KOD} {self.SEMESTR_ID}>"


class KomorniHraUcitel(_ReadOnly, db.Model):
    __bind_key__ = "oracle"
    __tablename__ = "SA_APP_KOMORNI_HRA_UCIT_TEST"
    __table_args__ = {"info": {"omit_from_migrations": True}}

    OSOBNI_CISLO = db.Column(db.BigInteger, primary_key=True)
    PREDMET = db.Column(db.String(256), primary_key=True)
    SEM_ID = db.Column(db.String(6), primary_key=True)

    JMENO = db.Column(db.String(128))
    PRIJMENI = db.Column(db.String(128))
    JMENO_UCITELE = db.Column(db.String(260))

    def __repr__(self):
        return f"<KomorniHraUcitel {self.OSOBNI_CISLO} {self.PREDMET} {self.SEM_ID}>"
