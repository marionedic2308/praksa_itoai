# ============================================================
# TEST 09 - STVARNI VIDEOIZVOR
# Modul za pristup RTSP videoizvoru
# Kontinuirano citanje najnovijeg framea u zasebnoj niti
# ============================================================

import cv2
import threading
import time


class Kamera:
    """
    Modul za pristup stvarnom videoizvoru putem RTSP protokola.

    Video stream cita se kontinuirano u zasebnoj niti.
    Glavni program uvijek preuzima najnoviji dostupni frame,
    cime se izbjegava gomilanje zastarjelih frameova tijekom
    sporije YOLO obrade.

    Modul iskljucivo cita postojeci video stream.
    Ne mijenja konfiguraciju mrezne kamere.
    """

    def __init__(self, rtsp_url):

        self.rtsp_url = rtsp_url
        self.cap = None

        self.frame = None
        self.uspjeh = False

        self.aktivna = False
        self.thread = None

        self.lock = threading.Lock()

    def otvori(self):
        """
        Otvara RTSP video stream i pokrece zasebnu nit
        za kontinuirano citanje frameova.
        """

        self.cap = cv2.VideoCapture(
            self.rtsp_url,
            cv2.CAP_FFMPEG
        )

        if not self.cap.isOpened():
            raise RuntimeError(
                "Nije moguce otvoriti RTSP video stream."
            )

        # Pokusaj smanjenja internog buffera.
        self.cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

        # Prvi frame potvrduje da stream stvarno daje sliku.
        uspjeh, frame = self.cap.read()

        if not uspjeh or frame is None:
            self.cap.release()
            self.cap = None

            raise RuntimeError(
                "RTSP stream je otvoren, ali prvi frame nije dostupan."
            )

        with self.lock:
            self.frame = frame
            self.uspjeh = True

        self.aktivna = True

        self.thread = threading.Thread(
            target=self._citaj_stream,
            daemon=True
        )

        self.thread.start()

        print("[OK] RTSP video stream uspjesno otvoren.")
        print("[OK] Pokrenuto kontinuirano citanje najnovijeg framea.")

    def _citaj_stream(self):
        """
        Kontinuirano cita RTSP stream u zasebnoj niti.

        Novi frame zamjenjuje prethodni frame. Na taj nacin
        se stari frameovi ne gomilaju dok glavni program
        izvodi YOLO obradu.
        """

        while self.aktivna:

            if self.cap is None:
                break

            uspjeh, frame = self.cap.read()

            if not uspjeh or frame is None:
                # Pojedinacni neuspjesan frame ne prekida
                # odmah cijeli program.
                time.sleep(0.01)
                continue

            with self.lock:
                self.frame = frame
                self.uspjeh = True

    def procitaj_frame(self):
        """
        Vraca kopiju najnovijeg dostupnog framea.
        """

        with self.lock:

            if self.frame is None:
                return False, None

            return self.uspjeh, self.frame.copy()

    def zatvori(self):
        """
        Zaustavlja nit i zatvara RTSP video stream.
        """

        self.aktivna = False

        if self.thread is not None:
            self.thread.join(timeout=2.0)
            self.thread = None

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        with self.lock:
            self.frame = None
            self.uspjeh = False

        print("[OK] RTSP video stream zatvoren.")