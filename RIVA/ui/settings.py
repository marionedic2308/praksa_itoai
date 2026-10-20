from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame, QScrollArea, QMessageBox,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStackedWidget, QDialog
)

from ui.notifications import show_notification

from core.users import (
    get_user_role, list_users, add_user,
    change_password, deactivate_user, activate_user
)

NAVY = "#0D1829"
PANEL = "#172B42"
PANEL2 = "#1D354D"
TEAL = "#37D5C7"
MUTED = "#99B0C6"
WHITE = "#EDF5FB"

BASE_DIR = Path(__file__).resolve().parent.parent


class SettingsPage(QWidget):
    def __init__(self, username):
        super().__init__()

        self.username = username
        self.role = get_user_role(username)

        self.setObjectName("settingsRoot")
        self.setStyleSheet(f"""
            QWidget#settingsRoot {{
                background: {NAVY};
                color: {WHITE};
                font-family: 'Segoe UI';
            }}
            QFrame#settingsCard {{
                background: {PANEL};
                border: 1px solid #294158;
                border-radius: 15px;
            }}
            QFrame#settingsTile {{
                background: {PANEL};
                border: 1px solid #294158;
                border-radius: 17px;
            }}
            QFrame#settingsTile:hover {{
                background: {PANEL2};
                border: 1px solid {TEAL};
            }}
            QLabel {{
                background: transparent;
            }}
            QLineEdit, QComboBox {{
                background: #0B1727;
                border: 1px solid #35516A;
                border-radius: 8px;
                padding: 10px;
                color: {WHITE};
                min-height: 23px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {TEAL};
            }}
            QPushButton {{
                background: {TEAL};
                color: #0D1829;
                border: none;
                border-radius: 8px;
                padding: 11px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: #65E6DC;
            }}
            QPushButton#secondary {{
                background: {PANEL2};
                color: {WHITE};
                border: 1px solid #3A5268;
            }}
            QTableWidget {{
                background: #0B1727;
                alternate-background-color: {PANEL2};
                border: 1px solid #35516A;
                border-radius: 8px;
                gridline-color: #294158;
            }}
            QHeaderView::section {{
                background: {PANEL2};
                color: {WHITE};
                padding: 9px;
                border: none;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        self.build_home()

        self.pages = {
            "profile": self.build_profile,
            "users": self.build_users,
            "general": self.build_general,
            "storage": self.build_storage,
            "analysis": self.build_analysis,
            "security": self.build_security,
        }

        self.opened_pages = {}

    def text(self, value, size=13, color=WHITE, bold=False):
        label = QLabel(value)
        label.setWordWrap(True)
        label.setStyleSheet(
            f"color: {color}; font-size: {size}px;"
            f"font-weight: {'bold' if bold else 'normal'};"
        )
        return label

    def card(self, title):
        frame = QFrame()
        frame.setObjectName("settingsCard")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(25, 23, 25, 25)
        layout.setSpacing(15)

        layout.addWidget(self.text(title, 15, TEAL, True))
        return frame

    def page(self, title, description):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(42, 35, 42, 40)
        layout.setSpacing(20)

        back = QPushButton("←  Natrag na postavke")
        back.setObjectName("secondary")
        back.setCursor(Qt.PointingHandCursor)
        back.setFixedWidth(220)
        back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(back)

        layout.addSpacing(10)
        layout.addWidget(self.text(title, 29, WHITE, True))
        layout.addWidget(self.text(description, 13, MUTED))

        scroll.setWidget(content)
        outer.addWidget(scroll)

        return page, layout

    def build_home(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(42, 35, 42, 40)
        layout.setSpacing(20)

        layout.addWidget(self.text("Postavke sustava", 30, WHITE, True))
        layout.addWidget(self.text(
            "Upravljanje korisnicima, sigurnost i konfiguracija aplikacije RIVA.",
            13, MUTED
        ))

        summary = QFrame()
        summary.setObjectName("settingsCard")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(24, 20, 24, 20)

        avatar = QLabel(self.username[:1].upper())
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(54, 54)
        avatar.setStyleSheet(f"""
            background: {TEAL};
            color: {NAVY};
            font-size: 24px;
            font-weight: bold;
            border-radius: 27px;
        """)
        summary_layout.addWidget(avatar)

        user_info = QVBoxLayout()
        user_info.addWidget(self.text(self.username, 17, WHITE, True))
        user_info.addWidget(self.text(
            "Administrator sustava" if self.role == "admin"
            else "Korisnik sustava", 12, MUTED
        ))
        summary_layout.addLayout(user_info)
        summary_layout.addStretch()

        summary_layout.addWidget(self.text("RIVA  |  OFFLINE", 12, TEAL, True))
        layout.addWidget(summary)

        layout.addSpacing(6)
        layout.addWidget(self.text("KATEGORIJE POSTAVKI", 12, MUTED, True))

        grid = QGridLayout()
        grid.setHorizontalSpacing(17)
        grid.setVerticalSpacing(17)

        tiles = [
            ("profile", "01", "Moj profil",
             "Osobni podaci i promjena lozinke."),
            ("users", "02", "Upravljanje korisnicima",
             "Dodavanje, pregled i deaktivacija računa."),
            ("general", "03", "Opće postavke",
             "Informacije o aplikaciji i sustavu."),
            ("storage", "04", "Pohrana podataka",
             "Baza podataka i korisnički računi."),
            ("analysis", "05", "Postavke analize",
             "YOLO detekcija i OCR konfiguracija."),
            ("security", "06", "Sigurnost sustava",
             "Korisnička prava i zaštita podataka."),
        ]

        for index, (key, number, title, description) in enumerate(tiles):
            tile = QFrame()
            tile.setObjectName("settingsTile")
            tile.setCursor(Qt.PointingHandCursor)
            tile.setMinimumHeight(155)

            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(23, 19, 23, 19)
            tile_layout.setSpacing(8)

            top = QHBoxLayout()
            top.addWidget(self.text(number, 19, TEAL, True))
            top.addStretch()
            top.addWidget(self.text("↗", 22, MUTED))
            tile_layout.addLayout(top)

            tile_layout.addWidget(self.text(title, 17, WHITE, True))
            tile_layout.addWidget(self.text(description, 12, MUTED))
            tile_layout.addStretch()

            tile.mousePressEvent = (
                lambda event, name=key: self.open_page(name)
                if event.button() == Qt.LeftButton else None
            )

            grid.addWidget(tile, index // 2, index % 2)

        layout.addLayout(grid)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.stack.addWidget(page)

    def open_page(self, name):
        if name not in self.opened_pages:
            page = self.pages[name]()
            self.opened_pages[name] = page
            self.stack.addWidget(page)

        if name == "users" and self.role == "admin":
            self.refresh_users()

        self.stack.setCurrentWidget(self.opened_pages[name])

    def build_profile(self):
        page, layout = self.page(
            "Moj profil",
            "Pregled korisničkog računa i sigurna promjena lozinke."
        )

        card = self.card("PODACI O KORISNIKU")
        card.layout().addWidget(
            self.text(f"Korisničko ime: {self.username}", 15)
        )
        card.layout().addWidget(
            self.text(
                "Uloga: Administrator" if self.role == "admin"
                else "Uloga: Korisnik", 14, MUTED
            )
        )
        layout.addWidget(card)

        password_card = self.card("PROMJENA LOZINKE")

        self.old_password = QLineEdit()
        self.old_password.setPlaceholderText("Trenutna lozinka")
        self.old_password.setEchoMode(QLineEdit.Password)

        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText("Nova lozinka (najmanje 10 znakova)")
        self.new_password.setEchoMode(QLineEdit.Password)

        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText("Potvrdite novu lozinku")
        self.confirm_password.setEchoMode(QLineEdit.Password)

        for field in (
            self.old_password, self.new_password, self.confirm_password
        ):
            password_card.layout().addWidget(field)

        button = QPushButton("Spremi novu lozinku")
        button.clicked.connect(self.update_password)
        password_card.layout().addWidget(button)

        layout.addWidget(password_card)
        layout.addStretch()
        return page

    def build_users(self):
        page, layout = self.page(
            "Upravljanje korisnicima",
            "Administracija korisničkih računa i pristupa aplikaciji."
        )

        if self.role != "admin":
            layout.addWidget(self.card(
                "PRISTUP OGRANIČEN"
            ))
            layout.addWidget(self.text(
                "Upravljanje korisnicima dostupno je samo administratoru.",
                14, MUTED
            ))
            layout.addStretch()
            return page

        card = self.card("KORISNIČKI RAČUNI")

        self.users_table = QTableWidget(0, 3)
        self.users_table.setHorizontalHeaderLabels(
            ["Korisničko ime", "Uloga", "Status"]
        )
        self.users_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.users_table.setMinimumHeight(185)
        self.users_table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.users_table.setStyleSheet("""
            QTableWidget {
                background: #0B1727;
                alternate-background-color: #1D354D;
                color: #EDF5FB;
                border: 1px solid #35516A;
                border-radius: 8px;
                gridline-color: #294158;
                selection-background-color: #168F8C;
                selection-color: #FFFFFF;
            }
            QTableWidget::item:selected {
                background: #168F8C;
                color: #FFFFFF;
                font-weight: bold;
            }
            QHeaderView::section {
                background: #1D354D;
                color: #EDF5FB;
                padding: 9px;
                border: none;
            }
        """)
        card.layout().addWidget(self.users_table)

        self.selected_user_label = QLabel(
            "Nijedan korisnik nije odabran."
        )
        self.selected_user_label.setStyleSheet("""
            background: #10283A;
            color: #37D5C7;
            border: 1px solid #31566A;
            border-radius: 8px;
            padding: 13px 16px;
            font-size: 13px;
            font-weight: bold;
        """)
        card.layout().addWidget(self.selected_user_label)

        self.users_table.itemSelectionChanged.connect(
            self.update_selected_user
        )

        layout.addWidget(card)

        add_card = self.card("DODAJ NOVOG KORISNIKA")

        self.add_username = QLineEdit()
        self.add_username.setPlaceholderText("Korisničko ime")

        self.add_password = QLineEdit()
        self.add_password.setPlaceholderText("Početna lozinka (najmanje 10 znakova)")
        self.add_password.setEchoMode(QLineEdit.Password)

        self.add_role = QComboBox()
        self.add_role.addItem("Korisnik", "user")
        self.add_role.addItem("Administrator", "admin")

        add_card.layout().addWidget(self.add_username)
        add_card.layout().addWidget(self.add_password)
        add_card.layout().addWidget(self.add_role)

        actions = QHBoxLayout()

        create = QPushButton("Dodaj korisnika")
        create.clicked.connect(self.create_account)
        actions.addWidget(create)

        disable = QPushButton("Deaktiviraj odabranog")
        disable.setObjectName("secondary")
        disable.clicked.connect(self.disable_account)
        actions.addWidget(disable)

        activate = QPushButton("Aktiviraj odabranog")
        activate.setObjectName("secondary")
        activate.clicked.connect(self.enable_account)
        actions.addWidget(activate)

        add_card.layout().addLayout(actions)
        layout.addWidget(add_card)

        layout.addStretch()
        return page

    def build_general(self):
        page, layout = self.page(
            "Opće postavke",
            "Osnovne informacije o aplikaciji RIVA."
        )

        card = self.card("O APLIKACIJI")
        for line in (
            "Naziv: RIVA | Road Intelligence & Vision Analysis",
            "Namjena: Analiza cestovnog prometa",
            "Vrsta: Desktop aplikacija",
            "Način rada: Lokalno / offline",
            "Sučelje: PySide6 / Python",
        ):
            card.layout().addWidget(self.text(line, 14, MUTED))

        layout.addWidget(card)
        layout.addStretch()
        return page

    def build_storage(self):
        page, layout = self.page(
            "Pohrana podataka",
            "Lokacije lokalne baze podataka i korisničkih računa."
        )

        card = self.card("LOKALNA POHRANA")

        for title, path in (
            ("Baza podataka", BASE_DIR / "data" / "riva.db"),
            ("Korisnički računi", BASE_DIR / "data" / "users.json"),
            ("Spremljene sesije", BASE_DIR / "data" / "sessions"),
        ):
            card.layout().addWidget(self.text(title, 14, WHITE, True))
            label = self.text(str(path), 12, MUTED)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            card.layout().addWidget(label)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def build_analysis(self):
        page, layout = self.page(
            "Postavke analize",
            "Pregled sustava detekcije i planirane OCR integracije."
        )

        card = self.card("ANALIZA PROMETA")
        for line in (
            "Detekcija vozila: YOLO11",
            "Praćenje vozila: integrirano u RIVA sustav",
            "Brojanje: prelazak definiranih linija",
            "OCR: priprema povezivanja postojećeg offline modula",
            "Napomena: parametri analize zasad se ne mijenjaju.",
        ):
            card.layout().addWidget(self.text(line, 14, MUTED))

        layout.addWidget(card)
        layout.addStretch()
        return page

    def build_security(self):
        page, layout = self.page(
            "Sigurnost sustava",
            "Zaštita pristupa i korisničkih podataka."
        )

        card = self.card("SIGURNOSNE ZNAČAJKE")

        for line in (
            "Zaštita lozinki: PBKDF2-HMAC-SHA256",
            "Korisničke uloge: Administrator / Korisnik",
            "Administracija računa: samo administrator",
            "Promjena lozinke: uz provjeru postojeće lozinke",
            "Pohrana korisničkih podataka: lokalna",
        ):
            card.layout().addWidget(self.text(line, 14, MUTED))

        layout.addWidget(card)
        layout.addStretch()
        return page

    def refresh_users(self):
        if self.role != "admin" or not hasattr(self, "users_table"):
            return

        self.users_table.clearSelection()
        self.users_table.setCurrentIndex(
            self.users_table.model().index(-1, -1)
        )

        users = list_users()
        self.users_table.setRowCount(len(users))

        for row, user in enumerate(users):
            values = (
                user["username"],
                "Administrator" if user["role"] == "admin" else "Korisnik",
                "Aktivan" if user["active"] else "Deaktiviran",
            )

            for column, value in enumerate(values):
                self.users_table.setItem(
                    row, column, QTableWidgetItem(value)
                )

    def update_password(self):
        old = self.old_password.text()
        new = self.new_password.text()
        confirm = self.confirm_password.text()

        if new != confirm:
            show_notification(
                self, "Provjera lozinke",
                "Nove lozinke se ne podudaraju.", "warning"
            )
            return

        try:
            change_password(self.username, old, new)
            self.old_password.clear()
            self.new_password.clear()
            self.confirm_password.clear()

            show_notification(
                self, "Uspješno",
                "Lozinka je uspješno promijenjena."
            )
        except (ValueError, PermissionError) as error:
            show_notification(self, "Promjena lozinke", str(error), "warning")

    def create_account(self):
        username = self.add_username.text().strip()
        password = self.add_password.text()
        role = self.add_role.currentData()

        try:
            add_user(self.username, username, password, role)
            self.add_username.clear()
            self.add_password.clear()
            self.refresh_users()

            show_notification(
                self, "Uspješno",
                "Novi korisnik je uspješno dodan."
            )
        except (ValueError, PermissionError) as error:
            show_notification(self, "Dodavanje korisnika", str(error), "warning")

    def disable_account(self):
        row = self.users_table.currentRow()

        if row < 0:
            show_notification(
                self, "Odabir korisnika",
                "Prvo odaberite korisnika.", "warning"
            )
            return

        item = self.users_table.item(row, 0)

        if item is None:
            return

        username = item.text()

        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        dialog.setModal(True)
        dialog.setMinimumWidth(440)

        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(12, 12, 12, 12)

        panel = QFrame()
        panel.setObjectName("confirmPanel")
        panel.setStyleSheet("""
            QFrame#confirmPanel {
                background: #152238;
                border: 1px solid #344960;
                border-radius: 18px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)

        body = QVBoxLayout(panel)
        body.setContentsMargins(28, 27, 28, 27)
        body.setSpacing(18)

        heading = QLabel("Deaktivacija korisnika")
        heading.setStyleSheet(
            "color: #EDF5FB; font-size: 20px; font-weight: bold;"
        )
        body.addWidget(heading)

        message = QLabel(
            f"?elite li deaktivirati korisni?ki ra?un {username}? "
            "Nakon deaktivacije korisnik se vi?e ne?e mo?i prijaviti."
        )
        message.setWordWrap(True)
        message.setStyleSheet(
            "color: #B8C9DC; font-size: 14px;"
        )
        body.addWidget(message)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel = QPushButton("Odustani")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet("""
            QPushButton {
                background: #263B52;
                color: #EDF5FB;
                border: 1px solid #40566C;
                border-radius: 9px;
                padding: 12px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #344E68;
            }
        """)
        cancel.clicked.connect(dialog.reject)
        buttons.addWidget(cancel)

        confirm = QPushButton("Deaktiviraj")
        confirm.setCursor(Qt.PointingHandCursor)
        confirm.setStyleSheet("""
            QPushButton {
                background: #F07882;
                color: #101B2B;
                border: none;
                border-radius: 9px;
                padding: 12px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FF9AA2;
            }
        """)
        confirm.clicked.connect(dialog.accept)
        buttons.addWidget(confirm)

        body.addLayout(buttons)
        outer.addWidget(panel)

        if dialog.exec() != QDialog.Accepted:
            return

        try:
            deactivate_user(self.username, username)
            self.refresh_users()
            self.clear_user_selection()

            show_notification(
                self, "Uspješno",
                "Korisnik je deaktiviran."
            )
        except (ValueError, PermissionError) as error:
            show_notification(self, "Deaktivacija korisnika", str(error), "warning")

    def enable_account(self):
        row = self.users_table.currentRow()

        if row < 0:
            show_notification(
                self, "Odabir korisnika",
                "Prvo odaberite korisnika.", "warning"
            )
            return

        item = self.users_table.item(row, 0)
        if item is None:
            return

        username = item.text()

        try:
            activate_user(self.username, username)
            self.refresh_users()
            self.clear_user_selection()
            show_notification(
                self, "Aktivacija korisnika",
                "Korisni?ki ra?un je ponovno aktiviran.", "success"
            )
        except (ValueError, PermissionError) as error:
            show_notification(
                self, "Aktivacija korisnika", str(error), "warning"
            )

    def clear_user_selection(self):
        self.users_table.clearSelection()
        self.users_table.setCurrentIndex(
            self.users_table.model().index(-1, -1)
        )
        self.update_selected_user()

    def update_selected_user(self):
        if not hasattr(self, "selected_user_label"):
            return

        row = self.users_table.currentRow()
        selected = self.users_table.selectedItems()

        if row < 0 or not selected:
            self.selected_user_label.setText(
                "Nijedan korisnik nije odabran."
            )
            return

        values = []
        for column in range(3):
            item = self.users_table.item(row, column)
            values.append(item.text() if item else "-")

        self.selected_user_label.setText(
            f"ODABRAN: {values[0]}    |    "
            f"Uloga: {values[1]}    |    Status: {values[2]}"
        )
