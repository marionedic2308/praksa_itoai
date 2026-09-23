import cv2
import subprocess
import sys
import math
from pathlib import Path
from datetime import datetime

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


# ============================================================
# POSTAVKE
# ============================================================

PRAG_NEAKTIVNOSTI = 30
MIN_SIRINA_PLOCICE = 65
MIN_VISINA_PLOCICE = 17
MIN_POUZDANOST_PLOCICE = 0.45
MIN_OMJER_PLOCICE = 1.8
MAX_OMJER_PLOCICE = 6.8

MIN_SIRINA_VOZILA = 80
MIN_VISINA_VOZILA = 60

# Lokalna mapa u koju se sprema samo jedan najbolji
# crop registarske plocice za svaki zavrseni ID vozila.
MAPA_REZULTATA = (
    Path(__file__).resolve().parent
    / "rezultati"
    / "najbolji_cropovi"
    / datetime.now().strftime("test_%Y%m%d_%H%M%S_%f")
)

MAPA_REZULTATA.mkdir(
    parents=True,
    exist_ok=True
)


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
        min(int(x1), sirina_framea - 1)
    )

    y1 = max(
        0,
        min(int(y1), visina_framea - 1)
    )

    x2 = max(
        0,
        min(int(x2), sirina_framea)
    )

    y2 = max(
        0,
        min(int(y2), visina_framea)
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
    """
    Dodaje mali rub oko detektirane registarske plocice
    kako znakovi ne bi bili odrezani uz rub bounding boxa.
    """

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
        "TEST 10 - FAZA 04 - IZDVAJANJE REGISTARSKIH PLOCICA"
    )
    print(
        "VOZILO -> BYTETrack ID -> PLOCICA -> NAJBOLJI CROP"
    )
    print("=" * 76)

    kamera = None
    zavrsetak_na_q = False

    # ========================================================
    # PRIVREMENI PODACI PO ID-u VOZILA
    # ========================================================
    #
    # Cropovi se NE spremaju svaki frame na disk.
    #
    # Za svaki ID u memoriji se cuva samo trenutno
    # najbolji crop. Ako kasnije dobijemo veci crop,
    # prethodni se zamjenjuje.
    #
    # Na disk se zapisuje tek kada vozilo postane
    # neaktivno.
    # ========================================================

    najbolji_cropovi = {}

    zavrseni_id_evi = set()

    # ========================================================
    # STATISTIKA
    # ========================================================

    broj_zavrsenih_vozila = 0
    broj_spremljenih_plocica = 0

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

        print(
            "[INFO] Sustav pokrenut."
        )

        print(
            "[INFO] Za svaki ID vozila cuva se "
            "samo najbolji crop plocice."
        )

        print(
            "[INFO] OCR se NE izvodi tijekom "
            "obrade videoizvora."
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

            if (
                not uspjeh
                or frame is None
            ):
                continue

            broj_framea += 1

            prikaz = frame.copy()

            (
                visina_framea,
                sirina_framea
            ) = frame.shape[:2]

            # =================================================
            # 1. DETEKCIJA I PRACENJE VOZILA
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

                # Premala vozila nemaju dovoljno
                # korisnih detalja za trazenje plocice.

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
                # 2. CROP CIJELOG VOZILA
                # =================================================

                crop_vozila = frame[
                    y1:y2,
                    x1:x2
                ].copy()

                # =================================================
                # 3. DETEKCIJA REGISTARSKE PLOCICE
                # =================================================

                plocica = (
                    detektor_plocica.detektiraj(
                        crop_vozila
                    )
                )

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
                        max(30, y1 - 15)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA
                )

                if plocica is None:
                    continue

                # =================================================
                # 4. KOORDINATE PLOCICE
                # =================================================

                (
                    px1,
                    py1,
                    px2,
                    py2
                ) = plocica[
                    "bbox"
                ]

                pouzdanost_plocice = float(
                    plocica[
                        "pouzdanost"
                    ]
                )

                (
                    crop_visina,
                    crop_sirina
                ) = crop_vozila.shape[:2]

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
                # 5. PRIKAZ BOUNDING BOXA PLOCICE
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

                cv2.putText(
                    prikaz,
                    (
                        "PLOCICA "
                        f"{pouzdanost_plocice:.2f}"
                    ),
                    (
                        global_px1,
                        max(
                            25,
                            global_py1 - 8
                        )
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.60,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA
                )

                # =================================================
                # 6. PROSIRENI CROP PLOCICE
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

                crop_plocice = (
                    crop_vozila[
                        oy1:oy2,
                        ox1:ox2
                    ].copy()
                )

                if (
                    crop_plocice is None
                    or crop_plocice.size == 0
                ):
                    continue

                (
                    visina_plocice,
                    sirina_plocice
                ) = crop_plocice.shape[:2]

                # Odbaci presitne, preuske/previsoke i nepouzdane detekcije.
                omjer = sirina_plocice / max(1, visina_plocice)
                if (sirina_plocice < MIN_SIRINA_PLOCICE
                    or visina_plocice < MIN_VISINA_PLOCICE
                    or not MIN_OMJER_PLOCICE <= omjer <= MAX_OMJER_PLOCICE
                    or pouzdanost_plocice < MIN_POUZDANOST_PLOCICE):
                    continue

                # Prednost: pouzdanost + citljivost + ostrina, a ne samo povrsina.
                siva = cv2.cvtColor(crop_plocice, cv2.COLOR_BGR2GRAY)
                ostrina = cv2.Laplacian(siva, cv2.CV_64F).var()
                velicina_cropa = sirina_plocice * visina_plocice
                rezultat_kvalitete = (
                    2.0 * pouzdanost_plocice
                    + 0.55 * math.log1p(sirina_plocice) / math.log(300)
                    + 0.15 * min(ostrina / 200.0, 1.0)
                )
                prethodni = najbolji_cropovi.get(track_id)
                treba_zamijeniti = (prethodni is None or
                                    rezultat_kvalitete > prethodni["kvaliteta"])

                if treba_zamijeniti:

                    najbolji_cropovi[
                        track_id
                    ] = {
                        "crop": crop_plocice,
                        "velicina": velicina_cropa,
                        "kvaliteta": rezultat_kvalitete,
                        "sirina": sirina_plocice,
                        "visina": visina_plocice,
                        "pouzdanost": (
                            pouzdanost_plocice
                        ),
                        "klasa": stabilna_klasa,
                        "frame": broj_framea,
                        "vrijeme": (
                            datetime.now()
                            .strftime(
                                "%Y-%m-%d "
                                "%H:%M:%S.%f"
                            )[:-3]
                        )
                    }

            # =================================================
            # 8. PROVJERA ZAVRSENIH VOZILA
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

                broj_zavrsenih_vozila += 1

                stabilna_klasa = (
                    pracenje
                    .dohvati_stabilnu_klasu(
                        track_id
                    )
                )

                broj_pracenih_frameova = (
                    pracenje
                    .dohvati_broj_frameova(
                        track_id
                    )
                )

                podatak = (
                    najbolji_cropovi.get(
                        track_id
                    )
                )

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
                    f"{stabilna_klasa}"
                )

                print(
                    f"Praceno frameova:     "
                    f"{broj_pracenih_frameova}"
                )

                if podatak is not None:

                    # =============================================
                    # 9. SPREMANJE SAMO JEDNOG NAJBOLJEG CROPA
                    # =============================================

                    naziv_datoteke = (
                        f"ID_{track_id:04d}_"
                        f"{stabilna_klasa}.jpg"
                    )

                    putanja = (
                        MAPA_REZULTATA
                        / naziv_datoteke
                    )

                    uspjesno_spremljeno = (
                        cv2.imwrite(
                            str(putanja),
                            podatak[
                                "crop"
                            ]
                        )
                    )

                    if uspjesno_spremljeno:

                        broj_spremljenih_plocica += 1

                        print(
                            "Plocica:              "
                            "SPREMLJENA"
                        )

                        print(
                            f"Crop:                 "
                            f"{podatak['sirina']}x"
                            f"{podatak['visina']}"
                        )

                        print(
                            f"Confidence detekcije: "
                            f"{podatak['pouzdanost']:.2f}"
                        )

                        print(
                            f"Frame najboljeg cropa:"
                            f" {podatak['frame']}"
                        )

                        print(
                            f"Datoteka:             "
                            f"{naziv_datoteke}"
                        )

                    else:

                        print(
                            "Plocica:              "
                            "GRESKA PRI SPREMANJU"
                        )

                else:

                    print(
                        "Plocica:              "
                        "NIJE PRONADENA"
                    )

                # =============================================
                # CISCENJE MEMORIJE ZAVRSENOG ID-a
                # =============================================

                najbolji_cropovi.pop(
                    track_id,
                    None
                )

                pracenje.ukloni_id(
                    track_id
                )

            # =================================================
            # 10. HUD
            # =================================================

            cv2.putText(
                prikaz,
                (
                    "TEST 10 - IZDVAJANJE "
                    "REGISTARSKIH PLOCICA"
                ),
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
                    f"{broj_zavrsenih_vozila} | "
                    f"Spremljene plocice: "
                    f"{broj_spremljenih_plocica}"
                ),
                (30, 190),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.70,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            # =================================================
            # 11. PRIKAZ
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
                    zavrsetak_na_q = True
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

        # Na Q spremi i vozila koja su jos aktivna, prije pokretanja OCR-a.
        if zavrsetak_na_q:
            for track_id, podatak in list(najbolji_cropovi.items()):
                if track_id in zavrseni_id_evi:
                    continue
                naziv = f"ID_{track_id:04d}_{podatak['klasa']}.jpg"
                putanja = MAPA_REZULTATA / naziv
                if cv2.imwrite(str(putanja), podatak["crop"]):
                    broj_spremljenih_plocica += 1
                    print(f"[SPREMLJENO PRI IZLASKU] ID {track_id}: {naziv}")
                else:
                    print(f"[UPOZORENJE] Nije spremljen crop ID {track_id}")
            najbolji_cropovi.clear()

        print()
        print("=" * 76)

        print(
            "ZAVRSNA STATISTIKA"
        )

        print("=" * 76)

        print(
            f"Zavrsena vozila:        "
            f"{broj_zavrsenih_vozila}"
        )

        print(
            f"Spremljene plocice:     "
            f"{broj_spremljenih_plocica}"
        )

        print(
            f"Mapa rezultata:         "
            f"{MAPA_REZULTATA}"
        )

        print("=" * 76)

        print(
            "[INFO] Live izdvajanje "
            "registarskih plocica zavrseno."
        )

        if zavrsetak_na_q:
            ocr_skripta = Path(__file__).resolve().parent / "offline_ocr_zavrsni_V2.py"
            if not ocr_skripta.is_file():
                print(f"[GRESKA] OCR skripta nije pronadena: {ocr_skripta}")
            else:
                print("\n[INFO] Automatski pokrecem OCR i izradu CSV izvjestaja...")
                print("[INFO] OCR obraduje samo slike iz ovog pokretanja.")
                try:
                    rezultat = subprocess.run([sys.executable, str(ocr_skripta),
                                              "--crop-dir", str(MAPA_REZULTATA),
                                              "--run-id", MAPA_REZULTATA.name],
                                             cwd=str(ocr_skripta.parent), check=False)
                    if rezultat.returncode == 0:
                        print("[OK] OCR postupak zavrsen. Provjeri CSV izvjestaje.")
                        excel_skripta = Path(__file__).resolve().parent / "izradi_excel_izvjestaje.py"
                        if excel_skripta.is_file():
                            print("[INFO] Izrada uredjenih Excel izvjestaja...")
                            excel_rezultat = subprocess.run(
                                [sys.executable, str(excel_skripta), "--run-id", MAPA_REZULTATA.name],
                                cwd=str(excel_skripta.parent), check=False
                            )
                            if excel_rezultat.returncode != 0:
                                print("[UPOZORENJE] Excel nije izradjen. CSV izvjestaji su sacuvani.")
                        else:
                            print("[UPOZORENJE] Nije pronadjena skripta za Excel izvjestaje.")
                    else:
                        print(f"[GRESKA] OCR zavrsio s kodom {rezultat.returncode}.")
                except OSError as greska:
                    print(f"[GRESKA] OCR se nije mogao pokrenuti: {greska}")


if __name__ == "__main__":
    main()