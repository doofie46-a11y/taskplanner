"""Adapter PostgreSQL: factory di connessione e init_db."""
import logging

import psycopg2

from server.config import DATABASE_URL

logger = logging.getLogger(__name__)


def get_connection():
    """Apre e restituisce una nuova connessione psycopg2."""
    return psycopg2.connect(DATABASE_URL)


def init_db(app):
    """
    Crea le tabelle PostgreSQL se non esistono e applica le migrazioni incrementali.
    Da chiamare una volta sola all'avvio, prima di servire richieste.
    """
    conn = None
    try:
        conn = get_connection()
        c    = conn.cursor()

        # Utenti
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         BIGSERIAL PRIMARY KEY,
                google_id  TEXT UNIQUE NOT NULL,
                email      TEXT NOT NULL,
                name       TEXT,
                picture    TEXT,
                api_key    TEXT UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Categorie
        c.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id      BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                name    TEXT NOT NULL,
                color   TEXT DEFAULT '#007bff'
            )
        """)

        # Tasks
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id                     BIGSERIAL PRIMARY KEY,
                user_id                BIGINT REFERENCES users(id) ON DELETE CASCADE,
                titolo                 TEXT NOT NULL,
                data_prevista          DATE NOT NULL,
                ora_prevista           TEXT,
                ricorrenza             TEXT DEFAULT 'none',
                ricorrenza_fine        DATE,
                ricorrenza_occorrenze  INTEGER,
                posticipato_da         DATE,
                priorita               TEXT DEFAULT 'Media',
                category_id            BIGINT,
                url                    TEXT,
                escalation             INTEGER,
                pinned                 INTEGER DEFAULT 0,
                note                   TEXT,
                card_color             TEXT,
                created_at             DATE
            )
        """)

        # Completamenti
        c.execute("""
            CREATE TABLE IF NOT EXISTS task_completed (
                task_id         BIGINT,
                data_completata DATE,
                tempo_impiegato INTEGER DEFAULT NULL,
                PRIMARY KEY (task_id, data_completata)
            )
        """)

        # Rollover history
        c.execute("""
            CREATE TABLE IF NOT EXISTS rollover_history (
                id       BIGSERIAL PRIMARY KEY,
                task_id  BIGINT,
                from_date DATE,
                to_date   DATE,
                moved_at  TIMESTAMP DEFAULT NOW()
            )
        """)

        # Allegati
        c.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id            BIGSERIAL PRIMARY KEY,
                task_id       BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                stored_name   TEXT NOT NULL,
                original_name TEXT NOT NULL,
                uploaded_at   TIMESTAMP DEFAULT NOW()
            )
        """)

        # Tipologie movimento (Contaschei)
        c.execute("""
            CREATE TABLE IF NOT EXISTS movement_categories (
                id      BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                name    TEXT NOT NULL,
                type    TEXT NOT NULL DEFAULT 'expense',
                color   TEXT DEFAULT '#007bff'
            )
        """)

        # Movimenti (Contaschei)
        c.execute("""
            CREATE TABLE IF NOT EXISTS movements (
                id                    BIGSERIAL PRIMARY KEY,
                user_id               BIGINT REFERENCES users(id) ON DELETE CASCADE,
                category_id           BIGINT REFERENCES movement_categories(id) ON DELETE SET NULL,
                tipo                  TEXT NOT NULL DEFAULT 'expense',
                amount                NUMERIC(12,2) NOT NULL,
                date                  DATE NOT NULL,
                ricorrenza            TEXT DEFAULT 'none',
                ricorrenza_fine       DATE,
                ricorrenza_occorrenze INTEGER,
                note                  TEXT,
                created_at            DATE
            )
        """)

        # Eccezioni alle occorrenze ricorrenti (Contaschei)
        c.execute("""
            CREATE TABLE IF NOT EXISTS movement_exceptions (
                id              BIGSERIAL PRIMARY KEY,
                movement_id     BIGINT NOT NULL REFERENCES movements(id) ON DELETE CASCADE,
                occurrence_date DATE NOT NULL,
                action          TEXT NOT NULL,
                override_amount NUMERIC(12,2),
                override_note   TEXT,
                UNIQUE (movement_id, occurrence_date)
            )
        """)

        # Migrazioni incrementali (idempotenti)
        for tbl in ("tasks", "categories"):
            c.execute(
                f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS "
                f"user_id BIGINT REFERENCES users(id) ON DELETE CASCADE"
            )
        c.execute("ALTER TABLE categories ADD COLUMN IF NOT EXISTS group_name TEXT DEFAULT NULL")
        c.execute("ALTER TABLE tasks      ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP DEFAULT NULL")
        # Login locale (1.6.0): utenti senza account Google, password hashata
        c.execute("ALTER TABLE users ALTER COLUMN google_id DROP NOT NULL")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username      TEXT UNIQUE")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_logins INTEGER NOT NULL DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until  TIMESTAMP")

        conn.commit()
        app.logger.info("Database PostgreSQL inizializzato / verificato")

    except Exception:
        app.logger.exception("Errore in server/db init_db")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
