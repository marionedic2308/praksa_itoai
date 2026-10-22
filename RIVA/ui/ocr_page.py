import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QComboBox, QLineEdit, QFrame, QGridLayout, QScrollArea
)
from core.sessions import DATABASE_PATH
from core.ocr_runner import run_ocr_for_saved_photos
from core.ocr_database import initialize_manual_ocr, save_manual_registration, save_review_decision
from core.audit import log_event


ROOT = Path(__file__).resolve().parent.parent



class OCRWorker(QThread):
    finished_ocr = Signal(dict)
    failed_ocr = Signal(str)

    def run(self):
        try:
            result = run_ocr_for_saved_photos()
            self.finished_ocr.emit(result)
        except Exception as error:
            self.failed_ocr.emit(
                f"{type(error).__name__}: {error}"
            )


class OCRPage(QWidget):
    def __init__(self):
        super().__init__()
        initialize_manual_ocr()
        self.setStyleSheet("""
            QWidget { background: #0B1423; color: #E5F0F8; }
            QLabel { color: #E5F0F8; }
            QGroupBox {
                border: 1px solid #304760; border-radius: 10px;
                margin-top: 12px; padding: 12px;
                font-weight: bold;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; }
            QPushButton {
                background: #203E4B; color: #E5F0F8;
                border: 1px solid #38566B; border-radius: 7px;
                padding: 9px 14px;
            }
            QPushButton:hover { background: #285363; }
            QPushButton:disabled { color: #738397; }
            QTableWidget {
                background: #111E30; alternate-background-color: #17263A;
                gridline-color: #304760; border: 1px solid #304760;
                selection-background-color: #245B65;
            }
            QHeaderView::section {
                background: #203E4B; color: #E5F0F8;
                padding: 7px; border: none;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(16)

        title = QLabel("OCR ANALIZA REGISTARSKIH PLOČICA")
        title.setStyleSheet("font-size: 23px; font-weight: bold; color: #5DD9D0;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Pregled evidentiranih prolazaka, OCR očitanja i fotografija."
        )
        subtitle.setStyleSheet("color: #91A6BE; font-size: 12px;")
        layout.addWidget(subtitle)

        session_row = QHBoxLayout()
        session_title = QLabel("ODABIR SESIJE")
        session_title.setStyleSheet(
            "color:#91A6BE; font-size:12px; font-weight:bold;"
        )
        session_row.addWidget(session_title)

        self.session_selector = QComboBox()
        self.session_selector.setMinimumHeight(42)
        self.session_selector.setStyleSheet("""
            QComboBox {
                background:#142438;
                color:#E5F0F8;
                border:1px solid #304760;
                border-radius:8px;
                padding:8px 14px;
            }
            QComboBox::drop-down {
                border:none;
                width:30px;
            }
        """)
        session_row.addWidget(self.session_selector, 1)
        layout.addLayout(session_row)

        self.session_selector.currentIndexChanged.connect(
            lambda _: self.refresh_data()
        )

        stats = QHBoxLayout()
        self.total_label = QLabel("Prolasci: —")
        self.ocr_label = QLabel("OCR zapisi: —")
        self.pending_label = QLabel("Čeka provjeru: —")
        for label in (self.total_label, self.ocr_label, self.pending_label):
            label.setMinimumHeight(54)
            label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            label.setStyleSheet(
                "background: #142438; border: 1px solid #304760;"
                "border-radius: 10px; padding: 0 16px;"
                "font-size: 13px; font-weight: bold;"
            )
            stats.addWidget(label)
        layout.addLayout(stats)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Sesija", "Vrijeme", "Vozilo", "Traka",
            "Smjer", "Registracija", "Pouzdanost", "Status"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setWordWrap(False)
        self.table.setMinimumHeight(250)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        for column, width in {
            0: 62, 1: 125, 2: 195, 3: 100,
            4: 85, 5: 145, 6: 135, 7: 105
        }.items():
            header.resizeSection(column, width)
        header.setSectionResizeMode(8, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self.show_selected_photos)
        self.table.itemSelectionChanged.connect(self.sync_manual_plate)
        layout.addWidget(self.table, 3)

        lower = QHBoxLayout()
        lower.setSpacing(24)

        photo_group = QGroupBox("Fotografija odabranog prolaska")
        photo_layout = QVBoxLayout(photo_group)
        self.photo_label = QLabel("Odaberi prolazak u tablici.")
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setMinimumSize(280, 150)
        self.photo_label.setMaximumHeight(230)
        self.photo_label.setStyleSheet(
            "background: #111E30; border: 1px solid #304760; border-radius: 6px;"
        )
        self.photo_label.setScaledContents(False)
        photo_layout.addWidget(self.photo_label)
        self.photo_info = QLabel("")
        self.photo_info.setWordWrap(True)
        photo_layout.addWidget(self.photo_info)
        lower.addWidget(photo_group, 2)

        actions = QVBoxLayout()
        actions.setSpacing(15)
        self.refresh_button = QPushButton("Osvježi podatke")
        # RIVA_STYLE_REFRESH_BUTTON
        self.refresh_button.setStyleSheet('''
            QPushButton {
                background-color: #203E52;
                color: #F0F8FC;
                border: 1px solid #3B657D;
                border-radius: 9px;
                padding: 11px 14px;
                font-size: 12px;
                font-weight: 600;
                min-height: 23px;
            }
            QPushButton:hover {
                background-color: #2B5067;
            }
            QPushButton:disabled {
                background-color: #233342;
                color: #71899B;
            }
        ''')
        self.refresh_button.clicked.connect(self.refresh_data)
        self.ocr_button = QPushButton("Pokreni OCR analizu spremljenih fotografija")
        # RIVA_STYLE_OCR_BUTTON
        self.ocr_button.setStyleSheet('''
            QPushButton {
                background-color: #176B73;
                color: #F0F8FC;
                border: 1px solid #2BA6AA;
                border-radius: 9px;
                padding: 11px 14px;
                font-size: 12px;
                font-weight: 600;
                min-height: 23px;
            }
            QPushButton:hover {
                background-color: #20858C;
            }
            QPushButton:disabled {
                background-color: #233342;
                color: #71899B;
            }
        ''')
        self.ocr_button.clicked.connect(self.run_ocr)
        self.ocr_button.setMinimumHeight(48)
        actions.addWidget(self.ocr_button)
        self.refresh_button.setMinimumHeight(44)
        actions.addWidget(self.refresh_button)

        self.confirm_button = QPushButton("Potvrdi očitanje")
        # RIVA_STYLE_CONFIRM_BUTTON
        self.confirm_button.setStyleSheet('''
            QPushButton {
                background-color: #176B59;
                color: #F0F8FC;
                border: 1px solid #2CA080;
                border-radius: 9px;
                padding: 11px 14px;
                font-size: 12px;
                font-weight: 600;
                min-height: 23px;
            }
            QPushButton:hover {
                background-color: #20846D;
            }
            QPushButton:disabled {
                background-color: #233342;
                color: #71899B;
            }
        ''')
        self.confirm_button.clicked.connect(
            lambda: self.set_review_status("CONFIRMED")
        )
        self.confirm_button.setMinimumHeight(44)
        actions.addWidget(self.confirm_button)

        self.reject_button = QPushButton("Odbaci očitanje")
        # RIVA_STYLE_REJECT_BUTTON
        self.reject_button.setStyleSheet('''
            QPushButton {
                background-color: #713B47;
                color: #F0F8FC;
                border: 1px solid #A65768;
                border-radius: 9px;
                padding: 11px 14px;
                font-size: 12px;
                font-weight: 600;
                min-height: 23px;
            }
            QPushButton:hover {
                background-color: #884654;
            }
            QPushButton:disabled {
                background-color: #233342;
                color: #71899B;
            }
        ''')
        self.reject_button.clicked.connect(
            lambda: self.set_review_status("REJECTED")
        )
        self.reject_button.setMinimumHeight(44)
        actions.addWidget(self.reject_button)

        manual_label = QLabel("RU\u010cNI UNOS / KOREKCIJA")
        manual_label.setStyleSheet("color:#91A6BE; font-weight:bold; font-size:11px;")
        actions.addWidget(manual_label)
        self.manual_plate_input = QLineEdit()
        # RIVA_MANUAL_INPUT_STYLE
        self.manual_plate_input.setStyleSheet('''
            QLineEdit {
                background: #13283D;
                color: #F0F8FC;
                border: 1px solid #3A6077;
                border-radius: 9px;
                padding: 10px 13px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #37D5C7;
            }
        ''')
        self.manual_plate_input.setPlaceholderText("Npr. A12-B-345")
        self.manual_plate_input.setMaxLength(16)
        self.manual_plate_input.setMinimumHeight(40)
        self.manual_plate_input.setStyleSheet(
            "QLineEdit {background:#142438; color:#E5F0F8; "
            "border:1px solid #304760; border-radius:7px; padding:8px;}"
        )
        actions.addWidget(self.manual_plate_input)
        self.manual_save_button = QPushButton("Spremi oznaku")
        self.manual_save_button.setMinimumHeight(44)
        self.manual_save_button.clicked.connect(self.save_manual_plate)
        actions.addWidget(self.manual_save_button)

        # RIVA_OCR_CARD_LAYOUT_V2
        # Existing buttons and signal connections are preserved.
        while actions.count():
            actions.takeAt(0)

        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
        cards.setColumnStretch(0, 1)
        cards.setColumnStretch(1, 1)

        def make_card(title, description, button, color):
            card = QFrame()
            card.setObjectName("ocrActionCard")
            card.setMinimumHeight(125)
            card.setStyleSheet("""
                QFrame#ocrActionCard {
                    background-color: #16273D;
                    border: 1px solid #304760;
                    border-radius: 13px;
                }
                QFrame#ocrActionCard QLabel {
                    background: transparent;
                    border: none;
                }
            """)

            body = QVBoxLayout(card)
            body.setContentsMargins(14, 13, 14, 13)
            body.setSpacing(7)

            heading = QLabel(title)
            heading.setWordWrap(True)
            heading.setStyleSheet(
                "color:#EAF5FC; font-size:12px; font-weight:bold;"
            )
            body.addWidget(heading)

            detail = QLabel(description)
            detail.setWordWrap(True)
            detail.setStyleSheet("color:#91A6BE; font-size:11px;")
            body.addWidget(detail)

            body.addStretch(1)

            button.setMinimumHeight(38)
            button.setMaximumHeight(42)
            button.setStyleSheet("""
                QPushButton {
                    background-color: %s;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 7px 9px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    border: 1px solid #5DD9D0;
                }
                QPushButton:disabled {
                    background-color: #26394B;
                    color: #8798A8;
                }
            """ % color)
            body.addWidget(button)

            return card

        cards.addWidget(make_card(
            "OCR ANALIZA",
            "Obrada spremljenih fotografija",
            self.ocr_button, "#176B73"
        ), 0, 0)

        cards.addWidget(make_card(
            "OSVJE\u017dAVANJE",
            "U\u010ditaj najnovije rezultate",
            self.refresh_button, "#31536A"
        ), 0, 1)

        cards.addWidget(make_card(
            "POTVRDA O\u010cITANJA",
            "Potvrdi odabranu registraciju",
            self.confirm_button, "#176B59"
        ), 1, 0)

        cards.addWidget(make_card(
            "ODBACIVANJE",
            "Odbaci odabrano o\u010ditanje",
            self.reject_button, "#713B47"
        ), 1, 1)

        actions.addLayout(cards)

        manual_card = QFrame()
        manual_card.setObjectName("ocrManualCard")
        manual_card.setMinimumHeight(164)
        manual_card.setStyleSheet("""
            QFrame#ocrManualCard {
                background-color: #16273D;
                border: 1px solid #304760;
                border-radius: 13px;
            }
            QFrame#ocrManualCard QLabel {
                background: transparent;
                border: none;
            }
        """)

        manual_body = QVBoxLayout(manual_card)
        manual_body.setContentsMargins(15, 14, 15, 14)
        manual_body.setSpacing(10)

        manual_heading = QLabel("RU\u010cNI UNOS / KOREKCIJA")
        manual_heading.setStyleSheet(
            "color:#5DD9D0; font-size:12px; font-weight:bold;"
        )
        manual_body.addWidget(manual_heading)

        manual_detail = QLabel(
            "Unesi ili ispravi registarsku oznaku odabranog prolaska."
        )
        manual_detail.setWordWrap(True)
        manual_detail.setStyleSheet(
            "color:#91A6BE; font-size:11px;"
        )
        manual_body.addWidget(manual_detail)

        self.manual_plate_input.setMinimumHeight(39)
        self.manual_plate_input.setStyleSheet("""
            QLineEdit {
                background: #102035;
                color: #F0F8FC;
                border: 1px solid #39546E;
                border-radius: 8px;
                padding: 7px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #5DD9D0;
            }
        """)
        manual_body.addWidget(self.manual_plate_input)

        self.manual_save_button.setMinimumHeight(39)
        self.manual_save_button.setStyleSheet("""
            QPushButton {
                background: #176B73;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #20858C;
            }
        """)
        manual_body.addWidget(self.manual_save_button)
        actions.addWidget(manual_card)

        self.status_label = QLabel(
            "OCR rezultati nisu automatski potvr\u0111eni."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "color:#91A6BE; font-size:11px;"
        )
        actions.addWidget(self.status_label)
        actions.addStretch()

        # Scroll prevents cards from being compressed vertically.
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_content.setLayout(actions)

        action_scroll = QScrollArea()
        action_scroll.setWidgetResizable(True)
        action_scroll.setFrameShape(QFrame.NoFrame)
        action_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        action_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )
        action_scroll.setWidget(scroll_content)
        action_scroll.setMinimumWidth(350)
        action_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #102035;
                width: 9px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #39546E;
                border-radius: 4px;
                min-height: 28px;
            }
        """)

        lower.addWidget(action_scroll, 2)

        layout.addLayout(lower, 2)
        self.refresh_data()

    def refresh_data(self):
        from datetime import datetime

        selected_event = self.selected_event_id()
        previous = self.session_selector.currentData()

        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                sessions = conn.execute("""
                    SELECT id, session_code, started_at
                    FROM traffic_sessions
                    ORDER BY id DESC
                """).fetchall()

                self.session_selector.blockSignals(True)
                self.session_selector.clear()

                for sid, code, started in sessions:
                    try:
                        date = datetime.fromisoformat(
                            str(started)
                        ).strftime("%d.%m.%Y. %H:%M:%S")
                    except (ValueError, TypeError):
                        date = str(started or "-")

                    self.session_selector.addItem(
                        f"{code}  |  {date}", sid
                    )

                self.session_selector.addItem(
                    "Sve sesije", "ALL"
                )

                index = self.session_selector.findData(previous)
                self.session_selector.setCurrentIndex(
                    index if index >= 0 else 0
                )
                self.session_selector.blockSignals(False)

                selected_session = self.session_selector.currentData()

                query = """
                    SELECT e.id, s.session_code, e.counted_at,
                           e.vehicle_type, e.lane, e.direction,
                           o.registration_text, o.confidence,
                           o.review_status, o.entry_source
                    FROM vehicle_events e
                    JOIN traffic_sessions s ON s.id = e.session_id
                    LEFT JOIN ocr_results o ON o.event_id = e.id
                """
                params = []

                if selected_session not in (None, "ALL"):
                    query += " WHERE e.session_id = ?"
                    params.append(selected_session)

                query += " ORDER BY e.id DESC"
                rows = conn.execute(query, params).fetchall()

            self.table.setRowCount(0)
            for row_data in rows:
                row = self.table.rowCount()
                self.table.insertRow(row)

                for col, value in enumerate(row_data):
                    if col == 2 and value:
                        try:
                            text = datetime.fromisoformat(
                                str(value)
                            ).strftime("%d.%m.%Y. %H:%M:%S")
                        except (ValueError, TypeError):
                            text = str(value)
                    elif col == 7 and value is not None:
                        text = f"{float(value) * 100:.1f}%"
                    elif col == 6 and row_data[8] == "REJECTED":
                        text = "Odbačeno"
                    elif col == 7 and row_data[8] == "REJECTED":
                        text = "?"
                    elif col == 8:
                        source = row_data[9]
                        if value == "REJECTED":
                            text = "Ručno odbačeno"
                        elif value == "CONFIRMED":
                            text = (
                                "Ručno potvrđeno"
                                if source in (
                                    "MANUAL_ENTRY",
                                    "MANUAL_CORRECTION",
                                    "MANUAL_CONFIRMATION"
                                )
                                else "Potvrđeno"
                            )
                        elif value == "PENDING":
                            text = "Na provjeri"
                        else:
                            text = "Nije obrađeno"
                    else:
                        text = "\u2014" if value is None else str(value)

                    item = QTableWidgetItem(text)
                    if col == 0:
                        item.setData(Qt.UserRole, int(row_data[0]))
                    self.table.setItem(row, col, item)

            ocr_count = sum(r[8] is not None for r in rows)
            pending_count = sum(r[8] == "PENDING" for r in rows)

            self.total_label.setText(f"Prolasci: {len(rows)}")
            self.ocr_label.setText(f"OCR zapisi: {ocr_count}")
            self.pending_label.setText(
                f"\u010ceka provjeru: {pending_count}"
            )
            self.status_label.setText(
                "Podaci u\u010ditani iz lokalne baze."
            )

            restored = False
            if selected_event is not None:
                for row in range(self.table.rowCount()):
                    if int(self.table.item(row, 0).text()) == selected_event:
                        self.table.selectRow(row)
                        restored = True
                        break

            if not restored and self.table.rowCount():
                self.table.selectRow(0)

            if not rows:
                self.photo_label.clear()
                self.photo_label.setText(
                    "Nema evidentiranih prolazaka za ovu sesiju."
                )
                self.photo_info.setText(
                    "Odaberi drugu sesiju ili pokreni novu analizu."
                )

        except Exception as error:
            self.status_label.setText(
                f"U\u010ditavanje nije uspjelo: "
                f"{type(error).__name__}: {error}"
            )

    def selected_event_id(self):
        row = self.table.currentRow()
        if row < 0 or self.table.item(row, 0) is None:
            return None
        return int(self.table.item(row, 0).text())

    def show_selected_photos(self):
        event_id = self.selected_event_id()
        row = self.table.currentRow()

        if event_id is None:
            return

        session_code = self.table.item(row, 1).text()
        folder = ROOT / "data" / "sessions" / session_code / "ocr"

        plate_folder = folder / "plocice"
        candidate_folder = folder / "kandidati"

        best_plate = plate_folder / (
            f"event_{event_id:08d}_najbolja_plocica.jpg"
        )

        if best_plate.is_file():
            selected_photo = best_plate
        else:
            plates = list(plate_folder.glob(
                f"event_{event_id:08d}_*_plocica.jpg"
            ))
            candidates = list(candidate_folder.glob(
                f"event_{event_id:08d}_kandidat_*.jpg"
            ))

            photos = plates if plates else candidates

            if not photos:
                self.photo_label.setPixmap(QPixmap())
                self.photo_label.setText("Fotografija nije pronađena.")
                self.photo_info.setText(
                    f"Prolazak {event_id} ? sesija {session_code}"
                )
                return

            def photo_quality(photo):
                import cv2
                image = cv2.imread(str(photo))
                if image is None:
                    return -1

                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                sharpness = cv2.Laplacian(
                    gray, cv2.CV_64F
                ).var()

                height, width = image.shape[:2]
                return sharpness + (width * height) / 1000

            selected_photo = max(photos, key=photo_quality)

        pixmap = QPixmap(str(selected_photo))

        if pixmap.isNull():
            self.photo_label.setPixmap(QPixmap())
            self.photo_label.setText(
                "Fotografiju nije moguće prikazati."
            )
            return

        self.photo_label.setText("")
        self.photo_label.setPixmap(
            pixmap.scaled(
                self.photo_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

        self.photo_info.setText(
            f"Prolazak {event_id} \u00b7 automatski odabrana fotografija"
        )


    def run_ocr(self):
        # RIVA_OCR_RUN_COUNTER_V1
        if getattr(self, "ocr_worker", None) is not None:
            if self.ocr_worker.isRunning():
                return

        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ocr_run_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute(
                    "INSERT INTO ocr_run_history DEFAULT VALUES"
                )
        except Exception as error:
            QMessageBox.critical(
                self, "OCR evidencija",
                f"Nije moguce evidentirati OCR obradu: {error}"
            )
            return

        self.ocr_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.confirm_button.setEnabled(False)
        self.reject_button.setEnabled(False)
        self.manual_save_button.setEnabled(False)
        self.status_label.setText("OCR obrada u tijeku...")

        self.ocr_worker = OCRWorker(self)
        self.ocr_worker.finished_ocr.connect(self.on_ocr_finished)
        self.ocr_worker.failed_ocr.connect(self.on_ocr_failed)
        self.ocr_worker.finished.connect(self.on_ocr_thread_finished)
        self.ocr_worker.start()

    def on_ocr_finished(self, stats):
        self.refresh_data()
        message = (
            f"Obrada završena. Fotografija: {stats['photos']} | "
            f"Spremljeno: {stats['saved']} | "
            f"Bez teksta: {stats['no_text']} | "
            f"Postojeći: {stats['existing']} | "
            f"Greške: {stats['errors']}"
        )
        self.status_label.setText(message)
        QMessageBox.information(self, "OCR obrada", message)

    def on_ocr_failed(self, error):
        self.status_label.setText(f"OCR greška: {error}")
        QMessageBox.critical(self, "OCR obrada", str(error))

    def on_ocr_thread_finished(self):
        self.ocr_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.confirm_button.setEnabled(True)
        self.reject_button.setEnabled(True)
        self.manual_save_button.setEnabled(True)

    def set_review_status(self, status):
        event_id = self.selected_event_id()
        if event_id is None:
            QMessageBox.information(
                self, "OCR provjera", "Najprije odaberi prolazak."
            )
            return

        action = (
            "odbaciti" if status == "REJECTED"
            else "potvrditi"
        )
        answer = QMessageBox.question(
            self, "OCR provjera",
            f"?eli? li {action} o?itanje za prolazak {event_id}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return

        try:
            user = getattr(self.window(), "username", None)
            save_review_decision(event_id, status, user)
            try:
                log_event(
                    "OCR_MANUAL_REJECTED"
                    if status == "REJECTED"
                    else "OCR_MANUAL_CONFIRMED",
                    username=user,
                    description=f"OCR odluka za prolazak {event_id}",
                    status="SUCCESS"
                )
            except Exception:
                pass

            self.refresh_data()
            self.status_label.setText(
                "Ručno odbačeno."
                if status == "REJECTED"
                else "Ručno potvrđeno."
            )
        except Exception as error:
            QMessageBox.warning(
                self, "OCR provjera",
                f"Spremanje nije uspjelo: {error}"
            )

    def sync_manual_plate(self):
        row = self.table.currentRow()
        if row < 0:
            self.manual_plate_input.clear()
            return
        cell = self.table.item(row, 6)
        value = cell.text().strip() if cell else ""
        self.manual_plate_input.setText("" if value in ("", "?", "Odbačeno") else value)

    def save_manual_plate(self):
        event_id = self.selected_event_id()
        if event_id is None:
            QMessageBox.information(self, "Ručni unos", "Najprije odaberi prolazak.")
            return
        registration = self.manual_plate_input.text().strip().upper()
        row = self.table.currentRow()
        previous_cell = self.table.item(row, 6)
        previous = previous_cell.text().strip() if previous_cell else ""
        if registration == previous:
            QMessageBox.information(self, "Ručni unos", "Registracija nije promijenjena.")
            return
        message = ("Spremiti registraciju za prolazak " + str(event_id) + "?\n\n"
                   + ("Prethodna: " + previous + "\n" if previous not in ("", "\u2014") else "")
                   + "Nova: " + registration + "\n\nIzmjena će biti evidentirana.")
        if QMessageBox.question(self, "Potvrda izmjene", message,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            user = getattr(self.window(), "username", None)
            action = save_manual_registration(event_id, registration, user)
            # U evidenciji aktivnosti nema stvarnih registracija.
            try:
                log_event("OCR_MANUAL_CORRECTION" if action == "MANUAL_CORRECTION" else "OCR_MANUAL_ENTRY",
                          username=user, description=f"Ručna intervencija za prolazak {event_id}",
                          status="SUCCESS")
            except Exception:
                pass  # Podaci i povijest izmjene vec su spremljeni u bazi.
            self.refresh_data()
            self.status_label.setText("Ručna registracija uspješno spremljena.")
        except Exception as error:
            QMessageBox.critical(self, "Ručni unos", f"Spremanje nije uspjelo: {error}")
