"""Route allegati: upload, download, elimina."""
import os
import uuid
from datetime import date

from flask import current_app, redirect, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from core.db import get_db
from core.utils import allowed_file


def register(app):

    @app.route("/upload/<int:tid>", methods=["POST"])
    @login_required
    def upload_attachment(tid):
        selected_date = request.form.get("date_original") or date.today().isoformat()

        if 'file' not in request.files:
            return redirect(url_for("home", date=selected_date))

        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return redirect(url_for("home", date=selected_date))

        if file:
            original_name = file.filename
            unique_str    = str(uuid.uuid4())[:8]
            stored_name   = f"{tid}_{unique_str}_{secure_filename(original_name)}"
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], stored_name))

            try:
                db = get_db()
                c  = db.cursor()
                c.execute(
                    "SELECT id FROM tasks WHERE id=%s AND user_id=%s AND deleted_at IS NULL",
                    (tid, current_user.id),
                )
                if c.fetchone():
                    c.execute(
                        "INSERT INTO attachments (task_id, stored_name, original_name) VALUES (%s, %s, %s)",
                        (tid, stored_name, original_name),
                    )
                    db.commit()
            except Exception as e:
                current_app.logger.exception("Errore salvataggio allegato: %s", e)

        return redirect(url_for("home", date=selected_date))

    @app.route("/download/<int:aid>")
    @login_required
    def download_attachment(aid):
        from flask import send_from_directory
        db = get_db()
        c  = db.cursor()
        c.execute("""
            SELECT a.stored_name, a.original_name
            FROM attachments a
            JOIN tasks t ON t.id = a.task_id
            WHERE a.id=%s AND t.user_id=%s
        """, (aid, current_user.id))
        row = c.fetchone()

        if row:
            return send_from_directory(
                current_app.config['UPLOAD_FOLDER'],
                row[0],
                download_name=row[1],
                as_attachment=True,
            )
        return "File non trovato", 404

    @app.route("/delete_attachment/<int:aid>", methods=["POST"])
    @login_required
    def delete_attachment(aid):
        selected_date = request.form.get("date_original") or date.today().isoformat()
        try:
            db = get_db()
            c  = db.cursor()
            c.execute("""
                SELECT a.stored_name FROM attachments a
                JOIN tasks t ON t.id = a.task_id
                WHERE a.id=%s AND t.user_id=%s
            """, (aid, current_user.id))
            row = c.fetchone()
            if row:
                stored_name = row[0]
                file_path   = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_name)
                c.execute("DELETE FROM attachments WHERE id=%s", (aid,))
                if os.path.exists(file_path):
                    os.remove(file_path)
                db.commit()
        except Exception as e:
            current_app.logger.exception("Errore eliminazione allegato: %s", e)
        return redirect(url_for("home", date=selected_date))
