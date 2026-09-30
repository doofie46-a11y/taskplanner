"""Auth server: Google OAuth, login_page, logout, user_loader."""
from flask import current_app, redirect, render_template_string, url_for
from flask_login import current_user, login_user, logout_user, login_required

from core.db import get_db
from core.models import User
from core.templates import _LOGIN_PAGE


def register(app, login_manager, oauth):
    """Registra le route di autenticazione e il user_loader su login_manager."""

    @login_manager.user_loader
    def load_user(user_id):
        try:
            db = get_db()
            c  = db.cursor()
            c.execute(
                "SELECT id, google_id, email, name, picture, api_key FROM users WHERE id = %s",
                (user_id,),
            )
            row = c.fetchone()
            if row:
                return User(*row)
        except Exception:
            pass
        return None

    @app.route("/login")
    def login_page():
        if current_user.is_authenticated:
            return redirect(url_for("home"))
        return render_template_string(
            _LOGIN_PAGE, version=current_app.config['APP_VERSION']
        )

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
            c.execute("SELECT COUNT(*) FROM categories WHERE user_id = %s", (row[0],))
            if c.fetchone()[0] == 0:
                c.execute(
                    "INSERT INTO categories (user_id, name, color) VALUES (%s, %s, %s)",
                    (row[0], 'Generale', '#6c757d'),
                )
                c.execute(
                    "INSERT INTO categories (user_id, name, color) VALUES (%s, %s, %s)",
                    (row[0], 'TaskPlanner Dev', '#007bff'),
                )

            db.commit()
            user = User(row[0], row[1], row[2], row[3], row[4], row[5])
            login_user(user, remember=True)
            return redirect(url_for("home"))

        except Exception:
            current_app.logger.exception("Errore callback OAuth")
            return redirect(url_for("login_page"))

    @app.route("/logout", methods=["POST", "GET"])
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login_page"))
