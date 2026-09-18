import cv2
import easyocr
import re


class OCRRegistracije:
    """
    OCR modul za citanje registarskih plocica.

    Modul prima crop prethodno detektirane registarske
    plocice, priprema ga za OCR i vraca valjane kandidate.

    Uz rezultate se vracaju i dijagnosticki podaci kako bi
    se moglo utvrditi u kojoj fazi OCR obrade dolazi do
    gubitka rezultata.
    """

    def __init__(self):

        print("[INFO] Ucitavanje EasyOCR modela na CPU...")

        self.reader = easyocr.Reader(
            ["en"],
            gpu=False
        )

        self.min_pouzdanost = 0.25
        self.min_znakova = 4
        self.max_znakova = 10

        print("[OK] EasyOCR model uspjesno ucitan na CPU.")

    def pripremi_crop(self, crop_plocice):
        """
        Povecava crop registarske plocice radi lakseg
        OCR prepoznavanja znakova.
        """

        if crop_plocice is None:
            return None

        if crop_plocice.size == 0:
            return None

        visina, sirina = crop_plocice.shape[:2]

        if visina < 2 or sirina < 2:
            return None

        faktor = 3

        povecana = cv2.resize(
            crop_plocice,
            (
                sirina * faktor,
                visina * faktor
            ),
            interpolation=cv2.INTER_CUBIC
        )

        return povecana

    def normaliziraj_tekst(self, tekst):
        """
        Normalizira OCR rezultat:
        - pretvara tekst u velika slova
        - uklanja sve osim A-Z i 0-9
        """

        if tekst is None:
            return ""

        tekst = tekst.upper().strip()

        tekst = re.sub(
            r"[^A-Z0-9]",
            "",
            tekst
        )

        return tekst

    def razlog_odbijanja(
        self,
        tekst,
        pouzdanost
    ):
        """
        Vraca razlog zbog kojeg kandidat nije prihvacen.

        Ako je rezultat valjan, vraca None.
        """

        if not tekst:
            return "prazan"

        if pouzdanost < self.min_pouzdanost:
            return "niska_pouzdanost"

        if len(tekst) < self.min_znakova:
            return "prekratak"

        if len(tekst) > self.max_znakova:
            return "predug"

        return None

    def procitaj(
        self,
        crop_plocice
    ):
        """
        Izvodi OCR i vraca:

        {
            "kandidati": [...],
            "broj_sirovih": X,
            "broj_valjanih": X,
            "odbijeni": {
                "prazan": X,
                "niska_pouzdanost": X,
                "prekratak": X,
                "predug": X
            }
        }
        """

        dijagnostika = {
            "kandidati": [],
            "broj_sirovih": 0,
            "broj_valjanih": 0,
            "odbijeni": {
                "prazan": 0,
                "niska_pouzdanost": 0,
                "prekratak": 0,
                "predug": 0
            }
        }

        pripremljena = self.pripremi_crop(
            crop_plocice
        )

        if pripremljena is None:
            return dijagnostika

        rezultati = self.reader.readtext(
            pripremljena,
            detail=1,
            paragraph=False,
            allowlist=(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "0123456789"
            )
        )

        dijagnostika[
            "broj_sirovih"
        ] = len(rezultati)

        for _, tekst, pouzdanost in rezultati:

            tekst = self.normaliziraj_tekst(
                tekst
            )

            pouzdanost = float(
                pouzdanost
            )

            razlog = self.razlog_odbijanja(
                tekst,
                pouzdanost
            )

            if razlog is not None:

                dijagnostika[
                    "odbijeni"
                ][
                    razlog
                ] += 1

                continue

            dijagnostika[
                "kandidati"
            ].append({
                "tekst": tekst,
                "pouzdanost": pouzdanost
            })

        dijagnostika[
            "broj_valjanih"
        ] = len(
            dijagnostika["kandidati"]
        )

        return dijagnostika