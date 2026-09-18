import easyocr
import cv2
import re


class OCRRegistracije:
    """
    OCR modul za citanje znakova s prethodno
    detektirane registarske plocice.

    Modul:
    - povecava crop registarske plocice
    - izvodi OCR pomocu EasyOCR-a
    - normalizira procitani tekst
    - odbacuje ocito nepouzdane rezultate
    """

    def __init__(self):
        print("[INFO] Ucitavanje EasyOCR modela...")

        self.reader = easyocr.Reader(
            ["en"],
            gpu=True
        )

        # Minimalna OCR pouzdanost za prihvacanje kandidata.
        # Namjerno nije previsoka jer su registarske plocice
        # na prometnoj kameri relativno male.
        self.min_pouzdanost = 0.25

        # Osnovna kontrola duljine kandidata.
        self.min_znakova = 4
        self.max_znakova = 10

        print("[OK] EasyOCR model uspjesno ucitan.")

    def pripremi_crop(self, crop_plocice):
        """
        Priprema crop registarske plocice za OCR.

        Crop se povecava kako bi znakovi bili laksi
        za prepoznavanje.
        """

        if crop_plocice is None or crop_plocice.size == 0:
            return None

        visina, sirina = crop_plocice.shape[:2]

        if visina < 2 or sirina < 2:
            return None

        faktor = 3

        povecana = cv2.resize(
            crop_plocice,
            (sirina * faktor, visina * faktor),
            interpolation=cv2.INTER_CUBIC
        )

        return povecana

    def normaliziraj_tekst(self, tekst):
        """
        Pretvara OCR rezultat u standardizirani oblik.

        Zadrzavaju se samo:
        A-Z
        0-9

        Razmaci, crtice, tocke i ostali znakovi
        uklanjaju se radi lakse usporedbe rezultata
        kroz vise frameova.
        """

        tekst = tekst.upper().strip()

        tekst = re.sub(
            r"[^A-Z0-9]",
            "",
            tekst
        )

        return tekst

    def valjan_kandidat(self, tekst, pouzdanost):
        """
        Provjerava zadovoljava li OCR rezultat
        osnovne kriterije kvalitete.
        """

        if not tekst:
            return False

        if pouzdanost < self.min_pouzdanost:
            return False

        if len(tekst) < self.min_znakova:
            return False

        if len(tekst) > self.max_znakova:
            return False

        return True

    def procitaj(self, crop_plocice):
        """
        Izvodi OCR nad jednom detektiranom
        registarskom plocicom.

        Vraca samo kandidate koji zadovoljavaju
        osnovne kriterije kvalitete.
        """

        pripremljena = self.pripremi_crop(
            crop_plocice
        )

        if pripremljena is None:
            return []

        rezultati = self.reader.readtext(
            pripremljena,
            detail=1,
            paragraph=False,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )

        procitano = []

        for _, tekst, pouzdanost in rezultati:

            tekst = self.normaliziraj_tekst(
                tekst
            )

            pouzdanost = float(
                pouzdanost
            )

            if not self.valjan_kandidat(
                tekst,
                pouzdanost
            ):
                continue

            procitano.append({
                "tekst": tekst,
                "pouzdanost": pouzdanost
            })

        return procitano