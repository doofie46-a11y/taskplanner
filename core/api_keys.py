"""
Chiavi API per utente (dalla 1.7.0).

Ogni utente può avere più chiavi con un nome (es. "Telefono", "Outlook ufficio"),
revocabili una per una. Nel DB si salva solo l'hash SHA-256: la chiave in chiaro
si vede una volta sola, quando viene creata o rigenerata.
SHA-256 semplice (senza salt né hash lento) basta perché le chiavi sono casuali
a 256 bit, non password scelte da persone: non si possono indovinare per tentativi,
e l'hash deterministico permette di cercare la chiave con un indice.
"""
import hashlib
import secrets

KEY_PREFIX        = "tp_"
MAX_KEYS_PER_USER = 10
MAX_KEY_NAME_LEN  = 50


def generate_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def key_hint(key: str) -> str:
    """Ultimi 4 caratteri, mostrati in pagina per riconoscere la chiave."""
    return key[-4:]


def find_user_by_key(db, key):
    """Ritorna (key_id, user_id) o None, e aggiorna la data di ultimo utilizzo."""
    c = db.cursor()
    c.execute("SELECT id, user_id FROM api_keys WHERE key_hash = %s", (hash_key(key),))
    row = c.fetchone()
    if row:
        c.execute(f"UPDATE api_keys SET last_used_at = {db.now_expr()} WHERE id = %s", (row[0],))
    return row


def list_keys(db, user_id):
    c = db.cursor()
    c.execute(
        "SELECT id, name, key_hint, created_at, last_used_at FROM api_keys "
        "WHERE user_id = %s ORDER BY id",
        (user_id,),
    )
    return c.fetchall()


def count_keys(db, user_id) -> int:
    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM api_keys WHERE user_id = %s", (user_id,))
    return c.fetchone()[0]


def create_key(db, user_id, name) -> str:
    """Crea una chiave e ritorna il valore in chiaro (da mostrare una volta sola)."""
    key = generate_key()
    c = db.cursor()
    c.execute(
        "INSERT INTO api_keys (user_id, name, key_hash, key_hint) VALUES (%s, %s, %s, %s)",
        (user_id, name, hash_key(key), key_hint(key)),
    )
    db.commit()
    return key


def regenerate_key(db, user_id, key_id):
    """Sostituisce una chiave (stesso nome): la vecchia smette subito di funzionare."""
    key = generate_key()
    c = db.cursor()
    c.execute(
        "UPDATE api_keys SET key_hash = %s, key_hint = %s, last_used_at = NULL, "
        f"created_at = {db.now_expr()} WHERE id = %s AND user_id = %s",
        (hash_key(key), key_hint(key), key_id, user_id),
    )
    if c.rowcount != 1:
        db.rollback()
        return None
    db.commit()
    return key


def delete_key(db, user_id, key_id) -> bool:
    c = db.cursor()
    c.execute("DELETE FROM api_keys WHERE id = %s AND user_id = %s", (key_id, user_id))
    db.commit()
    return c.rowcount == 1


def migrate_legacy_keys(c, legacy_name):
    """
    Sposta le vecchie chiavi in chiaro di users.api_key (fino alla 1.6.x) in
    api_keys come hash, poi le cancella da users. Idempotente: dopo la prima
    esecuzione non trova più chiavi da migrare. `c` è un cursore raw psycopg2.
    """
    c.execute("SELECT id, api_key FROM users WHERE api_key IS NOT NULL AND api_key <> ''")
    for user_id, key in c.fetchall():
        c.execute(
            "INSERT INTO api_keys (user_id, name, key_hash, key_hint) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (key_hash) DO NOTHING",
            (user_id, legacy_name, hash_key(key), key_hint(key)),
        )
    c.execute("UPDATE users SET api_key = NULL WHERE api_key IS NOT NULL")
