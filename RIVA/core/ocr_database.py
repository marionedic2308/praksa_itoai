"""Privatna evidencija OCR rezultata za RIVA sesije."""

import sqlite3
from pathlib import Path

from core.sessions import DATABASE_PATH


def initialize_ocr_database():
    """Stvori zasebnu tablicu za OCR bez izmjene postojecih tablica."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS ocr_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL UNIQUE,
                registration_text TEXT,
                confidence REAL,
                review_status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id)
                    REFERENCES vehicle_events(id)
                    ON DELETE RESTRICT,
                CHECK (
                    confidence IS NULL OR
                    (confidence >= 0 AND confidence <= 1)
                ),
                CHECK (
                    review_status IN (
                        'PENDING',
                        'CONFIRMED',
                        'REJECTED'
                    )
                )
            )
        """)


def get_ocr_database_status():
    """Vrati broj OCR zapisa bez otkrivanja registracija."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM ocr_results"
        ).fetchone()
        return {"ocr_records": row[0]}

def save_ocr_result(event_id, registration_text, confidence):
    """Spremi OCR rezultat uz prolazak; ne potvrduje automatski tocnost."""
    if type(event_id) is not int or event_id <= 0:
        raise ValueError("Neispravan ID prolaska.")

    if registration_text is not None:
        if not isinstance(registration_text, str):
            raise ValueError("OCR tekst mora biti niz znakova.")
        registration_text = registration_text.strip().upper()
        if not registration_text:
            registration_text = None

    if confidence is not None:
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("Pouzdanost mora biti broj.")
        if not 0 <= confidence <= 1:
            raise ValueError("Pouzdanost mora biti izmedu 0 i 1.")
        confidence = float(confidence)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("""
            INSERT INTO ocr_results
                (event_id, registration_text, confidence, review_status)
            VALUES (?, ?, ?, 'PENDING')
        """, (event_id, registration_text, confidence))



# Rucne intervencije cuvaju prethodne vrijednosti u zasebnoj povijesti.
def initialize_manual_ocr():
    with sqlite3.connect(DATABASE_PATH, timeout=10) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(ocr_results)")}
        if "entry_source" not in columns:
            conn.execute("ALTER TABLE ocr_results ADD COLUMN entry_source TEXT NOT NULL DEFAULT 'OCR'")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ocr_manual_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                previous_registration TEXT,
                new_registration TEXT NOT NULL,
                previous_status TEXT,
                previous_confidence REAL,
                previous_source TEXT,
                changed_by TEXT,
                changed_at TEXT NOT NULL,
                change_type TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES vehicle_events(id)
            )
        """)


def save_manual_registration(event_id, registration, username=None):
    import re
    from datetime import datetime
    if type(event_id) is not int or event_id <= 0:
        raise ValueError("Neispravan ID prolaska.")
    if not isinstance(registration, str):
        raise ValueError("Neispravna registracija.")
    registration = registration.strip().upper()
    if not re.fullmatch(r"[A-Z0-9ČĆŽŠĐ-]{3,16}", registration):
        raise ValueError("Registracija mora imati 3-16 znakova (slova, brojevi, crtica).")
    initialize_manual_ocr()
    with sqlite3.connect(DATABASE_PATH, timeout=10) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN IMMEDIATE")
        exists = conn.execute("SELECT 1 FROM vehicle_events WHERE id = ?", (event_id,)).fetchone()
        if not exists:
            raise ValueError("Odabrani prolazak ne postoji.")
        previous = conn.execute("""
            SELECT registration_text, confidence, review_status, entry_source
            FROM ocr_results WHERE event_id = ?
        """, (event_id,)).fetchone()
        change_type = "MANUAL_CORRECTION" if previous else "MANUAL_ENTRY"
        conn.execute("""
            INSERT INTO ocr_manual_history
                (event_id, previous_registration, new_registration,
                 previous_status, previous_confidence, previous_source,
                 changed_by, changed_at, change_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_id, previous[0] if previous else None, registration,
              previous[2] if previous else None, previous[1] if previous else None,
              previous[3] if previous else None, username,
              datetime.now().astimezone().isoformat(timespec="seconds"), change_type))
        if previous:
            conn.execute("""
                UPDATE ocr_results
                SET registration_text = ?, confidence = NULL,
                    review_status = 'CONFIRMED', entry_source = 'MANUAL_CORRECTION'
                WHERE event_id = ?
            """, (registration, event_id))
        else:
            conn.execute("""
                INSERT INTO ocr_results
                    (event_id, registration_text, confidence, review_status, entry_source)
                VALUES (?, ?, NULL, 'CONFIRMED', 'MANUAL_ENTRY')
            """, (event_id, registration))
    return change_type


# RIVA OCR - trajne ru?ne odluke
def save_review_decision(event_id, decision, username=None):
    from datetime import datetime

    if decision not in ("CONFIRMED", "REJECTED"):
        raise ValueError("Neispravna OCR odluka.")

    initialize_manual_ocr()

    with sqlite3.connect(DATABASE_PATH, timeout=10) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN IMMEDIATE")

        exists = conn.execute(
            "SELECT 1 FROM vehicle_events WHERE id=?",
            (event_id,)
        ).fetchone()

        if not exists:
            raise ValueError("Prolazak ne postoji.")

        previous = conn.execute("""
            SELECT registration_text, review_status, entry_source
            FROM ocr_results WHERE event_id=?
        """, (event_id,)).fetchone()

        if decision == "CONFIRMED":
            if not previous or not previous[0]:
                raise ValueError(
                    "Nema registracije za potvrdu. Koristi ru?ni unos."
                )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS ocr_review_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                previous_status TEXT,
                new_status TEXT NOT NULL,
                changed_by TEXT,
                changed_at TEXT NOT NULL
            )
        """)

        if previous:
            source = (
                "MANUAL_REJECTION" if decision == "REJECTED"
                else (
                    previous[2]
                    if previous[2] in (
                        "MANUAL_ENTRY", "MANUAL_CORRECTION"
                    )
                    else "MANUAL_CONFIRMATION"
                )
            )
            conn.execute("""
                UPDATE ocr_results
                SET review_status=?, entry_source=?
                WHERE event_id=?
            """, (decision, source, event_id))
        else:
            conn.execute("""
                INSERT INTO ocr_results
                (event_id, registration_text, confidence,
                 review_status, entry_source)
                VALUES (?, NULL, NULL, 'REJECTED',
                        'MANUAL_REJECTION')
            """, (event_id,))

        conn.execute("""
            INSERT INTO ocr_review_history
            (event_id, previous_status, new_status,
             changed_by, changed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_id,
            previous[1] if previous else None,
            decision,
            username,
            datetime.now().astimezone().isoformat(
                timespec="seconds"
            )
        ))

    return decision
