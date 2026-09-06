import cv2
import os
import torch

# =========================================================
# MODEL
# =========================================================

# OBB model je treniran za snimke iz zraka i prepoznaje mala vozila.
MODEL_IME = "yolo11n-obb.pt"


def ucitaj_model():
    """Učitava YOLO model tek kada obrada videa počne."""

    from ultralytics import YOLO

    return YOLO(MODEL_IME)

# =========================================================
# UREĐAJ ZA DETEKCIJU
# =========================================================


# "cuda" koristi NVIDIA grafičku karticu (brže),
# "cpu" koristi procesor. Ako CUDA nije dostupna,
# automatski se vraća na CPU.
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# =========================================================
# PREGLED VIDEA U REALNOM VREMENU
# =========================================================

# True  -> prikazuje prozor s videom tijekom obrade (cv2.imshow)
# False -> bez prikaza (brže, za remote/headless izvršavanje)
PRIKAZ_VIDEA = False

# =========================================================
# ULAZ / IZLAZ
# =========================================================

ULAZNI_VIDEO = "../test08.mp4"

IZLAZNA_MAPA = "rezultati/kruzni_tok"
os.makedirs(IZLAZNA_MAPA, exist_ok=True)

IZLAZNI_VIDEO = os.path.join(
    IZLAZNA_MAPA,
    "test08_vozila_i_zone.mp4"
)

IZLAZNI_IZVJESTAJ = os.path.join(IZLAZNA_MAPA, "vozila.csv")

TRAJANJE_TESTA_SEKUNDE = 15

# =========================================================
# POSTAVKE DETEKCIJE
# =========================================================

CONFIDENCE = 0.10
IMAGE_SIZE = 640

TRACKER = "tracker_zona.yaml"

# Nova zona mora biti prisutna u 3 uzastopna framea prije zapisa.
MINIMALNO_FRAMEOVA_U_NOVOJ_ZONI = 3

# Kraći ID-evi ostaju u CSV-u, ali su označeni kao nestabilni.
MINIMALNO_FRAMEOVA_STABILNOG_IDA = 5

# DOTA nazivi klasa koje OBB model koristi za vozila.
PRACENE_KLASE = {"small vehicle", "large vehicle"}

# =========================================================
# REGIJE (dobivene kalibracijom)
# =========================================================

REGIJE = {
    "Regija 1": ((821, 187), (991, 366)),
    "Regija 2": ((1115, 421), (1365, 586)),
    "Regija 3": ((848, 693), (991, 902)),
    "Regija 4": ((540, 463), (796, 584)),
}

# R5 je prsten ceste oko središnjeg otoka, a ne veliki pravokutnik.
KRUZNI_TOK_CENTAR = (960, 535)
KRUZNI_TOK_UNUTARNJI_POLUPRECNIK = 150
KRUZNI_TOK_VANJSKI_POLUPRECNIK = 320

BOJE = {
    "Regija 1": (0, 0, 255),
    "Regija 2": (0, 255, 255),
    "Regija 3": (255, 0, 0),
    "Regija 4": (255, 0, 255),
    "Regija 5 - KRUZNI TOK": (0, 255, 0),
}

# Redoslijed zona za izvjestaj.
ZONE_ZA_IZVJESTAJ = ["R1", "R2", "R3", "R4", "R5", "IZVAN"]


def _napravi_writer(putanja, fps, velicina):
    """
    Stvara VideoWriter. Najprije proba H.264 (avc1) jer je
    najkompatibilniji s playerima, a ako nije dostupan vraca se na mp4v.
    """

    for codec in ("avc1", "mp4v"):
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(putanja, fourcc, fps, velicina)
        if writer.isOpened():
            return writer
        writer.release()

    return None


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

    writer = _napravi_writer(IZLAZNI_VIDEO, fps, (sirina, visina))

    if writer is None:
        cap.release()
        raise SystemExit("GREŠKA: Izlazni video nije moguće otvoriti.")

    return cap, writer, (sirina, visina, fps, maksimalno_frameova)
