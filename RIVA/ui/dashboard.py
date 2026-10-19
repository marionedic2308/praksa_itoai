
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

        row.addWidget(
            self.text_label(
                "◈  RIVA CONTROL CENTER",
                12,
                "#5DD9D0",
                True
            )
        )

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
                "Evidencija izvještaja slijedi",
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
            "◉    Otvori LIVE kameru"
        )
        camera_button.setObjectName("primaryButton")
        camera_button.setMinimumHeight(49)
        camera_button.setCursor(Qt.PointingHandCursor)
        camera_button.clicked.connect(
            self.open_camera.emit
        )

        analysis_button = QPushButton(
            "◎    Pokreni OCR modul"
        )
        analysis_button.setObjectName("secondaryButton")
        analysis_button.setMinimumHeight(49)
        analysis_button.setCursor(Qt.PointingHandCursor)
        analysis_button.clicked.connect(
            self.open_analysis.emit
        )

        reports_button = QPushButton(
            "▤    Pregled izvještaja"
        )
        reports_button.setObjectName("secondaryButton")
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
        """Priprema grafikon za stvarne prometne podatke."""

        frame = self.card()

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(15)

        layout.addLayout(
            self.section_title(
                "Analitika prometa",
                "Kretanje broja vozila kroz vrijeme"
            )
        )

        chart_area = QFrame()
        chart_area.setMinimumHeight(185)
        chart_area.setStyleSheet("""
            QFrame {
                background-color: #101D30;
                border: 1px solid #263B54;
                border-radius: 12px;
            }
        """)

        chart_layout = QVBoxLayout(chart_area)
        chart_layout.setAlignment(Qt.AlignCenter)
        chart_layout.setSpacing(10)

        symbol = self.text_label(
            "▥", 35, "#5DD9D0", True
        )
        symbol.setAlignment(Qt.AlignCenter)

        title = self.text_label(
            "Analitički podaci još nisu dostupni",
            14,
            "#DDEAF5",
            True
        )
        title.setAlignment(Qt.AlignCenter)

        description = self.text_label(
            "Grafikon će prikazivati stvarne rezultate "
            "spremljenih prometnih sesija.",
            12,
            "#91A6BE"
        )
        description.setAlignment(Qt.AlignCenter)

        chart_layout.addWidget(symbol)
        chart_layout.addWidget(title)
        chart_layout.addWidget(description)

        layout.addWidget(chart_area)

        return frame

    # ========================================================
    # POSLJEDNJE PROMETNE SESIJE
    # ========================================================

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

        except Exception:
            # Crtica označava nedostupne podatke.
            self.vehicles_value.setText("—")
            self.ocr_value.setText("—")
            self.sessions_value.setText("—")

        self.load_sessions()
        self.load_activities()

    def clear_layout(self, layout):
        """Sigurno uklanja prethodno prikazane elemente."""

        while layout.count():
            item = layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

            elif item.layout():
                self.clear_layout(item.layout())
