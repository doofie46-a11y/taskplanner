"""Auth desktop: auto-login locale, nessun provider OAuth."""
from flask import current_app, redirect, render_template_string, url_for
from flask_login import current_user, login_required, login_user, logout_user

from core.db import get_db
from core.models import User

# Utente locale fisso — istanziato al primo accesso tramite DB
_local_user_cache = None


def _get_local_user():
    global _local_user_cache
    if _local_user_cache is None:
        try:
            db  = get_db()
            c   = db.cursor()
            c.execute(
                "SELECT id, google_id, email, name, picture, api_key FROM users WHERE id = 1"
            )
            row = c.fetchone()
            if row:
                _local_user_cache = User(*row)
        except Exception:
            pass
    return _local_user_cache


def register(app, login_manager):

    @login_manager.user_loader
    def load_user(user_id):
        if str(user_id) == '1':
            return _get_local_user()
        return None

    @app.before_request
    def _auto_login():
        from flask import request as _req
        # Lascia passare asset statici senza autenticazione
        if _req.endpoint in ('static', 'favicon', 'pwa_manifest', 'pwa_sw',
                             'pwa_icon_192', 'pwa_icon_512', 'outlook_js'):
            return
        if not current_user.is_authenticated:
            u = _get_local_user()
            if u:
                login_user(u, remember=True)

    @app.route("/login")
    def login_page():
        # In modalità desktop non c'è una vera pagina di login:
        # l'utente è già auto-loggato, reindirizza direttamente alla home.
        return redirect(url_for("home"))

    @app.route("/logout", methods=["POST", "GET"])
    @login_required
    def logout():
        # In modalità desktop il logout non ha senso funzionale;
        # riporta alla home (che triggera di nuovo l'auto-login).
        logout_user()
        return redirect(url_for("home"))
