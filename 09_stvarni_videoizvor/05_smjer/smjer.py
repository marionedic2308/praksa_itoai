# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# FAZA 05 - ODREDIVANJE SMJERA KRETANJA VOZILA
# ============================================================

from collections import defaultdict
from datetime import datetime


# ============================================================
# KALIBRIRANE LINIJE ZA ODREDIVANJE SMJERA
#
# Za svaku prometnu traku koriste se dvije virtualne linije.
#
# L1 = prva linija na koju vozilo nailazi u ocekivanom smjeru
# L2 = druga linija na koju vozilo nailazi u ocekivanom smjeru
#
# L1 -> L2 = ISPRAVAN SMJER
# L2 -> L1 = SUPROTAN SMJER
#
# Koordinate su u originalnoj rezoluciji videoizvora.
# ============================================================

LINIJE_SMJERA = {
    "Traka 1": {
        "L1": ((1173, 695), (1401, 748)),
        "L2": ((1082, 731), (1324, 788)),
    },
    "Traka 2": {
        "L1": ((1543, 695), (1900, 800)),
        "L2": ((1609, 646), (1927, 741)),
    },
}




# ============================================================
# POSTAVKE
# ============================================================

# Mala tolerancija oko krajeva stvarno nacrtanog segmenta.
# Sprjecava da se kratka virtualna linija ponasa kao
# beskonacna linija kroz cijeli kadar.
TOLERANCIJA_SEGMENTA = 35


# ============================================================
# KLASA ZA ODREDIVANJE SMJERA
# ============================================================

