from pathlib import Path
import re

import cv2
from paddleocr import PaddleOCR


# ============================================================
# POSTAVKE
# ============================================================

TRENUTNA_MAPA = Path(__file__).resolve().parent

MAPA_CROPOVA = (
    TRENUTNA_MAPA
    / "rezultati"
    / "najbolji_cropovi"
)

DOZVOLJENI_ZNAKOVI = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
)


def normaliziraj_tekst(tekst):
    """
    OCR rezultat pretvara u oblik pogodan za
    registarske plocice.

    Uklanjaju se razmaci, crtice i ostali znakovi,
    a ostaju samo velika slova A-Z i znamenke 0-9.
    """

    if tekst is None:
        return ""

    tekst = str(tekst).upper()

    tekst = "".join(
        znak
        for znak in tekst
        if znak in DOZVOLJENI_ZNAKOVI
    )

    return tekst


def izdvoji_id_i_klasu(putanja):
    """
    Iz naziva slike oblika:

        ID_0012_car.jpg

    izdvaja:
        ID = 12
        klasa = car
    """

    podudaranje = re.match(
        r"ID_(\d+)_(.+)$",
        putanja.stem
    )

    if podudaranje is None:
        return None, "unknown"

    track_id = int(
        podudaranje.group(1)
    )

    klasa = (
        podudaranje.group(2)
    )

    return track_id, klasa


def pripremi_sliku(slika):
    """
    Jednostavna priprema cropa za OCR.

    Crop se povecava kako bi znakovi registarske
    plocice imali vise piksela za OCR model.
    """

    if (
        slika is None
        or slika.size == 0
    ):
        return None

    visina, sirina = (
        slika.shape[:2]
    )

    # Manje cropove povecavamo vise.
    if sirina < 150:
        faktor = 4
    elif sirina < 250:
        faktor = 3
    else:
        faktor = 2

    nova_sirina = (
        sirina * faktor
    )

    nova_visina = (
        visina * faktor
    )

    povecana = cv2.resize(
        slika,
        (
            nova_sirina,
            nova_visina
        ),
        interpolation=cv2.INTER_CUBIC
    )

    return povecana


def izdvoji_rezultate(predikcija):
    """
    PaddleOCR 3.x vraca rezultate u novijem formatu.

    Funkcija iz rezultata izdvaja:
        - prepoznati tekst
        - OCR pouzdanost

    Ako postoji vise tekstualnih elemenata,
    spajaju se redoslijedom kojim ih OCR vrati.
    """

    tekstovi = []
    pouzdanosti = []

    if predikcija is None:
        return "", 0.0

    try:

        for rezultat in predikcija:

            # PaddleOCR/PaddleX rezultat moze se
            # ponasati kao dictionary objekt.

            if hasattr(
                rezultat,
                "json"
            ):

                podaci = rezultat.json

                if callable(podaci):
                    podaci = podaci()

                if isinstance(
                    podaci,
                    dict
                ):

                    # U nekim verzijama stvarni rezultat
                    # nalazi se unutar "res".

                    if (
                        "res" in podaci
                        and isinstance(
                            podaci["res"],
                            dict
                        )
                    ):
                        podaci = (
                            podaci["res"]
                        )

                    rec_texts = (
                        podaci.get(
                            "rec_texts",
                            []
                        )
                    )

                    rec_scores = (
                        podaci.get(
                            "rec_scores",
                            []
                        )
                    )

                    for indeks, tekst in enumerate(
                        rec_texts
                    ):

                        cisti = (
                            normaliziraj_tekst(
                                tekst
                            )
                        )

                        if not cisti:
                            continue

                        tekstovi.append(
                            cisti
                        )

                        if (
                            indeks
                            < len(rec_scores)
                        ):
                            pouzdanosti.append(
                                float(
                                    rec_scores[
                                        indeks
                                    ]
                                )
                            )

            elif isinstance(
                rezultat,
                dict
            ):

                podaci = rezultat

                rec_texts = (
                    podaci.get(
                        "rec_texts",
                        []
                    )
                )

                rec_scores = (
                    podaci.get(
                        "rec_scores",
                        []
                    )
                )

                for indeks, tekst in enumerate(
                    rec_texts
                ):

                    cisti = (
                        normaliziraj_tekst(
                            tekst
                        )
                    )

                    if not cisti:
                        continue

                    tekstovi.append(
                        cisti
                    )

                    if (
                        indeks
                        < len(rec_scores)
                    ):
                        pouzdanosti.append(
                            float(
                                rec_scores[
                                    indeks
                                ]
                            )
                        )

    except Exception as greska:

        print(
            "[UPOZORENJE] Problem pri "
            "citanju OCR rezultata:"
        )

        print(
            greska
        )

        return "", 0.0

    if not tekstovi:
        return "", 0.0

    tekst = "".join(
        tekstovi
    )

    if pouzdanosti:

        prosjecna_pouzdanost = (
            sum(pouzdanosti)
            / len(pouzdanosti)
        )

    else:

        prosjecna_pouzdanost = 0.0

    return (
        tekst,
        prosjecna_pouzdanost
    )


