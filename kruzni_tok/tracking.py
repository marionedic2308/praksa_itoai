from collections import defaultdict

from config import MINIMALNO_FRAMEOVA_PRACENJA, ZONE_ZA_IZVJESTAJ
from zones import status_prijelaza


class Pracenje:
    """
    Drži stanje praćenja objekata između frameova:
    povijest zona, brojeve ulazaka, pouzdanost i statistiku.
    """

    def __init__(self):
        self.prethodne_zone = {}
        self.povijest_zona = defaultdict(list)
        self.broj_frameova_po_idu = defaultdict(int)
        self.klase_po_idu = defaultdict(lambda: defaultdict(int))
        self.maksimalna_pouzdanost_po_idu = defaultdict(float)
        self.broj_ulazaka_u_zone = {zona: 0 for zona in ZONE_ZA_IZVJESTAJ}

        # True kad je za taj ID zabilježena vožnja krivim smjerom.
        self.krivi_smjer_po_idu = defaultdict(bool)

        self.ukupno_detekcija = 0
        self.odbačeno_premalih = 0

    def najcesca_klasa(self, track_id):
        """Najčešća klasa koju je model dodijelio tom ID-u."""

        if not self.klase_po_idu[track_id]:
            return "nepoznato"

        return max(
            self.klase_po_idu[track_id],
            key=self.klase_po_idu[track_id].get
        )

    def obradi_objekt(self, track_id, naziv_klase, confidence, zona, vrijeme_videa):
        """
        Ažurira stanje za jedan objekt. Vraca poruku za ispis
        kad objekt promijeni zonu (nakon što je stabilan), inače None.
        """

        self.ukupno_detekcija += 1
        self.broj_frameova_po_idu[track_id] += 1
        self.klase_po_idu[track_id][naziv_klase] += 1
        self.maksimalna_pouzdanost_po_idu[track_id] = max(
            self.maksimalna_pouzdanost_po_idu[track_id],
            float(confidence)
        )

        prethodna_zona = self.prethodne_zone.get(track_id)

        if (
            self.broj_frameova_po_idu[track_id] >= MINIMALNO_FRAMEOVA_PRACENJA
            and zona != prethodna_zona
        ):
            self.broj_ulazaka_u_zone[zona] += 1

            if (
                not self.povijest_zona[track_id]
                or self.povijest_zona[track_id][-1] != zona
            ):
                self.povijest_zona[track_id].append(zona)

            # Provjera smjera kretanja unutar kružnog toka.
            if status_prijelaza(prethodna_zona, zona) == "natrag":
                self.krivi_smjer_po_idu[track_id] = True

            poruka = (
                f"ID {track_id:<3} "
                f"({self.najcesca_klasa(track_id)}) | "
                f"{prethodna_zona or 'NOVA DETEKCIJA'} "
                f"-> {zona} | "
                f"conf {confidence:.2f} | "
                f"{vrijeme_videa}"
                f"{' | KRIVI SMJER!' if self.krivi_smjer_po_idu[track_id] else ''}"
            )

            self.prethodne_zone[track_id] = zona
            return poruka

        return None
