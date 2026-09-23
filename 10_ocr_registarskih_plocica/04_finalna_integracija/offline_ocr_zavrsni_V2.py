"""
TEST 10 - Zavrsna offline OCR obrada
Lokalni CSV s OCR tekstom + pseudonimizirani CSV s HMAC-SHA256.
Pokretanje: python offline_ocr_zavrsni.py
Ovisnosti: paddleocr, paddlepaddle, opencv-python, numpy
"""
from pathlib import Path
import csv
import argparse
import hashlib
import hmac
import re
import secrets
from datetime import datetime

import cv2
import numpy as np
from paddleocr import PaddleOCR

ROOT = Path(__file__).resolve().parent
CROPOVI = ROOT / "rezultati" / "najbolji_cropovi"
PRIVATNO = ROOT / "rezultati" / "privatno"
JAVNO = ROOT / "rezultati" / "za_pregled_prije_objave"
KLJUC = PRIVATNO / "hmac_kljuc.hex"
LOKALNI_CSV = PRIVATNO / "registracije_lokalno.csv"
PSEUDO_CSV = JAVNO / "registracije_pseudonimizirano.csv"

def normaliziraj(tekst):
    return re.sub(r"[^A-Z0-9]", "", str(tekst or "").upper())

def podaci_datoteke(putanja):
    m = re.match(r"ID_(\d+)_(.+)$", putanja.stem)
    return (int(m.group(1)), m.group(2)) if m else (None, "unknown")

def uvecaj(slika):
    h, w = slika.shape[:2]
    faktor = 4 if w < 150 else (3 if w < 250 else 2)
    return cv2.resize(slika, (w*faktor, h*faktor), interpolation=cv2.INTER_CUBIC)

def bez_plave_trake(slika):
    """Konzervativno: rezi samo ako se plava traka jasno vidi uz lijevi rub."""
    h, w = slika.shape[:2]
    hsv = cv2.cvtColor(slika, cv2.COLOR_BGR2HSV)
    maska = cv2.inRange(hsv, np.array([90, 65, 35]), np.array([135, 255, 255]))
    granica = min(int(w * 0.22), w-1)
    if granica < 3:
        return None
    omjeri = [np.mean(maska[:, x] > 0) for x in range(granica)]
    plavi = [x for x, udio in enumerate(omjeri) if udio >= 0.28]
    if not plavi or min(plavi) > int(w*0.08):
        return None
    kraj = max(plavi) + 1
    # Ne rezati vise od 18 % slike i ostaviti mali razmak.
    if kraj > int(w*0.18):
        return None
    pocetak = min(kraj + max(1, int(w*0.012)), int(w*0.18))
    return slika[:, pocetak:] if w-pocetak > 25 else None

def ocitaj(ocr, slika):
    try:
        predikcija = ocr.predict(uvecaj(slika))
        elementi = []
        for rezultat in predikcija or []:
            podaci = getattr(rezultat, "json", None)
            if callable(podaci):
                podaci = podaci()
            if podaci is None and isinstance(rezultat, dict):
                podaci = rezultat
            if not isinstance(podaci, dict):
                continue
            podaci = podaci.get("res", podaci)
            tekstovi = podaci.get("rec_texts", []) or []
            ocjene = podaci.get("rec_scores", []) or []
            for i, tekst in enumerate(tekstovi):
                cisto = normaliziraj(tekst)
                if cisto:
                    elementi.append((cisto, float(ocjene[i]) if i < len(ocjene) else 0.0))
        if not elementi:
            return "", 0.0, []
        return ("".join(t for t, _ in elementi),
                sum(s for _, s in elementi)/len(elementi), elementi)
    except Exception as greska:
        print(f"[UPOZORENJE] OCR: {type(greska).__name__}: {greska}")
        return "", 0.0, []

def kandidat(tekst, elementi):
    """
    Odabir bez pretpostavljanja drzave: preferiraj jedan tekstualni element
    duzine 5-10 koji sadrzi slova i brojeve. Ne izmisljaj ili mijenjaj znakove.
    """
    moguci = [(t, s) for t, s in elementi
              if 5 <= len(t) <= 10 and re.search(r"[A-Z]", t) and re.search(r"\d", t)]
    if moguci:
        return max(moguci, key=lambda x: x[1])
    if 5 <= len(tekst) <= 10 and re.search(r"[A-Z]", tekst) and re.search(r"\d", tekst):
        return tekst, (sum(s for _, s in elementi)/len(elementi) if elementi else 0.0)
    return "", 0.0

def ucitaj_kljuc():
    PRIVATNO.mkdir(parents=True, exist_ok=True)
    if KLJUC.exists():
        return bytes.fromhex(KLJUC.read_text(encoding="utf-8").strip())
    kljuc = secrets.token_bytes(32)
    # Ekskluzivno kreiranje: nikad ne prepisivati postojeci kljuc.
    try:
        with KLJUC.open("x", encoding="utf-8") as f:
            f.write(kljuc.hex())
    except FileExistsError:
        return bytes.fromhex(KLJUC.read_text(encoding="utf-8").strip())
    print("[INFO] Novi lokalni HMAC kljuc spremljen. Ne objavljivati ga.")
    return kljuc

