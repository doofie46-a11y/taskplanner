"""
Entrypoint desktop — Flask + SQLite + auto-login locale.

Avvio diretto:    python app_desktop.py
PyInstaller:      pyinstaller TaskPlannerDesktop.spec
"""
from desktop.launcher import run

if __name__ == "__main__":
    run()
