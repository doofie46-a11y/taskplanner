"""
Notifiche native per la finestra desktop.

pywebview non inoltra le notifiche web (Notification API) al sistema: WebView2
su Windows e QtWebEngine su Linux le negano. La pagina chiama invece
window.pywebview.api.notify(), esposto da DesktopApi tramite js_api, che le
mostra con plyer (balloon/toast su Windows, notify-send/D-Bus su Linux).
"""
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)


def _icona() -> str:
    """Icona .ico per le notifiche Windows (bundlata dallo spec), '' se assente."""
    if sys.platform != "win32":
        return ""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))
    ico = base / "desktop" / "icons" / "taskplanner.ico"
    return str(ico) if ico.exists() else ""


class DesktopApi:
    """Metodi chiamabili da JS come window.pywebview.api.<nome>()."""

    def notify(self, titolo: str, messaggio: str) -> bool:
        try:
            from plyer import notification
            notification.notify(
                title=str(titolo)[:64],
                message=str(messaggio)[:256],
                app_name="TaskPlanner",
                app_icon=_icona(),
                timeout=10,
            )
            return True
        except Exception:
            # Notifica persa ma l'app continua: niente popup d'errore all'utente
            log.exception("Notifica desktop non inviata")
            return False
