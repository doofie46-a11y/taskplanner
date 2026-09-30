"""Route principali: home, nuovo task, modifica, completamento, pin, posticipa, elimina."""
import os
import uuid
from datetime import date, datetime, timedelta

from flask import redirect, render_template_string, request, url_for, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from core.db import get_db
from core.logic import (
    _daily_cleanup, _get_cestino_count,
    calcola_priorita_effettiva, get_all_categories, get_tasks_for_date,
)
from core.templates import TEMPLATE_EDIT, TEMPLATE_INDEX, TEMPLATE_NEW
from core.utils import allowed_file, format_time


def register(app):

    @app.route("/", methods=["GET"])
    @login_required
    def home():
        selected_date = request.args.get("date") or date.today().isoformat()
        _daily_cleanup(current_user.id)
        tasks, total_time = get_tasks_for_date(selected_date)
        tasks = [t for t in tasks if t[11]] + [t for t in tasks if not t[11]]
        categories = get_all_categories()
        _cats_by_group = {}
        _cats_nogroup = []
        for _c in categories:
            if _c[3]:
                _cats_by_group.setdefault(_c[3], []).append(_c)
            else:
                _cats_nogroup.append(_c)
        _cats_grouped = list(_cats_by_group.items())
        cestino_count = _get_cestino_count(current_user.id)
        return render_template_string(
            TEMPLATE_INDEX,
            tasks=tasks,
            selected_date=selected_date,
            today_date=date.today().isoformat(),
            total_time=format_time(total_time),
            categories=categories,
            cats_grouped=_cats_grouped,
            cats_nogroup=_cats_nogroup,
            app_version=current_app.config['APP_VERSION'],
            app_codename=current_app.config['APP_CODENAME'],
            current_user=current_user,
            cestino_count=cestino_count,
            has_outlook=current_app.config.get('HAS_OUTLOOK', False),
        )

    @app.route("/new", methods=["GET"])
    @login_required
    def new_task():
        prefill = {
            'titolo':      request.args.get('titolo', ''),
            'data':        request.args.get('data', date.today().isoformat()),
            'ora':         request.args.get('ora', ''),
            'ricorrenza':  request.args.get('ricorrenza', 'none'),
            'priorita':    request.args.get('priorita', 'Media'),
            'category_id': request.args.get('category_id', ''),
            'url':         request.args.get('url', ''),
            'escalation':  request.args.get('escalation', ''),
        }
        categories = get_all_categories()
        return render_template_string(TEMPLATE_NEW, prefill=prefill, categories=categories)

    @app.route("/add", methods=["POST"])
    @login_required
    def add():
        titolo     = request.form.get("titolo")
        data_prev  = request.form.get("data") or date.today().isoformat()
        ora        = request.form.get("ora") or None
        ric        = request.form.get("ricorrenza") or "none"
        prio       = request.form.get("priorita") or "Media"
        cat_id     = request.form.get("category_id") or None
        url        = request.form.get("url") or None
        ric_fine   = request.form.get("ricorrenza_fine") or None
        ric_occ    = request.form.get("ricorrenza_occorrenze") or None
        if ric_occ:
            ric_occ = int(ric_occ) if str(ric_occ).isdigit() else None
        escalation = request.form.get("escalation") or None
        if escalation:
            escalation = int(escalation) if str(escalation).isdigit() else None
        pinned     = 1 if request.form.get("pinned") else 0
        note       = request.form.get("note") or None
        card_color = request.form.get("card_color") or None

        try:
            datetime.strptime(data_prev, "%Y-%m-%d")
            if ora:
                datetime.strptime(ora, "%H:%M")
        except ValueError:
            return "Formato data/ora non valido", 400

        try:
            db = get_db()
            c  = db.cursor()
            c.execute("""
                INSERT INTO tasks
                    (user_id, titolo, data_prevista, ora_prevista, ricorrenza, posticipato_da, priorita,
                     category_id, url, created_at, ricorrenza_fine, ricorrenza_occorrenze, escalation, pinned, note, card_color)
                VALUES (%s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (current_user.id, titolo, data_prev, ora, ric, prio, cat_id, url,
                  date.today().isoformat(), ric_fine, ric_occ, escalation, pinned, note, card_color))
            tid = c.fetchone()[0]

            file = request.files.get('file')
            if file and file.filename != '' and allowed_file(file.filename):
                unique_str  = str(uuid.uuid4())[:8]
                stored_name = f"{tid}_{unique_str}_{secure_filename(file.filename)}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], stored_name))
                c.execute(
                    "INSERT INTO attachments (task_id, stored_name, original_name) VALUES (%s, %s, %s)",
                    (tid, stored_name, file.filename),
                )

            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /add: %s", e)
            return "Errore nel salvataggio", 500

        return redirect(url_for("home", date=data_prev))

    @app.route("/done/<int:tid>", methods=["POST"])
    @login_required
    def done(tid):
        selected_date = request.form.get("date_original") or date.today().isoformat()
        tempo = request.form.get("tempo")
        tempo = int(tempo) if tempo and tempo.isdigit() else None

        try:
            db = get_db()
            c  = db.cursor()
            c.execute("""
                INSERT INTO task_completed (task_id, data_completata, tempo_impiegato)
                VALUES (%s, %s, %s)
                ON CONFLICT (task_id, data_completata) DO NOTHING
            """, (tid, selected_date, tempo))
            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /done: %s", e)
            return "Errore nel completamento", 500

        return redirect(url_for("home", date=selected_date))

    @app.route("/posticipa/<int:tid>", methods=["POST"])
    @login_required
    def posticipa(tid):
        selected_date = request.form.get("date_original") or date.today().isoformat()
        domani = (date.today() + timedelta(days=1)).isoformat()

        try:
            db = get_db()
            c  = db.cursor()
            c.execute(
                "SELECT data_prevista, posticipato_da FROM tasks WHERE id=%s AND user_id=%s AND deleted_at IS NULL",
                (tid, current_user.id),
            )
            row = c.fetchone()
            if row:
                data_p, post_da = row
                new_posticipato = data_p if post_da is None else post_da
                c.execute(
                    "UPDATE tasks SET data_prevista=%s, posticipato_da=%s WHERE id=%s",
                    (domani, new_posticipato, tid),
                )
                c.execute(
                    "INSERT INTO rollover_history (task_id, from_date, to_date) VALUES (%s, %s, %s)",
                    (tid, data_p, domani),
                )
                db.commit()
                current_app.logger.info("Posticipo manuale: task %s da %s a %s", tid, data_p, domani)
        except Exception as e:
            current_app.logger.exception("Errore in /posticipa: %s", e)
            return "Errore nel posticipo", 500

        return redirect(url_for("home", date=selected_date))

    @app.route("/pin/<int:tid>", methods=["POST"])
    @login_required
    def pin_task(tid):
        selected_date = request.form.get("date_original") or date.today().isoformat()
        try:
            db = get_db()
            c  = db.cursor()
            c.execute(
                "SELECT COALESCE(pinned,0) FROM tasks WHERE id=%s AND user_id=%s AND deleted_at IS NULL",
                (tid, current_user.id),
            )
            row = c.fetchone()
            if row:
                c.execute("UPDATE tasks SET pinned=%s WHERE id=%s", (0 if row[0] else 1, tid))
                db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /pin: %s", e)
            return "Errore nel pin", 500
        return redirect(url_for("home", date=selected_date))

    @app.route("/delete/<int:tid>", methods=["POST"])
    @login_required
    def delete_task(tid):
        selected_date = request.form.get("date_original") or date.today().isoformat()
        try:
            db = get_db()
            c  = db.cursor()
            c.execute(
                "SELECT id FROM tasks WHERE id=%s AND user_id=%s AND deleted_at IS NULL",
                (tid, current_user.id),
            )
            if c.fetchone():
                c.execute(
                    f"UPDATE tasks SET deleted_at={db.now_expr()} WHERE id=%s", (tid,)
                )
                db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /delete: %s", e)
            return "Errore nell'eliminazione", 500

        return redirect(url_for("home", date=selected_date))

    @app.route("/edit/<int:tid>", methods=["GET", "POST"])
    @login_required
    def edit_task(tid):
        try:
            db = get_db()
            c  = db.cursor()

            if request.method == "POST":
                titolo     = request.form.get("titolo")
                data_prev  = request.form.get("data")
                ora        = request.form.get("ora") or None
                ric        = request.form.get("ricorrenza")
                prio       = request.form.get("priorita") or "Media"
                cat_id     = request.form.get("category_id") or None
                url        = request.form.get("url") or None
                ric_fine   = request.form.get("ricorrenza_fine") or None
                ric_occ    = request.form.get("ricorrenza_occorrenze") or None
                if ric_occ:
                    ric_occ = int(ric_occ) if str(ric_occ).isdigit() else None
                escalation = request.form.get("escalation") or None
                if escalation:
                    escalation = int(escalation) if str(escalation).isdigit() else None
                pinned     = 1 if request.form.get("pinned") else 0
                note       = request.form.get("note") or None
                card_color = request.form.get("card_color") or None

                try:
                    datetime.strptime(data_prev, "%Y-%m-%d")
                    if ora:
                        datetime.strptime(ora, "%H:%M")
                except ValueError:
                    return "Formato data/ora non valido", 400

                c.execute("""
                    UPDATE tasks
                    SET titolo=%s, data_prevista=%s, ora_prevista=%s, ricorrenza=%s, priorita=%s,
                        category_id=%s, url=%s, ricorrenza_fine=%s, ricorrenza_occorrenze=%s,
                        escalation=%s, pinned=%s, note=%s, card_color=%s
                    WHERE id=%s AND user_id=%s
                """, (titolo, data_prev, ora, ric, prio, cat_id, url, ric_fine, ric_occ,
                      escalation, pinned, note, card_color, tid, current_user.id))

                file = request.files.get('file')
                if file and file.filename != '' and allowed_file(file.filename):
                    unique_str  = str(uuid.uuid4())[:8]
                    stored_name = f"{tid}_{unique_str}_{secure_filename(file.filename)}"
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], stored_name))
                    c.execute(
                        "INSERT INTO attachments (task_id, stored_name, original_name) VALUES (%s, %s, %s)",
                        (tid, stored_name, file.filename),
                    )

                db.commit()
                date_original = request.form.get("date_original") or data_prev
                return redirect(url_for("home", date=date_original))

            # GET
            c.execute("""
                SELECT id, titolo, data_prevista, ora_prevista, ricorrenza, priorita, category_id, url,
                       ricorrenza_fine, ricorrenza_occorrenze, escalation, COALESCE(pinned,0), note, card_color
                FROM tasks
                WHERE id=%s AND user_id=%s AND deleted_at IS NULL
            """, (tid, current_user.id))
            row = c.fetchone()

            categories = get_all_categories()
            if not row:
                return redirect(url_for("home"))

            date_original = request.args.get("date_original") or (str(row[2]) if row else date.today().isoformat())
            return render_template_string(TEMPLATE_EDIT, task=row, categories=categories, date_original=date_original)

        except Exception as e:
            current_app.logger.exception("Errore in /edit: %s", e)
            return "Errore nella modifica", 500
