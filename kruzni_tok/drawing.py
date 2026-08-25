import cv2

from config import REGIJE, BOJE
from zones import boja_zone


def nacrtaj_regije(frame):
    """Iscrtava okvire svih regija na frame."""

    # Velika Regija 5 (kružni tok).
    naziv_r5 = "Regija 5 - KRUZNI TOK"
    p5 = REGIJE[naziv_r5]
    cv2.rectangle(frame, p5[0], p5[1], BOJE[naziv_r5], 3)
    cv2.putText(
        frame,
        "R5 - KRUZNI TOK",
        (p5[0][0], max(25, p5[0][1] - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        BOJE[naziv_r5],
        2,
    )

    # Regije 1-4.
    for broj in range(1, 5):
        naziv = f"Regija {broj}"
        p = REGIJE[naziv]
        cv2.rectangle(frame, p[0], p[1], BOJE[naziv], 3)
        cv2.putText(
            frame,
            f"R{broj}",
            (p[0][0], max(25, p[0][1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            BOJE[naziv],
            2,
        )


def nacrtaj_objekt(frame, box, track_id, naziv_klase, confidence, zona, tocka, krivi_smjer=False):
    """Iscrtava bounding box, središnju točku i oznaku za jedan objekt.
    Krivi smjer se označava crvenom bojom i upozorenjem."""

    x1, y1, x2, y2 = box
    boja = (0, 0, 255) if krivi_smjer else boja_zone(zona)

    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), boja, 2)
    cv2.circle(frame, tocka, 6, boja, -1)

    tekst = f"ID {track_id} | {naziv_klase} | {confidence:.2f} | {zona}"
    if krivi_smjer:
        tekst += " | KRIVI SMJER!"

    cv2.putText(
        frame,
        tekst,
        (int(x1), max(25, int(y1) - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        boja,
        2,
    )


def nacrtaj_hud(frame, frame_broj, maksimalno_frameova, vrijeme_videa):
    """Iscrtava gornji informativni panel (HUD)."""

    cv2.rectangle(frame, (5, 5), (445, 95), (0, 0, 0), -1)
    cv2.putText(
        frame,
        "TEST 08 - POBOLJSANA DETEKCIJA",
        (15, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        frame,
        f"Frame: {frame_broj}/{maksimalno_frameova}",
        (15, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        frame,
        f"Vrijeme: {vrijeme_videa}",
        (15, 85),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )
