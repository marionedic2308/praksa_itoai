import cv2
import easyocr
import re


class OCRRegistracije:
    """
    OCR registarske plocice.

    OCR se izvodi samo kada glavni program odluci
    da za konkretni ID vozila treba pokusati citanje.

    Nakon uspjesnog citanja glavni program vise
    ne poziva OCR za isto vozilo.
    """

    def __init__(self):

        print(
            "[INFO] Ucitavanje EasyOCR modela na CPU..."
        )

        self.reader = easyocr.Reader(
            ["en"],
            gpu=False
        )

        self.min_pouzdanost = 0.25
        self.min_znakova = 4
        self.max_znakova = 10

        print(
            "[OK] EasyOCR model uspjesno ucitan na CPU."
        )

    def normaliziraj_tekst(
        self,
        tekst
    ):

        if tekst is None:
            return ""

        tekst = tekst.upper().strip()

        tekst = re.sub(
            r"[^A-Z0-9]",
            "",
            tekst
        )

        return tekst

    def pripremi_crop(
        self,
        crop_plocice
    ):
        """
        Povecava crop i poboljsava kontrast
        prije OCR obrade.
        """

        if crop_plocice is None:
            return None

        if crop_plocice.size == 0:
            return None

        visina, sirina = (
            crop_plocice.shape[:2]
        )

        if visina < 2 or sirina < 2:
            return None

        # Povecanje plocice.
        povecana = cv2.resize(
            crop_plocice,
            (
                sirina * 4,
                visina * 4
            ),
            interpolation=cv2.INTER_CUBIC
        )

        # Grayscale.
        siva = cv2.cvtColor(
            povecana,
            cv2.COLOR_BGR2GRAY
        )

        # Lokalno poboljsanje kontrasta.
        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        poboljsana = clahe.apply(
            siva
        )

        return poboljsana

    def procitaj(
        self,
        crop_plocice
    ):

        pripremljena = self.pripremi_crop(
            crop_plocice
        )

        if pripremljena is None:
            return []

        rezultati = self.reader.readtext(
            pripremljena,
            detail=1,
            paragraph=False,
            allowlist=(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "0123456789"
            )
        )

        kandidati = []

        for (
            _,
            tekst,
            pouzdanost
        ) in rezultati:

            tekst = self.normaliziraj_tekst(
                tekst
            )

            pouzdanost = float(
                pouzdanost
            )

            if not tekst:
                continue

            if (
                pouzdanost
                < self.min_pouzdanost
            ):
                continue

            if not (
                self.min_znakova
                <= len(tekst)
                <= self.max_znakova
            ):
                continue

            kandidati.append({
                "tekst": tekst,
                "pouzdanost": pouzdanost
            })

        kandidati.sort(
            key=lambda kandidat:
            kandidat["pouzdanost"],
            reverse=True
        )

        return kandidati