"""Route Contaschei: gestione entrate/spese personali, tipologie e bilancio per periodo."""
from datetime import date, datetime

from flask import current_app, redirect, render_template_string, request, url_for
from flask_login import current_user, login_required

from core.db import get_db
from core.logic import (
    _expand_recurring_movements,
    get_all_movement_categories,
    get_movement_exceptions_map,
    get_period_bounds,
)
from core.models import MOVEMENT_TYPES
from core.templates import (
    TEMPLATE_CONTASCHEI,
    TEMPLATE_CONTASCHEI_BILANCIO,
    TEMPLATE_CONTASCHEI_CATEGORIES,
)

PERIOD_TYPES = ["month", "bimonth", "quarter", "fourmonth", "semester", "year"]
SORT_FIELDS  = {"date", "amount", "tipo", "categoria"}
SORT_DIRS    = {"asc", "desc"}


def _make_sort_key(o, field):
    if field == "amount":
        return o["amount"]
    if field == "tipo":
        return o["tipo"] or ""
    if field == "categoria":
        return o["categoria"] or ""
    return o["occurrence_date"] or ""


def _load_movement_rows(uid, date_from, date_to, tipo=None, cat_ids=None, search=None):
    """Carica le righe movimento (con la categoria in join) che possono avere occorrenze nel range."""
    db = get_db()
    c  = db.cursor()
    conds  = [
        "m.user_id = %s", "m.date <= %s",
        "(m.ricorrenza_fine IS NULL OR m.ricorrenza_fine >= %s)",
        "(m.ricorrenza != 'none' OR m.date >= %s)",
    ]
    params = [uid, date_to, date_from, date_from]
    if tipo:
        conds.append("m.tipo = %s")
        params.append(tipo)
    if cat_ids:
        ph = ",".join(["%s"] * len(cat_ids))
        conds.append(f"m.category_id IN ({ph})")
        params.extend(cat_ids)
    if search:
        conds.append("(LOWER(m.note) LIKE LOWER(%s) OR LOWER(mc.name) LIKE LOWER(%s))")
        like = f"%{search}%"
        params.extend([like, like])
    c.execute(f"""
        SELECT m.id, m.category_id, mc.name, mc.color, m.tipo, m.amount, m.date,
               m.ricorrenza, m.ricorrenza_fine, m.ricorrenza_occorrenze, m.note
        FROM movements m LEFT JOIN movement_categories mc ON mc.id = m.category_id
        WHERE {' AND '.join(conds)}
        ORDER BY m.date DESC, m.id DESC
    """, params)
    return c.fetchall()


def _expand_for_period(uid, date_from, date_to, tipo=None, cat_ids=None, search=None):
    rows = _load_movement_rows(uid, date_from, date_to, tipo, cat_ids, search)
    mids = [r[0] for r in rows]
    exceptions = get_movement_exceptions_map(mids, date_from, date_to)
    return _expand_recurring_movements(rows, date_from, date_to, exceptions)


def _apply_sort(occurrences, sort1, sort1_dir, sort2, sort2_dir):
    if sort2 and sort2 in SORT_FIELDS:
        occurrences.sort(key=lambda o: _make_sort_key(o, sort2), reverse=(sort2_dir == "desc"))
    occurrences.sort(key=lambda o: _make_sort_key(o, sort1), reverse=(sort1_dir == "desc"))


