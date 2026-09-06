import cv2

from config import (
    BOJE,
    KRUZNI_TOK_CENTAR,
    KRUZNI_TOK_UNUTARNJI_POLUPRECNIK,
    KRUZNI_TOK_VANJSKI_POLUPRECNIK,
    REGIJE,
)
from zones import boja_zone


def nacrtaj_regije(frame):
    """Iscrtava okvire svih regija na frame."""

    # R5 je prsten ceste oko središnjeg otoka.
    naziv_r5 = "Regija 5 - KRUZNI TOK"
    boja_r5 = BOJE[naziv_r5]
    cv2.circle(
        frame,
        KRUZNI_TOK_CENTAR,
        KRUZNI_TOK_VANJSKI_POLUPRECNIK,
        boja_r5,
        3,
    )
    cv2.circle(
        frame,
        KRUZNI_TOK_CENTAR,
        KRUZNI_TOK_UNUTARNJI_POLUPRECNIK,
        boja_r5,
        3,
    )
    cv2.putText(
        frame,
        "R5 - KRUZNI TOK",
        (
            KRUZNI_TOK_CENTAR[0] - KRUZNI_TOK_VANJSKI_POLUPRECNIK,
            KRUZNI_TOK_CENTAR[1] - KRUZNI_TOK_VANJSKI_POLUPRECNIK - 8,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        boja_r5,
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


def _ispisi_oznaku(frame, redovi, x, y, boja):
    """Iscrtava jedan ili više redova na tamnoj pozadini."""

    font = cv2.FONT_HERSHEY_SIMPLEX
    skala = 0.65
    debljina = 2
    razmak = 7
    rub = 6

    velicine = [
        cv2.getTextSize(red, font, skala, debljina)[0]
        for red in redovi
    ]
    sirina_oznake = max(sirina for sirina, _ in velicine) + 2 * rub
    visina_oznake = sum(visina for _, visina in velicine)
    visina_oznake += razmak * (len(redovi) - 1) + 2 * rub

    visina_framea, sirina_framea = frame.shape[:2]
    x = max(0, min(x, sirina_framea - sirina_oznake))
    y = max(0, min(y, visina_framea - visina_oznake))

    cv2.rectangle(
        frame,
        (x, y),
        (x + sirina_oznake, y + visina_oznake),
        (0, 0, 0),
        -1,
    )

    tekst_y = y + rub
    for red, (_, visina) in zip(redovi, velicine):
        tekst_y += visina
        cv2.putText(
            frame,
            red,
            (x + rub, tekst_y),
            font,
            skala,
            boja,
            debljina,
        )
        tekst_y += razmak


def nacrtaj_objekt(
    frame,
    box,
    track_id,
    naziv_klase,
    trenutna_zona,
    posjecene_zone,
    tocka,
    krivi_smjer=False,
):
    """Crta vozilo i iznad njega klasu te sve posjećene zone."""

    x1, y1, x2, y2 = [int(v) for v in box]
    boja = (0, 0, 255) if krivi_smjer else boja_zone(trenutna_zona)

    cv2.rectangle(frame, (x1, y1), (x2, y2), boja, 3)
    cv2.circle(frame, tocka, 6, boja, -1)

    zone = ", ".join(posjecene_zone)
    prvi_red = f"ID {track_id} | {naziv_klase}"
    drugi_red = f"Zone: {zone}"

    if krivi_smjer:
        prvi_red += " | KRIVI SMJER!"

    # Oznaka iznad boxa; ako je preblizu vrha, ispod boxa.
    if y1 >= 65:
        oznaka_y = y1 - 65
    else:
        oznaka_y = y2 + 5

    _ispisi_oznaku(frame, [prvi_red, drugi_red], x1, oznaka_y, boja)


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
