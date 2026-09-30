"""Configurazione desktop: percorsi cross-platform per DB e dati."""
import os
from pathlib import Path

try:
    from platformdirs import user_data_dir
    _default_data = Path(user_data_dir("TaskPlanner", "TaskPlanner"))
except ImportError:
    # Fallback se platformdirs non è nel venv (non dovrebbe mai accadere)
    _default_data = Path.home() / ".taskplanner"

# TASKPLANNER_DATA consente override esplicito (es. per test o portable build)
DATA_DIR    = Path(os.environ.get("TASKPLANNER_DATA", _default_data))
SQLITE_PATH = DATA_DIR / "taskplanner.db"
