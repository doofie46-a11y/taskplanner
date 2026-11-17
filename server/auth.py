"""Auth server: Google OAuth, Cloudflare Access e/o login locale, logout, user_loader."""
import hmac
import secrets

from flask import abort, current_app, g, redirect, render_template_string, request, session, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_user, logout_user, login_required

from core.db import get_db
from core.models import User
from core.templates import _LOGIN_PAGE, _PASSWORD_PAGE
from server import cf_access
from server.users import (
    MIN_PASSWORD_LEN, USER_COLUMNS, authenticate, check_user_password,
    create_default_categories, set_password,
)


def _csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def _csrf_ok():
    token = request.form.get('csrf_token', '')
    return bool(token) and hmac.compare_digest(token, session.get('csrf_token', ''))


def register(app, login_manager, oauth=None):
    """Registra le route di autenticazione e il user_loader su login_manager."""
    google_enabled = oauth is not None
    local_enabled  = app.config['LOCAL_AUTH_ENABLED']
    cf_enabled     = app.config.get('CF_ACCESS_ENABLED', False)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            db = get_db()
            c  = db.cursor()
            c.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (user_id,))
            row = c.fetchone()
            if row:
                return User(*row)
        except Exception:
            pass
        return None

    def _render_login(error=None, username="", error_busy=False):
        if error_busy:
            error = _("Troppe demo avviate nell'ultima ora, riprova più tardi.")
        return render_template_string(
            _LOGIN_PAGE,
            version=current_app.config['APP_VERSION'],
            google_enabled=google_enabled,
            local_enabled=local_enabled,
            cf_enabled=cf_enabled,
            demo_mode=current_app.config.get('DEMO_MODE', False),
            csrf_token=_csrf_token(),
            error=error,
            username=username,
        )

    @app.route("/login", methods=["GET", "POST"])
    def login_page():
        if current_user.is_authenticated:
            return redirect(url_for("home"))
        if request.method == "GET":
            return _render_login()
        if not local_enabled:
            abort(404)
        username = request.form.get("username", "")
        if not _csrf_ok():
            return _render_login(_("Sessione scaduta, riprova."), username), 400
        row = authenticate(get_db(), username, request.form.get("password", ""))
        if not row:
            current_app.logger.warning("Login locale fallito per username=%r", username[:64])
            return _render_login(
                _("Credenziali non valide, oppure account bloccato temporaneamente dopo troppi tentativi."),
                username,
            ), 401
        login_user(User(*row), remember=True)
        return redirect(url_for("home"))

    @app.route("/account/password", methods=["GET", "POST"])
    @login_required
    def change_password():
        if not current_user.has_password:
            abort(404)
        error = None
        done  = False
        if request.method == "POST":
            new = request.form.get("new_password", "")
            db  = get_db()
            if not _csrf_ok():
                error = _("Sessione scaduta, riprova.")
            elif not check_user_password(db, current_user.id, request.form.get("current_password", "")):
                error = _("La password attuale non è corretta.")
            elif len(new) < MIN_PASSWORD_LEN:
                error = _("La nuova password deve avere almeno %(n)s caratteri.", n=MIN_PASSWORD_LEN)
            elif new != request.form.get("confirm_password", ""):
                error = _("Le due password non coincidono.")
            else:
                set_password(db, current_user.id, new)
                done = True
        return render_template_string(
            _PASSWORD_PAGE, csrf_token=_csrf_token(), error=error, done=done,
        ), (400 if error else 200)

    @app.route("/logout", methods=["POST", "GET"])
    @login_required
    def logout():
        via_cf = session.pop('auth_via', None) == 'cf'
        logout_user()
        if cf_enabled and (via_cf or cf_access.get_token()):
            # Chiude anche la sessione Access: altrimenti con Access su tutto il dominio
            # la richiesta successiva rifarebbe login in automatico
            return redirect("/cdn-cgi/access/logout")
        return redirect(url_for("login_page"))

    if google_enabled:
        _register_google(app, oauth)

    if cf_enabled:
        _register_cf_access(app, _render_login)

    if app.config.get('DEMO_MODE'):
        from server.demo import register as register_demo
        register_demo(app, _render_login, _csrf_ok)


