
import sqlite3
from datetime import datetime
from pathlib import Path


# ============================================================
# RIVA - EVIDENCIJA PROMETNIH SESIJA
# ============================================================
# Modul omogućuje:
# - stvaranje nove prometne sesije
# - bilježenje početka i završetka analize
# - trajno spremanje rezultata
# - evidentiranje datoteka povezanih sa sesijom
# - dohvat prethodnih analiza
#
# Podaci se spremaju u postojeću SQLite bazu riva.db.
# Originalni Test 10 ostaje potpuno netaknut.
# ============================================================


# Glavna mapa aplikacije RIVA.
BASE_DIR = Path(__file__).resolve().parent.parent

# Postojeća SQLite baza.
DATABASE_PATH = BASE_DIR / "data" / "riva.db"

# Mapa za rezultate pojedinih sesija.
SESSIONS_DIR = BASE_DIR / "data" / "sessions"


def current_timestamp():
    """Vraća trenutačni datum i vrijeme s vremenskom zonom."""

    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


def get_connection():
    """Otvara vezu s lokalnom SQLite bazom."""

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    # Uključujemo provjeru povezanosti tablica.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ============================================================
# INICIJALIZACIJA BAZE
# ============================================================

def initialize_sessions():
    """
    Stvara tablice prometnih sesija i pripadajućih datoteka.

    CREATE TABLE IF NOT EXISTS osigurava da postojeći
    podaci ostaju sačuvani.
    """

    SESSIONS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with get_connection() as connection:

        # Glavna tablica prometnih sesija.
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

        # Tablica datoteka povezanih sa sesijama.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS session_files (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                session_id INTEGER NOT NULL,

                file_type TEXT NOT NULL,

                file_path TEXT NOT NULL,

                created_at TEXT NOT NULL,

                FOREIGN KEY (session_id)
                    REFERENCES traffic_sessions(id)
                    ON DELETE CASCADE

            )
        """)


# ============================================================
# STVARANJE NOVE PROMETNE SESIJE
# ============================================================

def create_session(
    username,
    source_type="LIVE",
    source_name=None,
    notes=None
):
    """
    Stvara novu prometnu sesiju.

    Primjer:
        create_session(
            username="MARIO",
            source_type="LIVE",
            source_name="RTSP kamera"
        )

    Funkcija vraća ID i oznaku nove sesije.
    """

    initialize_sessions()

    if not username or not username.strip():
        raise ValueError(
            "Korisničko ime ne smije biti prazno."
        )

    if source_type not in ("LIVE", "VIDEO"):
        raise ValueError(
            "Izvor mora biti LIVE ili VIDEO."
        )

    with get_connection() as connection:

        cursor = connection.execute("""
            INSERT INTO traffic_sessions (
                username,
                source_type,
                source_name,
                started_at,
                status,
                notes
            )
            VALUES (?, ?, ?, ?, 'RUNNING', ?)
        """, (
            username.strip(),
            source_type,
            source_name,
            current_timestamp(),
            notes
        ))

        session_id = cursor.lastrowid

        # Jedinstvena oznaka sesije.
        session_code = f"RIVA-{session_id:06d}"

        connection.execute("""
            UPDATE traffic_sessions
            SET session_code = ?
            WHERE id = ?
        """, (
            session_code,
            session_id
        ))

    # Zasebna mapa za rezultate ove sesije.
    session_directory = SESSIONS_DIR / session_code

    session_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    return {
        "id": session_id,
        "session_code": session_code,
        "directory": str(session_directory)
    }


# ============================================================
# ZAVRŠETAK PROMETNE SESIJE
# ============================================================

def finish_session(
    session_id,
    status="COMPLETED",
    total_vehicles=0,
    ocr_attempts=0,
    ocr_success=0,
    notes=None
):
    """
    Završava postojeću prometnu sesiju.

    Dopušteni završni statusi:
    - COMPLETED
    - INTERRUPTED
    - FAILED

    Statistika se upisuje tek nakon stvarne analize.
    """

    initialize_sessions()

    allowed_statuses = (
        "COMPLETED",
        "INTERRUPTED",
        "FAILED"
    )

    if status not in allowed_statuses:
        raise ValueError(
            "Neispravan završni status sesije."
        )

    # Provjera statističkih vrijednosti.
    values = (
        total_vehicles,
        ocr_attempts,
        ocr_success
    )

    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for value in values
    ):
        raise ValueError(
            "Statističke vrijednosti moraju biti "
            "nenegativni cijeli brojevi."
        )

    if ocr_success > ocr_attempts:
        raise ValueError(
            "Broj uspješnih OCR očitanja ne može biti "
            "veći od broja OCR pokušaja."
        )

    with get_connection() as connection:

        # Dohvaćamo postojeću sesiju.
        session = connection.execute("""
            SELECT started_at, status
            FROM traffic_sessions
            WHERE id = ?
        """, (
            session_id,
        )).fetchone()

        if session is None:
            raise ValueError(
                "Prometna sesija ne postoji."
            )

        if session["status"] != "RUNNING":
            raise ValueError(
                "Sesija je već završena ili prekinuta."
            )

        finished_at = current_timestamp()

        # Izračun stvarnog trajanja sesije.
        started_datetime = datetime.fromisoformat(
            session["started_at"]
        )

        finished_datetime = datetime.fromisoformat(
            finished_at
        )

        duration_seconds = max(
            0,
            (
                finished_datetime - started_datetime
            ).total_seconds()
        )

        # Spremanje završnih podataka.
        connection.execute("""
            UPDATE traffic_sessions
            SET
                finished_at = ?,
                duration_seconds = ?,
                status = ?,
                total_vehicles = ?,
                ocr_attempts = ?,
                ocr_success = ?,
                notes = COALESCE(?, notes)
            WHERE id = ?
        """, (
            finished_at,
            duration_seconds,
            status,
            total_vehicles,
            ocr_attempts,
            ocr_success,
            notes,
            session_id
        ))

    return get_session(session_id)


# ============================================================
# DOHVAT POJEDINAČNE SESIJE
# ============================================================

def get_session(session_id):
    """Vraća sve podatke jedne prometne sesije."""

    initialize_sessions()

    with get_connection() as connection:

        row = connection.execute("""
            SELECT *
            FROM traffic_sessions
            WHERE id = ?
        """, (
            session_id,
        )).fetchone()

        return dict(row) if row else None


# ============================================================
# DOHVAT POVIJESTI SESIJA
# ============================================================

def get_recent_sessions(limit=20):
    """Vraća posljednje prometne sesije."""

    initialize_sessions()

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT *
            FROM traffic_sessions
            ORDER BY id DESC
            LIMIT ?
        """, (
            max(1, int(limit)),
        )).fetchall()

        return [
            dict(row)
            for row in rows
        ]


