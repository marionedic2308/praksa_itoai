# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# FAZA 04 - BROJANJE VOZILA PRELASKOM PREKO VIRTUALNIH LINIJA
# ============================================================

from collections import defaultdict


# ============================================================
# KALIBRIRANE LINIJE
# Koordinate su u originalnoj rezoluciji videoizvora.
# ============================================================

LINIJE_BROJANJA = {
    "Traka 1": ((1712, 418), (1842, 428)),
    "Traka 2": ((852, 1116), (1528, 1427)),
}


# ============================================================
# KLASA ZA BROJANJE
# ============================================================

class BrojanjeVozila:

    def __init__(self):

        # Posljednja poznata strana linije za svaki ID.
        #
        # Primjer:
        # prethodna_strana["Traka 1"][15] = -1
        self.prethodna_strana = {
            naziv: {}
            for naziv in LINIJE_BROJANJA
        }

        # ID-evi koji su vec prebrojani na pojedinoj liniji.
        #
        # Isti ID ne moze se vise puta brojiti
        # na istoj traci.
        self.prebrojani_id = {
            naziv: set()
            for naziv in LINIJE_BROJANJA
        }

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
    # ODREDIVANJE STRANE LINIJE
    # ========================================================

    @staticmethod
    def strana_linije(tocka, linija):

        """
        Odreduje s koje strane virtualne linije
        se nalazi zadana tocka.

        Koristi se predznak vektorskog produkta.

        Rezultat:
            > 0  jedna strana linije
            < 0  druga strana linije
            = 0  tocka je na liniji
        """

        x, y = tocka

        (x1, y1), (x2, y2) = linija

        return (
            (x2 - x1) * (y - y1)
            -
            (y2 - y1) * (x - x1)
        )


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
        Obraduje jednu pracenu poziciju vozila.

        Ako se predznak strane linije promijeni,
        smatra se da je praceni objekt presao
        virtualnu liniju.

        Funkcija vraca naziv trake ako je
        zabiljezen NOVI prijelaz.

        Ako prijelaza nema, vraca None.
        """

        for naziv_trake, linija in LINIJE_BROJANJA.items():

            trenutna_strana = self.strana_linije(
                tocka,
                linija
            )

            prethodna = self.prethodna_strana[
                naziv_trake
            ].get(track_id)

            # Prvo opazanje ID-a u odnosu na ovu liniju.
            if prethodna is None:

                self.prethodna_strana[
                    naziv_trake
                ][track_id] = trenutna_strana

                continue

            # Provjera promjene strane linije.
            presao_liniju = (
                prethodna * trenutna_strana < 0
            )

            # Sprema se aktualna strana za sljedeci frame.
            self.prethodna_strana[
                naziv_trake
            ][track_id] = trenutna_strana

            if not presao_liniju:
                continue

            # Isti ID ne brojimo ponovno
            # na istoj virtualnoj liniji.
            if track_id in self.prebrojani_id[naziv_trake]:
                continue

            self.prebrojani_id[
                naziv_trake
            ].add(track_id)

            self.broj_po_traci[
                naziv_trake
            ] += 1

            self.klase_po_traci[
                naziv_trake
            ][naziv_klase] += 1

            return naziv_trake

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

    def broj_trake(self, naziv_trake):

        return self.broj_po_traci.get(
            naziv_trake,
            0
        )


    # ========================================================
    # STATISTIKA KLASA
    # ========================================================

    def statistika_klasa(self, naziv_trake):

        return dict(
            self.klase_po_traci.get(
                naziv_trake,
                {}
            )
        )