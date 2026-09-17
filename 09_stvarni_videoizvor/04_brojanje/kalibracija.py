# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# FAZA 04 - KALIBRACIJA LINIJA ZA BROJANJE PO TRAKAMA
# ============================================================

import cv2

from config import RTSP_URL
from camera import Kamera


# ============================================================
# POSTAVKE PRIKAZA
# ============================================================

MAKSIMALNA_SIRINA_PRIKAZA = 1600
MAKSIMALNA_VISINA_PRIKAZA = 900

NAZIV_PROZORA = "Test 09/04 - Kalibracija linija za brojanje"

# Potrebne su ukupno 4 tocke:
# 1. i 2. tocka = Traka 1
# 3. i 4. tocka = Traka 2
tocke = []

originalni_frame = None
prikaz = None

faktor_prikaza = 1.0


# ============================================================
# PRILAGODBA FRAMEA ZA PRIKAZ
# ============================================================

def pripremi_prikaz(frame):

    global faktor_prikaza

    visina, sirina = frame.shape[:2]

    faktor_sirine = MAKSIMALNA_SIRINA_PRIKAZA / sirina
    faktor_visine = MAKSIMALNA_VISINA_PRIKAZA / visina

    faktor_prikaza = min(
        faktor_sirine,
        faktor_visine,
        1.0
    )

    nova_sirina = int(sirina * faktor_prikaza)
    nova_visina = int(visina * faktor_prikaza)

    if faktor_prikaza < 1.0:

        return cv2.resize(
            frame,
            (nova_sirina, nova_visina),
            interpolation=cv2.INTER_AREA
        )

    return frame.copy()


# ============================================================
# CRTANJE TOCAKA I LINIJA
# ============================================================

