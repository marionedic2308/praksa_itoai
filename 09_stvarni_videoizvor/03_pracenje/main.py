# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# FAZA 03 - PRACENJE VOZILA PRIMJENOM BYTETRACK ALGORITMA
# ============================================================

import cv2
import csv
import os
from collections import Counter

from config import (
    RTSP_URL,
    NAZIV_PROZORA,
    PRIKAZ_VIDEA,
)

from camera import Kamera
from tracking import PracenjeVozila


# ============================================================
# POSTAVKE PRIKAZA
# ============================================================

MAKSIMALNA_SIRINA_PRIKAZA = 1600
MAKSIMALNA_VISINA_PRIKAZA = 900

MAPA_REZULTATA = "rezultati"

CSV_DATOTEKA = os.path.join(
    MAPA_REZULTATA,
    "pracenje.csv"
)


# ============================================================
# PRILAGODBA PRIKAZA
# ============================================================

def prilagodi_prikaz(frame):

    visina, sirina = frame.shape[:2]

    faktor_sirine = MAKSIMALNA_SIRINA_PRIKAZA / sirina
    faktor_visine = MAKSIMALNA_VISINA_PRIKAZA / visina

    faktor = min(
        faktor_sirine,
        faktor_visine,
        1.0
    )

    nova_sirina = int(sirina * faktor)
    nova_visina = int(visina * faktor)

    if faktor < 1.0:
        return cv2.resize(
            frame,
            (nova_sirina, nova_visina),
            interpolation=cv2.INTER_AREA
        )

    return frame


# ============================================================
# CRTANJE TRACKING REZULTATA
# ============================================================

