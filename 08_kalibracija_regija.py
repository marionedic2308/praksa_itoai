import cv2
import os


print("Pokrećem Test 08 – kalibracija regija kružnog toka...")


# =========================================================
# OSNOVNE POSTAVKE
# =========================================================

ulazni_video = "test08.mp4"

izlazna_mapa = "rezultati"
os.makedirs(izlazna_mapa, exist_ok=True)

izlazna_slika = os.path.join(
    izlazna_mapa,
    "test08_kalibracija_regija.jpg"
)


# =========================================================
# NAZIVI I BOJE REGIJA
# =========================================================
# Regije 1–4 predstavljaju pojedine krakove kružnog toka.
# Regija 5 pokriva cijeli kružni tok.

nazivi_regija = [
    "Regija 1",
    "Regija 2",
    "Regija 3",
    "Regija 4",
    "Regija 5 - KRUZNI TOK",
]

# Boje su zadane u BGR formatu koji koristi OpenCV.
boje = {
    "Regija 1": (0, 0, 255),              # crvena
    "Regija 2": (0, 255, 255),            # žuta
    "Regija 3": (255, 0, 0),              # plava
    "Regija 4": (255, 0, 255),            # ljubičasta
    "Regija 5 - KRUZNI TOK": (0, 255, 0), # zelena
}


# =========================================================
# UČITAVANJE PRVOG FRAMEA
# =========================================================

cap = cv2.VideoCapture(ulazni_video)

if not cap.isOpened():
    print(f"GREŠKA: Video '{ulazni_video}' nije moguće otvoriti.")
    raise SystemExit

ret, originalni_frame = cap.read()
cap.release()

if not ret:
    print("GREŠKA: Prvi frame nije moguće učitati.")
    raise SystemExit

frame = originalni_frame.copy()


# =========================================================
# PODACI ZA CRTANJE
# =========================================================

regije = {
     "Regija 1": ((821, 187), (991, 366)),
    "Regija 2": ((1115, 421), (1365, 586)),
    "Regija 3": ((848, 693), (991, 902)),
    "Regija 4": ((540, 463), (796, 584)),
    "Regija 5 - KRUZNI TOK": ((474, 169), (1400, 962)),
}



trenutni_indeks = 0
pocetna_tocka = None
trenutna_tocka = None
crtanje_u_tijeku = False


# =========================================================
# POMOĆNE FUNKCIJE
# =========================================================

def normaliziraj_pravokutnik(tocka_1, tocka_2):
    """
    Vraća gornji lijevi i donji desni kut pravokutnika,
    bez obzira na smjer povlačenja miša.
    """
    x1, y1 = tocka_1
    x2, y2 = tocka_2

    lijevo = min(x1, x2)
    desno = max(x1, x2)
    gore = min(y1, y2)
    dolje = max(y1, y2)

    return (lijevo, gore), (desno, dolje)


def prikazni_naziv(naziv):
    """
    Vraća kraći naziv za ispis na slici.
    """
    if naziv == "Regija 5 - KRUZNI TOK":
        return "R5 - KRUZNI TOK"

    broj = naziv.split()[1]
    return f"R{broj}"


