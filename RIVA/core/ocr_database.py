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

