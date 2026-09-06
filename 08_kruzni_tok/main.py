import sys

import cv2

from config import (
    CONFIDENCE,
    IMAGE_SIZE,
    TRAJANJE_TESTA_SEKUNDE,
    ULAZNI_VIDEO,
    DEVICE,
    TRACKER,
    PRACENE_KLASE,
    PRIKAZ_VIDEA,
    ucitaj_model,
    otvori_video,
)
from zones import odredi_zonu, formatiraj_vrijeme_videa
from tracking import Pracenje
from drawing import nacrtaj_regije, nacrtaj_objekt, nacrtaj_hud
from report import ispisi_izvjestaj


def main():
    # Omogućava ispravan ispis č, ć, ž, š i đ u Windows terminalu.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("Pokrećem Test 08 – poboljšana detekcija kružnog toka...")
    print(f"Detekcija se vrti na uređaju: {DEVICE.upper()}")

    model = ucitaj_model()
    cap, writer, (sirina, visina, fps, maksimalno_frameova) = otvori_video()

    print(f"Ulazni video       : {ULAZNI_VIDEO}")
    print(f"Rezolucija         : {sirina}x{visina}")
    print(f"FPS                : {fps:.2f}")
    print(f"Frameova za obradu : {maksimalno_frameova}")
    print(f"Confidence         : {CONFIDENCE}")
    print(f"Image size         : {IMAGE_SIZE}")

    pracenje = Pracenje()
    frame_broj = 0

    print("\nPočinjem obradu frameova... (pritisni 'q' za prekid)\n")

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        frame_broj += 1

        if frame_broj > maksimalno_frameova:
            print(f"Završena obrada prvih {TRAJANJE_TESTA_SEKUNDE} sekundi.")
            break

        vrijeme_videa = formatiraj_vrijeme_videa(frame_broj / fps)

        if frame_broj % 100 == 0:
            print(f"Obrađen frame: {frame_broj}/{maksimalno_frameova}")

        results = model.track(
            frame,
            persist=True,
            conf=CONFIDENCE,
            imgsz=IMAGE_SIZE,
            tracker=TRACKER,
            device=DEVICE,
            verbose=False,
        )

        annotated = frame.copy()
        # OBB model vraća rotirane okvire. Za crtanje koristimo njihov
        # obični xyxy pravokutnik, a ID, klasu i confidence zadržavamo.
        detekcije = results[0].obb

        if detekcije is not None and detekcije.id is not None:
            ids = detekcije.id.cpu().numpy().astype(int)
            klase = detekcije.cls.cpu().numpy().astype(int)
            pouzdanosti = detekcije.conf.cpu().numpy()
            koordinate = detekcije.xyxy.cpu().numpy()

            for box, track_id, cls_id, confidence in zip(
                koordinate, ids, klase, pouzdanosti
            ):
                naziv_klase = model.names[int(cls_id)]

                if naziv_klase not in PRACENE_KLASE:
                    continue

                tocka = (int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2))
                zona = odredi_zonu(tocka)

                # Parkirana vozila i ostali ID-evi koji nikada nisu ušli
                # u nadzirane zone ne pripadaju izvještaju kružnog toka.
                if zona == "IZVAN" and track_id not in pracenje.vozila:
                    continue

                poruka = pracenje.obradi_objekt(
                    track_id, naziv_klase, confidence, zona, vrijeme_videa
                )
                if poruka:
                    print(poruka)

                vozilo = pracenje.vozila[track_id]
                nacrtaj_objekt(
                    annotated,
                    box,
                    track_id,
                    vozilo.najcesca_klasa,
                    vozilo.zadnja_zona,
                    vozilo.posjecene_zone,
                    tocka,
                    vozilo.krivi_smjer,
                )

        nacrtaj_regije(annotated)
        nacrtaj_hud(annotated, frame_broj, maksimalno_frameova, vrijeme_videa)

        writer.write(annotated)

        # Realni prikaz videa tijekom obrade (ako je uključen).
        if PRIKAZ_VIDEA:
            cv2.imshow("Kružni tok - realtime", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("Prekinuto od korisnika.")
                break

    cap.release()
    writer.release()
    if PRIKAZ_VIDEA:
        cv2.destroyAllWindows()

    ispisi_izvjestaj(pracenje)


if __name__ == "__main__":
    main()
