
from pathlib import Path

import cv2
from ultralytics import YOLO


# ============================================================
# RIVA - YOLO DETEKCIJA VOZILA
# ============================================================
# Modul koristi model YOLO11n.
#
# Zadužen je za:
# - prepoznavanje vozila na pojedinačnom kadru
# - crtanje okvira oko prepoznatih vozila
# - prikaz vrste vozila i pouzdanosti detekcije
# - vraćanje rezultata drugim modulima aplikacije
#
# Praćenje vozila, brojanje i OCR dodajemo kasnije.
# ============================================================


class VehicleDetector:
    """Detektor vozila temeljen na modelu YOLO11n."""

    # COCO kategorije koje predstavljaju cestovna vozila.
    VEHICLE_CLASSES = {
        2: "Automobil",
        3: "Motocikl",
        5: "Autobus",
        7: "Kamion"
    }

    def __init__(self, model_path=None, confidence=0.35):
        """
        Učitava YOLO model.

        Model se učitava samo jednom, prilikom
        stvaranja objekta detektora.
        """

        self.confidence = confidence

        if model_path is None:
            # Zadana lokacija modela unutar RIVA projekta.
            model_path = (
                Path(__file__).resolve().parent.parent
                / "models"
                / "yolo11n.pt"
            )

        self.model_path = Path(model_path)

        if not self.model_path.is_file():
            raise FileNotFoundError(
                "YOLO model nije pronađen:\n"
                f"{self.model_path}\n\n"
                "Datoteku yolo11n.pt potrebno je "
                "kopirati u mapu RIVA/models."
            )

        self.model = YOLO(str(self.model_path))

    def detect(self, frame):
        """
        Obrađuje jedan video kadar.

        Vraća:
        - kadar s nacrtanim okvirima
        - popis detektiranih vozila

        Ova metoda NE broji jedinstvena vozila.
        """

        if frame is None:
            raise ValueError(
                "Nije dostavljen valjan video kadar."
            )

        # YOLO prepoznaje samo odabrane klase vozila.
        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            classes=list(self.VEHICLE_CLASSES.keys()),
            verbose=False
        )

        annotated_frame = frame.copy()
        detections = []

        for result in results:

            for box in result.boxes:

                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())

                x1, y1, x2, y2 = [
                    int(value)
                    for value in box.xyxy[0].tolist()
                ]

                vehicle_type = self.VEHICLE_CLASSES.get(
                    class_id,
                    "Nepoznato"
                )

                # Spremanje strukturiranih rezultata.
                detections.append({
                    "class_id": class_id,
                    "vehicle_type": vehicle_type,
                    "confidence": round(confidence, 4),
                    "bbox": [x1, y1, x2, y2]
                })

                # Okvir oko detektiranog vozila.
                cv2.rectangle(
                    annotated_frame,
                    (x1, y1),
                    (x2, y2),
                    (93, 217, 208),
                    2
                )

                # Tekst iznad okvira.
                label = (
                    f"{vehicle_type} "
                    f"{confidence:.0%}"
                )

                text_y = max(20, y1 - 8)

                cv2.putText(
                    annotated_frame,
                    label,
                    (x1, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (93, 217, 208),
                    2,
                    cv2.LINE_AA
                )

        return annotated_frame, detections
