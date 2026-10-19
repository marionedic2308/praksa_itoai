
from collections import Counter
from datetime import datetime, timedelta


# ============================================================
# RIVA - BROJANJE VOZILA I ODREĐIVANJE SMJERA
# ============================================================
#
# Temeljeno na:
# TEST 09 / FAZA 04 - Brojanje vozila
# TEST 09 / FAZA 05 - Određivanje smjera
#
# L1 -> L2 = ISPRAVAN SMJER
# L2 -> L1 = SUPROTAN SMJER
#
# Koristi donju središnju točku okvira vozila.
# ============================================================


class VehicleCounter:

    def __init__(self, lanes, segment_tolerance=35):

        # Konfiguracija prometnih traka.
        self.lanes = self._validate_lanes(lanes)

        # Dopuštena tolerancija oko krajeva linije.
        self.segment_tolerance = float(segment_tolerance)

        if self.segment_tolerance < 0:
            raise ValueError(
                "Tolerancija segmenta ne može biti negativna."
            )

        # Posljednja pozicija svakog ByteTrack ID-a.
        self.previous_positions = {}

        # Prvi potvrđeni prijelaz pojedinog vozila.
        self.entered = {}

        # ID oznake s potvrđenim kompletnim prolaskom.
        self.counted_ids = set()

        # Ukupna statistika.
        self.total_count = 0
        self.correct_count = 0
        self.opposite_count = 0

        # Statistika po prometnim trakama.
        self.lane_counts = Counter()
        self.correct_by_lane = Counter()
        self.opposite_by_lane = Counter()

        # Statistika po kategorijama.
        self.category_counts = Counter()

        # Statistika kategorija po traci i smjeru.
        self.category_by_lane_direction = Counter()

        # Evidencija potvrđenih prolazaka.
        self.events = []

    # ========================================================
    # PROVJERA KONFIGURACIJE TRAKA
    # ========================================================

    @staticmethod
    def _validate_lanes(lanes):

        if not isinstance(lanes, (list, tuple)):
            raise ValueError(
                "Prometne trake moraju biti zadane popisom."
            )

        if not lanes:
            raise ValueError(
                "Potrebno je definirati barem jednu traku."
            )

        validated = []
        used_names = set()

        for lane in lanes:

            name = lane["name"]

            if not isinstance(name, str) or not name.strip():
                raise ValueError(
                    "Svaka traka mora imati naziv."
                )

            if name in used_names:
                raise ValueError(
                    f"Dupliciran naziv prometne trake: {name}"
                )

            used_names.add(name)

            line_1 = lane["line_1"]
            line_2 = lane["line_2"]

            for line in (line_1, line_2):

                if len(line) != 2:
                    raise ValueError(
                        "Linija mora imati dvije krajnje točke."
                    )

                if len(line[0]) != 2 or len(line[1]) != 2:
                    raise ValueError(
                        "Svaka točka mora imati X i Y koordinatu."
                    )

                if tuple(line[0]) == tuple(line[1]):
                    raise ValueError(
                        "Početak i kraj linije ne smiju biti isti."
                    )

            validated.append({
                "name": name,
                "line_1": (
                    tuple(line_1[0]),
                    tuple(line_1[1])
                ),
                "line_2": (
                    tuple(line_2[0]),
                    tuple(line_2[1])
                )
            })

        return validated

    # ========================================================
    # REFERENTNA TOČKA VOZILA
    # ========================================================

    @staticmethod
    def vehicle_point(vehicle):
        """Donja središnja točka bounding boxa."""

        x1, y1, x2, y2 = vehicle["bbox"]

        return (
            (x1 + x2) / 2.0,
            float(y2)
        )

    # ========================================================
    # GEOMETRIJA - VEKTORSKI PRODUKT
    # ========================================================

    @staticmethod
    def orientation(a, b, c):

        return (
            (b[0] - a[0]) * (c[1] - a[1])
            -
            (b[1] - a[1]) * (c[0] - a[0])
        )

    # ========================================================
    # PRESJEK PUTANJE I VIRTUALNE LINIJE
    # ========================================================

    def _intersection_parameter(
        self,
        previous,
        current,
        line
    ):
        """
        Vraća položaj presjeka na putanji vozila.

        t = 0 -> prethodna pozicija
        t = 1 -> trenutačna pozicija

        Ako nema stvarnog presjeka segmenta,
        vraća None.

        Parametar t omogućuje određivanje redoslijeda
        prelaska L1 i L2 između dva kadra.
        """

        a, b = line

        px, py = previous
        qx, qy = current

        ax, ay = a
        bx, by = b

        rx = qx - px
        ry = qy - py

        sx = bx - ax
        sy = by - ay

        denominator = rx * sy - ry * sx

        if abs(denominator) < 1e-9:
            return None

        apx = ax - px
        apy = ay - py

        t = (
            apx * sy - apy * sx
        ) / denominator

        u = (
            apx * ry - apy * rx
        ) / denominator

        # Presjek mora biti između dvije pozicije vozila.
        if not (0.0 <= t <= 1.0):
            return None

        # Tolerancija oko krajeva virtualne linije
        # izražena je u pikselima duž segmenta.
        line_length = (sx * sx + sy * sy) ** 0.5

        tolerance_ratio = (
            self.segment_tolerance / line_length
        )

        if not (
            -tolerance_ratio
            <= u
            <= 1.0 + tolerance_ratio
        ):
            return None

        # Kao u Testu 09, zahtijevamo promjenu strane.
        side_before = self.orientation(
            a, b, previous
        )

        side_after = self.orientation(
            a, b, current
        )

        if side_before * side_after >= 0:
            return None

        return t

    # ========================================================
    # PRONALAZAK I SORTIRANJE PRIJEĐENIH LINIJA
    # ========================================================

    def _find_crossings(self, previous, current):

        crossings = []

        for lane in self.lanes:

            for line_name, key in (
                ("L1", "line_1"),
                ("L2", "line_2")
            ):

                t = self._intersection_parameter(
                    previous,
                    current,
                    lane[key]
                )

                if t is not None:

                    crossings.append({
                        "lane": lane["name"],
                        "line": line_name,
                        "t": t
                    })

        # Presjeci se obrađuju stvarnim redoslijedom
        # kretanja vozila, ne redoslijedom konfiguracije.
        crossings.sort(
            key=lambda crossing: crossing["t"]
        )

        return crossings

    # ========================================================
    # VRIJEME PRELASKA
    # ========================================================

    @staticmethod
    def _parse_timestamp(timestamp):

        if timestamp is None:
            return datetime.now().astimezone()

        if isinstance(timestamp, datetime):
            return timestamp

        if isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp)

        raise TypeError(
            "Vrijeme mora biti datetime ili ISO tekst."
        )

    @staticmethod
    def _crossing_time(
        previous_time,
        current_time,
        t
    ):
        """
        Procjena trenutka prelaska između dva kadra.

        Vrijeme se linearno interpolira prema položaju
        presjeka na putanji vozila.
        """

        if previous_time is None:
            return current_time

        return (
            previous_time
            +
            (current_time - previous_time) * t
        )

    # ========================================================
    # OBRADA PRIJELAZA JEDNE LINIJE
    # ========================================================

    def _process_crossing(
        self,
        track_id,
        lane_name,
        line_name,
        crossing_time,
        vehicle_type
    ):

        # Već završen ID ne brojimo ponovno.
        if track_id in self.counted_ids:
            return None

        state = self.entered.get(track_id)

        # Prvi prijelaz.
        if state is None:

            self.entered[track_id] = {
                "lane": lane_name,
                "first_line": line_name,
                "first_time": crossing_time
            }

            return None

        # Obje linije moraju pripadati istoj traci.
        if state["lane"] != lane_name:
            return None

        # Ponovni prijelaz iste linije ignoriramo.
        if state["first_line"] == line_name:
            return None

        first_line = state["first_line"]

        if first_line == "L1" and line_name == "L2":
            direction = "ISPRAVAN SMJER"
        elif first_line == "L2" and line_name == "L1":
            direction = "SUPROTAN SMJER"
        else:
            return None

        duration = (
            crossing_time - state["first_time"]
        ).total_seconds()

        # Evidentiramo samo kronološki valjan prolazak.
        if duration < 0:
            return None

        event = {
            "track_id": track_id,
            "lane": lane_name,
            "vehicle_type": vehicle_type,
            "first_line": first_line,
            "second_line": line_name,
            "entered_at": state["first_time"].isoformat(
                timespec="milliseconds"
            ),
            "counted_at": crossing_time.isoformat(
                timespec="milliseconds"
            ),
            "duration_seconds": round(duration, 3),
            "direction": direction
        }

        self.events.append(event)
        self.counted_ids.add(track_id)

        self.total_count += 1
        self.lane_counts[lane_name] += 1
        self.category_counts[vehicle_type] += 1

        self.category_by_lane_direction[
            (lane_name, direction, vehicle_type)
        ] += 1

        if direction == "ISPRAVAN SMJER":

            self.correct_count += 1
            self.correct_by_lane[lane_name] += 1

        else:

            self.opposite_count += 1
            self.opposite_by_lane[lane_name] += 1

        self.entered.pop(track_id, None)

        return event

    # ========================================================
    # GLAVNA OBRADA KADRA
    # ========================================================

    def update(self, vehicles, timestamp=None):
        """
        Prima popis vozila iz VehicleTracker.track().

        Vraća samo nove potvrđene događaje.
        """

        current_time = self._parse_timestamp(
            timestamp
        )

        new_events = []

        for vehicle in vehicles:

            track_id = int(vehicle["track_id"])

            current_point = self.vehicle_point(
                vehicle
            )

            vehicle_type = vehicle.get(
                "stable_type",
                vehicle.get(
                    "vehicle_type",
                    "Nepoznato"
                )
            )

            previous_record = (
                self.previous_positions.get(track_id)
            )

            # Prvi kadar u kojem vidimo ovaj ID.
            if previous_record is None:

                self.previous_positions[track_id] = {
                    "point": current_point,
                    "time": current_time
                }

                continue

            previous_point = previous_record["point"]
            previous_time = previous_record["time"]

            # Pronalaženje svih stvarnih presjeka.
            crossings = self._find_crossings(
                previous_point,
                current_point
            )

            for crossing in crossings:

                crossing_time = self._crossing_time(
                    previous_time,
                    current_time,
                    crossing["t"]
                )

                event = self._process_crossing(
                    track_id=track_id,
                    lane_name=crossing["lane"],
                    line_name=crossing["line"],
                    crossing_time=crossing_time,
                    vehicle_type=vehicle_type
                )

                if event is not None:
                    new_events.append(event)
                    break

            # Pamćenje trenutačne pozicije i vremena.
            self.previous_positions[track_id] = {
                "point": current_point,
                "time": current_time
            }

        return new_events

    # ========================================================
    # UKLANJANJE NEAKTIVNIH ID OZNAKA
    # ========================================================

    def remove_inactive(self, track_ids):
        """
        Uklanja privremene podatke neaktivnih vozila.

        Završene ID oznake ostaju u counted_ids
        kako isti ID ne bi bio ponovno prebrojan.
        """

        for track_id in track_ids:

            self.previous_positions.pop(
                track_id,
                None
            )

            self.entered.pop(
                track_id,
                None
            )

    # ========================================================
    # STATISTIKA
    # ========================================================

    def get_statistics(self):

        return {
            "total_count": self.total_count,
            "correct_count": self.correct_count,
            "opposite_count": self.opposite_count,
            "lane_counts": dict(self.lane_counts),
            "correct_by_lane": dict(
                self.correct_by_lane
            ),
            "opposite_by_lane": dict(
                self.opposite_by_lane
            ),
            "category_counts": dict(
                self.category_counts
            ),
            "events": list(self.events)
        }
