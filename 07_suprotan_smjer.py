from ultralytics import YOLO
import cv2
import os
from datetime import datetime
from collections import defaultdict


print("Pokrećem Test 07 – detekcija vozila u suprotnom smjeru...")


# =========================================================
# OSNOVNE POSTAVKE
# =========================================================

model = YOLO("yolo11n.pt")
print("YOLO model je učitan.")

ulazni_video = "test06.mp4"

izlazna_mapa = "rezultati/suprotan_smjer"
os.makedirs(izlazna_mapa, exist_ok=True)

izlazni_video = os.path.join(
    izlazna_mapa,
    "test07_suprotan_smjer_final.mp4"
)


# =========================================================
# ZAMIJENJENE LINIJE IZ TESTA 06
# =========================================================
# U Testu 06 program je provjeravao ispravan smjer L1 -> L2.
#
# U Testu 07 fizičke pozicije Linije 1 i Linije 2 su zamijenjene.
# Program i dalje provjerava L1 -> L2, ali to sada predstavlja
# suprotan smjer u odnosu na Test 06.

linije = {
    # Test 06:
    # L1 = ((316, 483), (396, 503))
    # L2 = ((253, 536), (338, 555))

    "T1-L1": ((253, 536), (338, 555)),
    "T1-L2": ((316, 483), (396, 503)),

    # Test 06:
    # L1 = ((526, 403), (572, 408))
    # L2 = ((495, 440), (558, 451))

    "T2-L1": ((495, 440), (558, 451)),
    "T2-L2": ((526, 403), (572, 408)),

    # Test 06:
    # L1 = ((700, 435), (768, 434))
    # L2 = ((692, 381), (740, 381))

    "T3-L1": ((692, 381), (740, 381)),
    "T3-L2": ((700, 435), (768, 434)),

    # Test 06:
    # L1 = ((901, 591), (991, 573))
    # L2 = ((863, 525), (922, 510))

    "T4-L1": ((863, 525), (922, 510)),
    "T4-L2": ((901, 591), (991, 573)),
}


# Boje u BGR formatu koji koristi OpenCV
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


