from ultralytics import YOLO
import cv2
import os
from collections import defaultdict


print("Pokrećem Test 08 – poboljšana detekcija kružnog toka...")


# =========================================================
# OSNOVNE POSTAVKE
# =========================================================

# Jači YOLO model od prethodno korištenog yolo11n.pt.
# Ako model nije ranije preuzet, Ultralytics će ga automatski preuzeti.
model = YOLO("yolo11m.pt")

print("YOLO11m model je učitan.")

ulazni_video = "test08.mp4"

izlazna_mapa = "rezultati/kruzni_tok"
os.makedirs(izlazna_mapa, exist_ok=True)

izlazni_video = os.path.join(
    izlazna_mapa,
    "test08_poboljsana_dijagnostika.mp4"
)

TRAJANJE_TESTA_SEKUNDE = 15


# =========================================================
# POSTAVKE DETEKCIJE
# =========================================================

CONFIDENCE = 0.10
IMAGE_SIZE = 1920

# Objekt mora biti praćen najmanje ovoliko frameova
# prije nego što se smatra dovoljno stabilnim.
MINIMALNO_FRAMEOVA_PRAĆENJA = 4

# Minimalne dimenzije bounding boxa.
# Time odbacujemo vrlo sitne i nestabilne detekcije.
MINIMALNA_SIRINA_OBJEKTA = 8
MINIMALNA_VISINA_OBJEKTA = 8


# =========================================================
# REGIJE DOBIVENE KALIBRACIJOM
# =========================================================

regije = {
    "Regija 1": ((821, 187), (991, 366)),
    "Regija 2": ((1115, 421), (1365, 586)),
    "Regija 3": ((848, 693), (991, 902)),
    "Regija 4": ((540, 463), (796, 584)),
    "Regija 5 - KRUZNI TOK": ((474, 169), (1400, 962)),
}


boje = {
    "Regija 1": (0, 0, 255),
    "Regija 2": (0, 255, 255),
    "Regija 3": (255, 0, 0),
    "Regija 4": (255, 0, 255),
    "Regija 5 - KRUZNI TOK": (0, 255, 0),
}


# =========================================================
# OTVARANJE VIDEA
# =========================================================

cap = cv2.VideoCapture(ulazni_video)

if not cap.isOpened():
    print(f"GREŠKA: Video '{ulazni_video}' nije moguće otvoriti.")
    raise SystemExit

sirina = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
visina = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
ukupno_frameova = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

if fps <= 0:
    print("GREŠKA: FPS nije ispravno očitan.")
    cap.release()
    raise SystemExit

maksimalno_frameova = min(
    int(fps * TRAJANJE_TESTA_SEKUNDE),
    ukupno_frameova
)

print(f"Ulazni video       : {ulazni_video}")
print(f"Rezolucija         : {sirina}x{visina}")
print(f"FPS                : {fps:.2f}")
print(f"Ukupno frameova    : {ukupno_frameova}")
print(f"Trajanje testa     : {TRAJANJE_TESTA_SEKUNDE} sekundi")
print(f"Frameova za obradu : {maksimalno_frameova}")
print(f"Confidence         : {CONFIDENCE}")
print(f"Image size         : {IMAGE_SIZE}")

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

writer = cv2.VideoWriter(
    izlazni_video,
    fourcc,
    fps,
    (sirina, visina)
)

if not writer.isOpened():
    print("GREŠKA: Izlazni video nije moguće otvoriti.")
    cap.release()
    raise SystemExit


# =========================================================
# PODACI ZA PRAĆENJE I DIJAGNOSTIKU
# =========================================================

prethodne_zone = {}

povijest_zona = defaultdict(list)

broj_frameova_po_idu = defaultdict(int)

klase_po_idu = defaultdict(lambda: defaultdict(int))

maksimalna_pouzdanost_po_idu = defaultdict(float)

broj_ulazaka_u_zone = {
    "R1": 0,
    "R2": 0,
    "R3": 0,
    "R4": 0,
    "R5": 0,
    "IZVAN": 0,
}

ukupno_detekcija = 0
odbačeno_premalih = 0


# =========================================================
# POMOĆNE FUNKCIJE
# =========================================================

def tocka_u_pravokutniku(tocka, pravokutnik):
    """
    Provjerava nalazi li se zadana točka unutar pravokutnika.
    """

    x, y = tocka
    (x1, y1), (x2, y2) = pravokutnik

    return x1 <= x <= x2 and y1 <= y <= y2


