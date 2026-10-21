import os
import re
import sqlite3
from pathlib import Path

from core.sessions import DATABASE_PATH


def run_ocr_for_saved_photos():
    """Obradi spremljene fotografije plocica i spremi najbolje OCR rezultate."""
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

    from paddleocr import PaddleOCR
    from core.ocr_database import initialize_ocr_database, save_ocr_result

    project_root = Path(__file__).resolve().parent.parent
    sessions_root = project_root / "data" / "sessions"

    initialize_ocr_database()

    # Obrada samo fotografija koje su vec izdvojene kao plocice.
    pattern = re.compile(r"^event_(\d+)_.*_plocica\.jpg$", re.IGNORECASE)
    groups = {}

    for folder in sessions_root.iterdir():
        if not folder.is_dir():
            continue
        plate_folder = folder / "ocr" / "plocice"
        if not plate_folder.is_dir():
            continue
        for photo in plate_folder.glob("*.jpg"):
            match = pattern.match(photo.name)
            if match:
                event_id = int(match.group(1))
                groups.setdefault(event_id, []).append(photo)

    if not groups:
        return {
            "photos": 0, "saved": 0, "no_text": 0,
            "existing": 0, "errors": 0
        }

    # Ne prepisuj postojece OCR rezultate.
    with sqlite3.connect(DATABASE_PATH) as conn:
        existing = {
            row[0] for row in conn.execute(
                "SELECT event_id FROM ocr_results"
            ).fetchall()
        }
        valid_events = {
            row[0] for row in conn.execute(
                "SELECT id FROM vehicle_events"
            ).fetchall()
        }

    ocr = PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False
    )

    stats = {
        "photos": sum(len(v) for v in groups.values()),
        "saved": 0, "no_text": 0, "existing": 0, "errors": 0
    }

    for event_id, photos in sorted(groups.items()):
        if event_id in existing:
            stats["existing"] += 1
            continue
        if event_id not in valid_events:
            stats["errors"] += 1
            continue

        best = None

        for photo in photos:
            try:
                results = ocr.predict(str(photo))
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
                        value = str(raw).strip().upper()
                        value = re.sub(r"\s+", "", value)
                        alnum_count = len(re.sub(r"[^A-Z0-9]", "", value))

                        # Odbaci ocigledno prekratke/preduge OCR fragmente.
                        if not 4 <= alnum_count <= 10:
                            continue

                        confidence = float(score)
                        if not 0 <= confidence <= 1:
                            continue

                        candidate = (confidence, value)
                        if best is None or candidate[0] > best[0]:
                            best = candidate
            except Exception:
                stats["errors"] += 1

        if best is None:
            stats["no_text"] += 1
            continue

        try:
            save_ocr_result(event_id, best[1], best[0])
            stats["saved"] += 1
        except sqlite3.IntegrityError:
            # Ako je rezultat u medjuvremenu spremljen, ne prepisuj ga.
            stats["existing"] += 1
        except Exception:
            stats["errors"] += 1

    return stats
