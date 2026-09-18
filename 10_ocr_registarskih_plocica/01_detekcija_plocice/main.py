import cv2

from camera import Kamera
from config import (
    RTSP_URL,
    NAZIV_PROZORA,
    PRIKAZ_VIDEA,
    MAX_SIRINA_PRIKAZA,
    MAX_VISINA_PRIKAZA,
)
from detection import DetektorPlocica


def prilagodi_prikaz(frame):
    """
    Smanjuje frame samo za prikaz na ekranu.

    Detekcija se izvodi nad originalnim frameom,
    dok se kopija rezultata prilagodava velicini ekrana.
    """

    visina, sirina = frame.shape[:2]

    faktor = min(
        MAX_SIRINA_PRIKAZA / sirina,
        MAX_VISINA_PRIKAZA / visina,
        1.0
    )

    if faktor < 1.0:
        nova_sirina = int(sirina * faktor)
        nova_visina = int(visina * faktor)

        frame = cv2.resize(
            frame,
            (nova_sirina, nova_visina),
            interpolation=cv2.INTER_AREA
        )

    return frame


def main():

    print("=" * 60)
    print("TEST 10 - DETEKCIJA REGISTARSKIH PLOCICA")
    print("=" * 60)

    kamera = None

    try:

        # ====================================================
        # OTVARANJE STVARNOG RTSP VIDEOIZVORA
        # ====================================================

        print("[INFO] Otvaranje RTSP videoizvora...")

        kamera = Kamera(RTSP_URL)
        kamera.otvori()

        # ====================================================
        # UCITAVANJE MODELA ZA REGISTARSKE PLOCICE
        # ====================================================

        detektor = DetektorPlocica()

        print("[INFO] Pokrenuta detekcija registarskih plocica.")
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

            # ------------------------------------------------
            # DETEKCIJA REGISTARSKIH PLOCICA
            # ------------------------------------------------

            rezultat = detektor.detektiraj(frame)

            # YOLO prikaz bounding boxova
            prikaz = rezultat.plot()

            # ------------------------------------------------
            # BROJ DETEKTIRANIH PLOCICA
            # ------------------------------------------------

            broj_plocica = 0

            if rezultat.boxes is not None:
                broj_plocica = len(rezultat.boxes)

            # ------------------------------------------------
            # INFORMACIJE NA EKRANU
            # ------------------------------------------------

            cv2.putText(
                prikaz,
                f"Detektirane plocice: {broj_plocica}",
                (30, 140),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )

            cv2.putText(
                prikaz,
                f"Frame: {broj_framea}",
                (30, 185),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            # ------------------------------------------------
            # PRIKAZ
            # ------------------------------------------------

            if PRIKAZ_VIDEA:

                prikaz = prilagodi_prikaz(prikaz)

                cv2.imshow(
                    NAZIV_PROZORA,
                    prikaz
                )

                tipka = cv2.waitKey(1) & 0xFF

                if tipka == ord("q"):
                    print("[INFO] Zaustavljanje programa...")
                    break

    except KeyboardInterrupt:

        print("\n[INFO] Program prekinut tipkovnicom.")

    except Exception as greska:

        print(f"[GRESKA] {greska}")

    finally:

        # ====================================================
        # ZATVARANJE
        # ====================================================

        if kamera is not None:
            kamera.zatvori()

        cv2.destroyAllWindows()

        print("[INFO] Test zavrsen.")


if __name__ == "__main__":
    main()