from models.core import db, InstrumentSection, InstrumentGroup, Instrument, ProjectState, EventType
from models import User, StudentChamberApplicationStatus
from models import Composition, Composer, CompositionInstrumentation
from werkzeug.security import generate_password_hash


def seed_instruments():
    if not InstrumentSection.query.first():
        # Instrument Sections
        sections = [
            InstrumentSection(id=1, name="Smyčce", weight=10),
            InstrumentSection(id=2, name="Dřeva", weight=20),
            InstrumentSection(id=3, name="Žestě", weight=30),
            InstrumentSection(id=4, name="Bicí", weight=40),
            InstrumentSection(id=5, name="Sbor", weight=50),
            InstrumentSection(id=6, name="Ostatní", weight=60),
        ]
        db.session.bulk_save_objects(sections)
        db.session.commit()
        print("✅ Instrument sections seeded successfully.")

    # Instrument Groups
    if not InstrumentGroup.query.first():
        groups = [
            InstrumentGroup(id=1, name="Housle I", instrument_section_id=1, weight=10),
            InstrumentGroup(id=2, name="Housle II", instrument_section_id=1, weight=20),
            InstrumentGroup(id=3, name="Violy", instrument_section_id=1, weight=30),
            InstrumentGroup(id=4, name="Violoncella", instrument_section_id=1, weight=40),
            InstrumentGroup(id=5, name="Kontrabasy", instrument_section_id=1, weight=50),
            InstrumentGroup(id=6, name="Flétny", instrument_section_id=2, weight=60),
            InstrumentGroup(id=7, name="Hoboje", instrument_section_id=2, weight=70),
            InstrumentGroup(id=8, name="Klarinety", instrument_section_id=2, weight=80),
            InstrumentGroup(id=9, name="Fagoty", instrument_section_id=2, weight=90),
            InstrumentGroup(id=10, name="Lesní rohy", instrument_section_id=3, weight=100),
            InstrumentGroup(id=11, name="Trubky", instrument_section_id=3, weight=110),
            InstrumentGroup(id=12, name="Pozouny", instrument_section_id=3, weight=120),
            InstrumentGroup(id=13, name="Tuby", instrument_section_id=3, weight=130),
            InstrumentGroup(id=14, name="Tympány", instrument_section_id=4, weight=140),
            InstrumentGroup(id=15, name="Perkuse", instrument_section_id=4, weight=150),
            InstrumentGroup(id=16, name="Sbor", instrument_section_id=5, weight=160),
            InstrumentGroup(id=17, name="Harfa", instrument_section_id=6, weight=170),
            InstrumentGroup(id=18, name="Klavír", instrument_section_id=6, weight=180),
            InstrumentGroup(id=19, name="Ostatní", instrument_section_id=6, weight=190),
        ]
        db.session.bulk_save_objects(groups)
        db.session.commit()
        print("✅ Instrument groups seeded successfully.")

    # Instruments (Partial for readability)
    if not Instrument.query.first():
        instruments = [
            Instrument(id=2, name="Flétna", name_en="Flute", abbreviation="Fl", instrument_section_id=2,
                       instrument_group_id=6,
                       weight=15,
                       is_primary=True),
            Instrument(id=5, name="Zobcová flétna", abbreviation="Zfl", instrument_section_id=2,
                       instrument_group_id=6, weight=30, is_primary=False),
            Instrument(id=10, name="Hoboj", name_en="Oboe", abbreviation="Ob", instrument_section_id=2,
                       instrument_group_id=7,
                       weight=60,
                       is_primary=False),
            Instrument(id=13, name="Klarinet", name_en="Clarinet", abbreviation="Cl", instrument_section_id=2,
                       instrument_group_id=8,
                       weight=75,
                       is_primary=True),
            Instrument(id=17, name="Saxofon", abbreviation="Sax", instrument_section_id=2,
                       instrument_group_id=8,
                       weight=95, is_primary=False),
            Instrument(id=19, name="Fagot", name_en="Bassoon", abbreviation="Fag", instrument_section_id=2,
                       instrument_group_id=9,
                       weight=110,
                       is_primary=True),
            Instrument(id=21, name="Lesní roh", name_en="Horn", abbreviation="Hn", instrument_section_id=3,
                       instrument_group_id=10,
                       weight=120, is_primary=True),
            Instrument(id=23, name="Trubka", name_en="Trumpet", abbreviation="Tr", instrument_section_id=3,
                       instrument_group_id=11,
                       weight=130,
                       is_primary=True),
            Instrument(id=24, name="Pozoun", name_en="Trombone", abbreviation="Tbn", instrument_section_id=3,
                       instrument_group_id=12,
                       weight=140, is_primary=True),
            Instrument(id=26, name="Tuba", abbreviation="Tba", instrument_section_id=3, instrument_group_id=13,
                       weight=150,
                       is_primary=True),
            Instrument(id=29, name="Housle", name_en="Violin", abbreviation="Vln", instrument_section_id=1,
                       instrument_group_id=1),
            Instrument(id=32, name="Viola", name_en="Viola", abbreviation="Vla", instrument_section_id=1,
                       instrument_group_id=3,
                       weight=220,
                       is_primary=True),
            Instrument(id=33, name="Violoncello", name_en="Violoncello", abbreviation="Vcl", instrument_section_id=1,
                       instrument_group_id=4,
                       weight=230, is_primary=True),
            Instrument(id=34, name="Kontrabas", name_en="Double Bass", abbreviation="Cb", instrument_section_id=1,
                       instrument_group_id=5,
                       weight=240, is_primary=True),
            Instrument(id=39, name="Klavír", abbreviation="Pf", instrument_section_id=6, instrument_group_id=18,
                       weight=280,
                       is_primary=True),
            Instrument(id=41, name="Harfa", name_en="Harp", abbreviation="Arp", instrument_section_id=6,
                       instrument_group_id=17,
                       weight=270,
                       is_primary=True),
            Instrument(id=42, name="Kytara", name_en="Guitar", abbreviation="Gtr", instrument_section_id=6,
                       instrument_group_id=19,
                       weight=300, is_primary=False),
            Instrument(id=46, name="Akordeon", abbreviation="Acc", instrument_section_id=6, instrument_group_id=18,
                       weight=55, is_primary=True),
            Instrument(id=49, name="Cembalo", name_en="Cemballo", abbreviation="Cemb", instrument_section_id=6,
                       instrument_group_id=18,
                       weight=288, is_primary=True),
            Instrument(id=50, name="Varhany", name_en="Organ", abbreviation="org", instrument_section_id=6,
                       instrument_group_id=18,
                       weight=289, is_primary=True),
        ]
        db.session.bulk_save_objects(instruments)
        db.session.commit()
        print("✅ Instruments seeded successfully.")

    if not ProjectState.query.first():
        states = [
            ProjectState(id=1, name="Draft"),
            ProjectState(id=2, name="Publikovaný"),
            ProjectState(id=3, name="Archivovaný"),
            ProjectState(id=4, name="Zrušený"),
            ProjectState(id=5, name="Blokace")
        ]
        db.session.bulk_save_objects(states)
        db.session.commit()
        print("✅ Project states seeded successfully.")

    if not EventType.query.first():
        types = [
            EventType(id=1, name="Zkouška", abbr="Zk"),
            EventType(id=2, name="Natáčení", abbr="Nat"),
            EventType(id=3, name="Generální zkouška", abbr="Gz"),
            EventType(id=4, name="Koncert", abbr="Kon"),
            EventType(id=5, name="Zvuková zkouška", abbr="Zvuk"),
        ]
        db.session.bulk_save_objects(types)
        db.session.commit()
        print("✅ Event types seeded successfully.")

    # Example seeding for roles

    else:
        print("ℹ️ Database already seeded. Skipping seeding.")
        return


