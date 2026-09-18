import cv2
from datetime import datetime
from pathlib import Path

from camera import Kamera
from config import (
    RTSP_URL,
    NAZIV_PROZORA,
    PRIKAZ_VIDEA,
    MAX_SIRINA_PRIKAZA,
    MAX_VISINA_PRIKAZA,
)
from tracking import PracenjeVozila
from detection import DetektorPlocica
from ocr import OCRRegistracije


# ============================================================
# POSTAVKE
# ============================================================

PRAG_NEAKTIVNOSTI = 30

MIN_SIRINA_VOZILA = 80
MIN_VISINA_VOZILA = 60

# Ako OCR vrati rezultat s barem ovom pouzdanoscu,
# rezultat se odmah prihvaca i OCR se za taj ID
# vise ne izvodi.
MIN_POUZDANOST_ZAKLJUCAVANJA = 0.40

# Ako OCR ne uspije, ne pokusava se ponovno odmah
# u sljedecem obradenom frameu.
#
# Time se smanjuje opterecenje CPU-a i omogucava
# da se vozilo malo priblizi kameri prije novog pokusaja.
RAZMAK_OCR_POKUSAJA = 5

# Maksimalan broj OCR pokusaja za jedno vozilo.
MAX_OCR_POKUSAJA = 5
MAPA_CROPOVA = Path("rezultati") / "cropovi"
MAPA_CROPOVA.mkdir(parents=True, exist_ok=True)

# Za svaki ID spremamo samo jedan crop.
# Novi crop zamjenjuje prethodni samo ako je veci,
# odnosno ako sadrzi vise piksela plocice.
najbolji_crop_velicina = {}


def prilagodi_prikaz(frame):

    visina, sirina = frame.shape[:2]

    faktor = min(
        MAX_SIRINA_PRIKAZA / sirina,
        MAX_VISINA_PRIKAZA / visina,
        1.0
    )

    if faktor < 1.0:

        frame = cv2.resize(
            frame,
            (
                int(sirina * faktor),
                int(visina * faktor)
            ),
            interpolation=cv2.INTER_AREA
        )

    return frame


def ogranicenje_bbox(
    x1,
    y1,
    x2,
    y2,
    sirina_framea,
    visina_framea
):

    x1 = max(
        0,
        min(x1, sirina_framea - 1)
    )

    y1 = max(
        0,
        min(y1, visina_framea - 1)
    )

    x2 = max(
        0,
        min(x2, sirina_framea)
    )

    y2 = max(
        0,
        min(y2, visina_framea)
    )

    return x1, y1, x2, y2


def prosiri_plocicu(
    x1,
    y1,
    x2,
    y2,
    sirina,
    visina
):

    sirina_boxa = x2 - x1
    visina_boxa = y2 - y1

    dodatak_x = int(
        sirina_boxa * 0.10
    )

    dodatak_y = int(
        visina_boxa * 0.15
    )

    novi_x1 = max(
        0,
        x1 - dodatak_x
    )

    novi_y1 = max(
        0,
        y1 - dodatak_y
    )

    novi_x2 = min(
        sirina,
        x2 + dodatak_x
    )

    novi_y2 = min(
        visina,
        y2 + dodatak_y
    )

    return (
        novi_x1,
        novi_y1,
        novi_x2,
        novi_y2
    )


