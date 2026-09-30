"""Adapter SQLite: factory di connessione e init_db."""
import sqlite3
import uuid
from pathlib import Path


def make_connection_factory(db_path: Path):
    """Restituisce una callable che apre una connessione SQLite."""
    str_path = str(db_path)

    def _connect():
        conn = sqlite3.connect(str_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    return _connect


def init_db(app, db_path: Path):
    """
    Crea le tabelle SQLite se non esistono e applica le migrazioni incrementali.
    Da chiamare una volta sola all'avvio.
    """
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    try:
        # Utenti
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id  TEXT UNIQUE NOT NULL,
                email      TEXT NOT NULL,
                name       TEXT,
                picture    TEXT,
                api_key    TEXT UNIQUE NOT NULL,
                created_at DATETIME DEFAULT (datetime('now'))
            )
        """)

        # Categorie
        c.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name    TEXT NOT NULL,
                color   TEXT DEFAULT '#007bff'
            )
        """)

        # Tasks
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id               INTEGER REFERENCES users(id) ON DELETE CASCADE,
                titolo                TEXT NOT NULL,
                data_prevista         DATE NOT NULL,
                ora_prevista          TEXT,
                ricorrenza            TEXT DEFAULT 'none',
                ricorrenza_fine       DATE,
                ricorrenza_occorrenze INTEGER,
                posticipato_da        DATE,
                priorita              TEXT DEFAULT 'Media',
                category_id           INTEGER,
                url                   TEXT,
                escalation            INTEGER,
                pinned                INTEGER DEFAULT 0,
                note                  TEXT,
                card_color            TEXT,
                created_at            DATE,
                deleted_at            DATETIME DEFAULT NULL
            )
        """)

        # Completamenti
        c.execute("""
            CREATE TABLE IF NOT EXISTS task_completed (
                task_id         INTEGER,
                data_completata DATE,
                tempo_impiegato INTEGER DEFAULT NULL,
                PRIMARY KEY (task_id, data_completata)
            )
        """)

        # Rollover history
        c.execute("""
            CREATE TABLE IF NOT EXISTS rollover_history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id   INTEGER,
                from_date DATE,
                to_date   DATE,
                moved_at  DATETIME DEFAULT (datetime('now'))
            )
        """)

        # Allegati
        c.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id       INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                stored_name   TEXT NOT NULL,
                original_name TEXT NOT NULL,
                uploaded_at   DATETIME DEFAULT (datetime('now'))
            )
        """)

        # Tipologie movimento (Contaschei)
        c.execute("""
            CREATE TABLE IF NOT EXISTS movement_categories (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name    TEXT NOT NULL,
                type    TEXT NOT NULL DEFAULT 'expense',
                color   TEXT DEFAULT '#007bff'
            )
        """)

        # Movimenti (Contaschei)
        c.execute("""
            CREATE TABLE IF NOT EXISTS movements (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id               INTEGER REFERENCES users(id) ON DELETE CASCADE,
                category_id           INTEGER REFERENCES movement_categories(id) ON DELETE SET NULL,
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
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                movement_id     INTEGER NOT NULL REFERENCES movements(id) ON DELETE CASCADE,
                occurrence_date DATE NOT NULL,
                action          TEXT NOT NULL,
                override_amount NUMERIC(12,2),
                override_note   TEXT,
                UNIQUE (movement_id, occurrence_date)
            )
        """)

        # Migrazioni incrementali (try/except per compatibilità con DB esistenti)
        _add_col(c, "categories", "user_id",    "INTEGER")
        _add_col(c, "categories", "group_name", "TEXT DEFAULT NULL")
        _add_col(c, "tasks",      "user_id",    "INTEGER")
        _add_col(c, "tasks",      "deleted_at", "DATETIME DEFAULT NULL")

        # Utente locale fisso (id=1) — creato se assente
        c.execute("SELECT id FROM users WHERE id = 1")
        if not c.fetchone():
            api_key = str(uuid.uuid4())
            c.execute("""
                INSERT INTO users (id, google_id, email, name, api_key)
                VALUES (1, 'local', 'desktop@local', 'Utente Desktop', ?)
            """, (api_key,))
            # Categorie default
            c.execute(
                "INSERT INTO categories (user_id, name, color) VALUES (1, 'Generale', '#6c757d')"
            )
            # Tipologie movimento default (Contaschei)
            c.execute(
                "INSERT INTO movement_categories (user_id, name, type, color) VALUES (1, 'Stipendio', 'income', '#28a745')"
            )
            c.execute(
                "INSERT INTO movement_categories (user_id, name, type, color) VALUES (1, 'Varie', 'expense', '#6c757d')"
            )

        conn.commit()
        app.logger.info("Database SQLite inizializzato / verificato: %s", db_path)
    except Exception:
        app.logger.exception("Errore in desktop/db init_db")
        raise
    finally:
        conn.close()


def _add_col(cursor, table: str, col: str, col_def: str):
    """Aggiunge una colonna se non esiste (SQLite non supporta ADD COLUMN IF NOT EXISTS < 3.37)."""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
    except Exception:
        pass  # La colonna esiste già
