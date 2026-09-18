from pathlib import Path

from ultralytics import YOLO


class DetektorPlocica:
    """
    Detekcija registarske plocice unutar prethodno
    detektiranog i pracenog vozila.

    U finalnoj integraciji:
    1. YOLO11 + ByteTrack prati cijelo vozilo.
    2. Iz originalnog framea izdvaja se crop vozila.
    3. Ovaj model unutar cropa vozila trazi plocicu.
    4. Detektirana plocica kasnije se salje OCR modulu.
    5. OCR rezultat povezuje se s ByteTrack ID-em vozila.
    """

    def __init__(
        self,
        confidence=0.20,
        image_size=640
    ):

        trenutna_mapa = Path(
            __file__
        ).resolve().parent

        test10_mapa = (
            trenutna_mapa.parent
        )

        self.model_path = (
            test10_mapa
            / "license-plate-finetune-v1n.pt"
        )

        self.confidence = confidence
        self.image_size = image_size

        if not self.model_path.exists():
            raise FileNotFoundError(
                "Model za detekciju registarskih "
                f"plocica nije pronaden: "
                f"{self.model_path}"
            )

        print(
            "[INFO] Ucitavanje modela za "
            "detekciju registarskih plocica..."
        )

        self.model = YOLO(
            str(self.model_path)
        )

        print(
            "[OK] Model za detekciju registarskih "
            "plocica uspjesno ucitan."
        )

    def detektiraj(
        self,
        crop_vozila
    ):
        """
        Trazi registarsku plocicu unutar cropa vozila.

        Vraca najbolju pronadenu plocicu ili None.
        Bounding box je izrazen u koordinatama cropa vozila.
        """

        if crop_vozila is None:
            return None

        if crop_vozila.size == 0:
            return None

        rezultati = self.model.predict(
            source=crop_vozila,
            conf=self.confidence,
            imgsz=self.image_size,
            verbose=False
        )

        rezultat = rezultati[0]

        if (
            rezultat.boxes is None
            or len(rezultat.boxes) == 0
        ):
            return None

        najbolja_plocica = None
        najbolji_confidence = -1.0

        boxes = (
            rezultat.boxes.xyxy
            .cpu()
            .numpy()
        )

        pouzdanosti = (
            rezultat.boxes.conf
            .cpu()
            .tolist()
        )

        for box, confidence in zip(
            boxes,
            pouzdanosti
        ):

            confidence = float(
                confidence
            )

            if confidence <= najbolji_confidence:
                continue

            x1, y1, x2, y2 = map(
                int,
                box
            )

            najbolji_confidence = confidence

            najbolja_plocica = {
                "bbox": (
                    x1,
                    y1,
                    x2,
                    y2
                ),
                "pouzdanost": confidence
            }

        return najbolja_plocica