def main():

    print("=" * 76)
    print(
        "TEST 10 - FAZA 04 - FINALNA INTEGRACIJA"
    )
    print(
        "VOZILO -> ID -> PLOCICA -> OCR -> REZULTAT"
    )
    print("=" * 76)

    kamera = None

    # ========================================================
    # OCR STANJE PO ID-u VOZILA
    # ========================================================

    # Konacni OCR rezultat:
    #
    # rezultati_ocr[ID] = {
    #     "tekst": "...",
    #     "pouzdanost": 0.85,
    #     "vrijeme": "...",
    #     "frame": 123
    # }

    rezultati_ocr = {}

    # Broj OCR pokusaja za svaki ID.
    broj_ocr_pokusaja = {}

    # Frame posljednjeg OCR pokusaja.
    zadnji_ocr_frame = {}

    # Koliko je puta detektor vidio plocicu.
    broj_detekcija_plocice = {}

    # Zavrseni ID-evi.
    zavrseni_id_evi = set()

    # ========================================================
    # STATISTIKA
    # ========================================================

    broj_zavrsenih = 0
    broj_s_plocicom = 0
    broj_ocitanih = 0

    try:

        # ====================================================
        # INICIJALIZACIJA
        # ====================================================

        print(
            "[INFO] Otvaranje RTSP videoizvora..."
        )

        kamera = Kamera(
            RTSP_URL
        )

        kamera.otvori()

        pracenje = PracenjeVozila()

        detektor_plocica = (
            DetektorPlocica()
        )

        ocr = OCRRegistracije()

        print(
            "[INFO] Finalna integracija pokrenuta."
        )

        print(
            "[INFO] OCR se izvodi samo dok za "
            "vozilo nije dobiven prihvatljiv rezultat."
        )

        print(
            "[INFO] Nakon uspjesnog OCR-a rezultat "
            "se zakljucava za ID vozila."
        )

        print(
            "[INFO] Q = izlaz"
        )

        broj_framea = 0

        # ====================================================
        # GLAVNA PETLJA
        # ====================================================

        while True:

            uspjeh, frame = (
                kamera.procitaj_frame()
            )

            if not uspjeh or frame is None:
                continue

            broj_framea += 1

            prikaz = frame.copy()

            visina_framea, sirina_framea = (
                frame.shape[:2]
            )

            # =================================================
            # 1. TRACKING VOZILA
            # =================================================

            vozila = pracenje.prati(
                frame,
                broj_framea
            )

            for vozilo in vozila:

                track_id = vozilo[
                    "track_id"
                ]

                stabilna_klasa = vozilo[
                    "stabilna_klasa"
                ]

                (
                    x1,
                    y1,
                    x2,
                    y2
                ) = vozilo[
                    "bbox"
                ]

                (
                    x1,
                    y1,
                    x2,
                    y2
                ) = ogranicenje_bbox(
                    x1,
                    y1,
                    x2,
                    y2,
                    sirina_framea,
                    visina_framea
                )

                if (
                    x2 - x1
                    < MIN_SIRINA_VOZILA
                ):
                    continue

                if (
                    y2 - y1
                    < MIN_VISINA_VOZILA
                ):
                    continue

                # =================================================
                # PRIKAZ VOZILA
                # =================================================

                cv2.rectangle(
                    prikaz,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    3
                )

                cv2.putText(
                    prikaz,
                    (
                        f"ID {track_id} | "
                        f"{stabilna_klasa}"
                    ),
                    (
                        x1,
                        max(30, y1 - 40)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA
                )

                # =================================================
                # AKO JE OCR VEC USPJESAN:
                #
                # NEMA VISE DETEKCIJE PLOCICE NI EASYOCR-a
                # ZA TAJ ID.
                # =================================================

                if track_id in rezultati_ocr:

                    rezultat = (
                        rezultati_ocr[
                            track_id
                        ]
                    )

                    cv2.putText(
                        prikaz,
                        (
                            f"OCR: "
                            f"{rezultat['tekst']} "
                            f"({rezultat['pouzdanost']:.2f})"
                        ),
                        (
                            x1,
                            max(55, y1 - 10)
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.70,
                        (0, 255, 255),
                        2,
                        cv2.LINE_AA
                    )

                    continue

                # =================================================
                # 2. CROP VOZILA
                # =================================================

                crop_vozila = frame[
                    y1:y2,
                    x1:x2
                ].copy()

                # =================================================
                # 3. DETEKCIJA PLOCICE
                # =================================================

                plocica = (
                    detektor_plocica.detektiraj(
                        crop_vozila
                    )
                )

                if plocica is None:

                    cv2.putText(
                        prikaz,
                        "PLOCICA: nije pronadena",
                        (
                            x1,
                            max(55, y1 - 10)
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.60,
                        (255, 255, 255),
                        2,
                        cv2.LINE_AA
                    )

                    continue

                broj_detekcija_plocice[
                    track_id
                ] = (
                    broj_detekcija_plocice.get(
                        track_id,
                        0
                    )
                    + 1
                )

                (
                    px1,
                    py1,
                    px2,
                    py2
                ) = plocica[
                    "bbox"
                ]

                crop_visina, crop_sirina = (
                    crop_vozila.shape[:2]
                )

                (
                    px1,
                    py1,
                    px2,
                    py2
                ) = ogranicenje_bbox(
                    px1,
                    py1,
                    px2,
                    py2,
                    crop_sirina,
                    crop_visina
                )

                # =================================================
                # CRTANJE DETEKTIRANE PLOCICE
                # =================================================

                global_px1 = (
                    x1 + px1
                )

                global_py1 = (
                    y1 + py1
                )

                global_px2 = (
                    x1 + px2
                )

                global_py2 = (
                    y1 + py2
                )

                cv2.rectangle(
                    prikaz,
                    (
                        global_px1,
                        global_py1
                    ),
                    (
                        global_px2,
                        global_py2
                    ),
                    (0, 255, 255),
                    3
                )

                # =================================================
                # 4. TREBA LI UOPCE POKRENUTI OCR?
                # =================================================

                pokusaji = (
                    broj_ocr_pokusaja.get(
                        track_id,
                        0
                    )
                )

                if (
                    pokusaji
                    >= MAX_OCR_POKUSAJA
                ):

                    cv2.putText(
                        prikaz,
                        "OCR: nema rezultata",
                        (
                            x1,
                            max(55, y1 - 10)
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.60,
                        (0, 165, 255),
                        2,
                        cv2.LINE_AA
                    )

                    continue

                zadnji_pokusaj = (
                    zadnji_ocr_frame.get(
                        track_id,
                        -9999
                    )
                )

                if (
                    broj_framea
                    - zadnji_pokusaj
                    < RAZMAK_OCR_POKUSAJA
                ):

                    cv2.putText(
                        prikaz,
                        "OCR: ceka novi pokusaj",
                        (
                            x1,
                            max(55, y1 - 10)
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.60,
                        (255, 255, 255),
                        2,
                        cv2.LINE_AA
                    )

                    continue

                # =================================================
                # 5. CROP PLOCICE
                # =================================================

                (
                    ox1,
                    oy1,
                    ox2,
                    oy2
                ) = prosiri_plocicu(
                    px1,
                    py1,
                    px2,
                    py2,
                    crop_sirina,
                    crop_visina
                )

                crop_plocice = crop_vozila[
                    oy1:oy2,
                    ox1:ox2
                ].copy()

                # =================================================
                # 6. JEDAN OCR POKUSAJ
                # =================================================

                broj_ocr_pokusaja[
                    track_id
                ] = (
                    pokusaji + 1
                )

                zadnji_ocr_frame[
                    track_id
                ] = broj_framea

                kandidati = ocr.procitaj(
                    crop_plocice
                )

                if not kandidati:

                    print(
                        f"[OCR] ID {track_id} | "
                        f"pokusaj "
                        f"{broj_ocr_pokusaja[track_id]} | "
                        f"bez rezultata"
                    )

                    continue

                najbolji = kandidati[0]

                tekst = najbolji[
                    "tekst"
                ]

                pouzdanost = najbolji[
                    "pouzdanost"
                ]

                print(
                    f"[OCR] ID {track_id} | "
                    f"pokusaj "
                    f"{broj_ocr_pokusaja[track_id]} | "
                    f"kandidat | "
                    f"conf={pouzdanost:.2f}"
                )

                # =================================================
                # 7. ZAKLJUCAVANJE OCR REZULTATA
                # =================================================

                if (
                    pouzdanost
                    >= MIN_POUZDANOST_ZAKLJUCAVANJA
                ):

                    vrijeme = (
                        datetime.now()
                        .strftime(
                            "%Y-%m-%d %H:%M:%S.%f"
                        )[:-3]
                    )

                    rezultati_ocr[
                        track_id
                    ] = {
                        "tekst": tekst,
                        "pouzdanost": pouzdanost,
                        "vrijeme": vrijeme,
                        "frame": broj_framea
                    }

                    print(
                        f"[OCR USPJESAN] "
                        f"ID {track_id} | "
                        f"rezultat zakljucan | "
                        f"conf={pouzdanost:.2f}"
                    )

            # =================================================
            # 8. ZAVRSENA / NEAKTIVNA VOZILA
            # =================================================

            neaktivni = (
                pracenje.neaktivni_id_evi(
                    broj_framea,
                    PRAG_NEAKTIVNOSTI
                )
            )

            for track_id in neaktivni:

                if (
                    track_id
                    in zavrseni_id_evi
                ):
                    continue

                zavrseni_id_evi.add(
                    track_id
                )

                broj_zavrsenih += 1

                klasa = (
                    pracenje
                    .dohvati_stabilnu_klasu(
                        track_id
                    )
                )

                broj_frameova = (
                    pracenje
                    .dohvati_broj_frameova(
                        track_id
                    )
                )

                detekcije = (
                    broj_detekcija_plocice.get(
                        track_id,
                        0
                    )
                )

                pokusaji = (
                    broj_ocr_pokusaja.get(
                        track_id,
                        0
                    )
                )

                if detekcije > 0:
                    broj_s_plocicom += 1

                print()
                print("-" * 76)
                print(
                    "[VOZILO ZAVRSENO]"
                )

                print(
                    f"ID vozila:           "
                    f"{track_id}"
                )

                print(
                    f"Klasa:                "
                    f"{klasa}"
                )

                print(
                    f"Praceno frameova:     "
                    f"{broj_frameova}"
                )

                print(
                    f"Detekcija plocice:    "
                    f"{detekcije}"
                )

                print(
                    f"OCR pokusaja:         "
                    f"{pokusaji}"
                )

                if (
                    track_id
                    in rezultati_ocr
                ):

                    rezultat = (
                        rezultati_ocr[
                            track_id
                        ]
                    )

                    broj_ocitanih += 1

                    print(
                        f"Registracija:         "
                        f"{rezultat['tekst']}"
                    )

                    print(
                        f"OCR pouzdanost:       "
                        f"{rezultat['pouzdanost']:.2f}"
                    )

                    print(
                        f"Vrijeme ocitanja:     "
                        f"{rezultat['vrijeme']}"
                    )

                    print(
                        "Status:               "
                        "OCR USPJESAN"
                    )

                else:

                    print(
                        "Registracija:         "
                        "NIJE OCITANA"
                    )

                    print(
                        "Status:               "
                        "OCR NIJE USPJESAN"
                    )

                # Ciscenje podataka zavrsenog ID-a.

                rezultati_ocr.pop(
                    track_id,
                    None
                )

                broj_ocr_pokusaja.pop(
                    track_id,
                    None
                )

                zadnji_ocr_frame.pop(
                    track_id,
                    None
                )

                broj_detekcija_plocice.pop(
                    track_id,
                    None
                )

                pracenje.ukloni_id(
                    track_id
                )

            # =================================================
            # 9. HUD
            # =================================================

            cv2.putText(
                prikaz,
                "TEST 10 - FINALNA INTEGRACIJA",
                (30, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.90,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )

            cv2.putText(
                prikaz,
                (
                    f"Frame: {broj_framea} | "
                    f"Zavrsena vozila: "
                    f"{broj_zavrsenih} | "
                    f"OCR: {broj_ocitanih}"
                ),
                (30, 190),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.70,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            # =================================================
            # 10. PRIKAZ
            # =================================================

            if PRIKAZ_VIDEA:

                prikaz = (
                    prilagodi_prikaz(
                        prikaz
                    )
                )

                cv2.imshow(
                    NAZIV_PROZORA,
                    prikaz
                )

                if (
                    cv2.waitKey(1)
                    & 0xFF
                    == ord("q")
                ):
                    break

    except KeyboardInterrupt:

        print(
            "\n[INFO] Program prekinut."
        )

    except Exception as greska:

        print(
            f"[GRESKA] {greska}"
        )

    finally:

        if kamera is not None:
            kamera.zatvori()

        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass

        print()
        print("=" * 76)
        print(
            "ZAVRSNA STATISTIKA"
        )
        print("=" * 76)

        print(
            f"Zavrsena vozila:        "
            f"{broj_zavrsenih}"
        )

        print(
            f"Pronadena plocica:       "
            f"{broj_s_plocicom}"
        )

        print(
            f"Uspjesno OCR ocitanje:   "
            f"{broj_ocitanih}"
        )

        print("=" * 76)
        print(
            "[INFO] Finalna integracija zavrsena."
        )


if __name__ == "__main__":
    main()