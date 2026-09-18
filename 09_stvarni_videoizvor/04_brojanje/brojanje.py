# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# FAZA 04 - BROJANJE VOZILA PRELASKOM PREKO VIRTUALNIH LINIJA
# ============================================================

from collections import defaultdict
import math


# ============================================================
# KALIBRIRANE LINIJE
# Koordinate su u originalnoj rezoluciji videoizvora.
# ============================================================

LINIJE_BROJANJA = {
    "Traka 1": ((993, 770), (1241, 836)),
    "Traka 2": ((1704, 586), (2003, 626)),
}


# ============================================================
# POSTAVKE BROJANJA
# ============================================================

# Dodatna tolerancija oko krajeva nacrtanog segmenta.
#
# Time se dopusta mala pogreska trackinga, ali se sprjecava
# da kratka linija djeluje kao beskonacna linija preko kadra.
TOLERANCIJA_SEGMENTA = 35


# ============================================================
# KLASA ZA BROJANJE
# ============================================================

class BrojanjeVozila:

    def __init__(self):

        # Posljednja poznata pozicija svakog ID-a.
        #
        # Za pouzdanu provjeru prijelaza nije dovoljno
        # znati samo stranu linije. Potrebno je znati
        # putanju referentne tocke izmedu dva framea.
        self.prethodna_tocka = {}

        # Globalni skup prebrojanih ID-eva.
        #
        # Jedan ByteTrack ID tijekom ove faze moze
        # predstavljati samo jedan prebrojani prolazak.
        self.prebrojani_id = set()

        # Ukupan broj vozila po traci.
        self.broj_po_traci = {
            naziv: 0
            for naziv in LINIJE_BROJANJA
        }

        # Brojanje po klasama za svaku traku.
        self.klase_po_traci = {
            naziv: defaultdict(int)
            for naziv in LINIJE_BROJANJA
        }


    # ========================================================
    # ORIJENTACIJA TRI TOCKE
    # ========================================================

    @staticmethod
    def orijentacija(a, b, c):

        """
        Izracunava orijentaciju tri tocke.

        Vrijednost predstavlja predznak
        vektorskog produkta.

        Koristi se za provjeru sijeku li se
        dva konacna segmenta.
        """

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

        """
        Provjerava nalazi li se tocka unutar
        granica konacnog segmenta uz malu toleranciju.
        """

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
    # SJECISTE DVIJU PRAVACA
    # ========================================================

    @staticmethod
    def izracunaj_sjeciste(
        a,
        b,
        c,
        d
    ):

        """
        Izracunava sjeciste pravca putanje vozila AB
        i pravca virtualne linije CD.

        Ako su pravci paralelni, vraca None.
        """

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

        Time se uklanja problem prethodne verzije,
        u kojoj se kratka linija matematicki ponasala
        kao beskonacna linija kroz cijeli kadar.
        """

        p1, p2 = linija

        # Strane virtualne linije na kojima se nalaze
        # prethodna i trenutna pozicija vozila.
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

        # Mora postojati stvarna promjena strane.
        if (
            strana_prethodna
            * strana_trenutna
            >= 0
        ):
            return False

        # Izracunava se tocno mjesto na kojem je
        # putanja vozila presjekla pravac linije.
        sjeciste = self.izracunaj_sjeciste(
            prethodna,
            trenutna,
            p1,
            p2
        )

        if sjeciste is None:
            return False

        # Najvaznija provjera:
        # sjeciste mora biti na stvarno nacrtanom
        # segmentu, a ne negdje na njegovu produzetku.
        if not self.tocka_na_segmentu(
            sjeciste,
            p1,
            p2
        ):
            return False

        # Dodatna provjera da se sjeciste nalazi i
        # izmedu prethodne i trenutne pozicije vozila.
        if not self.tocka_na_segmentu(
            sjeciste,
            prethodna,
            trenutna,
            tolerancija=5
        ):
            return False

        return True


    # ========================================================
    # PROVJERA PRELASKA
    # ========================================================

    def obradi_objekt(
        self,
        track_id,
        tocka,
        naziv_klase
    ):

        """
        Obraduje aktualnu bottom-center poziciju
        pracenog vozila.

        Vozilo se broji samo ako putanja njegove
        referentne tocke stvarno presijece jedan od
        kalibriranih konacnih segmenata.

        Jedan ByteTrack ID broji se samo jednom.
        """

        prethodna = (
            self.prethodna_tocka.get(
                track_id
            )
        )

        # Prvo opazanje vozila.
        if prethodna is None:

            self.prethodna_tocka[
                track_id
            ] = tocka

            return None

        # Ako je ID vec prebrojan, samo se
        # azurira njegova posljednja pozicija.
        if track_id in self.prebrojani_id:

            self.prethodna_tocka[
                track_id
            ] = tocka

            return None

        # Provjera svake fizicke prometne trake.
        for naziv_trake, linija in (
            LINIJE_BROJANJA.items()
        ):

            presao = (
                self.presjek_segmenata(
                    prethodna,
                    tocka,
                    linija
                )
            )

            if not presao:
                continue

            # ID se globalno oznacava kao prebrojan.
            self.prebrojani_id.add(
                track_id
            )

            # Povecanje broja za odgovarajucu traku.
            self.broj_po_traci[
                naziv_trake
            ] += 1

            # Evidencija stabilne klase.
            self.klase_po_traci[
                naziv_trake
            ][naziv_klase] += 1

            # Aktualna pozicija se pamti.
            self.prethodna_tocka[
                track_id
            ] = tocka

            return naziv_trake

        # Nije bilo prijelaza.
        self.prethodna_tocka[
            track_id
        ] = tocka

        return None


    # ========================================================
    # UKUPAN BROJ VOZILA
    # ========================================================

    def ukupno(self):

        return sum(
            self.broj_po_traci.values()
        )


    # ========================================================
    # BROJ ZA POJEDINU TRAKU
    # ========================================================

    def broj_trake(
        self,
        naziv_trake
    ):

        return self.broj_po_traci.get(
            naziv_trake,
            0
        )


    # ========================================================
    # STATISTIKA KLASA
    # ========================================================

    def statistika_klasa(
        self,
        naziv_trake
    ):

        return dict(
            self.klase_po_traci.get(
                naziv_trake,
                {}
            )
        )