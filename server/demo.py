"""
Modalità demo pubblica (DEMO_MODE=true): ogni visitatore riceve un account usa e
getta con dati di esempio, cancellato dopo DEMO_TTL_HOURS da `manage purge-demo`.

Nella demo sono disattivati il login normale, gli allegati e l'API (pagina chiavi,
/api/tasks, /add_from_mail): niente hosting di file né endpoint per estranei.
"""
import secrets
from datetime import date, timedelta

from flask import abort, current_app, redirect, request, url_for
from flask_babel import get_locale
from flask_login import login_user

from core.db import get_db
from core.models import User
from server.users import USER_COLUMNS

DEMO_PREFIX = "demo-"

# Path non disponibili nella demo (prefissi)
_BLOCKED = ("/upload/", "/download/", "/delete_attachment/", "/account/",
            "/api/tasks", "/add_from_mail")


def register(app, render_login, csrf_ok):
    max_per_hour = app.config['DEMO_MAX_PER_HOUR']

    @app.before_request
    def _demo_block():
        if request.path.startswith(_BLOCKED):
            abort(403, "Not available in the demo")

    @app.route("/demo/start", methods=["POST"])
    def demo_start():
        if not csrf_ok():
            return render_login(), 400
        db = get_db()
        c  = db.cursor()
        # Tetto globale: limita il riempimento del DB anche se il rate limit
        # per IP del reverse proxy viene aggirato
        c.execute(
            "SELECT COUNT(*) FROM users WHERE username LIKE %s "
            "AND created_at > NOW() - INTERVAL '1 hour'",
            (DEMO_PREFIX + "%",),
        )
        if c.fetchone()[0] >= max_per_hour:
            current_app.logger.warning("Demo: tetto di %s account/ora raggiunto", max_per_hour)
            return render_login(error_busy=True), 503
        username = DEMO_PREFIX + secrets.token_hex(6)
        c.execute(
            "INSERT INTO users (username, email, name) VALUES (%s, '', %s) RETURNING id",
            (username, "Demo"),
        )
        uid  = c.fetchone()[0]
        lang = str(get_locale() or "en")
        seed_demo_data(c, uid, lang if lang in _TEXT else "en")
        c.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (uid,))
        row = c.fetchone()
        db.commit()
        current_app.logger.info("Demo: creato account %s (id %s, %s)", username, uid, lang)
        login_user(User(*row), remember=True)
        return redirect(url_for("home"))


def purge_demo_users(db, hours):
    """Cancella gli account demo più vecchi di `hours` ore. Ritorna quanti."""
    c = db.cursor()
    old = ("SELECT id FROM users WHERE username LIKE %s "
           "AND created_at < NOW() - make_interval(hours => %s)")
    args = (DEMO_PREFIX + "%", hours)
    # task_completed e rollover_history non hanno FK verso tasks: vanno a mano
    for tbl in ("task_completed", "rollover_history"):
        c.execute(f"DELETE FROM {tbl} WHERE task_id IN "
                  f"(SELECT id FROM tasks WHERE user_id IN ({old}))", args)
    c.execute(f"DELETE FROM users WHERE id IN ({old})", args)
    n = c.rowcount
    db.commit()
    return n


# ------------------------------------------------------------- dati di esempio
# Testi nella lingua del visitatore al momento della creazione
_TEXT = {
    "en": {
        "groups": ("Personal", "Job", "Other"),
        "cats": ("Errands", "Health", "Home", "Meetings", "Work", "General"),
        "tasks": (
            "Send invoice to client", "Review quarterly budget", "Monthly report",
            "Prepare slides for Thursday demo", "Team stand-up", "Go to the gym",
            "Buy groceries", "Water the plants", "Book dentist appointment",
            "Pay electricity bill", "Read one chapter of a book",
        ),
        "note": "Double-click a card to see its details. Try ✔ Complete, 🕒 Postpone and 📌 Pin.",
        "mcats": ("Salary", "Rent", "Groceries", "Free time"),
        "mnote": "Weekly shopping",
    },
    "it": {
        "groups": ("Personale", "Lavoro", "Altro"),
        "cats": ("Commissioni", "Salute", "Casa", "Riunioni", "Ufficio", "Generale"),
        "tasks": (
            "Inviare fattura al cliente", "Rivedere il budget trimestrale", "Report mensile",
            "Preparare le slide per la demo di giovedì", "Riunione di team", "Palestra",
            "Fare la spesa", "Innaffiare le piante", "Prenotare il dentista",
            "Pagare la bolletta della luce", "Leggere un capitolo di un libro",
        ),
        "note": "Doppio clic su una card per vederne i dettagli. Prova ✔ Completa, 🕒 Posticipa e 📌 Fissa.",
        "mcats": ("Stipendio", "Affitto", "Spesa", "Tempo libero"),
        "mnote": "Spesa settimanale",
    },
}


