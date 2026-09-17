# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# Glavni program - RTSP videoizvor i pracenje vozila
# ============================================================

import cv2

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


def prilagodi_prikaz(frame):
    """
    Prilagodava frame samo za prikaz na monitoru.

    Originalni frame ostaje u punoj rezoluciji za YOLO,
    ByteTrack i kasniju analizu virtualnih linija.

    Omjer stranica slike ostaje sacuvan.
    """

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


def nacrtaj_tracking(rezultat, tracker):
    """
    Crta bounding box, track ID i stabilnu klasu vozila.

    Crtanje se izvodi na kopiji originalnog framea.
    """

    prikaz = rezultat.orig_img.copy()

    if rezultat.boxes is None:
        return prikaz

    if rezultat.boxes.id is None:
        return prikaz

    boxes = rezultat.boxes.xyxy.int().cpu().tolist()
    ids = rezultat.boxes.id.int().cpu().tolist()

    for box, track_id in zip(boxes, ids):

        x1, y1, x2, y2 = box

        stabilna_klasa_id = tracker.stabilna_klasa(
            track_id
        )

        naziv_klase = tracker.naziv_klase(
            stabilna_klasa_id
        )

        # Bounding box
        cv2.rectangle(
            prikaz,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            3
        )

        # Tekst uz vozilo
        tekst = (
            f"ID {track_id} | {naziv_klase}"
        )

        # Velicina teksta
        (sirina_teksta, visina_teksta), baseline = (
            cv2.getTextSize(
                tekst,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                2
            )
        )

        # Pozicija teksta
        tekst_y = max(
            y1 - 10,
            visina_teksta + 10
        )

        # Pozadina teksta
        cv2.rectangle(
            prikaz,
            (x1, tekst_y - visina_teksta - 8),
            (x1 + sirina_teksta + 10, tekst_y + baseline),
            (0, 0, 0),
            -1
        )

        # Ispis ID-a i klase
        cv2.putText(
            prikaz,
            tekst,
            (x1 + 5, tekst_y - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

    return prikaz


def main():

    print("=" * 60)
    print("TEST 09 - STVARNI VIDEOIZVOR")
    print("=" * 60)

    # --------------------------------------------------------
    # Inicijalizacija YOLO + ByteTrack sustava
    # --------------------------------------------------------

    tracker = PracenjeVozila(
        model_path="yolo11n.pt",
        confidence=0.25,
        image_size=640,
        tracker="bytetrack.yaml"
    )

    # --------------------------------------------------------
    # Povezivanje na stvarni RTSP videoizvor
    # --------------------------------------------------------

    print("[INFO] Povezivanje na RTSP videoizvor...")

    kamera = Kamera(RTSP_URL)

    try:

        kamera.otvori()

        print("[INFO] Videoizvor je spreman.")
        print("[INFO] YOLO detekcija je aktivna.")
        print("[INFO] ByteTrack pracenje je aktivno.")
        print("[INFO] Za prekid prikaza pritisni tipku Q.")

        # ----------------------------------------------------
        # Glavna petlja
        # ----------------------------------------------------

        while True:

            uspjeh, frame = kamera.procitaj_frame()

            if not uspjeh or frame is None:
                print(
                    "[UPOZORENJE] Nije moguce procitati frame."
                )
                break

            # ------------------------------------------------
            # YOLO detekcija + ByteTrack pracenje
            # ------------------------------------------------

            rezultat = tracker.prati(frame)

            # ------------------------------------------------
            # Vizualizacija rezultata
            # ------------------------------------------------

            if rezultat is not None:

                prikaz = nacrtaj_tracking(
                    rezultat,
                    tracker
                )

            else:

                prikaz = frame.copy()

            # ------------------------------------------------
            # Prilagodba SAMO za prikaz na monitoru
            # ------------------------------------------------

            prikaz_ekran = prilagodi_prikaz(
                prikaz
            )

            # ------------------------------------------------
            # Live prikaz
            # ------------------------------------------------

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

        print("[OK] Program zavrsen.")


if __name__ == "__main__":
    main()