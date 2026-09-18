from ultralytics import YOLO

from config import MODEL_PATH, CONFIDENCE, IMAGE_SIZE


class DetektorPlocica:
    """
    Detekcija registarskih plocica pomocu
    YOLO11 modela prilagodenog za registarske plocice.
    """

    def __init__(self):
        print("[INFO] Ucitavanje modela za detekciju registarskih plocica...")

        self.model = YOLO(MODEL_PATH)

        print("[OK] Model za registarske plocice uspjesno ucitan.")


    def detektiraj(self, frame):
        """
        Obraduje jedan frame i vraca YOLO rezultat.
        """

        rezultati = self.model.predict(
            source=frame,
            conf=CONFIDENCE,
            imgsz=IMAGE_SIZE,
            verbose=False
        )

        return rezultati[0]