
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame
)


# --------------------------------------------------
# RIVA - MODERNE OBAVIJESTI
# --------------------------------------------------
# Zajednički dijaloški prozor za sve obavijesti.
# Koristi se kod prijave, kamere, OCR-a i izvještaja.
# --------------------------------------------------


class RivaNotification(QDialog):
    """Prikazuje obavijest u vizualnom stilu RIVA-e."""

    def __init__(self, parent, title, message, kind="success"):
        super().__init__(parent)

        # Prozor bez standardne Windows naslovne trake.
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(390)

        # Boja i simbol ovise o vrsti obavijesti.
        variants = {
            "success": ("✓", "#45D6CD"),
            "warning": ("!", "#F2BA61"),
            "error": ("×", "#F07882"),
            "info": ("i", "#75AFFF"),
        }

        symbol, accent = variants.get(kind, variants["info"])

        # Glavni raspored prozora.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        # Kartica obavijesti.
        card = QFrame()
        card.setObjectName("notificationCard")
        card.setStyleSheet("""
            QFrame#notificationCard {
                background-color: #152238;
                border: 1px solid #344960;
                border-radius: 18px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 25)
        layout.setSpacing(16)

        # Zaglavlje sa simbolom i naslovom.
        header = QHBoxLayout()
        header.setSpacing(14)

        icon = QLabel(symbol)
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(42, 42)
        icon.setStyleSheet(f"""
            background-color: #203B4A;
            color: {accent};
            border-radius: 21px;
            font-size: 24px;
            font-weight: bold;
        """)

        heading = QLabel(title)
        heading.setStyleSheet("""
            color: #FFFFFF;
            font-size: 20px;
            font-weight: bold;
        """)

        header.addWidget(icon)
        header.addWidget(heading)
        header.addStretch()

        # Tekst obavijesti.
        description = QLabel(message)
        description.setWordWrap(True)
        description.setStyleSheet("""
            color: #B8C9DC;
            font-size: 14px;
        """)

        # Gumb za zatvaranje obavijesti.
        close_button = QPushButton("U redu")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setMinimumHeight(43)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #081522;
                border: none;
                border-radius: 10px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #FFFFFF;
            }}
        """)
        close_button.clicked.connect(self.accept)

        layout.addLayout(header)
        layout.addWidget(description)
        layout.addSpacing(8)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

        outer.addWidget(card)


def show_notification(parent, title, message, kind="success"):
    """
    Prikazuje RIVA obavijest i čeka korisničku potvrdu.

    kind može biti:
    success, warning, error ili info.
    """
    dialog = RivaNotification(parent, title, message, kind)
    dialog.exec()
