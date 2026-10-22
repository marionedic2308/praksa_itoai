"""Priprema OCR podataka za pojedinu RIVA sesiju."""

from pathlib import Path


def pripremi_ocr_mape(session_directory):
    """Pripremi zasebne OCR mape unutar postojece sesije."""
    session_path = Path(session_directory).resolve()

    if not session_path.is_dir():
        raise ValueError("Mapa sesije ne postoji.")

    ocr_root = session_path / "ocr"

    mape = {
        "kandidati": ocr_root / "kandidati",
        "plocice": ocr_root / "plocice",
        "privatno": ocr_root / "privatno",
        "za_pregled": ocr_root / "za_pregled",
    }

    for mapa in mape.values():
        mapa.mkdir(parents=True, exist_ok=True)

    return mape


def izdvoji_vozilo(frame, bbox, min_sirina=80, min_visina=60):
    """Sigurno izdvoji fotografiju vozila iz originalnog kadra."""
    if frame is None or not hasattr(frame, "shape"):
        return None

    if len(frame.shape) != 3 or frame.shape[2] != 3:
        return None

    if bbox is None or len(bbox) != 4:
        return None

    try:
        x1, y1, x2, y2 = (int(v) for v in bbox)
    except (TypeError, ValueError, OverflowError):
        return None

    visina, sirina = frame.shape[:2]

    x1 = max(0, min(x1, sirina))
    x2 = max(0, min(x2, sirina))
    y1 = max(0, min(y1, visina))
    y2 = max(0, min(y2, visina))

    if x2 - x1 < min_sirina or y2 - y1 < min_visina:
        return None

    return frame[y1:y2, x1:x2].copy()


def ocijeni_fotografiju(crop):
    """Ocijeni fotografiju vozila prema velicini i ostrini."""
    import cv2
    import math

    if crop is None or crop.size == 0:
        return 0.0

    visina, sirina = crop.shape[:2]

    if sirina < 80 or visina < 60:
        return 0.0

    siva = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    ostrina = float(cv2.Laplacian(siva, cv2.CV_64F).var())

    ocjena_velicine = min(math.log1p(sirina * visina) / 15.0, 1.0)
    ocjena_ostrine = min(ostrina / 300.0, 1.0)

    return round(0.6 * ocjena_velicine + 0.4 * ocjena_ostrine, 4)


class UpraviteljOCRKandidata:
    """Ogranicena memorija fotografija vozila za naknadni OCR."""

    def __init__(self, max_po_vozilu=3, max_vozila=50):
        self.max_po_vozilu = max(1, min(int(max_po_vozilu), 3))
        self.max_vozila = max(1, min(int(max_vozila), 50))
        self.kandidati = {}

    def dodaj(self, track_id, crop):
        """Zadrzi kvalitetnije fotografije bez neogranicenog rasta."""
        import cv2

        if crop is None or not hasattr(crop, "shape"):
            return False

        if len(crop.shape) != 3 or crop.shape[2] != 3:
            return False

        visina, sirina = crop.shape[:2]

        if sirina < 80 or visina < 60:
            return False

        ocjena = ocijeni_fotografiju(crop)

        if ocjena <= 0:
            return False

        if track_id not in self.kandidati:
            if len(self.kandidati) >= self.max_vozila:
                return False
            self.kandidati[track_id] = []

        fotografije = self.kandidati[track_id]

        # Ne cuvaj potpuno identicne fotografije.
        import numpy as np
        if any(
            np.array_equal(crop, postojeca_slika)
            for _, postojeca_slika in fotografije
        ):
            return False

        if len(fotografije) >= self.max_po_vozilu:
            najlosija = min(fotografije, key=lambda x: x[0])
            if ocjena <= najlosija[0]:
                return False
            fotografije.remove(najlosija)

        fotografije.append((ocjena, crop.copy()))
        fotografije.sort(key=lambda x: x[0], reverse=True)

        return True

    def preuzmi(self, track_id):
        """Preuzmi i ukloni fotografije jednog vozila iz memorije."""
        return self.kandidati.pop(track_id, [])

    def ocisti(self):
        """Oslobodi sve privremene fotografije."""
        self.kandidati.clear()



def spremi_ocr_kandidate(mapa_kandidata, event_id, fotografije):
    """Spremi OCR kandidate pod jedinstvenim ID-jem prolaska."""
    import cv2

    mapa = provjeri_ocr_putanju(mapa_kandidata)

    if isinstance(event_id, bool) or not isinstance(event_id, int) or event_id <= 0:
        raise ValueError("Neispravan ID prolaska.")

    spremljeno = []

    for redni_broj, podatak in enumerate(fotografije[:3], start=1):
        ocjena, crop = podatak

        if crop is None or crop.size == 0:
            continue

        naziv = f"event_{event_id:08d}_kandidat_{redni_broj}.jpg"
        putanja = mapa / naziv

        # Ne prepisuj vec spremljenu fotografiju.
        if putanja.exists():
            continue

        uspjeh, kodirana_slika = cv2.imencode(".jpg", crop)

        if not uspjeh:
            continue

        # Ne dopusti prekoracenje OCR limita po sesiji.
        trenutno_zauzece = zauzece_ocr_kandidata(mapa)
        if trenutno_zauzece + kodirana_slika.nbytes > OCR_LIMIT_DISKA_BAJTOVA:
            break

        try:
            with putanja.open("xb") as datoteka:
                datoteka.write(kodirana_slika.tobytes())
            spremljeno.append(str(putanja))
        except FileExistsError:
            continue

    return spremljeno


def provjeri_ocr_putanju(mapa_kandidata):
    """Provjeri pripada li mapa kandidata stvarnoj RIVA sesiji."""
    import re

    sessions_root = (
        Path(__file__).resolve().parent.parent
        / "data" / "sessions"
    ).resolve()

    mapa = Path(mapa_kandidata).resolve()

    try:
        relativna = mapa.relative_to(sessions_root)
    except ValueError:
        raise ValueError("OCR mapa je izvan RIVA sesija.")

    dijelovi = relativna.parts

    if (
        len(dijelovi) != 3
        or re.fullmatch(r"RIVA-[0-9]{6}", dijelovi[0]) is None
        or dijelovi[1:] != ("ocr", "kandidati")
        or not mapa.is_dir()
    ):
        raise ValueError("Neispravna struktura OCR mape.")

    return mapa


# Najveci dopusteni prostor za OCR kandidate po sesiji: 500 MB.
OCR_LIMIT_DISKA_BAJTOVA = 500 * 1024 * 1024


def zauzece_ocr_kandidata(mapa_kandidata):
    """Izracunaj zauzece OCR kandidata u bajtovima."""
    mapa = provjeri_ocr_putanju(mapa_kandidata)

    ukupno = 0

    for datoteka in mapa.iterdir():
        if datoteka.is_file():
            ukupno += datoteka.stat().st_size

    return ukupno

