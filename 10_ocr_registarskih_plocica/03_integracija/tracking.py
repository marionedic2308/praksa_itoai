from collections import Counter, defaultdict

from ultralytics import YOLO

from config import MODEL_PATH, CONFIDENCE, IMAGE_SIZE


class PracenjePlocica:
    """
    Pracenje registarskih plocica pomocu YOLO modela
    i ByteTrack algoritma.

    Za svaki track ID zasebno se cuvaju:
    - broj frameova u kojima je ID pracen
    - broj OCR pokusaja
    - broj sirovih EasyOCR rezultata
    - broj valjanih OCR kandidata
    - razlozi odbijanja OCR rezultata
    - OCR povijest
    - OCR confidence vrijednosti
    """

    def __init__(self):

        print(
            "[INFO] Ucitavanje modela za pracenje "
            "registarskih plocica..."
        )

        self.model = YOLO(
            MODEL_PATH
        )

        # ====================================================
        # OCR POVIJEST
        # ====================================================

        self.ocr_povijest = defaultdict(
            list
        )

        self.ocr_pouzdanosti = defaultdict(
            lambda: defaultdict(list)
        )

        # ====================================================
        # TRACKING PODACI
        # ====================================================

        self.zadnji_frame = {}

        self.broj_frameova = defaultdict(
            int
        )

        # ====================================================
        # OCR DIJAGNOSTIKA
        # ====================================================

        self.broj_ocr_pokusaja = defaultdict(
            int
        )

        self.broj_sirovih_ocr = defaultdict(
            int
        )

        self.broj_valjanih_ocr = defaultdict(
            int
        )

        self.odbijeni_prazni = defaultdict(
            int
        )

        self.odbijeni_niska_pouzdanost = defaultdict(
            int
        )

        self.odbijeni_prekratki = defaultdict(
            int
        )

        self.odbijeni_predugi = defaultdict(
            int
        )

        print(
            "[OK] Model za pracenje registarskih "
            "plocica uspjesno ucitan."
        )

    def prati(self, frame):
        """
        Izvodi YOLO detekciju i ByteTrack pracenje.
        """

        rezultati = self.model.track(
            source=frame,
            persist=True,
            conf=CONFIDENCE,
            imgsz=IMAGE_SIZE,
            tracker="tracker_plocice.yaml",
            verbose=False
        )

        return rezultati[0]

    def oznaci_vidljiv(
        self,
        track_id,
        broj_framea
    ):
        """
        Biljezi pojavljivanje track ID-a u trenutnom frameu.
        """

        self.zadnji_frame[
            track_id
        ] = broj_framea

        self.broj_frameova[
            track_id
        ] += 1

    def dodaj_ocr_dijagnostiku(
        self,
        track_id,
        rezultat_ocr
    ):
        """
        Biljezi rezultate jednog OCR pokusaja.

        rezultat_ocr je dijagnosticki dictionary
        koji vraca OCRRegistracije.procitaj().
        """

        self.broj_ocr_pokusaja[
            track_id
        ] += 1

        self.broj_sirovih_ocr[
            track_id
        ] += rezultat_ocr.get(
            "broj_sirovih",
            0
        )

        self.broj_valjanih_ocr[
            track_id
        ] += rezultat_ocr.get(
            "broj_valjanih",
            0
        )

        odbijeni = rezultat_ocr.get(
            "odbijeni",
            {}
        )

        self.odbijeni_prazni[
            track_id
        ] += odbijeni.get(
            "prazan",
            0
        )

        self.odbijeni_niska_pouzdanost[
            track_id
        ] += odbijeni.get(
            "niska_pouzdanost",
            0
        )

        self.odbijeni_prekratki[
            track_id
        ] += odbijeni.get(
            "prekratak",
            0
        )

        self.odbijeni_predugi[
            track_id
        ] += odbijeni.get(
            "predug",
            0
        )

    def dodaj_ocr(
        self,
        track_id,
        tekst,
        pouzdanost,
        broj_framea
    ):
        """
        Dodaje valjani OCR kandidat u povijest
        odgovarajuceg track ID-a.
        """

        if not tekst:
            return

        self.ocr_povijest[
            track_id
        ].append(
            tekst
        )

        self.ocr_pouzdanosti[
            track_id
        ][
            tekst
        ].append(
            float(pouzdanost)
        )

        self.zadnji_frame[
            track_id
        ] = broj_framea

    def najbolji_kandidat(
        self,
        track_id
    ):
        """
        Odreduje najbolji OCR kandidat.

        Prvo se uzima kandidat s najvecim brojem
        ponavljanja.

        Ako vise kandidata ima isti broj ponavljanja,
        prednost ima kandidat s vecom prosjecnom
        OCR pouzdanoscu.
        """

        povijest = self.ocr_povijest.get(
            track_id,
            []
        )

        if not povijest:
            return None

        brojac = Counter(
            povijest
        )

        najveci_broj = max(
            brojac.values()
        )

        kandidati = [
            tekst
            for tekst, broj in brojac.items()
            if broj == najveci_broj
        ]

        najbolji_tekst = None
        najbolji_prosjek = -1.0

        for tekst in kandidati:

            vrijednosti = (
                self.ocr_pouzdanosti[
                    track_id
                ][
                    tekst
                ]
            )

            if vrijednosti:

                prosjek = (
                    sum(vrijednosti)
                    / len(vrijednosti)
                )

            else:

                prosjek = 0.0

            if prosjek > najbolji_prosjek:

                najbolji_prosjek = prosjek
                najbolji_tekst = tekst

        return {
            "tekst": najbolji_tekst,
            "broj_potvrda": brojac[
                najbolji_tekst
            ],
            "prosjecna_pouzdanost": najbolji_prosjek,
            "broj_ocr_opazanja": len(
                povijest
            )
        }

    def dohvati_dijagnostiku(
        self,
        track_id
    ):
        """
        Vraca kompletnu dijagnostiku jednog track ID-a.
        """

        return {
            "broj_frameova":
                self.broj_frameova[
                    track_id
                ],

            "broj_ocr_pokusaja":
                self.broj_ocr_pokusaja[
                    track_id
                ],

            "broj_sirovih":
                self.broj_sirovih_ocr[
                    track_id
                ],

            "broj_valjanih":
                self.broj_valjanih_ocr[
                    track_id
                ],

            "niska_pouzdanost":
                self.odbijeni_niska_pouzdanost[
                    track_id
                ],

            "prekratki":
                self.odbijeni_prekratki[
                    track_id
                ],

            "predugi":
                self.odbijeni_predugi[
                    track_id
                ],

            "prazni":
                self.odbijeni_prazni[
                    track_id
                ]
        }

    def neaktivni_id_evi(
        self,
        trenutni_frame,
        prag_frameova=15
    ):
        """
        Vraca track ID-eve koji se vise nisu pojavili
        zadani broj frameova.
        """

        rezultat = []

        for track_id, zadnji in list(
            self.zadnji_frame.items()
        ):

            if (
                trenutni_frame - zadnji
                >= prag_frameova
            ):
                rezultat.append(
                    track_id
                )

        return rezultat

    def ukloni_id(
        self,
        track_id
    ):
        """
        Uklanja zavrseni ID iz aktivne memorije.
        """

        self.ocr_povijest.pop(
            track_id,
            None
        )

        self.ocr_pouzdanosti.pop(
            track_id,
            None
        )

        self.zadnji_frame.pop(
            track_id,
            None
        )

        self.broj_frameova.pop(
            track_id,
            None
        )

        self.broj_ocr_pokusaja.pop(
            track_id,
            None
        )

        self.broj_sirovih_ocr.pop(
            track_id,
            None
        )

        self.broj_valjanih_ocr.pop(
            track_id,
            None
        )

        self.odbijeni_prazni.pop(
            track_id,
            None
        )

        self.odbijeni_niska_pouzdanost.pop(
            track_id,
            None
        )

        self.odbijeni_prekratki.pop(
            track_id,
            None
        )

        self.odbijeni_predugi.pop(
            track_id,
            None
        )