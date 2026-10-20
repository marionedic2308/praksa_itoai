
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
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

    # Sluzbena RIVA ikona za prozore aplikacije.
    icon_path = BASE_DIR / "assets" / "RIVA.ico"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Učitavanje zajedničke teme iz zasebne datoteke.
    if THEME_PATH.is_file():
        with open(THEME_PATH, "r", encoding="utf-8") as file:
            app.setStyleSheet(file.read())

    # Prikaz zaslona za prijavu.
    login_window = LoginWindow()
    login_window.showMaximized()

    # Windows 11: tamna naslovna traka za RIVA prozore.
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        def dark_titlebar(window):
            try:
                hwnd = wintypes.HWND(int(window.winId()))
                enabled = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 20, ctypes.byref(enabled),
                    ctypes.sizeof(enabled)
                )
            except (OSError, AttributeError):
                pass

        dark_titlebar(login_window)

        app.focusWindowChanged.connect(
            lambda window: dark_titlebar(window)
            if window is not None and window.isWindow()
            else None
        )

    # Pokretanje glavne petlje aplikacije.
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
