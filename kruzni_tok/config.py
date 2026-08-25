from ultralytics import YOLO
import cv2
import os
import torch

# =========================================================
# MODEL
# =========================================================

MODEL = YOLO("yolo11x.pt")

# =========================================================
# UREĐAJ ZA DETEKCIJU
# =========================================================

# "cuda" koristi NVIDIA grafičku karticu (brže),
# "cpu" koristi procesor. Ako CUDA nije dostupna,
# automatski se vraća na CPU.
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Detekcija se vrti na uređaju: {DEVICE.upper()}")

# =========================================================
# PREGLED VIDEA U REALNOM VREMENU
# =========================================================

# True  -> prikazuje prozor s videom tijekom obrade (cv2.imshow)
# False -> bez prikaza (brže, za remote/headless izvršavanje)
PRIKAZ_VIDEA = False

# =========================================================
# ULAZ / IZLAZ
# =========================================================

ULAZNI_VIDEO = "test08.mp4"

IZLAZNA_MAPA = "rezultati/kruzni_tok"
os.makedirs(IZLAZNA_MAPA, exist_ok=True)

IZLAZNI_VIDEO = os.path.join(
    IZLAZNA_MAPA,
    "test08_poboljsana_dijagnostika.mp4"
)

TRAJANJE_TESTA_SEKUNDE = 15

# =========================================================
# POSTAVKE DETEKCIJE
# =========================================================

CONFIDENCE = 0.10
IMAGE_SIZE = 1920

# Objekt mora biti praćen najmanje ovoliko frameova
# prije nego što se smatra dovoljno stabilnim.
MINIMALNO_FRAMEOVA_PRACENJA = 4

# Minimalne dimenzije bounding boxa (odbacujemo sitne detekcije).
MINIMALNA_SIRINA_OBJEKTA = 8
MINIMALNA_VISINA_OBJEKTA = 8

# =========================================================
# REGIJE (dobivene kalibracijom)
# =========================================================

REGIJE = {
    "Regija 1": ((821, 187), (991, 366)),
    "Regija 2": ((1115, 421), (1365, 586)),
    "Regija 3": ((848, 693), (991, 902)),
    "Regija 4": ((540, 463), (796, 584)),
    "Regija 5 - KRUZNI TOK": ((474, 169), (1400, 962)),
}

BOJE = {
    "Regija 1": (0, 0, 255),
    "Regija 2": (0, 255, 255),
    "Regija 3": (255, 0, 0),
    "Regija 4": (255, 0, 255),
    "Regija 5 - KRUZNI TOK": (0, 255, 0),
}

# Redoslijed zona za izvjestaj.
ZONE_ZA_IZVJESTAJ = ["R1", "R2", "R3", "R4", "R5", "IZVAN"]


def otvori_video():
    """
    Otvara ulazni video i priprema izlazni zapisivac.
    Vraca (cap, writer, (sirina, visina, fps, maksimalno_frameova)).
    """

    cap = cv2.VideoCapture(ULAZNI_VIDEO)

    if not cap.isOpened():
        raise SystemExit(
            f"GREŠKA: Video '{ULAZNI_VIDEO}' nije moguće otvoriti.")

    sirina = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    visina = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    ukupno_frameova = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0:
        cap.release()
        raise SystemExit("GREŠKA: FPS nije ispravno očitan.")

    maksimalno_frameova = min(
        int(fps * TRAJANJE_TESTA_SEKUNDE),
        ukupno_frameova
    )

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(IZLAZNI_VIDEO, fourcc, fps, (sirina, visina))

    if not writer.isOpened():
        cap.release()
        raise SystemExit("GREŠKA: Izlazni video nije moguće otvoriti.")

    return cap, writer, (sirina, visina, fps, maksimalno_frameova)
