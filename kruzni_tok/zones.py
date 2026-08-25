from config import REGIJE, BOJE


def tocka_u_pravokutniku(tocka, pravokutnik):
    """True ako se točka nalazi unutar pravokutnika."""

    x, y = tocka
    (x1, y1), (x2, y2) = pravokutnik

    return x1 <= x <= x2 and y1 <= y <= y2


def odredi_zonu(tocka):
    """
    Vraca zonu u kojoj je središte objekta.
    Regije 1-4 imaju prednost jer leže unutar Regije 5.
    """

    for broj_regije in range(1, 5):
        if tocka_u_pravokutniku(tocka, REGIJE[f"Regija {broj_regije}"]):
            return f"R{broj_regije}"

    if tocka_u_pravokutniku(tocka, REGIJE["Regija 5 - KRUZNI TOK"]):
        return "R5"

    return "IZVAN"


def boja_zone(zona):
    """Boja kojom se iscrtava zadana zona."""

    mapa = {
        "R1": BOJE["Regija 1"],
        "R2": BOJE["Regija 2"],
        "R3": BOJE["Regija 3"],
        "R4": BOJE["Regija 4"],
        "R5": BOJE["Regija 5 - KRUZNI TOK"],
        "IZVAN": (255, 255, 255),
    }

    return mapa.get(zona, (255, 255, 255))


def formatiraj_vrijeme_videa(sekunde):
    """Pretvara sekunde u format MM:SS.mmm."""

    minute = int(sekunde // 60)
    ostatak = sekunde % 60

    return f"{minute:02d}:{ostatak:06.3f}"