def seed_composers():
    if not Composer.query.first():
        # Instrument Sections
        composers = [
            Composer(first_name="Antonín", last_name="Dvořák"),
            Composer(first_name="Wolfgang Amadeus", last_name="Mozart"),
            Composer(first_name="Bedřich", last_name="Smetana"),
            Composer(first_name="Johannes", last_name="Brahms"),
            Composer(first_name="Ludvig van", last_name="Beethoven"),
            Composer(first_name="Felix", last_name="Mendelssohn-Bartholdy"),
            Composer(first_name="Joseph", last_name="Haydn"),
            Composer(first_name="Francis", last_name="Poulenc"),
        ]
        db.session.bulk_save_objects(composers)
        db.session.commit()
        print("✅ Composers seeded successfully.")
    else:
        print("ℹ️ Composer/Compositions already seeded. Skipping seeding.")
        return


def seed_basic_compositions():
    if Composition.query.first():
        print("ℹ️ Compositions already exist. Skipping seeding.")
        return

    # Fetch composers
    mozart = Composer.query.filter(Composer.last_name.ilike("Mozart")).first()
    beethoven = Composer.query.filter(Composer.last_name.ilike("Beethoven")).first()
    dvorak = Composer.query.filter(Composer.last_name.ilike("Dvořák")).first()

    # Ensure all composers are found
    if not all([mozart, beethoven, dvorak]):
        print("❌ One or more required composers are missing in the database.")
        return

    compositions = [
        Composition(name="Dvě serenády", type="chamber", year=1875, durata=25,
                    description="Serenády pro smyčcové nástroje", composer_id=dvorak.id),
        Composition(name="Flute Quartet in D major, K. 285", type="chamber", year=1777, durata=20,
                    description="Mozartův kvartet pro flétnu a smyčce", composer_id=mozart.id),
        Composition(name="Septet in E-flat major, Op. 20", type="chamber", year=1800, durata=40,
                    description="Beethovenův septet", composer_id=beethoven.id),
    ]

    db.session.bulk_save_objects(compositions)
    db.session.commit()
    print("✅ Compositions seeded.")


def seed_chamber_application_statuses():
    if StudentChamberApplicationStatus.query.first():
        print("Application statuses already exist. Skipping seeding.")
        return

    statuses = [
        StudentChamberApplicationStatus(name='Založeno', description='Žádost byla založena.'),
        StudentChamberApplicationStatus(name='Schváleno', description='Žádost posouzena a schválena.'),
        StudentChamberApplicationStatus(name='Zamítnuto', description='Žádost byla zamítnuta.')

    ]

    db.session.bulk_save_objects(statuses)
    db.session.commit()
    print("Application statuses seeded.")
