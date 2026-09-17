# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# Glavni program
# ============================================================

import cv2

from config import (
    RTSP_URL,
    NAZIV_PROZORA,
    PRIKAZ_VIDEA,
    SIRINA_PRIKAZA,
)

from camera import Kamera


def prilagodi_prikaz(frame, ciljna_sirina):
    """
    Prilagodava velicinu framea za prikaz na monitoru.

    Omjer sirine i visine izvornog videozapisa ostaje sacuvan,
    tako da ne dolazi do rastezanja ili deformacije slike.
    """

    visina, sirina = frame.shape[:2]

    # Ako je izvorni frame vec manji od zadane sirine,
    # nema potrebe za povecavanjem.
    if sirina <= ciljna_sirina:
        return frame

    omjer = ciljna_sirina / sirina

    nova_sirina = ciljna_sirina
    nova_visina = int(visina * omjer)

    frame_prikaz = cv2.resize(
        frame,
        (nova_sirina, nova_visina),
        interpolation=cv2.INTER_AREA
    )

    return frame_prikaz


def main():

    print("=" * 60)
    print("TEST 09 - STVARNI VIDEOIZVOR")
    print("=" * 60)

    print("Povezivanje na RTSP videoizvor...")

    kamera = Kamera(RTSP_URL)

    try:
        # ----------------------------------------------------
        # Otvaranje RTSP veze
        # ----------------------------------------------------

        kamera.otvori()

        print("[INFO] Videoizvor je spreman.")
        print("[INFO] Za prekid prikaza pritisni tipku Q.")

        # ----------------------------------------------------
        # Glavna petlja za citanje video streama
        # ----------------------------------------------------

        while True:

            uspjeh, frame = kamera.procitaj_frame()

            if not uspjeh or frame is None:
                print(
                    "[UPOZORENJE] Nije moguce procitati frame."
                )
                break

            # ------------------------------------------------
            # Prikaz video streama
            # ------------------------------------------------

            if PRIKAZ_VIDEA:

                # Za prikaz se koristi smanjena kopija framea.
                # Izvorni frame ostaje nepromijenjen za kasniju
                # YOLO obradu.

                frame_prikaz = prilagodi_prikaz(
                    frame,
                    SIRINA_PRIKAZA
                )

                cv2.imshow(
                    NAZIV_PROZORA,
                    frame_prikaz
                )

                # Pritiskom tipke Q prekida se prikaz.
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

        # ----------------------------------------------------
        # Uredno zatvaranje RTSP veze
        # ----------------------------------------------------

        kamera.zatvori()

        cv2.destroyAllWindows()

        print("[OK] Program zavrsen.")


if __name__ == "__main__":
    main()