def nacrtaj_spremljenu_regiju(slika, naziv, pravokutnik):
    """
    Crta spremljenu regiju s prozirnom ispunom i oznakom.
    """
    gornji_lijevi, donji_desni = pravokutnik
    boja = boje[naziv]

    overlay = slika.copy()

    cv2.rectangle(
        overlay,
        gornji_lijevi,
        donji_desni,
        boja,
        -1
    )

    cv2.addWeighted(
        overlay,
        0.18,
        slika,
        0.82,
        0,
        slika
    )

    cv2.rectangle(
        slika,
        gornji_lijevi,
        donji_desni,
        boja,
        3
    )

    cv2.putText(
        slika,
        prikazni_naziv(naziv),
        (
            gornji_lijevi[0],
            max(25, gornji_lijevi[1] - 8)
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        boja,
        2
    )


def ponovno_nacrtaj():
    """
    Ponovno prikazuje originalni frame, spremljene regije
    i privremeni pravokutnik koji se trenutačno crta.
    """
    global frame

    frame = originalni_frame.copy()

    for naziv, pravokutnik in regije.items():
        nacrtaj_spremljenu_regiju(
            frame,
            naziv,
            pravokutnik
        )

    if (
        crtanje_u_tijeku
        and pocetna_tocka is not None
        and trenutna_tocka is not None
        and trenutni_indeks < len(nazivi_regija)
    ):
        gornji_lijevi, donji_desni = normaliziraj_pravokutnik(
            pocetna_tocka,
            trenutna_tocka
        )

        naziv = nazivi_regija[trenutni_indeks]
        boja = boje[naziv]

        cv2.rectangle(
            frame,
            gornji_lijevi,
            donji_desni,
            boja,
            2
        )

    if trenutni_indeks < len(nazivi_regija):
        naziv = nazivi_regija[trenutni_indeks]

        cv2.putText(
            frame,
            f"Trenutno oznacavanje: {naziv}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            boje[naziv],
            2
        )

        if naziv == "Regija 5 - KRUZNI TOK":
            uputa = "Oznaci cijelo podrucje kruznog toka"
        else:
            uputa = "Oznaci krak kruznog toka - ulaz i izlaz zajedno"

        cv2.putText(
            frame,
            uputa,
            (20, 68),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
    else:
        cv2.putText(
            frame,
            "Sve regije oznacene - ENTER za potvrdu",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )


def obrisi_zadnju_regiju():
    """
    Briše posljednju spremljenu regiju.
    """
    global trenutni_indeks
    global pocetna_tocka
    global trenutna_tocka
    global crtanje_u_tijeku

    pocetna_tocka = None
    trenutna_tocka = None
    crtanje_u_tijeku = False

    if trenutni_indeks == 0:
        print("Nema spremljenih regija za brisanje.")
        ponovno_nacrtaj()
        return

    trenutni_indeks -= 1
    naziv = nazivi_regija[trenutni_indeks]

    if naziv in regije:
        del regije[naziv]

    print(f"Obrisana regija: {naziv}")

    ponovno_nacrtaj()


def ponisti_sve():
    """
    Briše sve regije i vraća kalibraciju na početak.
    """
    global trenutni_indeks
    global pocetna_tocka
    global trenutna_tocka
    global crtanje_u_tijeku

    regije.clear()

    trenutni_indeks = 0
    pocetna_tocka = None
    trenutna_tocka = None
    crtanje_u_tijeku = False

    print("Sve regije su obrisane.")

    ponovno_nacrtaj()


def obrada_misa(event, x, y, flags, param):
    """
    Klikom i povlačenjem miša crta se pravokutna regija.
    """
    global trenutni_indeks
    global pocetna_tocka
    global trenutna_tocka
    global crtanje_u_tijeku

    if trenutni_indeks >= len(nazivi_regija):
        return

    if event == cv2.EVENT_LBUTTONDOWN:
        pocetna_tocka = (x, y)
        trenutna_tocka = (x, y)
        crtanje_u_tijeku = True

        ponovno_nacrtaj()

    elif event == cv2.EVENT_MOUSEMOVE and crtanje_u_tijeku:
        trenutna_tocka = (x, y)

        ponovno_nacrtaj()

    elif event == cv2.EVENT_LBUTTONUP and crtanje_u_tijeku:
        trenutna_tocka = (x, y)

        gornji_lijevi, donji_desni = normaliziraj_pravokutnik(
            pocetna_tocka,
            trenutna_tocka
        )

        sirina_regije = donji_desni[0] - gornji_lijevi[0]
        visina_regije = donji_desni[1] - gornji_lijevi[1]

        if sirina_regije < 10 or visina_regije < 10:
            print(
                "Regija je premala. "
                "Ponovno nacrtaj pravokutnik."
            )

            pocetna_tocka = None
            trenutna_tocka = None
            crtanje_u_tijeku = False

            ponovno_nacrtaj()
            return

        naziv = nazivi_regija[trenutni_indeks]

        regije[naziv] = (
            gornji_lijevi,
            donji_desni
        )

        print(
            f"{naziv}: "
            f"({gornji_lijevi}, {donji_desni})"
        )

        trenutni_indeks += 1
        pocetna_tocka = None
        trenutna_tocka = None
        crtanje_u_tijeku = False

        ponovno_nacrtaj()


# =========================================================
# POKRETANJE PROZORA
# =========================================================

naziv_prozora = "Test 08 - Kalibracija 5 regija kruznog toka"

cv2.namedWindow(
    naziv_prozora,
    cv2.WINDOW_NORMAL
)

cv2.setMouseCallback(
    naziv_prozora,
    obrada_misa
)

ponovno_nacrtaj()


print("\nUPUTE")
print("--------------------------------------------------")
print("Lijeva tipka miša + povlačenje : crtanje regije")
print("Backspace                      : obriši zadnju")
print("R                              : obriši sve")
print("Enter                          : potvrdi regije")
print("Esc                            : prekid bez spremanja")
print("--------------------------------------------------")
print("Redoslijed označavanja:")
print("Regija 1 - gornji krak")
print("Regija 2 - desni krak")
print("Regija 3 - donji krak")
print("Regija 4 - lijevi krak")
print("Regija 5 - cijeli kružni tok")
print("--------------------------------------------------")


potvrdeno = False

while True:
    cv2.imshow(
        naziv_prozora,
        frame
    )

    key = cv2.waitKey(10) & 0xFF

    if key == 27:
        break

    if key in (8, 127):
        obrisi_zadnju_regiju()

    if key in (ord("r"), ord("R")):
        ponisti_sve()

    if key in (10, 13):
        if len(regije) == len(nazivi_regija):
            potvrdeno = True
            break

        print(
            f"Nisu označene sve regije: "
            f"{len(regije)}/{len(nazivi_regija)}"
        )

cv2.destroyAllWindows()


# =========================================================
# ISPIS I SPREMANJE REZULTATA
# =========================================================

if potvrdeno:
    ponovno_nacrtaj()

    cv2.imwrite(
        izlazna_slika,
        frame
    )

    print(
        "\nKopiraj sljedeće regije u "
        "08_kruzni_tok.py:\n"
    )

    print("regije = {")

    for naziv in nazivi_regija:
        gornji_lijevi, donji_desni = regije[naziv]

        print(
            f'    "{naziv}": '
            f"({gornji_lijevi}, {donji_desni}),"
        )

    print("}")

    print(
        f"\nSlika kalibracije spremljena je u: "
        f"{izlazna_slika}"
    )

else:
    print(
        "Kalibracija regija prekinuta je bez spremanja."
    )