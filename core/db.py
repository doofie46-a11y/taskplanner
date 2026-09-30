"""
Astrazione sottile del database.

Tutte le query nel core usano la sintassi PostgreSQL (%s, RETURNING id, NOW(), ecc.).
CursorAdapter normalizza automaticamente per SQLite quando necessario.

Utilizzo nelle route:
    from core.db import get_db
    db = get_db()
    c = db.cursor()
    c.execute("SELECT ... WHERE id = %s", (tid,))
    row = c.fetchone()
    db.commit()
    # La connessione viene chiusa automaticamente a fine request (teardown_appcontext)
"""
import re
from flask import current_app, g


class CursorAdapter:
    """
    Cursore con normalizzazione automatica tra PostgreSQL e SQLite:
    - %s  →  ? per SQLite
    - RETURNING id: per SQLite viene rimosso dalla query e il risultato
      viene costruito da lastrowid, così fetchone()[0] funziona uguale.
    """

    def __init__(self, cursor, dialect: str):
        self._cur = cursor
        self._dialect = dialect
        self._returning_stripped = False

    def execute(self, sql: str, params=()):
        self._returning_stripped = False
        if self._dialect == 'sqlite':
            sql = sql.replace('%s', '?')
            # ON CONFLICT (...) DO NOTHING  →  INSERT OR IGNORE
            m_conflict = re.search(
                r'\s+ON\s+CONFLICT\s*(?:\([^)]*\))?\s+DO\s+NOTHING', sql, re.IGNORECASE
            )
            if m_conflict:
                sql = sql[:m_conflict.start()]
                sql = re.sub(r'(?i)^(\s*INSERT\s+)', r'\1OR IGNORE ', sql, count=1)
            # RETURNING id  →  stripped; result via lastrowid
            m_ret = re.search(r'\s+RETURNING\s+\w+', sql, re.IGNORECASE)
            if m_ret:
                sql = sql[:m_ret.start()]
                self._returning_stripped = True
        self._cur.execute(sql, params)
        return self

    def executemany(self, sql: str, params_list):
        if self._dialect == 'sqlite':
            sql = sql.replace('%s', '?')
        self._cur.executemany(sql, params_list)

    def fetchone(self):
        if self._returning_stripped:
            return (self._cur.lastrowid,)
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount


class DbAdapter:
    """Wrappa una connessione raw esponendo un cursore normalizzato e helper SQL dialect-aware."""

    def __init__(self, conn, dialect: str):
        self.conn = conn
        self.dialect = dialect  # 'postgresql' | 'sqlite'

    def cursor(self) -> CursorAdapter:
        return CursorAdapter(self.conn.cursor(), self.dialect)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    # --- Frammenti SQL dialect-aware ---
    # Usare questi metodi nelle query che non si possono normalizzare con semplice
    # sostituzione di placeholder (es. _daily_cleanup, stats).

    def now_expr(self) -> str:
        """Espressione SQL per il timestamp corrente."""
        return "NOW()" if self.dialect == 'postgresql' else "datetime('now')"

    def interval_ago(self, days: int) -> str:
        """Espressione SQL per un timestamp N giorni fa."""
        if self.dialect == 'postgresql':
            return f"NOW() - INTERVAL '{days} days'"
        return f"datetime('now', '-{days} days')"

    def extract_day(self, col: str) -> str:
        """Estrae il giorno da una colonna data/timestamp."""
        if self.dialect == 'postgresql':
            return f"EXTRACT(DAY FROM {col})"
        return f"CAST(strftime('%d', {col}) AS INTEGER)"


def get_db() -> DbAdapter:
    """
    Restituisce il DbAdapter per la request corrente.
    Crea la connessione al primo accesso e la mette in cache su flask.g.
    Viene chiusa automaticamente da close_db() nel teardown_appcontext.
    """
    if 'db' not in g:
        factory = current_app.config['DB_FACTORY']
        dialect = current_app.config['DB_DIALECT']
        g.db = DbAdapter(factory(), dialect)
    return g.db


def close_db(e=None):
    """Chiude la connessione DB a fine request. Registrata in teardown_appcontext."""
    db: DbAdapter = g.pop('db', None)
    if db is not None:
        db.close()
