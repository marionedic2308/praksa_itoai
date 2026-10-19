
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame
)

# RIVA - zasebni moduli aplikacije.
from core.auth import verify_login
from core.audit import log_event
from ui.notifications import show_notification
from ui.main_window import MainWindow


class LoginWindow(QWidget):
    """
    RIVA - zaslon za prijavu korisnika.

    Prikazuje obrazac za prijavu, provjerava korisničke
    podatke i nakon uspješne prijave otvara glavni prozor.
    """

    def __init__(self):
        super().__init__()

        # --------------------------------------------------
        # OSNOVNE POSTAVKE PROZORA
        # --------------------------------------------------

        self.setWindowTitle("RIVA | Prijava u sustav")
        self.resize(1150, 720)
        self.setMinimumSize(900, 580)

        self.setStyleSheet("background-color: #0B1220;")

        # Glavni vodoravni raspored.
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --------------------------------------------------
        # LIJEVA STRANA - IDENTITET SUSTAVA RIVA
        # --------------------------------------------------

        left_panel = QFrame()
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #101D30;
                border-right: 1px solid #24354B;
            }

            QLabel {
                border: none;
                background: transparent;
            }
        """)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(65, 70, 55, 55)
        left_layout.setSpacing(18)

        # Logotip i naziv aplikacije.
        logo = QLabel("◈  RIVA")
        logo.setStyleSheet("""
            color: #5DD9D0;
            font-size: 44px;
            font-weight: 800;
        """)

        subtitle = QLabel(
            "ROAD INTELLIGENCE\n"
            "& VISION ANALYSIS"
        )
        subtitle.setStyleSheet("""
            color: #EAF2FA;
            font-size: 18px;
            font-weight: bold;
        """)

        description = QLabel(
            "Inteligentni sustav za detekciju,\n"
            "praćenje i analizu cestovnog prometa."
        )
        description.setStyleSheet("""
            color: #91A6BE;
            font-size: 15px;
        """)

        footer = QLabel(
            "RIVA  •  Intelligent Traffic Analytics\n"
            "Verzija 1.0"
        )
        footer.setStyleSheet("""
            color: #70859E;
            font-size: 12px;
        """)

        left_layout.addWidget(logo)
        left_layout.addWidget(subtitle)
        left_layout.addSpacing(25)
        left_layout.addWidget(description)
        left_layout.addStretch()
        left_layout.addWidget(footer)

        main_layout.addWidget(left_panel, 5)

        # --------------------------------------------------
        # DESNA STRANA - OBRAZAC ZA PRIJAVU
        # --------------------------------------------------

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(55, 50, 55, 50)

        # Kartica za prijavu korisnika.
        login_card = QFrame()
        login_card.setObjectName("loginCard")
        login_card.setMaximumWidth(440)

        login_card.setStyleSheet("""
            QFrame#loginCard {
                background-color: #152238;
                border: 1px solid #2A3D55;
                border-radius: 22px;
            }

            QLabel {
                background: transparent;
                border: none;
            }

            QLineEdit {
                background-color: #0D192A;
                color: #FFFFFF;
                border: 1px solid #344960;
                border-radius: 10px;
                padding: 13px;
                font-size: 14px;
            }

            QLineEdit:focus {
                border: 2px solid #45D6CD;
            }

            QPushButton {
                background-color: #45D6CD;
                color: #081522;
                border: none;
                border-radius: 11px;
                padding: 14px;
                font-size: 15px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #75E8E0;
            }
        """)

        card_layout = QVBoxLayout(login_card)
        card_layout.setContentsMargins(38, 40, 38, 40)
        card_layout.setSpacing(14)

        # Naslov obrasca.
        welcome = QLabel("Dobro došli natrag")
        welcome.setStyleSheet("""
            color: #FFFFFF;
            font-size: 27px;
            font-weight: bold;
        """)

        hint = QLabel("Prijavite se za pristup sustavu RIVA.")
        hint.setStyleSheet("""
            color: #91A6BE;
            font-size: 13px;
        """)

        # Korisničko ime.
        username_label = QLabel("KORISNIČKO IME")
        username_label.setStyleSheet("""
            color: #AFC1D5;
            font-size: 11px;
        """)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Unesite korisničko ime")
        self.username.setMinimumHeight(47)

        # Lozinka.
        password_label = QLabel("LOZINKA")
        password_label.setStyleSheet("""
            color: #AFC1D5;
            font-size: 11px;
        """)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Unesite lozinku")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setMinimumHeight(47)

        # Gumb za prijavu.
        self.login_button = QPushButton("Prijavi se  →")
        self.login_button.setCursor(Qt.PointingHandCursor)

        # Povezivanje gumba i tipke Enter s prijavom.
        self.login_button.clicked.connect(self.login)
        self.password.returnPressed.connect(self.login)

        # Dodavanje elemenata u karticu.
        card_layout.addWidget(welcome)
        card_layout.addWidget(hint)
        card_layout.addSpacing(24)

        card_layout.addWidget(username_label)
        card_layout.addWidget(self.username)

        card_layout.addSpacing(8)

        card_layout.addWidget(password_label)
        card_layout.addWidget(self.password)

        card_layout.addSpacing(22)
        card_layout.addWidget(self.login_button)

        # Centriranje kartice na desnoj strani.
        right_layout.addStretch()
        right_layout.addWidget(
            login_card,
            alignment=Qt.AlignCenter
        )
        right_layout.addStretch()

        main_layout.addWidget(right_panel, 6)

        # Početni fokus na korisničko ime.
        self.username.setFocus()

    # --------------------------------------------------
    # AUTENTIFIKACIJA KORISNIKA
    # --------------------------------------------------

    def login(self):
        """
        Provjerava korisničko ime i lozinku.

        Uspješne i neuspješne pokušaje prijave bilježi
        u SQLite audit log, bez spremanja lozinke.

        Nakon uspješne prijave otvara glavni prozor.
        """

        # Preuzimanje unesenih podataka.
        username = self.username.text().strip()
        password = self.password.text()

        # Provjera obveznih polja.
        if not username or not password:
            show_notification(
                self,
                "Nedostaju podaci",
                "Unesite korisničko ime i lozinku.",
                "warning"
            )
            return

        # --------------------------------------------------
        # USPJEŠNA PRIJAVA
        # --------------------------------------------------

        if verify_login(username, password):

            # Evidentiranje uspješne prijave.
            log_event(
                event_type="LOGIN_SUCCESS",
                username=username,
                description="Uspješna prijava u sustav RIVA.",
                status="SUCCESS"
            )

            # Uklanjanje lozinke iz obrasca.
            self.password.clear()

            # Moderna obavijest o uspješnoj prijavi.
            show_notification(
                self,
                "Prijava uspješna",
                "Dobro došli u sustav RIVA!",
                "success"
            )

            # Otvaranje glavnog prozora aplikacije.
            # Referencu čuvamo kako se prozor ne bi zatvorio.
            self.main_window = MainWindow(username)
            self.main_window.show()

            # Zatvaranje zaslona za prijavu.
            self.close()

        # --------------------------------------------------
        # NEUSPJEŠNA PRIJAVA
        # --------------------------------------------------

        else:

            # Evidentiranje neuspješnog pokušaja.
            log_event(
                event_type="LOGIN_FAILED",
                username=username,
                description="Neuspješan pokušaj prijave.",
                status="FAILED"
            )

            # Brisanje lozinke i vraćanje fokusa.
            self.password.clear()
            self.password.setFocus()

            # Moderna obavijest o pogrešnoj prijavi.
            show_notification(
                self,
                "Prijava nije uspjela",
                "Neispravno korisničko ime ili lozinka.",
                "error"
            )
