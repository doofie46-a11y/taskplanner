"""
Launcher desktop: avvia Flask su thread daemon e apre una finestra nativa
tramite pywebview. Blocca finché la finestra viene chiusa.
"""
import os
import socket
import sys
import threading
import time

import requests


def _free_port() -> int:
    """Trova una porta TCP libera lasciando al kernel la scelta."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_flask(url: str, timeout: float = 10.0) -> bool:
    """
    Polling GET finché Flask risponde (qualsiasi codice HTTP) o scade il timeout.
    Usa allow_redirects=False per non inseguire i redirect di login.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            requests.get(url, timeout=1, allow_redirects=False)
            return True
        except Exception:
            time.sleep(0.15)
    return False


def run() -> None:
    """
    Punto di ingresso principale del launcher desktop.
    1. Imposta la data-dir (platformdirs) prima che create_app() la legga.
    2. Avvia Flask su thread daemon su una porta libera.
    3. Attende che Flask risponda (max 10 s).
    4. Apre la finestra pywebview; blocca finché non viene chiusa.
    Flask è daemon → termina automaticamente con il processo principale.
    """
    import webview  # import tardivo: evita errori negli ambienti headless/CI

    # Imposta TASKPLANNER_DATA prima di create_app() in modo che factory.py la legga
    from desktop.config import DATA_DIR
    os.environ.setdefault("TASKPLANNER_DATA", str(DATA_DIR))

    from core.factory import create_app
    app = create_app("desktop")

    host = "127.0.0.1"
    port = _free_port()
    url  = f"http://{host}:{port}"

    flask_thread = threading.Thread(
        target=lambda: app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True,
        ),
        daemon=True,
    )
    flask_thread.start()

    if not _wait_for_flask(url, timeout=10.0):
        sys.exit("TaskPlanner: Flask non ha risposto entro 10 secondi.")

    # Link con target="_blank" (es. Ko-fi, changelog GitHub) nel browser di
    # sistema, non dentro la finestra dell'app
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True

    from desktop.notify import DesktopApi
    webview.create_window(
        "TaskPlanner",
        url,
        width=1280,
        height=800,
        min_size=(800, 600),
        js_api=DesktopApi(),
    )
    # Su Linux forziamo il backend Qt (QtWebEngine/PySide6): GTK+WebKit2GTK
    # richiede binding gi legati a librerie di sistema che l'eseguibile
    # PyInstaller standalone non porta con sé.
    gui = "qt" if sys.platform.startswith("linux") else None
    webview.start(gui=gui)
    # webview.start() ritorna solo quando tutte le finestre sono chiuse.
    # Il thread Flask è daemon → il processo termina normalmente qui.
