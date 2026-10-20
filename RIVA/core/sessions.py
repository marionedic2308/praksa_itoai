"""RIVA - lokalna evidencija prometnih sesija i statističkih rezultata.

Statističke tablice ne pohranjuju registarske oznake niti RTSP vjerodajnice.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "data" / "riva.db"
SESSIONS_DIR = BASE_DIR / "data" / "sessions"


def current_timestamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_sessions():
    """Dodaje nedostajuće tablice, bez brisanja postojećih podataka."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS traffic_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_code TEXT UNIQUE,
                username TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_name TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                duration_seconds REAL,
                status TEXT NOT NULL DEFAULT 'RUNNING',
                total_vehicles INTEGER DEFAULT 0,
                ocr_attempts INTEGER DEFAULT 0,
                ocr_success INTEGER DEFAULT 0,
                notes TEXT
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS session_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES traffic_sessions(id)
                    ON DELETE CASCADE
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS session_statistics (
                session_id INTEGER PRIMARY KEY,
                total_count INTEGER NOT NULL DEFAULT 0,
                correct_count INTEGER NOT NULL DEFAULT 0,
                opposite_count INTEGER NOT NULL DEFAULT 0,
                category_counts TEXT NOT NULL DEFAULT '{}',
                lane_counts TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES traffic_sessions(id)
                    ON DELETE CASCADE
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS vehicle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                track_id TEXT NOT NULL,
                vehicle_type TEXT NOT NULL,
                lane TEXT NOT NULL,
                direction TEXT NOT NULL,
                counted_at TEXT NOT NULL,
                duration_seconds REAL,
                FOREIGN KEY (session_id) REFERENCES traffic_sessions(id)
                    ON DELETE CASCADE
            )
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_vehicle_events_session
            ON vehicle_events(session_id, id)
        """)


def create_session(username, source_type="LIVE", source_name=None, notes=None):
    initialize_sessions()
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Korisničko ime ne smije biti prazno.")
    if source_type not in ("LIVE", "VIDEO"):
        raise ValueError("Izvor mora biti LIVE ili VIDEO.")
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO traffic_sessions
                (username, source_type, source_name, started_at, status, notes)
            VALUES (?, ?, ?, ?, 'RUNNING', ?)
        """, (username.strip(), source_type, source_name,
              current_timestamp(), notes))
        session_id = cursor.lastrowid
        session_code = f"RIVA-{session_id:06d}"
        connection.execute(
            "UPDATE traffic_sessions SET session_code = ? WHERE id = ?",
            (session_code, session_id)
        )
    session_directory = SESSIONS_DIR / session_code
    session_directory.mkdir(parents=True, exist_ok=True)
    return {"id": session_id, "session_code": session_code,
            "directory": str(session_directory)}


def finish_session(session_id, status="COMPLETED", total_vehicles=0,
                   ocr_attempts=0, ocr_success=0, notes=None):
    initialize_sessions()
    if status not in ("COMPLETED", "INTERRUPTED", "FAILED"):
        raise ValueError("Neispravan završni status sesije.")
    values = (total_vehicles, ocr_attempts, ocr_success)
    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError("Statističke vrijednosti moraju biti nenegativni cijeli brojevi.")
    if ocr_success > ocr_attempts:
        raise ValueError("Broj uspješnih OCR očitanja ne može biti veći od pokušaja.")
    with get_connection() as connection:
        session = connection.execute(
            "SELECT started_at, status FROM traffic_sessions WHERE id = ?",
            (session_id,)
        ).fetchone()
        if session is None:
            raise ValueError("Prometna sesija ne postoji.")
        if session["status"] != "RUNNING":
            raise ValueError("Sesija je već završena ili prekinuta.")
        finished_at = current_timestamp()
        duration_seconds = max(0, (
            datetime.fromisoformat(finished_at) -
            datetime.fromisoformat(session["started_at"])
        ).total_seconds())
        connection.execute("""
            UPDATE traffic_sessions
            SET finished_at = ?, duration_seconds = ?, status = ?,
                total_vehicles = ?, ocr_attempts = ?, ocr_success = ?,
                notes = COALESCE(?, notes)
            WHERE id = ?
        """, (finished_at, duration_seconds, status, total_vehicles,
              ocr_attempts, ocr_success, notes, session_id))
    return get_session(session_id)


def get_session(session_id):
    initialize_sessions()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM traffic_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None


def get_recent_sessions(limit=20):
    initialize_sessions()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM traffic_sessions ORDER BY id DESC LIMIT ?",
            (max(1, int(limit)),)
        ).fetchall()
        return [dict(row) for row in rows]


def get_session_statistics():
    """Ukupni pregled svih sesija (postojeći API za dashboard)."""
    initialize_sessions()
    with get_connection() as connection:
        row = connection.execute("""
            SELECT COUNT(*) AS total_sessions,
                COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) AS total_reports,
                COALESCE(SUM(CASE WHEN status = 'COMPLETED'
                    THEN total_vehicles ELSE 0 END), 0) AS total_vehicles,
                COALESCE(SUM(CASE WHEN status = 'COMPLETED'
                    THEN ocr_attempts ELSE 0 END), 0) AS total_ocr_attempts,
                COALESCE(SUM(CASE WHEN status = 'COMPLETED'
                    THEN ocr_success ELSE 0 END), 0) AS total_ocr_success
            FROM traffic_sessions
        """).fetchone()
        return dict(row)


