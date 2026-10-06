"""
Adapter server: PostgreSQL + Google OAuth e/o login locale (username e password).

init_app(app, login_manager):
  - Imposta DB_FACTORY e DB_DIALECT
  - Inizializza il database PostgreSQL
  - Registra le route di autenticazione (login, oauth, logout)
  - Configura il user_loader
"""
from server.config import (
    APP_BASE_URL,
    DATABASE_URL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_ENABLED,
    LOCAL_AUTH_ENABLED,
    PRIVACY_CONTACT_EMAIL,
)
from server.db import get_connection, init_db


def init_app(app, login_manager):
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL non impostata (vedi .env.example).")
    app.config['PRIVACY_CONTACT_EMAIL'] = PRIVACY_CONTACT_EMAIL

    # --- config DB ---
    app.config['DB_FACTORY'] = get_connection
    app.config['DB_DIALECT'] = 'postgresql'
    app.config['APP_BASE_URL'] = APP_BASE_URL

    # --- init schema ---
    with app.app_context():
        init_db(app)

    # --- metodi di login ---
    if not (GOOGLE_ENABLED or LOCAL_AUTH_ENABLED):
        raise RuntimeError(
            "Nessun metodo di login attivo: configura GOOGLE_CLIENT_ID/SECRET "
            "oppure imposta LOCAL_AUTH=true (vedi .env.example)."
        )
    app.config['LOCAL_AUTH_ENABLED']  = LOCAL_AUTH_ENABLED
    app.config['GOOGLE_AUTH_ENABLED'] = GOOGLE_ENABLED

    oauth = None
    if GOOGLE_ENABLED:
        from authlib.integrations.flask_client import OAuth
        oauth = OAuth(app)
        oauth.register(
            name="google",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    # --- Auth routes + user_loader ---
    from server.auth import register as register_auth
    register_auth(app, login_manager, oauth)
