"""Route export: scarica task in CSV/JSON/TXT/MD."""
import csv
import io
import json as json_module
from datetime import date, datetime, timedelta

from flask import Response, current_app, render_template_string, request
from flask_login import current_user, login_required

from core.db import get_db
from core.logic import _expand_recurring, get_all_categories
from core.templates import TEMPLATE_EXPORT


def register(app):

    @app.route("/export", methods=["GET", "POST"])
    @login_required
    def export_tasks():
        if request.method == "GET":
            categories = get_all_categories()
            return render_template_string(
                TEMPLATE_EXPORT,
                categories=categories,
                app_version=current_app.config['APP_VERSION'],
                app_codename=current_app.config['APP_CODENAME'],
                today=date.today().isoformat(),
            )

        # POST: esegui export
        fmt           = request.form.get("format", "csv")
        date_from     = request.form.get("date_from") or ""
        date_to       = request.form.get("date_to")   or ""
        prio_filter   = request.form.getlist("priorita")
        cat_filter    = request.form.getlist("category_id")
        stato_filter  = request.form.getlist("stato")
        escludi_ric   = request.form.get("escludi_ricorrenti") == "1"
        espandi_ric   = request.form.get("espandi_ricorrenti") == "1"
        fields        = request.form.getlist("fields")
        solo_allegati = request.form.get("solo_allegati") == "1"

        if not date_from:
            date_from = (date.today() - timedelta(days=30)).isoformat()
        if not date_to:
            date_to = date.today().isoformat()

        try:
            db = get_db()
            c  = db.cursor()

            conds  = ["t.user_id = %s", "t.deleted_at IS NULL"]
            params = [current_user.id]

            if prio_filter:
                placeholders = ",".join(["%s"] * len(prio_filter))
                conds.append(f"t.priorita IN ({placeholders})")
                params.extend(prio_filter)

            if cat_filter:
                placeholders = ",".join(["%s"] * len(cat_filter))
                conds.append(f"t.category_id IN ({placeholders})")
                params.extend(cat_filter)

            if escludi_ric:
                conds.append("t.ricorrenza = 'none'")

            c.execute(f"""
                SELECT t.id, t.titolo, t.data_prevista, t.ora_prevista,
                       t.ricorrenza, t.priorita,
                       COALESCE(cat.name, '') as cat_name,
                       COALESCE(t.url, '') as url,
                       COALESCE(t.created_at, '') as created_at,
                       COALESCE(t.ricorrenza_fine, '') as ric_fine,
                       COALESCE(t.ricorrenza_occorrenze, 0) as ric_occ,
                       CASE WHEN tc.task_id IS NOT NULL THEN 'completato' ELSE 'aperto' END as stato
                FROM tasks t
                LEFT JOIN categories cat ON cat.id = t.category_id
                LEFT JOIN task_completed tc ON tc.task_id = t.id
                  AND tc.data_completata = t.data_prevista
                WHERE {' AND '.join(conds)}
            """, params)
            raw_rows = c.fetchall()

            c.execute("""
                SELECT a.task_id, a.original_name FROM attachments a
                JOIN tasks t ON t.id = a.task_id
                WHERE t.user_id = %s AND t.deleted_at IS NULL ORDER BY a.task_id, a.id
            """, (current_user.id,))
            _allegati_map = {}
            for _att_tid, _att_name in c.fetchall():
                _allegati_map.setdefault(_att_tid, []).append(_att_name)

            if espandi_ric:
                rows = _expand_recurring(raw_rows, date_from, date_to)
                for r in rows:
                    nomi = _allegati_map.get(r.get("id"), [])
                    r["allegati"] = "; ".join(nomi)
            else:
                rows = []
                for row in raw_rows:
                    (tid, titolo, data_prev, ora, ric, prio, cat_name, url,
                     created_at, ric_fine, ric_occ, stato) = row
                    try:
                        dp = datetime.strptime(str(data_prev), "%Y-%m-%d").date()
                        df = datetime.strptime(date_from, "%Y-%m-%d").date()
                        dt = datetime.strptime(date_to,   "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        continue
                    if df <= dp <= dt:
                        nomi = _allegati_map.get(tid, [])
                        rows.append({
                            "id": tid, "titolo": titolo, "data_prevista": data_prev or "",
                            "ora_prevista": ora or "", "ricorrenza": ric or "none",
                            "priorita": prio or "", "categoria": cat_name or "",
                            "url": url or "", "created_at": created_at or "",
                            "stato": stato or "aperto", "occurrence_date": str(dp),
                            "allegati": "; ".join(nomi),
                        })

            if stato_filter and "tutti" not in stato_filter:
                rows = [r for r in rows if r["stato"] in stato_filter]

            if solo_allegati:
                rows = [r for r in rows if r.get("allegati")]

            ALL_FIELDS = ["occurrence_date", "id", "titolo", "ora_prevista", "ricorrenza",
                          "priorita", "categoria", "stato", "url", "created_at", "data_prevista", "allegati"]
            if not fields:
                fields = ALL_FIELDS

            LABELS = {
                "occurrence_date": "Data",
                "id": "ID",
                "titolo": "Titolo",
                "ora_prevista": "Orario",
                "ricorrenza": "Ricorrenza",
                "priorita": "Priorità",
                "categoria": "Categoria",
                "stato": "Stato",
                "url": "URL",
                "created_at": "Creato il",
                "data_prevista": "Data prevista originale",
                "allegati": "Allegati",
            }

            if fmt == "csv":
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
                writer.writerow({f: LABELS.get(f, f) for f in fields})
                for r in rows:
                    writer.writerow({f: r.get(f, "") for f in fields})
                content  = output.getvalue()
                mimetype = "text/csv"
                filename = f"taskplanner_export_{date_from}_{date_to}.csv"

            elif fmt == "json":
                filtered = [{f: r.get(f, "") for f in fields} for r in rows]
                content  = json_module.dumps(filtered, ensure_ascii=False, indent=2)
                mimetype = "application/json"
                filename = f"taskplanner_export_{date_from}_{date_to}.json"

            elif fmt == "md":
                lines = [
                    "# TaskPlanner Export",
                    f"**Periodo:** {date_from} → {date_to}",
                    f"**Task esportati:** {len(rows)}",
                    "",
                    "| " + " | ".join(LABELS.get(f, f) for f in fields) + " |",
                    "| " + " | ".join("---" for _ in fields) + " |",
                ]
                for r in rows:
                    lines.append("| " + " | ".join(str(r.get(f, "")).replace("|", "\\|") for f in fields) + " |")
                content  = "\n".join(lines)
                mimetype = "text/markdown"
                filename = f"taskplanner_export_{date_from}_{date_to}.md"

            else:  # txt
                lines = [
                    f"TaskPlanner Export — {date_from} → {date_to}",
                    f"Task esportati: {len(rows)}",
                    "=" * 60,
                    "",
                ]
                for r in rows:
                    lines.append("-" * 40)
                    for f in fields:
                        lines.append(f"  {LABELS.get(f, f)}: {r.get(f, '')}")
                content  = "\n".join(lines)
                mimetype = "text/plain"
                filename = f"taskplanner_export_{date_from}_{date_to}.txt"

            return Response(
                content,
                mimetype=mimetype,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        except Exception as e:
            current_app.logger.exception("Errore in /export: %s", e)
            return "Errore nell'esportazione", 500
