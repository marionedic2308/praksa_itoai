from collections import Counter, defaultdict
from difflib import SequenceMatcher


class EvidencijaRegistracija:
    """
    Evidencija OCR rezultata povezanih s ByteTrack ID-em vozila.

    Za svako praceno vozilo cuvaju se OCR kandidati dobiveni
    kroz vise frameova.

    Konacni rezultat ne temelji se samo na jednom OCR citanju.
    Kandidati se usporeduju prema:
    - broju pojavljivanja
    - OCR pouzdanosti
    - medusobnoj slicnosti tekstualnih rezultata

    Time se pokusava dobiti jedna najvjerojatnija registracija
    za cijeli prolazak vozila.
    """

    def __init__(self):

        # OCR rezultati po ID-u vozila.
        self.povijest = defaultdict(
            list
        )

        # Broj frameova u kojima je za vozilo
        # pronadena registarska plocica.
        self.broj_detekcija_plocice = defaultdict(
            int
        )

        # Broj frameova u kojima je OCR dao
        # barem jedan valjani rezultat.
        self.broj_uspjesnih_ocr = defaultdict(
            int
        )

    def oznaci_plocicu(
        self,
        track_id
    ):
        """
        Biljezi da je za vozilo u trenutnom frameu
        pronadena registarska plocica.
        """

        self.broj_detekcija_plocice[
            track_id
        ] += 1

    def dodaj_kandidat(
        self,
        track_id,
        tekst,
        pouzdanost,
        broj_framea
    ):
        """
        Dodaje jedan OCR rezultat u povijest vozila.
        """

        if not tekst:
            return

        self.povijest[
            track_id
        ].append({
            "tekst": tekst,
            "pouzdanost": float(
                pouzdanost
            ),
            "frame": int(
                broj_framea
            )
        })

    def oznaci_uspjesan_ocr(
        self,
        track_id
    ):
        """
        Biljezi frame u kojem je OCR dao
        barem jedan valjani kandidat.
        """

        self.broj_uspjesnih_ocr[
            track_id
        ] += 1

    def _slicnost(
        self,
        tekst_a,
        tekst_b
    ):
        """
        Vraca slicnost dvaju OCR rezultata
        u rasponu 0.0 - 1.0.
        """

        return SequenceMatcher(
            None,
            tekst_a,
            tekst_b
        ).ratio()

    def najbolji_rezultat(
        self,
        track_id
    ):
        """
        Odreduje najbolju registraciju za vozilo.

        Tocno ponavljanje istog OCR rezultata ima najveci
        znacaj. Dodatno se uzima u obzir prosjecna OCR
        pouzdanost i podrska slicnih kandidata.

        Primjer:

        E45J679
        E45J679
        E4SJ679
        E45J67
        E45J679

        treba dati prednost kandidatu E45J679.
        """

        zapisi = self.povijest.get(
            track_id,
            []
        )

        if not zapisi:
            return None

        tekstovi = [
            zapis["tekst"]
            for zapis in zapisi
        ]

        brojac = Counter(
            tekstovi
        )

        confidence_po_tekstu = defaultdict(
            list
        )

        for zapis in zapisi:

            confidence_po_tekstu[
                zapis["tekst"]
            ].append(
                zapis["pouzdanost"]
            )

        kandidati = []

        for tekst, broj in brojac.items():

            confidence_vrijednosti = (
                confidence_po_tekstu[
                    tekst
                ]
            )

            prosjecni_confidence = (
                sum(confidence_vrijednosti)
                / len(confidence_vrijednosti)
            )

            maksimalni_confidence = max(
                confidence_vrijednosti
            )

            # Podrska slicnih OCR rezultata.
            #
            # Ako drugi OCR kandidat nije identican,
            # ali je vrlo slican ovom tekstu, daje mu
            # dodatnu podrsku.
            slicna_podrska = 0.0

            for drugi_tekst in tekstovi:

                if drugi_tekst == tekst:
                    continue

                slicnost = self._slicnost(
                    tekst,
                    drugi_tekst
                )

                if slicnost >= 0.70:
                    slicna_podrska += (
                        slicnost
                    )

            # Glavni kriterij je broj tocnih ponavljanja.
            #
            # Confidence i slicni rezultati koriste se
            # kao dodatna podrska.
            ocjena = (
                broj * 3.0
                + prosjecni_confidence
                + slicna_podrska * 0.25
            )

            kandidati.append({
                "tekst": tekst,
                "broj_potvrda": broj,
                "prosjecna_pouzdanost":
                    prosjecni_confidence,
                "maksimalna_pouzdanost":
                    maksimalni_confidence,
                "slicna_podrska":
                    slicna_podrska,
                "ocjena":
                    ocjena
            })

        kandidati.sort(
            key=lambda kandidat: (
                kandidat["ocjena"],
                kandidat["broj_potvrda"],
                kandidat[
                    "prosjecna_pouzdanost"
                ]
            ),
            reverse=True
        )

        najbolji = kandidati[0]

        najbolji[
            "ukupno_ocr_opazanja"
        ] = len(
            zapisi
        )

        najbolji[
            "detekcija_plocice"
        ] = self.broj_detekcija_plocice.get(
            track_id,
            0
        )

        najbolji[
            "uspjesnih_ocr_frameova"
        ] = self.broj_uspjesnih_ocr.get(
            track_id,
            0
        )

        return najbolji

    def odredi_status(
        self,
        track_id
    ):
        """
        Odreduje koliko je konacni OCR rezultat
        potkrijepljen rezultatima kroz vise frameova.
        """

        rezultat = self.najbolji_rezultat(
            track_id
        )

        if rezultat is None:
            return "OCR NIJE USPJESAN"

        broj = rezultat[
            "broj_potvrda"
        ]

        prosjecni_confidence = rezultat[
            "prosjecna_pouzdanost"
        ]

        # Vise jednakih OCR citanja.
        if (
            broj >= 3
            and prosjecni_confidence >= 0.40
        ):
            return "POTVRDENO"

        # Dva jednaka citanja vec predstavljaju
        # dobru vremensku potvrdu.
        if (
            broj >= 2
            and prosjecni_confidence >= 0.30
        ):
            return "STABILNO"

        # Jedno citanje moze ostati kandidat,
        # posebno ako ima visoku OCR pouzdanost.
        return "KANDIDAT"

    def ukloni_id(
        self,
        track_id
    ):
        """
        Uklanja podatke zavrsenog vozila iz
        aktivne memorije.
        """

        self.povijest.pop(
            track_id,
            None
        )

        self.broj_detekcija_plocice.pop(
            track_id,
            None
        )

        self.broj_uspjesnih_ocr.pop(
            track_id,
            None
        )