from collections import Counter
from dataclasses import dataclass, field

from config import (
    MINIMALNO_FRAMEOVA_STABILNOG_IDA,
    MINIMALNO_FRAMEOVA_U_NOVOJ_ZONI,
    ZONE_ZA_IZVJESTAJ,
)
from zones import CIKLUS_REGIJA, status_prijelaza


@dataclass
class Vozilo:
    """Sve što znamo o jednom tracker ID-u."""

    track_id: int
    broj_frameova: int = 0
    klase: Counter = field(default_factory=Counter)
    maksimalna_pouzdanost: float = 0.0
    povijest_zona: list = field(default_factory=list)
    prvo_videno: str = ""
    zadnje_videno: str = ""
    zadnja_zona: str = ""
    zadnja_kruzna_zona: str = ""
    kandidat_zone: str = ""
    broj_frameova_kandidata: int = 0
    krivi_smjer: bool = False

    @property
    def najcesca_klasa(self):
        """Klasa koju je YOLO najčešće dodijelio ovom vozilu."""

        if not self.klase:
            return "nepoznato"
        return self.klase.most_common(1)[0][0]

    @property
    def posjecene_zone(self):
        """Zone u kojima je vozilo bilo, bez ponavljanja."""

        return list(dict.fromkeys(self.povijest_zona))

    @property
    def stabilan(self):
        """True kada je tracker pratio ID kroz dovoljno frameova."""

        return self.broj_frameova >= MINIMALNO_FRAMEOVA_STABILNOG_IDA

    def _potvrdi_zonu(self, zona):
        """Dodaje potvrđenu zonu i provjerava smjer kretanja."""

        self.povijest_zona.append(zona)
        self.zadnja_zona = zona
        self.kandidat_zone = ""
        self.broj_frameova_kandidata = 0

        # R5 i IZVAN ne prekidaju provjeru smjera između R1-R4.
        if zona in CIKLUS_REGIJA:
            if status_prijelaza(self.zadnja_kruzna_zona, zona) == "natrag":
                self.krivi_smjer = True
            self.zadnja_kruzna_zona = zona

    def azuriraj(self, naziv_klase, confidence, zona, vrijeme_videa):
        """Dodaje jednu detekciju. Vraća True kada se zona promijenila."""

        self.broj_frameova += 1
        self.klase[naziv_klase] += 1
        self.maksimalna_pouzdanost = max(
            self.maksimalna_pouzdanost,
            float(confidence),
        )

        if not self.prvo_videno:
            self.prvo_videno = vrijeme_videa
        self.zadnje_videno = vrijeme_videa

        if not self.zadnja_zona:
            self._potvrdi_zonu(zona)
            return True

        if zona == self.zadnja_zona:
            self.kandidat_zone = ""
            self.broj_frameova_kandidata = 0
            return False

        if zona != self.kandidat_zone:
            self.kandidat_zone = zona
            self.broj_frameova_kandidata = 1
            return False

        self.broj_frameova_kandidata += 1
        if self.broj_frameova_kandidata < MINIMALNO_FRAMEOVA_U_NOVOJ_ZONI:
            return False

        self._potvrdi_zonu(zona)
        return True


class Pracenje:
    """Čuva sva vozila koja je tracker pronašao."""

    def __init__(self):
        self.vozila = {}
        self.broj_ulazaka_u_zone = {zona: 0 for zona in ZONE_ZA_IZVJESTAJ}
        self.ukupno_detekcija = 0

    def obradi_objekt(self, track_id, naziv_klase, confidence, zona, vrijeme_videa):
        """
        Dodaje detekciju vozila i vraća poruku kada promijeni zonu.
        """

        self.ukupno_detekcija += 1

        if track_id not in self.vozila:
            self.vozila[track_id] = Vozilo(track_id)

        vozilo = self.vozila[track_id]
        prethodna_zona = vozilo.zadnja_zona or "NOVA DETEKCIJA"
        zona_promijenjena = vozilo.azuriraj(
            naziv_klase,
            confidence,
            zona,
            vrijeme_videa,
        )

        if not zona_promijenjena:
            return None

        self.broj_ulazaka_u_zone[zona] += 1
        putanja = " -> ".join(vozilo.povijest_zona)
        upozorenje = " | KRIVI SMJER!" if vozilo.krivi_smjer else ""

        return (
            f"ID {track_id:<3} ({vozilo.najcesca_klasa}) | "
            f"{prethodna_zona} -> {zona} | "
            f"zone: {putanja} | {vrijeme_videa}{upozorenje}"
        )
