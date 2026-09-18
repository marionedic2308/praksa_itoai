# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# FAZA 05 - KALIBRACIJA LINIJA ZA ODREDIVANJE SMJERA
# ============================================================

import cv2

from config import RTSP_URL
from camera import Kamera


# ============================================================
# POSTAVKE PRIKAZA
# ============================================================

MAKSIMALNA_SIRINA_PRIKAZA = 1600
MAKSIMALNA_VISINA_PRIKAZA = 900

NAZIV_PROZORA = "Test 09/05 - Kalibracija linija za smjer"

# Potrebno je ukupno 8 tocaka:
#
# 1. i 2. tocka = Traka 1 - L1
# 3. i 4. tocka = Traka 1 - L2
#
# 5. i 6. tocka = Traka 2 - L1
# 7. i 8. tocka = Traka 2 - L2
#
# Redoslijed L1 -> L2 kasnije ce predstavljati
# ocekivani smjer kretanja za pojedinu traku.

tocke = []

originalni_frame = None
prikaz = None

faktor_prikaza = 1.0


# ============================================================
# DEFINICIJA LINIJA ZA KALIBRACIJU
# ============================================================

DEFINICIJE_LINIJA = [
    {
        "naziv": "TRAKA 1 - L1",
        "kljuc": "L1",
        "traka": "Traka 1",
        "boja": (0, 255, 0)
    },
    {
        "naziv": "TRAKA 1 - L2",
        "kljuc": "L2",
        "traka": "Traka 1",
        "boja": (0, 180, 0)
    },
    {
        "naziv": "TRAKA 2 - L1",
        "kljuc": "L1",
        "traka": "Traka 2",
        "boja": (0, 255, 255)
    },
    {
        "naziv": "TRAKA 2 - L2",
        "kljuc": "L2",
        "traka": "Traka 2",
        "boja": (0, 180, 180)
    }
]


# ============================================================
# PRILAGODBA FRAMEA ZA PRIKAZ
# ============================================================

def pripremi_prikaz(frame):

    global faktor_prikaza

    visina, sirina = frame.shape[:2]

    faktor_sirine = (
        MAKSIMALNA_SIRINA_PRIKAZA
        /
        sirina
    )

    faktor_visine = (
        MAKSIMALNA_VISINA_PRIKAZA
        /
        visina
    )

    faktor_prikaza = min(
        faktor_sirine,
        faktor_visine,
        1.0
    )

    nova_sirina = int(
        sirina * faktor_prikaza
    )

    nova_visina = int(
        visina * faktor_prikaza
    )

    if faktor_prikaza < 1.0:

        return cv2.resize(
            frame,
            (
                nova_sirina,
                nova_visina
            ),
            interpolation=cv2.INTER_AREA
        )

    return frame.copy()


# ============================================================
# PRETVARANJE ORIGINALNE TOCKE U PRIKAZ
# ============================================================

