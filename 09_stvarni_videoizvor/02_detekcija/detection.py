# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# Modul za detekciju vozila primjenom YOLO11 modela
# ============================================================

from ultralytics import YOLO


class DetektorVozila:
    """
    Modul za detekciju vozila na pojedinacnim frameovima
    stvarnog RTSP videoizvora.

    Koristi prethodno obuceni YOLO11 model.

    U ovoj fazi detektiraju se samo:
    - car
    - bus
    - truck

    Tracking, brojanje i analiza smjera kretanja
    bit ce dodani u sljedecim fazama Testa 09.
    """

    # COCO klase koje se koriste u projektu:
    # 2 = car
    # 5 = bus
    # 7 = truck
    KLASE_VOZILA = [2, 5, 7]

    def __init__(
        self,
        model_path="yolo11n.pt",
        confidence=0.25,
        image_size=640
    ):
        """
        Inicijalizira YOLO11 model i osnovne parametre
        detekcije.
        """

        self.model_path = model_path
        self.confidence = confidence
        self.image_size = image_size

        print(
            f"[INFO] Ucitavanje YOLO modela: {self.model_path}"
        )

        self.model = YOLO(self.model_path)

        print("[OK] YOLO model uspjesno ucitan.")

    def detektiraj(self, frame):
        """
        Izvodi detekciju vozila na jednom frameu.

        Funkcija vraca Ultralytics rezultat koji se
        kasnije moze koristiti za:
        - bounding box
        - klasu objekta
        - confidence
        - vizualizaciju
        - tracking
        """

        rezultati = self.model.predict(
            source=frame,
            classes=self.KLASE_VOZILA,
            conf=self.confidence,
            imgsz=self.image_size,
            verbose=False
        )

        if not rezultati:
            return None

        return rezultati[0]