# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# FAZA 05 - ODREDIVANJE SMJERA KRETANJA VOZILA
# ============================================================

import cv2
import csv
import os

from config import (
    RTSP_URL,
    NAZIV_PROZORA,
    PRIKAZ_VIDEA,
)

from camera import Kamera
from tracking import PracenjeVozila
from smjer import (
    OdredivanjeSmjera,
    LINIJE_SMJERA,
)


# ============================================================
# POSTAVKE PRIKAZA I REZULTATA
# ============================================================

MAKSIMALNA_SIRINA_PRIKAZA = 1600
MAKSIMALNA_VISINA_PRIKAZA = 900

MAPA_REZULTATA = "rezultati"

CSV_DATOTEKA = os.path.join(
    MAPA_REZULTATA,
    "smjer.csv"
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
# CRTANJE VIRTUALNIH LINIJA ZA SMJER
# ============================================================

def nacrtaj_linije(prikaz):

    # Traka 1 = zelene nijanse
    # Traka 2 = zute nijanse
    #
    # L1 je svjetlija, L2 tamnija.

    boje = {
        ("Traka 1", "L1"): (0, 255, 0),
        ("Traka 1", "L2"): (0, 180, 0),
        ("Traka 2", "L1"): (0, 255, 255),
        ("Traka 2", "L2"): (0, 180, 180),
    }

    for naziv_trake, linije in (
        LINIJE_SMJERA.items()
    ):

        for naziv_linije, linija in (
            linije.items()
        ):

            p1, p2 = linija

            boja = boje.get(
                (
                    naziv_trake,
                    naziv_linije
                ),
                (255, 255, 255)
            )

            cv2.line(
                prikaz,
                p1,
                p2,
                boja,
                5
            )

            oznaka = (
                f"{naziv_trake} - "
                f"{naziv_linije}"
            )

            cv2.putText(
                prikaz,
                oznaka,
                (
                    p1[0],
                    max(
                        p1[1] - 15,
                        30
                    )
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                boja,
                2,
                cv2.LINE_AA
            )


# ============================================================
# CRTANJE STATISTIKE
# ============================================================

def nacrtaj_statistiku(
    prikaz,
    smjer
):

    tekstovi = [
        (
            "Traka 1 | "
            f"OK: {smjer.broj_ispravnih('Traka 1')} | "
            f"SUPROTAN: {smjer.broj_suprotnih('Traka 1')}"
        ),
        (
            "Traka 2 | "
            f"OK: {smjer.broj_ispravnih('Traka 2')} | "
            f"SUPROTAN: {smjer.broj_suprotnih('Traka 2')}"
        ),
        (
            "Ukupno | "
            f"OK: {smjer.ukupno_ispravnih()} | "
            f"SUPROTAN: {smjer.ukupno_suprotnih()}"
        ),
    ]

    x = 30
    y = 350

    for tekst in tekstovi:

        (
            sirina_teksta,
            visina_teksta
        ), baseline = cv2.getTextSize(
            tekst,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
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
            0.85,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        y += 50


# ============================================================
# STATUS POJEDINOG ID-a
# ============================================================

def status_id(
    smjer,
    track_id
):

    # Potpuno zavrsen prolazak.
    if track_id in smjer.zavrseni_id:

        stanje = smjer.stanje.get(
            track_id
        )

        if stanje is not None:

            prva = stanje.get(
                "prva_linija"
            )

            if prva == "L1":
                return "SMJER POTVRDEN"

            if prva == "L2":
                return "SUPROTAN SMJER"

        return "PROLAZAK POTVRDEN"

    # Vozilo je preslo samo prvu liniju.
    stanje = smjer.stanje.get(
        track_id
    )

    if stanje is not None:

        return (
            f"{stanje['traka']} | "
            f"{stanje['prva_linija']} predena"
        )

    return None


# ============================================================
# OBRADA TRACKING REZULTATA I SMJERA
# ============================================================

def obradi_i_nacrtaj(
    rezultat,
    tracker,
    smjer,
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
            smjer
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
        # REFERENTNA BOTTOM-CENTER TOCKA
        # ----------------------------------------------------

        tocka_vozila = (
            int(
                (x1 + x2) / 2
            ),
            y2
        )

        # ----------------------------------------------------
        # ODREDIVANJE SMJERA
        # ----------------------------------------------------

        dogadaj = (
            smjer.obradi_objekt(
                track_id,
                tocka_vozila,
                naziv_klase
            )
        )

        # Dogadaj se vraca tek kada isti ID
        # prijede obje linije iste prometne trake.

        if dogadaj is not None:

            dogadaji.append(
                dogadaj
            )

        # ----------------------------------------------------
        # BOJA BOUNDING BOXA
        # ----------------------------------------------------

        boja_boxa = (
            0,
            255,
            0
        )

        # Ako je zavrsen prolazak u suprotnom smjeru,
        # bounding box postaje crven.

        if track_id in smjer.zavrseni_id:

            stanje = smjer.stanje.get(
                track_id
            )

            if (
                stanje is not None
                and
                stanje.get("prva_linija")
                == "L2"
            ):

                boja_boxa = (
                    0,
                    0,
                    255
                )

        # ----------------------------------------------------
        # BOUNDING BOX
        # ----------------------------------------------------

        cv2.rectangle(
            prikaz,
            (x1, y1),
            (x2, y2),
            boja_boxa,
            3
        )

        # Referentna bottom-center tocka.
        cv2.circle(
            prikaz,
            tocka_vozila,
            6,
            (0, 0, 255),
            -1
        )

        # ----------------------------------------------------
        # OZNAKA ID-a I KLASE
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # TRENUTNI STATUS ID-a
        # ----------------------------------------------------

        status = status_id(
            smjer,
            track_id
        )

        if status is not None:

            status_y = min(
                y2 + 35,
                prikaz.shape[0] - 15
            )

            (
                status_sirina,
                status_visina
            ), status_baseline = cv2.getTextSize(
                status,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                2
            )

            status_x = x1

            if (
                status_x
                + status_sirina
                + 10
                > prikaz.shape[1]
            ):

                status_x = max(
                    0,
                    prikaz.shape[1]
                    - status_sirina
                    - 15
                )

            cv2.rectangle(
                prikaz,
                (
                    status_x,
                    status_y
                    - status_visina
                    - 8
                ),
                (
                    status_x
                    + status_sirina
                    + 10,
                    status_y
                    + status_baseline
                ),
                (0, 0, 0),
                -1
            )

            cv2.putText(
                prikaz,
                status,
                (
                    status_x + 5,
                    status_y - 4
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                boja_boxa,
                2,
                cv2.LINE_AA
            )

    # --------------------------------------------------------
    # VIRTUALNE LINIJE I STATISTIKA
    # --------------------------------------------------------

    nacrtaj_linije(
        prikaz
    )

    nacrtaj_statistiku(
        prikaz,
        smjer
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
            "datum",
            "track_id",
            "stabilna_klasa",
            "traka",
            "prva_linija",
            "druga_linija",
            "vrijeme_prve_linije",
            "vrijeme_druge_linije",
            "trajanje_s",
            "status",
        ])

        for dogadaj in dogadaji:

            vrijeme_prve = (
                dogadaj["vrijeme_prve"]
            )

            vrijeme_druge = (
                dogadaj["vrijeme_druge"]
            )

            writer.writerow([
                vrijeme_prve.strftime(
                    "%Y-%m-%d"
                ),
                dogadaj["track_id"],
                dogadaj["klasa"],
                dogadaj["traka"],
                dogadaj["prva_linija"],
                dogadaj["druga_linija"],
                vrijeme_prve.strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )[:-3],
                vrijeme_druge.strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )[:-3],
                f"{dogadaj['trajanje']:.3f}",
                dogadaj["status"],
            ])


# ============================================================
# ISPIS STATISTIKE KLASA
# ============================================================

def ispisi_klase(
    naslov,
    statistika
):

    print(
        f"  {naslov}:"
    )

    print(
        f"    Car   : "
        f"{statistika.get('car', 0)}"
    )

    print(
        f"    Bus   : "
        f"{statistika.get('bus', 0)}"
    )

    print(
        f"    Truck : "
        f"{statistika.get('truck', 0)}"
    )


# ============================================================
# GLAVNI PROGRAM
# ============================================================

def main():

    print("=" * 70)
    print("TEST 09 - STVARNI VIDEOIZVOR")
    print("FAZA 05 - ODREDIVANJE SMJERA KRETANJA VOZILA")
    print("=" * 70)

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
    # ODREDIVANJE SMJERA
    # --------------------------------------------------------

    smjer = OdredivanjeSmjera()

    # Spremaju se samo kompletni prolazi:
    # L1 -> L2 ili L2 -> L1.
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
            "[INFO] Analiza smjera je aktivna."
        )

        print(
            "[INFO] Za svaku prometnu traku "
            "koriste se linije L1 i L2."
        )

        print(
            "[INFO] L1 -> L2 = ISPRAVAN SMJER."
        )

        print(
            "[INFO] L2 -> L1 = SUPROTAN SMJER."
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
                        smjer,
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
                    smjer
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
        print("=" * 70)
        print(
            "ZAVRSNA STATISTIKA SMJERA KRETANJA"
        )
        print("=" * 70)

        for naziv_trake in [
            "Traka 1",
            "Traka 2"
        ]:

            broj_ok = (
                smjer.broj_ispravnih(
                    naziv_trake
                )
            )

            broj_suprotan = (
                smjer.broj_suprotnih(
                    naziv_trake
                )
            )

            print()
            print(
                f"{naziv_trake}:"
            )

            print(
                f"  Ispravan smjer : "
                f"{broj_ok}"
            )

            print(
                f"  Suprotan smjer : "
                f"{broj_suprotan}"
            )

            print()

            ispisi_klase(
                "Ispravan smjer - klase",
                smjer.statistika_ispravnih_klasa(
                    naziv_trake
                )
            )

            ispisi_klase(
                "Suprotan smjer - klase",
                smjer.statistika_suprotnih_klasa(
                    naziv_trake
                )
            )

        print()
        print("-" * 70)

        print(
            f"UKUPNO POTVRDENIH PROLAZAKA: "
            f"{smjer.ukupno_prolazaka()}"
        )

        print(
            f"ISPRAVAN SMJER: "
            f"{smjer.ukupno_ispravnih()}"
        )

        print(
            f"SUPROTAN SMJER: "
            f"{smjer.ukupno_suprotnih()}"
        )

        print("-" * 70)

        print(
            f"[OK] Dogadaji spremljeni: "
            f"{CSV_DATOTEKA}"
        )

        print()
        print(
            "[NAPOMENA] Prolazak se potvrduje tek kada "
            "isti ByteTrack ID prijede obje virtualne "
            "linije iste prometne trake."
        )

        print(
            "[NAPOMENA] L1 -> L2 oznacava ispravan, "
            "a L2 -> L1 suprotan smjer."
        )

        print(
            "[NAPOMENA] Vrijeme predstavlja lokalno "
            "sistemsko vrijeme racunala u trenutku obrade."
        )

        print("=" * 70)

        print(
            "[OK] Program zavrsen."
        )


if __name__ == "__main__":
    main()