
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)


# ============================================================
# RIVA - REZULTATI ANALIZE PROMETA
# ============================================================
# Prikaz rezultata pojedine sesije.
#
# Statisticki podaci:
# - ukupni broj vozila
# - ispravan i suprotan smjer
# - kategorije vozila
# - evidencija prolazaka
#
# OCR registracije ovdje se ne prikazuju.
# Za njih ce postojati zaseban zasticeni prikaz.
# ============================================================


class ResultsPage(QWidget):

    def __init__(self):
        super().__init__()

        self.current_session = None
        self.build_ui()
        self.clear_results()

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        # ZAGLAVLJE

        title = QLabel("Rezultati analize")
        title.setStyleSheet("""
            color: #FFFFFF;
            font-size: 30px;
            font-weight: bold;
        """)

        subtitle = QLabel(
            "Pregled prometnih podataka i evidentiranih prolazaka"
        )
        subtitle.setStyleSheet("""
            color: #91A6BE;
            font-size: 13px;
        """)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # ODABIR SESIJE

        session_card = QFrame()
        session_card.setStyleSheet("""
            QFrame {
                background-color: #152238;
                border: 1px solid #293D57;
                border-radius: 14px;
            }
        """)

        session_layout = QVBoxLayout(session_card)
        session_layout.setContentsMargins(20, 16, 20, 16)
        session_layout.setSpacing(10)

        session_title = QLabel("ODABIR ANALIZE")
        session_title.setStyleSheet("""
            color: #5DD9D0;
            font-size: 12px;
            font-weight: bold;
            border: none;
        """)

        self.session_selector = QComboBox()
        self.session_selector.setMinimumHeight(42)
        self.session_selector.addItem(
            "Nema dostupnih analiza"
        )
        self.session_selector.setEnabled(False)

        session_layout.addWidget(session_title)
        session_layout.addWidget(self.session_selector)

        layout.addWidget(session_card)

        # STATISTICKE KARTICE

        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self.total_value = self.create_card(
            cards_row,
            "UKUPNO VOZILA",
            "#5DD9D0"
        )

        self.correct_value = self.create_card(
            cards_row,
            "ISPRAVAN SMJER",
            "#52D8A4"
        )

        self.opposite_value = self.create_card(
            cards_row,
            "SUPROTAN SMJER",
            "#F2BA61"
        )

        layout.addLayout(cards_row)

        # KATEGORIJE VOZILA

        category_card = QFrame()
        category_card.setStyleSheet("""
            QFrame {
                background-color: #152238;
                border: 1px solid #293D57;
                border-radius: 14px;
            }
        """)

        category_layout = QVBoxLayout(category_card)
        category_layout.setContentsMargins(20, 18, 20, 18)
        category_layout.setSpacing(14)

        category_title = QLabel("KATEGORIJE VOZILA")
        category_title.setStyleSheet("""
            color: #FFFFFF;
            font-size: 15px;
            font-weight: bold;
            border: none;
        """)

        category_layout.addWidget(category_title)

        category_row = QHBoxLayout()
        category_row.setSpacing(12)

        self.category_labels = {}

        for name in (
            "Automobil",
            "Kamion",
            "Autobus",
            "Motocikl"
        ):

            item = QLabel(f"{name}\n—")
            item.setAlignment(Qt.AlignCenter)
            item.setMinimumHeight(65)
            item.setStyleSheet("""
                background-color: #1C3047;
                color: #E5F0F8;
                border: 1px solid #304760;
                border-radius: 10px;
                font-size: 13px;
                font-weight: bold;
            """)

            category_row.addWidget(item)
            self.category_labels[name] = item

        category_layout.addLayout(category_row)
        layout.addWidget(category_card)

        # TABLICA PROLAZAKA

        table_card = QFrame()
        table_card.setStyleSheet("""
            QFrame {
                background-color: #152238;
                border: 1px solid #293D57;
                border-radius: 14px;
            }
        """)

        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(20, 18, 20, 18)
        table_layout.setSpacing(12)

        table_title = QLabel("EVIDENCIJA PROLAZAKA")
        table_title.setStyleSheet("""
            color: #FFFFFF;
            font-size: 15px;
            font-weight: bold;
            border: none;
        """)

        table_layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)

        self.table.setHorizontalHeaderLabels([
            "ID vozila",
            "Kategorija",
            "Prometna traka",
            "Smjer",
            "Vrijeme prolaska",
            "Trajanje (s)"
        ])

        self.table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.table.setAlternatingRowColors(True)

        self.table.verticalHeader().setVisible(False)

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #101D30;
                alternate-background-color: #182A40;
                color: #E5F0F8;
                border: 1px solid #293D57;
                border-radius: 8px;
                gridline-color: #293D57;
                font-size: 12px;
                selection-background-color: #176C72;
            }

            QHeaderView::section {
                background-color: #213750;
                color: #DDEAF5;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #36516A;
                font-weight: bold;
            }
        """)

        self.table.setMinimumHeight(180)

        table_layout.addWidget(self.table)

        self.empty_label = QLabel(
            "Nema evidentiranih prolazaka za prikaz."
        )
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("""
            color: #91A6BE;
            font-size: 12px;
            border: none;
        """)

        table_layout.addWidget(self.empty_label)

        layout.addWidget(table_card, 1)

        # NAPOMENA O ZASTITI PODATAKA

        privacy_label = QLabel(
            "Registarske oznake nisu dostupne u ovom "
            "pregledu. Zaštićeni OCR izvještaji zahtijevaju "
            "ponovnu autentifikaciju."
        )
        privacy_label.setWordWrap(True)
        privacy_label.setStyleSheet("""
            color: #91A6BE;
            font-size: 11px;
            padding: 6px;
        """)

        layout.addWidget(privacy_label)

    def create_card(self, parent_layout, title, color):

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #152238;
                border: 1px solid #293D57;
                border-radius: 14px;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(8)

        heading = QLabel(title)
        heading.setStyleSheet("""
            color: #91A6BE;
            font-size: 11px;
            font-weight: bold;
            border: none;
        """)

        value = QLabel("—")
        value.setStyleSheet(f"""
            color: {color};
            font-size: 32px;
            font-weight: bold;
            border: none;
        """)

        card_layout.addWidget(heading)
        card_layout.addWidget(value)

        parent_layout.addWidget(card)

        return value

    def clear_results(self):
        """Uklanja prethodne rezultate iz prikaza."""

        self.current_session = None

        self.total_value.setText("—")
        self.correct_value.setText("—")
        self.opposite_value.setText("—")

        for name, label in self.category_labels.items():
            label.setText(f"{name}\n—")

        self.table.setRowCount(0)
        self.empty_label.setVisible(True)

    def set_results(self, session_id, statistics, events):
        """
        Prikazuje rezultate jedne odabrane sesije.

        statistics je rjecnik s brojcanim podacima.
        events je popis evidentiranih prolazaka.

        OCR podaci se namjerno ne koriste.
        """

        self.clear_results()
        self.current_session = session_id

        self.total_value.setText(
            str(statistics.get("total_count", 0))
        )

        self.correct_value.setText(
            str(statistics.get("correct_count", 0))
        )

        self.opposite_value.setText(
            str(statistics.get("opposite_count", 0))
        )

        categories = statistics.get(
            "category_counts", {}
        )

        for name, label in self.category_labels.items():

            label.setText(
                f"{name}\n{categories.get(name, 0)}"
            )

        self.table.setRowCount(len(events))

        for row, event in enumerate(events):

            values = [
                event.get("track_id", ""),
                event.get("vehicle_type", ""),
                event.get("lane", ""),
                event.get("direction", ""),
                event.get("counted_at", ""),
                event.get("duration_seconds", "")
            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)

                self.table.setItem(
                    row,
                    column,
                    item
                )

        self.empty_label.setVisible(
            len(events) == 0
        )
