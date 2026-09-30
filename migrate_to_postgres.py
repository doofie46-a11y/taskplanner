"""
Script di migrazione: SQLite → PostgreSQL per TaskPlanner.

Uso:
    python3 migrate_to_postgres.py --sqlite ~/.taskplanner/taskplanner.db \
                                   --user-email tuo@gmail.com

Il parametro --user-email identifica l'utente Google già registrato nel DB PostgreSQL
(deve aver fatto almeno un login prima di eseguire la migrazione).
Se l'utente non esiste viene creato con un google_id placeholder.
"""

import argparse
import sqlite3
import psycopg2
import os
import sys

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def connect_sqlite(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def connect_pg():
    if not DATABASE_URL:
        sys.exit("DATABASE_URL non impostata.")
    return psycopg2.connect(DATABASE_URL)


def get_or_create_user(pg, email):
    c = pg.cursor()
    c.execute("SELECT id FROM users WHERE email = %s", (email,))
    row = c.fetchone()
    if row:
        print(f"Utente trovato: id={row[0]}")
        return row[0]
    # Crea utente placeholder (google_id fittizio, verrà aggiornato al primo login OAuth)
    import uuid
    fake_google_id = f"migrated_{uuid.uuid4().hex[:16]}"
    c.execute("""
        INSERT INTO users (google_id, email, name, picture)
        VALUES (%s, %s, %s, '')
        RETURNING id
    """, (fake_google_id, email, email.split('@')[0]))
    uid = c.fetchone()[0]
    pg.commit()
    print(f"Utente creato: id={uid}, email={email}")
    return uid


def migrate(sqlite_path, user_email):
    print(f"=== Migrazione da SQLite: {sqlite_path} ===")
    sq = connect_sqlite(sqlite_path)
    pg = connect_pg()
    pgc = pg.cursor()

    uid = get_or_create_user(pg, user_email)

    # --- Categorie ---
    print("Migrazione categorie...")
    sq_cats = sq.execute("SELECT id, name, color FROM categories").fetchall()
    cat_id_map = {}  # sqlite_id → pg_id
    for r in sq_cats:
        pgc.execute("""
            INSERT INTO categories (user_id, name, color) VALUES (%s, %s, %s) RETURNING id
        """, (uid, r['name'], r['color'] or '#007bff'))
        pg_id = pgc.fetchone()[0]
        cat_id_map[r['id']] = pg_id
    pg.commit()
    print(f"  {len(sq_cats)} categorie migrate")

    # --- Tasks ---
    print("Migrazione tasks...")
    # Leggi colonne disponibili nel SQLite (sync_casa potrebbe mancare nelle versioni vecchie)
    sq_cols = {row[1] for row in sq.execute("PRAGMA table_info(tasks)").fetchall()}
    sync_casa_sql = "sync_casa" if "sync_casa" in sq_cols else "0 AS sync_casa"

    sq_tasks = sq.execute(f"""
        SELECT id, titolo, data_prevista, ora_prevista, ricorrenza, ricorrenza_fine,
               ricorrenza_occorrenze, posticipato_da, priorita, category_id, url,
               escalation, pinned, note, card_color, created_at, {sync_casa_sql}
        FROM tasks
    """).fetchall()
    task_id_map = {}
    for r in sq_tasks:
        cat_pg = cat_id_map.get(r['category_id']) if r['category_id'] else None
        pgc.execute("""
            INSERT INTO tasks (
                user_id, titolo, data_prevista, ora_prevista, ricorrenza, ricorrenza_fine,
                ricorrenza_occorrenze, posticipato_da, priorita, category_id, url,
                escalation, pinned, note, card_color, created_at, sync_casa
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            uid, r['titolo'], r['data_prevista'], r['ora_prevista'],
            r['ricorrenza'] or 'none', r['ricorrenza_fine'], r['ricorrenza_occorrenze'],
            r['posticipato_da'], r['priorita'] or 'Media', cat_pg, r['url'],
            r['escalation'], r['pinned'] or 0, r['note'], r['card_color'],
            r['created_at'], r['sync_casa'] or 0
        ))
        pg_id = pgc.fetchone()[0]
        task_id_map[r['id']] = pg_id
    pg.commit()
    print(f"  {len(sq_tasks)} tasks migrati")

    # --- task_completed ---
    print("Migrazione task_completed...")
    sq_tc = sq.execute("SELECT task_id, data_completata, tempo_impiegato FROM task_completed").fetchall()
    migrated_tc = 0
    for r in sq_tc:
        pg_tid = task_id_map.get(r['task_id'])
        if not pg_tid:
            continue
        pgc.execute("""
            INSERT INTO task_completed (task_id, data_completata, tempo_impiegato)
            VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
        """, (pg_tid, r['data_completata'], r['tempo_impiegato']))
        migrated_tc += 1
    pg.commit()
    print(f"  {migrated_tc} completamenti migrati")

    # --- rollover_history ---
    print("Migrazione rollover_history...")
    sq_rh = sq.execute("SELECT task_id, from_date, to_date FROM rollover_history").fetchall()
    migrated_rh = 0
    for r in sq_rh:
        pg_tid = task_id_map.get(r['task_id'])
        if not pg_tid:
            continue
        pgc.execute("""
            INSERT INTO rollover_history (task_id, from_date, to_date) VALUES (%s, %s, %s)
        """, (pg_tid, r['from_date'], r['to_date']))
        migrated_rh += 1
    pg.commit()
    print(f"  {migrated_rh} rollover migrati")

    # --- attachments ---
    print("Migrazione attachments (solo metadati DB, i file rimangono nella stessa cartella)...")
    sq_att = sq.execute("SELECT task_id, stored_name, original_name FROM attachments").fetchall()
    migrated_att = 0
    for r in sq_att:
        pg_tid = task_id_map.get(r['task_id'])
        if not pg_tid:
            continue
        pgc.execute("""
            INSERT INTO attachments (task_id, stored_name, original_name) VALUES (%s, %s, %s)
        """, (pg_tid, r['stored_name'], r['original_name']))
        migrated_att += 1
    pg.commit()
    print(f"  {migrated_att} allegati migrati")

    sq.close()
    pg.close()
    print("=== Migrazione completata! ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migra TaskPlanner da SQLite a PostgreSQL")
    parser.add_argument("--sqlite", default=os.path.expanduser("~/.taskplanner/taskplanner.db"),
                        help="Percorso del file SQLite sorgente")
    parser.add_argument("--user-email", required=True,
                        help="Email Google dell'utente proprietario dei dati")
    args = parser.parse_args()

    if not os.path.exists(args.sqlite):
        print(f"Errore: file SQLite non trovato: {args.sqlite}")
        sys.exit(1)

    migrate(args.sqlite, args.user_email)
