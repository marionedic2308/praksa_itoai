# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# FAZA 04 - BROJANJE VOZILA PRELASKOM PREKO VIRTUALNIH LINIJA
# ============================================================

import cv2
import csv
import os
from datetime import datetime

from config import (
    RTSP_URL,
    NAZIV_PROZORA,
    PRIKAZ_VIDEA,
)

from camera import Kamera
from tracking import PracenjeVozila
from brojanje import (
    BrojanjeVozila,
    LINIJE_BROJANJA,
)


# ============================================================
# POSTAVKE PRIKAZA I REZULTATA
# ============================================================

MAKSIMALNA_SIRINA_PRIKAZA = 1600
MAKSIMALNA_VISINA_PRIKAZA = 900

MAPA_REZULTATA = "rezultati"

CSV_DATOTEKA = os.path.join(
    MAPA_REZULTATA,
    "brojanje.csv"
)


# ============================================================
# PRILAGODBA PRIKAZA
# ============================================================

def prilagodi_prikaz(frame):

    visina, sirina = frame.shape[:2]

    faktor_sirine = (
        MAKSIMALNA_SIRINA_PRIKAZA / sirina
    )

    faktor_visine = (
        MAKSIMALNA_VISINA_PRIKAZA / visina
    )

    faktor = min(
        faktor_sirine,
        faktor_visine,
        1.0
    )

    nova_sirina = int(
        sirina * faktor
    )

    nova_visina = int(
        visina * faktor
    )

    if faktor < 1.0:

        return cv2.resize(
            frame,
            (
                nova_sirina,
                nova_visina
            ),
            interpolation=cv2.INTER_AREA
        )

    return frame


# ============================================================
# CRTANJE VIRTUALNIH LINIJA
# ============================================================

def nacrtaj_linije(prikaz):

    boje = {
        "Traka 1": (0, 255, 0),
        "Traka 2": (0, 255, 255),
    }

    for naziv_trake, linija in (
        LINIJE_BROJANJA.items()
    ):

        p1, p2 = linija

        boja = boje.get(
            naziv_trake,
            (255, 255, 255)
        )

        cv2.line(
            prikaz,
            p1,
            p2,
            boja,
            5
        )

        cv2.putText(
            prikaz,
            naziv_trake,
            (
                p1[0],
                max(
                    p1[1] - 15,
                    30
                )
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            boja,
            2,
            cv2.LINE_AA
        )


# ============================================================
# CRTANJE STATISTIKE
# ============================================================

def nacrtaj_statistiku(
    prikaz,
    brojanje
):

    tekstovi = [
        (
            "Traka 1: "
            f"{brojanje.broj_trake('Traka 1')}"
        ),
        (
            "Traka 2: "
            f"{brojanje.broj_trake('Traka 2')}"
        ),
        (
            "Ukupno: "
            f"{brojanje.ukupno()}"
        ),
    ]

    x = 30
    y = 50

    for tekst in tekstovi:

        (
            sirina_teksta,
            visina_teksta
        ), baseline = cv2.getTextSize(
            tekst,
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            2
        )

        cv2.rectangle(
            prikaz,
            (
                x - 10,
                y - visina_teksta - 10
            ),
            (
                x + sirina_teksta + 10,
                y + baseline + 8
            ),
            (0, 0, 0),
            -1
        )

        cv2.putText(
            prikaz,
            tekst,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        y += 50


# ============================================================
# OBRADA TRACKING REZULTATA I BROJANJA
# ============================================================

def obradi_i_nacrtaj(
    rezultat,
    tracker,
    brojanje,
    dogadaji
):

    prikaz = rezultat.orig_img.copy()

    if (
        rezultat.boxes is None
        or rezultat.boxes.id is None
    ):

        nacrtaj_linije(
            prikaz
        )

        nacrtaj_statistiku(
            prikaz,
            brojanje
        )

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

        # ----------------------------------------------------
        # STABILNA KLASA VOZILA
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # REFERENTNA TOCKA VOZILA
        #
        # Koristi se donja sredina bounding boxa jer bolje
        # predstavlja polozaj vozila na povrsini kolnika.
        # ----------------------------------------------------

        tocka_vozila = (
            int(
                (x1 + x2) / 2
            ),
            y2
        )

        # ----------------------------------------------------
        # PROVJERA PRELASKA VIRTUALNE LINIJE
        # ----------------------------------------------------

        prijelaz = (
            brojanje.obradi_objekt(
                track_id,
                tocka_vozila,
                naziv_klase
            )
        )

        if prijelaz is not None:

            vrijeme = (
                datetime.now()
                .strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )[:-3]
            )

            dogadaji.append({
                "vrijeme": vrijeme,
                "track_id": track_id,
                "klasa": naziv_klase,
                "traka": prijelaz,
            })

            print(
                f"[PRIJELAZ] "
                f"{vrijeme} | "
                f"ID {track_id} | "
                f"{naziv_klase} | "
                f"{prijelaz}"
            )

        # ----------------------------------------------------
        # BOUNDING BOX
        # ----------------------------------------------------

        cv2.rectangle(
            prikaz,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            3
        )

        # Referentna bottom-center tocka
        cv2.circle(
            prikaz,
            tocka_vozila,
            6,
            (0, 0, 255),
            -1
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

    # --------------------------------------------------------
    # LINIJE I STATISTIKA
    # --------------------------------------------------------

    nacrtaj_linije(
        prikaz
    )

    nacrtaj_statistiku(
        prikaz,
        brojanje
    )

    return prikaz


# ============================================================
# SPREMANJE CSV DOGADAJA
# ============================================================

def spremi_csv(dogadaji):

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
            "vrijeme_prijelaza",
            "track_id",
            "stabilna_klasa",
            "traka"
        ])

        for dogadaj in dogadaji:

            writer.writerow([
                dogadaj["vrijeme"],
                dogadaj["track_id"],
                dogadaj["klasa"],
                dogadaj["traka"],
            ])