class OdredivanjeSmjera:

    def __init__(self):

        # Posljednja bottom-center pozicija svakog ID-a.
        self.prethodna_tocka = {}

        # Stanje prijelaza pojedinog ID-a.
        #
        # Primjer:
        #
        # stanje[25] = {
        #     "traka": "Traka 1",
        #     "prva_linija": "L1",
        #     "vrijeme_prve": datetime(...),
        #     "zavrseno": False
        # }
        self.stanje = {}

        # ID-evi za koje je vec utvrden kompletan prolazak.
        self.zavrseni_id = set()

        # Statistika potvrdenih prolazaka.
        self.ispravan_po_traci = {
            naziv: 0
            for naziv in LINIJE_SMJERA
        }

        self.suprotan_po_traci = {
            naziv: 0
            for naziv in LINIJE_SMJERA
        }

        # Statistika klasa.
        self.klase_ispravan = {
            naziv: defaultdict(int)
            for naziv in LINIJE_SMJERA
        }

        self.klase_suprotan = {
            naziv: defaultdict(int)
            for naziv in LINIJE_SMJERA
        }


    # ========================================================
    # ORIJENTACIJA TRI TOCKE
    # ========================================================

    @staticmethod
    def orijentacija(a, b, c):

        ax, ay = a
        bx, by = b
        cx, cy = c

        return (
            (bx - ax) * (cy - ay)
            -
            (by - ay) * (cx - ax)
        )


    # ========================================================
    # PROVJERA JE LI TOCKA NA SEGMENTU
    # ========================================================

    @staticmethod
    def tocka_na_segmentu(
        tocka,
        pocetak,
        kraj,
        tolerancija=TOLERANCIJA_SEGMENTA
    ):

        x, y = tocka

        x1, y1 = pocetak
        x2, y2 = kraj

        return (
            min(x1, x2) - tolerancija
            <= x
            <= max(x1, x2) + tolerancija
            and
            min(y1, y2) - tolerancija
            <= y
            <= max(y1, y2) + tolerancija
        )


    # ========================================================
    # IZRAČUN SJECISTA DVAJU PRAVACA
    # ========================================================

    @staticmethod
    def izracunaj_sjeciste(a, b, c, d):

        x1, y1 = a
        x2, y2 = b

        x3, y3 = c
        x4, y4 = d

        nazivnik = (
            (x1 - x2) * (y3 - y4)
            -
            (y1 - y2) * (x3 - x4)
        )

        if abs(nazivnik) < 1e-9:
            return None

        px = (
            (
                x1 * y2
                -
                y1 * x2
            )
            * (x3 - x4)
            -
            (x1 - x2)
            * (
                x3 * y4
                -
                y3 * x4
            )
        ) / nazivnik

        py = (
            (
                x1 * y2
                -
                y1 * x2
            )
            * (y3 - y4)
            -
            (y1 - y2)
            * (
                x3 * y4
                -
                y3 * x4
            )
        ) / nazivnik

        return (
            px,
            py
        )


    # ========================================================
    # PROVJERA STVARNOG PRELASKA SEGMENTA
    # ========================================================

    def presjek_segmenata(
        self,
        prethodna,
        trenutna,
        linija
    ):

        """
        Provjerava je li putanja bottom-center tocke
        izmedu dva uzastopna framea stvarno presjekla
        NACRTANI segment virtualne linije.

        Ne koristi se samo promjena strane beskonacnog
        pravca, nego stvarna geometrijska pozicija
        sjecista na konacnom segmentu.
        """

        p1, p2 = linija

        strana_prethodna = self.orijentacija(
            p1,
            p2,
            prethodna
        )

        strana_trenutna = self.orijentacija(
            p1,
            p2,
            trenutna
        )

        # Mora postojati promjena strane.
        if (
            strana_prethodna
            * strana_trenutna
            >= 0
        ):
            return False

        sjeciste = self.izracunaj_sjeciste(
            prethodna,
            trenutna,
            p1,
            p2
        )

        if sjeciste is None:
            return False

        # Sjeciste mora biti na stvarno nacrtanoj
        # virtualnoj liniji.
        if not self.tocka_na_segmentu(
            sjeciste,
            p1,
            p2
        ):
            return False

        # Sjeciste mora biti i na stvarnoj putanji
        # bottom-center tocke izmedu dva framea.
        if not self.tocka_na_segmentu(
            sjeciste,
            prethodna,
            trenutna,
            tolerancija=5
        ):
            return False

        return True


    # ========================================================
    # PRONALAZAK PRIJEĐENIH LINIJA
    # ========================================================

    def pronadi_prijelaze(
        self,
        prethodna,
        trenutna
    ):

        """
        Vraca popis svih virtualnih linija koje je
        putanja objekta presjekla izmedu dva framea.

        Rezultat:
            [
                ("Traka 1", "L1"),
                ...
            ]
        """

        prijelazi = []

        for naziv_trake, linije in (
            LINIJE_SMJERA.items()
        ):

            for naziv_linije, linija in (
                linije.items()
            ):

                if self.presjek_segmenata(
                    prethodna,
                    trenutna,
                    linija
                ):

                    prijelazi.append(
                        (
                            naziv_trake,
                            naziv_linije
                        )
                    )

        return prijelazi


    # ========================================================
    # OBRADA JEDNOG OBJEKTA
    # ========================================================

    def obradi_objekt(
        self,
        track_id,
        tocka,
        naziv_klase
    ):

        """
        Obraduje aktualnu bottom-center poziciju vozila.

        Prvi potvrdeni prijelaz preko L1 ili L2 pamti se.

        Kada isti ID u istoj prometnoj traci prijede
        drugu virtualnu liniju, odreduje se smjer:

            L1 -> L2 = ISPRAVAN SMJER
            L2 -> L1 = SUPROTAN SMJER

        Funkcija vraca dogadaj samo kada je kompletan
        prolazak potvrden.
        """

        prethodna = self.prethodna_tocka.get(
            track_id
        )

        # Prvo opazanje vozila.
        if prethodna is None:

            self.prethodna_tocka[
                track_id
            ] = tocka

            return None

        # Vec zavrsen prolazak vise se ne obraduje.
        if track_id in self.zavrseni_id:

            self.prethodna_tocka[
                track_id
            ] = tocka

            return None

        prijelazi = self.pronadi_prijelaze(
            prethodna,
            tocka
        )

        # Aktualna pozicija sprema se bez obzira
        # postoji li prijelaz.
        self.prethodna_tocka[
            track_id
        ] = tocka

        if not prijelazi:
            return None

        # U normalnom radu ocekuje se najcesce jedan
        # prijelaz izmedu dva obradena framea.
        for naziv_trake, naziv_linije in prijelazi:

            vrijeme_sada = datetime.now()

            trenutno_stanje = self.stanje.get(
                track_id
            )

            # ------------------------------------------------
            # PRVA PRIJEĐENA LINIJA
            # ------------------------------------------------

            if trenutno_stanje is None:

                self.stanje[
                    track_id
                ] = {
                    "traka": naziv_trake,
                    "prva_linija": naziv_linije,
                    "vrijeme_prve": vrijeme_sada,
                    "zavrseno": False
                }

                print(
                    f"[ID {track_id}] "
                    f"{naziv_trake} | "
                    f"prijedena {naziv_linije} | "
                    f"{vrijeme_sada.strftime('%H:%M:%S.%f')[:-3]}"
                )

                continue

            # ------------------------------------------------
            # PRIJELAZ MORA BITI U ISTOJ TRACI
            # ------------------------------------------------

            if (
                trenutno_stanje["traka"]
                != naziv_trake
            ):
                continue

            # ------------------------------------------------
            # ISTA LINIJA SE NE RACUNA PONOVNO
            # ------------------------------------------------

            if (
                trenutno_stanje["prva_linija"]
                == naziv_linije
            ):
                continue

            # ------------------------------------------------
            # DRUGA LINIJA JE PRIJEĐENA
            # ------------------------------------------------

            prva_linija = (
                trenutno_stanje["prva_linija"]
            )

            vrijeme_prve = (
                trenutno_stanje["vrijeme_prve"]
            )

            vrijeme_druge = vrijeme_sada

            trajanje = (
                vrijeme_druge
                -
                vrijeme_prve
            ).total_seconds()

            # ------------------------------------------------
            # ODREĐIVANJE SMJERA
            # ------------------------------------------------

            if (
                prva_linija == "L1"
                and
                naziv_linije == "L2"
            ):

                status = "ISPRAVAN SMJER"

                self.ispravan_po_traci[
                    naziv_trake
                ] += 1

                self.klase_ispravan[
                    naziv_trake
                ][naziv_klase] += 1

            elif (
                prva_linija == "L2"
                and
                naziv_linije == "L1"
            ):

                status = "SUPROTAN SMJER"

                self.suprotan_po_traci[
                    naziv_trake
                ] += 1

                self.klase_suprotan[
                    naziv_trake
                ][naziv_klase] += 1

            else:

                continue

            # ID je zavrsio kompletan prolazak.
            self.zavrseni_id.add(
                track_id
            )

            self.stanje[
                track_id
            ]["zavrseno"] = True

            # ------------------------------------------------
            # DOGAĐAJ ZA MAIN / CSV
            # ------------------------------------------------

            dogadaj = {
                "track_id": track_id,
                "klasa": naziv_klase,
                "traka": naziv_trake,
                "prva_linija": prva_linija,
                "druga_linija": naziv_linije,
                "vrijeme_prve": vrijeme_prve,
                "vrijeme_druge": vrijeme_druge,
                "trajanje": trajanje,
                "status": status
            }

            print()
            print(
                f"[PROLAZAK] ID {track_id} | "
                f"{naziv_klase} | "
                f"{naziv_trake}"
            )

            print(
                f"           {prva_linija} -> "
                f"{naziv_linije}"
            )

            print(
                f"           T1: "
                f"{vrijeme_prve.strftime('%H:%M:%S.%f')[:-3]}"
            )

            print(
                f"           T2: "
                f"{vrijeme_druge.strftime('%H:%M:%S.%f')[:-3]}"
            )

            print(
                f"           dt: "
                f"{trajanje:.3f} s"
            )

            print(
                f"           STATUS: {status}"
            )

            print()

            return dogadaj

        return None


    # ========================================================
    # STATISTIKA PO TRACI
    # ========================================================

    def broj_ispravnih(
        self,
        naziv_trake
    ):

        return self.ispravan_po_traci.get(
            naziv_trake,
            0
        )


    def broj_suprotnih(
        self,
        naziv_trake
    ):

        return self.suprotan_po_traci.get(
            naziv_trake,
            0
        )


    # ========================================================
    # UKUPNA STATISTIKA
    # ========================================================

    def ukupno_ispravnih(self):

        return sum(
            self.ispravan_po_traci.values()
        )


    def ukupno_suprotnih(self):

        return sum(
            self.suprotan_po_traci.values()
        )


    def ukupno_prolazaka(self):

        return (
            self.ukupno_ispravnih()
            +
            self.ukupno_suprotnih()
        )


    # ========================================================
    # STATISTIKA KLASA
    # ========================================================

    def statistika_ispravnih_klasa(
        self,
        naziv_trake
    ):

        return dict(
            self.klase_ispravan.get(
                naziv_trake,
                {}
            )
        )


    def statistika_suprotnih_klasa(
        self,
        naziv_trake
    ):

        return dict(
            self.klase_suprotan.get(
                naziv_trake,
                {}
            )
        )