# ============================================================
# UKUPNA STATISTIKA PROMETNIH SESIJA
# ============================================================

def get_session_statistics():
    """
    Vraća ukupnu statistiku iz stvarno spremljenih sesija.

    Ne koristi demonstracijske podatke.
    """

    initialize_sessions()

    with get_connection() as connection:

        row = connection.execute("""
            SELECT

                COUNT(*) AS total_sessions,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'COMPLETED'
                            THEN total_vehicles
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_vehicles,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'COMPLETED'
                            THEN ocr_attempts
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_ocr_attempts,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'COMPLETED'
                            THEN ocr_success
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_ocr_success

            FROM traffic_sessions
        """).fetchone()

        return dict(row)


# ============================================================
# EVIDENCIJA DATOTEKA SESIJE
# ============================================================

def add_session_file(
    session_id,
    file_type,
    file_path
):
    """
    Evidentira datoteku povezanu s prometnom sesijom.

    Primjeri vrsta datoteka:
    - IMAGE
    - CSV
    - EXCEL
    - REPORT
    - VIDEO

    Funkcija ne kopira datoteku, nego sprema
    njezinu putanju u bazu.
    """

    initialize_sessions()

    # Provjera postojanja sesije.
    if get_session(session_id) is None:
        raise ValueError(
            "Nije moguće dodati datoteku: sesija ne postoji."
        )

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Datoteka ne postoji: {file_path}"
        )

    with get_connection() as connection:

        cursor = connection.execute("""
            INSERT INTO session_files (
                session_id,
                file_type,
                file_path,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            session_id,
            file_type,
            str(path.resolve()),
            current_timestamp()
        ))

        return cursor.lastrowid


# ============================================================
# DOHVAT DATOTEKA SESIJE
# ============================================================

def get_session_files(session_id):
    """Vraća popis datoteka povezanih sa sesijom."""

    initialize_sessions()

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT *
            FROM session_files
            WHERE session_id = ?
            ORDER BY id DESC
        """, (
            session_id,
        )).fetchall()

        return [
            dict(row)
            for row in rows
        ]