# ============================================================
# GLAVNI PROGRAM
# ============================================================

def main():

    print("=" * 65)
    print("TEST 09 - STVARNI VIDEOIZVOR")
    print("FAZA 04 - BROJANJE VOZILA")
    print("=" * 65)

    # --------------------------------------------------------
    # YOLO + BYTETRACK
    # --------------------------------------------------------

    tracker = PracenjeVozila(
        model_path="../yolo11n.pt",
        confidence=0.25,
        image_size=640,
        tracker="bytetrack.yaml"
    )

    # --------------------------------------------------------
    # BROJANJE PRELASKA LINIJA
    # --------------------------------------------------------

    brojanje = BrojanjeVozila()

    # Evidencija potvrdenih prijelaza za CSV.
    dogadaji = []

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
            "[INFO] Brojanje prelaska virtualnih "
            "linija je aktivno."
        )

        print(
            "[INFO] Traka 1 i Traka 2 "
            "obraduju se odvojeno."
        )

        print(
            "[INFO] Za prekid prikaza "
            "pritisni tipku Q."
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

                prikaz = (
                    obradi_i_nacrtaj(
                        rezultat,
                        tracker,
                        brojanje,
                        dogadaji
                    )
                )

            else:

                prikaz = (
                    frame.copy()
                )

                nacrtaj_linije(
                    prikaz
                )

                nacrtaj_statistiku(
                    prikaz,
                    brojanje
                )

            # ------------------------------------------------
            # PRIKAZ
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
        # CSV
        # ----------------------------------------------------

        spremi_csv(
            dogadaji
        )

        # ----------------------------------------------------
        # ZAVRSNA STATISTIKA
        # ----------------------------------------------------

        print()
        print("=" * 65)
        print(
            "ZAVRSNA STATISTIKA BROJANJA"
        )
        print("=" * 65)

        for naziv_trake in [
            "Traka 1",
            "Traka 2"
        ]:

            broj = (
                brojanje.broj_trake(
                    naziv_trake
                )
            )

            klase = (
                brojanje.statistika_klasa(
                    naziv_trake
                )
            )

            print()
            print(
                f"{naziv_trake}: {broj}"
            )

            print(
                f"  Car   : "
                f"{klase.get('car', 0)}"
            )

            print(
                f"  Bus   : "
                f"{klase.get('bus', 0)}"
            )

            print(
                f"  Truck : "
                f"{klase.get('truck', 0)}"
            )

        print()
        print("-" * 65)

        print(
            f"UKUPNO PREBROJANIH VOZILA: "
            f"{brojanje.ukupno()}"
        )

        print("-" * 65)

        print(
            f"[OK] Dogadaji spremljeni: "
            f"{CSV_DATOTEKA}"
        )

        print()
        print(
            "[NAPOMENA] Vozilo se broji tek nakon "
            "potvrdenog prelaska virtualne linije."
        )

        print(
            "[NAPOMENA] Isti ByteTrack ID moze biti "
            "prebrojan samo jednom na istoj traci."
        )

        print(
            "[NAPOMENA] Smjer kretanja jos se ne "
            "odreduje u ovoj fazi."
        )

        print("=" * 65)

        print(
            "[OK] Program zavrsen."
        )


if __name__ == "__main__":
    main()