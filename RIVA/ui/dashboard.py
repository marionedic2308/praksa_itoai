
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QSizePolicy
)

from core.audit import get_recent_events
from core.sessions import (
    get_session_statistics,
    get_recent_sessions
)


# ============================================================
# RIVA - PREMIUM NADZORNA PLOČA 2.1
# ============================================================
# Prikazuje stvarne podatke iz SQLite baze:
# - statistiku prometnih sesija
# - obrađena vozila i OCR očitanja
# - posljednje prometne analize
# - aktivnosti korisnika
#
# Kamera, OCR obrada i grafikoni povezivat će se
# s odgovarajućim modulima tijekom razvoja.
# ============================================================



class TrafficChart(QWidget):
    """Stupcasti grafikon stvarnih prometnih sesija."""

    def __init__(self):
        super().__init__()
        self.values = []
        self.setMinimumHeight(240)

    def set_data(self, sessions):
        self.values = list(reversed(sessions))
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QPen, QFont
        from PySide6.QtCore import QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#101D30"))

        if not self.values:
            painter.setPen(QColor("#91A6BE"))
            painter.drawText(
                self.rect(), Qt.AlignCenter,
                "Nema spremljenih prometnih sesija."
            )
            painter.end()
            return

        left, right = 48, 18
        top, bottom = 35, 52
        width = max(1, self.width() - left - right)
        height = max(1, self.height() - top - bottom)

        maximum = max(
            1, max(int(s.get("total_vehicles") or 0)
                   for s in self.values)
        )

        # Cjelobrojna skala.
        step = max(1, (maximum + 3) // 4)
        ceiling = step * 4

        painter.setFont(QFont("Segoe UI", 9))

        for i in range(5):
            value = ceiling - i * step
            y = top + height * i / 4

            painter.setPen(QPen(QColor("#30445B"), 1))
            painter.drawLine(
                int(left), int(y),
                int(left + width), int(y)
            )

            painter.setPen(QColor("#91A6BE"))
            painter.drawText(
                QRectF(0, y - 9, left - 10, 18),
                Qt.AlignRight | Qt.AlignVCenter,
                str(value)
            )

        count = len(self.values)
        slot = width / count
        bar_width = min(22, slot * 0.32)

        for i, session in enumerate(self.values):
            value = int(session.get("total_vehicles") or 0)
            bar_height = height * value / ceiling

            x = left + slot * (i + 0.5)
            y = top + height - bar_height

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#F2B84B"))

            if value:
                painter.drawRoundedRect(
                    QRectF(
                        x - bar_width / 2, y,
                        bar_width, bar_height
                    ),
                    6, 6
                )

            painter.setPen(QColor("#EAF5FC"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(
                QRectF(x - 35, max(0, y - 24), 70, 20),
                Qt.AlignCenter,
                str(value)
            )

            code = session.get("session_code") or ""
            label = code.replace("RIVA-", "")

            painter.setPen(QColor("#91A6BE"))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(
                QRectF(
                    x - slot / 2,
                    top + height + 13,
                    slot, 20
                ),
                Qt.AlignCenter,
                label
            )

        painter.end()


class DashboardPage(QWidget):

    # Signali za navigaciju glavnog prozora.
    open_camera = Signal()
    open_analysis = Signal()
    open_reports = Signal()

    def __init__(self):
        super().__init__()

        self.setObjectName("dashboardPage")

        # Glavni raspored.
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("dashboardScroll")

        content = QWidget()
        content.setObjectName("dashboardContent")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 30, 36, 36)
        layout.setSpacing(22)

        # Zaglavlje i statusna traka.
        layout.addLayout(self.build_header())
        layout.addWidget(self.build_status_bar())

        # Statističke kartice.
        layout.addLayout(self.build_statistics())

        # Nadzorni centar i brze akcije.
        middle = QHBoxLayout()
        middle.setSpacing(18)

        middle.addWidget(self.build_monitor_panel(), 3)
        middle.addWidget(self.build_actions_panel(), 2)

        layout.addLayout(middle)

        # Analitika i posljednje sesije.
        analytics = QHBoxLayout()
        analytics.setSpacing(18)

        analytics.addWidget(self.build_chart_panel(), 3)
        analytics.addWidget(self.build_sessions_panel(), 2)

        layout.addLayout(analytics)

        # Evidencija aktivnosti.
        layout.addWidget(self.build_activity_panel())

        footer = QLabel(
            "RIVA  •  ROAD INTELLIGENCE & VISION ANALYSIS"
        )
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("""
            color: #516780;
            font-size: 10px;
            padding: 10px;
        """)

        layout.addWidget(footer)

        scroll.setWidget(content)
        root.addWidget(scroll)

        # Učitavanje stvarnih podataka.
        self.refresh_dashboard()

    # ========================================================
    # POMOĆNE METODE
    # ========================================================

    def card(self):
        """Stvara standardnu premium karticu."""

        frame = QFrame()
        frame.setObjectName("rivaPremiumCard")
        frame.setStyleSheet("""
            QFrame#rivaPremiumCard {
                background-color: #152238;
                border: 1px solid #293D57;
                border-radius: 16px;
            }
        """)
        return frame

    def text_label(self, text, size=13, color="#91A6BE",
                   bold=False):
        """Stvara tekstnu oznaku."""

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"""
            color: {color};
            font-size: {size}px;
            font-weight: {"bold" if bold else "normal"};
            background: transparent;
            border: none;
        """)
        return label

    def section_title(self, title, subtitle=None):
        """Stvara naslov odjeljka."""

        box = QVBoxLayout()
        box.setSpacing(5)

        box.addWidget(
            self.text_label(title, 19, "#F2F7FC", True)
        )

        if subtitle:
            box.addWidget(
                self.text_label(subtitle, 12, "#91A6BE")
            )

        return box

    def status_pill(self, text, color, background):
        """Stvara statusnu oznaku."""

        label = QLabel(f"●  {text}")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"""
            color: {color};
            background-color: {background};
            border: 1px solid {background};
            border-radius: 9px;
            padding: 9px 12px;
            font-size: 11px;
            font-weight: bold;
        """)
        return label

    # ========================================================
    # ZAGLAVLJE
    # ========================================================

    def build_header(self):
        """Izrađuje zaglavlje nadzorne ploče."""

        row = QHBoxLayout()

        heading = QVBoxLayout()
        heading.setSpacing(6)

        heading.addWidget(
            self.text_label(
                "Nadzorna ploča", 31, "#FFFFFF", True
            )
        )

        heading.addWidget(
            self.text_label(
                "Inteligentni nadzor i analiza cestovnog prometa",
                13,
                "#91A6BE"
            )
        )

        row.addLayout(heading)
        row.addStretch()

        date = QLabel(
            datetime.now().strftime("%d.%m.%Y.")
        )
        date.setStyleSheet("""
            color: #D5E3F1;
            background-color: #152238;
            border: 1px solid #293D57;
            border-radius: 10px;
            padding: 12px 18px;
            font-size: 13px;
            font-weight: bold;
        """)

        row.addWidget(date)

        return row

    def build_status_bar(self):
        """Izrađuje informacijsku statusnu traku."""

        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #101E30;
                border: 1px solid #263B54;
                border-radius: 12px;
            }
        """)

        row = QHBoxLayout(frame)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(10)

        control_label = self.text_label(
            chr(0x25C8) + "  RIVA CONTROL CENTER",
            12,
            "#5DD9D0",
            True
        )
        control_label.setWordWrap(False)
        control_label.setMinimumWidth(
            control_label.fontMetrics().horizontalAdvance(
                control_label.text()
            ) + 12
        )
        row.addWidget(control_label)

        row.addStretch()

        row.addWidget(
            self.status_pill(
                "APLIKACIJA AKTIVNA",
                "#52D8C9",
                "#143B3C"
            )
        )

        row.addWidget(
            self.status_pill(
                "KAMERA NEPOVEZANA",
                "#F2BA61",
                "#3B3024"
            )
        )

        row.addWidget(
            self.status_pill(
                "OCR MIROVANJE",
                "#B0C2D5",
                "#27364A"
            )
        )

        return frame

    # ========================================================
    # STATISTIČKE KARTICE
    # ========================================================

    def build_statistics(self):
        """Izrađuje kartice s podacima iz baze."""

        grid = QGridLayout()
        grid.setSpacing(16)

        # Kartice stvaramo jednom, a vrijednosti osvježavamo.
        self.vehicles_value = QLabel("0")
        self.ocr_value = QLabel("0")
        self.sessions_value = QLabel("0")
        self.reports_value = QLabel("—")

        cards = [
            (
                "OBRAĐENA VOZILA",
                self.vehicles_value,
                "Vozila iz završenih analiza",
                "▣",
                "#5DD9D0"
            ),
            (
                "OCR OČITANJA",
                self.ocr_value,
                "Uspješno očitane registracije",
                "◎",
                "#7FA8FF"
            ),
            (
                "PROMETNE SESIJE",
                self.sessions_value,
                "Ukupno evidentiranih sesija",
                "◷",
                "#B59BFF"
            ),
            (
                "IZVJEŠTAJI",
                self.reports_value,
                "Dostupni prometni izvjestaji",
                "▤",
                "#F2BA61"
            )
        ]

        for index, data in enumerate(cards):
            grid.addWidget(
                self.create_stat_card(*data),
                0,
                index
            )

        return grid

    def create_stat_card(self, title, value_label,
                         description, symbol, accent):
        """Stvara karticu sa statističkom vrijednošću."""

        frame = self.card()
        frame.setMinimumHeight(165)
        frame.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 19, 20, 20)
        layout.setSpacing(10)

        top = QHBoxLayout()

        top.addWidget(
            self.text_label(title, 11, "#9FB4CC", True)
        )
        top.addStretch()

        top.addWidget(
            self.text_label(symbol, 25, accent, True)
        )

        layout.addLayout(top)

        value_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 35px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)

        layout.addWidget(value_label)

        layout.addWidget(
            self.text_label(description, 11, "#91A6BE")
        )

        accent_line = QFrame()
        accent_line.setFixedHeight(3)
        accent_line.setStyleSheet(f"""
            background-color: {accent};
            border: none;
            border-radius: 1px;
        """)

        layout.addStretch()
        layout.addWidget(accent_line)

        return frame

    # ========================================================
    # NADZORNI CENTAR
    # ========================================================

    def build_monitor_panel(self):
        """Priprema područje za LIVE kameru."""

        frame = self.card()

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        header = QHBoxLayout()

        header.addLayout(
            self.section_title(
                "Nadzorni centar",
                "Pregled izvora videoanalize"
            )
        )

        header.addStretch()

        header.addWidget(
            self.status_pill(
                "OFFLINE",
                "#F2BA61",
                "#3B3024"
            )
        )

        layout.addLayout(header)

        preview = QFrame()
        preview.setMinimumHeight(205)
        preview.setStyleSheet("""
            QFrame {
                background-color: #0B1525;
                border: 1px dashed #35516B;
                border-radius: 13px;
            }
        """)

        preview_layout = QVBoxLayout(preview)
        preview_layout.setAlignment(Qt.AlignCenter)
        preview_layout.setSpacing(10)

        symbol = self.text_label(
            "◉", 39, "#5DD9D0", True
        )
        symbol.setAlignment(Qt.AlignCenter)

        title = self.text_label(
            "Videoizvor nije povezan",
            17,
            "#DDEAF5",
            True
        )
        title.setAlignment(Qt.AlignCenter)

        description = self.text_label(
            "Povežite kameru za prikaz prometnog toka.",
            12,
            "#91A6BE"
        )
        description.setAlignment(Qt.AlignCenter)

        preview_layout.addWidget(symbol)
        preview_layout.addWidget(title)
        preview_layout.addWidget(description)

        layout.addWidget(preview)

        info = QHBoxLayout()

        info.addWidget(
            self.text_label(
                "IZVOR  •  Nije odabran",
                11,
                "#9FB4CC"
            )
        )

        info.addStretch()

        info.addWidget(
            self.text_label(
                "ANALIZA  •  Neaktivna",
                11,
                "#9FB4CC"
            )
        )

        layout.addLayout(info)

        return frame

    # ========================================================
    # BRZE AKCIJE
    # ========================================================

    def build_actions_panel(self):
        """Izrađuje gumbe za navigaciju."""

        frame = self.card()

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(13)

        layout.addLayout(
            self.section_title(
                "Upravljanje sustavom",
                "Brzi pristup modulima RIVA-e"
            )
        )

        layout.addSpacing(8)

        camera_button = QPushButton(
            "Otvori LIVE kameru"
        )
        camera_button.setObjectName("primaryButton")
        camera_button.setMinimumHeight(49)
        camera_button.setCursor(Qt.PointingHandCursor)
        camera_button.clicked.connect(
            self.open_camera.emit
        )

        analysis_button = QPushButton(
            "Pokreni OCR modul"
        )
        analysis_button.setObjectName("secondaryButton")
        analysis_button.setMinimumHeight(49)
        analysis_button.setCursor(Qt.PointingHandCursor)
        analysis_button.clicked.connect(
            self.open_analysis.emit
        )

        reports_button = QPushButton(
            "Pregled izvještaja"
        )
        reports_button.setObjectName("secondaryButton")

        # Ujednacene vektorske ikone za brzi pristup.
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QIcon, QPainter, QPixmap
        from PySide6.QtSvg import QSvgRenderer

        def make_icon(paths, color):
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'width="24" height="24" viewBox="0 0 24 24" '
                'fill="none" stroke="' + color + '" '
                'stroke-width="1.9" stroke-linecap="round" '
                'stroke-linejoin="round">' + paths + '</svg>'
            )
            pixmap = QPixmap(48, 48)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer = QSvgRenderer(svg.encode("utf-8"))
            renderer.render(painter)
            painter.end()
            return QIcon(pixmap)

        camera_button.setIcon(make_icon(
            '<rect x="3" y="5" width="14" height="14" rx="2"/>'
            '<path d="m17 10 4-3v10l-4-3z"/>',
            "#10263A"
        ))
        analysis_button.setIcon(make_icon(
            '<path d="M8 3H5a2 2 0 0 0-2 2v3"/>'
            '<path d="M16 3h3a2 2 0 0 1 2 2v3"/>'
            '<path d="M3 16v3a2 2 0 0 0 2 2h3"/>'
            '<path d="M21 16v3a2 2 0 0 1-2 2h-3"/>',
            "#A8C1D4"
        ))
        reports_button.setIcon(make_icon(
            '<path d="M7 3h8l4 4v14H7z"/>'
            '<path d="M15 3v5h4"/>'
            '<path d="M10 12h6M10 16h6"/>',
            "#A8C1D4"
        ))

        for button in (
            camera_button, analysis_button, reports_button
        ):
            button.setIconSize(QSize(20, 20))

        reports_button.setMinimumHeight(49)
        reports_button.setCursor(Qt.PointingHandCursor)
        reports_button.clicked.connect(
            self.open_reports.emit
        )

        layout.addWidget(camera_button)
        layout.addWidget(analysis_button)
        layout.addWidget(reports_button)

        layout.addStretch()

        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("""
            background-color: #2A3D55;
            border: none;
        """)
        layout.addWidget(separator)

        layout.addWidget(
            self.text_label(
                "SIGURNOST SUSTAVA",
                11,
                "#5DD9D0",
                True
            )
        )

        layout.addWidget(
            self.text_label(
                "Aktivnosti korisnika evidentiraju se "
                "u lokalnoj SQLite bazi.",
                12,
                "#91A6BE"
            )
        )

        return frame

    # ========================================================
    # ANALITIČKI GRAFIKON
    # ========================================================

    def build_chart_panel(self):
        frame = self.card()

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(15)

        layout.addLayout(
            self.section_title(
                "Analitika prometa",
                "Broj evidentiranih vozila po sesijama"
            )
        )

        chart_area = QFrame()
        chart_area.setStyleSheet("""
            QFrame {
                background:#101D30;
                border:1px solid #263B54;
                border-radius:12px;
            }
        """)

        chart_layout = QVBoxLayout(chart_area)
        chart_layout.setContentsMargins(12, 14, 12, 10)

        self.traffic_chart = TrafficChart()
        chart_layout.addWidget(self.traffic_chart)

        layout.addWidget(chart_area)

        legend = self.text_label(
            "Zlatno: broj vozila  |  "
            "X: prometne sesije  |  "
            "Y: broj vozila",
            11, "#91A6BE"
        )
        layout.addWidget(legend)

        return frame

    def refresh_traffic_chart(self):
        try:
            sessions = get_recent_sessions(7)
            self.traffic_chart.set_data(sessions)
        except Exception:
            self.traffic_chart.set_data([])

    # POSLJEDNJE PROMETNE SESIJE

    def build_sessions_panel(self):
        """Prikazuje posljednje spremljene analize."""

        frame = self.card()

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(15)

        layout.addLayout(
            self.section_title(
                "Posljednje analize",
                "Povijest prometnih sesija"
            )
        )

        # Sadržaj ćemo dinamički osvježavati.
        self.sessions_container = QVBoxLayout()
        self.sessions_container.setSpacing(9)

        layout.addLayout(self.sessions_container)

        return frame

    def load_sessions(self):
        """Učitava stvarne prometne sesije iz baze."""

        self.clear_layout(self.sessions_container)

        try:
            sessions = get_recent_sessions(4)

        except Exception:
            self.sessions_container.addWidget(
                self.text_label(
                    "Nije moguće učitati prometne sesije.",
                    12,
                    "#F07882"
                )
            )
            return

        if not sessions:
            empty = QFrame()
            empty.setMinimumHeight(185)
            empty.setStyleSheet("""
                QFrame {
                    background-color: #101D30;
                    border: 1px solid #263B54;
                    border-radius: 12px;
                }
            """)

            empty_layout = QVBoxLayout(empty)
            empty_layout.setAlignment(Qt.AlignCenter)
            empty_layout.setSpacing(10)

            symbol = self.text_label(
                "◷", 35, "#B59BFF", True
            )
            symbol.setAlignment(Qt.AlignCenter)

            title = self.text_label(
                "Nema spremljenih sesija",
                14,
                "#DDEAF5",
                True
            )
            title.setAlignment(Qt.AlignCenter)

            description = self.text_label(
                "Nakon prve analize ovdje će se "
                "prikazati njezini rezultati.",
                12,
                "#91A6BE"
            )
            description.setAlignment(Qt.AlignCenter)

            empty_layout.addWidget(symbol)
            empty_layout.addWidget(title)
            empty_layout.addWidget(description)

            self.sessions_container.addWidget(empty)
            return

        # Prikaz stvarnih sesija.
        for session in sessions:

            row = QFrame()
            row.setStyleSheet("""
                QFrame {
                    background-color: #101D30;
                    border: 1px solid #263B54;
                    border-radius: 10px;
                }
                QLabel {
                    background: transparent;
                    border: none;
                }
            """)

            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(14, 12, 14, 12)
            row_layout.setSpacing(5)

            code = session["session_code"]
            status = session["status"]
            vehicles = session["total_vehicles"]

            try:
                date = datetime.fromisoformat(
                    session["started_at"]
                ).strftime("%d.%m.%Y. %H:%M")
            except (ValueError, TypeError):
                date = session["started_at"]

            status_names = {
                "RUNNING": "U TIJEKU",
                "COMPLETED": "ZAVRŠENA",
                "INTERRUPTED": "PREKINUTA",
                "FAILED": "NEUSPJEŠNA"
            }

            row_layout.addWidget(
                self.text_label(
                    code,
                    13,
                    "#5DD9D0",
                    True
                )
            )

            row_layout.addWidget(
                self.text_label(
                    f"{date}  •  {status_names.get(status, status)}",
                    11,
                    "#B8C9DC"
                )
            )

            row_layout.addWidget(
                self.text_label(
                    f"Obrađena vozila: {vehicles}",
                    11,
                    "#91A6BE"
                )
            )

            self.sessions_container.addWidget(row)

    # ========================================================
    # AKTIVNOSTI SUSTAVA
    # ========================================================

    def build_activity_panel(self):
        """Stvara prikaz audit aktivnosti."""

        frame = self.card()

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        header = QHBoxLayout()

        header.addLayout(
            self.section_title(
                "Aktivnosti sustava",
                "Posljednji evidentirani događaji"
            )
        )

        header.addStretch()

        refresh = QPushButton("↻  Osvježi")
        refresh.setObjectName("secondaryButton")
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.clicked.connect(
            self.refresh_dashboard
        )

        header.addWidget(refresh)

        layout.addLayout(header)

        self.activity_container = QVBoxLayout()
        self.activity_container.setSpacing(9)

        layout.addLayout(self.activity_container)

        return frame

    def load_activities(self):
        """Učitava posljednjih pet stvarnih audit događaja."""

        self.clear_layout(self.activity_container)

        try:
            events = get_recent_events(5)

        except Exception:
            self.activity_container.addWidget(
                self.text_label(
                    "Nije moguće učitati aktivnosti.",
                    12,
                    "#F07882"
                )
            )
            return

        if not events:
            self.activity_container.addWidget(
                self.text_label(
                    "Još nema evidentiranih aktivnosti.",
                    12,
                    "#91A6BE"
                )
            )
            return

        for event in events:

            (
                event_id,
                timestamp,
                username,
                event_type,
                description,
                status
            ) = event

            try:
                formatted_date = datetime.fromisoformat(
                    timestamp
                ).strftime("%d.%m.%Y.  %H:%M:%S")
            except (ValueError, TypeError):
                formatted_date = str(timestamp)

            if status == "SUCCESS":
                color = "#45D6CD"
                status_text = "USPJEŠNO"
            elif status == "FAILED":
                color = "#F07882"
                status_text = "NEUSPJEŠNO"
            else:
                color = "#9FB4CC"
                status_text = status or "INFO"

            row = QFrame()
            row.setStyleSheet("""
                QFrame {
                    background-color: #101D30;
                    border: 1px solid #263B54;
                    border-radius: 10px;
                }
                QLabel {
                    background: transparent;
                    border: none;
                }
            """)

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(16, 12, 16, 12)
            row_layout.setSpacing(12)

            dot = self.text_label(
                "●", 14, color, True
            )
            row_layout.addWidget(dot)

            details = QVBoxLayout()
            details.setSpacing(5)

            details.addWidget(
                self.text_label(
                    description or event_type,
                    12,
                    "#EAF2FA",
                    True
                )
            )

            details.addWidget(
                self.text_label(
                    f"{formatted_date}  •  "
                    f"{username or 'Sustav'}",
                    11,
                    "#91A6BE"
                )
            )

            row_layout.addLayout(details)
            row_layout.addStretch()

            row_layout.addWidget(
                self.text_label(
                    status_text,
                    11,
                    color,
                    True
                )
            )

            self.activity_container.addWidget(row)

    # ========================================================
    # OSVJEŽAVANJE PODATAKA
    # ========================================================

    def refresh_dashboard(self):
        """
        Osvježava statistiku, sesije i aktivnosti
        iz stvarne SQLite baze.
        """

        try:
            stats = get_session_statistics()

            self.vehicles_value.setText(
                str(stats["total_vehicles"])
            )

            self.ocr_value.setText(
                str(stats["total_ocr_success"])
            )

            self.sessions_value.setText(
                str(stats["total_sessions"])
            )

            self.reports_value.setText(
                str(stats["total_reports"])
            )

        except Exception:
            # Crtica označava nedostupne podatke.
            self.vehicles_value.setText("—")
            self.ocr_value.setText("—")
            self.sessions_value.setText("—")
            self.reports_value.setText(chr(8212))

        self.load_sessions()
        self.load_activities()
        self.refresh_traffic_chart()

    def clear_layout(self, layout):
        """Sigurno uklanja prethodno prikazane elemente."""

        while layout.count():
            item = layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

            elif item.layout():
                self.clear_layout(item.layout())
