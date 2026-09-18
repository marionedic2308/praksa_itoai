from urllib.parse import quote
from pathlib import Path
import sys


# ============================================================
# PUTANJE
# ============================================================

TRENUTNA_MAPA = Path(__file__).resolve().parent
TEST10_MAPA = TRENUTNA_MAPA.parent
PROJEKT_MAPA = TEST10_MAPA.parent

# Koristi postojeću lokalnu konfiguraciju iz Testa 09.
# Datoteka sadrži podatke za pristup kameri i NE ide na GitHub.
TEST09_MAPA = PROJEKT_MAPA / "09_stvarni_videoizvor"

sys.path.append(str(TEST09_MAPA))

try:
    from local_config import CAMERA_IP, CAMERA_USER, CAMERA_PASSWORD
except ImportError:
    raise RuntimeError(
        "Nije moguce ucitati local_config.py iz Testa 09."
    )


# ============================================================
# RTSP VIDEOIZVOR
# ============================================================

if not CAMERA_IP or not CAMERA_USER or not CAMERA_PASSWORD:
    raise RuntimeError(
        "Nisu uneseni svi potrebni podaci za pristup kameri."
    )

KORISNIK = quote(CAMERA_USER, safe="")
LOZINKA = quote(CAMERA_PASSWORD, safe="")

RTSP_URL = (
    f"rtsp://{KORISNIK}:{LOZINKA}@{CAMERA_IP}:554/"
    f"Streaming/Channels/101"
)


# ============================================================
# MODEL ZA DETEKCIJU REGISTARSKIH PLOCICA
# ============================================================

MODEL_PATH = str(
    TEST10_MAPA / "license-plate-finetune-v1n.pt"
)


# ============================================================
# POSTAVKE DETEKCIJE
# ============================================================

CONFIDENCE = 0.25
IMAGE_SIZE = 1280


# ============================================================
# PRIKAZ
# ============================================================

NAZIV_PROZORA = "TEST 10 - Detekcija registarskih plocica"

PRIKAZ_VIDEA = True

MAX_SIRINA_PRIKAZA = 1600
MAX_VISINA_PRIKAZA = 900