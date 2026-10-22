
import os
import re
import sqlite3
from pathlib import Path

import cv2

from core.sessions import DATABASE_PATH


def run_ocr_for_saved_photos():
    """Naknadna detekcija plocica i OCR spremljenih fotografija vozila."""
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

    from paddleocr import PaddleOCR
    from core.plate_detector import DetektorPlocica
    from core.ocr_database import initialize_ocr_database, save_ocr_result

    root = Path(__file__).resolve().parent.parent
    sessions_root = root / "data" / "sessions"

    stats = {
        "photos": 0,
        "saved": 0,
        "no_text": 0,
        "existing": 0,
        "errors": 0
    }

    initialize_ocr_database()

    if not sessions_root.is_dir():
        return stats

    pattern = re.compile(
        r"^event_(\d+)_kandidat_\d+\.jpg$",
        re.IGNORECASE
    )

    groups = {}

    for session in sorted(sessions_root.iterdir()):
        if not session.is_dir() or not re.fullmatch(
            r"RIVA-\d{6}", session.name
        ):
            continue

        candidate_folder = session / "ocr" / "kandidati"

        if not candidate_folder.is_dir():
            continue

        for photo in sorted(candidate_folder.glob("*.jpg")):
            match = pattern.fullmatch(photo.name)

            if match:
                event_id = int(match.group(1))
                groups.setdefault(event_id, []).append(photo)
                stats["photos"] += 1

    if not groups:
        return stats

    with sqlite3.connect(DATABASE_PATH) as conn:
        existing = {
            row[0]
            for row in conn.execute(
                "SELECT event_id FROM ocr_results"
            )
        }

        valid_events = {
            row[0]
            for row in conn.execute(
                "SELECT id FROM vehicle_events"
            )
        }

    detector = None
    ocr = None

    for event_id, photos in sorted(groups.items()):
        if event_id in existing:
            stats["existing"] += 1
            continue

        if event_id not in valid_events:
            stats["errors"] += 1
            continue

        best = None
        best_plate = None
        best_photo = None
        best_quality = None

        for photo in photos:
            try:
                image = cv2.imread(str(photo))

                if image is None:
                    stats["errors"] += 1
                    continue

                if detector is None:
                    detector = DetektorPlocica()

                detection = detector.detektiraj(image)

                if detection is None:
                    continue

                x1, y1, x2, y2 = detection["bbox"]

                height, width = image.shape[:2]
                x1 = max(0, min(int(x1), width))
                x2 = max(0, min(int(x2), width))
                y1 = max(0, min(int(y1), height))
                y2 = max(0, min(int(y2), height))

                if x2 <= x1 or y2 <= y1:
                    continue

                plate = image[y1:y2, x1:x2].copy()

                if ocr is None:
                    ocr = PaddleOCR(
                        lang="en",
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=False
                    )

                results = ocr.predict(plate)

                for item in results:
                    data = item.json

                    if callable(data):
                        data = data()

                    if not isinstance(data, dict):
                        continue

                    data = data.get("res", data)

                    texts = data.get("rec_texts", [])
                    scores = data.get("rec_scores", [])

                    for raw, score in zip(texts, scores):
                        value = re.sub(
                            r"\s+", "", str(raw).strip().upper()
                        )

                        alnum_count = len(
                            re.sub(r"[^A-Z0-9]", "", value)
                        )

                        if not 4 <= alnum_count <= 10:
                            continue

                        confidence = float(score)

                        if not 0 <= confidence <= 1:
                            continue

                        candidate = (confidence, value)

                        # Quality is evaluated only after OCR succeeds.
                        gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
                        sharpness = float(
                            cv2.Laplacian(gray, cv2.CV_64F).var()
                        )
                        plate_h, plate_w = plate.shape[:2]
                        area = plate_w * plate_h

                        # Larger and sharper plates are preferred when
                        # OCR confidence differs by no more than 2%.
                        quality = (
                            min(area, 50000) / 50000.0
                            + min(sharpness, 1000.0) / 1000.0
                        )

                        choose = best is None
                        if best is not None:
                            difference = confidence - best[0]
                            if difference > 0.02:
                                choose = True
                            elif abs(difference) <= 0.02:
                                choose = quality > best_quality

                        if choose:
                            best = candidate
                            best_plate = plate.copy()
                            best_photo = photo
                            best_quality = quality

            except Exception as exc:
                stats["errors"] += 1
                print(f"[OCR] Greska {photo.name}: {exc}")

        if best is None:
            stats["no_text"] += 1
            continue

        try:
            # Spremi rezultat bez prepisivanja postojecih zapisa.
            save_ocr_result(event_id, best[1], best[0])
            stats["saved"] += 1
            existing.add(event_id)

            # Spremi jednu najbolju izdvojenu plocicu.
            plate_folder = best_photo.parent.parent / "plocice"
            plate_folder.mkdir(parents=True, exist_ok=True)

            plate_path = plate_folder / (
                f"event_{event_id:08d}_najbolja_plocica.jpg"
            )

            if not plate_path.exists():
                success, encoded = cv2.imencode(
                    ".jpg", best_plate
                )

                if success:
                    with open(plate_path, "xb") as file:
                        file.write(encoded.tobytes())
                else:
                    stats["errors"] += 1

        except sqlite3.IntegrityError:
            stats["existing"] += 1

        except Exception as exc:
            stats["errors"] += 1
            print(f"[OCR] Greska spremanja event {event_id}: {exc}")

    return stats
