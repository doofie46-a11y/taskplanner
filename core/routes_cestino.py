"""Route cestino: lista, ripristino, eliminazione singola, svuota."""
import os
from datetime import date, datetime

from flask import current_app, redirect, render_template_string, request, url_for
from flask_login import current_user, login_required

from core.db import get_db
from core.templates import TEMPLATE_CESTINO


def _parse_deleted_at(deleted_at):
    """Normalizza deleted_at (str o datetime tz-aware) a datetime naive."""
    if deleted_at is None:
        return None
    if isinstance(deleted_at, str):
        # SQLite restituisce stringhe tipo '2025-05-20 10:30:00.123456'
        return datetime.fromisoformat(deleted_at.split('.')[0])
    # psycopg2 restituisce datetime tz-aware
    if hasattr(deleted_at, 'tzinfo') and deleted_at.tzinfo is not None:
        return deleted_at.replace(tzinfo=None)
    return deleted_at


def register(app):

    @app.route("/cestino")
    @login_required
    def cestino():
        try:
            db = get_db()
            c  = db.cursor()
            c.execute("""
                SELECT id, titolo, data_prevista, priorita, deleted_at
                FROM tasks
                WHERE user_id=%s AND deleted_at IS NOT NULL
                ORDER BY deleted_at DESC
            """, (current_user.id,))
            rows = c.fetchall()
        except Exception as e:
            current_app.logger.exception("Errore in /cestino: %s", e)
            rows = []

        now = datetime.now()
        task_eliminati = []
        for row in rows:
            tid, titolo, data_prev, priorita, deleted_at = row
            try:
                dt              = _parse_deleted_at(deleted_at)
                giorni_trascorsi = (now - dt).days if dt else 0
                giorni_rimasti  = max(0, 7 - giorni_trascorsi)
            except Exception:
                giorni_rimasti = 7
            task_eliminati.append((tid, titolo, data_prev, priorita, deleted_at, giorni_rimasti))

        return render_template_string(
            TEMPLATE_CESTINO,
            task_eliminati=task_eliminati,
            app_version=current_app.config['APP_VERSION'],
            app_codename=current_app.config['APP_CODENAME'],
            current_user=current_user,
            cestino_count=len(task_eliminati),
        )

    @app.route("/cestino/restore/<int:tid>", methods=["POST"])
    @login_required
    def cestino_restore(tid):
        try:
            db = get_db()
            c  = db.cursor()
            c.execute("""
                UPDATE tasks SET deleted_at=NULL, data_prevista=%s
                WHERE id=%s AND user_id=%s AND deleted_at IS NOT NULL
            """, (date.today().isoformat(), tid, current_user.id))
            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /cestino/restore: %s", e)
        return redirect(url_for("cestino"))

    @app.route("/cestino/elimina/<int:tid>", methods=["POST"])
    @login_required
    def cestino_elimina(tid):
        try:
            db = get_db()
            c  = db.cursor()
            c.execute(
                "SELECT id FROM tasks WHERE id=%s AND user_id=%s AND deleted_at IS NOT NULL",
                (tid, current_user.id),
            )
            if c.fetchone():
                c.execute("SELECT stored_name FROM attachments WHERE task_id=%s", (tid,))
                for (fname,) in c.fetchall():
                    fpath = os.path.join(current_app.config['UPLOAD_FOLDER'], fname)
                    try:
                        if os.path.exists(fpath):
                            os.remove(fpath)
                    except Exception:
                        pass
                c.execute("DELETE FROM task_completed   WHERE task_id=%s", (tid,))
                c.execute("DELETE FROM rollover_history WHERE task_id=%s", (tid,))
                c.execute("DELETE FROM tasks            WHERE id=%s",      (tid,))
                db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /cestino/elimina: %s", e)
        return redirect(url_for("cestino"))

    @app.route("/cestino/svuota", methods=["POST"])
    @login_required
    def cestino_svuota():
        try:
            db = get_db()
            c  = db.cursor()
            c.execute(
                "SELECT id FROM tasks WHERE user_id=%s AND deleted_at IS NOT NULL",
                (current_user.id,),
            )
            ids = [r[0] for r in c.fetchall()]
            for tid in ids:
                c.execute("SELECT stored_name FROM attachments WHERE task_id=%s", (tid,))
                for (fname,) in c.fetchall():
                    fpath = os.path.join(current_app.config['UPLOAD_FOLDER'], fname)
                    try:
                        if os.path.exists(fpath):
                            os.remove(fpath)
                    except Exception:
                        pass
                c.execute("DELETE FROM task_completed   WHERE task_id=%s", (tid,))
                c.execute("DELETE FROM rollover_history WHERE task_id=%s", (tid,))
                c.execute("DELETE FROM tasks            WHERE id=%s",      (tid,))
            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /cestino/svuota: %s", e)
        return redirect(url_for("cestino"))
