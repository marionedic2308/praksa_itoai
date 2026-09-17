# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# FAZA 02 - YOLO DETEKCIJA VOZILA NA STVARNOM VIDEOIZVORU
# ============================================================

import cv2
import csv
import os
from datetime import datetime
from collections import Counter

from config import (
    RTSP_URL,
    NAZIV_PROZORA,
    PRIKAZ_VIDEA,
)

from camera import Kamera
from detection import DetektorVozila


# ============================================================
# POSTAVKE PRIKAZA
# ============================================================

MAKSIMALNA_SIRINA_PRIKAZA = 1600
MAKSIMALNA_VISINA_PRIKAZA = 900

MAPA_REZULTATA = "rezultati"
CSV_DATOTEKA = os.path.join(
    MAPA_REZULTATA,
    "detekcije.csv"
)

NAZIVI_KLASA = {
    2: "car",
    5: "bus",
    7: "truck",
}


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


def spremi_csv(zapisi):

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

        writer = csv.writer(datoteka)

        writer.writerow([
            "vrijeme",
            "klasa",
            "pouzdanost"
        ])

        writer.writerows(zapisi)


def main():

    print("=" * 60)
    print("TEST 09 - STVARNI VIDEOIZVOR")
    print("FAZA 02 - YOLO DETEKCIJA VOZILA")
    print("=" * 60)

    detektor = DetektorVozila(
        model_path="../yolo11n.pt",
        confidence=0.25,
        image_size=640
    )

    brojac = Counter()
    zapisi = []

    print("[INFO] Povezivanje na RTSP videoizvor...")

    kamera = Kamera(RTSP_URL)

    try:

        kamera.otvori()

        print("[INFO] Videoizvor je spreman.")
        print("[INFO] YOLO detekcija vozila je aktivna.")
        print("[INFO] Za prekid prikaza pritisni tipku Q.")

        while True:

            uspjeh, frame = kamera.procitaj_frame()

            if not uspjeh or frame is None:
                print(
                    "[UPOZORENJE] Nije moguce procitati frame."
                )
                break

            rezultat = detektor.detektiraj(frame)

            if rezultat is not None:

                prikaz = rezultat.plot()

                if rezultat.boxes is not None:

                    klase = (
                        rezultat.boxes.cls
                        .int()
                        .cpu()
                        .tolist()
                    )

                    pouzdanosti = (
                        rezultat.boxes.conf
                        .cpu()
                        .tolist()
                    )

                    vrijeme = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S.%f"
                    )[:-3]

                    for klasa_id, pouzdanost in zip(
                        klase,
                        pouzdanosti
                    ):

                        naziv = NAZIVI_KLASA.get(
                            klasa_id,
                            "unknown"
                        )

                        brojac[naziv] += 1

                        zapisi.append([
                            vrijeme,
                            naziv,
                            round(
                                float(pouzdanost),
                                4
                            )
                        ])

            else:

                prikaz = frame.copy()

            prikaz_ekran = prilagodi_prikaz(
                prikaz
            )

            if PRIKAZ_VIDEA:

                cv2.imshow(
                    NAZIV_PROZORA,
                    prikaz_ekran
                )

                if cv2.waitKey(1) & 0xFF == ord("q"):

                    print(
                        "[INFO] Korisnik je zaustavio prikaz."
                    )

                    break

    except KeyboardInterrupt:

        print(
            "\n[INFO] Program je prekinut putem tipkovnice."
        )

    except Exception as greska:

        print(
            f"[GRESKA] {greska}"
        )

    finally:

        kamera.zatvori()
        cv2.destroyAllWindows()

        spremi_csv(zapisi)

        ukupno = sum(
            brojac.values()
        )

        print()
        print("=" * 60)
        print("ZAVRSNA STATISTIKA DETEKCIJA")
        print("=" * 60)

        print(
            f"Ukupno YOLO detekcija : {ukupno}"
        )

        print(
            f"Car                  : {brojac['car']}"
        )

        print(
            f"Bus                  : {brojac['bus']}"
        )

        print(
            f"Truck                : {brojac['truck']}"
        )

        print("-" * 60)

        print(
            f"[OK] Rezultati spremljeni: {CSV_DATOTEKA}"
        )

        print()
        print(
            "[NAPOMENA] Rezultati predstavljaju broj YOLO "
            "detekcija po frameovima, a ne broj jedinstvenih vozila."
        )

        print("=" * 60)
        print("[OK] Program zavrsen.")


if __name__ == "__main__":
    main()