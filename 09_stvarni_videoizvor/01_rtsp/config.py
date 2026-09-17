# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# Konfiguracija sustava
# ============================================================

from urllib.parse import quote
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from local_config import (
    CAMERA_IP,
    CAMERA_USER,
    CAMERA_PASSWORD,
)


# ------------------------------------------------------------
# RTSP postavke
# ------------------------------------------------------------

RTSP_PORT = 554
RTSP_CHANNEL = "101"


# ------------------------------------------------------------
# Provjera lokalne konfiguracije
# ------------------------------------------------------------

if not CAMERA_IP:
    raise RuntimeError(
        "Nije postavljena IP adresa videoizvora."
    )

if not CAMERA_USER or not CAMERA_PASSWORD:
    raise RuntimeError(
        "Nisu postavljeni pristupni podaci za videoizvor."
    )


# ------------------------------------------------------------
# Izrada RTSP adrese
# ------------------------------------------------------------

USER_ENCODED = quote(CAMERA_USER, safe="")
PASSWORD_ENCODED = quote(CAMERA_PASSWORD, safe="")

RTSP_URL = (
    f"rtsp://{USER_ENCODED}:{PASSWORD_ENCODED}"
    f"@{CAMERA_IP}:{RTSP_PORT}/Streaming/Channels/{RTSP_CHANNEL}"
)


# ------------------------------------------------------------
# Postavke prikaza
# ------------------------------------------------------------

NAZIV_PROZORA = "Test 09 - Stvarni videoizvor"
PRIKAZ_VIDEA = True

# Maksimalna sirina prikaza na monitoru.
# Visina se automatski izracunava uz ocuvanje omjera slike.
SIRINA_PRIKAZA = 1600
