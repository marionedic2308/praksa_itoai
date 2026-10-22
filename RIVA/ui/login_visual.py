
import math

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient
from PySide6.QtWidgets import QWidget


class LoginVisual(QWidget):
    """RIVA Motion 4.0 - animirani prikaz AI obrade prometa."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 280)

        self.frame = 0
        self.total_frames = 240

        self.stages = [
            ("AI DETEKCIJA", "#5DD9D0"),
            ("PRAĆENJE", "#8DAFF5"),
            ("OCR", "#F2C47B"),
            ("IZVJEŠTAJ", "#BBA0EE"),
        ]

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(33)

    def advance(self):
        self.frame = (self.frame + 1) % self.total_frames
        if self.isVisible():
            self.update()

    def label(self, p, rect, value, size=10,
              color="#EAF2FA", bold=False,
              align=Qt.AlignLeft | Qt.AlignVCenter):
        font = QFont("Segoe UI", size)
        font.setBold(bold)
        p.setFont(font)
        p.setPen(QColor(color))
        p.drawText(rect, align, value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        t = self.frame / self.total_frames
        stage = min(3, int(t * 4))

        p.fillRect(self.rect(), QColor("#101D30"))

        self.draw_scene(p, w, h, t, stage)
        self.draw_progress(p, w, h, t, stage)

        p.end()

    def draw_header(self, p, w):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#15283B"))
        p.drawRoundedRect(QRectF(0, 0, w, 45), 9, 9)

        self.label(
            p, QRectF(16, 6, w - 150, 22),
            "RIVA AI  /  OBRADA PROMETA",
            12, "#EAF2FA", True
        )

        self.label(
            p, QRectF(16, 26, w - 150, 15),
            "Detekcija, praćenje, OCR i izvještavanje",
            9, "#91A6BE"
        )

        alpha = 140 + int(
            115 * abs(math.sin(self.frame * 0.12))
        )

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(93, 217, 208, alpha))
        p.drawEllipse(QPointF(w - 91, 22), 4, 4)

        self.label(
            p, QRectF(w - 81, 11, 75, 22),
            "AI DEMO", 9, "#A5E8DF", True
        )

    def draw_scene(self, p, w, h, t, stage):
        top = 5
        bottom = h - 55
        scene_h = max(155, bottom - top)

        p.setPen(QPen(QColor("#355065"), 1))
        p.setBrush(QColor("#16283A"))
        p.drawRoundedRect(
            QRectF(0, top, w, scene_h), 10, 10
        )

        road_x = 14
        road_y = top + 29
        road_w = w * 0.61
        road_h = scene_h - 55

        gradient = QLinearGradient(
            road_x, road_y, road_x, road_y + road_h
        )
        gradient.setColorAt(0, QColor("#34444C"))
        gradient.setColorAt(0.5, QColor("#293A43"))
        gradient.setColorAt(1, QColor("#34444C"))

        road = QRectF(road_x, road_y, road_w, road_h)

        p.setPen(Qt.NoPen)
        p.setBrush(gradient)
        p.drawRoundedRect(road, 7, 7)

        p.setPen(QPen(QColor("#D8D9C7"), 1.5))
        p.drawLine(
            QPointF(road.left() + 5, road.top() + 6),
            QPointF(road.right() - 5, road.top() + 6)
        )
        p.drawLine(
            QPointF(road.left() + 5, road.bottom() - 6),
            QPointF(road.right() - 5, road.bottom() - 6)
        )

        p.setPen(QPen(
            QColor("#E4DAB8"), 1.5, Qt.DashLine
        ))
        p.drawLine(
            QPointF(road.left() + 5, road.center().y()),
            QPointF(road.right() - 5, road.center().y())
        )

        # RIVA_LANE_FIX_V1
        # Two lanes with a vehicle centered inside L1.
        lane_height = road.height() / 2.0

        # Lane labels remain visible and do not overlap the car.
        self.label(
            p,
            QRectF(road.left() + 12, road.top() + 9, 45, 18),
            "L2", 10, "#8DAFF5", True
        )
        self.label(
            p,
            QRectF(road.left() + 12,
                   road.center().y() + 9, 45, 18),
            "L1", 10, "#5DD9D0", True
        )

        # Car dimensions adapt to the lane height.
        car_h = max(15.0, min(34.0, lane_height * 0.56))
        car_w = car_h * 2.05

        travel = min(1.0, t * 1.35)
        cx = road.left() - car_w + travel * (
            road.width() + car_w * 2
        )
        cy = road.top() + lane_height * 1.5

        car = QRectF(
            cx - car_w / 2,
            cy - car_h / 2,
            car_w,
            car_h
        )

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 65))
        p.drawRoundedRect(
            car.translated(3, 3), 9, 9
        )

        p.setBrush(QColor("#398FC5"))
        p.setPen(QPen(QColor("#B5DDEB"), 1))
        p.drawRoundedRect(car, 9, 9)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#A6D8E9"))
        p.drawRoundedRect(
            QRectF(
                cx - car_w * 0.15,
                cy - car_h * 0.37,
                car_w * 0.40,
                car_h * 0.74
            ),
            4, 4
        )

        p.setBrush(QColor("#FFE8AD"))
        p.drawEllipse(
            QPointF(cx + car_w * 0.43,
                    cy - car_h * 0.28), 2.5, 2.5
        )
        p.drawEllipse(
            QPointF(cx + car_w * 0.43,
                    cy + car_h * 0.28), 2.5, 2.5
        )

        # AI detekcija prati vozilo.
        if t >= 0.10 and t <= 0.77:
            box = car.adjusted(-8, -8, 8, 8)

            p.setPen(QPen(QColor("#5DD9D0"), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(box, 5, 5)

            self.label(
                p,
                QRectF(box.left(), box.top() - 22, 125, 20),
                "AI  /  VOZILO",
                9, "#5DD9D0", True
            )

        # Linija brojanja.
        line_x = road.left() + road.width() * 0.54

        p.setPen(QPen(QColor("#8DAFF5"), 1.5, Qt.DashLine))
        p.drawLine(
            QPointF(line_x, road.top() + 8),
            QPointF(line_x, road.bottom() - 8)
        )

        if stage >= 1:
            p.setPen(QPen(QColor("#5DD9D0"), 2))
            p.drawLine(
                QPointF(max(road.left() + 8, cx - 70), cy),
                QPointF(cx - 48, cy)
            )

        # Desna informacijska kartica.
        card_x = road.right() + 12
        card_w = w - card_x - 14
        card = QRectF(
            card_x, road_y, card_w, road_h
        )

        p.setPen(QPen(QColor("#456276"), 1))
        p.setBrush(QColor("#102335"))
        p.drawRoundedRect(card, 8, 8)

        titles = [
            "AI DETEKCIJA",
            "PRAĆENJE",
            "OCR OBRADA",
            "IZVJEŠTAJ",
        ]

        details = [
            ("Prepoznato vozilo", "Klasifikacija objekta"),
            ("Praćenje putanje", "Brojanje i smjer"),
            ("Očitanje oznake", "OCR prepoznavanje"),
            ("Prometna statistika", "PDF dokument"),
        ]

        accent = self.stages[stage][1]

        self.label(
            p, QRectF(card_x + 13, road_y + 12,
                      card_w - 20, 22),
            titles[stage], 11, accent, True
        )

        self.label(
            p, QRectF(card_x + 13, road_y + 45,
                      card_w - 20, 20),
            details[stage][0],
            10, "#EDF4F8", True
        )

        self.label(
            p, QRectF(card_x + 13, road_y + 65,
                      card_w - 20, 20),
            details[stage][1],
            9, "#9CB2C4"
        )

        # Prikaz aktivne obrade.
        local = (t * 4) % 1.0

        if stage == 2:
            plate = QRectF(
                card_x + 13, road_y + 100,
                max(70, card_w - 26), 32
            )

            p.setBrush(QColor("#E6EDF2"))
            p.setPen(QPen(QColor("#F2C47B"), 2))
            p.drawRoundedRect(plate, 4, 4)

            self.label(
                p, plate,
                "OCR  /  DEMO",
                10, "#203341", True,
                Qt.AlignCenter
            )

            scan_x = plate.left() + (
                plate.width() - 5
            ) * local

            p.setPen(QPen(QColor("#E0A744"), 2))
            p.drawLine(
                QPointF(scan_x, plate.top() + 3),
                QPointF(scan_x, plate.bottom() - 3)
            )

        elif stage == 3:
            bx = card_x + 15
            by = road_y + 106

            for i, value in enumerate(
                (0.85, 0.52, 0.96)
            ):
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(
                    ("#5DD9D0", "#8DAFF5", "#F2C47B")[i]
                ))
                p.drawRoundedRect(
                    QRectF(
                        bx + i * 27,
                        by + 32 * (1 - value),
                        16,
                        32 * value * min(1, local * 3)
                    ),
                    3, 3
                )

            self.label(
                p, QRectF(card_x + 13, by + 40,
                          card_w - 20, 20),
                "PDF  /  SPREMAN",
                9, "#BBA0EE", True
            )

        else:
            track = QRectF(
                card_x + 13, road_y + 108,
                max(30, card_w - 26), 7
            )

            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#294357"))
            p.drawRoundedRect(track, 3, 3)

            p.setBrush(QColor(accent))
            p.drawRoundedRect(
                QRectF(
                    track.left(), track.top(),
                    track.width() * max(0.04, local),
                    track.height()
                ),
                3, 3
            )

    def draw_progress(self, p, w, h, t, stage):
        labels = [
            "DETEKCIJA",
            "PRAĆENJE",
            "OCR",
            "IZVJEŠTAJ",
        ]

        colors = [
            "#5DD9D0",
            "#8DAFF5",
            "#F2C47B",
            "#BBA0EE",
        ]

        gap = 8
        item_w = (w - gap * 3) / 4
        y = h - 38

        for index, name in enumerate(labels):
            x = index * (item_w + gap)

            p.setPen(Qt.NoPen)
            p.setBrush(QColor(
                colors[index]
                if index <= stage else "#2C4559"
            ))

            p.drawRoundedRect(
                QRectF(x, y, item_w, 4),
                2, 2
            )

            self.label(
                p,
                QRectF(x, y + 9, item_w, 20),
                name,
                11,
                "#DDEAF3",
                True
            )

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)
