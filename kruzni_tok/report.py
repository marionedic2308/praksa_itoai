from config import (
    ULAZNI_VIDEO,
    IZLAZNI_VIDEO,
    CONFIDENCE,
    IMAGE_SIZE,
    TRAJANJE_TESTA_SEKUNDE,
)
from zones import formatiraj_vrijeme_videa


def ispisi_izvjestaj(pracenje):
    """Ispisuje završni izvještaj praćenja."""

    print("\n==================================================")
    print("       REZULTAT POBOLJŠANOG TESTA 08")
    print("==================================================")
    print("Status         : Uspješno završeno")
    print(f"Ulazni video   : {ULAZNI_VIDEO}")
    print("Model          : yolo11m.pt")
    print("Tracker        : ByteTrack")
    print(f"Confidence     : {CONFIDENCE}")
    print(f"Image size     : {IMAGE_SIZE}")
    print(f"Trajanje testa : {TRAJANJE_TESTA_SEKUNDE} sekundi")
    print("--------------------------------------------------")
    print(f"Detekcija ukupno          : {pracenje.ukupno_detekcija}")
    print(f"Odbačeno premalih objekata: {pracenje.odbačeno_premalih}")
    print(f"Broj različitih ID-eva    : {len(pracenje.broj_frameova_po_idu)}")
    print("--------------------------------------------------")
    print("Broj ulazaka u pojedine zone:")

    for zona, broj in pracenje.broj_ulazaka_u_zone.items():
        print(f"{zona:<6}: {broj}")

    print("\n--------------------------------------------------")
    print("POVIJEST ZONA PO ID-u")
    print("--------------------------------------------------")

    if not pracenje.povijest_zona:
        print("Nije pronađen nijedan stabilan objekt.")
    else:
        for track_id in sorted(pracenje.povijest_zona):
            povijest = pracenje.povijest_zona[track_id]
            klasa = pracenje.najcesca_klasa(track_id)
            broj_frameova = pracenje.broj_frameova_po_idu[track_id]
            max_conf = pracenje.maksimalna_pouzdanost_po_idu[track_id]

            print(
                f"ID {track_id:<4} | "
                f"klasa: {klasa:<15} | "
                f"frameova: {broj_frameova:<4} | "
                f"max conf: {max_conf:.2f} | "
                f"{' -> '.join(povijest)}"
            )

    print("--------------------------------------------------")
    print(f"Rezultat       : {IZLAZNI_VIDEO}")
    print("==================================================")
