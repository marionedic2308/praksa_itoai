import cv2

from camera import Kamera
from config import (
    RTSP_URL,
    NAZIV_PROZORA,
    PRIKAZ_VIDEA,
    MAX_SIRINA_PRIKAZA,
    MAX_VISINA_PRIKAZA,
)
from tracking import PracenjePlocica
from ocr import OCRRegistracije


# ============================================================
# POSTAVKE
# ============================================================

PRAG_NEAKTIVNOSTI = 15
MIN_YOLO_CONF_ZA_OCR = 0.30


def prilagodi_prikaz(frame):
    """
    Smanjuje sliku samo za prikaz.
    Obrada ostaje na originalnoj rezoluciji.
    """

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


def prosiri_crop(
    x1,
    y1,
    x2,
    y2,
    sirina_framea,
    visina_framea
):
    """
    Dodaje mali prostor oko YOLO bounding boxa.
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
        sirina_framea,
        x2 + dodatak_x
    )

    novi_y2 = min(
        visina_framea,
        y2 + dodatak_y
    )

    return (
        novi_x1,
        novi_y1,
        novi_x2,
        novi_y2
    )


def odredi_status(kandidat):
    """
    Odreduje status konacnog OCR kandidata.
    """

    if kandidat is None:
        return "OCR NIJE USPJESAN"

    broj_potvrda = kandidat[
        "broj_potvrda"
    ]

    if broj_potvrda >= 3:
        return "POTVRDEN"

    if broj_potvrda == 2:
        return "STABILAN"

    return "NAJBOLJI KANDIDAT"


def main():

    print("=" * 76)
    print(
        "TEST 10 - FAZA 03 - DIJAGNOSTIKA TRACKINGA I OCR-a"
    )
    print("=" * 76)

    kamera = None

    zavrseni_id_evi = set()

    broj_zavrsenih = 0
    broj_potvrdenih = 0
    broj_stabilnih = 0
    broj_kandidata = 0
    broj_bez_ocr = 0

    try:

        # ====================================================
        # KAMERA
        # ====================================================

        print(
            "[INFO] Otvaranje RTSP videoizvora..."
        )

        kamera = Kamera(
            RTSP_URL
        )

        kamera.otvori()

        # ====================================================
        # TRACKING I OCR
        # ====================================================

        pracenje = PracenjePlocica()
        ocr = OCRRegistracije()

        print(
            "[INFO] Dijagnosticki test pokrenut."
        )

        print(
            "[INFO] EasyOCR: CPU | "
            "YOLO/ByteTrack: GPU ako je dostupan."
        )

        print(
            "[INFO] Za prekid programa pritisni Q."
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

            # =================================================
            # YOLO + BYTETRACK
            # =================================================

            rezultat = pracenje.prati(
                frame
            )

            if (
                rezultat.boxes is not None
                and rezultat.boxes.id is not None
            ):

                boxes = (
                    rezultat.boxes.xyxy
                    .cpu()
                    .numpy()
                )

                ids = (
                    rezultat.boxes.id
                    .int()
                    .cpu()
                    .tolist()
                )

                confidences = (
                    rezultat.boxes.conf
                    .cpu()
                    .tolist()
                )

                # =============================================
                # SVAKI AKTIVNI TRACK ID
                # =============================================

                for box, track_id, yolo_conf in zip(
                    boxes,
                    ids,
                    confidences
                ):

                    track_id = int(
                        track_id
                    )

                    yolo_conf = float(
                        yolo_conf
                    )

                    x1, y1, x2, y2 = map(
                        int,
                        box
                    )

                    visina_framea, sirina_framea = (
                        frame.shape[:2]
                    )

                    x1 = max(
                        0,
                        min(
                            x1,
                            sirina_framea - 1
                        )
                    )

                    x2 = max(
                        0,
                        min(
                            x2,
                            sirina_framea
                        )
                    )

                    y1 = max(
                        0,
                        min(
                            y1,
                            visina_framea - 1
                        )
                    )

                    y2 = max(
                        0,
                        min(
                            y2,
                            visina_framea
                        )
                    )

                    if x2 <= x1 or y2 <= y1:
                        continue

                    # =========================================
                    # TRACKING STATISTIKA
                    # =========================================

                    pracenje.oznaci_vidljiv(
                        track_id,
                        broj_framea
                    )

                    # =========================================
                    # OCR
                    # =========================================

                    if (
                        yolo_conf
                        >= MIN_YOLO_CONF_ZA_OCR
                    ):

                        (
                            crop_x1,
                            crop_y1,
                            crop_x2,
                            crop_y2
                        ) = prosiri_crop(
                            x1,
                            y1,
                            x2,
                            y2,
                            sirina_framea,
                            visina_framea
                        )

                        crop_plocice = frame[
                            crop_y1:crop_y2,
                            crop_x1:crop_x2
                        ].copy()
                        
                        # =================================================
# SPREMANJE NAJBOLJEG CROPA PLOCICE PO ID-u VOZILA
# =================================================

if (
    crop_plocice is not None
    and crop_plocice.size > 0
):

    visina_plocice, sirina_plocice = (
        crop_plocice.shape[:2]
    )

    velicina_plocice = (
        sirina_plocice
        * visina_plocice
    )

    prethodna_velicina = (
        najbolji_crop_velicina.get(
            track_id,
            0
        )
    )

    if (
        velicina_plocice
        > prethodna_velicina
    ):

        putanja_cropa = (
            MAPA_CROPOVA
            / f"ID_{track_id}.jpg"
        )

        cv2.imwrite(
            str(putanja_cropa),
            crop_plocice
        )

        najbolji_crop_velicina[
            track_id
        ] = velicina_plocice

        print(
            f"[CROP] ID {track_id} | "
            f"spremljen najbolji crop | "
            f"{sirina_plocice}x"
            f"{visina_plocice}"
        )

                        # Nova verzija OCR modula vraca
                        # rezultate + dijagnostiku.
                        ocr_rezultat = (
                            ocr.procitaj(
                                crop_plocice
                            )
                        )

                        # Biljezimo svaki OCR pokusaj,
                        # ukljucujuci neuspjesne.
                        pracenje.dodaj_ocr_dijagnostiku(
                            track_id,
                            ocr_rezultat
                        )

                        kandidati = (
                            ocr_rezultat[
                                "kandidati"
                            ]
                        )

                        if kandidati:

                            najbolji_frame = max(
                                kandidati,
                                key=lambda x:
                                x["pouzdanost"]
                            )

                            pracenje.dodaj_ocr(
                                track_id,
                                najbolji_frame[
                                    "tekst"
                                ],
                                najbolji_frame[
                                    "pouzdanost"
                                ],
                                broj_framea
                            )

                    # =========================================
                    # TRENUTNI NAJBOLJI KANDIDAT
                    # =========================================

                    kandidat = (
                        pracenje.najbolji_kandidat(
                            track_id
                        )
                    )

                    # =========================================
                    # CRTANJE
                    # =========================================

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
                            f"plocica {yolo_conf:.2f}"
                        ),
                        (
                            x1,
                            max(
                                30,
                                y1 - 38
                            )
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA
                    )

                    if kandidat is not None:

                        status = odredi_status(
                            kandidat
                        )

                        tekst_ocr = (
                            f"{status}: "
                            f"{kandidat['tekst']} "
                            f"({kandidat['broj_potvrda']}x)"
                        )

                    else:

                        tekst_ocr = (
                            "OCR: nema valjanog kandidata"
                        )

                    cv2.putText(
                        prikaz,
                        tekst_ocr,
                        (
                            x1,
                            max(
                                55,
                                y1 - 10
                            )
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA
                    )

            # =================================================
            # NEAKTIVNI ID-evi
            # =================================================

            neaktivni = (
                pracenje.neaktivni_id_evi(
                    broj_framea,
                    PRAG_NEAKTIVNOSTI
                )
            )

            for track_id in neaktivni:

                if track_id in zavrseni_id_evi:

                    pracenje.ukloni_id(
                        track_id
                    )

                    continue

                kandidat = (
                    pracenje.najbolji_kandidat(
                        track_id
                    )
                )

                dijagnostika = (
                    pracenje.dohvati_dijagnostiku(
                        track_id
                    )
                )

                status = odredi_status(
                    kandidat
                )

                broj_zavrsenih += 1

                # =============================================
                # KONACNI OCR STATUS
                # =============================================

                if kandidat is None:

                    broj_bez_ocr += 1

                    rezultat_tekst = (
                        "OCR NIJE USPJESAN"
                    )

                else:

                    if status == "POTVRDEN":

                        broj_potvrdenih += 1

                    elif status == "STABILAN":

                        broj_stabilnih += 1

                    else:

                        broj_kandidata += 1

                    rezultat_tekst = (
                        f"{status} | "
                        f"{kandidat['tekst']} | "
                        f"ponavljanja: "
                        f"{kandidat['broj_potvrda']} | "
                        f"prosjecni conf: "
                        f"{kandidat['prosjecna_pouzdanost']:.2f}"
                    )

                # =============================================
                # DIJAGNOSTICKI ISPIS
                # =============================================

                print()
                print(
                    "-" * 76
                )

                print(
                    f"[ID {track_id}] "
                    f"{rezultat_tekst}"
                )

                print(
                    f"  Pracen kroz frameova:       "
                    f"{dijagnostika['broj_frameova']}"
                )

                print(
                    f"  OCR pokusaja:               "
                    f"{dijagnostika['broj_ocr_pokusaja']}"
                )

                print(
                    f"  Sirovih EasyOCR rezultata:  "
                    f"{dijagnostika['broj_sirovih']}"
                )

                print(
                    f"  Valjanih OCR rezultata:     "
                    f"{dijagnostika['broj_valjanih']}"
                )

                print(
                    f"  Odbijeno - nizak conf:      "
                    f"{dijagnostika['niska_pouzdanost']}"
                )

                print(
                    f"  Odbijeno - prekratko:       "
                    f"{dijagnostika['prekratki']}"
                )

                print(
                    f"  Odbijeno - predugo:         "
                    f"{dijagnostika['predugi']}"
                )

                print(
                    f"  Odbijeno - prazno:          "
                    f"{dijagnostika['prazni']}"
                )

                zavrseni_id_evi.add(
                    track_id
                )

                pracenje.ukloni_id(
                    track_id
                )

            # =================================================
            # HUD
            # =================================================

            cv2.putText(
                prikaz,
                "TEST 10 - OCR DIJAGNOSTIKA",
                (30, 140),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )

            cv2.putText(
                prikaz,
                f"Frame: {broj_framea}",
                (30, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            statistika = (
                f"ID: {broj_zavrsenih} | "
                f"Potvrden: {broj_potvrdenih} | "
                f"Stabilan: {broj_stabilnih} | "
                f"Kandidat: {broj_kandidata} | "
                f"Bez OCR: {broj_bez_ocr}"
            )

            cv2.putText(
                prikaz,
                statistika,
                (30, 220),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            # =================================================
            # PRIKAZ
            # =================================================

            if PRIKAZ_VIDEA:

                prikaz = prilagodi_prikaz(
                    prikaz
                )

                cv2.imshow(
                    NAZIV_PROZORA,
                    prikaz
                )

                if (
                    cv2.waitKey(1) & 0xFF
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
        print("ZAVRSNA STATISTIKA")
        print("=" * 76)

        print(
            f"Zavrseni track ID-evi: "
            f"{broj_zavrsenih}"
        )

        print(
            f"OCR potvrden:           "
            f"{broj_potvrdenih}"
        )

        print(
            f"OCR stabilan:           "
            f"{broj_stabilnih}"
        )

        print(
            f"Najbolji kandidat:       "
            f"{broj_kandidata}"
        )

        print(
            f"Bez OCR rezultata:       "
            f"{broj_bez_ocr}"
        )

        print("=" * 76)
        print(
            "[INFO] Dijagnosticki test zavrsen."
        )


if __name__ == "__main__":
    main()