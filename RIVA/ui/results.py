"""RIVA - pregled spremljenih prometnih analiza iz SQLite baze.

OCR podaci se namjerno ne prikazuju u ovom modulu.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPushButton, QMessageBox, QScrollArea, QSizePolicy,
)

from core.sessions import (
    get_recent_sessions,
    get_saved_session_statistics,
    get_vehicle_events,
)


class ResultsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_session = None
        self.build_ui()
        self.clear_results()
        # Prvo učitavanje i pri otvaranju stranice iz glavnog prozora.
        self.refresh_sessions()

    def build_ui(self):
        # Vanjsko pomicanje cijele stranice, neovisno o tablici.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.page_scroll = QScrollArea(self)
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setFrameShape(QFrame.NoFrame)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.page_scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: #101D30; width: 10px; margin: 0; }
            QScrollBar::handle:vertical { background: #35516B; border-radius: 5px; min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self.page_content = QWidget()
        self.page_content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self.page_content)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)
        self.page_scroll.setWidget(self.page_content)
        outer.addWidget(self.page_scroll)

        title = QLabel("Rezultati analize")
        title.setStyleSheet("color: #FFFFFF; font-size: 30px; font-weight: bold;")
        subtitle = QLabel("Pregled prometnih podataka i evidentiranih prolazaka")
        subtitle.setStyleSheet("color: #91A6BE; font-size: 13px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        session_card = QFrame()
        session_card.setObjectName("resultsSessionCard")
        session_card.setStyleSheet("""
            QFrame#resultsSessionCard {
                background-color: #152238;
                border: 1px solid #293D57;
                border-radius: 14px;
            }
        """)
        session_layout = QVBoxLayout(session_card)
        session_layout.setContentsMargins(20, 16, 20, 16)
        session_layout.setSpacing(10)
        session_title = QLabel("ODABIR ANALIZE")
        session_title.setStyleSheet("color: #5DD9D0; font-size: 12px; font-weight: bold;")
        session_layout.addWidget(session_title)

        selector_row = QHBoxLayout()
        self.session_selector = QComboBox()
        self.session_selector.setMinimumHeight(42)
        self.session_selector.setStyleSheet("""
            QComboBox { background: #0D1B2C; color: #E5F0F8;
                        border: 1px solid #35516B; border-radius: 8px;
                        padding: 8px 12px; }
            QComboBox QAbstractItemView { background: #152238; color: #E5F0F8;
                                         selection-background-color: #176C72; }
        """)
        self.session_selector.addItem("Nema dostupnih analiza")
        self.session_selector.setEnabled(False)
        self.session_selector.currentIndexChanged.connect(self.load_selected_session)
        selector_row.addWidget(self.session_selector, 1)

        self.refresh_button = QPushButton("↻  Osvježi")
        self.refresh_button.setMinimumHeight(42)
        self.refresh_button.setStyleSheet("""
            QPushButton { background: #176C72; color: white; border: none;
                          border-radius: 8px; padding: 9px 16px; font-weight: bold; }
            QPushButton:hover { background: #19858B; }
        """)
        self.refresh_button.clicked.connect(self.refresh_sessions)
        selector_row.addWidget(self.refresh_button)
        session_layout.addLayout(selector_row)

        self.session_info = QLabel("Nije odabrana analiza.")
        self.session_info.setWordWrap(True)
        self.session_info.setStyleSheet("color: #91A6BE; font-size: 12px;")
        session_layout.addWidget(self.session_info)
        layout.addWidget(session_card)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)
        self.total_value = self.create_card(cards_row, "UKUPNO VOZILA", "#5DD9D0")
        self.correct_value = self.create_card(cards_row, "ISPRAVAN SMJER", "#52D8A4")
        self.opposite_value = self.create_card(cards_row, "SUPROTAN SMJER", "#F2BA61")
        layout.addLayout(cards_row)

        category_card = QFrame()
        category_card.setObjectName("resultsCategoryCard")
        category_card.setStyleSheet("""
            QFrame#resultsCategoryCard {
                background-color: #152238; border: 1px solid #293D57;
                border-radius: 14px;
            }
        """)
        category_layout = QVBoxLayout(category_card)
        category_layout.setContentsMargins(20, 18, 20, 18)
        category_layout.setSpacing(14)
        category_title = QLabel("KATEGORIJE VOZILA")
        category_title.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: bold;")
        category_layout.addWidget(category_title)
        category_row = QHBoxLayout()
        category_row.setSpacing(12)
        self.category_labels = {}
        for name in ("Automobil", "Kamion", "Autobus", "Motocikl"):
            item = QLabel(f"{name}\n—")
            item.setAlignment(Qt.AlignCenter)
            item.setMinimumHeight(65)
            item.setStyleSheet("""
                background-color: #1C3047; color: #E5F0F8;
                border: 1px solid #304760; border-radius: 10px;
                font-size: 13px; font-weight: bold;
            """)
            category_row.addWidget(item)
            self.category_labels[name] = item
        category_layout.addLayout(category_row)
        layout.addWidget(category_card)

        self.lanes_label = QLabel("Po trakama: —")
        self.lanes_label.setWordWrap(True)
        self.lanes_label.setStyleSheet("color: #AFC1D4; font-size: 12px;")
        layout.addWidget(self.lanes_label)

        table_card = QFrame()
        table_card.setObjectName("resultsTableCard")
        table_card.setStyleSheet("""
            QFrame#resultsTableCard {
                background-color: #152238; border: 1px solid #293D57;
                border-radius: 14px;
            }
        """)
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(20, 18, 20, 18)
        table_layout.setSpacing(12)
        table_title = QLabel("EVIDENCIJA PROLAZAKA")
        table_title.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: bold;")
        table_layout.addWidget(table_title)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID vozila", "Kategorija", "Prometna traka", "Smjer",
            "Vrijeme prolaska", "Trajanje (s)",
        ])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #101D30; alternate-background-color: #182A40;
                color: #E5F0F8; border: 1px solid #293D57;
                border-radius: 8px; gridline-color: #293D57;
                font-size: 12px; selection-background-color: #176C72;
            }
            QHeaderView::section {
                background-color: #213750; color: #DDEAF5;
                padding: 10px; border: none;
                border-bottom: 1px solid #36516A; font-weight: bold;
            }
        """)
        # Fiksna visina omogućuje zaseban scroll za stotine prolazaka.
        self.table.setFixedHeight(340)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        table_layout.addWidget(self.table)
        self.empty_label = QLabel("Nema evidentiranih prolazaka za prikaz.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #91A6BE; font-size: 12px; border: none;")
        table_layout.addWidget(self.empty_label)
        layout.addWidget(table_card)

        privacy_label = QLabel(
            "Registarske oznake nisu dostupne u ovom pregledu. "
            "Zaštićeni OCR izvještaji zahtijevaju ponovnu autentifikaciju."
        )
        privacy_label.setWordWrap(True)
        privacy_label.setStyleSheet("color: #91A6BE; font-size: 11px; padding: 6px;")
        layout.addWidget(privacy_label)
        layout.addStretch(0)

    def create_card(self, parent_layout, title, color):
        card = QFrame()
        card.setObjectName("resultsStatCard")
        card.setStyleSheet("""
            QFrame#resultsStatCard {
                background-color: #152238; border: 1px solid #293D57;
                border-radius: 14px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(8)
        heading = QLabel(title)
        heading.setStyleSheet("color: #91A6BE; font-size: 11px; font-weight: bold;")
        value = QLabel("—")
        value.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold;")
        card_layout.addWidget(heading)
        card_layout.addWidget(value)
        parent_layout.addWidget(card)
        return value

    def clear_results(self):
        self.current_session = None
        self.total_value.setText("—")
        self.correct_value.setText("—")
        self.opposite_value.setText("—")
        for name, label in self.category_labels.items():
            label.setText(f"{name}\n—")
        self.lanes_label.setText("Po trakama: —")
        self.table.setRowCount(0)
        self.empty_label.setVisible(True)

    def refresh_sessions(self):
        """Učitava povijest iz baze, čuvajući prethodni odabir kada je moguće."""
        previous_id = self.session_selector.currentData()
        try:
            sessions = get_recent_sessions(limit=100)
        except Exception as error:
            self.session_selector.blockSignals(True)
            self.session_selector.clear()
            self.session_selector.addItem("Pogreška pri učitavanju analiza")
            self.session_selector.setEnabled(False)
            self.session_selector.blockSignals(False)
            self.clear_results()
            self.session_info.setText("Nije moguće učitati povijest analiza.")
            QMessageBox.warning(self, "RIVA - Rezultati", f"Učitavanje nije uspjelo: {type(error).__name__}")
            return

        self.session_selector.blockSignals(True)
        self.session_selector.clear()
        for session in sessions:
            session_id = session.get("id")
            code = session.get("session_code") or f"RIVA-{int(session_id):06d}"
            status = session.get("status", "")
            username = session.get("username", "")
            started = session.get("started_at") or session.get("start_time") or ""
            label = f"{code}  |  {started}  |  {username}  |  {status}"
            self.session_selector.addItem(label, session_id)
        self.session_selector.setEnabled(bool(sessions))
        if not sessions:
            self.session_selector.addItem("Nema dostupnih analiza")
        else:
            selected_index = self.session_selector.findData(previous_id)
            self.session_selector.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.session_selector.blockSignals(False)

        if sessions:
            self.load_selected_session()
        else:
            self.clear_results()
            self.session_info.setText("Još nema spremljenih analiza.")

    def load_selected_session(self, *_):
        session_id = self.session_selector.currentData()
        if session_id is None:
            self.clear_results()
            return
        try:
            statistics = get_saved_session_statistics(session_id)
            events = get_vehicle_events(session_id)
        except Exception as error:
            self.clear_results()
            self.session_info.setText("Pogreška pri čitanju odabrane analize.")
            QMessageBox.warning(self, "RIVA - Rezultati", f"Čitanje nije uspjelo: {type(error).__name__}")
            return
        if statistics is None:
            statistics = {
                "total_count": 0, "correct_count": 0, "opposite_count": 0,
                "category_counts": {}, "lane_counts": {},
            }
        self.set_results(session_id, statistics, events)
        self.session_info.setText(
            f"Odabrana sesija: RIVA-{int(session_id):06d}  •  "
            f"Evidentiranih prolazaka: {len(events)}"
        )


    @staticmethod
    def format_event_time(value):
        """Formatira ISO datum za prikaz u tablici."""
        from datetime import datetime

        if not value:
            return ""

        try:
            dt = datetime.fromisoformat(str(value))
            return dt.strftime("%d.%m.%Y. %H:%M:%S")
        except (ValueError, TypeError):
            return str(value)

    def set_results(self, session_id, statistics, events):
        """Prikazuje statistiku i pojedinačne događaje; bez OCR podataka."""
        self.clear_results()
        self.current_session = session_id
        self.total_value.setText(str(statistics.get("total_count", 0)))
        self.correct_value.setText(str(statistics.get("correct_count", 0)))
        self.opposite_value.setText(str(statistics.get("opposite_count", 0)))
        categories = statistics.get("category_counts") or {}
        for name, label in self.category_labels.items():
            label.setText(f"{name}\n{categories.get(name, 0)}")
        lanes = statistics.get("lane_counts") or {}
        self.lanes_label.setText(
            "Po trakama: " + ", ".join(f"{name}: {count}" for name, count in lanes.items())
            if lanes else "Po trakama: —"
        )
        self.table.setRowCount(len(events))
        for row, event in enumerate(events):
            duration = event.get("duration_seconds")
            values = [
                event.get("track_id", ""), event.get("vehicle_type", ""),
                event.get("lane", ""), event.get("direction", ""),
                self.format_event_time(event.get("counted_at", "")),
                f"{duration:.2f}" if isinstance(duration, (int, float)) else "—",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)
        self.empty_label.setVisible(len(events) == 0)
