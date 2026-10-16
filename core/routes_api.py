"""Route API: tasks_stato, tasks_in_scadenza, /api/tasks (alias storico /add_from_mail)."""
import json as _json
import re as _re
from datetime import date, datetime, timedelta

from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from core.api_keys import find_user_by_key
from core.db import get_db
from core.logic import get_tasks_for_date
from core.utils import is_safe_url


def register(app):

    @app.route("/tasks_stato")
    @login_required
    def tasks_stato():
        selected_date = request.args.get("date") or date.today().isoformat()
        try:
            tasks, total_time = get_tasks_for_date(selected_date)
            stato = [
                {
                    "id": t[0],
                    "completed": bool(t[3]),
                    "in_scadenza": bool(t[7]),
                    "priorita": t[9],
                    "prio_base": t[15],
                    "livelli_scalati": t[16],
                }
                for t in tasks
            ]
            return jsonify({"tasks": stato, "total": len(tasks)})
        except Exception:
            current_app.logger.exception("Errore in /tasks_stato")
            return jsonify({"tasks": [], "total": 0}), 500

    @app.route("/tasks_in_scadenza")
    @login_required
    def tasks_in_scadenza():
        selected_date = request.args.get("date") or date.today().isoformat()
        try:
            tasks, _ = get_tasks_for_date(selected_date)
            in_scad = [
                {"id": t[0], "titolo": t[1], "ora": t[2]}
                for t in tasks
                if t[7] and not t[3]
            ]
            return jsonify(in_scad)
        except Exception:
            current_app.logger.exception("Errore in /tasks_in_scadenza")
            return jsonify([]), 500

    @app.route("/api/tasks", methods=["POST"])
    @app.route("/add_from_mail", methods=["POST"])
    def add_from_mail():
        """
        Crea un task da client esterni (Outlook, HTTP Shortcuts, script).
        Chiave in header X-API-Key o Authorization: Bearer (o, per compatibilità,
        nel campo api_key del JSON). Messaggi d'errore in inglese, con il campo
        sbagliato in "field", così i client li possono gestire.
        """
        raw = request.get_data(as_text=True)
        masked = _mask_key(raw)
        current_app.logger.debug("add_from_mail body (%d chars): %s", len(raw), masked[:1000])

        data = None
        try:
            data = _json.loads(raw)
        except _json.JSONDecodeError as e:
            ctx_start = max(0, e.pos - 40)
            ctx_end   = min(len(raw), e.pos + 40)
            current_app.logger.warning(
                "add_from_mail JSON error '%s' at pos %d | ...%s[HERE]%s...",
                e.msg, e.pos, repr(masked[ctx_start:e.pos]), repr(masked[e.pos:ctx_end]),
            )
            cleaned = _re.sub(r'[\x00-\x08\x0b-\x1f]', '', raw)
            try:
                data = _json.loads(cleaned)
            except _json.JSONDecodeError:
                return _err("Malformed JSON body")
        if not data:
            return _err("Missing JSON body")
        if not isinstance(data, dict):
            return _err("JSON body must be an object")

        api_key = _request_key(data)
        if not api_key:
            return _err("Missing API key: send it in the X-API-Key header", status=401)

        try:
            db = get_db()
            found = find_user_by_key(db, api_key)
            if not found:
                db.rollback()
                return _err("Invalid or revoked API key", status=403)
            uid = found[1]
            db.commit()  # salva last_used_at anche se poi i dati non sono validi

            fields, error = _parse_task(db, uid, data)
            if error:
                return error

            c = db.cursor()
            c.execute("""
                INSERT INTO tasks
                    (user_id, titolo, data_prevista, ora_prevista, ricorrenza, posticipato_da,
                     priorita, category_id, url, created_at, note)
                VALUES (%s, %s, %s, %s, 'none', NULL, %s, %s, %s, %s, %s)
                RETURNING id
            """, (uid, fields["titolo"], fields["data_prevista"], fields["ora"],
                  fields["priorita"], fields["category_id"], fields["url"],
                  date.today().isoformat(), fields["note"]))
            tid = c.fetchone()[0]
            db.commit()
            current_app.logger.info(
                "add_from_mail: task #%d creato per user %s — '%s'", tid, uid, fields["titolo"]
            )
            return jsonify({
                "ok": True, "task_id": tid, "titolo": fields["titolo"],
                "data_prevista": fields["data_prevista"], "ora": fields["ora"],
                "priorita": fields["priorita"], "categoria": fields["categoria"],
                "url": fields["url"],
            })
        except Exception as e:
            current_app.logger.exception("Errore in /add_from_mail: %s", e)
            return _err("Database error", status=500)


# ------------------------------------------------------------- /api/tasks

