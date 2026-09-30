"""Route API: tasks_stato, tasks_in_scadenza, add_from_mail."""
import json as _json
import re as _re
from datetime import date

from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from core.db import get_db
from core.logic import get_tasks_for_date


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

    @app.route("/add_from_mail", methods=["POST"])
    def add_from_mail():
        """Crea un task da email inoltrata via macro Outlook VBA. Richiede api_key nel JSON."""
        from datetime import datetime
        raw = request.get_data(as_text=True)
        current_app.logger.debug("add_from_mail body (%d chars): %s", len(raw), raw[:1000])

        data = None
        try:
            data = _json.loads(raw)
        except _json.JSONDecodeError as e:
            ctx_start = max(0, e.pos - 40)
            ctx_end   = min(len(raw), e.pos + 40)
            current_app.logger.warning(
                "add_from_mail JSON error '%s' at pos %d | ...%s[HERE]%s...",
                e.msg, e.pos, repr(raw[ctx_start:e.pos]), repr(raw[e.pos:ctx_end]),
            )
            cleaned = _re.sub(r'[\x00-\x08\x0b-\x1f]', '', raw)
            try:
                data = _json.loads(cleaned)
            except _json.JSONDecodeError:
                return jsonify({"ok": False, "error": "JSON malformato"}), 400
        if not data:
            return jsonify({"ok": False, "error": "JSON mancante"}), 400

        api_key = (request.headers.get("X-API-Key") or data.get("api_key") or "").strip()
        if not api_key:
            return jsonify({"ok": False, "error": "api_key mancante"}), 401

        try:
            db = get_db()
            c  = db.cursor()
            c.execute("SELECT id FROM users WHERE api_key = %s", (api_key,))
            user_row = c.fetchone()
            if not user_row:
                return jsonify({"ok": False, "error": "api_key non valida"}), 403
            uid = user_row[0]

            titolo = (data.get("titolo") or "").strip()
            if not titolo:
                return jsonify({"ok": False, "error": "Titolo mancante"}), 400

            note      = (data.get("note") or "").strip() or None
            data_prev = (data.get("data_prevista") or date.today().isoformat()).strip()
            try:
                datetime.strptime(data_prev, "%Y-%m-%d")
            except ValueError:
                data_prev = date.today().isoformat()

            c.execute("""
                INSERT INTO tasks
                    (user_id, titolo, data_prevista, ora_prevista, ricorrenza, posticipato_da,
                     priorita, category_id, url, created_at, note)
                VALUES (%s, %s, %s, NULL, 'none', NULL, 'Media', NULL, NULL, %s, %s)
                RETURNING id
            """, (uid, titolo, data_prev, date.today().isoformat(), note))
            tid = c.fetchone()[0]
            db.commit()
            current_app.logger.info(
                "add_from_mail: task #%d creato per user %s — '%s'", tid, uid, titolo
            )
            return jsonify({"ok": True, "task_id": tid, "titolo": titolo})
        except Exception as e:
            current_app.logger.exception("Errore in /add_from_mail: %s", e)
            return jsonify({"ok": False, "error": "Errore DB"}), 500
