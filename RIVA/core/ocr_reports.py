from pathlib import Path

"""Priprema OCR izvjesca uz provjeru korisnickih ovlasti."""

import hashlib
import hmac
import os
import sqlite3

from core.sessions import DATABASE_PATH
from core.users import get_user_role


def _get_hmac_key():
    """Ucitaj trajni lokalni HMAC kljuc."""
    key_file = Path(__file__).resolve().parent.parent / "data" / ".ocr_hmac_key"

    if not key_file.is_file():
        raise RuntimeError("Lokalni HMAC kljuc nije pronadjen.")

    key = key_file.read_text(encoding="ascii").strip()

    try:
        key_bytes = bytes.fromhex(key)
    except ValueError:
        raise RuntimeError("Neispravan format HMAC kljuca.")

    if len(key_bytes) != 32:
        raise RuntimeError("HMAC kljuc mora imati 32 bajta.")

    return key_bytes


def pseudonymize_plate(registration):
    if not registration:
        return None

    normalized = "".join(
        char for char in str(registration).upper()
        if char.isalnum()
    )

    digest = hmac.new(
        _get_hmac_key(),
        normalized.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return "RIVA-" + digest[:16].upper()


def get_ocr_report(username, session_id, internal=False):
    role = get_user_role(username)

    if role not in ("admin", "user"):
        raise PermissionError("Korisnik nije ovlasten.")

    if internal and role != "admin":
        raise PermissionError(
            "Interna OCR izvjesca dostupna su samo administratoru."
        )

    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT e.id, e.counted_at, e.vehicle_type,
                   e.lane, e.direction,
                   o.registration_text, o.confidence,
                   o.review_status
            FROM vehicle_events e
            LEFT JOIN ocr_results o ON o.event_id = e.id
            WHERE e.session_id = ?
            ORDER BY e.id
        """, (session_id,)).fetchall()

    result = []

    for row in rows:
        item = dict(row)

        if not internal:
            item["registration_text"] = pseudonymize_plate(
                item["registration_text"]
            )

        result.append(item)

    return result
