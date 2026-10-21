
from PySide6.QtCore import Qt, QPoint
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
from core.users import verify_user
from core.audit import log_event
from ui.notifications import show_notification
from ui.main_window import MainWindow
from ui.login_visual import LoginVisual


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
        self.resize(1250, 750)
        self.setMinimumSize(1050, 640)

        self.setStyleSheet("background-color: #0B1220;")

        # Vlastita RIVA naslovna traka.
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        titlebar = QWidget()
        titlebar.setFixedHeight(46)
        titlebar.setObjectName("rivaTitlebar")
        titlebar.setStyleSheet('''
            QWidget#rivaTitlebar {
                background-color: #101D30;
                border-bottom: 1px solid #294158;
            }
            QLabel {
                background: transparent;
                border: none;
            }
            QPushButton {
                background: transparent;
                color: #DCEBF7;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #294158;
            }
            QPushButton#closeButton:hover {
                background: #C9414C;
                color: white;
            }
        ''')

        bar = QHBoxLayout(titlebar)
        bar.setContentsMargins(18, 0, 0, 0)
        bar.setSpacing(0)

        brand = QLabel("RIVA")
        brand.setStyleSheet(
            "color:#45D6CD; font-size:15px; font-weight:bold;"
        )

        caption = QLabel("  |  Prijava u sustav")
        caption.setStyleSheet(
            "color:#91A6BE; font-size:12px;"
        )

        bar.addWidget(brand)
        bar.addWidget(caption)
        bar.addStretch()

        minimize = QPushButton(chr(0x2212))
        maximize = QPushButton(chr(0x25A1))
        close = QPushButton(chr(0x00D7))
        close.setObjectName("closeButton")

        for button in (minimize, maximize, close):
            button.setFixedSize(48, 46)
            button.setCursor(Qt.PointingHandCursor)

        minimize.clicked.connect(self.showMinimized)
        maximize.clicked.connect(self.toggle_maximize)
        close.clicked.connect(self.close)

        bar.addWidget(minimize)
        bar.addWidget(maximize)
        bar.addWidget(close)

        self.titlebar = titlebar
        root.addWidget(titlebar)

        # Postojeci sadrzaj prijave ostaje nepromijenjen.
        content = QWidget()
        main_layout = QHBoxLayout(content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        root.addWidget(content, 1)

        self._drag_position = None

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
        left_layout.setContentsMargins(42, 55, 30, 35)
        left_layout.setSpacing(18)


        # RIVA identitet - kompaktno profesionalno zaglavlje.
        brand_row = QHBoxLayout()
        brand_row.setSpacing(15)

        brand_icon = QLabel(chr(0x25C8))
        brand_icon.setFixedSize(54, 54)
        brand_icon.setAlignment(Qt.AlignCenter)
        brand_icon.setStyleSheet("""
            background-color: #17374A;
            color: #5DD9D0;
            border: 1px solid #31576A;
            border-radius: 12px;
            font-size: 29px;
        """)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)

        logo = QLabel("RIVA")
        logo.setStyleSheet("""
            color: #5DD9D0;
            font-size: 39px;
            font-weight: 800;
        """)

        subtitle = QLabel("Road Intelligence & Vision Analysis")
        subtitle.setStyleSheet("""
            color: #C1D3E1;
            font-size: 13px;
            font-weight: 500;
        """)

        brand_text.addWidget(logo)
        brand_text.addWidget(subtitle)

        brand_row.addWidget(brand_icon)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #2D485D; border: none;")

        description = QLabel(
            "Inteligentni sustav za detekciju, "
            "praćenje i analizu cestovnog prometa."
        )
        description.setWordWrap(True)
        description.setStyleSheet("""
            color: #C5D7E5;
            font-family: "Segoe UI";
            font-size: 16px;
            font-weight: 600;
        """)

        footer = QLabel(
            "RIVA  •  Intelligent Traffic Analytics\n"
            "Verzija 1.0"
        )
        footer.setStyleSheet("""
            color: #70859E;
            font-size: 12px;
        """)

        left_layout.addLayout(brand_row)
        left_layout.addWidget(separator)
        left_layout.addWidget(description)

        # Animirana offline vizualizacija prometnog sustava.
        self.login_visual = LoginVisual(left_panel)
        self.login_visual.setMinimumHeight(280)
        left_layout.addWidget(self.login_visual, 0)

        left_layout.addWidget(footer)

        main_layout.addWidget(left_panel, 7)

        # --------------------------------------------------
        # DESNA STRANA - OBRAZAC ZA PRIJAVU
        # --------------------------------------------------

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 35, 20, 35)

        # Kartica za prijavu korisnika.
        login_card = QFrame()
        login_card.setObjectName("loginCard")
        login_card.setMaximumWidth(365)

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
        card_layout.setContentsMargins(23, 30, 23, 30)
        card_layout.setSpacing(11)

        # Naslov obrasca.
        welcome = QLabel("Prijava u sustav")
        welcome.setStyleSheet("""
            color: #FFFFFF;
            font-size: 27px;
            font-weight: bold;
        """)

        hint = QLabel("Unesite korisničke podatke za pristup aplikaciji RIVA.")
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
        self.username.setTextMargins(29, 0, 0, 0)

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
        self.password.setTextMargins(29, 0, 0, 0)


        # Ikone korisnika i lokota unutar polja.
        from PySide6.QtCore import QByteArray
        from PySide6.QtGui import QIcon, QPixmap
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtGui import QPainter

        def make_icon(svg):
            pixmap = QPixmap(20, 20)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
            renderer.render(painter)
            painter.end()
            return QIcon(pixmap)

        user_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="20" height="20" viewBox="0 0 24 24" '
            'fill="none" stroke="#91A6BE" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="8" r="4"/>'
            '<path d="M4 21v-2a8 8 0 0 1 16 0v2"/>'
            '</svg>'
        )

        lock_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="20" height="20" viewBox="0 0 24 24" '
            'fill="none" stroke="#91A6BE" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="5" y="10" width="14" height="11" rx="2"/>'
            '<path d="M8 10V7a4 4 0 0 1 8 0v3"/>'
            '</svg>'
        )

        self.username.addAction(
            make_icon(user_svg),
            QLineEdit.LeadingPosition
        )

        self.password.addAction(
            make_icon(lock_svg),
            QLineEdit.LeadingPosition
        )

        # Gumb za prijavu.
        self.login_button = QPushButton("Prijavi se  →")
        self.login_button.setCursor(Qt.PointingHandCursor)

        # Povezivanje gumba i tipke Enter s prijavom.
        self.login_button.clicked.connect(self.login)
        self.password.returnPressed.connect(self.login)

        # Dodavanje elemenata u karticu.
        card_layout.addWidget(welcome)
        card_layout.addWidget(hint)
        card_layout.addSpacing(12)

        card_layout.addWidget(username_label)
        card_layout.addWidget(self.username)

        card_layout.addSpacing(8)

        card_layout.addWidget(password_label)
        card_layout.addWidget(self.password)

        card_layout.addSpacing(14)
        card_layout.addWidget(self.login_button)

        # Centriranje kartice na desnoj strani.
        right_layout.addStretch()
        right_layout.addWidget(
            login_card,
            alignment=Qt.AlignCenter
        )
        right_layout.addStretch()

        main_layout.addWidget(right_panel, 3)

        # Početni fokus na korisničko ime.
        self.username.setFocus()


    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if event.position().y() <= 46:
                self._drag_position = (
                    event.globalPosition().toPoint()
                    - self.frameGeometry().topLeft()
                )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._drag_position is not None
            and event.buttons() & Qt.LeftButton
            and not self.isMaximized()
        ):
            self.move(
                event.globalPosition().toPoint()
                - self._drag_position
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_position = None
        super().mouseReleaseEvent(event)

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

        if verify_user(username, password):

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
            self.main_window.showMaximized()

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