def tocka_za_prikaz(tocka):

    x, y = tocka

    return (
        int(x * faktor_prikaza),
        int(y * faktor_prikaza)
    )


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

    for indeks, tocka in enumerate(tocke):

        # Svake dvije tocke pripadaju jednoj liniji.
        indeks_linije = indeks // 2

        definicija = (
            DEFINICIJE_LINIJA[indeks_linije]
        )

        boja = definicija["boja"]

        x_prikaz, y_prikaz = (
            tocka_za_prikaz(tocka)
        )

        cv2.circle(
            prikaz,
            (
                x_prikaz,
                y_prikaz
            ),
            7,
            boja,
            -1
        )

    # --------------------------------------------------------
    # CRTANJE GOTOVIH LINIJA
    # --------------------------------------------------------

    broj_gotovih_linija = (
        len(tocke) // 2
    )

    for indeks_linije in range(
        broj_gotovih_linija
    ):

        definicija = (
            DEFINICIJE_LINIJA[indeks_linije]
        )

        indeks_prve_tocke = (
            indeks_linije * 2
        )

        indeks_druge_tocke = (
            indeks_prve_tocke + 1
        )

        p1 = tocka_za_prikaz(
            tocke[indeks_prve_tocke]
        )

        p2 = tocka_za_prikaz(
            tocke[indeks_druge_tocke]
        )

        boja = definicija["boja"]

        cv2.line(
            prikaz,
            p1,
            p2,
            boja,
            4
        )

        cv2.putText(
            prikaz,
            definicija["naziv"],
            (
                p1[0],
                max(
                    p1[1] - 12,
                    30
                )
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            boja,
            2,
            cv2.LINE_AA
        )


# ============================================================
# ISPIS GOTOVIH KOORDINATA
# ============================================================

def ispisi_koordinate():

    if len(tocke) != 8:
        return

    print()
    print("=" * 70)
    print("KALIBRACIJA SMJERA ZAVRSENA")
    print("=" * 70)

    print()
    print("LINIJE_SMJERA = {")

    print('    "Traka 1": {')

    print(
        f'        "L1": '
        f'({tocke[0]}, {tocke[1]}),'
    )

    print(
        f'        "L2": '
        f'({tocke[2]}, {tocke[3]}),'
    )

    print("    },")

    print('    "Traka 2": {')

    print(
        f'        "L1": '
        f'({tocke[4]}, {tocke[5]}),'
    )

    print(
        f'        "L2": '
        f'({tocke[6]}, {tocke[7]}),'
    )

    print("    },")

    print("}")

    print()
    print("=" * 70)

    print(
        "Koordinate su izrazene u ORIGINALNOJ "
        "rezoluciji videoizvora."
    )

    print()

    print(
        "Redoslijed L1 -> L2 koristit ce se "
        "za potvrdu ocekivanog smjera kretanja."
    )

    print("=" * 70)


# ============================================================
# INFORMACIJA O TRENUTNOJ LINIJI
# ============================================================

def trenutna_definicija():

    if len(tocke) >= 8:
        return None

    indeks_linije = (
        len(tocke) // 2
    )

    return (
        DEFINICIJE_LINIJA[indeks_linije]
    )


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

    # Nakon osam tocaka kalibracija je gotova.
    if len(tocke) >= 8:
        return

    # Klik je napravljen na smanjenom prikazu.
    # Koordinate se vracaju u originalnu
    # rezoluciju videoizvora.

    original_x = int(
        x / faktor_prikaza
    )

    original_y = int(
        y / faktor_prikaza
    )

    definicija = trenutna_definicija()

    tocke.append(
        (
            original_x,
            original_y
        )
    )

    broj_tocke = len(tocke)

    # Je li klik prva ili druga tocka
    # aktualne virtualne linije.
    lokalni_broj_tocke = (
        1
        if broj_tocke % 2 == 1
        else 2
    )

    print(
        f"[{definicija['naziv']} - "
        f"TOCKA {lokalni_broj_tocke}] "
        f"({original_x}, {original_y})"
    )

    osvjezi_prikaz()

    # --------------------------------------------------------
    # ZAVRSENA JEDNA LINIJA
    # --------------------------------------------------------

    if broj_tocke % 2 == 0:

        print()

        print(
            f"[OK] {definicija['naziv']} "
            f"je definirana."
        )

        # Ako jos nisu definirane sve linije,
        # ispisuje se sljedeca.
        if broj_tocke < 8:

            sljedeca = (
                trenutna_definicija()
            )

            print(
                f"[UPUTA] Sada oznaci dvije tocke "
                f"za {sljedeca['naziv']}."
            )

            print()

        # Sve cetiri linije su definirane.
        else:

            ispisi_koordinate()


# ============================================================
# GLAVNI PROGRAM
# ============================================================

def main():

    global originalni_frame

    print("=" * 70)
    print("TEST 09 - STVARNI VIDEOIZVOR")
    print("FAZA 05 - KALIBRACIJA LINIJA ZA SMJER")
    print("=" * 70)

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

        uspjeh, frame = (
            kamera.procitaj_frame()
        )

        if not uspjeh or frame is None:

            raise RuntimeError(
                "Nije moguce preuzeti frame "
                "sa videoizvora."
            )

        # Zamrzava se jedan aktualni frame.
        originalni_frame = (
            frame.copy()
        )

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
        print("-" * 70)
        print("UPUTE")
        print("-" * 70)

        print(
            "1. Oznaci dvije tocke za TRAKU 1 - L1."
        )

        print(
            "2. Oznaci dvije tocke za TRAKU 1 - L2."
        )

        print(
            "3. Oznaci dvije tocke za TRAKU 2 - L1."
        )

        print(
            "4. Oznaci dvije tocke za TRAKU 2 - L2."
        )

        print(
            "5. Tipka R ponistava sve tocke."
        )

        print(
            "6. Tipka Q zatvara kalibraciju."
        )

        print("-" * 70)

        print()
        print(
            "[UPUTA] Oznaci dvije tocke "
            "za TRAKU 1 - L1."
        )
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
                    "tocke za TRAKU 1 - L1."
                )

                print()

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