def odredi_zonu(tocka):
    """
    Određuje zonu u kojoj se nalazi središte objekta.

    Regije 1–4 moraju imati prednost jer se nalaze
    unutar velike Regije 5.
    """

    for broj_regije in range(1, 5):
        naziv_regije = f"Regija {broj_regije}"

        if tocka_u_pravokutniku(
            tocka,
            regije[naziv_regije]
        ):
            return f"R{broj_regije}"

    if tocka_u_pravokutniku(
        tocka,
        regije["Regija 5 - KRUZNI TOK"]
    ):
        return "R5"

    return "IZVAN"


def boja_zone(zona):
    """
    Vraća boju kojom se prikazuje trenutačna zona objekta.
    """

    mapa_boja = {
        "R1": boje["Regija 1"],
        "R2": boje["Regija 2"],
        "R3": boje["Regija 3"],
        "R4": boje["Regija 4"],
        "R5": boje["Regija 5 - KRUZNI TOK"],
        "IZVAN": (255, 255, 255),
    }

    return mapa_boja.get(zona, (255, 255, 255))


def formatiraj_vrijeme_videa(sekunde):
    """
    Pretvara sekunde u format MM:SS.mmm.
    """

    minute = int(sekunde // 60)
    ostatak = sekunde % 60

    return f"{minute:02d}:{ostatak:06.3f}"


def najčešća_klasa(track_id):
    """
    Za određeni tracking ID vraća klasu koju je model
    najčešće dodijelio tijekom praćenja.
    """

    if not klase_po_idu[track_id]:
        return "nepoznato"

    return max(
        klase_po_idu[track_id],
        key=klase_po_idu[track_id].get
    )


# =========================================================
# OBRADA VIDEA
# =========================================================

print("\nPočinjem obradu frameova...\n")

frame_broj = 0

while True:
    ret, frame = cap.read()

    if not ret:
        break

    frame_broj += 1

    if frame_broj > maksimalno_frameova:
        print(
            f"Završena obrada prvih "
            f"{TRAJANJE_TESTA_SEKUNDE} sekundi."
        )
        break

    vrijeme_videa = frame_broj / fps

    if frame_broj % 100 == 0:
        print(
            f"Obrađen frame: "
            f"{frame_broj}/{maksimalno_frameova}"
        )

    results = model.track(
        frame,
        persist=True,
        conf=CONFIDENCE,
        imgsz=IMAGE_SIZE,
        tracker="bytetrack.yaml",
        verbose=False
    )

    annotated_frame = frame.copy()

    boxes = results[0].boxes

    if (
        boxes is not None
        and boxes.id is not None
        and len(boxes) > 0
    ):
        ids = boxes.id.cpu().numpy().astype(int)
        klase = boxes.cls.cpu().numpy().astype(int)
        pouzdanosti = boxes.conf.cpu().numpy()
        koordinate = boxes.xyxy.cpu().numpy()

        for box, track_id, cls_id, confidence in zip(
            koordinate,
            ids,
            klase,
            pouzdanosti
        ):
            ukupno_detekcija += 1

            x1, y1, x2, y2 = box

            sirina_objekta = x2 - x1
            visina_objekta = y2 - y1

            # Odbacivanje vrlo sitnih detekcija.
            if (
                sirina_objekta < MINIMALNA_SIRINA_OBJEKTA
                or visina_objekta < MINIMALNA_VISINA_OBJEKTA
            ):
                odbačeno_premalih += 1
                continue

            broj_frameova_po_idu[track_id] += 1

            naziv_klase = model.names[int(cls_id)]

            klase_po_idu[track_id][naziv_klase] += 1

            maksimalna_pouzdanost_po_idu[track_id] = max(
                maksimalna_pouzdanost_po_idu[track_id],
                float(confidence)
            )

            # Za zračni pogled koristimo točno središte
            # bounding boxa, a ne donju sredinu.
            tocka_pracenja = (
                int((x1 + x2) / 2),
                int((y1 + y2) / 2)
            )

            zona = odredi_zonu(tocka_pracenja)

            prethodna_zona = prethodne_zone.get(track_id)

            # Povijest i terminalski ispis ažuriramo
            # tek kada je objekt praćen dovoljan broj frameova.
            if (
                broj_frameova_po_idu[track_id]
                >= MINIMALNO_FRAMEOVA_PRAĆENJA
                and zona != prethodna_zona
            ):
                broj_ulazaka_u_zone[zona] += 1

                if (
                    not povijest_zona[track_id]
                    or povijest_zona[track_id][-1] != zona
                ):
                    povijest_zona[track_id].append(zona)

                najcesca_klasa = najčešća_klasa(track_id)

                print(
                    f"ID {track_id:<3} "
                    f"({najcesca_klasa}) | "
                    f"{prethodna_zona or 'NOVA DETEKCIJA'} "
                    f"-> {zona} | "
                    f"conf {confidence:.2f} | "
                    f"{formatiraj_vrijeme_videa(vrijeme_videa)}"
                )

                prethodne_zone[track_id] = zona

            boja = boja_zone(zona)

            # Bounding box
            cv2.rectangle(
                annotated_frame,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                boja,
                2
            )

            # Središnja točka objekta
            cv2.circle(
                annotated_frame,
                tocka_pracenja,
                6,
                boja,
                -1
            )

            # Tekst iznad objekta
            tekst = (
                f"ID {track_id} | "
                f"{naziv_klase} | "
                f"{confidence:.2f} | "
                f"{zona}"
            )

            cv2.putText(
                annotated_frame,
                tekst,
                (
                    int(x1),
                    max(25, int(y1) - 8)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                boja,
                2
            )


    # =====================================================
    # CRTANJE VELIKE REGIJE 5
    # =====================================================

    naziv_r5 = "Regija 5 - KRUZNI TOK"
    pravokutnik_r5 = regije[naziv_r5]

    cv2.rectangle(
        annotated_frame,
        pravokutnik_r5[0],
        pravokutnik_r5[1],
        boje[naziv_r5],
        3
    )

    cv2.putText(
        annotated_frame,
        "R5 - KRUZNI TOK",
        (
            pravokutnik_r5[0][0],
            max(25, pravokutnik_r5[0][1] - 8)
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        boje[naziv_r5],
        2
    )


    # =====================================================
    # CRTANJE REGIJA 1–4
    # =====================================================

    for broj_regije in range(1, 5):
        naziv = f"Regija {broj_regije}"
        pravokutnik = regije[naziv]

        cv2.rectangle(
            annotated_frame,
            pravokutnik[0],
            pravokutnik[1],
            boje[naziv],
            3
        )

        cv2.putText(
            annotated_frame,
            f"R{broj_regije}",
            (
                pravokutnik[0][0],
                max(25, pravokutnik[0][1] - 8)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            boje[naziv],
            2
        )


    # =====================================================
    # OPĆI ISPIS NA VIDEO
    # =====================================================

    cv2.rectangle(
        annotated_frame,
        (5, 5),
        (445, 95),
        (0, 0, 0),
        -1
    )

    cv2.putText(
        annotated_frame,
        "TEST 08 - POBOLJSANA DETEKCIJA",
        (15, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"Frame: {frame_broj}/{maksimalno_frameova}",
        (15, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"Vrijeme: {formatiraj_vrijeme_videa(vrijeme_videa)}",
        (15, 85),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    writer.write(annotated_frame)


# =========================================================
# ZAVRŠETAK
# =========================================================

cap.release()
writer.release()


# =========================================================
# ZAVRŠNI IZVJEŠTAJ
# =========================================================

print("\n==================================================")
print("       REZULTAT POBOLJŠANOG TESTA 08")
print("==================================================")
print("Status         : Uspješno završeno")
print(f"Ulazni video   : {ulazni_video}")
print("Model          : yolo11m.pt")
print("Tracker        : ByteTrack")
print(f"Confidence     : {CONFIDENCE}")
print(f"Image size     : {IMAGE_SIZE}")
print(f"Trajanje testa : {TRAJANJE_TESTA_SEKUNDE} sekundi")
print("--------------------------------------------------")
print(f"Detekcija ukupno          : {ukupno_detekcija}")
print(f"Odbačeno premalih objekata: {odbačeno_premalih}")
print(f"Broj različitih ID-eva    : {len(broj_frameova_po_idu)}")
print("--------------------------------------------------")
print("Broj ulazaka u pojedine zone:")

for zona, broj in broj_ulazaka_u_zone.items():
    print(f"{zona:<6}: {broj}")

print("\n--------------------------------------------------")
print("POVIJEST ZONA PO ID-u")
print("--------------------------------------------------")

if not povijest_zona:
    print("Nije pronađen nijedan stabilan objekt.")

else:
    for track_id in sorted(povijest_zona):
        povijest = povijest_zona[track_id]
        najcesca_klasa = najčešća_klasa(track_id)
        broj_frameova = broj_frameova_po_idu[track_id]
        max_conf = maksimalna_pouzdanost_po_idu[track_id]

        print(
            f"ID {track_id:<4} | "
            f"klasa: {najcesca_klasa:<15} | "
            f"frameova: {broj_frameova:<4} | "
            f"max conf: {max_conf:.2f} | "
            f"{' -> '.join(povijest)}"
        )

print("--------------------------------------------------")
print(f"Rezultat       : {izlazni_video}")
print("==================================================")