
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget
)

from ui.dashboard import DashboardPage
from ui.live_camera import LiveCameraPage
from ui.results import ResultsPage
from ui.notifications import show_notification


# ============================================================
# RIVA - GLAVNI PROZOR APLIKACIJE
# ============================================================
# Glavni prozor upravlja:
# - bocnim navigacijskim izbornikom
# - prikazom svih stranica
# - nadzornom plocom
# - LIVE kamerom
# - rezultatima analize
# - prikazom prijavljenog korisnika
#
# Originalni Test 10 ostaje potpuno netaknut.
# ============================================================


class MainWindow(QMainWindow):
    """
    Glavni prozor aplikacije RIVA.

    Upravlja navigacijom izmedu pojedinih modula.
    """

    def __init__(self, username):
        super().__init__()

        # ----------------------------------------------------
        # OSNOVNE POSTAVKE PROZORA
        # ----------------------------------------------------

        self.username = username

        self.setWindowTitle(
            "RIVA | Road Intelligence & Vision Analysis"
        )
        self.resize(1400, 850)
        self.setMinimumSize(1100, 700)

        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ----------------------------------------------------
        # BOCNI NAVIGACIJSKI IZBORNIK
        # ----------------------------------------------------

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 25)
        sidebar_layout.setSpacing(10)

        # Logotip aplikacije.
        logo = QLabel("◈  RIVA")
        logo.setStyleSheet("""
            color: #5DD9D0;
            font-size: 30px;
            font-weight: bold;
        """)

        subtitle = QLabel(
            "ROAD INTELLIGENCE\n"
            "& VISION ANALYSIS"
        )
        subtitle.setStyleSheet("""
            color: #91A6BE;
            font-size: 10px;
        """)

        sidebar_layout.addWidget(logo)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(35)

        # ----------------------------------------------------
        # STRANICE APLIKACIJE
        # ----------------------------------------------------

        self.pages = QStackedWidget()

        # Nadzorna ploca.
        self.dashboard = DashboardPage()

        # LIVE kamera.
        self.live_camera = LiveCameraPage()

        # Rezultati analize.
        self.results = ResultsPage()

        # Pozicija 0 - Nadzorna ploca.
        self.pages.addWidget(self.dashboard)

        # Pozicija 1 - LIVE kamera.
        self.pages.addWidget(self.live_camera)

        # Pozicija 2 - OCR analiza.
        self.pages.addWidget(
            self.create_placeholder(
                "OCR analiza",
                "Modul je pripremljen za implementaciju."
            )
        )

        # Pozicija 3 - Rezultati analize.
        self.pages.addWidget(self.results)

        # Pozicija 4 - Izvjestaji.
        self.pages.addWidget(
            self.create_placeholder(
                "Izvještaji",
                "Modul je pripremljen za implementaciju."
            )
        )

        # Pozicija 5 - Aktivnosti sustava.
        self.pages.addWidget(
            self.create_placeholder(
                "Aktivnosti sustava",
                "Modul je pripremljen za implementaciju."
            )
        )

        # Pozicija 6 - Postavke.
        self.pages.addWidget(
            self.create_placeholder(
                "Postavke",
                "Modul je pripremljen za implementaciju."
            )
        )

        # ----------------------------------------------------
        # POVEZIVANJE BRZIH AKCIJA DASHBOARDA
        # ----------------------------------------------------

        self.dashboard.open_camera.connect(
            lambda: self.change_page(1)
        )

        self.dashboard.open_analysis.connect(
            lambda: self.change_page(2)
        )

        self.dashboard.open_reports.connect(
            lambda: self.change_page(4)
        )

        # ----------------------------------------------------
        # DEFINICIJA NAVIGACIJSKIH MODULA
        # ----------------------------------------------------

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

            button.clicked.connect(
                lambda checked=False, i=index:
                    self.change_page(i)
            )

            sidebar_layout.addWidget(button)
            self.nav_buttons.append(button)

        sidebar_layout.addStretch()

        # ----------------------------------------------------
        # PRIJAVLJENI KORISNIK
        # ----------------------------------------------------

        user_label = QLabel(f"●  {self.username}")
        user_label.setStyleSheet("""
            color: #DDEAF5;
            font-size: 13px;
            font-weight: bold;
        """)

        sidebar_layout.addWidget(user_label)

        # ----------------------------------------------------
        # ODJAVA
        # ----------------------------------------------------

        logout_button = QPushButton("↪  Odjava")
        logout_button.setObjectName("secondaryButton")
        logout_button.setCursor(Qt.PointingHandCursor)

        logout_button.clicked.connect(
            self.logout
        )

        sidebar_layout.addWidget(logout_button)

        # ----------------------------------------------------
        # ZAVRSNO SLAGANJE PROZORA
        # ----------------------------------------------------

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages, 1)

        # Pocetno prikazujemo nadzornu plocu.
        self.change_page(0)

    # ========================================================
    # PRIVREMENE STRANICE
    # ========================================================

    def create_placeholder(self, title, description):
        """
        Stvara privremenu stranicu za module
        koji jos nisu implementirani.
        """

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(45, 40, 45, 40)
        layout.setSpacing(12)

        heading = QLabel(title)
        heading.setStyleSheet("""
            color: #FFFFFF;
            font-size: 30px;
            font-weight: bold;
        """)

        description_label = QLabel(description)
        description_label.setStyleSheet("""
            color: #91A6BE;
            font-size: 15px;
        """)

        layout.addWidget(heading)
        layout.addWidget(description_label)
        layout.addStretch()

        return page

    # ========================================================
    # PROMJENA STRANICE
    # ========================================================

    def change_page(self, index):
        """
        Otvara odabranu stranicu i oznacava
        aktivni gumb u bocnom izborniku.
        """

        self.pages.setCurrentIndex(index)

        # Pri povratku na nadzornu plocu
        # osvjezavamo statistiku i sesije.
        if index == 0:
            self.dashboard.refresh_dashboard()

        # Oznacavanje aktivne stavke izbornika.
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    # ========================================================
    # ODJAVA KORISNIKA
    # ========================================================

    def logout(self):
        """
        Privremena obavijest o odjavi.

        Stvarnu odjavu povezujemo naknadno.
        """

        show_notification(
            self,
            "Odjava iz sustava",
            "Odjava će uskoro biti dostupna.",
            "info"
        )

    # ========================================================
    # ZATVARANJE APLIKACIJE
    # ========================================================

    def closeEvent(self, event):
        """
        Prije zatvaranja aplikacije zaustavlja
        video nit kako ne bi ostala aktivna.
        """

        if self.live_camera.worker is not None:

            self.live_camera.worker.stop()
            self.live_camera.worker.wait(3000)

            if self.live_camera.worker.isRunning():
                event.ignore()
                return

        super().closeEvent(event)
