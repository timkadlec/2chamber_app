import re
from flask import flash
from models import db
from models.core import Instrument, DoublingInstrumentation
from models import CompositionInstrumentation
from collections import defaultdict
from sqlalchemy import func


def normalize_abbr(abbr):
    return abbr.lower().replace('.', '').replace(' ', '').replace('-', '')


def find_instrument_by_abbr(abbr, strict=True):
    """
    Finds an instrument by performing a case-insensitive search
    on the existing 'abbreviation' column.
    """
    # 1. Normalize the user's input string (e.g., "Pf." -> "pf")
    normalized_input = normalize_abbr(abbr)

    # 2. Use func.lower() to make the database column lowercase before comparing
    instrument = Instrument.query.filter(
        func.lower(Instrument.abbreviation) == normalized_input
    ).first()

    if instrument:
        return instrument

    if strict:
        raise ValueError(f"Instrument abbreviation not found: '{abbr}'")

    return None


def clean_line(input_line):
    cleaned = re.sub(r'[\u200b\u200c\u200d\u2060\ufeff]', '', input_line)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()


def split_instrumentation_line(input_line):
    input_line = clean_line(input_line)

    parts = []
    current = ''
    parentheses_level = 0

    for char in input_line:
        if char == ',' and parentheses_level == 0:
            parts.append(current.strip())
            current = ''
        else:
            if char == '(':
                parentheses_level += 1
            elif char == ')':
                parentheses_level -= 1
            current += char

    if current:
        parts.append(current.strip())

    return parts


def assign_doublings(players, items, separate, find_instrument_func):
    numbered = []
    non_numbered = []

    for item in items:
        item = item.strip()
        if re.match(r"\d+", item):
            numbered.append(item)
        else:
            non_numbered.append(item)

    # Numbered → reverse order
    for item in numbered:
        m = re.match(r"(\d+)([a-zA-Z .]+)", item)
        if not m:
            continue
        count = int(m.group(1))
        abbr = m.group(2).strip()

        instrument = find_instrument_func(abbr, strict=False)
        targets = sorted(players, key=lambda p: p.position, reverse=True)[:count]

        if instrument:
            for p in targets:
                existing = DoublingInstrumentation.query.filter_by(
                    instrumentation_id=p.id,
                    doubling_instrument_id=instrument.id
                ).first()

                if not existing:
                    db.session.add(DoublingInstrumentation(
                        instrumentation_id=p.id,
                        doubling_instrument_id=instrument.id,
                        separate=separate
                    ))

    # Non-numbered → last player
    target_player = sorted(players, key=lambda p: p.position)[-1] if players else None

    if not target_player and players:
        target_player = next((p for p in players if p.concertmaster), None)

    for abbr in non_numbered:
        abbr = abbr.strip()
        instrument = find_instrument_func(abbr, strict=False)

        if instrument and target_player:
            existing = DoublingInstrumentation.query.filter_by(
                instrumentation_id=target_player.id,
                doubling_instrument_id=instrument.id
            ).first()

            if not existing:
                db.session.add(DoublingInstrumentation(
                    instrumentation_id=target_player.id,
                    doubling_instrument_id=instrument.id,
                    separate=separate
                ))
        elif target_player:
            # Unknown instrument → add comment
            target_player.comment = ((target_player.comment or '') + f" {abbr}").strip()
            db.session.add(target_player)


def process_chamber_instrumentation_line(composition_id, line, clear_existing=True):
    # STEP 1: Log function entry and initial inputs
    print(f"\n[DEBUG] --- Starting process_chamber_instrumentation_line ---")
    print(f"[DEBUG] Composition ID: {composition_id}")
    print(f"[DEBUG] Raw input line: '{line}'")

    if clear_existing:
        # STEP 2: Log the deletion of existing records
        existing_count = CompositionInstrumentation.query.filter_by(composition_id=composition_id).count()
        print(f"[DEBUG] 'clear_existing' is True. Deleting {existing_count} existing instrumentation entries.")
        CompositionInstrumentation.query.filter_by(composition_id=composition_id).delete()

    # STEP 3: Log the result of splitting the input line
    instruments = split_instrumentation_line(line)
    print(f"[DEBUG] Line split into parts: {instruments}")

    grouped = defaultdict(list)

    # STEP 4: Loop through each part and log the parsing process
    print("[DEBUG] ---> Looping through each instrument part...")
    for abbr in instruments:
        abbr = abbr.strip()
        print(f"\n[DEBUG]   Processing part: '{abbr}'")

        if not abbr:
            print("[DEBUG]   Skipping empty part.")
            continue

        match = re.match(r"(\d+)?([a-zA-Z .]+)", abbr)
        count = int(match.group(1)) if match and match.group(1) else 1
        pure_abbr = match.group(2).strip() if match else abbr

        print(f"[DEBUG]   Parsed -> Count: {count}, Abbreviation: '{pure_abbr}'")

        instrument = find_instrument_by_abbr(pure_abbr, strict=False)

        if instrument:
            print(f"[DEBUG]   SUCCESS: Found instrument '{instrument.name}' (ID: {instrument.id}) in database.")
            grouped[instrument.id].extend([instrument] * count)
        else:
            # This is a critical message to watch for
            print(f"[DEBUG]   WARNING: Instrument NOT FOUND for abbreviation '{pure_abbr}'.")
            flash(f"Instrument '{abbr}' not recognized", "warning")

    # STEP 5: Log the final grouped structure before creating DB objects
    print("\n[DEBUG] ---> Finished parsing. Final grouping:")
    print(f"[DEBUG] {dict(grouped)}")

    # STEP 6: Loop through the groups and log the creation of each DB entry
    print("[DEBUG] ---> Creating new database entries...")
    for instrument_id, entries in grouped.items():
        count = len(entries)
        for i in range(count):
            # Create the object but don't add it to the session just yet
            entry_data = {
                "composition_id": composition_id,
                "instrument_id": instrument_id,
                "position": (i + 1) if count > 1 else None,
                "concertmaster": (i == 0)
            }
            print(f"[DEBUG]   Staging entry for session: {entry_data}")

            # Now create and add the object
            entry = CompositionInstrumentation(**entry_data)
            db.session.add(entry)

    print("[DEBUG] --- Finished process_chamber_instrumentation_line ---\n")
