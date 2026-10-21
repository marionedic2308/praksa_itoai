import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox
)
from core.sessions import DATABASE_PATH
from core.ocr_runner import run_ocr_for_saved_photos


ROOT = Path(__file__).resolve().parent.parent


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
        selected_event = self.selected_event_id()
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                rows = conn.execute("""
                    SELECT e.id, s.session_code, e.counted_at,
                           e.vehicle_type, e.lane, e.direction,
                           o.registration_text, o.confidence,
                           o.review_status
                    FROM vehicle_events e
                    JOIN traffic_sessions s ON s.id = e.session_id
                    LEFT JOIN ocr_results o ON o.event_id = e.id
                    ORDER BY e.id DESC
                """).fetchall()

                ocr_count = conn.execute(
                    "SELECT COUNT(*) FROM ocr_results"
                ).fetchone()[0]
                pending_count = conn.execute("""
                    SELECT COUNT(*) FROM ocr_results
                    WHERE review_status = 'PENDING'
                """).fetchone()[0]

            self.table.setRowCount(0)
            for row_data in rows:
                row = self.table.rowCount()
                self.table.insertRow(row)
                for col, value in enumerate(row_data):
                    if col == 7 and value is not None:
                        text = f"{float(value) * 100:.1f}%"
                    else:
                        text = "—" if value is None else str(value)
                    item = QTableWidgetItem(text)
                    if col == 0:
                        item.setData(Qt.UserRole, int(row_data[0]))
                    self.table.setItem(row, col, item)

            self.total_label.setText(f"Prolasci: {len(rows)}")
            self.ocr_label.setText(f"OCR zapisi: {ocr_count}")
            self.pending_label.setText(f"Čeka provjeru: {pending_count}")
            self.status_label.setText("Podaci učitani iz lokalne baze.")

            if selected_event is not None:
                for row in range(self.table.rowCount()):
                    if int(self.table.item(row, 0).text()) == selected_event:
                        self.table.selectRow(row)
                        break
            if self.table.currentRow() < 0 and self.table.rowCount():
                self.table.selectRow(0)

            if not rows:
                self.photo_label.setText("Još nema evidentiranih prolazaka.")
                self.photo_info.setText("Pokreni analizu vozila pa osvježi podatke.")
        except Exception as error:
            self.status_label.setText(
                f"Učitavanje nije uspjelo: {type(error).__name__}"
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
        patterns = [
            f"event_{event_id:08d}_*_plocica.jpg",
            f"event_{event_id:08d}_kandidat_*.jpg",
        ]
        photos = []
        for subfolder in ("plocice", "kandidati"):
            directory = folder / subfolder
            for pattern in patterns:
                photos.extend(directory.glob(pattern))

        photos = sorted(set(photos))
        if not photos:
            self.photo_label.setPixmap(QPixmap())
            self.photo_label.setText("Fotografija nije pronađena.")
            self.photo_info.setText(
                f"Prolazak {event_id} · sesija {session_code}"
            )
            return

        pixmap = QPixmap(str(photos[0]))
        if pixmap.isNull():
            self.photo_label.setText("Fotografiju nije moguće prikazati.")
            return

        self.photo_label.setText("")
        self.photo_label.setPixmap(
            pixmap.scaled(
                600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )
        self.photo_info.setText(
            f"Prolazak {event_id} · {len(photos)} fotografija · "
            f"Prikaz: {photos[0].name}"
        )

    def run_ocr(self):
        self.ocr_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.status_label.setText(
            "OCR obrada u tijeku. Prva obrada moze potrajati..."
        )
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            stats = run_ocr_for_saved_photos()
            self.refresh_data()
            self.status_label.setText(
                f"Obrada zavrsena. Fotografija: {stats['photos']} | "
                f"Spremljeno: {stats['saved']} | "
                f"Bez valjanog teksta: {stats['no_text']} | "
                f"Vec postojeci: {stats['existing']} | "
                f"Greske: {stats['errors']}"
            )
            QMessageBox.information(
                self, "OCR obrada",
                self.status_label.text()
            )
        except Exception as error:
            self.status_label.setText(
                f"OCR obrada nije uspjela: {type(error).__name__}"
            )
            QMessageBox.critical(
                self, "OCR obrada",
                self.status_label.text()
            )
        finally:
            self.ocr_button.setEnabled(True)
            self.refresh_button.setEnabled(True)

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
