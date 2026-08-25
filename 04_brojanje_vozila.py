from ultralytics import YOLO
import cv2
import os
from collections import defaultdict

print("Pokrećem Test 04 – brojanje vozila preko linija...")

model = YOLO("yolo11n.pt")
print("YOLO model je učitan.")

ulazni_video = "test03.mp4"
izlazna_mapa = "rezultati/brojanje_vozila"
os.makedirs(izlazna_mapa, exist_ok=True)

izlazni_video = os.path.join(
    izlazna_mapa,
    "test04_brojanje_vozila_final.mp4"
)

cap = cv2.VideoCapture(ulazni_video)

if not cap.isOpened():
    print("GREŠKA: Video nije moguće otvoriti.")
    exit()

sirina = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
visina = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
ukupno_frameova = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

print(f"Ulazni video: {ulazni_video}")
print(f"Rezolucija  : {sirina}x{visina}")
print(f"FPS         : {fps}")
print(f"Frameova    : {ukupno_frameova}")

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(izlazni_video, fourcc, fps, (sirina, visina))

if not writer.isOpened():
    print("GREŠKA: VideoWriter nije moguće otvoriti.")
    exit()

# Linije brojanja po prometnim trakama

linije = {
    "Traka 1": ((338, 135), (393, 136)),
    "Traka 2": ((382, 286), (477, 295)),
    "Traka 3": ((568, 536), (697, 543)),
    "Traka 4": ((878, 569), (1050, 638)),
}


boje = {
    "Traka 1": (0, 255, 0),
    "Traka 2": (0, 255, 255),
    "Traka 3": (0, 0, 255),
    "Traka 4": (255, 0, 0),
}

brojaci = {
    "Traka 1": 0,
    "Traka 2": 0,
    "Traka 3": 0,
    "Traka 4": 0,
}

brojaci_klase = defaultdict(int)
prethodne_pozicije = {}
prebrojani_id = set()


def strana_linije(tocka, linija):
    x, y = tocka
    (x1, y1), (x2, y2) = linija
    return (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)


def vozilo_blizu_linije(tocka, linija, tolerancija=35):
    x, y = tocka
    (x1, y1), (x2, y2) = linija

    return (
        min(x1, x2) - tolerancija <= x <= max(x1, x2) + tolerancija
        and min(y1, y2) - tolerancija <= y <= max(y1, y2) + tolerancija
    )


print("Počinjem obradu frameova...")

frame_broj = 0

while True:
    ret, frame = cap.read()

    if not ret:
        break

    frame_broj += 1

    if frame_broj % 100 == 0:
        print(f"Obrađen frame: {frame_broj}/{ukupno_frameova}")

    results = model.track(
        frame,
        persist=True,
        classes=[2, 5, 7],  # 2=car, 5=bus, 7=truck
        verbose=False
    )

    annotated_frame = results[0].plot()
    boxes = results[0].boxes

    if boxes.id is not None:
        ids = boxes.id.cpu().numpy().astype(int)
        klase = boxes.cls.cpu().numpy().astype(int)
        koordinate = boxes.xyxy.cpu().numpy()

        for box, track_id, cls_id in zip(koordinate, ids, klase):
            x1, y1, x2, y2 = box
            centar = (int((x1 + x2) / 2), int((y1 + y2) / 2))

            if track_id in prethodne_pozicije:
                prethodni_centar = prethodne_pozicije[track_id]

                for naziv_trake, linija in linije.items():
                    prije = strana_linije(prethodni_centar, linija)
                    sada = strana_linije(centar, linija)

                    presao_liniju = prije * sada < 0
                    blizu_linije = vozilo_blizu_linije(centar, linija)

                    if presao_liniju and blizu_linije and track_id not in prebrojani_id:
                        brojaci[naziv_trake] += 1
                        prebrojani_id.add(track_id)

                        naziv_klase = model.names[cls_id]
                        brojaci_klase[naziv_klase] += 1

                        print(
                            f"Prebrojano vozilo ID {track_id} "
                            f"({naziv_klase}) u {naziv_trake}"
                        )

            prethodne_pozicije[track_id] = centar

    # Crtanje linija i brojača
    for indeks, (naziv_trake, linija) in enumerate(linije.items()):
        cv2.line(annotated_frame, linija[0], linija[1], boje[naziv_trake], 4)

        cv2.putText(
            annotated_frame,
            f"{naziv_trake}: {brojaci[naziv_trake]}",
            (10, 30 + 30 * indeks),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            boje[naziv_trake],
            2
        )

    ukupno = sum(brojaci.values())

    cv2.putText(
        annotated_frame,
        f"Ukupno: {ukupno}",
        (10, 160),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2
    )

    writer.write(annotated_frame)

cap.release()
writer.release()

print("\n========================================")
print("      REZULTAT BROJANJA VOZILA")
print("========================================")
print("Status        : Uspješno završeno")
print("Ulazni video  : test03.mp4")
print("Model         : yolo11n.pt")
print("Metoda        : Brojanje prelaskom preko linije")
print("----------------------------------------")

for traka, broj in brojaci.items():
    print(f"{traka:<13}: {broj}")

print("----------------------------------------")
print(f"Ukupno vozila : {sum(brojaci.values())}")

for klasa, broj in brojaci_klase.items():
    print(f"{klasa:<13}: {broj}")

print("----------------------------------------")
print(f"Rezultat      : {izlazni_video}")
print("========================================")