def seed_demo_data(c, uid, lang):
    t     = _TEXT[lang]
    today = date.today()
    g_pers, g_job, g_other = t["groups"]
    cat_rows = (
        (t["cats"][0], "#f97316", g_pers), (t["cats"][1], "#dc2626", g_pers),
        (t["cats"][2], "#16a34a", g_pers), (t["cats"][3], "#9333ea", g_job),
        (t["cats"][4], "#2563eb", g_job),  (t["cats"][5], "#6c757d", g_other),
    )
    cat = []
    for name, color, group in cat_rows:
        c.execute(
            "INSERT INTO categories (user_id, name, color, group_name) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (uid, name, color, group),
        )
        cat.append(c.fetchone()[0])
    errands, health, home, meetings, work, general = cat

    d = lambda n: today + timedelta(days=n)  # noqa: E731
    # primo lunedì del mese scorso: inizio della serie "monthly_first_monday"
    first_monday = (date(today.year, today.month, 1) - timedelta(days=1)).replace(day=1)
    first_monday += timedelta(days=(7 - first_monday.weekday()) % 7)
    # (titolo, data, ora, ricorrenza, priorità, categoria, pinned, posticipato_da, note)
    tasks = (
        (0, d(0),  "11:00", "none",  "Urgente", work,     1, None,  t["note"]),
        (1, d(0),  "09:30", "none",  "Urgente", work,     0, d(-3), None),
        (2, first_monday, "09:00", "monthly_first_monday", "Alta", work, 0, None, None),
        (3, d(0),  "14:30", "none",  "Alta",    work,     0, None,  None),
        (4, d(-14), "09:00", "daily", "Media",  meetings, 0, None,  None),
        (5, d(-10), "18:30", "every2days", "Media", health, 0, None, None),
        (6, d(0),  None,    "none",  "Bassa",   errands,  0, None,  None),
        (7, d(-6), None,    "weekly", "Bassa",  home,     0, None,  None),
        (8, d(1),  None,    "none",  "Media",   health,   0, None,  None),
        (9, d(3),  None,    "none",  "Alta",    home,     0, None,  None),
        (10, d(-20), "22:00", "daily", "Bassa", general,  0, None,  None),
    )
    ids = []
    for i, data, ora, ric, prio, cid, pinned, post, note in tasks:
        c.execute(
            "INSERT INTO tasks (user_id, titolo, data_prevista, ora_prevista, ricorrenza, "
            "priorita, category_id, pinned, posticipato_da, note, escalation, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (uid, t["tasks"][i], data, ora, ric, prio, cid, pinned, post, note,
             2 if post else None, d(-20)),
        )
        ids.append(c.fetchone()[0])

    # Storico completamenti per avere statistiche non vuote
    done = [(ids[4], n, 15) for n in range(1, 14) if n % 7 not in (5, 6)]
    done += [(ids[5], n, 50) for n in range(2, 11, 2)]
    done += [(ids[10], n, 25) for n in range(1, 20) if n % 3]
    done += [(ids[7], 6, 5), (ids[4], 0, 20)]
    for tid, ago, minutes in done:
        c.execute(
            "INSERT INTO task_completed (task_id, data_completata, tempo_impiegato) "
            "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (tid, d(-ago), minutes),
        )

    # Contaschei
    mcat = []
    for (name, kind, color) in zip(t["mcats"], ("income", "expense", "expense", "expense"),
                                   ("#16a34a", "#dc2626", "#f97316", "#9333ea")):
        c.execute(
            "INSERT INTO movement_categories (user_id, name, type, color) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (uid, name, kind, color),
        )
        mcat.append((c.fetchone()[0], kind))
    start = date(today.year, today.month, 1) - timedelta(days=62)
    movements = (
        (0, 2400, start.replace(day=27), "monthly", None),
        (1, 850,  start.replace(day=1),  "monthly", None),
        (2, 70,   d(-25), "weekly", t["mnote"]),
        (3, 45,   d(-9),  "none",  None),
        (3, 120,  d(-40), "none",  None),
    )
    for k, amount, day, ric, note in movements:
        mid, kind = mcat[k]
        c.execute(
            "INSERT INTO movements (user_id, category_id, tipo, amount, date, ricorrenza, "
            "note, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (uid, mid, kind, amount, day, ric, note, today),
        )