def register(app):

    @app.route("/contaschei")
    @login_required
    def contaschei_dashboard():
        uid = current_user.id
        try:
            _default_from, _default_to = get_period_bounds("month", 0)
            date_from = request.args.get("date_from", _default_from)
            date_to   = request.args.get("date_to",   _default_to)
            try:
                datetime.strptime(date_from, "%Y-%m-%d")
                datetime.strptime(date_to,   "%Y-%m-%d")
            except ValueError:
                date_from, date_to = _default_from, _default_to

            tipo_filter = request.args.get("tipo") or None
            cat_filter  = request.args.getlist("category_id")
            search      = request.args.get("search", "").strip()
            sort1       = request.args.get("sort1", "date")
            sort1_dir   = request.args.get("sort1_dir", "desc")
            sort2       = request.args.get("sort2", "") or ""
            sort2_dir   = request.args.get("sort2_dir", "asc")
            if sort1 not in SORT_FIELDS:     sort1     = "date"
            if sort1_dir not in SORT_DIRS:   sort1_dir = "desc"
            if sort2 not in SORT_FIELDS:     sort2     = ""
            if sort2_dir not in SORT_DIRS:   sort2_dir = "asc"

            occurrences = _expand_for_period(uid, date_from, date_to, tipo_filter, cat_filter, search or None)
            _apply_sort(occurrences, sort1, sort1_dir, sort2, sort2_dir)
            tot_income  = round(sum(o["amount"] for o in occurrences if o["tipo"] == "income"), 2)
            tot_expense = round(sum(o["amount"] for o in occurrences if o["tipo"] == "expense"), 2)

            categories = get_all_movement_categories(uid)

            edit_movement = None
            edit_id = request.args.get("edit")
            if edit_id and edit_id.isdigit():
                db = get_db()
                c  = db.cursor()
                c.execute(
                    "SELECT id, category_id, tipo, amount, date, ricorrenza, "
                    "ricorrenza_fine, ricorrenza_occorrenze, note "
                    "FROM movements WHERE id = %s AND user_id = %s",
                    (int(edit_id), uid),
                )
                row = c.fetchone()
                if row:
                    edit_movement = {
                        "id": row[0], "category_id": row[1], "tipo": row[2],
                        "amount": row[3], "date": str(row[4]), "ricorrenza": row[5] or "none",
                        "ricorrenza_fine": str(row[6]) if row[6] else "",
                        "ricorrenza_occorrenze": row[7] or "", "note": row[8] or "",
                    }

            copy_movement = None
            copy_id = request.args.get("copy")
            if not edit_movement and copy_id and copy_id.isdigit():
                db = get_db()
                c  = db.cursor()
                c.execute(
                    "SELECT category_id, tipo, amount, ricorrenza, "
                    "ricorrenza_fine, ricorrenza_occorrenze, note "
                    "FROM movements WHERE id = %s AND user_id = %s",
                    (int(copy_id), uid),
                )
                row = c.fetchone()
                if row:
                    # Stessi dettagli del movimento originale, ma data odierna: l'utente
                    # può modificare tutto prima di salvare come nuovo movimento.
                    copy_movement = {
                        "category_id": row[0], "tipo": row[1], "amount": row[2],
                        "date": date.today().isoformat(), "ricorrenza": row[3] or "none",
                        "ricorrenza_fine": str(row[4]) if row[4] else "",
                        "ricorrenza_occorrenze": row[5] or "", "note": row[6] or "",
                    }

            sort_is_default = (sort1 == "date" and sort1_dir == "desc" and not sort2)
            return render_template_string(
                TEMPLATE_CONTASCHEI,
                occurrences=occurrences,
                categories=categories,
                tot_income=tot_income,
                tot_expense=tot_expense,
                net=round(tot_income - tot_expense, 2),
                date_from=date_from,
                date_to=date_to,
                tipo_filter=tipo_filter or "",
                cat_filter=[str(x) for x in cat_filter],
                search=search,
                sort1=sort1, sort1_dir=sort1_dir,
                sort2=sort2, sort2_dir=sort2_dir,
                sort_is_default=sort_is_default,
                edit_movement=edit_movement,
                copy_movement=copy_movement,
                today=date.today().isoformat(),
            )
        except Exception as e:
            current_app.logger.exception("Errore in /contaschei: %s", e)
            return "Errore nel caricamento Contaschei", 500

    @app.route("/contaschei/add", methods=["POST"])
    @login_required
    def add_movement():
        uid = current_user.id
        tipo   = request.form.get("tipo")
        cat_id = request.form.get("category_id") or None
        amount = request.form.get("amount")
        mdate  = request.form.get("date") or date.today().isoformat()
        ric          = request.form.get("ricorrenza") or "none"
        ric_fine     = request.form.get("ricorrenza_fine") or None
        ric_occ      = request.form.get("ricorrenza_occorrenze") or None
        note         = request.form.get("note") or None

        if ric_occ:
            ric_occ = int(ric_occ) if str(ric_occ).isdigit() else None

        if tipo not in MOVEMENT_TYPES:
            return "Tipo movimento non valido", 400
        try:
            amount = round(float(amount), 2)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return "Importo non valido", 400
        try:
            datetime.strptime(mdate, "%Y-%m-%d")
        except ValueError:
            return "Formato data non valido", 400

        try:
            db = get_db()
            c  = db.cursor()
            if cat_id:
                c.execute(
                    "SELECT type FROM movement_categories WHERE id = %s AND user_id = %s",
                    (cat_id, uid),
                )
                cat_row = c.fetchone()
                if not cat_row or cat_row[0] != tipo:
                    cat_id = None

            c.execute("""
                INSERT INTO movements
                    (user_id, category_id, tipo, amount, date, ricorrenza,
                     ricorrenza_fine, ricorrenza_occorrenze, note, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (uid, cat_id, tipo, amount, mdate, ric, ric_fine, ric_occ, note,
                  date.today().isoformat()))
            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /contaschei/add: %s", e)
            return "Errore nel salvataggio", 500

        _df, _dt = get_period_bounds("month", 0)
        df = request.form.get("date_from", _df)
        dt = request.form.get("date_to",   _dt)
        try:
            datetime.strptime(df, "%Y-%m-%d")
            datetime.strptime(dt, "%Y-%m-%d")
        except ValueError:
            df, dt = _df, _dt
        tf  = request.form.get("tipo_filter") or None
        cf  = request.form.getlist("cat_filter")
        sr  = request.form.get("search") or None
        s1  = request.form.get("sort1", "date")
        s1d = request.form.get("sort1_dir", "desc")
        s2  = request.form.get("sort2", "") or ""
        s2d = request.form.get("sort2_dir", "asc")
        return redirect(url_for("contaschei_dashboard", date_from=df, date_to=dt,
                                tipo=tf, category_id=cf, search=sr,
                                sort1=s1, sort1_dir=s1d, sort2=s2, sort2_dir=s2d))

    @app.route("/contaschei/edit/<int:mid>", methods=["POST"])
    @login_required
    def edit_movement(mid):
        uid = current_user.id
        tipo   = request.form.get("tipo")
        cat_id = request.form.get("category_id") or None
        amount = request.form.get("amount")
        mdate  = request.form.get("date") or date.today().isoformat()
        ric          = request.form.get("ricorrenza") or "none"
        ric_fine     = request.form.get("ricorrenza_fine") or None
        ric_occ      = request.form.get("ricorrenza_occorrenze") or None
        note         = request.form.get("note") or None

        if ric_occ:
            ric_occ = int(ric_occ) if str(ric_occ).isdigit() else None

        if tipo not in MOVEMENT_TYPES:
            return "Tipo movimento non valido", 400
        try:
            amount = round(float(amount), 2)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return "Importo non valido", 400
        try:
            datetime.strptime(mdate, "%Y-%m-%d")
        except ValueError:
            return "Formato data non valido", 400

        try:
            db = get_db()
            c  = db.cursor()
            if cat_id:
                c.execute(
                    "SELECT type FROM movement_categories WHERE id = %s AND user_id = %s",
                    (cat_id, uid),
                )
                cat_row = c.fetchone()
                if not cat_row or cat_row[0] != tipo:
                    cat_id = None

            c.execute("""
                UPDATE movements
                SET category_id = %s, tipo = %s, amount = %s, date = %s, ricorrenza = %s,
                    ricorrenza_fine = %s, ricorrenza_occorrenze = %s, note = %s
                WHERE id = %s AND user_id = %s
            """, (cat_id, tipo, amount, mdate, ric, ric_fine, ric_occ, note, mid, uid))
            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /contaschei/edit/%s: %s", mid, e)
            return "Errore nel salvataggio", 500

        _df, _dt = get_period_bounds("month", 0)
        df = request.form.get("date_from", _df)
        dt = request.form.get("date_to",   _dt)
        try:
            datetime.strptime(df, "%Y-%m-%d")
            datetime.strptime(dt, "%Y-%m-%d")
        except ValueError:
            df, dt = _df, _dt
        tf  = request.form.get("tipo_filter") or None
        cf  = request.form.getlist("cat_filter")
        sr  = request.form.get("search") or None
        s1  = request.form.get("sort1", "date")
        s1d = request.form.get("sort1_dir", "desc")
        s2  = request.form.get("sort2", "") or ""
        s2d = request.form.get("sort2_dir", "asc")
        return redirect(url_for("contaschei_dashboard", date_from=df, date_to=dt,
                                tipo=tf, category_id=cf, search=sr,
                                sort1=s1, sort1_dir=s1d, sort2=s2, sort2_dir=s2d))

    @app.route("/contaschei/delete/<int:mid>", methods=["POST"])
    @login_required
    def delete_movement(mid):
        try:
            db = get_db()
            c  = db.cursor()
            c.execute(
                "DELETE FROM movements WHERE id = %s AND user_id = %s",
                (mid, current_user.id),
            )
            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /contaschei/delete/%s: %s", mid, e)
        _df, _dt = get_period_bounds("month", 0)
        df = request.form.get("date_from", _df)
        dt = request.form.get("date_to",   _dt)
        try:
            datetime.strptime(df, "%Y-%m-%d")
            datetime.strptime(dt, "%Y-%m-%d")
        except ValueError:
            df, dt = _df, _dt
        tf  = request.form.get("tipo_filter") or None
        cf  = request.form.getlist("cat_filter")
        sr  = request.form.get("search") or None
        s1  = request.form.get("sort1", "date")
        s1d = request.form.get("sort1_dir", "desc")
        s2  = request.form.get("sort2", "") or ""
        s2d = request.form.get("sort2_dir", "asc")
        return redirect(url_for("contaschei_dashboard", date_from=df, date_to=dt,
                                tipo=tf, category_id=cf, search=sr,
                                sort1=s1, sort1_dir=s1d, sort2=s2, sort2_dir=s2d))

    @app.route("/contaschei/exception/<int:mid>", methods=["POST"])
    @login_required
    def set_movement_exception(mid):
        uid             = current_user.id
        occurrence_date = request.form.get("occurrence_date")
        action          = request.form.get("action")
        override_amount = request.form.get("override_amount") or None
        override_note   = request.form.get("override_note") or None

        if action not in ("skip", "override") or not occurrence_date:
            return "Dati eccezione non validi", 400
        if action == "override" and override_amount:
            try:
                override_amount = round(float(override_amount), 2)
            except (TypeError, ValueError):
                return "Importo non valido", 400

        try:
            db = get_db()
            c  = db.cursor()
            c.execute(
                "SELECT id FROM movements WHERE id = %s AND user_id = %s", (mid, uid)
            )
            if not c.fetchone():
                return "Movimento non trovato", 404

            c.execute(
                "DELETE FROM movement_exceptions WHERE movement_id = %s AND occurrence_date = %s",
                (mid, occurrence_date),
            )
            c.execute("""
                INSERT INTO movement_exceptions
                    (movement_id, occurrence_date, action, override_amount, override_note)
                VALUES (%s, %s, %s, %s, %s)
            """, (mid, occurrence_date, action, override_amount, override_note))
            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /contaschei/exception/%s: %s", mid, e)
            return "Errore nel salvataggio", 500

        return redirect(request.referrer or url_for("contaschei_dashboard"))

    @app.route("/contaschei/exception/<int:mid>/delete", methods=["POST"])
    @login_required
    def delete_movement_exception(mid):
        uid             = current_user.id
        occurrence_date = request.form.get("occurrence_date")
        try:
            db = get_db()
            c  = db.cursor()
            c.execute("""
                DELETE FROM movement_exceptions
                WHERE movement_id = %s AND occurrence_date = %s
                  AND movement_id IN (SELECT id FROM movements WHERE user_id = %s)
            """, (mid, occurrence_date, uid))
            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /contaschei/exception/%s/delete: %s", mid, e)
        return redirect(request.referrer or url_for("contaschei_dashboard"))

    @app.route("/contaschei/categories")
    @login_required
    def contaschei_categories():
        cats = get_all_movement_categories(current_user.id)
        return render_template_string(TEMPLATE_CONTASCHEI_CATEGORIES, categories=cats)

    @app.route("/contaschei/categories/add", methods=["POST"])
    @login_required
    def add_movement_category():
        name  = request.form.get("name")
        type_ = request.form.get("type")
        color = request.form.get("color") or "#007bff"
        if name and type_ in MOVEMENT_TYPES:
            try:
                db = get_db()
                c  = db.cursor()
                c.execute(
                    "INSERT INTO movement_categories (user_id, name, type, color) VALUES (%s, %s, %s, %s)",
                    (current_user.id, name, type_, color),
                )
                db.commit()
            except Exception as e:
                current_app.logger.exception("Errore in /contaschei/categories/add: %s", e)
        return redirect(url_for("contaschei_categories"))

    @app.route("/contaschei/categories/update/<int:cid>", methods=["POST"])
    @login_required
    def update_movement_category(cid):
        uid   = current_user.id
        name  = request.form.get("name")
        type_ = request.form.get("type")
        color = request.form.get("color") or "#007bff"
        if not name or type_ not in MOVEMENT_TYPES:
            return redirect(url_for("contaschei_categories"))
        try:
            db = get_db()
            c  = db.cursor()
            c.execute(
                "SELECT COUNT(*) FROM movements WHERE category_id = %s AND user_id = %s",
                (cid, uid),
            )
            has_movements = c.fetchone()[0] > 0
            if has_movements:
                c.execute(
                    "SELECT type FROM movement_categories WHERE id = %s AND user_id = %s",
                    (cid, uid),
                )
                row = c.fetchone()
                if row:
                    type_ = row[0]  # blocca il cambio tipo se la tipologia ha già movimenti

            c.execute(
                "UPDATE movement_categories SET name=%s, type=%s, color=%s WHERE id=%s AND user_id=%s",
                (name, type_, color, cid, uid),
            )
            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /contaschei/categories/update: %s", e)
        return redirect(url_for("contaschei_categories"))

    @app.route("/contaschei/categories/delete/<int:cid>", methods=["POST"])
    @login_required
    def delete_movement_category(cid):
        uid = current_user.id
        try:
            db = get_db()
            c  = db.cursor()
            c.execute(
                "UPDATE movements SET category_id = NULL WHERE category_id = %s AND user_id = %s",
                (cid, uid),
            )
            c.execute(
                "DELETE FROM movement_categories WHERE id = %s AND user_id = %s",
                (cid, uid),
            )
            db.commit()
        except Exception as e:
            current_app.logger.exception("Errore in /contaschei/categories/delete: %s", e)
        return redirect(url_for("contaschei_categories"))

    @app.route("/contaschei/bilancio")
    @login_required
    def contaschei_bilancio():
        uid = current_user.id
        try:
            period_type   = request.args.get("period_type", "month")
            if period_type not in PERIOD_TYPES:
                period_type = "month"
            period_offset = request.args.get("period_offset", "0")
            period_offset = int(period_offset) if period_offset.lstrip("-").isdigit() else 0
            tipo_filter   = request.args.get("tipo") or None
            cat_filter    = request.args.getlist("category_id")

            date_from, date_to = get_period_bounds(period_type, period_offset)

            occurrences = _expand_for_period(uid, date_from, date_to, tipo_filter, cat_filter)
            tot_income  = round(sum(o["amount"] for o in occurrences if o["tipo"] == "income"), 2)
            tot_expense = round(sum(o["amount"] for o in occurrences if o["tipo"] == "expense"), 2)

            by_category = {}
            for o in occurrences:
                key = (o["categoria"], o["color"], o["tipo"])  # None → "Nessuna tipologia" tradotto nel template
                by_category[key] = by_category.get(key, 0) + o["amount"]
            by_category_list = sorted(
                [(name, color, tipo, round(tot, 2)) for (name, color, tipo), tot in by_category.items()],
                key=lambda r: r[3], reverse=True,
            )

            categories = get_all_movement_categories(uid)

            return render_template_string(
                TEMPLATE_CONTASCHEI_BILANCIO,
                occurrences=occurrences,
                categories=categories,
                period_type=period_type,
                period_offset=period_offset,
                period_types=PERIOD_TYPES,
                tipo_filter=tipo_filter or "",
                cat_filter=[str(x) for x in cat_filter],
                date_from=date_from,
                date_to=date_to,
                tot_income=tot_income,
                tot_expense=tot_expense,
                net=round(tot_income - tot_expense, 2),
                by_category=by_category_list,
            )
        except Exception as e:
            current_app.logger.exception("Errore in /contaschei/bilancio: %s", e)
            return "Errore nel caricamento bilancio", 500