trake = {
    "Traka 1": {
        "L1": "T1-L1",
        "L2": "T1-L2",
    },
    "Traka 2": {
        "L1": "T2-L1",
        "L2": "T2-L2",
    },
    "Traka 3": {
        "L1": "T3-L1",
        "L2": "T3-L2",
    },
    "Traka 4": {
        "L1": "T4-L1",
        "L2": "T4-L2",
    },
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
    print("GREŠKA: FPS videozapisa nije ispravno očitan.")
    cap.release()
    raise SystemExit

trajanje_videa = ukupno_frameova / fps

print(f"Ulazni video : {ulazni_video}")
print(f"Rezolucija   : {sirina}x{visina}")
print(f"FPS          : {fps:.2f}")
print(f"Frameova     : {ukupno_frameova}")
print(f"Trajanje     : {trajanje_videa:.2f} sekundi")

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

writer = cv2.VideoWriter(
    izlazni_video,
    fourcc,
    fps,
    (sirina, visina)
)

if not writer.isOpened():
    print("GREŠKA: Izlazni video nije moguće otvoriti za zapisivanje.")
    cap.release()
    raise SystemExit


# =========================================================
# PODACI KOJE PROGRAM PAMTI
# =========================================================

# Prethodna pozicija svakog tracking ID-a
prethodne_pozicije = {}

# Pamti kada je vozilo aktiviralo novu Liniju 1.
# Budući da su linije zamijenjene, ta Linija 1 odgovara
# staroj Liniji 2 iz Testa 06.
aktivacije_l1 = {}

# Sprječava višestruku aktivaciju iste linije istim ID-em
aktivirane_linije_po_id = set()

# Vozila koja su već evidentirana kao suprotan smjer
zavrseni_id = set()

# Broj vozila u suprotnom smjeru po prometnim trakama
brojaci = {
    "Traka 1": 0,
    "Traka 2": 0,
    "Traka 3": 0,
    "Traka 4": 0,
}

# Dijagnostičko brojanje aktivacija svake linije
aktivacije_linija = {
    "T1-L1": 0,
    "T1-L2": 0,
    "T2-L1": 0,
    "T2-L2": 0,
    "T3-L1": 0,
    "T3-L2": 0,
    "T4-L1": 0,
    "T4-L2": 0,
}

brojaci_klase = defaultdict(int)
evidencija_suprotan_smjer = []

zadnja_poruka = ""
zadnja_poruka_do_framea = 0


# =========================================================
# POMOĆNE FUNKCIJE
# =========================================================

def orijentacija(a, b, c):
    """
    Određuje orijentaciju triju točaka.
    Koristi se za provjeru sijeku li se dva segmenta.
    """
    vrijednost = (
        (b[1] - a[1]) * (c[0] - b[0])
        - (b[0] - a[0]) * (c[1] - b[1])
    )

    if abs(vrijednost) < 1e-9:
        return 0

    return 1 if vrijednost > 0 else 2


def presao_liniju(prethodna_tocka, trenutna_tocka, linija):
    """
    Provjerava siječe li putanja vozila između dva uzastopna
    framea definiranu virtualnu liniju.
    """
    p1 = prethodna_tocka
    p2 = trenutna_tocka
    p3, p4 = linija

    o1 = orijentacija(p1, p2, p3)
    o2 = orijentacija(p1, p2, p4)
    o3 = orijentacija(p3, p4, p1)
    o4 = orijentacija(p3, p4, p2)

    return o1 != o2 and o3 != o4


def formatiraj_vrijeme_videa(sekunde):
    """
    Pretvara vrijeme u sekundama u format MM:SS.mmm.
    """
    minute = int(sekunde // 60)
    preostale_sekunde = sekunde % 60

    return f"{minute:02d}:{preostale_sekunde:06.3f}"


def evidentiraj_aktivaciju_linije(
    track_id,
    naziv_linije,
    naziv_trake,
    vrijeme_videa,
    frame_broj
):
    """
    Bilježi aktivaciju određene linije samo jednom
    za isti tracking ID.
    """
    kljuc_aktivacije = (track_id, naziv_linije)

    if kljuc_aktivacije in aktivirane_linije_po_id:
        return False

    aktivirane_linije_po_id.add(kljuc_aktivacije)
    aktivacije_linija[naziv_linije] += 1

    print(
        f"ID {track_id} aktivirao {naziv_linije} "
        f"({naziv_trake}) | "
        f"frame: {frame_broj} | "
        f"vrijeme videa: "
        f"{formatiraj_vrijeme_videa(vrijeme_videa)}"
    )

    return True


# =========================================================
# OBRADA CIJELOG VIDEA
# =========================================================

print("Počinjem obradu cijelog videozapisa...")

frame_broj = 0

while True:
    ret, frame = cap.read()

    if not ret:
        break

    frame_broj += 1
    vrijeme_videa = frame_broj / fps

    if frame_broj % 100 == 0:
        print(
            f"Obrađen frame: "
            f"{frame_broj}/{ukupno_frameova}"
        )

    results = model.track(
        frame,
        persist=True,
        classes=[2, 5, 7],       # car, bus, truck
        conf=0.15,
        imgsz=1280,
        tracker="bytetrack.yaml",
        verbose=False
    )

    annotated_frame = results[0].plot()
    boxes = results[0].boxes

    if boxes.id is not None:
        ids = boxes.id.cpu().numpy().astype(int)
        klase = boxes.cls.cpu().numpy().astype(int)
        koordinate = boxes.xyxy.cpu().numpy()

        for box, track_id, cls_id in zip(
            koordinate,
            ids,
            klase
        ):
            x1, y1, x2, y2 = box

            # Donja sredina bounding boxa približno predstavlja
            # položaj vozila na površini ceste.
            tocka_pracenja = (
                int((x1 + x2) / 2),
                int(y2)
            )

            if track_id in prethodne_pozicije:
                prethodna_tocka = prethodne_pozicije[track_id]

                if track_id not in zavrseni_id:

                    for naziv_trake, oznake in trake.items():
                        naziv_l1 = oznake["L1"]
                        naziv_l2 = oznake["L2"]

                        linija_l1 = linije[naziv_l1]
                        linija_l2 = linije[naziv_l2]

                        kljuc_vozila_i_trake = (
                            track_id,
                            naziv_trake
                        )

                        # -----------------------------------------
                        # PRELAZAK PREKO ZAMIJENJENE LINIJE 1
                        # -----------------------------------------

                        if presao_liniju(
                            prethodna_tocka,
                            tocka_pracenja,
                            linija_l1
                        ):
                            nova_aktivacija = evidentiraj_aktivaciju_linije(
                                track_id,
                                naziv_l1,
                                naziv_trake,
                                vrijeme_videa,
                                frame_broj
                            )

                            if (
                                nova_aktivacija
                                and kljuc_vozila_i_trake
                                not in aktivacije_l1
                            ):
                                aktivacije_l1[
                                    kljuc_vozila_i_trake
                                ] = {
                                    "vrijeme_videa": vrijeme_videa,
                                    "vrijeme_racunala": datetime.now(),
                                    "frame": frame_broj,
                                }

                        # -----------------------------------------
                        # PRELAZAK PREKO ZAMIJENJENE LINIJE 2
                        # -----------------------------------------

                        if presao_liniju(
                            prethodna_tocka,
                            tocka_pracenja,
                            linija_l2
                        ):
                            evidentiraj_aktivaciju_linije(
                                track_id,
                                naziv_l2,
                                naziv_trake,
                                vrijeme_videa,
                                frame_broj
                            )

                            # Prolaz se evidentira samo ako je isti ID
                            # prethodno prešao zamijenjenu Liniju 1.
                            if (
                                kljuc_vozila_i_trake
                                in aktivacije_l1
                            ):
                                podatak_l1 = aktivacije_l1[
                                    kljuc_vozila_i_trake
                                ]

                                vrijeme_l1_video = podatak_l1[
                                    "vrijeme_videa"
                                ]
                                vrijeme_l1_racunalo = podatak_l1[
                                    "vrijeme_racunala"
                                ]

                                vrijeme_l2_video = vrijeme_videa
                                vrijeme_l2_racunalo = datetime.now()

                                razlika_vremena = (
                                    vrijeme_l2_video
                                    - vrijeme_l1_video
                                )

                                if razlika_vremena > 0:
                                    naziv_klase = model.names[
                                        cls_id
                                    ]

                                    brojaci[naziv_trake] += 1
                                    brojaci_klase[
                                        naziv_klase
                                    ] += 1

                                    zavrseni_id.add(track_id)

                                    rezultat = {
                                        "id": track_id,
                                        "klasa": naziv_klase,
                                        "traka": naziv_trake,
                                        "vrijeme_l1_video":
                                            vrijeme_l1_video,
                                        "vrijeme_l2_video":
                                            vrijeme_l2_video,
                                        "vrijeme_l1_racunalo":
                                            vrijeme_l1_racunalo,
                                        "vrijeme_l2_racunalo":
                                            vrijeme_l2_racunalo,
                                        "razlika":
                                            razlika_vremena,
                                        "status":
                                            "SUPROTAN SMJER",
                                    }

                                    evidencija_suprotan_smjer.append(
                                        rezultat
                                    )

                                    zadnja_poruka = (
                                        f"ID {track_id} | "
                                        f"{naziv_trake} | "
                                        "SUPROTAN SMJER"
                                    )

                                    zadnja_poruka_do_framea = (
                                        frame_broj + int(fps * 2)
                                    )

                                    print("\n----------------------------------------")
                                    print("SUPROTAN SMJER")
                                    print("----------------------------------------")
                                    print(
                                        f"ID vozila          : {track_id}"
                                    )
                                    print(
                                        f"Klasa               : {naziv_klase}"
                                    )
                                    print(
                                        f"Prometna traka      : {naziv_trake}"
                                    )
                                    print(
                                        "Redoslijed          : "
                                        "zamijenjena L1 -> zamijenjena L2"
                                    )
                                    print(
                                        "Vrijeme videa L1    : "
                                        f"{formatiraj_vrijeme_videa(vrijeme_l1_video)}"
                                    )
                                    print(
                                        "Vrijeme videa L2    : "
                                        f"{formatiraj_vrijeme_videa(vrijeme_l2_video)}"
                                    )
                                    print(
                                        "Vrijeme računala L1 : "
                                        f"{vrijeme_l1_racunalo.strftime('%H:%M:%S.%f')[:-3]}"
                                    )
                                    print(
                                        "Vrijeme računala L2 : "
                                        f"{vrijeme_l2_racunalo.strftime('%H:%M:%S.%f')[:-3]}"
                                    )
                                    print(
                                        "Razlika vremena     : "
                                        f"{razlika_vremena:.3f} s"
                                    )
                                    print(
                                        "Status               : "
                                        "SUPROTAN SMJER"
                                    )
                                    print("----------------------------------------\n")

                                    break

            prethodne_pozicije[track_id] = tocka_pracenja


    # =====================================================
    # CRTANJE LINIJA I NJIHOVIH OZNAKA
    # =====================================================

    for naziv_linije, linija in linije.items():
        boja = boje[naziv_linije]

        cv2.line(
            annotated_frame,
            linija[0],
            linija[1],
            boja,
            4
        )

        cv2.putText(
            annotated_frame,
            naziv_linije,
            (
                linija[0][0],
                max(25, linija[0][1] - 10)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            boja,
            2
        )


    # =====================================================
    # ISPIS BROJAČA NA VIDEO
    # =====================================================

    osnovne_boje = {
        "Traka 1": (0, 255, 0),
        "Traka 2": (0, 255, 255),
        "Traka 3": (0, 0, 255),
        "Traka 4": (255, 0, 0),
    }

    for indeks, (naziv_trake, broj) in enumerate(
        brojaci.items()
    ):
        cv2.putText(
            annotated_frame,
            f"{naziv_trake}: {broj}",
            (10, 30 + indeks * 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            osnovne_boje[naziv_trake],
            2
        )

    ukupno_suprotnih = sum(brojaci.values())

    cv2.putText(
        annotated_frame,
        f"Ukupno vozila u suprotnom smjeru: "
        f"{ukupno_suprotnih}",
        (10, 160),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (0, 0, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"Vrijeme videa: "
        f"{formatiraj_vrijeme_videa(vrijeme_videa)}",
        (10, 195),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    if frame_broj <= zadnja_poruka_do_framea:
        cv2.putText(
            annotated_frame,
            zadnja_poruka,
            (10, visina - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            3
        )

    writer.write(annotated_frame)


# =========================================================
# ZAVRŠETAK I ISPIS REZULTATA
# =========================================================

cap.release()
writer.release()

print("\n========================================")
print("       REZULTAT TESTA 07")
print("========================================")
print("Status        : Uspješno završeno")
print(f"Ulazni video  : {ulazni_video}")
print("Model         : yolo11n.pt")
print("Metoda        : Detekcija suprotnog smjera")
print("Redoslijed    : Zamijenjene linije iz Testa 06")
print("Trajanje testa: Cijeli videozapis")
print("----------------------------------------")

for naziv_trake, broj in brojaci.items():
    print(f"{naziv_trake:<14}: {broj}")

print("----------------------------------------")
print(
    f"Ukupno vozila u suprotnom smjeru: "
    f"{sum(brojaci.values())}"
)

for naziv_klase, broj in brojaci_klase.items():
    print(f"{naziv_klase:<14}: {broj}")

print("\n========================================")
print("       AKTIVACIJE PO LINIJAMA")
print("========================================")

for naziv_linije, broj in aktivacije_linija.items():
    print(f"{naziv_linije:<8}: {broj}")

print("----------------------------------------")
print(f"Rezultat      : {izlazni_video}")
print("========================================")