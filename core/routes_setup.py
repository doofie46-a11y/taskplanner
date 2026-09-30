"""Route gestione categorie."""
from flask import redirect, render_template_string, request, url_for, current_app
from flask_login import current_user, login_required

from core.db import get_db
from core.logic import get_all_categories
from core.templates import TEMPLATE_SETUP


def register(app):

    @app.route("/setup/categories")
    @login_required
    def setup_categories():
        cats = get_all_categories()
        return render_template_string(TEMPLATE_SETUP, categories=cats)

    @app.route("/setup/categories/add", methods=["POST"])
    @login_required
    def add_category():
        name       = request.form.get("name")
        color      = request.form.get("color") or "#007bff"
        group_name = request.form.get("group_name") or None
        if name:
            try:
                db = get_db()
                c  = db.cursor()
                c.execute(
                    "INSERT INTO categories (user_id, name, color, group_name) VALUES (%s, %s, %s, %s)",
                    (current_user.id, name, color, group_name),
                )
                db.commit()
            except Exception as e:
                current_app.logger.exception("Errore in /setup/categories/add: %s", e)
        return redirect(url_for("setup_categories"))

    @app.route("/setup/categories/delete/<int:cid>", methods=["POST"])
    @login_required
    def delete_category(cid):
        try:
            db = get_db()
            c  = db.cursor()
            c.execute(
                "UPDATE tasks SET category_id = NULL WHERE category_id = %s AND user_id = %s",
                (cid, current_user.id),
            )
            c.execute(
                "DELETE FROM categories WHERE id = %s AND user_id = %s",
                (cid, current_user.id),
            )
            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /setup/categories/delete: %s", e)
        return redirect(url_for("setup_categories"))

    @app.route("/setup/categories/update/<int:cid>", methods=["POST"])
    @login_required
    def update_category(cid):
        name       = request.form.get("name")
        color      = request.form.get("color") or "#007bff"
        group_name = request.form.get("group_name") or None
        if name:
            try:
                db = get_db()
                c  = db.cursor()
                c.execute(
                    "UPDATE categories SET name=%s, color=%s, group_name=%s WHERE id=%s AND user_id=%s",
                    (name, color, group_name, cid, current_user.id),
                )
                db.commit()
            except Exception as e:
                current_app.logger.exception("Errore in /setup/categories/update: %s", e)
        return redirect(url_for("setup_categories"))