def main():
    global CROPOVI, LOKALNI_CSV, PSEUDO_CSV
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop-dir", type=Path, default=CROPOVI)
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()
    CROPOVI = args.crop_dir
    if args.run_id:
        LOKALNI_CSV = PRIVATNO / f"registracije_lokalno_{args.run_id}.csv"
        PSEUDO_CSV = JAVNO / f"registracije_pseudonimizirano_{args.run_id}.csv"
    slike = sorted(p for p in CROPOVI.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}) if CROPOVI.exists() else []
    if not slike:
        print(f"[GRESKA] Nema slika u mapi: {CROPOVI}")
        return

    PRIVATNO.mkdir(parents=True, exist_ok=True)
    JAVNO.mkdir(parents=True, exist_ok=True)
    kljuc = ucitaj_kljuc()
    print(f"[INFO] Pronađeno slika: {len(slike)}")
    print("[INFO] Ucitavanje PaddleOCR-a...")
    ocr = PaddleOCR(lang="en", use_doc_orientation_classify=False,
                    use_doc_unwarping=False, use_textline_orientation=False)
    lokalni = []
    pseudo = []
    sada = datetime.now().astimezone().isoformat(timespec="seconds")
    for i, putanja in enumerate(slike, 1):
        track_id, klasa = podaci_datoteke(putanja)
        slika = cv2.imread(str(putanja))
        if slika is None:
            print(f"[{i}/{len(slike)}] ID {track_id}: slika se ne moze ucitati")
            lokalni.append([track_id, klasa, putanja.name, "", "", "", "", "GRESKA_UCITAVANJA", "", sada])
            pseudo.append([track_id, klasa, "", "", "GRESKA_UCITAVANJA", sada])
            continue

        izvorni, izvorni_conf, izvorni_el = ocitaj(ocr, slika)
        obradena = bez_plave_trake(slika)
        bez_trake, bez_conf, bez_el = ocitaj(ocr, obradena) if obradena is not None else ("", 0.0, [])
        kandidati = []
        for oznaka, tekst, elementi in [("izvorni", izvorni, izvorni_el),
                                         ("bez_plave_trake", bez_trake, bez_el)]:
            vrijednost, pouzdanost = kandidat(tekst, elementi)
            if vrijednost:
                kandidati.append((vrijednost, pouzdanost, oznaka))
        # Ako su kandidati razliciti, oznaci za rucnu provjeru, ne pogadjaj.
        razliciti = len({x[0] for x in kandidati}) > 1
        odabrani = max(kandidati, key=lambda x: x[1]) if kandidati else ("", 0.0, "")
        tekst, pouzdanost, metoda = odabrani
        status = ("ZA_PROVJERU" if razliciti else
                  "KANDIDAT_PROVJERITI" if tekst else "NIJE_IZDVOJENO")
        digest = hmac.new(kljuc, tekst.encode("utf-8"), hashlib.sha256).hexdigest() if tekst else ""
        lokalni.append([track_id, klasa, putanja.name, izvorni, bez_trake, tekst,
                        f"{pouzdanost:.4f}" if tekst else "", status, metoda, sada])
        pseudo.append([track_id, klasa, digest, f"{pouzdanost:.4f}" if tekst else "", status, sada])
        print(f"[{i}/{len(slike)}] ID {track_id}: {status}; "
              f"izvorni={izvorni or '-'}; bez trake={bez_trake or '-'}; "
              f"odabrani={tekst or '-'}")
    with LOKALNI_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID_vozila", "Klasa", "Datoteka_cropa", "OCR_izvorni",
                    "OCR_bez_plave_trake", "OCR_odabrani", "OCR_pouzdanost",
                    "Status", "Metoda", "Vrijeme_OCR_obrade"])
        w.writerows(lokalni)
    with PSEUDO_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID_vozila", "Klasa", "HMAC_SHA256_OCR_rezultata",
                    "OCR_pouzdanost", "Status", "Vrijeme_OCR_obrade"])
        w.writerows(pseudo)
    print("\n[OK] Lokalni CSV:", LOKALNI_CSV)
    print("[OK] Pseudonimizirani CSV:", PSEUDO_CSV)
    print("[VAZNO] CSV za pregled NIJE automatski siguran za javnu objavu.")
    print("[VAZNO] OCR pouzdanost nije mjera tocnosti; rezultate provjeriti lokalno.")
    print("[VAZNO] Vrijeme je vrijeme OCR obrade, a ne vrijeme prolaska vozila.")

if __name__ == "__main__":
    main()
