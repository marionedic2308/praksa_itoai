import cv2
from pathlib import Path

from camera import Kamera
from config import RTSP_URL
from detection import DetektorPlocica


MAPA = Path("rezultati") / "cropovi_test"
MAPA.mkdir(parents=True, exist_ok=True)

MAX_CROPOVA = 20


def main():

    print("=" * 60)
    print("TEST CROPOVA REGISTARSKIH PLOCICA")
    print("=" * 60)

    kamera = Kamera(RTSP_URL)
    detektor = DetektorPlocica()

    kamera.otvori()

    broj_cropa = 0
    broj_framea = 0

    try:

        while True:

            uspjeh, frame = kamera.procitaj_frame()

            if not uspjeh or frame is None:
                continue

            broj_framea += 1

            rezultat = detektor.detektiraj(frame)

            if rezultat is not None:

                x1, y1, x2, y2 = rezultat["bbox"]
                confidence = rezultat["pouzdanost"]

                visina, sirina = frame.shape[:2]

                # Mali dodatni rub oko plocice.
                box_sirina = x2 - x1
                box_visina = y2 - y1

                dodatak_x = int(box_sirina * 0.10)
                dodatak_y = int(box_visina * 0.15)

                x1_crop = max(0, x1 - dodatak_x)
                y1_crop = max(0, y1 - dodatak_y)

                x2_crop = min(
                    sirina,
                    x2 + dodatak_x
                )

                y2_crop = min(
                    visina,
                    y2 + dodatak_y
                )

                crop = frame[
                    y1_crop:y2_crop,
                    x1_crop:x2_crop
                ].copy()

                if crop.size > 0:

                    broj_cropa += 1

                    naziv = (
                        MAPA
                        / f"crop_{broj_cropa:03d}"
                          f"_conf_{confidence:.2f}.jpg"
                    )

                    cv2.imwrite(
                        str(naziv),
                        crop
                    )

                    print(
                        f"[CROP {broj_cropa:02d}] "
                        f"frame={broj_framea} | "
                        f"velicina="
                        f"{crop.shape[1]}x{crop.shape[0]} | "
                        f"conf={confidence:.2f}"
                    )

            prikaz = frame.copy()

            visina, sirina = prikaz.shape[:2]

            faktor = min(
                1600 / sirina,
                900 / visina,
                1.0
            )

            if faktor < 1.0:

                prikaz = cv2.resize(
                    prikaz,
                    (
                        int(sirina * faktor),
                        int(visina * faktor)
                    ),
                    interpolation=cv2.INTER_AREA
                )

            cv2.imshow(
                "TEST CROPOVA - Q za izlaz",
                prikaz
            )

            if (
                cv2.waitKey(1) & 0xFF
                == ord("q")
            ):
                break

            if broj_cropa >= MAX_CROPOVA:
                print(
                    "[OK] Spremljeno 20 cropova."
                )
                break

    finally:

        kamera.zatvori()
        cv2.destroyAllWindows()

        print()
        print(
            f"[OK] Ukupno spremljeno: "
            f"{broj_cropa}"
        )

        print(
            f"[OK] Mapa: "
            f"{MAPA.resolve()}"
        )


if __name__ == "__main__":
    main()