# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# Modul za pristup RTSP videoizvoru
# ============================================================

import cv2


class Kamera:
    """
    Modul za pristup stvarnom videoizvoru putem RTSP protokola.

    Modul iskljucivo cita postojeci video stream.
    Ne mijenja konfiguraciju mrezne kamere.
    """

    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.cap = None

    def otvori(self):
        """
        Otvara RTSP video stream.
        """

        self.cap = cv2.VideoCapture(self.rtsp_url)

        if not self.cap.isOpened():
            raise RuntimeError(
                "Nije moguce otvoriti RTSP video stream."
            )

        print("[OK] RTSP video stream uspjesno otvoren.")

    def procitaj_frame(self):
        """
        Cita sljedeci frame iz video streama.
        """

        if self.cap is None:
            return False, None

        return self.cap.read()

    def zatvori(self):
        """
        Zatvara vezu prema RTSP video streamu.
        """

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        print("[OK] RTSP video stream zatvoren.")