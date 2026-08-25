from ultralytics import YOLO

# Učitavanje prethodno istreniranog YOLO modela
model = YOLO("yolo11n.pt")

# Pokretanje detekcije objekata na slici
results = model.predict(
    source="bus.jpg",
    save=True,
    project="rezultati",
    name="prvi_test",
    exist_ok=True
)

# Ispis rezultata u terminal
print("\n========================================")
print("      REZULTAT DETEKCIJE SLIKE")
print("========================================")
print("Status        : Uspješno završeno")
print("Ulazna slika  : bus.jpg")
print("Model         : yolo11n.pt")
print("Rezultati     : runs/detect/rezultati/prvi_test")
print("========================================")