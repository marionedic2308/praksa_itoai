from PySide6.QtWidgets import QScrollArea
"""RIVA - LIVE video, RTSP prijava, detekcija, tracking i brojanje."""

import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import cv2
from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFileDialog, QLineEdit, QComboBox, QMessageBox, QSizePolicy,
)

from core.vehicle_detector import VehicleDetector
from core.vehicle_tracker import VehicleTracker
from core.vehicle_counter import VehicleCounter
from core.ocr_capture import (
    UpraviteljOCRKandidata,
    izdvoji_vozilo,
    pripremi_ocr_mape,
    spremi_ocr_kandidate,
)
from core.sessions import (create_session, save_session_statistics,
                           add_vehicle_event, finish_session)
from ui.line_calibration import LineCalibrationDialog

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CALIBRATION_DIR = PROJECT_ROOT / "data" / "calibrations"


def clean_rtsp_source(source):
    """Uklanja eventualne pristupne podatke iz RTSP adrese."""
    parts = urlsplit(source)
    if parts.scheme.lower() != "rtsp":
        return source
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parts.port is not None:
        host += f":{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, parts.query, ""))


def rtsp_connection_url(source, username, password):
    """Sastavlja RTSP URL samo u memoriji, uz kodiranje posebnih znakova."""
    parts = urlsplit(source)
    if parts.scheme.lower() != "rtsp" or not parts.hostname:
        raise ValueError("Neispravna RTSP adresa")
    host = parts.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parts.port is not None:
        host += f":{parts.port}"
    if username:
        host = f"{quote(username, safe='')}:{quote(password, safe='')}@{host}"
    return urlunsplit((parts.scheme, host, parts.path, parts.query, ""))


def calibration_path(source):
    """Kalibracija ovisi o adresi kamere, ali nikada o lozinki."""
    digest = hashlib.sha256(clean_rtsp_source(source).encode("utf-8")).hexdigest()[:24]
    return CALIBRATION_DIR / f"camera_{digest}.json"


def load_calibration(source, width=None, height=None):
    path = calibration_path(source)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data.get("lanes"), list) or not data["lanes"]:
            return None
        if width is not None and (data.get("frame_width") != width or data.get("frame_height") != height):
            return None
        for lane in data["lanes"]:
            for key in ("line_1", "line_2"):
                points = lane[key]
                if len(points) != 2 or any(len(p) != 2 for p in points):
                    return None
        return data["lanes"]
    except (OSError, ValueError, TypeError, KeyError):
        return None


