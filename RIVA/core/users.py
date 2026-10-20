import hashlib
import hmac
import json
import os
import secrets
import tempfile
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
USERS_FILE = BASE_DIR / "data" / "users.json"
ITERATIONS = 600_000


def _load_users():
    if not USERS_FILE.exists():
        return {"users": []}

    with open(USERS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict) or not isinstance(data.get("users"), list):
        raise ValueError("Neispravna korisnicka baza.")

    return data


def _save_users(data):
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary = tempfile.mkstemp(
        prefix=".users_",
        suffix=".tmp",
        dir=str(USERS_FILE.parent)
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        os.replace(temporary, USERS_FILE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _password_hash(password, salt, iterations=ITERATIONS):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations
    )


def _find_user(data, username):
    for user in data["users"]:
        if user["username"].casefold() == username.strip().casefold():
            return user
    return None


def list_users():
    data = _load_users()

    return [
        {
            "username": user["username"],
            "role": user["role"],
            "active": user["active"],
            "created_at": user["created_at"]
        }
        for user in data["users"]
    ]


def verify_user(username, password):
    data = _load_users()
    user = _find_user(data, username)

    if not user or not user["active"]:
        return False

    salt = bytes.fromhex(user["salt"])
    saved_hash = bytes.fromhex(user["password_hash"])

    calculated = _password_hash(
        password,
        salt,
        user["iterations"]
    )

    return hmac.compare_digest(saved_hash, calculated)


def get_user_role(username):
    data = _load_users()
    user = _find_user(data, username)

    if not user or not user["active"]:
        return None

    return user["role"]


def add_user(actor, username, password, role="user"):
    data = _load_users()

    if get_user_role(actor) != "admin":
        raise PermissionError("Samo administrator moze dodavati korisnike.")

    username = username.strip()

    if not username:
        raise ValueError("Korisnicko ime je obvezno.")

    if len(password) < 10:
        raise ValueError("Lozinka mora imati najmanje 10 znakova.")

    if role not in ("admin", "user"):
        raise ValueError("Nepoznata korisnicka uloga.")

    if _find_user(data, username):
        raise ValueError("Korisnik vec postoji.")

    salt = secrets.token_bytes(16)

    data["users"].append({
        "username": username,
        "role": role,
        "active": True,
        "salt": salt.hex(),
        "password_hash": _password_hash(password, salt).hex(),
        "iterations": ITERATIONS,
        "created_at": datetime.now().isoformat(timespec="seconds")
    })

    _save_users(data)


def change_password(username, old_password, new_password):
    if not verify_user(username, old_password):
        raise ValueError("Trenutna lozinka nije ispravna.")

    if len(new_password) < 10:
        raise ValueError("Nova lozinka mora imati najmanje 10 znakova.")

    data = _load_users()
    user = _find_user(data, username)

    salt = secrets.token_bytes(16)

    user["salt"] = salt.hex()
    user["password_hash"] = _password_hash(new_password, salt).hex()
    user["iterations"] = ITERATIONS

    _save_users(data)


def deactivate_user(actor, username):
    data = _load_users()

    if get_user_role(actor) != "admin":
        raise PermissionError("Samo administrator moze deaktivirati korisnike.")

    user = _find_user(data, username)

    if not user:
        raise ValueError("Korisnik ne postoji.")

    if user["username"].casefold() == actor.casefold():
        raise ValueError("Administrator ne moze deaktivirati vlastiti racun.")

    if user["role"] == "admin":
        active_admins = sum(
            1 for item in data["users"]
            if item["role"] == "admin" and item["active"]
        )

        if active_admins <= 1:
            raise ValueError("Posljednji administrator mora ostati aktivan.")

    user["active"] = False
    _save_users(data)


def activate_user(actor, username):
    """Ponovno aktivira postojeci korisnicki racun."""
    data = _load_users()

    administrator = _find_user(data, actor)
    if (
        administrator is None
        or not administrator["active"]
        or administrator["role"] != "admin"
    ):
        raise PermissionError(
            "Samo administrator moze aktivirati korisnike."
        )

    user = _find_user(data, username)

    if user is None:
        raise ValueError("Korisnik ne postoji.")

    if user["active"]:
        raise ValueError("Korisnik je vec aktivan.")

    user["active"] = True
    _save_users(data)