def add_session_file(session_id, file_type, file_path):
    initialize_sessions()
    if get_session(session_id) is None:
        raise ValueError("Nije moguće dodati datoteku: sesija ne postoji.")
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Datoteka ne postoji: {file_path}")
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO session_files (session_id, file_type, file_path, created_at)
            VALUES (?, ?, ?, ?)
        """, (session_id, file_type, str(path.resolve()), current_timestamp()))
        return cursor.lastrowid


def get_session_files(session_id):
    initialize_sessions()
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM session_files WHERE session_id = ? ORDER BY id DESC
        """, (session_id,)).fetchall()
        return [dict(row) for row in rows]


def _nonnegative_count(value, field):
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} mora biti nenegativni cijeli broj.")
    return value


def _count_map(value, field):
    if not isinstance(value, dict):
        raise ValueError(f"{field} mora biti rječnik.")
    for key, count in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field} mora imati tekstualne nazive.")
        _nonnegative_count(count, field)
    return json.dumps(value, ensure_ascii=False)


def save_session_statistics(session_id, statistics):
    """Spremi ili ažuriraj statistiku jedne sesije (bez OCR podataka)."""
    initialize_sessions()
    if not isinstance(statistics, dict):
        raise ValueError("Statistika mora biti rječnik.")
    total = _nonnegative_count(statistics.get("total_count", 0), "total_count")
    correct = _nonnegative_count(statistics.get("correct_count", 0), "correct_count")
    opposite = _nonnegative_count(statistics.get("opposite_count", 0), "opposite_count")
    if correct + opposite > total:
        raise ValueError("Zbroj smjerova ne smije biti veći od ukupnog broja.")
    categories = _count_map(statistics.get("category_counts", {}), "category_counts")
    lanes = _count_map(statistics.get("lane_counts", {}), "lane_counts")
    with get_connection() as connection:
        row = connection.execute(
            "SELECT status FROM traffic_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Prometna sesija ne postoji.")
        if row["status"] != "RUNNING":
            raise ValueError("Statistika se može mijenjati samo tijekom aktivne sesije.")
        connection.execute("""
            INSERT INTO session_statistics
                (session_id, total_count, correct_count, opposite_count,
                 category_counts, lane_counts, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                total_count = excluded.total_count,
                correct_count = excluded.correct_count,
                opposite_count = excluded.opposite_count,
                category_counts = excluded.category_counts,
                lane_counts = excluded.lane_counts,
                updated_at = excluded.updated_at
        """, (session_id, total, correct, opposite, categories, lanes,
              current_timestamp()))
    return get_saved_session_statistics(session_id)


def get_saved_session_statistics(session_id):
    """Vrati statistiku u obliku koji očekuje ResultsPage.set_results()."""
    initialize_sessions()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM session_statistics WHERE session_id = ?", (session_id,)
        ).fetchone()
    if row is None:
        return None
    return {
        "total_count": row["total_count"],
        "correct_count": row["correct_count"],
        "opposite_count": row["opposite_count"],
        "category_counts": json.loads(row["category_counts"]),
        "lane_counts": json.loads(row["lane_counts"]),
    }


def add_vehicle_event(session_id, event):
    """Dodaj jedan evidentirani prolazak bez registarske oznake."""
    initialize_sessions()
    if not isinstance(event, dict):
        raise ValueError("Događaj mora biti rječnik.")
    required = ("track_id", "vehicle_type", "lane", "direction", "counted_at")
    values = []
    for key in required:
        value = event.get(key)
        if value is None or not str(value).strip():
            raise ValueError(f"Nedostaje podatak: {key}")
        values.append(str(value).strip())
    duration = event.get("duration_seconds")
    if duration is not None:
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not 0 <= duration < float("inf"):
            raise ValueError("Trajanje mora biti nenegativan konačan broj.")
        duration = float(duration)
    with get_connection() as connection:
        row = connection.execute(
            "SELECT status FROM traffic_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Prometna sesija ne postoji.")
        if row["status"] != "RUNNING":
            raise ValueError("Prolasci se mogu dodavati samo aktivnoj sesiji.")
        cursor = connection.execute("""
            INSERT INTO vehicle_events
                (session_id, track_id, vehicle_type, lane, direction,
                 counted_at, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, *values, duration))
        return cursor.lastrowid


def get_vehicle_events(session_id):
    """Vrati prolaske jedne sesije, kronološki prema upisu."""
    initialize_sessions()
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT track_id, vehicle_type, lane, direction,
                   counted_at, duration_seconds
            FROM vehicle_events WHERE session_id = ? ORDER BY id ASC
        """, (session_id,)).fetchall()
        return [dict(row) for row in rows]