def main():

    print("=" * 76)

    print(
        "TEST 10 - OFFLINE OCR REGISTARSKIH PLOCICA"
    )

    print(
        "NAJBOLJI CROP -> PADDLEOCR -> TEKST"
    )

    print("=" * 76)

    # ========================================================
    # PROVJERA MAPE
    # ========================================================

    if not MAPA_CROPOVA.exists():

        print(
            "[GRESKA] Mapa s cropovima "
            "ne postoji:"
        )

        print(
            MAPA_CROPOVA
        )

        return

    slike = sorted(
        list(
            MAPA_CROPOVA.glob(
                "*.jpg"
            )
        )
        +
        list(
            MAPA_CROPOVA.glob(
                "*.jpeg"
            )
        )
        +
        list(
            MAPA_CROPOVA.glob(
                "*.png"
            )
        )
    )

    if not slike:

        print(
            "[GRESKA] Nisu pronadene "
            "slike registarskih plocica."
        )

        return

    print(
        f"[INFO] Pronadeno cropova: "
        f"{len(slike)}"
    )

    # ========================================================
    # UCITAVANJE PADDLEOCR-a
    # ========================================================

    print(
        "[INFO] Ucitavanje PaddleOCR modela..."
    )

    ocr = PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False
    )

    print(
        "[OK] PaddleOCR model uspjesno ucitan."
    )

    print()

    broj_uspjesnih = 0
    broj_bez_rezultata = 0

    # ========================================================
    # OBRADA SVAKE SPREMLJENE PLOCICE
    # ========================================================

    for indeks, putanja in enumerate(
        slike,
        start=1
    ):

        track_id, klasa = (
            izdvoji_id_i_klasu(
                putanja
            )
        )

        slika = cv2.imread(
            str(putanja)
        )

        print("-" * 76)

        print(
            f"[{indeks}/{len(slike)}]"
        )

        print(
            f"Datoteka:       "
            f"{putanja.name}"
        )

        print(
            f"ID vozila:      "
            f"{track_id}"
        )

        print(
            f"Klasa vozila:   "
            f"{klasa}"
        )

        if (
            slika is None
            or slika.size == 0
        ):

            print(
                "OCR rezultat:   "
                "GRESKA PRI UCITAVANJU SLIKE"
            )

            broj_bez_rezultata += 1

            continue

        visina, sirina = (
            slika.shape[:2]
        )

        print(
            f"Original crop:   "
            f"{sirina}x{visina}"
        )

        pripremljena = (
            pripremi_sliku(
                slika
            )
        )

        if pripremljena is None:

            print(
                "OCR rezultat:   "
                "NEUSPJELA PRIPREMA SLIKE"
            )

            broj_bez_rezultata += 1

            continue

        # ====================================================
        # PADDLEOCR
        # ====================================================

        try:

            predikcija = ocr.predict(
                pripremljena
            )

            (
                tekst,
                pouzdanost
            ) = izdvoji_rezultate(
                predikcija
            )

        except Exception as greska:

            print(
                "OCR rezultat:   "
                "GRESKA"
            )

            print(
                f"Detalj:         "
                f"{greska}"
            )

            broj_bez_rezultata += 1

            continue

        # ====================================================
        # ISPIS
        # ====================================================

        if tekst:

            broj_uspjesnih += 1

            print(
                f"OCR rezultat:   "
                f"{tekst}"
            )

            print(
                f"Pouzdanost:     "
                f"{pouzdanost:.2f}"
            )

        else:

            broj_bez_rezultata += 1

            print(
                "OCR rezultat:   "
                "NIJE PREPOZNAT TEKST"
            )

    # ========================================================
    # ZAVRSNA STATISTIKA
    # ========================================================

    print()
    print("=" * 76)

    print(
        "ZAVRSNA STATISTIKA"
    )

    print("=" * 76)

    print(
        f"Ukupno cropova:        "
        f"{len(slike)}"
    )

    print(
        f"OCR dao rezultat:      "
        f"{broj_uspjesnih}"
    )

    print(
        f"Bez OCR rezultata:      "
        f"{broj_bez_rezultata}"
    )

    print("=" * 76)

    print(
        "[INFO] Offline OCR test zavrsen."
    )


if __name__ == "__main__":
    main()