"""
Adapter desktop: SQLite + auto-login locale.

init_app(app, login_manager):
  - Imposta DB_FACTORY e DB_DIALECT
  - Inizializza il database SQLite
  - Registra le route di autenticazione (auto-login)
  - Registra le route Outlook
  - Configura il user_loader
"""
from desktop.config import DATA_DIR, SQLITE_PATH
from desktop.db import init_db, make_connection_factory


def _load_secret_key():
    """Chiave di sessione per-installazione: generata al primo avvio e salvata nella data dir."""
    import secrets
    key_file = DATA_DIR / "secret_key"
    try:
        key = key_file.read_text(encoding="utf-8").strip()
        if key:
            return key
    except OSError:
        pass
    key = secrets.token_hex(32)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    key_file.write_text(key, encoding="utf-8")
    try:
        key_file.chmod(0o600)
    except OSError:
        pass
    return key


def init_app(app, login_manager):
    if not app.secret_key:
        app.secret_key = _load_secret_key()

    # --- config DB ---
    app.config['DB_FACTORY'] = make_connection_factory(SQLITE_PATH)
    app.config['DB_DIALECT'] = 'sqlite'

    # --- init schema ---
    with app.app_context():
        init_db(app, SQLITE_PATH)

    # --- Auth routes + user_loader ---
    from desktop.auth import register as register_auth
    register_auth(app, login_manager)

    # --- Outlook routes (Windows only, import condizionale) ---
    try:
        from desktop.routes_outlook import register as register_outlook
        register_outlook(app)
        app.config['HAS_OUTLOOK'] = True
    except ImportError:
        pass  # win32com non disponibile fuori Windows
