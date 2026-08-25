from ultralytics import YOLO

# Učitavanje prethodno istreniranog YOLO modela
model = YOLO("yolo11n.pt")

# Pokretanje detekcije objekata na videozapisu
results = model.predict(
    source="testvideo.mp4",
    save=True,
    project="rezultati",
    name="test_video",
    exist_ok=True
)

# Ispis rezultata u terminal
print("\n========================================")
print("      REZULTAT DETEKCIJE VIDEA")
print("========================================")
print("Status        : Uspješno završeno")
print("Ulazni video  : testvideo.mp4")
print("Model         : yolo11n.pt")
print("Rezultati     : runs/detect/rezultati/test_video")
print("========================================")