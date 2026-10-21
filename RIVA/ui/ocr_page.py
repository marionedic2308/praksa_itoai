import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QComboBox
)
from core.sessions import DATABASE_PATH
from core.ocr_runner import run_ocr_for_saved_photos


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
        layout.addWidget(self.table, 3)

        lower = QHBoxLayout()
        lower.setSpacing(18)

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
        actions.setSpacing(12)
        self.refresh_button = QPushButton("Osvježi podatke")
        self.refresh_button.clicked.connect(self.refresh_data)
        self.ocr_button = QPushButton("Pokreni OCR analizu spremljenih fotografija")
        self.ocr_button.clicked.connect(self.run_ocr)
        self.ocr_button.setMinimumHeight(48)
        actions.addWidget(self.ocr_button)
        self.refresh_button.setMinimumHeight(44)
        actions.addWidget(self.refresh_button)

        self.confirm_button = QPushButton("Potvrdi očitanje")
        self.confirm_button.clicked.connect(
            lambda: self.set_review_status("CONFIRMED")
        )
        self.confirm_button.setMinimumHeight(44)
        actions.addWidget(self.confirm_button)

        self.reject_button = QPushButton("Odbaci očitanje")
        self.reject_button.clicked.connect(
            lambda: self.set_review_status("REJECTED")
        )
        self.reject_button.setMinimumHeight(44)
        actions.addWidget(self.reject_button)

        actions.addStretch()
        self.status_label = QLabel(
            "OCR rezultati nisu automatski potvrđeni."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #91A6BE;")
        actions.addWidget(self.status_label)
        lower.addLayout(actions, 1)

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
                           o.review_status
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
                    elif col == 8:
                        labels = {
                            "PENDING": "Treba potvrda",
                            "CONFIRMED": "Potvr\u0111eno",
                            "REJECTED": "Nije potvr\u0111eno",
                        }
                        text = labels.get(value, "Nije obra\u0111eno")
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
                self.photo_label.setText("Fotografija nije prona?ena.")
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
                "Fotografiju nije mogu?e prikazati."
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
        if getattr(self, "ocr_worker", None) is not None:
            if self.ocr_worker.isRunning():
                return

        self.ocr_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.confirm_button.setEnabled(False)
        self.reject_button.setEnabled(False)
        self.status_label.setText("OCR obrada u tijeku...")

        self.ocr_worker = OCRWorker(self)
        self.ocr_worker.finished_ocr.connect(self.on_ocr_finished)
        self.ocr_worker.failed_ocr.connect(self.on_ocr_failed)
        self.ocr_worker.finished.connect(self.on_ocr_thread_finished)
        self.ocr_worker.start()

    def on_ocr_finished(self, stats):
        self.refresh_data()
        message = (
            f"Obrada zavrsena. Fotografija: {stats['photos']} | "
            f"Spremljeno: {stats['saved']} | "
            f"Bez teksta: {stats['no_text']} | "
            f"Postojeci: {stats['existing']} | "
            f"Greske: {stats['errors']}"
        )
        self.status_label.setText(message)
        QMessageBox.information(self, "OCR obrada", message)

    def on_ocr_failed(self, error):
        self.status_label.setText(f"OCR greska: {error}")
        QMessageBox.critical(self, "OCR obrada", str(error))

    def on_ocr_thread_finished(self):
        self.ocr_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.confirm_button.setEnabled(True)
        self.reject_button.setEnabled(True)

    def set_review_status(self, status):
        event_id = self.selected_event_id()
        if event_id is None:
            QMessageBox.information(
                self, "OCR provjera", "Najprije odaberi prolazak."
            )
            return

        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.execute("""
                    UPDATE ocr_results
                    SET review_status = ?
                    WHERE event_id = ? AND review_status = 'PENDING'
                """, (status, event_id))
                changed = cursor.rowcount

            if not changed:
                QMessageBox.information(
                    self, "OCR provjera",
                    "Za ovaj prolazak nema OCR zapisa koji čeka provjeru."
                )
                return

            self.status_label.setText(
                "Status očitanja: " + status
            )
            self.refresh_data()
        except Exception as error:
            QMessageBox.critical(
                self, "OCR provjera",
                f"Spremanje nije uspjelo: {type(error).__name__}"
            )
