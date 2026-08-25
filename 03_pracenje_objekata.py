from ultralytics import YOLO

# Učitavanje prethodno istreniranog YOLO modela
model = YOLO("yolo11n.pt")

# Pokretanje praćenja objekata na prometnom videozapisu
results = model.track(
    source="test03.mp4",
    save=True,
    project="rezultati",
    name="pracenje_objekata",
    exist_ok=True,
    persist=True
)

# Ispis rezultata u terminal
print("\n========================================")
print("      REZULTAT PRAĆENJA OBJEKATA")
print("========================================")
print("Status        : Uspješno završeno")
print("Ulazni video  : test03.mp4")
print("Model         : yolo11n.pt")
print("Metoda        : YOLO praćenje objekata")
print("Rezultati     : runs/detect/rezultati/pracenje_objekata")
print("========================================")