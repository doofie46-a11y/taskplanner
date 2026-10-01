"""
Notifiche native per la finestra desktop.

pywebview non inoltra le notifiche web (Notification API) al sistema: WebView2
su Windows e QtWebEngine su Linux le negano. La pagina chiama invece
window.pywebview.api.notify(), esposto da DesktopApi tramite js_api.

Windows: toast nativo (WinRT) via PowerShell, che segnala gli errori; se
fallisce, ripiego sui balloon della tray (plyer), spesso disattivati su
Windows 10/11 e sui PC aziendali. Linux: plyer (notify-send / D-Bus).
"""
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from xml.sax.saxutils import escape

log = logging.getLogger(__name__)

# AppUserModelID di PowerShell: un eseguibile non installato non ne ha uno
# proprio, e senza un AUMID registrato Windows scarta i toast in silenzio
_AUMID_POWERSHELL = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"

# Il testo arriva via variabile d'ambiente, mai interpolato nello script
_PS_TOAST = r"""
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($env:TP_TOAST_XML)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($env:TP_TOAST_AUMID).Show($toast)
"""


def _icona() -> str:
    """Icona .ico per i balloon Windows (bundlata dallo spec), '' se assente."""
    if sys.platform != "win32":
        return ""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))
    ico = base / "desktop" / "icons" / "taskplanner.ico"
    return str(ico) if ico.exists() else ""


def _impostazioni_windows() -> dict:
    """Valori di registro che possono silenziare le notifiche (solo diagnostica)."""
    import winreg
    chiavi = {
        "ToastEnabled": r"Software\Microsoft\Windows\CurrentVersion\PushNotifications",
        "EnableBalloonTips": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "NoToastApplicationNotification": r"Software\Policies\Microsoft\Windows\CurrentVersion\PushNotifications",
        "TaskbarNoNotification": r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
    }
    valori = {}
    for nome, percorso in chiavi.items():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, percorso) as k:
                valori[nome] = winreg.QueryValueEx(k, nome)[0]
        except OSError:
            valori[nome] = None  # assente = default di Windows (abilitato)
    return valori


class DesktopApi:
    """Metodi chiamabili da JS come window.pywebview.api.<nome>()."""

    def __init__(self, logger=None):
        # logger dell'app Flask: è l'unico con l'handler su taskplanner.log
        self._log = logger or log
        self._diagnostica_fatta = False

    def notify(self, titolo: str, messaggio: str) -> bool:
        titolo, messaggio = str(titolo)[:64], str(messaggio)[:256]
        self._log.info("Notifica desktop: %s — %s", titolo, messaggio)
        try:
            if sys.platform == "win32":
                return self._notify_windows(titolo, messaggio)
            from plyer import notification
            notification.notify(title=titolo, message=messaggio,
                                app_name="TaskPlanner", timeout=10)
            return True
        except Exception:
            # Notifica persa ma l'app continua: niente popup d'errore all'utente
            self._log.exception("Notifica desktop non inviata")
            return False

    def _notify_windows(self, titolo: str, messaggio: str) -> bool:
        if not self._diagnostica_fatta:
            self._diagnostica_fatta = True
            try:
                self._log.info("Impostazioni notifiche Windows: %s", _impostazioni_windows())
            except Exception:
                self._log.exception("Lettura impostazioni notifiche Windows fallita")

        xml = (
            '<toast><visual><binding template="ToastGeneric">'
            f"<text>{escape(titolo)}</text><text>{escape(messaggio)}</text>"
            "</binding></visual></toast>"
        )
        env = dict(os.environ, TP_TOAST_XML=xml, TP_TOAST_AUMID=_AUMID_POWERSHELL)
        try:
            r = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", _PS_TOAST],
                env=env, capture_output=True, text=True, timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if r.returncode == 0:
                self._log.info("Toast Windows inviato")
                return True
            self._log.warning("Toast Windows fallito (rc=%s): %s",
                              r.returncode, (r.stderr or r.stdout).strip()[:1000])
        except Exception:
            self._log.exception("Toast Windows non avviato")

        # Ripiego: balloon della tray. plyer lo mostra in un thread suo, dove
        # le eccezioni andrebbero perse: lo chiamiamo noi per registrarle
        def _balloon():
            try:
                from plyer.platforms.win.libs.balloontip import balloon_tip
                balloon_tip(title=titolo, message=messaggio, app_name="TaskPlanner",
                            app_icon=_icona(), timeout=10)
                self._log.info("Balloon Windows mostrato")
            except Exception:
                self._log.exception("Balloon Windows fallito")
        threading.Thread(target=_balloon, daemon=True).start()
        return True

    def log_js(self, messaggio: str) -> None:
        """Errori lato pagina: nella finestra desktop non c'è una console visibile."""
        self._log.warning("JS: %s", messaggio)
