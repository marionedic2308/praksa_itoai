from ui.settings import SettingsPage
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

    def __init__(self, parent=None, analysis_active=False, logout_mode=False):
        super().__init__(parent)
        self.setWindowTitle("RIVA | Potvrda odjave" if logout_mode else "RIVA | Potvrda izlaska")
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
        heading = QLabel("Odjava iz sustava" if logout_mode else "Izlazak iz RIVA-e")
        heading.setStyleSheet("color: #FFFFFF; font-size: 21px; font-weight: bold;")
        subtitle = QLabel("POTVRDA ODJAVE KORISNIKA" if logout_mode else "POTVRDA ZATVARANJA APLIKACIJE")
        subtitle.setStyleSheet("color: #7FA6B9; font-size: 10px; font-weight: bold;")
        titles.addWidget(heading)
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        layout.addLayout(header)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #304760; border: none;")
        layout.addWidget(divider)

        question = QLabel("Jeste li sigurni da se želite odjaviti iz sustava RIVA?" if logout_mode else "Želite li sigurno izaći iz aplikacije?")
        question.setWordWrap(True)
        question.setStyleSheet("color: #E5F0F8; font-size: 15px; font-weight: bold;")
        layout.addWidget(question)
        details = QLabel(
            "Trenutni korisnik bit ce odjavljen. Aplikacija ostaje otvorena na zaslonu za prijavu."
            if logout_mode else
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
        exit_button = QPushButton("Odjavi se" if logout_mode else "↪  Izađi")
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

        self.setWindowFlags(
            Qt.Window | Qt.FramelessWindowHint
        )

        root = QWidget()
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        titlebar = QFrame()
        titlebar.setFixedHeight(46)
        titlebar.setStyleSheet("""
            QFrame {
                background: #101D30;
                border-bottom: 1px solid #294158;
            }
        """)

        title_layout = QHBoxLayout(titlebar)
        title_layout.setContentsMargins(18, 0, 0, 0)
        title_layout.setSpacing(0)

        app_name = QLabel(chr(0x25C8) + "  RIVA")
        app_name.setStyleSheet("""
            color: #37D5C7;
            font-size: 15px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        title_layout.addWidget(app_name)

        app_subtitle = QLabel("   ROAD INTELLIGENCE & VISION ANALYSIS")
        app_subtitle.setStyleSheet("""
            color: #91A6BE;
            font-size: 10px;
            background: transparent;
            border: none;
        """)
        title_layout.addWidget(app_subtitle)
        title_layout.addStretch()

        button_style = """
            QPushButton {
                background: transparent;
                color: #DDEAF5;
                border: none;
                border-radius: 0;
                font-size: 17px;
                padding: 0;
            }
            QPushButton:hover {
                background: #294158;
            }
        """

        minimize = QPushButton(chr(0x2212))
        minimize.setToolTip("Minimiziraj")
        minimize.setFixedSize(48, 46)
        minimize.setStyleSheet(button_style)
        minimize.clicked.connect(self.showMinimized)
        title_layout.addWidget(minimize)

        maximize = QPushButton(chr(0x25A1))
        maximize.setToolTip("Maksimiziraj / Vrati")
        maximize.setFixedSize(48, 46)
        maximize.setStyleSheet(button_style)
        maximize.clicked.connect(self.toggle_main_maximize)
        title_layout.addWidget(maximize)

        close = QPushButton(chr(0x00D7))
        close.setToolTip("Zatvori RIVA-u")
        close.setFixedSize(48, 46)
        close.setStyleSheet(button_style + """
            QPushButton:hover {
                background: #C84D5A;
                color: white;
            }
        """)
        close.clicked.connect(self.close)
        title_layout.addWidget(close)

        self.main_titlebar = titlebar
        self.main_titlebar.mousePressEvent = self.title_mouse_press
        self.main_titlebar.mouseMoveEvent = self.title_mouse_move
        self.main_titlebar.mouseDoubleClickEvent = self.title_double_click

        root_layout.addWidget(titlebar)

        body = QWidget()
        root_layout.addWidget(body, 1)

        main_layout = QHBoxLayout(body)
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
        self.settings = SettingsPage(self.username)
        self.pages.addWidget(self.settings)  # 6

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

    def toggle_main_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def title_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()

    def title_mouse_move(self, event):
        if (
            event.buttons() & Qt.LeftButton
            and hasattr(self, "_drag_position")
            and not self.isMaximized()
        ):
            self.move(
                event.globalPosition().toPoint()
                - self._drag_position
            )
            event.accept()

    def title_double_click(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_main_maximize()
            event.accept()

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
        dialog = ExitDialog(
            self,
            analysis_active=(
                self.live_camera.worker is not None
                and self.live_camera.worker.isRunning()
            ),
            logout_mode=True
        )
        if dialog.exec() != QDialog.Accepted:
            return

        """Sigurna odjava i povratak na prijavu."""
        from ui.login import LoginWindow
        from core.audit import log_event

        worker = self.live_camera.worker

        if worker is not None and worker.isRunning():
            worker.stop()

            if not worker.wait(10000):
                show_notification(
                    self,
                    "Odjava nije moguca",
                    "LIVE analiza se jos zaustavlja. "
                    "Pricekajte spremanje rezultata.",
                    "warning"
                )
                return

        try:
            log_event(
                event_type="LOGOUT",
                username=self.username,
                description="Korisnik se odjavio iz sustava RIVA.",
                status="SUCCESS"
            )
        except Exception as error:
            show_notification(
                self,
                "Odjava nije dovrsena",
                str(error),
                "error"
            )
            return

        self.login_window = LoginWindow()
        self.login_window.showMaximized()

        self._logout_in_progress = True
        self.close()

    def closeEvent(self, event):
        """Potvrđuje izlazak i čeka spremanje aktivne LIVE sesije."""
        if getattr(self, "_logout_in_progress", False):
            event.accept()
            return

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
