from collections import Counter, defaultdict

from ultralytics import YOLO


class PracenjeVozila:
    """
    Pracenje vozila pomocu YOLO11 i ByteTrack algoritma.

    U finalnoj integraciji Testa 10 ne prati se registarska
    plocica kao zaseban objekt. Prati se cijelo vozilo, koje
    dobiva stabilniji ByteTrack ID.

    OCR rezultati registarske plocice kasnije ce se povezivati
    upravo s ovim ID-em vozila.
    """

    def __init__(
        self,
        model_path="../yolo11n.pt",
        confidence=0.25,
        image_size=640
    ):

        print(
            "[INFO] Ucitavanje YOLO11 modela "
            "za pracenje vozila..."
        )

        self.model = YOLO(
            model_path
        )

        self.confidence = confidence
        self.image_size = image_size

        # COCO klase:
        # 2 = car
        # 5 = bus
        # 7 = truck
        self.klase_vozila = [
            2,
            5,
            7
        ]

        self.nazivi_klasa = {
            2: "car",
            5: "bus",
            7: "truck"
        }

        # Povijest klasifikacije za svaki ByteTrack ID.
        # Time se smanjuje utjecaj povremenih pogresnih
        # klasifikacija kroz pojedine frameove.
        self.povijest_klasa = defaultdict(
            list
        )

        # Zadnji frame u kojem je pojedini ID bio vidljiv.
        self.zadnji_frame = {}

        # Broj frameova u kojima je vozilo praceno.
        self.broj_frameova = defaultdict(
            int
        )

        print(
            "[OK] YOLO11 model za pracenje "
            "vozila uspjesno ucitan."
        )

    def prati(
        self,
        frame,
        broj_framea
    ):
        """
        Izvodi detekciju vozila i ByteTrack pracenje.
        """

        rezultati = self.model.track(
            source=frame,
            persist=True,
            classes=self.klase_vozila,
            conf=self.confidence,
            imgsz=self.image_size,
            tracker="bytetrack.yaml",
            verbose=False
        )

        rezultat = rezultati[0]

        vozila = []

        if (
            rezultat.boxes is None
            or rezultat.boxes.id is None
        ):
            return vozila

        boxes = (
            rezultat.boxes.xyxy
            .cpu()
            .numpy()
        )

        ids = (
            rezultat.boxes.id
            .int()
            .cpu()
            .tolist()
        )

        klase = (
            rezultat.boxes.cls
            .int()
            .cpu()
            .tolist()
        )

        pouzdanosti = (
            rezultat.boxes.conf
            .cpu()
            .tolist()
        )

        for (
            box,
            track_id,
            class_id,
            confidence
        ) in zip(
            boxes,
            ids,
            klase,
            pouzdanosti
        ):

            track_id = int(
                track_id
            )

            class_id = int(
                class_id
            )

            confidence = float(
                confidence
            )

            x1, y1, x2, y2 = map(
                int,
                box
            )

            naziv_klase = (
                self.nazivi_klasa.get(
                    class_id,
                    str(class_id)
                )
            )

            # Biljezi klasu kroz vise frameova.
            self.povijest_klasa[
                track_id
            ].append(
                naziv_klase
            )

            # Biljezi koliko dugo pratimo vozilo.
            self.zadnji_frame[
                track_id
            ] = broj_framea

            self.broj_frameova[
                track_id
            ] += 1

            stabilna_klasa = (
                self.dohvati_stabilnu_klasu(
                    track_id
                )
            )

            vozila.append({
                "track_id": track_id,
                "bbox": (
                    x1,
                    y1,
                    x2,
                    y2
                ),
                "klasa": naziv_klase,
                "stabilna_klasa": stabilna_klasa,
                "pouzdanost": confidence
            })

        return vozila

    def dohvati_stabilnu_klasu(
        self,
        track_id
    ):
        """
        Vraca najcesce detektiranu klasu vozila
        za zadani ByteTrack ID.
        """

        povijest = self.povijest_klasa.get(
            track_id,
            []
        )

        if not povijest:
            return "unknown"

        brojac = Counter(
            povijest
        )

        return brojac.most_common(
            1
        )[0][0]

    def dohvati_broj_frameova(
        self,
        track_id
    ):
        """
        Vraca broj frameova u kojima je vozilo praceno.
        """

        return self.broj_frameova.get(
            track_id,
            0
        )

    def neaktivni_id_evi(
        self,
        trenutni_frame,
        prag_frameova=30
    ):
        """
        Vraca ID-eve vozila koja vise nisu vidljiva.

        Veci prag nego kod pracenja same plocice koristi se
        kako kratkotrajni gubitak detekcije vozila ne bi
        odmah zavrsio njegov zapis.
        """

        neaktivni = []

        for (
            track_id,
            zadnji_frame
        ) in list(
            self.zadnji_frame.items()
        ):

            if (
                trenutni_frame
                - zadnji_frame
                >= prag_frameova
            ):
                neaktivni.append(
                    track_id
                )

        return neaktivni

    def ukloni_id(
        self,
        track_id
    ):
        """
        Uklanja zavrseni track iz aktivne memorije.
        """

        self.povijest_klasa.pop(
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