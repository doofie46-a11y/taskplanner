"""Gestione utenti server: categorie di default, account locali, verifica password."""
from werkzeug.security import check_password_hash, generate_password_hash

# Lockout per account dopo troppi tentativi falliti (vale anche con più worker:
# lo stato sta nel DB, non in memoria)
MAX_FAILED_LOGINS = 5
LOCK_MINUTES      = 15
MIN_PASSWORD_LEN  = 8

USER_COLUMNS = (
    "id, google_id, email, name, picture, api_key, "
    "username, password_hash IS NOT NULL"
)

# Hash fittizio: con username inesistente si fa comunque un check, così il
# tempo di risposta non rivela quali username esistono
_DUMMY_HASH = generate_password_hash("taskplanner-dummy-password")


def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def create_default_categories(c, user_id):
    """Categorie iniziali per un nuovo utente (solo se non ne ha già)."""
    c.execute("SELECT COUNT(*) FROM categories WHERE user_id = %s", (user_id,))
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO categories (user_id, name, color) VALUES (%s, %s, %s)",
            (user_id, 'Generale', '#6c757d'),
        )
        c.execute(
            "INSERT INTO categories (user_id, name, color) VALUES (%s, %s, %s)",
            (user_id, 'TaskPlanner Dev', '#007bff'),
        )


def create_local_user(db, username, password, name=None, email=None):
    """Crea un account locale. Ritorna l'id; ValueError se username già usato."""
    username = normalize_username(username)
    if not username:
        raise ValueError("username vuoto")
    c = db.cursor()
    c.execute("SELECT 1 FROM users WHERE username = %s", (username,))
    if c.fetchone():
        raise ValueError(f"username '{username}' già esistente")
    c.execute(
        """
        INSERT INTO users (username, password_hash, email, name)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (username, generate_password_hash(password), email or "", name or username),
    )
    user_id = c.fetchone()[0]
    create_default_categories(c, user_id)
    db.commit()
    return user_id


def set_password(db, user_id, password):
    """Imposta una nuova password e sblocca l'account."""
    c = db.cursor()
    c.execute(
        "UPDATE users SET password_hash = %s, failed_logins = 0, locked_until = NULL "
        "WHERE id = %s",
        (generate_password_hash(password), user_id),
    )
    db.commit()


def check_user_password(db, user_id, password) -> bool:
    c = db.cursor()
    c.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
    row = c.fetchone()
    return bool(row and row[0] and check_password_hash(row[0], password))


def authenticate(db, username, password):
    """
    Verifica username/password. Ritorna la riga utente (USER_COLUMNS) o None.
    Account bloccato e credenziali errate danno lo stesso None, così la
    risposta non rivela se l'username esiste.
    """
    username = normalize_username(username)
    c = db.cursor()
    c.execute(
        "SELECT id, password_hash, failed_logins, "
        "COALESCE(locked_until > NOW(), FALSE) FROM users WHERE username = %s",
        (username,),
    )
    row = c.fetchone()
    if not row or not row[1]:
        check_password_hash(_DUMMY_HASH, password or "")
        return None

    user_id, pw_hash, failed, locked = row
    if locked:
        return None

    if check_password_hash(pw_hash, password or ""):
        c.execute(
            "UPDATE users SET failed_logins = 0, locked_until = NULL WHERE id = %s",
            (user_id,),
        )
        c.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (user_id,))
        user_row = c.fetchone()
        db.commit()
        return user_row

    failed += 1
    if failed >= MAX_FAILED_LOGINS:
        c.execute(
            "UPDATE users SET failed_logins = 0, "
            "locked_until = NOW() + make_interval(mins => %s) WHERE id = %s",
            (LOCK_MINUTES, user_id),
        )
    else:
        c.execute("UPDATE users SET failed_logins = %s WHERE id = %s", (failed, user_id))
    db.commit()
    return None
