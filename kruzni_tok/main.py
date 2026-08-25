import cv2

from config import (
    MODEL,
    CONFIDENCE,
    IMAGE_SIZE,
    TRAJANJE_TESTA_SEKUNDE,
    ULAZNI_VIDEO,
    DEVICE,
    MINIMALNA_SIRINA_OBJEKTA,
    MINIMALNA_VISINA_OBJEKTA,
    PRIKAZ_VIDEA,
    otvori_video,
)
from zones import odredi_zonu, formatiraj_vrijeme_videa
from tracking import Pracenje
from drawing import nacrtaj_regije, nacrtaj_objekt, nacrtaj_hud
from report import ispisi_izvjestaj


def main():
    print("Pokrećem Test 08 – poboljšana detekcija kružnog toka...")

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

        results = MODEL.track(
            frame,
            persist=True,
            conf=CONFIDENCE,
            imgsz=IMAGE_SIZE,
            tracker="bytetrack.yaml",
            device=DEVICE,
            verbose=False,
        )

        annotated = frame.copy()
        boxes = results[0].boxes

        if boxes is not None and boxes.id is not None and len(boxes) > 0:
            ids = boxes.id.cpu().numpy().astype(int)
            klase = boxes.cls.cpu().numpy().astype(int)
            pouzdanosti = boxes.conf.cpu().numpy()
            koordinate = boxes.xyxy.cpu().numpy()

            for box, track_id, cls_id, confidence in zip(
                koordinate, ids, klase, pouzdanosti
            ):
                sirina_objekta = box[2] - box[0]
                visina_objekta = box[3] - box[1]

                if (
                    sirina_objekta < MINIMALNA_SIRINA_OBJEKTA
                    or visina_objekta < MINIMALNA_VISINA_OBJEKTA
                ):
                    pracenje.odbačeno_premalih += 1
                    continue

                tocka = (int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2))
                zona = odredi_zonu(tocka)

                poruka = pracenje.obradi_objekt(
                    track_id, MODEL.names[int(cls_id)], confidence, zona, vrijeme_videa
                )
                if poruka:
                    print(poruka)

                nacrtaj_objekt(
                    annotated,
                    box,
                    track_id,
                    MODEL.names[int(cls_id)],
                    confidence,
                    zona,
                    tocka,
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