def draw_lanes(frame, lanes):
    colors = [(208, 217, 93), (102, 209, 255), (250, 139, 167), (133, 222, 105)]
    for index, lane in enumerate(lanes):
        color = colors[index % len(colors)]
        for line_key, suffix in (("line_1", "L1"), ("line_2", "L2")):
            a, b = lane[line_key]
            p1, p2 = (int(a[0]), int(a[1])), (int(b[0]), int(b[1]))
            cv2.line(frame, p1, p2, color, 3, cv2.LINE_AA)
            cv2.putText(frame, f"{lane['name']} {suffix}",
                        (p1[0], max(20, p1[1] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)


class VideoWorker(QThread):
    frame_ready = Signal(QImage)
    raw_frame_ready = Signal(object)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    ai_status_changed = Signal(str)
    detections_changed = Signal(int)
    statistics_changed = Signal(object)
    session_changed = Signal(str)

    def __init__(self, source, connection_source, is_file=False, mode=0, username=None):
        super().__init__()
        self.source = source  # Javna adresa za kalibraciju, bez vjerodajnica.
        self.connection_source = connection_source  # Privatno, samo u memoriji.
        self.is_file = is_file
        self.mode = mode
        self.username = username
        self.running = True
        self.paused = False

    def stop(self):
        self.running = False
        self.paused = False

    def run(self):
        capture = None
        session_id = None
        counter = None
        failure = False
        reached_eof = False
        try:
            detector = tracker = lanes = None
            if self.mode:
                self.ai_status_changed.emit("UČITAVANJE MODELA")
                if self.mode == 1:
                    detector = VehicleDetector(confidence=0.35)
                else:
                    tracker = VehicleTracker(confidence=0.25)
                self.ai_status_changed.emit("AI AKTIVAN")
            else:
                self.ai_status_changed.emit("AI ISKLJUČEN")

            if not self.running:
                return
            capture = cv2.VideoCapture(self.connection_source)
            if not capture.isOpened():
                raise RuntimeError("Videoizvor nije otvoren")

            fps = capture.get(cv2.CAP_PROP_FPS)
            if fps <= 0 or fps > 120:
                fps = 25.0
            frame_interval = 1.0 / fps
            frame_index = 0
            start_wall_time = datetime.now().astimezone()
            self.status_changed.emit("POVEZANO")

            while self.running:
                if self.paused:
                    self.msleep(40)
                    continue
                started = time.monotonic()
                success, original = capture.read()
                if not success:
                    reached_eof = True
                    break
                frame_index += 1
                height, width = original.shape[:2]
                self.raw_frame_ready.emit(original.copy())

                if lanes is None or (self.mode == 2 and counter is None):
                    lanes = load_calibration(self.source, width, height)
                    if self.mode == 2 and lanes:
                        counter = VehicleCounter(lanes)
                        if self.username:
                            # Ne spremamo RTSP URL, IP, korisnika kamere ni lozinku.
                            session = create_session(
                                username=self.username,
                                source_type="VIDEO" if self.is_file else "LIVE",
                                source_name="Lokalni video" if self.is_file else "RTSP kamera",
                                notes="Statistička analiza (bez OCR-a)",
                            )
                            session_id = session["id"]
                            ocr_mape = pripremi_ocr_mape(session["directory"])
                            ocr_upravitelj = UpraviteljOCRKandidata()
                            save_session_statistics(session_id, counter.get_statistics())

                            try:
                                from core.audit import log_event
                                log_event(
                                    event_type="ANALYSIS_STARTED",
                                    username=self.username,
                                    description=(
                                        f"Pokrenuta analiza {session['session_code']}. "
                                        f"Izvor: {'VIDEO' if self.is_file else 'LIVE'}."
                                    ),
                                    status="SUCCESS"
                                )
                            except Exception as audit_error:
                                print(
                                    "Upozorenje: Pocetak analize nije evidentiran:",
                                    type(audit_error).__name__
                                )

                            self.session_changed.emit(
                                f"Analiza {session['session_code']} započela je."
                            )
                        else:
                            self.session_changed.emit(
                                "Brojanje radi, ali spremanje čeka povezivanje prijavljenog korisnika."
                            )

                output = original.copy()
                if detector is not None:
                    output, detections = detector.detect(original)
                    self.detections_changed.emit(len(detections))
                elif tracker is not None:
                    output, vehicles = tracker.track(original)
                    self.detections_changed.emit(len(vehicles))
                    if counter is not None:
                        if session_id is not None and frame_index % 10 == 0:
                            for vozilo in vehicles:
                                track_id = vozilo.get("track_id")
                                bbox = vozilo.get("bbox")
                                if type(track_id) is not int or bbox is None:
                                    continue
                                try:
                                    fotografija = izdvoji_vozilo(original, bbox)
                                    if fotografija is not None:
                                        ocr_upravitelj.dodaj(track_id, fotografija)
                                except (ValueError, TypeError, cv2.error):
                                    continue
                        timestamp = (start_wall_time + timedelta(seconds=(frame_index - 1) / fps)
                                     if self.is_file else datetime.now().astimezone())
                        new_events = counter.update(vehicles, timestamp=timestamp)
                        if session_id is not None and new_events:
                            for event in new_events:
                                event_id = add_vehicle_event(session_id, event)
                                try:
                                    fotografije = ocr_upravitelj.preuzmi(event["track_id"])
                                    if fotografije:
                                        spremi_ocr_kandidate(
                                            ocr_mape["kandidati"],
                                            event_id,
                                            fotografije
                                        )
                                except Exception as ocr_error:
                                    print(
                                        "Upozorenje: OCR fotografije nisu spremljene:",
                                        type(ocr_error).__name__
                                    )
                            save_session_statistics(session_id, counter.get_statistics())
                        inactive = tracker.get_inactive_ids(threshold_frames=30)
                        if inactive:
                            counter.remove_inactive(inactive)
                            for track_id in inactive:
                                if session_id is not None:
                                    ocr_upravitelj.preuzmi(track_id)
                                tracker.remove_id(track_id)
                        self.statistics_changed.emit(counter.get_statistics())
                else:
                    self.detections_changed.emit(0)

                if lanes:
                    draw_lanes(output, lanes)
                rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
                h, w, _ = rgb.shape
                image = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
                self.frame_ready.emit(image)
                if self.is_file:
                    remaining = frame_interval - (time.monotonic() - started)
                    if remaining > 0:
                        self.msleep(max(1, int(remaining * 1000)))
        except Exception as error:
            failure = True
            # Namjerno ne prikazujemo puni URL niti detalje koji bi otkrili lozinku.
            if isinstance(error, RuntimeError) and str(error) == "Videoizvor nije otvoren":
                message = (
                    "Nije moguce otvoriti videoizvor. "
                    "Provjerite adresu kamere, mrezu i pristupne podatke."
                )
            else:
                message = (
                    "Obrada nije uspjela: "
                    + type(error).__name__
                )
            self.error_occurred.emit(message)
        finally:
            if session_id is not None and "ocr_upravitelj" in locals():
                ocr_upravitelj.ocisti()
            if session_id is not None:
                try:
                    final_stats = counter.get_statistics() if counter else {"total_count": 0}
                    save_session_statistics(session_id, final_stats)
                    final_status = "FAILED" if failure else (
                        "COMPLETED" if self.is_file and reached_eof else
                        "COMPLETED" if not self.running else "INTERRUPTED"
                    )
                    finish_session(
                        session_id, status=final_status,
                        total_vehicles=int(final_stats.get("total_count", 0))
                    )

                    try:
                        from core.audit import log_event
                        log_event(
                            event_type="ANALYSIS_" + final_status,
                            username=self.username,
                            description=(
                                f"Zavrsena sesija #{session_id}. "
                                f"Izvor: {'VIDEO' if self.is_file else 'LIVE'}. "
                                f"Broj vozila: {int(final_stats.get('total_count', 0))}. "
                                f"Status: {final_status}."
                            ),
                            status=(
                                "FAILED" if final_status == "FAILED"
                                else "SUCCESS" if final_status == "COMPLETED"
                                else "INFO"
                            )
                        )
                    except Exception as audit_error:
                        print(
                            "Upozorenje: Zavrsetak analize nije evidentiran:",
                            type(audit_error).__name__
                        )

                    self.session_changed.emit(
                        f"Sesija #{session_id} spremljena ({final_status})."
                    )
                except Exception as db_error:
                    self.error_occurred.emit(
                        f"Spremanje sesije nije uspjelo: {type(db_error).__name__}"
                    )
            if capture is not None:
                capture.release()
            self.connection_source = ""
            self.status_changed.emit("ZAUSTAVLJENO")
            self.ai_status_changed.emit("AI ISKLJUČEN")
            self.detections_changed.emit(0)


class LiveCameraPage(QWidget):
    """LIVE preglednik s RTSP prijavom i kalibracijom."""

    def __init__(self, username=None):
        super().__init__()
        self.app_username = username
        self.worker = None
        self.current_image = None
        self.raw_frame = None
        self.settings = QSettings("RIVA", "Road Intelligence & Vision Analysis")
        self.build_ui()

    def build_ui(self):
        self.setStyleSheet("""
            QLabel { color: #E5F0F8; }
            QFrame#liveSourceCard, QFrame#liveVideoCard {
                background-color: #152238; border: 1px solid #293D57;
                border-radius: 16px;
            }
            QLineEdit, QComboBox {
                background-color: #0D1B2C; color: #E5F0F8;
                border: 1px solid #35516B; border-radius: 8px; padding: 9px;
            }
            QPushButton {
                background-color: #293B52; color: #E5F0F8;
                border: 1px solid #40556E; border-radius: 9px;
                padding: 10px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #344C67; }
            QPushButton:disabled { color: #61748B; background-color: #1A293A; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(32, 24, 32, 24)
        main.setSpacing(12)

        title = QLabel("LIVE kamera")
        title.setStyleSheet("font-size: 29px; font-weight: bold; color: white;")
        main.addWidget(title)
        subtitle = QLabel("Video nadzor • YOLO11 • ByteTrack • brojanje vozila")
        subtitle.setStyleSheet("color: #91A6BE; font-size: 12px;")
        main.addWidget(subtitle)

        source_card = QFrame()
        source_card.setObjectName("liveSourceCard")
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(18, 15, 18, 15)
        source_layout.setSpacing(9)
        source_title = QLabel("VIDEOIZVOR I ANALIZA")
        source_title.setStyleSheet("color: #5DD9D0; font-weight: bold;")
        source_layout.addWidget(source_title)

        row = QHBoxLayout()
        self.source_selector = QComboBox()
        self.source_selector.addItems(["Lokalni videozapis (MP4)", "RTSP kamera"])
        self.source_selector.currentIndexChanged.connect(self.source_changed)
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Samo video", "YOLO detekcija", "YOLO + ByteTrack + brojanje"])
        row.addWidget(self.source_selector, 1)
        row.addWidget(self.mode_selector, 2)
        source_layout.addLayout(row)

        row = QHBoxLayout()
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Odaberi lokalni videozapis...")
        self.browse_button = QPushButton("Odaberi datoteku")
        self.browse_button.clicked.connect(self.browse_video)
        row.addWidget(self.source_input, 1)
        row.addWidget(self.browse_button)
        source_layout.addLayout(row)

        # RTSP pristupni podaci: pamtimo samo korisničko ime.
        self.credentials_row = QWidget()
        credentials_layout = QHBoxLayout(self.credentials_row)
        credentials_layout.setContentsMargins(0, 0, 0, 0)
        credentials_layout.setSpacing(10)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Korisničko ime kamere")
        self.username_input.setText(self.settings.value("rtsp_username", "", type=str))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Lozinka kamere (ne sprema se)")
        self.password_input.setEchoMode(QLineEdit.Password)
        credentials_layout.addWidget(self.username_input)
        credentials_layout.addWidget(self.password_input)
        source_layout.addWidget(self.credentials_row)
        self.credentials_row.setVisible(False)

        row = QHBoxLayout()
        self.calibration_button = QPushButton("✎  Kalibriraj linije")
        self.calibration_button.clicked.connect(self.calibrate)
        self.calibration_status = QLabel("Kalibracija: nije provjerena")
        self.calibration_status.setStyleSheet("color: #91A6BE;")
        row.addWidget(self.calibration_button)
        row.addWidget(self.calibration_status, 1)
        source_layout.addLayout(row)
        main.addWidget(source_card)

        video_card = QFrame()
        video_card.setObjectName("liveVideoCard")
        video_layout = QVBoxLayout(video_card)
        video_layout.setContentsMargins(18, 14, 18, 14)
        video_layout.setSpacing(10)
        header = QHBoxLayout()
        monitor = QLabel("◉  VIDEO MONITOR")
        monitor.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.status_label = QLabel("●  OFFLINE")
        header.addWidget(monitor)
        header.addStretch()
        header.addWidget(self.status_label)
        video_layout.addLayout(header)

        self.video_label = QLabel("◉\n\nČeka se povezivanje videoizvora")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumHeight(450)
        self.video_label.setMinimumWidth(0)
        self.video_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.video_label.setStyleSheet("""
            background: #0B1525; border: 1px dashed #35516B;
            border-radius: 12px; color: #91A6BE; font-size: 15px;
        """)
        video_layout.addWidget(self.video_label, 1)

        stats = QHBoxLayout()
        self.detection_count_label = QLabel("U kadru: —")
        self.total_label = QLabel("Ukupno: 0")
        self.correct_label = QLabel("Ispravan: 0")
        self.opposite_label = QLabel("Suprotan: 0")
        for label in (self.detection_count_label, self.total_label,
                      self.correct_label, self.opposite_label):
            label.setStyleSheet("color: #5DD9D0; font-size: 13px; font-weight: bold;")
            stats.addWidget(label)
        stats.addStretch()
        video_layout.addLayout(stats)

        self.lanes_label = QLabel("Po trakama: —")
        self.lanes_label.setWordWrap(True)
        self.lanes_label.setStyleSheet("color: #AFC1D4; font-size: 12px;")
        video_layout.addWidget(self.lanes_label)

        controls = QHBoxLayout()
        self.start_button = QPushButton("▶  Pokreni video")
        self.start_button.setStyleSheet("""
            QPushButton { background: #168C86; color: white; border: none;
                          border-radius: 9px; padding: 11px 18px; font-weight: bold; }
            QPushButton:hover { background: #1AA59D; }
            QPushButton:disabled { background: #31485A; color: #8496A7; }
        """)
        self.stop_button = QPushButton("■  Zaustavi")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_video)
        self.stop_button.clicked.connect(self.stop_video)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addStretch()
        self.ai_status_label = QLabel("●  AI ISKLJUČEN")
        controls.addWidget(self.ai_status_label)
        video_layout.addLayout(controls)
        main.addWidget(video_card, 1)

        self.info_label = QLabel("Sustav je spreman za odabir videoizvora.")
        self.info_label.setStyleSheet("color: #91A6BE; font-size: 12px;")
        main.addWidget(self.info_label)
        self.update_status("OFFLINE")
        scroll.setWidget(content)
        outer.addWidget(scroll)


    def source_changed(self, *_):
        self.source_input.clear()
        self.raw_frame = None
        self.calibration_status.setText("Kalibracija: nije provjerena")
        is_file = self.source_selector.currentIndex() == 0
        self.browse_button.setEnabled(is_file)
        self.credentials_row.setVisible(not is_file)
        self.source_input.setPlaceholderText(
            "Odaberi lokalni videozapis..." if is_file
            else "rtsp://IP:554/Streaming/Channels/101"
        )

    def browse_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Odaberi videozapis", str(Path.home()),
            "Videozapisi (*.mp4 *.avi *.mov *.mkv)"
        )
        if path:
            self.source_input.setText(path)
            self.raw_frame = None
            self.calibration_status.setText("Kalibracija: nije provjerena")

    def get_connection_source(self):
        """Provjerava izvor i sastavlja privatnu RTSP adresu bez spremanja."""
        source = self.source_input.text().strip()
        if not source:
            raise ValueError("Najprije odaberi videoizvor.")
        is_file = self.source_selector.currentIndex() == 0
        if is_file:
            if not Path(source).is_file():
                raise ValueError("Odabrana video datoteka ne postoji.")
            return source, source, True
        if urlsplit(source).username or urlsplit(source).password:
            raise ValueError("U RTSP adresi nemoj unositi lozinku. Koristi polja ispod.")
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            raise ValueError("Unesi korisničko ime i lozinku kamere.")
        self.settings.setValue("rtsp_username", username)
        return source, rtsp_connection_url(source, username, password), False

    def calibrate(self):
        try:
            source, connection_source, is_file = self.get_connection_source()
        except ValueError as error:
            QMessageBox.warning(self, "RIVA", str(error))
            return

        if self.worker is not None:
            if self.raw_frame is None:
                QMessageBox.information(self, "RIVA", "Pričekaj prvi kadar kamere.")
                return
            self.worker.paused = True
            frame = self.raw_frame.copy()
        else:
            capture = cv2.VideoCapture(connection_source)
            if not capture.isOpened():
                capture.release()
                QMessageBox.warning(self, "RIVA", "Videoizvor nije dostupan. Provjeri prijavu.")
                return
            success, frame = capture.read()
            capture.release()
            if not success:
                QMessageBox.warning(self, "RIVA", "Nije moguće očitati kadar.")
                return

        try:
            dialog = LineCalibrationDialog(
                frame, save_path=calibration_path(source), parent=self
            )
            if dialog.exec():
                self.calibration_status.setText(
                    f"Kalibracija spremljena: {len(dialog.lanes)} traka"
                )
                self.info_label.setText(
                    "Linije spremljene. Za primjenu zaustavi i ponovno pokreni analizu."
                )
        finally:
            if self.worker is not None:
                self.worker.paused = False

    def start_video(self):
        if self.worker is not None:
            return
        try:
            source, connection_source, is_file = self.get_connection_source()
        except ValueError as error:
            QMessageBox.warning(self, "RIVA", str(error))
            return

        self.current_image = None
        self.raw_frame = None
        self.reset_statistics()
        self.worker = VideoWorker(
            source, connection_source, is_file, self.mode_selector.currentIndex(),
            username=self.app_username
        )
        self.worker.frame_ready.connect(self.update_frame)
        self.worker.raw_frame_ready.connect(self.receive_raw_frame)
        self.worker.status_changed.connect(self.update_status)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.ai_status_changed.connect(self.update_ai_status)
        self.worker.detections_changed.connect(self.update_detections)
        self.worker.statistics_changed.connect(self.update_statistics)
        self.worker.session_changed.connect(self.update_session_info)
        self.worker.finished.connect(self.video_finished)

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.source_selector.setEnabled(False)
        self.source_input.setEnabled(False)
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.mode_selector.setEnabled(False)
        self.update_status("POVEZIVANJE")
        self.worker.start()

    def receive_raw_frame(self, frame):
        self.raw_frame = frame
        if self.calibration_status.text() == "Kalibracija: nije provjerena":
            height, width = frame.shape[:2]
            lanes = load_calibration(self.source_input.text().strip(), width, height)
            self.calibration_status.setText(
                f"Kalibracija: {len(lanes)} traka" if lanes
                else "Kalibracija: nije pronađena za ovu rezoluciju"
            )

    def update_frame(self, image):
        self.current_image = image
        self.video_label.setPixmap(QPixmap.fromImage(image).scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_image is not None:
            self.update_frame(self.current_image)

    def reset_statistics(self):
        self.detection_count_label.setText("U kadru: —")
        self.total_label.setText("Ukupno: 0")
        self.correct_label.setText("Ispravan: 0")
        self.opposite_label.setText("Suprotan: 0")
        self.lanes_label.setText("Po trakama: —")

    def update_detections(self, count):
        self.detection_count_label.setText(
            f"U kadru: {count}" if self.mode_selector.currentIndex() else "U kadru: —"
        )

    def update_statistics(self, data):
        self.total_label.setText(f"Ukupno: {data.get('total_count', 0)}")
        self.correct_label.setText(f"Ispravan: {data.get('correct_count', 0)}")
        self.opposite_label.setText(f"Suprotan: {data.get('opposite_count', 0)}")
        counts = data.get("lane_counts", {})
        self.lanes_label.setText(
            "Po trakama: " + ", ".join(f"{name}: {count}" for name, count in counts.items())
            if counts else "Po trakama: —"
        )

    def update_session_info(self, message):
        self.info_label.setText(message)

    def stop_video(self):
        if self.worker is not None:
            self.worker.stop()
            self.stop_button.setEnabled(False)
            self.update_status("ZAUSTAVLJANJE")

    def video_finished(self):
        self.worker = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.source_selector.setEnabled(True)
        self.source_input.setEnabled(True)
        self.username_input.setEnabled(True)
        self.password_input.setEnabled(True)
        self.mode_selector.setEnabled(True)
        self.browse_button.setEnabled(self.source_selector.currentIndex() == 0)
        self.update_status("OFFLINE")
        self.update_ai_status("AI ISKLJUČEN")
        self.info_label.setText("Videoizvor je zaustavljen. Rezultati ostaju prikazani.")

    def update_status(self, status):
        if status == "POVEZANO":
            self.status_label.setText("●  POVEZANO")
            color, background = "#52D8C9", "#143B3C"
            self.info_label.setText("Videoizvor je uspješno otvoren.")
        elif status in ("POVEZIVANJE", "ZAUSTAVLJANJE"):
            self.status_label.setText(f"●  {status}")
            color, background = "#F2BA61", "#3B3024"
        else:
            self.status_label.setText("●  OFFLINE")
            color, background = "#F2BA61", "#3B3024"
        self.status_label.setStyleSheet(
            f"color: {color}; background: {background}; border-radius: 8px; "
            "padding: 8px 12px; font-size: 11px; font-weight: bold;"
        )

    def update_ai_status(self, status):
        self.ai_status_label.setText(f"●  {status}")
        color = "#52D8C9" if status == "AI AKTIVAN" else (
            "#F2BA61" if status == "UČITAVANJE MODELA" else "#91A6BE"
        )
        self.ai_status_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def show_error(self, message):
        self.info_label.setText(message)
        QMessageBox.warning(self, "RIVA - Videoizvor", message)

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(3000)
            if self.worker.isRunning():
                event.ignore()
                return
        super().closeEvent(event)





