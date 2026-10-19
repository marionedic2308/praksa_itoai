import cv2
from pathlib import Path

from core.vehicle_detector import VehicleDetector


# Odabir videozapisa putem Windows prozora.
from tkinter import Tk, filedialog

root = Tk()
root.withdraw()

video_path = filedialog.askopenfilename(
    title="RIVA - Odaberi video za YOLO test",
    filetypes=[("Videozapisi", "*.mp4 *.avi *.mov *.mkv")]
)

root.destroy()

if not video_path:
    print("Video nije odabran.")
    raise SystemExit

capture = cv2.VideoCapture(video_path)

if not capture.isOpened():
    print("GRESKA: Video nije moguce otvoriti.")
    raise SystemExit

# Uzimamo kadar nakon jedne sekunde.
fps = capture.get(cv2.CAP_PROP_FPS)

if fps > 0:
    capture.set(cv2.CAP_PROP_POS_FRAMES, int(fps * 5))

success, frame = capture.read()
capture.release()

if not success:
    print("GRESKA: Nije moguce procitati kadar.")
    raise SystemExit

# Pokretanje YOLO detekcije.
detector = VehicleDetector(confidence=0.35)

annotated_frame, detections = detector.detect(frame)

# Spremanje slike unutar RIVA projekta.
output_path = Path(__file__).resolve().parent / "data" / "yolo_test.jpg"
output_path.parent.mkdir(parents=True, exist_ok=True)

saved = cv2.imwrite(str(output_path), annotated_frame)

if not saved:
    print("GRESKA: Nije moguce spremiti sliku.")
    raise SystemExit

print("BROJ DETEKCIJA:", len(detections))

for vehicle in detections:
    print(
        vehicle["vehicle_type"],
        "- pouzdanost:",
        vehicle["confidence"]
    )

print("REZULTAT SPREMLJEN:", output_path)