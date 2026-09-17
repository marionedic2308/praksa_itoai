# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# Modul za pracenje vozila primjenom ByteTrack algoritma
# ============================================================

from collections import Counter

from ultralytics import YOLO


class PracenjeVozila:
    """
    Modul za detekciju i pracenje vozila na stvarnom
    RTSP videoizvoru.

    Koristi:
    - YOLO11 za detekciju vozila
    - ByteTrack za dodjelu i odrzavanje ID oznaka

    Za svaki ID pamte se i detektirane klase kroz vrijeme
    kako bi se kasnije mogla odrediti stabilnija klasa vozila.
    """

    # COCO klase:
    # 2 = car
    # 5 = bus
    # 7 = truck
    KLASE_VOZILA = [2, 5, 7]

    def __init__(
        self,
        model_path="yolo11n.pt",
        confidence=0.25,
        image_size=640,
        tracker="bytetrack.yaml"
    ):

        self.model_path = model_path
        self.confidence = confidence
        self.image_size = image_size
        self.tracker = tracker

        # Povijest klasifikacije za svaki track ID.
        self.povijest_klasa = {}

        print(
            f"[INFO] Ucitavanje YOLO modela za tracking: "
            f"{self.model_path}"
        )

        self.model = YOLO(self.model_path)

        print("[OK] YOLO model za tracking uspjesno ucitan.")
        print(f"[INFO] Tracker: {self.tracker}")

    def prati(self, frame):
        """
        Izvodi YOLO detekciju i ByteTrack pracenje
        na jednom frameu.

        persist=True omogucuje zadrzavanje informacija
        trackera izmedu uzastopnih frameova.
        """

        rezultati = self.model.track(
            source=frame,
            persist=True,
            classes=self.KLASE_VOZILA,
            conf=self.confidence,
            imgsz=self.image_size,
            tracker=self.tracker,
            verbose=False
        )

        if not rezultati:
            return None

        rezultat = rezultati[0]

        self._azuriraj_klase(rezultat)

        return rezultat

    def _azuriraj_klase(self, rezultat):
        """
        Pamti klase koje je YOLO dodijelio svakom track ID-u.

        Ovo je vazno kod stvarnog videoizvora jer udaljeno
        vozilo moze privremeno biti pogresno klasificirano.
        """

        if rezultat.boxes is None:
            return

        if rezultat.boxes.id is None:
            return

        ids = rezultat.boxes.id.int().cpu().tolist()
        klase = rezultat.boxes.cls.int().cpu().tolist()

        for track_id, klasa_id in zip(ids, klase):

            if track_id not in self.povijest_klasa:
                self.povijest_klasa[track_id] = []

            self.povijest_klasa[track_id].append(klasa_id)

    def stabilna_klasa(self, track_id):
        """
        Vraca najcesce detektiranu klasu za zadani ID.

        Time pojedinacna pogresna klasifikacija ne mora
        odrediti konacnu klasu vozila.
        """

        klase = self.povijest_klasa.get(
            track_id,
            []
        )

        if not klase:
            return None

        brojac = Counter(klase)

        return brojac.most_common(1)[0][0]

    @staticmethod
    def naziv_klase(klasa_id):
        """
        Pretvara COCO ID klase u naziv koji koristimo
        u projektu.
        """

        nazivi = {
            2: "car",
            5: "bus",
            7: "truck"
        }

        return nazivi.get(
            klasa_id,
            "unknown"
        )