
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from ui.login import LoginWindow


# --------------------------------------------------
# RIVA - GLAVNA ULAZNA TOČKA APLIKACIJE
# --------------------------------------------------
# Ovdje se pokreće aplikacija i učitava
# zajednički vizualni identitet sustava.
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
THEME_PATH = BASE_DIR / "styles" / "theme.qss"


def main():
    """
    Pokreće RIVA aplikaciju.

    Učitava globalnu temu i prikazuje
    početni zaslon za prijavu korisnika.
    """

    # Stvaranje Qt aplikacije.
    app = QApplication(sys.argv)

    # Učitavanje zajedničke teme iz zasebne datoteke.
    if THEME_PATH.is_file():
        with open(THEME_PATH, "r", encoding="utf-8") as file:
            app.setStyleSheet(file.read())

    # Prikaz zaslona za prijavu.
    login_window = LoginWindow()
    login_window.show()

    # Pokretanje glavne petlje aplikacije.
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
