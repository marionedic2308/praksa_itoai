import csv

from config import (
    ULAZNI_VIDEO,
    IZLAZNI_VIDEO,
    MODEL_IME,
    CONFIDENCE,
    IMAGE_SIZE,
    TRAJANJE_TESTA_SEKUNDE,
    IZLAZNI_IZVJESTAJ,
)


def spremi_csv(pracenje, putanja=IZLAZNI_IZVJESTAJ):
    """Sprema jedan red za svaki pronađeni tracker ID."""

    stupci = [
        "id",
        "klasa",
        "prvo_videno",
        "zadnje_videno",
        "broj_frameova",
        "stabilan",
        "najveca_pouzdanost",
        "posjecene_zone",
        "putanja",
        "krivi_smjer",
    ]

    with open(putanja, "w", newline="", encoding="utf-8-sig") as datoteka:
        writer = csv.DictWriter(datoteka, fieldnames=stupci)
        writer.writeheader()

        for track_id in sorted(pracenje.vozila):
            vozilo = pracenje.vozila[track_id]
            writer.writerow({
                "id": vozilo.track_id,
                "klasa": vozilo.najcesca_klasa,
                "prvo_videno": vozilo.prvo_videno,
                "zadnje_videno": vozilo.zadnje_videno,
                "broj_frameova": vozilo.broj_frameova,
                "stabilan": "DA" if vozilo.stabilan else "NE",
                "najveca_pouzdanost": f"{vozilo.maksimalna_pouzdanost:.3f}",
                "posjecene_zone": ", ".join(vozilo.posjecene_zone),
                "putanja": " -> ".join(vozilo.povijest_zona),
                "krivi_smjer": "DA" if vozilo.krivi_smjer else "NE",
            })

    return putanja


def ispisi_izvjestaj(pracenje):
    """Ispisuje završni izvještaj praćenja."""

    print("\n==================================================")
    print("       REZULTAT POBOLJŠANOG TESTA 08")
    print("==================================================")
    print("Status         : Uspješno završeno")
    print(f"Ulazni video   : {ULAZNI_VIDEO}")
    print(f"Model          : {MODEL_IME}")
    print("Tracker        : ByteTrack")
    print(f"Confidence     : {CONFIDENCE}")
    print(f"Image size     : {IMAGE_SIZE}")
    print(f"Trajanje testa : {TRAJANJE_TESTA_SEKUNDE} sekundi")
    print("--------------------------------------------------")
    print(f"Detekcija ukupno          : {pracenje.ukupno_detekcija}")
    print(f"Broj različitih ID-eva    : {len(pracenje.vozila)}")
    print(f"Stabilnih ID-eva          : {sum(v.stabilan for v in pracenje.vozila.values())}")
    print(f"Vozila krivim smjerom     : {sum(v.krivi_smjer for v in pracenje.vozila.values())}")
    print("--------------------------------------------------")
    print("Broj ulazaka u pojedine zone:")

    for zona, broj in pracenje.broj_ulazaka_u_zone.items():
        print(f"{zona:<6}: {broj}")

    print("\n--------------------------------------------------")
    print("POVIJEST ZONA PO ID-u")
    print("--------------------------------------------------")

    if not pracenje.vozila:
        print("Nije pronađeno nijedno vozilo.")
    else:
        for track_id in sorted(pracenje.vozila):
            vozilo = pracenje.vozila[track_id]

            print(
                f"ID {track_id:<4} | "
                f"klasa: {vozilo.najcesca_klasa:<15} | "
                f"frameova: {vozilo.broj_frameova:<4} | "
                f"stabilan: {'DA' if vozilo.stabilan else 'NE':<2} | "
                f"max conf: {vozilo.maksimalna_pouzdanost:.2f} | "
                f"{' -> '.join(vozilo.povijest_zona)}"
            )

    csv_putanja = spremi_csv(pracenje)
    print("--------------------------------------------------")
    print(f"Video          : {IZLAZNI_VIDEO}")
    print(f"CSV izvještaj  : {csv_putanja}")
    print("==================================================")