MAX_TITLE_LEN = 500
MAX_URL_LEN   = 2000
API_FIELDS = ("titolo", "note", "data_prevista", "ora", "priorita", "categoria", "url", "api_key")

# Priorità accettate in italiano e in inglese, senza distinzione maiuscole/minuscole
_PRIO_ALIASES = {
    "bassa": "Bassa", "low": "Bassa",
    "media": "Media", "medium": "Media",
    "alta": "Alta", "high": "Alta",
    "urgente": "Urgente", "urgent": "Urgente",
}
_TODAY_WORDS    = ("oggi", "today")
_TOMORROW_WORDS = ("domani", "tomorrow")

# La chiave nel JSON (client vecchi) non deve finire nel log: si sostituisce con
# asterischi della stessa lunghezza, così le posizioni degli errori JSON restano giuste
_KEY_IN_BODY = _re.compile(r'("api_key"\s*:\s*")([^"]*)')


def _mask_key(raw):
    return _KEY_IN_BODY.sub(lambda m: m.group(1) + "*" * len(m.group(2)), raw)


def _err(message, field=None, status=400):
    body = {"ok": False, "error": message}
    if field:
        body["field"] = field
    return jsonify(body), status


def _request_key(data):
    key = request.headers.get("X-API-Key") or ""
    if not key:
        auth = request.headers.get("Authorization") or ""
        if auth[:7].lower() == "bearer ":
            key = auth[7:]
    if not key and isinstance(data.get("api_key"), str):
        key = data["api_key"]
    return key.strip()


def _parse_date(value):
    """YYYY-MM-DD, oggi/today, domani/tomorrow, +N giorni. None se non valida."""
    v = value.strip().lower()
    today = date.today()
    if not v or v in _TODAY_WORDS:
        return today
    if v in _TOMORROW_WORDS:
        return today + timedelta(days=1)
    if _re.fullmatch(r"\+\d{1,4}", v):
        return today + timedelta(days=int(v[1:]))
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_task(db, uid, data):
    """Valida il JSON. Ritorna (campi, None) oppure (None, risposta d'errore)."""
    unknown = [k for k in data if k not in API_FIELDS]
    if unknown:
        return None, _err(
            f"Unknown field '{unknown[0]}'. Allowed fields: {', '.join(API_FIELDS[:-1])}",
            unknown[0],
        )
    for k, v in data.items():
        if v is not None and not isinstance(v, str):
            return None, _err(f"Field '{k}' must be a string", k)

    def get(k):
        return (data.get(k) or "").strip()

    titolo = get("titolo")
    if not titolo:
        return None, _err("Field 'titolo' is required", "titolo")
    if len(titolo) > MAX_TITLE_LEN:
        return None, _err(
            f"Field 'titolo' is too long ({len(titolo)} characters, max {MAX_TITLE_LEN})", "titolo"
        )

    data_prev = _parse_date(get("data_prevista"))
    if data_prev is None:
        return None, _err(
            f"Invalid date '{get('data_prevista')}'. Use YYYY-MM-DD, today, tomorrow or +N (days from today)",
            "data_prevista",
        )

    ora = get("ora") or None
    if ora:
        try:
            ora = datetime.strptime(ora, "%H:%M").strftime("%H:%M")
        except ValueError:
            return None, _err(f"Invalid time '{ora}'. Use HH:MM, e.g. 09:30", "ora")

    priorita = "Media"
    if get("priorita"):
        priorita = _PRIO_ALIASES.get(get("priorita").lower())
        if not priorita:
            return None, _err(
                f"Invalid priority '{get('priorita')}'. Allowed values: Bassa, Media, Alta, Urgente "
                "(or Low, Medium, High, Urgent)",
                "priorita",
            )

    category_id, categoria = None, None
    if get("categoria"):
        c = db.cursor()
        c.execute("SELECT id, name FROM categories WHERE user_id = %s ORDER BY id", (uid,))
        cats = c.fetchall()
        wanted = get("categoria").casefold()
        match = next((row for row in cats if (row[1] or "").strip().casefold() == wanted), None)
        if not match:
            names = ", ".join(row[1] for row in cats) or "none"
            return None, _err(
                f"Category '{get('categoria')}' not found. Your categories: {names}", "categoria"
            )
        category_id, categoria = match

    url = get("url") or None
    if url:
        # Solo http/https: l'URL diventa un link nella card (niente javascript: e simili)
        if not is_safe_url(url):
            return None, _err("Invalid URL: it must start with http:// or https://", "url")
        if len(url) > MAX_URL_LEN:
            return None, _err(f"URL too long (max {MAX_URL_LEN} characters)", "url")

    return {
        "titolo": titolo, "note": get("note") or None, "data_prevista": data_prev.isoformat(),
        "ora": ora, "priorita": priorita, "category_id": category_id, "categoria": categoria,
        "url": url,
    }, None
