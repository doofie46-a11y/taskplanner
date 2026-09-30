# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — TaskPlanner Desktop (one-file bundle).

Build (dalla root del progetto con venv attivo):
    pyinstaller taskplanner_desktop.spec

Prerequisiti:
    pip install -r requirements/desktop.txt pillow
    python desktop/make_icons.py   # genera le icone in desktop/icons/
"""
import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)  # directory del file .spec (root del progetto)


# ── Icona ──────────────────────────────────────────────────────────────────
def _resolve_icon():
    """Seleziona l'icona in base alla piattaforma; None se non presente."""
    candidates = {
        "win32":  root / "desktop" / "icons" / "taskplanner.ico",
        "darwin": root / "desktop" / "icons" / "taskplanner.icns",
    }
    path = candidates.get(sys.platform, root / "desktop" / "icons" / "taskplanner.png")
    return str(path) if path.exists() else None


# ── Dati da bundlare ────────────────────────────────────────────────────────
# Le traduzioni (.mo) devono essere incluse come data file; i template Python
# sono compilati nella PYZ e non richiedono trattamento speciale.
datas = [
    (str(root / "translations"), "translations"),
]

# ── Backend finestra Linux (Qt/PySide6) ─────────────────────────────────────
# pywebview su Linux importa gi/GTK oppure qtpy/PySide6 dinamicamente (try/
# except a runtime): PyInstaller non li rileva staticamente, vanno dichiarati
# a mano. Usiamo Qt (vedi requirements/desktop.txt) perché è bundlabile senza
# dipendenze di sistema, a differenza di GTK+WebKit2GTK.
linux_hidden = [
    "qtpy", "qtpy.QtCore", "qtpy.QtGui", "qtpy.QtWidgets",
    "PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
    "PySide6.QtNetwork", "PySide6.QtPrintSupport",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "webview.platforms.qt",
] if sys.platform.startswith("linux") else []

# ── Analisi ────────────────────────────────────────────────────────────────
a = Analysis(
    [str(root / "app_desktop.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # core
        "core", "core.factory", "core.db", "core.models", "core.logic",
        "core.utils",
        "core.routes_tasks", "core.routes_attachments", "core.routes_cestino",
        "core.routes_api", "core.routes_setup", "core.routes_stats",
        "core.routes_export", "core.routes_misc",
        "core.templates", "core.templates.index", "core.templates.forms",
        "core.templates.setup", "core.templates.stats", "core.templates.export",
        "core.templates.cestino", "core.templates.login", "core.templates.outlook",
        # desktop adapter
        "desktop", "desktop.auth", "desktop.config", "desktop.db",
        "desktop.launcher",
        # flask stack
        "flask", "flask.templating", "flask_babel", "flask_login",
        "werkzeug", "werkzeug.serving", "werkzeug.routing",
        "jinja2", "jinja2.ext", "markupsafe",
        # i18n
        "babel", "babel.dates", "babel.numbers",
        # stdlib usati a runtime
        "sqlite3", "zoneinfo", "email.mime.text",
        # platformdirs
        "platformdirs",
    ] + linux_hidden,
    excludes=[
        # server-only — non devono finire nel bundle desktop
        "psycopg2", "psycopg2._psycopg",
        "authlib", "authlib.oauth2",
        "gunicorn", "gunicorn.arbiter",
        "server", "server.auth", "server.db", "server.config",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="TaskPlanner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # nessuna console nera su Windows/macOS
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_resolve_icon(),
    onefile=True,
)
