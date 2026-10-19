
import sqlite3
from datetime import datetime
from pathlib import Path


# --------------------------------------------------
# RIVA - EVIDENCIJA AKTIVNOSTI SUSTAVA (AUDIT LOG)
# --------------------------------------------------
# Svi događaji spremaju se u lokalnu SQLite bazu.
# Podaci ostaju sačuvani nakon zatvaranja aplikacije.
# --------------------------------------------------

# Glavna mapa aplikacije RIVA.
BASE_DIR = Path(__file__).resolve().parent.parent

# Lokacija baze podataka.
DATABASE_PATH = BASE_DIR / "data" / "riva.db"


def get_connection():
    """
    Otvara vezu s lokalnom SQLite bazom.

    Ako mapa za podatke ne postoji,
    automatski će se stvoriti.
    """

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    return sqlite3.connect(DATABASE_PATH, timeout=10)


def initialize_audit():
    """
    Stvara tablicu audit_log ako još ne postoji.

    Postojeći zapisi neće se obrisati.
    """

    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                username TEXT,
                event_type TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL
            )
        """)


def log_event(event_type, username=None, description="", status="INFO"):
    """
    Sprema novi događaj u evidenciju aktivnosti.

    Primjeri događaja:
    - LOGIN_SUCCESS
    - LOGIN_FAILED
    - LOGOUT
    - CAMERA_CONNECTED
    - OCR_STARTED
    - OCR_STOPPED
    - REPORT_GENERATED

    Lozinke i osjetljivi podaci ne smiju se
    zapisivati u opis događaja.
    """

    # Osiguravamo da tablica postoji.
    initialize_audit()

    # Lokalni datum i vrijeme događaja.
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")

    # Spremanje događaja u bazu podataka.
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO audit_log
                (timestamp, username, event_type, description, status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp,
            username,
            event_type,
            description,
            status
        ))


def get_recent_events(limit=50):
    """
    Dohvaća posljednje zabilježene događaje.

    Rezultati su poredani od najnovijeg
    prema najstarijem događaju.
    """

    with get_connection() as connection:
        cursor = connection.execute("""
            SELECT id, timestamp, username,
                   event_type, description, status
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
        """, (max(1, int(limit)),))

        return cursor.fetchall()