def _register_google(app, oauth):

    @app.route("/auth/google/login")
    def google_login():
        base_url     = current_app.config['APP_BASE_URL']
        redirect_uri = base_url + "/auth/google/callback"
        return oauth.google.authorize_redirect(redirect_uri)

    @app.route("/auth/google/callback")
    def google_callback():
        from datetime import date
        try:
            token     = oauth.google.authorize_access_token()
            user_info = token.get("userinfo") or oauth.google.userinfo()
            google_id = user_info["sub"]
            email     = user_info.get("email", "")
            name      = user_info.get("name", email)
            picture   = user_info.get("picture", "")

            db = get_db()
            c  = db.cursor()

            # Controlla se esiste un utente migrato (google_id placeholder) con stessa email
            c.execute(
                "SELECT id FROM users WHERE email = %s AND google_id LIKE 'migrated_%%'",
                (email,),
            )
            existing = c.fetchone()
            if existing:
                c.execute("""
                    UPDATE users SET google_id=%s, name=%s, picture=%s WHERE id=%s
                    RETURNING id, google_id, email, name, picture, api_key
                """, (google_id, name, picture, existing[0]))
            else:
                c.execute("""
                    INSERT INTO users (google_id, email, name, picture)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (google_id) DO UPDATE
                      SET email   = EXCLUDED.email,
                          name    = EXCLUDED.name,
                          picture = EXCLUDED.picture
                    RETURNING id, google_id, email, name, picture, api_key
                """, (google_id, email, name, picture))
            row = c.fetchone()

            # Categorie default per nuovi utenti
            create_default_categories(c, row[0])

            db.commit()
            user = User(row[0], row[1], row[2], row[3], row[4], row[5])
            login_user(user, remember=True)
            return redirect(url_for("home"))

        except Exception:
            current_app.logger.exception("Errore callback OAuth")
            return redirect(url_for("login_page"))


# Path che non aprono né chiudono sessioni Cloudflare: API con chiave (in Access vanno in
# Bypass, quindi senza JWT) e asset statici/PWA, inutile verificare il JWT a ogni icona.
_CF_SKIP_PATHS    = ("/api/", "/add_from_mail", "/static/")
_CF_SKIP_ENDPOINTS = {"static"}
_CF_SKIP_EXACT    = {
    "/favicon.ico", "/manifest.json", "/sw.js", "/pwa-icon-192.png", "/pwa-icon-512.png",
    "/outlook.js", "/calendar.js",
}


def _register_cf_access(app, render_login):
    """Login tramite Cloudflare Access: la sessione segue il JWT allegato da Cloudflare."""

    @app.before_request
    def _cf_access_session():
        path = request.path
        if (path.startswith(_CF_SKIP_PATHS) or path in _CF_SKIP_EXACT
                or request.endpoint in _CF_SKIP_ENDPOINTS):
            return
        claims = cf_access.current_identity() if cf_access.get_token() else None
        g.cf_claims = claims
        g.cf_user_missing = False
        if claims is None:
            # Sessione aperta via Cloudflare ma JWT sparito/scaduto: si chiude anche qui
            if session.get('auth_via') == 'cf' and current_user.is_authenticated:
                current_app.logger.info("Cloudflare Access: JWT assente, logout utente %s", current_user.id)
                session.pop('auth_via', None)
                logout_user()
            return
        email = claims["email"]
        if current_user.is_authenticated and (current_user.email or "").strip().lower() == email:
            return
        user_id = cf_access.find_or_create_user(get_db(), email, current_app.config['CF_ACCESS_AUTO_CREATE'])
        if user_id is None:
            g.cf_user_missing = True
            if session.get('auth_via') == 'cf' and current_user.is_authenticated:
                session.pop('auth_via', None)
                logout_user()
            return
        db = get_db()
        c  = db.cursor()
        c.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (user_id,))
        if current_user.is_authenticated:
            current_app.logger.info(
                "Cloudflare Access: cambio utente %s → %s (%s)", current_user.id, user_id, email,
            )
        # remember=False: la durata della sessione la decide Access, non un cookie dell'app
        login_user(User(*c.fetchone()), remember=False)
        session['auth_via'] = 'cf'

    @app.route("/auth/cloudflare")
    def cf_login():
        # Con Access su questo path (modo B) Cloudflare chiede il login prima di arrivare qui,
        # e l'hook sopra ha già aperto la sessione.
        if current_user.is_authenticated:
            return redirect(url_for("home"))
        if g.get('cf_user_missing'):
            error = _("Nessun account TaskPlanner è associato a questa email. Chiedi all'amministratore di crearlo.")
        else:
            error = _("Cloudflare Access non ha fornito un'identità valida. Riprova, oppure contatta l'amministratore.")
        return render_login(error), 403
