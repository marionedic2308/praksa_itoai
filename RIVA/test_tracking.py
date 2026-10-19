
import cv2
from pathlib import Path
from tkinter import Tk, filedialog

from core.vehicle_tracker import VehicleTracker


# ============================================================
# RIVA - TEST BYTE TRACK PRAĆENJA VOZILA
# ============================================================
# Testira praćenje vozila na lokalnom videozapisu.
# Svakom praćenom vozilu prikazuje ID oznaku.
#
# Tipka Q - prekid testiranja.
# ============================================================


def main():

    # Odabir videozapisa.
    root = Tk()
    root.withdraw()

    video_path = filedialog.askopenfilename(
        title="RIVA - Odaberi video za ByteTrack test",
        filetypes=[
            ("Videozapisi", "*.mp4 *.avi *.mov *.mkv")
        ]
    )

    root.destroy()

    if not video_path:
        print("Videozapis nije odabran.")
        return

    capture = cv2.VideoCapture(video_path)

    if not capture.isOpened():
        print("GRESKA: Video nije moguce otvoriti.")
        return

    # Učitavanje YOLO modela i ByteTracka.
    print("Ucitavanje YOLO + ByteTrack sustava...")

    tracker = VehicleTracker(
        confidence=0.25
    )

    print("Pracenje je pokrenuto.")
    print("Pritisni Q za zaustavljanje.")

    # Popis svih ID oznaka koje su se pojavile.
    seen_ids = set()

    fps = capture.get(cv2.CAP_PROP_FPS)

    if fps <= 0 or fps > 120:
        fps = 25

    delay = max(1, int(1000 / fps))

    try:

        while True:

            success, frame = capture.read()

            if not success:
                print("Dosegnut kraj videozapisa.")
                break

            # Obrada kadra.
            annotated_frame, vehicles = tracker.track(
                frame
            )

            # Pamćenje viđenih ID oznaka.
            for vehicle in vehicles:
                seen_ids.add(
                    vehicle["track_id"]
                )

            # Informativni prikaz.
            cv2.putText(
                annotated_frame,
                f"Trenutno pracenih: {len(vehicles)}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (93, 217, 208),
                2
            )

            cv2.imshow(
                "RIVA - ByteTrack test",
                annotated_frame
            )

            # Pritisni Q za prekid.
            if cv2.waitKey(delay) & 0xFF == ord("q"):
                print("Test prekinut.")
                break

    finally:
        capture.release()
        cv2.destroyAllWindows()

    print()
    print("TEST ZAVRSEN")
    print("Razlicitih ID oznaka:", len(seen_ids))
    print("NAPOMENA: Broj ID oznaka nije broj vozila koja su prosla.")


if __name__ == "__main__":
    main()
