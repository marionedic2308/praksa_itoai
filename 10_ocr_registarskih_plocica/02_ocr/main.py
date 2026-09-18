import cv2
from collections import Counter, defaultdict

from camera import Kamera
from config import (
    RTSP_URL,
    NAZIV_PROZORA,
    PRIKAZ_VIDEA,
    MAX_SIRINA_PRIKAZA,
    MAX_VISINA_PRIKAZA,
)
from detection import DetektorPlocica
from ocr import OCRRegistracije


# ============================================================
# POSTAVKE STABILIZACIJE OCR-a
# ============================================================

# Koliko puta isti OCR tekst mora biti procitan
# prije nego sto ga smatramo potvrdenim.
MIN_POTVRDA = 3

# Koliko zadnjih OCR rezultata pamtimo.
MAX_POVIJEST = 12

# Ako neko vrijeme nema detektirane plocice,
# prethodnu OCR povijest brisemo kako se rezultati
# razlicitih vozila ne bi mijesali.
FRAMEOVA_BEZ_PLOCICE_ZA_RESET = 15


def prilagodi_prikaz(frame):
    """
    Smanjuje frame samo za prikaz na ekranu.
    Obrada se i dalje izvodi nad originalnom rezolucijom.
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
            (int(sirina * faktor), int(visina * faktor)),
            interpolation=cv2.INTER_AREA
        )

    return frame


def prosiri_crop(x1, y1, x2, y2, sirina_framea, visina_framea):
    """
    Dodaje mali prostor oko YOLO bounding boxa.

    Preuski crop moze odrezati rubove znakova registarske
    plocice i time smanjiti kvalitetu OCR-a.
    """

    sirina_boxa = x2 - x1
    visina_boxa = y2 - y1

    dodatak_x = int(sirina_boxa * 0.10)
    dodatak_y = int(visina_boxa * 0.15)

    novi_x1 = max(0, x1 - dodatak_x)
    novi_y1 = max(0, y1 - dodatak_y)

    novi_x2 = min(
        sirina_framea,
        x2 + dodatak_x
    )

    novi_y2 = min(
        visina_framea,
        y2 + dodatak_y
    )

    return novi_x1, novi_y1, novi_x2, novi_y2


def main():

    print("=" * 65)
    print("TEST 10 - FAZA 02 - STABILIZIRANI OCR REGISTARSKIH PLOCICA")
    print("=" * 65)

    kamera = None

    # Povijest OCR kandidata za trenutno promatranu plocicu.
    povijest = []

    # Za svaki tekst pamtimo njegove OCR confidence vrijednosti.
    pouzdanosti = defaultdict(list)

    # Zadnji potvrdeni rezultat.
    potvrdeni_tekst = None

    # Sprjecava ponavljanje istog terminalskog ispisa.
    vec_ispisano = None

    frameovi_bez_plocice = 0

    try:

        # ====================================================
        # KAMERA
        # ====================================================

        print("[INFO] Otvaranje RTSP videoizvora...")

        kamera = Kamera(RTSP_URL)
        kamera.otvori()

        # ====================================================
        # MODELI
        # ====================================================

        detektor = DetektorPlocica()
        ocr = OCRRegistracije()

        print("[INFO] Detekcija i stabilizirani OCR pokrenuti.")
        print(
            f"[INFO] Za potvrdu OCR-a potrebno je "
            f"{MIN_POTVRDA} ponavljanja istog kandidata."
        )
        print("[INFO] Za prekid programa pritisni Q.")

        broj_framea = 0

        # ====================================================
        # GLAVNA PETLJA
        # ====================================================

        while True:

            uspjeh, frame = kamera.procitaj_frame()

            if not uspjeh or frame is None:
                continue

            broj_framea += 1

            rezultat = detektor.detektiraj(frame)

            prikaz = frame.copy()

            plocica_prisutna = False

            # =================================================
            # DETEKTIRANE PLOCICE
            # =================================================

            if rezultat.boxes is not None:

                for box in rezultat.boxes:

                    plocica_prisutna = True

                    x1, y1, x2, y2 = map(
                        int,
                        box.xyxy[0].tolist()
                    )

                    yolo_conf = float(
                        box.conf[0]
                    )

                    visina_framea, sirina_framea = frame.shape[:2]

                    x1 = max(
                        0,
                        min(x1, sirina_framea - 1)
                    )

                    x2 = max(
                        0,
                        min(x2, sirina_framea)
                    )

                    y1 = max(
                        0,
                        min(y1, visina_framea - 1)
                    )

                    y2 = max(
                        0,
                        min(y2, visina_framea)
                    )

                    if x2 <= x1 or y2 <= y1:
                        continue

                    # =========================================
                    # PROSIRENI CROP
                    # =========================================

                    crop_x1, crop_y1, crop_x2, crop_y2 = prosiri_crop(
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

                    # =========================================
                    # OCR
                    # =========================================

                    ocr_rezultati = ocr.procitaj(
                        crop_plocice
                    )

                    trenutni_kandidat = None
                    trenutni_conf = 0.0

                    if ocr_rezultati:

                        najbolji = max(
                            ocr_rezultati,
                            key=lambda x: x["pouzdanost"]
                        )

                        trenutni_kandidat = najbolji["tekst"]
                        trenutni_conf = najbolji["pouzdanost"]

                        # -------------------------------------
                        # DODAVANJE U POVIJEST
                        # -------------------------------------

                        povijest.append(
                            trenutni_kandidat
                        )

                        pouzdanosti[
                            trenutni_kandidat
                        ].append(
                            trenutni_conf
                        )

                        # Ogranicavamo povijest.
                        if len(povijest) > MAX_POVIJEST:

                            uklonjeni = povijest.pop(0)

                            if pouzdanosti[uklonjeni]:
                                pouzdanosti[
                                    uklonjeni
                                ].pop(0)

                        # -------------------------------------
                        # ANALIZA POVIJESTI
                        # -------------------------------------

                        brojac = Counter(
                            povijest
                        )

                        najcesci_tekst, broj_potvrda = (
                            brojac.most_common(1)[0]
                        )

                        # -------------------------------------
                        # POTVRDA OCR-a
                        # -------------------------------------

                        if broj_potvrda >= MIN_POTVRDA:

                            potvrdeni_tekst = najcesci_tekst

                            lista_conf = pouzdanosti[
                                potvrdeni_tekst
                            ]

                            if lista_conf:

                                prosjecni_conf = (
                                    sum(lista_conf)
                                    / len(lista_conf)
                                )

                            else:

                                prosjecni_conf = 0.0

                            # Ispisujemo samo kada je potvrden
                            # novi rezultat.
                            if potvrdeni_tekst != vec_ispisano:

                                print(
                                    f"[OCR POTVRDEN] "
                                    f"{potvrdeni_tekst} | "
                                    f"potvrde: {broj_potvrda} | "
                                    f"prosjecni OCR confidence: "
                                    f"{prosjecni_conf:.2f}"
                                )

                                vec_ispisano = potvrdeni_tekst

                    # =========================================
                    # VIZUALIZACIJA
                    # =========================================

                    cv2.rectangle(
                        prikaz,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        3
                    )

                    # Ako imamo potvrden rezultat,
                    # prikazujemo samo njega.
                    if potvrdeni_tekst:

                        oznaka = (
                            f"OCR POTVRDEN: "
                            f"{potvrdeni_tekst}"
                        )

                    elif trenutni_kandidat:

                        oznaka = (
                            f"OCR kandidat: "
                            f"{trenutni_kandidat}"
                        )

                    else:

                        oznaka = (
                            f"Plocica "
                            f"{yolo_conf:.2f}"
                        )

                    cv2.putText(
                        prikaz,
                        oznaka,
                        (x1, max(30, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.75,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA
                    )

            # =================================================
            # RESET IZMEDU VOZILA
            # =================================================

            if plocica_prisutna:

                frameovi_bez_plocice = 0

            else:

                frameovi_bez_plocice += 1

                if (
                    frameovi_bez_plocice
                    >= FRAMEOVA_BEZ_PLOCICE_ZA_RESET
                ):

                    if povijest or potvrdeni_tekst:

                        povijest.clear()
                        pouzdanosti.clear()

                        potvrdeni_tekst = None
                        vec_ispisano = None

                    frameovi_bez_plocice = 0

            # =================================================
            # HUD
            # =================================================

            cv2.putText(
                prikaz,
                "TEST 10 - YOLO + EasyOCR - stabilizacija",
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

            if potvrdeni_tekst:

                status = "OCR STATUS: POTVRDEN"

            else:

                status = "OCR STATUS: CEKANJE POTVRDE"

            cv2.putText(
                prikaz,
                status,
                (30, 220),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
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

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:

        print("\n[INFO] Program prekinut.")

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

        print("[INFO] Test zavrsen.")


if __name__ == "__main__":
    main()