import cv2

# Ulazni video za Test 06
video_path = "test06.mp4"

# Redoslijed kojim će se crtati linije
nazivi_linija = [
    "T1-L1",
    "T1-L2",
    "T2-L1",
    "T2-L2",
    "T3-L1",
    "T3-L2",
    "T4-L1",
    "T4-L2",
]

# Boje su zadane u BGR formatu koji koristi OpenCV
boje = {
    "T1-L1": (0, 180, 0),
    "T1-L2": (0, 255, 0),

    "T2-L1": (0, 180, 180),
    "T2-L2": (0, 255, 255),

    "T3-L1": (0, 0, 180),
    "T3-L2": (0, 0, 255),

    "T4-L1": (180, 0, 0),
    "T4-L2": (255, 0, 0),
}

tocke = []
linije = {}
trenutni_indeks = 0

cap = cv2.VideoCapture(video_path)

ret, originalni_frame = cap.read()
cap.release()

if not ret:
    print("GREŠKA: Nije moguće učitati prvi frame videozapisa.")
    raise SystemExit

frame = originalni_frame.copy()


def ponovno_nacrtaj():
    global frame

    frame = originalni_frame.copy()

    for naziv, linija in linije.items():
        pocetak, kraj = linija
        boja = boje[naziv]

        cv2.line(frame, pocetak, kraj, boja, 4)

        cv2.putText(
            frame,
            naziv,
            (pocetak[0], max(25, pocetak[1] - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            boja,
            2
        )

    if trenutni_indeks < len(nazivi_linija):
        trenutni_naziv = nazivi_linija[trenutni_indeks]

        cv2.putText(
            frame,
            f"Trenutno oznacavanje: {trenutni_naziv}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            boje[trenutni_naziv],
            2
        )
    else:
        cv2.putText(
            frame,
            "Sve linije su oznacene. ENTER = potvrda",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )


def klik_mis(event, x, y, flags, param):
    global trenutni_indeks, tocke

    if event == cv2.EVENT_LBUTTONDOWN:
        if trenutni_indeks >= len(nazivi_linija):
            return

        tocke.append((x, y))

        if len(tocke) == 2:
            naziv = nazivi_linija[trenutni_indeks]
            linije[naziv] = (tocke[0], tocke[1])

            print(
                f"{naziv}: ({tocke[0]}, {tocke[1]})"
            )

            tocke = []
            trenutni_indeks += 1
            ponovno_nacrtaj()


def obrisi_zadnju_liniju():
    global trenutni_indeks, tocke

    tocke = []

    if trenutni_indeks == 0:
        return

    trenutni_indeks -= 1
    naziv = nazivi_linija[trenutni_indeks]

    if naziv in linije:
        del linije[naziv]

    print(f"Obrisana zadnja linija: {naziv}")
    ponovno_nacrtaj()


cv2.namedWindow("Kalibracija smjera", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Kalibracija smjera", klik_mis)

ponovno_nacrtaj()

print("UPUTE")
print("----------------------------------------")
print("Lijevi klik  : odabir početka i kraja linije")
print("Backspace    : brisanje zadnje označene linije")
print("R            : ponovno crtanje svih linija")
print("Enter        : potvrda i ispis koordinata")
print("Esc          : izlaz bez potvrde")
print("----------------------------------------")

potvrdeno = False

while True:
    cv2.imshow("Kalibracija smjera", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == 27:
        break

    if key in (8, 127):
        obrisi_zadnju_liniju()

    if key in (ord("r"), ord("R")):
        linije.clear()
        tocke = []
        trenutni_indeks = 0
        ponovno_nacrtaj()
        print("Kalibracija je ponovno pokrenuta.")

    if key in (10, 13):
        if len(linije) == len(nazivi_linija):
            potvrdeno = True
            break
        else:
            print(
                f"Još nisu označene sve linije: "
                f"{len(linije)}/{len(nazivi_linija)}"
            )

cv2.destroyAllWindows()

if potvrdeno:
    print("\nKopiraj sljedeće koordinate u 06_smjer_kretanja.py:\n")

    print("linije = {")
    for naziv in nazivi_linija:
        pocetak, kraj = linije[naziv]
        print(f'    "{naziv}": ({pocetak}, {kraj}),')
    print("}")

    slika_rezultata = "rezultati/kalibracija_smjera.jpg"

    import os
    os.makedirs("rezultati", exist_ok=True)

    cv2.imwrite(slika_rezultata, frame)

    print(f"\nSlika kalibracije spremljena je u: {slika_rezultata}")
else:
    print("Kalibracija je prekinuta bez spremanja.")