def nacrtaj_tracking(rezultat, tracker):

    prikaz = rezultat.orig_img.copy()

    if rezultat.boxes is None:
        return prikaz

    if rezultat.boxes.id is None:
        return prikaz

    boxes = (
        rezultat.boxes.xyxy
        .int()
        .cpu()
        .tolist()
    )

    ids = (
        rezultat.boxes.id
        .int()
        .cpu()
        .tolist()
    )

    for box, track_id in zip(
        boxes,
        ids
    ):

        x1, y1, x2, y2 = box

        stabilna_klasa_id = (
            tracker.stabilna_klasa(
                track_id
            )
        )

        naziv_klase = (
            tracker.naziv_klase(
                stabilna_klasa_id
            )
        )

        # Bounding box
        cv2.rectangle(
            prikaz,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            3
        )

        tekst = (
            f"ID {track_id} | "
            f"{naziv_klase}"
        )

        (
            sirina_teksta,
            visina_teksta
        ), baseline = cv2.getTextSize(
            tekst,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            2
        )

        tekst_y = max(
            y1 - 10,
            visina_teksta + 10
        )

        # Pozadina oznake
        cv2.rectangle(
            prikaz,
            (
                x1,
                tekst_y
                - visina_teksta
                - 8
            ),
            (
                x1
                + sirina_teksta
                + 10,
                tekst_y
                + baseline
            ),
            (0, 0, 0),
            -1
        )

        # ID i stabilna klasa
        cv2.putText(
            prikaz,
            tekst,
            (
                x1 + 5,
                tekst_y - 4
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

    return prikaz


# ============================================================
# SPREMANJE REZULTATA
# ============================================================

def spremi_csv(tracker, broj_pojavljivanja):

    os.makedirs(
        MAPA_REZULTATA,
        exist_ok=True
    )

    with open(
        CSV_DATOTEKA,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as datoteka:

        writer = csv.writer(
            datoteka
        )

        writer.writerow([
            "track_id",
            "stabilna_klasa",
            "broj_opazanja"
        ])

        for track_id in sorted(
            broj_pojavljivanja.keys()
        ):

            klasa_id = (
                tracker.stabilna_klasa(
                    track_id
                )
            )

            naziv_klase = (
                tracker.naziv_klase(
                    klasa_id
                )
            )

            writer.writerow([
                track_id,
                naziv_klase,
                broj_pojavljivanja[
                    track_id
                ]
            ])


# ============================================================
# GLAVNI PROGRAM
# ============================================================

def main():

    print("=" * 60)
    print("TEST 09 - STVARNI VIDEOIZVOR")
    print("FAZA 03 - PRACENJE VOZILA")
    print("=" * 60)

    # --------------------------------------------------------
    # YOLO + ByteTrack
    # --------------------------------------------------------

    tracker = PracenjeVozila(
        model_path="../yolo11n.pt",
        confidence=0.25,
        image_size=640,
        tracker="bytetrack.yaml"
    )

    # Broj frameova u kojima je pojedini ID opazen
    broj_pojavljivanja = Counter()

    print(
        "[INFO] Povezivanje na RTSP videoizvor..."
    )

    kamera = Kamera(
        RTSP_URL
    )

    try:

        kamera.otvori()

        print(
            "[INFO] Videoizvor je spreman."
        )

        print(
            "[INFO] YOLO detekcija je aktivna."
        )

        print(
            "[INFO] ByteTrack pracenje je aktivno."
        )

        print(
            "[INFO] Za prekid prikaza pritisni tipku Q."
        )

        while True:

            uspjeh, frame = (
                kamera.procitaj_frame()
            )

            if (
                not uspjeh
                or frame is None
            ):

                print(
                    "[UPOZORENJE] "
                    "Nije moguce procitati frame."
                )

                break

            # ------------------------------------------------
            # YOLO DETEKCIJA + BYTETRACK
            # ------------------------------------------------

            rezultat = (
                tracker.prati(
                    frame
                )
            )

            if rezultat is not None:

                # --------------------------------------------
                # Evidencija aktivnih track ID-eva
                # --------------------------------------------

                if (
                    rezultat.boxes
                    is not None
                    and rezultat.boxes.id
                    is not None
                ):

                    ids = (
                        rezultat.boxes.id
                        .int()
                        .cpu()
                        .tolist()
                    )

                    for track_id in ids:

                        broj_pojavljivanja[
                            track_id
                        ] += 1

                # --------------------------------------------
                # Vizualizacija
                # --------------------------------------------

                prikaz = (
                    nacrtaj_tracking(
                        rezultat,
                        tracker
                    )
                )

            else:

                prikaz = (
                    frame.copy()
                )

            # ------------------------------------------------
            # PRIKAZ NA MONITORU
            # ------------------------------------------------

            prikaz_ekran = (
                prilagodi_prikaz(
                    prikaz
                )
            )

            if PRIKAZ_VIDEA:

                cv2.imshow(
                    NAZIV_PROZORA,
                    prikaz_ekran
                )

                if (
                    cv2.waitKey(1)
                    & 0xFF
                    == ord("q")
                ):

                    print(
                        "[INFO] Korisnik je "
                        "zaustavio prikaz."
                    )

                    break

    except KeyboardInterrupt:

        print(
            "\n[INFO] Program je prekinut "
            "putem tipkovnice."
        )

    except Exception as greska:

        print(
            f"[GRESKA] {greska}"
        )

    finally:

        kamera.zatvori()

        cv2.destroyAllWindows()

        # ----------------------------------------------------
        # SPREMANJE CSV REZULTATA
        # ----------------------------------------------------

        spremi_csv(
            tracker,
            broj_pojavljivanja
        )

        # ----------------------------------------------------
        # ZAVRSNA STATISTIKA
        # ----------------------------------------------------

        broj_klasa = Counter()

        for track_id in (
            broj_pojavljivanja.keys()
        ):

            klasa_id = (
                tracker.stabilna_klasa(
                    track_id
                )
            )

            naziv = (
                tracker.naziv_klase(
                    klasa_id
                )
            )

            broj_klasa[
                naziv
            ] += 1

        ukupno_id = len(
            broj_pojavljivanja
        )

        print()
        print("=" * 60)
        print(
            "ZAVRSNA STATISTIKA PRACENJA"
        )
        print("=" * 60)

        print(
            f"Jedinstveni ByteTrack ID-evi : "
            f"{ukupno_id}"
        )

        print(
            f"Car                        : "
            f"{broj_klasa['car']}"
        )

        print(
            f"Bus                        : "
            f"{broj_klasa['bus']}"
        )

        print(
            f"Truck                      : "
            f"{broj_klasa['truck']}"
        )

        print("-" * 60)

        print(
            f"[OK] Rezultati spremljeni: "
            f"{CSV_DATOTEKA}"
        )

        print()

        print(
            "[NAPOMENA] ByteTrack ID predstavlja "
            "praceni objekt tijekom ovog pokretanja."
        )

        print(
            "[NAPOMENA] Broj ID-eva jos nije konacni "
            "broj vozila koja su prosla cestom."
        )

        print(
            "[NAPOMENA] Pouzdano brojanje prolazaka "
            "uvodi se u sljedecoj fazi pomocu "
            "virtualne linije."
        )

        print("=" * 60)

        print(
            "[OK] Program zavrsen."
        )


if __name__ == "__main__":
    main()