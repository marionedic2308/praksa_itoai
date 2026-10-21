from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QLineEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QStackedWidget, QGridLayout, QScrollArea, QSizePolicy,
    QDialog
)
from PySide6.QtGui import QPainter, QPen, QColor, QFont

from core.audit import get_recent_events



class ActivityTile(QFrame):
    clicked = Signal()

    def __init__(self, index, title, description):
        super().__init__()
        self.index = index
        self.hovered = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(178)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMouseTracking(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(23, 20, 23, 20)
        layout.setSpacing(7)

        top = QHBoxLayout()
        top.setSpacing(12)

        self.icon = QLabel()
        self.icon.setFixedSize(43, 43)
        self.icon.setAlignment(Qt.AlignCenter)
        top.addWidget(self.icon)

        top.addStretch()

        arrow = QLabel(chr(0x2197))
        arrow.setStyleSheet(
            "color: #91A6BE; font-size: 20px; border: none;"
        )
        top.addWidget(arrow)

        layout.addLayout(top)
        layout.addSpacing(3)

        heading = QLabel(title)
        heading.setStyleSheet(
            "color: #F2F7FC; font-size: 16px;"
            "font-weight: bold; border: none;"
        )
        layout.addWidget(heading)

        info = QLabel(description)
        info.setStyleSheet(
            "color: #91A6BE; font-size: 12px; border: none;"
        )
        layout.addWidget(info)

        layout.addStretch()

        action = QLabel("OTVORI EVIDENCIJU  " + chr(0x2192))
        action.setStyleSheet(
            "color: #5DD9D0; font-size: 11px;"
            "font-weight: bold; border: none;"
        )
        layout.addWidget(action)

        self.setStyleSheet("""
            ActivityTile {
                background: #152238;
                border: 1px solid #294158;
                border-radius: 16px;
            }
            ActivityTile:hover {
                background: #1C3046;
                border: 1px solid #5DD9D0;
            }
        """)

        self.draw_icon()

    def draw_icon(self):
        from PySide6.QtGui import QPixmap

        pixmap = QPixmap(43, 43)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        color = "#F2BA61" if self.index == 1 else "#5DD9D0"
        painter.setBrush(QColor(
            "#45372C" if self.index == 1 else "#1C4651"
        ))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 42, 42, 11, 11)

        painter.setPen(QPen(QColor(color), 2))
        painter.setBrush(Qt.NoBrush)

        if self.index == 0:
            painter.drawRoundedRect(12, 9, 18, 24, 3, 3)
            painter.drawLine(8, 21, 23, 21)
            painter.drawLine(18, 16, 23, 21)
            painter.drawLine(18, 26, 23, 21)

        elif self.index == 1:
            from PySide6.QtGui import QPolygon
            from PySide6.QtCore import QPoint

            shield = QPolygon([
                QPoint(21, 7), QPoint(32, 12),
                QPoint(30, 25), QPoint(21, 34),
                QPoint(12, 25), QPoint(10, 12)
            ])
            painter.drawPolygon(shield)
            painter.drawLine(21, 15, 21, 23)
            painter.drawPoint(21, 28)

        elif self.index == 2:
            painter.drawRoundedRect(9, 13, 24, 17, 3, 3)
            painter.drawEllipse(17, 16, 9, 9)
            painter.drawLine(13, 9, 19, 9)
            painter.drawLine(19, 9, 22, 13)

        else:
            painter.drawRoundedRect(12, 8, 19, 26, 2, 2)
            painter.drawLine(16, 15, 26, 15)
            painter.drawLine(16, 20, 26, 20)
            painter.drawLine(21, 24, 21, 31)
            painter.drawLine(17, 27, 21, 31)
            painter.drawLine(25, 27, 21, 31)

        painter.end()
        self.icon.setPixmap(pixmap)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ActivityPage(QWidget):
    """Centar aktivnosti sustava RIVA."""

    CATEGORIES = [
        (
            "Prijave i odjave",
            "Povijest prijava, odjava i korisničkih pristupa",
            "LOGIN"
        ),
        (
            "Sigurnosni događaji",
            "Neuspjele prijave i sigurnosna upozorenja",
            "SECURITY"
        ),
        (
            "Analize i kamere",
            "Videoanaliza, LIVE kamera i OCR aktivnosti",
            "ANALYSIS"
        ),
        (
            "Izvještaji i preuzimanja",
            "Standardni i OCR izvještaji te preuzimanja",
            "REPORT"
        ),
    ]

    def __init__(self):
        super().__init__()
        self.events = []
        self.category = None
        self.build_ui()
        self.refresh_activities()

    def label(self, text, size=13, color="#EDF5FB", bold=False):
        widget = QLabel(text)
        widget.setWordWrap(True)
        widget.setStyleSheet(
            f"color: {color}; font-size: {size}px;"
            f"font-weight: {'bold' if bold else 'normal'};"
        )
        return widget

    def panel(self):
        frame = QFrame()
        frame.setObjectName("activityPanel")
        return frame

    def build_ui(self):
        self.setObjectName("activityRoot")
        self.setStyleSheet("""
            QWidget#activityRoot {
                background: #0B1423;
                color: #EDF5FB;
                font-family: 'Segoe UI';
            }
            QFrame#activityPanel, QFrame#activityTile {
                background: #152238;
                border: 1px solid #294158;
                border-radius: 16px;
            }
            QPushButton#activityTileButton {
                background: #152238;
                color: #EDF5FB;
                border: 1px solid #294158;
                border-radius: 16px;
                text-align: left;
                padding: 19px;
            }
            QPushButton#activityTileButton:hover {
                background: #1C3046;
                border: 1px solid #5DD9D0;
            }
            QPushButton#activityBack, QPushButton#activityRefresh {
                background: #1D354D;
                color: #5DD9D0;
                border: 1px solid #36566A;
                border-radius: 9px;
                padding: 10px 15px;
                font-weight: bold;
            }
            QPushButton#activityBack:hover,
            QPushButton#activityRefresh:hover {
                background: #29465C;
            }
            QLineEdit, QComboBox {
                background: #101D30;
                color: #EDF5FB;
                border: 1px solid #36516A;
                border-radius: 8px;
                padding: 9px;
                min-height: 22px;
            }
            QTableWidget {
                background: #142238;
                alternate-background-color: #1A2B40;
                color: #EDF5FB;
                gridline-color: #304760;
                border: 1px solid #304760;
                border-radius: 10px;
                selection-background-color: #245261;
            }
            QHeaderView::section {
                background: #20354A;
                color: #BBD0E2;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 27, 32, 25)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        self.build_home()
        self.build_details()

    def build_home(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #0B1423;
                width: 9px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #36566A;
                border-radius: 4px;
                min-height: 35px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 12, 12)
        layout.setSpacing(20)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(self.label(
            "Aktivnosti sustava", 29, "#FFFFFF", True
        ))
        titles.addWidget(self.label(
            "Sigurnost, korisničke aktivnosti i evidencija događaja",
            13, "#91A6BE"
        ))
        header.addLayout(titles)
        header.addStretch()

        active = self.label(chr(0x25CF) + "  SUSTAV AKTIVAN", 11, "#5DD9D0", True)
        active.setWordWrap(False)
        header.addWidget(active)
        layout.addLayout(header)

        stats = QHBoxLayout()
        stats.setSpacing(14)

        self.total_value = self.stat_card(
            stats, "UKUPNO DOGAĐAJA", "#5DD9D0"
        )
        self.success_value = self.stat_card(
            stats, "USPJEŠNE AKTIVNOSTI", "#5DD9D0"
        )
        self.failed_value = self.stat_card(
            stats, "NEUSPJEŠNE AKTIVNOSTI", "#F2BA61"
        )
        layout.addLayout(stats)

        layout.addWidget(self.label(
            "KATEGORIJE AKTIVNOSTI", 12, "#91A6BE", True
        ))

        grid = QGridLayout()
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(22)

        for index, (title, description, key) in enumerate(self.CATEGORIES):
            tile = ActivityTile(index, title, description)
            tile.clicked.connect(
                lambda k=key: self.open_category(k)
            )
            grid.addWidget(tile, index // 2, index % 2)

        layout.addLayout(grid)

        recent = self.panel()
        recent_layout = QVBoxLayout(recent)
        recent_layout.setContentsMargins(20, 17, 20, 17)
        recent_layout.setSpacing(11)

        recent_header = QHBoxLayout()
        recent_title = self.label(
            "POSLJEDNJE AKTIVNOSTI", 12, "#EDF5FB", True
        )
        recent_title.setWordWrap(False)
        recent_header.addWidget(recent_title)
        recent_header.addStretch()

        view_all = QPushButton("Prikaži sve  ?")
        view_all.setObjectName("activityRefresh")
        view_all.setCursor(Qt.PointingHandCursor)
        view_all.clicked.connect(
            lambda: self.open_category("ALL")
        )
        recent_header.addWidget(view_all)
        recent_layout.addLayout(recent_header)

        self.recent_rows = QVBoxLayout()
        self.recent_rows.setSpacing(7)
        recent_layout.addLayout(self.recent_rows)

        layout.addWidget(recent)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.stack.addWidget(page)

    def stat_card(self, parent, heading, color):
        card = self.panel()
        body = QVBoxLayout(card)
        body.setContentsMargins(20, 17, 20, 17)
        body.setSpacing(8)
        body.addWidget(self.label(heading, 11, "#91A6BE", True))

        number = self.label("0", 30, color, True)
        body.addWidget(number)
        parent.addWidget(card, 1)
        return number

    def build_details(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QHBoxLayout()

        back = QPushButton(chr(0x2190) + "  Natrag na aktivnosti")
        back.setObjectName("activityBack")
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(
            lambda: self.stack.setCurrentIndex(0)
        )
        header.addWidget(back)
        header.addStretch()

        refresh = QPushButton("Osvježi")
        refresh.setObjectName("activityRefresh")
        refresh.clicked.connect(self.refresh_activities)
        header.addWidget(refresh)
        layout.addLayout(header)

        self.detail_title = self.label(
            "Pregled aktivnosti", 27, "#FFFFFF", True
        )
        layout.addWidget(self.detail_title)

        self.detail_subtitle = self.label(
            "Detaljna evidencija zabilježenih događaja",
            13, "#91A6BE"
        )
        layout.addWidget(self.detail_subtitle)

        filters = QHBoxLayout()
        filters.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Pretraži korisnika, događaj ili opis..."
        )
        self.search.textChanged.connect(self.apply_filters)
        filters.addWidget(self.search, 3)

        self.event_filter = QComboBox()
        self.event_filter.addItem("Sve vrste događaja", "")
        self.event_filter.currentIndexChanged.connect(
            self.apply_filters
        )
        filters.addWidget(self.event_filter, 2)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Svi statusi", "")
        self.status_filter.addItem("Uspješno", "SUCCESS")
        self.status_filter.addItem("Neuspješno", "FAILED")
        self.status_filter.addItem("Informativno", "INFO")
        self.status_filter.currentIndexChanged.connect(
            self.apply_filters
        )
        filters.addWidget(self.status_filter, 1)

        layout.addLayout(filters)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "DATUM", "VRIJEME", "KORISNIK", "DOGAĐAJ", "STATUS"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self.show_event_details)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        layout.addWidget(self.table, 1)

        self.footer = self.label("", 12, "#91A6BE")
        layout.addWidget(self.footer)

        self.stack.addWidget(page)


    def show_event_details(self, row, column):
        id_item = self.table.item(row, 0)
        if id_item is None:
            return

        event_id = id_item.data(Qt.UserRole + 1)
        event = next(
            (item for item in self.events if item[0] == event_id),
            None
        )
        if event is None:
            return

        names = {
            "LOGIN_SUCCESS": "Uspje" + chr(0x0161) + "na prijava",
            "LOGIN_FAILED": "Neuspje" + chr(0x0161) + "na prijava",
            "LOGOUT": "Odjava korisnika",
        }

        kind = str(event[3] or "")
        title = names.get(kind, kind.replace("_", " ").title())

        dialog = QDialog(self)
        dialog.setWindowTitle("RIVA | Detalji aktivnosti")
        dialog.setMinimumWidth(490)
        dialog.setStyleSheet("""
            QDialog {
                background: #0B1423;
                color: #EDF5FB;
                font-family: 'Segoe UI';
            }
            QFrame#detailPanel {
                background: #152238;
                border: 1px solid #36516A;
                border-radius: 14px;
            }
            QPushButton {
                background: #5DD9D0;
                color: #0B1423;
                border: none;
                border-radius: 8px;
                padding: 11px 25px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #75E8DF;
            }
        """)

        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(17)

        heading = QLabel(title)
        heading.setStyleSheet(
            "color: #FFFFFF; font-size: 23px; font-weight: bold;"
        )
        outer.addWidget(heading)

        subtitle = QLabel("DETALJI EVIDENTIRANOG DOGA" + chr(0x0110) + "AJA")
        subtitle.setStyleSheet(
            "color: #5DD9D0; font-size: 11px; font-weight: bold;"
        )
        outer.addWidget(subtitle)

        panel = QFrame()
        panel.setObjectName("detailPanel")
        body = QVBoxLayout(panel)
        body.setContentsMargins(22, 19, 22, 19)
        body.setSpacing(14)

        timestamp = str(event[1] or "-")
        try:
            timestamp = datetime.fromisoformat(
                timestamp
            ).strftime("%d.%m.%Y.  %H:%M:%S")
        except (ValueError, TypeError):
            pass

        fields = [
            ("ID zapisa", str(event[0])),
            ("Korisnik", str(event[2] or "-")),
            ("Datum i vrijeme", timestamp),
            ("Vrsta", kind),
            ("Status", str(event[5] or "-")),
            ("Opis", str(event[4] or "Nema dodatnog opisa.")),
        ]

        for label, value in fields:
            line = QVBoxLayout()
            line.setSpacing(4)

            name_label = QLabel(label.upper())
            name_label.setStyleSheet(
                "color: #91A6BE; font-size: 10px;"
                "font-weight: bold; border: none;"
            )
            line.addWidget(name_label)

            value_label = QLabel(value)
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(
                Qt.TextSelectableByMouse
            )
            value_label.setStyleSheet(
                "color: #EDF5FB; font-size: 13px; border: none;"
            )
            line.addWidget(value_label)
            body.addLayout(line)

        outer.addWidget(panel)

        close_button = QPushButton("Zatvori")
        close_button.clicked.connect(dialog.accept)
        outer.addWidget(close_button, alignment=Qt.AlignRight)

        dialog.exec()

    def category_matches(self, event):
        kind = str(event[3] or "").upper()

        if self.category in (None, "ALL"):
            return True
        if self.category == "LOGIN":
            return kind in ("LOGIN_SUCCESS", "LOGOUT")
        if self.category == "SECURITY":
            return (
                "FAILED" in kind or
                "SECURITY" in kind or
                "WARNING" in kind
            )
        if self.category == "ANALYSIS":
            return any(
                word in kind
                for word in ("CAMERA", "OCR", "ANALYSIS", "VIDEO")
            )
        if self.category == "REPORT":
            return any(
                word in kind
                for word in ("REPORT", "EXPORT", "DOWNLOAD")
            )
        return False

    def open_category(self, key):
        self.category = key
        names = {
            "ALL": "Svi događaji",
            "LOGIN": "Prijave i odjave",
            "SECURITY": "Sigurnosni događaji",
            "ANALYSIS": "Analize i kamere",
            "REPORT": "Izvještaji i preuzimanja",
        }
        self.detail_title.setText(names.get(key, "Aktivnosti"))
        self.search.clear()
        self.status_filter.setCurrentIndex(0)
        self.refresh_activities()
        self.stack.setCurrentIndex(1)

    def refresh_activities(self):
        self.events = get_recent_events(limit=1000)

        self.total_value.setText(str(len(self.events)))
        self.success_value.setText(str(sum(
            1 for event in self.events
            if str(event[5]).upper() == "SUCCESS"
        )))
        self.failed_value.setText(str(sum(
            1 for event in self.events
            if str(event[5]).upper() == "FAILED"
        )))

        while self.recent_rows.count():
            item = self.recent_rows.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for event in self.events[:3]:
            kind = str(event[3] or "").upper()
            username = str(event[2] or "-")
            state = str(event[5] or "INFO").upper()

            timestamp = str(event[1])
            try:
                timestamp = datetime.fromisoformat(
                    timestamp
                ).strftime("%d.%m.%Y.  %H:%M")
            except (ValueError, TypeError):
                pass

            if kind == "LOGIN_SUCCESS":
                title = "Uspje" + chr(0x0161) + "na prijava"
                icon_text = chr(0x2713)
                color = "#5DD9D0"
            elif kind == "LOGIN_FAILED":
                title = "Neuspje" + chr(0x0161) + "na prijava"
                icon_text = "!"
                color = "#F2BA61"
            elif kind == "LOGOUT":
                title = "Odjava korisnika"
                icon_text = chr(0x2192)
                color = "#5DD9D0"
            else:
                title = kind.replace("_", " ").title()
                icon_text = chr(0x2022)
                color = "#91A6BE"

            if state == "SUCCESS":
                status_text = "USPJE" + chr(0x0160) + "NO"
            elif state == "FAILED":
                status_text = "NEUSPJE" + chr(0x0160) + "NO"
            else:
                status_text = "INFORMACIJA"

            activity_row = QFrame()
            activity_row.setObjectName("recentActivityRow")
            activity_row.setStyleSheet("""
                QFrame#recentActivityRow {
                    background: #101D30;
                    border: 1px solid #294158;
                    border-radius: 10px;
                }
                QFrame#recentActivityRow QLabel {
                    border: none;
                    background: transparent;
                }
            """)

            row_layout = QHBoxLayout(activity_row)
            row_layout.setContentsMargins(14, 11, 14, 11)
            row_layout.setSpacing(13)

            icon = QLabel(icon_text)
            icon.setFixedSize(34, 34)
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet(
                f"background: #1D354D; color: {color};"
                "border-radius: 9px; font-size: 19px;"
                "font-weight: bold;"
            )
            row_layout.addWidget(icon)

            text_column = QVBoxLayout()
            text_column.setSpacing(3)

            name_label = QLabel(title)
            name_label.setStyleSheet(
                "color: #EDF5FB; font-size: 13px;"
                "font-weight: bold;"
            )
            text_column.addWidget(name_label)

            user_label = QLabel("Korisnik: " + username)
            user_label.setStyleSheet(
                "color: #91A6BE; font-size: 11px;"
            )
            text_column.addWidget(user_label)

            row_layout.addLayout(text_column, 1)

            right_column = QVBoxLayout()
            right_column.setSpacing(4)

            date_label = QLabel(timestamp)
            date_label.setAlignment(Qt.AlignRight)
            date_label.setStyleSheet(
                "color: #BBD0E2; font-size: 11px;"
            )
            right_column.addWidget(date_label)

            status_label = QLabel(status_text)
            status_label.setAlignment(Qt.AlignRight)
            status_label.setStyleSheet(
                f"color: {color}; font-size: 10px;"
                "font-weight: bold;"
            )
            right_column.addWidget(status_label)

            row_layout.addLayout(right_column)
            self.recent_rows.addWidget(activity_row)

        if not self.events:
            self.recent_rows.addWidget(self.label(
                "Još nema evidentiranih aktivnosti.",
                12, "#91A6BE"
            ))

        selected = self.event_filter.currentData()
        types = sorted({
            str(event[3])
            for event in self.events
            if event[3] and self.category_matches(event)
        })

        self.event_filter.blockSignals(True)
        self.event_filter.clear()
        self.event_filter.addItem("Sve vrste događaja", "")

        for event_type in types:
            self.event_filter.addItem(event_type, event_type)

        index = self.event_filter.findData(selected)
        self.event_filter.setCurrentIndex(max(index, 0))
        self.event_filter.blockSignals(False)

        self.apply_filters()

    def apply_filters(self, *_):
        query = self.search.text().strip().casefold()
        kind_filter = self.event_filter.currentData()
        status_filter = self.status_filter.currentData()

        filtered = []

        for event in self.events:
            if not self.category_matches(event):
                continue

            searchable = " ".join(
                str(value or "") for value in (
                    event[2], event[3], event[4]
                )
            ).casefold()

            if query and query not in searchable:
                continue
            if kind_filter and event[3] != kind_filter:
                continue
            if status_filter and event[5] != status_filter:
                continue

            filtered.append(event)

        self.table.setRowCount(len(filtered))

        for row_index, event in enumerate(filtered):
            timestamp = str(event[1])

            try:
                dt = datetime.fromisoformat(timestamp)
                date_text = dt.strftime("%d.%m.%Y.")
                time_text = dt.strftime("%H:%M:%S")
            except ValueError:
                date_text = timestamp
                time_text = ""

            values = [
                date_text,
                time_text,
                str(event[2] or "-"),
                str(event[3]),
                str(event[5]),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, event[4] or "")
                item.setData(Qt.UserRole + 1, event[0])
                self.table.setItem(row_index, column, item)

        self.footer.setText(
            f"Prikazano {len(filtered)} od {len(self.events)} "
            "učitanih događaja."
        )
