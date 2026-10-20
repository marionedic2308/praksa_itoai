"""RIVA - glavni prozor, navigacija, osvježavanje i siguran izlazak."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QMessageBox, QDialog,
)

from ui.dashboard import DashboardPage
from ui.live_camera import LiveCameraPage
from ui.results import ResultsPage
from ui.reports import ReportsPage
from ui.notifications import show_notification


class ExitDialog(QDialog):
    """Prilagođena potvrda izlaska u vizualnom stilu RIVA-e."""

    def __init__(self, parent=None, analysis_active=False):
        super().__init__(parent)
        self.setWindowTitle("RIVA | Potvrda izlaska")
        self.setModal(True)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(470)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        panel = QFrame()
        panel.setObjectName("exitPanel")
        panel.setStyleSheet("""
            QFrame#exitPanel {
                background: #142238;
                border: 1px solid #36516A;
                border-radius: 18px;
            }
            QLabel { background: transparent; border: none; }
        """)
        outer.addWidget(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(26, 26, 26, 24)
        layout.setSpacing(17)

        header = QHBoxLayout()
        icon = QLabel("↪")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(54, 54)
        icon.setStyleSheet("""
            background: #203E4B; color: #5DD9D0;
            border-radius: 14px; font-size: 30px; font-weight: bold;
        """)
        header.addWidget(icon)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        heading = QLabel("Izlazak iz RIVA-e")
        heading.setStyleSheet("color: #FFFFFF; font-size: 21px; font-weight: bold;")
        subtitle = QLabel("POTVRDA ZATVARANJA APLIKACIJE")
        subtitle.setStyleSheet("color: #7FA6B9; font-size: 10px; font-weight: bold;")
        titles.addWidget(heading)
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        layout.addLayout(header)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #304760; border: none;")
        layout.addWidget(divider)

        question = QLabel("Želite li sigurno izaći iz aplikacije?")
        question.setWordWrap(True)
        question.setStyleSheet("color: #E5F0F8; font-size: 15px; font-weight: bold;")
        layout.addWidget(question)
        details = QLabel(
            "LIVE analiza je aktivna. Prije izlaska sustav će je pokušati "
            "uredno zaustaviti i spremiti rezultate."
            if analysis_active else
            "Aplikacija će se zatvoriti. Spremljene analize ostat će u bazi podataka."
        )
        details.setWordWrap(True)
        details.setStyleSheet("color: #9BB1C7; font-size: 12px; line-height: 1.4;")
        layout.addWidget(details)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch()
        cancel = QPushButton("Odustani")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setMinimumSize(122, 42)
        cancel.setStyleSheet("""
            QPushButton { background: #253D55; color: #E5F0F8;
                border: 1px solid #3B5770; border-radius: 10px;
                padding: 10px 18px; font-weight: bold; }
            QPushButton:hover { background: #31516A; }
        """)
        cancel.clicked.connect(self.reject)
        exit_button = QPushButton("↪  Izađi")
        exit_button.setCursor(Qt.PointingHandCursor)
        exit_button.setMinimumSize(122, 42)
        exit_button.setStyleSheet("""
            QPushButton { background: #168C86; color: #FFFFFF;
                border: 1px solid #168C86; border-radius: 10px;
                padding: 10px 18px; font-weight: bold; }
            QPushButton:hover { background: #1AA59D; }
        """)
        exit_button.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(exit_button)
        layout.addLayout(buttons)
        cancel.setFocus()


class MainWindow(QMainWindow):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle("RIVA | Road Intelligence & Vision Analysis")
        self.resize(1400, 850)
        self.setMinimumSize(1100, 700)

        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 25)
        sidebar_layout.setSpacing(10)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(8)
        logo = QLabel("◈  RIVA")
        logo.setStyleSheet("color: #5DD9D0; font-size: 30px; font-weight: bold;")
        logo_row.addWidget(logo)
        logo_row.addStretch()

        self.refresh_button = QPushButton("↻")
        self.refresh_button.setToolTip("Osvježi trenutačnu stranicu")
        self.refresh_button.setAccessibleName("Osvježi stranicu")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setFixedSize(36, 36)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background: #1B3547; color: #5DD9D0;
                border: 1px solid #35616B; border-radius: 10px;
                font-size: 24px; font-weight: bold; padding: 0;
            }
            QPushButton:hover { background: #245261; border-color: #5DD9D0; }
            QPushButton:pressed { background: #16313C; }
        """)
        self.refresh_button.clicked.connect(self.refresh_current_page)
        logo_row.addWidget(self.refresh_button)
        sidebar_layout.addLayout(logo_row)

        subtitle = QLabel("ROAD INTELLIGENCE\n& VISION ANALYSIS")
        subtitle.setStyleSheet("color: #91A6BE; font-size: 10px;")
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(35)

        self.pages = QStackedWidget()
        self.dashboard = DashboardPage()
        self.live_camera = LiveCameraPage(username=self.username)
        self.results = ResultsPage()
        self.reports = ReportsPage()

        self.pages.addWidget(self.dashboard)  # 0
        self.pages.addWidget(self.live_camera)  # 1
        self.pages.addWidget(self.create_placeholder(
            "OCR analiza", "Modul je pripremljen za implementaciju."))  # 2
        self.pages.addWidget(self.results)  # 3
        self.pages.addWidget(self.reports)  # 4
        self.pages.addWidget(self.create_placeholder(
            "Aktivnosti sustava", "Modul je pripremljen za implementaciju."))  # 5
        self.pages.addWidget(self.create_placeholder(
            "Postavke", "Modul je pripremljen za implementaciju."))  # 6

        self.dashboard.open_camera.connect(lambda: self.change_page(1))
        self.dashboard.open_analysis.connect(lambda: self.change_page(2))
        self.dashboard.open_reports.connect(lambda: self.change_page(4))

        sections = [
            ("⌂  Nadzorna ploča", 0),
            ("◉  LIVE kamera", 1),
            ("◎  OCR analiza", 2),
            ("▤  Rezultati", 3),
            ("▥  Izvještaji", 4),
            ("◷  Aktivnosti sustava", 5),
            ("⚙  Postavke", 6),
        ]
        self.nav_buttons = []
        for title, index in sections:
            button = QPushButton(title)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, i=index: self.change_page(i))
            sidebar_layout.addWidget(button)
            self.nav_buttons.append(button)

        sidebar_layout.addStretch()
        user_label = QLabel(f"●  {self.username}")
        user_label.setStyleSheet("color: #DDEAF5; font-size: 13px; font-weight: bold;")
        sidebar_layout.addWidget(user_label)

        logout_button = QPushButton("↪  Odjava")
        logout_button.setObjectName("secondaryButton")
        logout_button.setCursor(Qt.PointingHandCursor)
        logout_button.clicked.connect(self.logout)
        sidebar_layout.addWidget(logout_button)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages, 1)
        self.change_page(0)

    def create_placeholder(self, title, description):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(45, 40, 45, 40)
        layout.setSpacing(12)
        heading = QLabel(title)
        heading.setStyleSheet("color: #FFFFFF; font-size: 30px; font-weight: bold;")
        description_label = QLabel(description)
        description_label.setStyleSheet("color: #91A6BE; font-size: 15px;")
        layout.addWidget(heading)
        layout.addWidget(description_label)
        layout.addStretch()
        return page

    def change_page(self, index):
        self.pages.setCurrentIndex(index)
        if index == 0:
            self.dashboard.refresh_dashboard()
        elif index == 3:
            self.results.refresh_sessions()
        elif index == 4:
            self.reports.refresh_reports()
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def refresh_current_page(self):
        """Osvježava podatke aktivnog modula, bez prekidanja LIVE videa."""
        index = self.pages.currentIndex()
        try:
            if index == 0:
                self.dashboard.refresh_dashboard()
            elif index == 3:
                self.results.refresh_sessions()
            elif index == 4:
                self.reports.refresh_reports()
            elif index == 1:
                show_notification(
                    self, "LIVE kamera",
                    "LIVE prikaz se ažurira automatski. Aktivna analiza nije prekinuta.",
                    "info",
                )
            else:
                show_notification(
                    self, "Osvježavanje",
                    "Za ovaj modul još nema podataka za osvježavanje.",
                    "info",
                )
        except Exception:
            QMessageBox.warning(
                self, "RIVA", "Osvježavanje nije uspjelo. Provjeri dostupnost podataka."
            )

    def logout(self):
        show_notification(
            self, "Odjava iz sustava", "Odjava će uskoro biti dostupna.", "info"
        )

    def closeEvent(self, event):
        """Potvrđuje izlazak i čeka spremanje aktivne LIVE sesije."""
        active_worker = self.live_camera.worker
        is_active = active_worker is not None and active_worker.isRunning()
        dialog = ExitDialog(self, analysis_active=is_active)
        if dialog.exec() != QDialog.Accepted:
            event.ignore()
            return

        if is_active:
            active_worker.stop()
            if not active_worker.wait(10000):
                QMessageBox.warning(
                    self, "RIVA | Analiza je aktivna",
                    "Analiza se još zaustavlja. Aplikacija ostaje otvorena "
                    "kako se podaci ne bi izgubili. Pokušaj ponovno za nekoliko trenutaka."
                )
                event.ignore()
                return
        super().closeEvent(event)
