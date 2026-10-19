
import json
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QMessageBox,
    QScrollArea,
)


# ============================================================
# RIVA - KALIBRACIJA VIRTUALNIH LINIJA
# ============================================================
#
# Svaka prometna traka ima dvije linije:
# L1 - prva linija očekivanog smjera
# L2 - druga linija očekivanog smjera
#
# Koordinate se spremaju u originalnoj rezoluciji.
# ============================================================


class CalibrationCanvas(QLabel):

    line_drawn = Signal(tuple)

    def __init__(self, frame):
        super().__init__()

        self.original_frame = frame.copy()
        self.original_height, self.original_width = frame.shape[:2]

        self.lines = []
        self.start_point = None
        self.current_point = None

        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

        self.setStyleSheet("""
            background-color: #091321;
            border: 1px solid #35516B;
            border-radius: 8px;
        """)

        self.setMinimumSize(400, 260)

        self.update_image()

    def _image_rect(self):
        """Izračunava stvarni položaj slike unutar QLabela."""

        available_width = max(1, self.width())
        available_height = max(1, self.height())

        scale = min(
            available_width / self.original_width,
            available_height / self.original_height
        )

        display_width = max(
            1, round(self.original_width * scale)
        )
        display_height = max(
            1, round(self.original_height * scale)
        )

        offset_x = (available_width - display_width) // 2
        offset_y = (available_height - display_height) // 2

        return (
            offset_x,
            offset_y,
            display_width,
            display_height
        )

    def _to_original(self, position):
        """Pretvara koordinate miša u koordinate videoizvora."""

        offset_x, offset_y, width, height = self._image_rect()

        x = position.x() - offset_x
        y = position.y() - offset_y

        if not (0 <= x < width and 0 <= y < height):
            return None

        original_x = round(
            x * self.original_width / width
        )
        original_y = round(
            y * self.original_height / height
        )

        return (
            min(self.original_width - 1, original_x),
            min(self.original_height - 1, original_y)
        )

    def update_image(self):

        import cv2

        rgb = cv2.cvtColor(
            self.original_frame,
            cv2.COLOR_BGR2RGB
        )

        height, width, channels = rgb.shape

        image = QImage(
            rgb.data,
            width,
            height,
            channels * width,
            QImage.Format_RGB888
        ).copy()

        canvas = QPixmap.fromImage(image)

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing)

        for index, (line, color, label) in enumerate(self.lines):

            start, end = line

            painter.setPen(
                QPen(QColor(color), 5)
            )

            painter.drawLine(
                QPoint(*start),
                QPoint(*end)
            )

            painter.setPen(
                QPen(QColor("#FFFFFF"), 2)
            )

            painter.drawText(
                start[0] + 8,
                max(20, start[1] - 10),
                label
            )

        if self.start_point is not None and self.current_point is not None:

            painter.setPen(
                QPen(QColor("#FFFFFF"), 3, Qt.DashLine)
            )

            painter.drawLine(
                QPoint(*self.start_point),
                QPoint(*self.current_point)
            )

        painter.end()

        self.setPixmap(
            canvas.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image()

    def mousePressEvent(self, event):

        if event.button() != Qt.LeftButton:
            return

        point = self._to_original(
            event.position().toPoint()
        )

        if point is None:
            return

        self.start_point = point
        self.current_point = point

    def mouseMoveEvent(self, event):

        if self.start_point is None:
            return

        point = self._to_original(
            event.position().toPoint()
        )

        if point is not None:
            self.current_point = point
            self.update_image()

    def mouseReleaseEvent(self, event):

        if event.button() != Qt.LeftButton:
            return

        if self.start_point is None:
            return

        end_point = self._to_original(
            event.position().toPoint()
        )

        start_point = self.start_point

        self.start_point = None
        self.current_point = None

        if end_point is None or end_point == start_point:
            self.update_image()
            return

        self.line_drawn.emit(
            (start_point, end_point)
        )

    def add_line(self, line, color, label):

        self.lines.append(
            (line, color, label)
        )

        self.update_image()

    def remove_last_line(self):

        if self.lines:
            self.lines.pop()
            self.update_image()


class LineCalibrationDialog(QDialog):

    calibration_saved = Signal(list)

    COLORS = [
        ("#5DD9D0", "#168C86"),
        ("#FFD166", "#C58B2B"),
        ("#A78BFA", "#7954CC"),
        ("#FB7185", "#C4475B"),
        ("#60A5FA", "#3177CB"),
        ("#4ADE80", "#259C53"),
    ]

    def __init__(self, frame, save_path=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            "RIVA | Kalibracija prometnih traka"
        )

        self.resize(1150, 760)
        self.setMinimumSize(700, 520)

        self.save_path = Path(save_path) if save_path else None

        self.lanes = []
        self.pending_line = None

        self.canvas = CalibrationCanvas(frame)
        self.canvas.line_drawn.connect(
            self.handle_line
        )

        self.build_ui()
        self.update_status()

    def build_ui(self):

        self.setStyleSheet("""
            QDialog {
                background-color: #0D1829;
                color: #F2F7FC;
            }
            QLabel {
                color: #E5F0F8;
            }
            QPushButton {
                background-color: #233A52;
                color: #FFFFFF;
                border: 1px solid #36516A;
                border-radius: 9px;
                padding: 11px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30516E;
            }
            QPushButton:disabled {
                background-color: #192A3B;
                color: #74869A;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel(
            "KALIBRACIJA PROMETNIH TRAKA"
        )
        title.setStyleSheet("""
            font-size: 23px;
            font-weight: bold;
            color: #FFFFFF;
        """)

        subtitle = QLabel(
            "Mišem povuci liniju L1, zatim L2. "
            "Svaka prometna traka mora imati obje linije."
        )
        subtitle.setStyleSheet(
            "color: #91A6BE; font-size: 12px;"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addWidget(self.canvas, 1)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            color: #5DD9D0;
            font-size: 13px;
            font-weight: bold;
        """)

        layout.addWidget(self.status_label)

        self.lanes_label = QLabel()
        self.lanes_label.setWordWrap(True)
        self.lanes_label.setStyleSheet("""
            color: #AFC1D4;
            font-size: 12px;
        """)

        layout.addWidget(self.lanes_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        self.undo_button = QPushButton(
            "↶  Poništi posljednju liniju"
        )
        self.undo_button.clicked.connect(
            self.undo_last
        )

        self.clear_button = QPushButton(
            "Obriši sve"
        )
        self.clear_button.clicked.connect(
            self.clear_all
        )

        self.save_button = QPushButton(
            "✓  Spremi kalibraciju"
        )
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #168C86;
                color: white;
                border: none;
                border-radius: 9px;
                padding: 11px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1AA59D;
            }
        """)
        self.save_button.clicked.connect(
            self.save_calibration
        )

        buttons.addWidget(self.undo_button)
        buttons.addWidget(self.clear_button)
        buttons.addStretch()
        buttons.addWidget(self.save_button)

        layout.addLayout(buttons)

    def handle_line(self, line):

        lane_index = len(self.lanes)

        if self.pending_line is None:

            color = self.COLORS[
                lane_index % len(self.COLORS)
            ][0]

            self.pending_line = line

            self.canvas.add_line(
                line,
                color,
                f"Traka {lane_index + 1} - L1"
            )

        else:

            color = self.COLORS[
                lane_index % len(self.COLORS)
            ][1]

            lane = {
                "name": f"Traka {lane_index + 1}",
                "line_1": self.pending_line,
                "line_2": line
            }

            self.lanes.append(lane)
            self.pending_line = None

            self.canvas.add_line(
                line,
                color,
                f"Traka {lane_index + 1} - L2"
            )

        self.update_status()

    def undo_last(self):

        if self.pending_line is not None:

            self.pending_line = None
            self.canvas.remove_last_line()

        elif self.lanes:

            last_lane = self.lanes.pop()

            self.canvas.remove_last_line()

            self.pending_line = last_lane["line_1"]

        self.update_status()

    def clear_all(self):

        self.lanes.clear()
        self.pending_line = None
        self.canvas.lines.clear()
        self.canvas.update_image()

        self.update_status()

    def update_status(self):

        lane_number = len(self.lanes) + 1

        if self.pending_line is None:

            self.status_label.setText(
                f"SLJEDEĆE: Traka {lane_number} — nacrtaj L1"
            )

        else:

            self.status_label.setText(
                f"SLJEDEĆE: Traka {lane_number} — nacrtaj L2"
            )

        if self.lanes:

            names = ", ".join(
                lane["name"]
                for lane in self.lanes
            )

            self.lanes_label.setText(
                f"Završene trake ({len(self.lanes)}): {names}"
            )

        else:

            self.lanes_label.setText(
                "Još nema potpuno kalibriranih prometnih traka."
            )

    def save_calibration(self):

        if self.pending_line is not None:

            QMessageBox.warning(
                self,
                "Nedovršena traka",
                "Prije spremanja nacrtaj i drugu liniju (L2)."
            )
            return

        if not self.lanes:

            QMessageBox.warning(
                self,
                "Nema kalibracije",
                "Potrebno je nacrtati barem jednu prometnu traku."
            )
            return

        if self.save_path is not None:

            try:

                self.save_path.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                data = {
                    "version": 1,
                    "frame_width": self.canvas.original_width,
                    "frame_height": self.canvas.original_height,
                    "lanes": self.lanes
                }

                with open(
                    self.save_path,
                    "w",
                    encoding="utf-8"
                ) as file:

                    json.dump(
                        data,
                        file,
                        ensure_ascii=False,
                        indent=4
                    )

            except OSError:

                QMessageBox.warning(
                    self,
                    "Pogreška spremanja",
                    "Kalibraciju nije moguće spremiti."
                )
                return

        self.calibration_saved.emit(
            list(self.lanes)
        )

        self.accept()
