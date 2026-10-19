
from collections import Counter, defaultdict
from pathlib import Path

import cv2
from ultralytics import YOLO


# ============================================================
# RIVA - YOLO11 + BYTE TRACK PRAĆENJE VOZILA
# ============================================================
# Temeljeno na logici završne integracije Testa 10.
#
# Funkcionalnosti:
# - praćenje cijelih vozila
# - dodjeljivanje ByteTrack ID oznaka
# - stabilizacija kategorije kroz više kadrova
# - evidencija trajanja praćenja
# - prepoznavanje neaktivnih ID oznaka
# - uklanjanje neaktivnih zapisa iz memorije
#
# Brojanje prelazaka linija dodajemo u zaseban modul.
# ============================================================


class VehicleTracker:
    """Praćenje vozila pomoću YOLO11 i ByteTracka."""

    VEHICLE_CLASSES = {
        2: "Automobil",
        3: "Motocikl",
        5: "Autobus",
        7: "Kamion"
    }

    def __init__(
        self,
        model_path=None,
        confidence=0.25,
        image_size=640
    ):
        # Zadani model nalazi se unutar RIVA projekta.
        if model_path is None:
            model_path = (
                Path(__file__).resolve().parent.parent
                / "models"
                / "yolo11n.pt"
            )

        self.model_path = Path(model_path)

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"YOLO model nije pronađen: {self.model_path}"
            )

        self.confidence = confidence
        self.image_size = image_size

        # Učitavanje modela.
        self.model = YOLO(str(self.model_path))

        # Povijest kategorija po ID-u vozila.
        self.class_history = defaultdict(list)

        # Posljednji kadar u kojem je ID viđen.
        self.last_seen_frame = {}

        # Broj kadrova u kojima je vozilo praćeno.
        self.frame_counts = defaultdict(int)

        # Interni brojač kadrova.
        self.frame_number = 0

    def track(self, frame):
        """
        Obrađuje kadar i vraća:
        - označeni kadar
        - popis praćenih vozila
        """

        if frame is None:
            raise ValueError(
                "Nije dostavljen valjan video kadar."
            )

        self.frame_number += 1

        results = self.model.track(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=self.confidence,
            imgsz=self.image_size,
            classes=list(self.VEHICLE_CLASSES.keys()),
            verbose=False
        )

        annotated_frame = frame.copy()
        tracked_vehicles = []

        for result in results:

            boxes = result.boxes

            if boxes is None or boxes.id is None:
                continue

            for box in boxes:

                track_id = int(box.id[0].item())
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

                # Pamćenje kategorije kroz kadrove.
                self.class_history[track_id].append(
                    vehicle_type
                )

                # Evidencija praćenja.
                self.last_seen_frame[track_id] = (
                    self.frame_number
                )
                self.frame_counts[track_id] += 1

                # Najčešća kategorija za ovaj ID.
                stable_type = self.get_stable_type(
                    track_id
                )

                tracked_vehicles.append({
                    "track_id": track_id,
                    "class_id": class_id,
                    "vehicle_type": vehicle_type,
                    "stable_type": stable_type,
                    "confidence": round(confidence, 4),
                    "bbox": [x1, y1, x2, y2],
                    "frames_tracked": self.frame_counts[
                        track_id
                    ]
                })

                # Okvir vozila.
                cv2.rectangle(
                    annotated_frame,
                    (x1, y1),
                    (x2, y2),
                    (93, 217, 208),
                    2
                )

                # Prikaz stabilizirane kategorije.
                label = (
                    f"ID {track_id} | "
                    f"{stable_type} "
                    f"{confidence:.0%}"
                )

                cv2.putText(
                    annotated_frame,
                    label,
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (93, 217, 208),
                    2,
                    cv2.LINE_AA
                )

        return annotated_frame, tracked_vehicles

    def get_stable_type(self, track_id):
        """Vraća najčešću kategoriju za zadani ID."""

        history = self.class_history.get(
            track_id,
            []
        )

        if not history:
            return "Nepoznato"

        return Counter(history).most_common(1)[0][0]

    def get_frame_count(self, track_id):
        """Vraća broj kadrova praćenja."""

        return self.frame_counts.get(
            track_id,
            0
        )

    def get_inactive_ids(self, threshold_frames=30):
        """Vraća ID-ove nevidljive zadani broj kadrova."""

        inactive = []

        for track_id, last_frame in list(
            self.last_seen_frame.items()
        ):
            if (
                self.frame_number - last_frame
                >= threshold_frames
            ):
                inactive.append(track_id)

        return inactive

    def remove_id(self, track_id):
        """Uklanja završeni ID iz aktivne memorije."""

        self.class_history.pop(track_id, None)
        self.last_seen_frame.pop(track_id, None)
        self.frame_counts.pop(track_id, None)
