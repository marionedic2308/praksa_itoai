
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path


# --------------------------------------------------
# RIVA - AUTENTIFIKACIJA KORISNIKA
# --------------------------------------------------
# Modul upravlja jednim korisničkim računom.
# Lozinka se ne sprema kao običan tekst.
# Za zaštitu koristimo PBKDF2-HMAC-SHA256.
# --------------------------------------------------

# Mapa u kojoj se nalazi aplikacija RIVA.
BASE_DIR = Path(__file__).resolve().parent.parent

# Datoteka za pohranu korisničkog računa.
AUTH_FILE = BASE_DIR / "data" / "auth.json"

# Broj iteracija za izračun hash vrijednosti.
ITERATIONS = 600_000


def hash_password(password, salt):
    """
    Izračunava sigurnosnu hash vrijednost lozinke.

    Salt osigurava da iste lozinke ne proizvode
    uvijek identične hash vrijednosti.
    """
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS
    )


def user_exists():
    """Provjerava postoji li korisnički račun."""
    return AUTH_FILE.is_file()


def create_user(username, password):
    """
    Stvara početni korisnički račun.

    Korisnički račun moguće je stvoriti samo
    ako prethodno ne postoji.
    """

    # Sprječavamo slučajno prepisivanje računa.
    if user_exists():
        raise ValueError("Korisnički račun već postoji.")

    username = username.strip()

    # Osnovna provjera unesenih podataka.
    if not username:
        raise ValueError("Korisničko ime ne smije biti prazno.")

    if len(password) < 10:
        raise ValueError("Lozinka mora imati najmanje 10 znakova.")

    # Generiranje nasumične sigurnosne vrijednosti.
    salt = secrets.token_bytes(16)

    # Izračun hash vrijednosti lozinke.
    password_hash = hash_password(password, salt)

    # Podaci koji se spremaju na disk.
    user_data = {
        "username": username,
        "salt": salt.hex(),
        "password_hash": password_hash.hex(),
        "iterations": ITERATIONS
    }

    # Stvaranje mape za podatke aplikacije.
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Spremanje korisničkog računa.
    with open(AUTH_FILE, "x", encoding="utf-8") as file:
        json.dump(user_data, file, indent=4)


def verify_login(username, password):
    """
    Provjerava korisničko ime i lozinku.

    Vraća True ako su podaci ispravni,
    odnosno False ako prijava nije uspješna.
    """

    if not user_exists():
        return False

    # Učitavanje spremljenih podataka.
    with open(AUTH_FILE, "r", encoding="utf-8") as file:
        user_data = json.load(file)

    # Provjera korisničkog imena.
    if not hmac.compare_digest(
        username.strip().encode("utf-8"),
        user_data["username"].encode("utf-8")
    ):
        return False

    # Učitavanje spremljene sigurnosne vrijednosti.
    salt = bytes.fromhex(user_data["salt"])
    saved_hash = bytes.fromhex(user_data["password_hash"])

    # Izračun hash vrijednosti unesene lozinke.
    calculated_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        user_data["iterations"]
    )

    # Sigurna usporedba hash vrijednosti.
    return hmac.compare_digest(saved_hash, calculated_hash)