def osvjezi_prikaz():

    global prikaz

    prikaz = pripremi_prikaz(
        originalni_frame
    )

    # --------------------------------------------------------
    # CRTANJE ODABRANIH TOCAKA
    # --------------------------------------------------------

    for indeks, (x, y) in enumerate(tocke):

        x_prikaz = int(x * faktor_prikaza)
        y_prikaz = int(y * faktor_prikaza)

        # Traka 1 - zelena
        if indeks < 2:
            boja = (0, 255, 0)

        # Traka 2 - zuta
        else:
            boja = (0, 255, 255)

        cv2.circle(
            prikaz,
            (x_prikaz, y_prikaz),
            7,
            boja,
            -1
        )

    # --------------------------------------------------------
    # TRAKA 1
    # --------------------------------------------------------

    if len(tocke) >= 2:

        p1 = (
            int(tocke[0][0] * faktor_prikaza),
            int(tocke[0][1] * faktor_prikaza)
        )

        p2 = (
            int(tocke[1][0] * faktor_prikaza),
            int(tocke[1][1] * faktor_prikaza)
        )

        cv2.line(
            prikaz,
            p1,
            p2,
            (0, 255, 0),
            4
        )

        cv2.putText(
            prikaz,
            "TRAKA 1",
            (
                p1[0],
                max(p1[1] - 15, 30)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )

    # --------------------------------------------------------
    # TRAKA 2
    # --------------------------------------------------------

    if len(tocke) >= 4:

        p1 = (
            int(tocke[2][0] * faktor_prikaza),
            int(tocke[2][1] * faktor_prikaza)
        )

        p2 = (
            int(tocke[3][0] * faktor_prikaza),
            int(tocke[3][1] * faktor_prikaza)
        )

        cv2.line(
            prikaz,
            p1,
            p2,
            (0, 255, 255),
            4
        )

        cv2.putText(
            prikaz,
            "TRAKA 2",
            (
                p1[0],
                max(p1[1] - 15, 30)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
            cv2.LINE_AA
        )


# ============================================================
# ISPIS GOTOVIH KOORDINATA
# ============================================================

def ispisi_koordinate():

    if len(tocke) != 4:
        return

    print()
    print("=" * 65)
    print("KALIBRACIJA ZAVRSENA")
    print("=" * 65)

    print()
    print("LINIJE_BROJANJA = {")

    print(
        f'    "Traka 1": '
        f'({tocke[0]}, {tocke[1]}),'
    )

    print(
        f'    "Traka 2": '
        f'({tocke[2]}, {tocke[3]}),'
    )

    print("}")

    print()
    print("=" * 65)
    print(
        "Koordinate su izrazene u ORIGINALNOJ "
        "rezoluciji videoizvora."
    )
    print("=" * 65)


# ============================================================
# OBRADA KLIKA MISA
# ============================================================

def klik_misa(
    event,
    x,
    y,
    flags,
    param
):

    if event != cv2.EVENT_LBUTTONDOWN:
        return

    # Nakon cetiri tocke vise se ne prima klik.
    if len(tocke) >= 4:
        return

    # Klik je napravljen na smanjenom prikazu.
    # Koordinate se pretvaraju u originalnu rezoluciju.

    original_x = int(
        x / faktor_prikaza
    )

    original_y = int(
        y / faktor_prikaza
    )

    tocke.append(
        (
            original_x,
            original_y
        )
    )

    broj_tocke = len(tocke)

    # --------------------------------------------------------
    # INFORMACIJE U TERMINALU
    # --------------------------------------------------------

    if broj_tocke <= 2:
        traka = "TRAKA 1"
        lokalni_broj = broj_tocke

    else:
        traka = "TRAKA 2"
        lokalni_broj = broj_tocke - 2

    print(
        f"[{traka} - TOCKA {lokalni_broj}] "
        f"({original_x}, {original_y})"
    )

    osvjezi_prikaz()

    # Nakon prve linije
    if broj_tocke == 2:

        print()
        print(
            "[OK] Linija za TRAKU 1 je definirana."
        )

        print(
            "[UPUTA] Sada oznaci dvije tocke "
            "linije za TRAKU 2."
        )

    # Nakon druge linije
    elif broj_tocke == 4:

        print()
        print(
            "[OK] Linija za TRAKU 2 je definirana."
        )

        ispisi_koordinate()


# ============================================================
# GLAVNI PROGRAM
# ============================================================

def main():

    global originalni_frame

    print("=" * 65)
    print("TEST 09 - STVARNI VIDEOIZVOR")
    print("FAZA 04 - KALIBRACIJA LINIJA ZA BROJANJE")
    print("=" * 65)

    print()
    print(
        "[INFO] Povezivanje na stvarni videoizvor..."
    )

    kamera = Kamera(
        RTSP_URL
    )

    try:

        kamera.otvori()

        print(
            "[OK] Videoizvor je otvoren."
        )

        print(
            "[INFO] Preuzimanje aktualnog framea..."
        )

        uspjeh, frame = kamera.procitaj_frame()

        if not uspjeh or frame is None:

            raise RuntimeError(
                "Nije moguce preuzeti frame "
                "sa videoizvora."
            )

        # Zamrzava se jedan aktualni frame.
        originalni_frame = frame.copy()

        print(
            f"[OK] Originalna rezolucija: "
            f"{originalni_frame.shape[1]} x "
            f"{originalni_frame.shape[0]}"
        )

        osvjezi_prikaz()

        cv2.namedWindow(
            NAZIV_PROZORA,
            cv2.WINDOW_NORMAL
        )

        cv2.setMouseCallback(
            NAZIV_PROZORA,
            klik_misa
        )

        print()
        print("-" * 65)
        print("UPUTE")
        print("-" * 65)

        print(
            "1. Oznaci dvije tocke linije za TRAKU 1."
        )

        print(
            "2. Zatim oznaci dvije tocke linije za TRAKU 2."
        )

        print(
            "3. Tipka R ponistava sve tocke."
        )

        print(
            "4. Tipka Q zatvara kalibraciju."
        )

        print("-" * 65)
        print()

        while True:

            cv2.imshow(
                NAZIV_PROZORA,
                prikaz
            )

            tipka = (
                cv2.waitKey(20)
                & 0xFF
            )

            # Q - izlaz
            if tipka == ord("q"):
                break

            # R - ponovna kalibracija
            if tipka == ord("r"):

                tocke.clear()

                osvjezi_prikaz()

                print()
                print(
                    "[INFO] Sve tocke su ponistene."
                )

                print(
                    "[UPUTA] Ponovno oznaci dvije "
                    "tocke za TRAKU 1."
                )

    except Exception as greska:

        print(
            f"[GRESKA] {greska}"
        )

    finally:

        kamera.zatvori()

        cv2.destroyAllWindows()

        print()
        print(
            "[OK] Kalibracija zavrsena."
        )


if __name__ == "__main__":
    main()