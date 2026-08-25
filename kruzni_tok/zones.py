from config import (
    BOJE,
    KRUZNI_TOK_CENTAR,
    KRUZNI_TOK_UNUTARNJI_POLUPRECNIK,
    KRUZNI_TOK_VANJSKI_POLUPRECNIK,
    REGIJE,
)

# Ispravan smjer vožnje gledano iz zraka je suprotno od kazaljke na satu.
CIKLUS_REGIJA = ["R1", "R4", "R3", "R2"]


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

    x, y = tocka
    cx, cy = KRUZNI_TOK_CENTAR
    udaljenost_na_kvadrat = (x - cx) ** 2 + (y - cy) ** 2

    unutarnji = KRUZNI_TOK_UNUTARNJI_POLUPRECNIK ** 2
    vanjski = KRUZNI_TOK_VANJSKI_POLUPRECNIK ** 2

    if unutarnji <= udaljenost_na_kvadrat <= vanjski:
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


def status_prijelaza(trenutna, nova):
    """
    Vraca smjer prijelaza izmedu dvije regije u kružnom toku:
    "naprijed"  - ispravan smjer (R1->R4->R3->R2->R1)
    "natrag"    - krivi smjer (voznja unazad)
    "preskok"   - preskocena regija (ne racuna se kao krivi smjer)
    "ostalo"    - ulazak/izlazak izvan ciklusa (neutralno)
    """

    if trenutna in CIKLUS_REGIJA and nova in CIKLUS_REGIJA:
        i = CIKLUS_REGIJA.index(trenutna)
        j = CIKLUS_REGIJA.index(nova)

        if j == (i + 1) % 4:
            return "naprijed"
        if j == (i - 1) % 4:
            return "natrag"
        return "preskok"

    return "ostalo"
