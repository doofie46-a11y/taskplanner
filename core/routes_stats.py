"""Route statistiche."""
from datetime import date, datetime, timedelta

from flask import current_app, render_template_string, request
from flask_login import current_user, login_required

from core.db import get_db
from core.logic import get_all_categories
from core.templates import TEMPLATE_STATS
from core.utils import format_time


def register(app):

    @app.route("/stats")
    @login_required
    def stats():
        uid = current_user.id
        try:
            db = get_db()
            c  = db.cursor()

            date_from   = request.args.get("date_from") or ""
            date_to     = request.args.get("date_to") or ""
            prio_filter = request.args.getlist("priorita")
            cat_filter  = request.args.getlist("category_id")
            view_mode   = request.args.get("view_mode", "totale")

            if not date_from:
                date_from = (date.today() - timedelta(days=30)).isoformat()
            if not date_to:
                date_to = date.today().isoformat()

            categories = get_all_categories()

            def build_conditions(alias_task="t", alias_comp="tc"):
                conds  = [f"{alias_task}.user_id = %s", f"{alias_comp}.data_completata BETWEEN %s AND %s"]
                params = [uid, date_from, date_to]
                if prio_filter:
                    ph = ",".join(["%s"] * len(prio_filter))
                    conds.append(f"{alias_task}.priorita IN ({ph})")
                    params.extend(prio_filter)
                if cat_filter:
                    ph = ",".join(["%s"] * len(cat_filter))
                    conds.append(f"{alias_task}.category_id IN ({ph})")
                    params.extend(cat_filter)
                return " AND ".join(conds), params

            # --- Task risolti nel periodo ---
            cond, params = build_conditions()
            c.execute(f"""
                SELECT COUNT(*), SUM(tc.tempo_impiegato)
                FROM task_completed tc
                JOIN tasks t ON t.id = tc.task_id
                WHERE {cond}
            """, params)
            row = c.fetchone()
            tot_risolti = row[0] or 0
            tot_tempo   = row[1] or 0

            # --- Task creati nel periodo ---
            open_conds  = ["t.user_id = %s", "t.created_at BETWEEN %s AND %s", "t.deleted_at IS NULL"]
            open_params = [uid, date_from, date_to]
            if prio_filter:
                ph = ",".join(["%s"] * len(prio_filter))
                open_conds.append(f"t.priorita IN ({ph})")
                open_params.extend(prio_filter)
            if cat_filter:
                ph = ",".join(["%s"] * len(cat_filter))
                open_conds.append(f"t.category_id IN ({ph})")
                open_params.extend(cat_filter)
            c.execute(f"""
                SELECT COUNT(*) FROM tasks t WHERE {' AND '.join(open_conds)}
            """, open_params)
            tot_creati = c.fetchone()[0] or 0

            # --- Rollover nel periodo ---
            rollover_conds  = ["t.user_id = %s", "rh.to_date BETWEEN %s AND %s"]
            rollover_params = [uid, date_from, date_to]
            if prio_filter:
                ph = ",".join(["%s"] * len(prio_filter))
                rollover_conds.append(f"t.priorita IN ({ph})")
                rollover_params.extend(prio_filter)
            if cat_filter:
                ph = ",".join(["%s"] * len(cat_filter))
                rollover_conds.append(f"t.category_id IN ({ph})")
                rollover_params.extend(cat_filter)
            c.execute(f"""
                SELECT COUNT(*) FROM rollover_history rh
                JOIN tasks t ON t.id = rh.task_id
                WHERE {' AND '.join(rollover_conds)}
            """, rollover_params)
            tot_rollover = c.fetchone()[0] or 0

            # --- Dati giornalieri ---
            daily_data = []
            if view_mode == "giornaliero":
                today_iso = date.today().isoformat()

                cond_g, params_g = build_conditions()
                c.execute(f"""
                    SELECT tc.data_completata, COUNT(*) as risolti, SUM(tc.tempo_impiegato) as tempo
                    FROM task_completed tc JOIN tasks t ON t.id = tc.task_id
                    WHERE {cond_g} GROUP BY tc.data_completata ORDER BY tc.data_completata ASC
                """, params_g)
                risolti_per_giorno = {str(r[0]): (r[1], r[2]) for r in c.fetchall()}

                roll_g_conds  = ["t.user_id = %s", "rh.to_date BETWEEN %s AND %s"]
                roll_g_params = [uid, date_from, date_to]
                if prio_filter:
                    ph = ",".join(["%s"] * len(prio_filter))
                    roll_g_conds.append(f"t.priorita IN ({ph})")
                    roll_g_params.extend(prio_filter)
                if cat_filter:
                    ph = ",".join(["%s"] * len(cat_filter))
                    roll_g_conds.append(f"t.category_id IN ({ph})")
                    roll_g_params.extend(cat_filter)
                c.execute(f"""
                    SELECT rh.to_date, COUNT(*) as cnt FROM rollover_history rh
                    JOIN tasks t ON t.id = rh.task_id
                    WHERE {' AND '.join(roll_g_conds)}
                    GROUP BY rh.to_date ORDER BY rh.to_date ASC
                """, roll_g_params)
                rollover_per_giorno = {str(r[0]): r[1] for r in c.fetchall()}

                created_g_conds  = ["t.user_id = %s", "t.created_at BETWEEN %s AND %s"]
                created_g_params = [uid, date_from, date_to]
                if prio_filter:
                    ph = ",".join(["%s"] * len(prio_filter))
                    created_g_conds.append(f"t.priorita IN ({ph})")
                    created_g_params.extend(prio_filter)
                if cat_filter:
                    ph = ",".join(["%s"] * len(cat_filter))
                    created_g_conds.append(f"t.category_id IN ({ph})")
                    created_g_params.extend(cat_filter)
                c.execute(f"""
                    SELECT t.created_at, COUNT(*) as cnt FROM tasks t
                    WHERE {' AND '.join(created_g_conds)}
                    GROUP BY t.created_at ORDER BY t.created_at ASC
                """, created_g_params)
                creati_per_giorno = {str(r[0]): r[1] for r in c.fetchall()}

                future_conds  = ["t.user_id = %s"]
                future_params = [uid]
                if prio_filter:
                    ph = ",".join(["%s"] * len(prio_filter))
                    future_conds.append(f"t.priorita IN ({ph})")
                    future_params.extend(prio_filter)
                if cat_filter:
                    ph = ",".join(["%s"] * len(cat_filter))
                    future_conds.append(f"t.category_id IN ({ph})")
                    future_params.extend(cat_filter)
                c.execute(f"""
                    SELECT t.id, t.ricorrenza, t.data_prevista FROM tasks t
                    WHERE {' AND '.join(future_conds)}
                      AND (
                          t.ricorrenza != 'none'
                          OR NOT EXISTS (
                              SELECT 1 FROM task_completed tc
                              WHERE tc.task_id = t.id AND tc.data_completata = t.data_prevista
                          )
                      )
                """, future_params)
                all_active_tasks = c.fetchall()

                c.execute(
                    "SELECT tc.task_id, tc.data_completata FROM task_completed tc "
                    "JOIN tasks t ON t.id = tc.task_id WHERE t.user_id = %s", (uid,)
                )
                completed_set = set((str(r[0]), str(r[1])) for r in c.fetchall())

                scadenza_per_giorno = {}
                try:
                    d_from_dt  = datetime.strptime(date_from, "%Y-%m-%d").date()
                    d_to_dt    = datetime.strptime(date_to,   "%Y-%m-%d").date()
                    d_today_dt = datetime.strptime(today_iso, "%Y-%m-%d").date()
                    cur = max(d_from_dt, d_today_dt)
                    while cur <= d_to_dt:
                        cur_iso = cur.isoformat()
                        cnt = 0
                        for _tid, ric, dp_str in all_active_tasks:
                            try:
                                dp = datetime.strptime(str(dp_str), "%Y-%m-%d").date()
                            except (ValueError, TypeError):
                                continue
                            cade = False
                            if   ric == "none"    and dp == cur: cade = True
                            elif ric == "daily"   and dp <= cur: cade = True
                            elif ric == "every2days"   and dp <= cur and (cur - dp).days % 2  == 0: cade = True
                            elif ric == "weekly"       and dp <= cur and (cur - dp).days % 7  == 0: cade = True
                            elif ric == "every2weeks"  and dp <= cur and (cur - dp).days % 14 == 0: cade = True
                            elif ric == "monthly"      and dp <= cur and dp.day == cur.day:          cade = True
                            elif ric == "monthly_first_monday" and dp <= cur:
                                first_day = cur.replace(day=1)
                                days_to_monday = (7 - first_day.weekday()) % 7 if first_day.weekday() != 0 else 0
                                if cur == first_day + timedelta(days=days_to_monday): cade = True
                            elif ric == "monthly_last_friday" and dp <= cur:
                                last_day = (cur.replace(day=31) if cur.month == 12
                                            else cur.replace(month=cur.month + 1, day=1) - timedelta(days=1))
                                days_back = (last_day.weekday() - 4) % 7
                                if cur == last_day - timedelta(days=days_back): cade = True
                            if cade and (str(_tid), cur_iso) not in completed_set:
                                cnt += 1
                        if cnt > 0:
                            scadenza_per_giorno[cur_iso] = cnt
                        cur += timedelta(days=1)
                except Exception as e:
                    current_app.logger.warning("Errore calcolo scadenze giornaliere: %s", e)

                all_dates = sorted(set(
                    list(risolti_per_giorno.keys()) +
                    list(rollover_per_giorno.keys()) +
                    list(creati_per_giorno.keys()) +
                    list(scadenza_per_giorno.keys())
                ))
                for d in all_dates:
                    risolti_d, tempo_d = risolti_per_giorno.get(d, (0, 0))
                    daily_data.append((
                        d,
                        risolti_d,
                        tempo_d or 0,
                        rollover_per_giorno.get(d, 0),
                        creati_per_giorno.get(d, 0),
                        scadenza_per_giorno.get(d, 0),
                        d >= today_iso,  # show_scadenza
                        d == today_iso,  # is_today
                    ))

            # --- Ripartizioni ---
            cond_p, params_p = build_conditions()
            c.execute(f"""
                SELECT t.priorita, COUNT(*) FROM task_completed tc
                JOIN tasks t ON t.id = tc.task_id WHERE {cond_p} GROUP BY t.priorita
            """, params_p)
            by_prio = c.fetchall()

            cond_c, params_c = build_conditions()
            c.execute(f"""
                SELECT COALESCE(cat.name, 'Nessuna'), cat.color, COUNT(*)
                FROM task_completed tc JOIN tasks t ON t.id = tc.task_id
                LEFT JOIN categories cat ON cat.id = t.category_id
                WHERE {cond_c} GROUP BY t.category_id
            """, params_c)
            by_cat = c.fetchall()

            creati_cat_conds  = ["t.user_id = %s", "t.created_at BETWEEN %s AND %s"]
            creati_cat_params = [uid, date_from, date_to]
            if prio_filter:
                ph = ",".join(["%s"] * len(prio_filter))
                creati_cat_conds.append(f"t.priorita IN ({ph})")
                creati_cat_params.extend(prio_filter)
            if cat_filter:
                ph = ",".join(["%s"] * len(cat_filter))
                creati_cat_conds.append(f"t.category_id IN ({ph})")
                creati_cat_params.extend(cat_filter)
            c.execute(f"""
                SELECT COALESCE(cat.name,'Nessuna'), cat.color, COUNT(*) FROM tasks t
                LEFT JOIN categories cat ON cat.id = t.category_id
                WHERE {' AND '.join(creati_cat_conds)} GROUP BY t.category_id
            """, creati_cat_params)
            creati_by_cat = c.fetchall()

            creati_prio_conds  = ["t.user_id = %s", "t.created_at BETWEEN %s AND %s"]
            creati_prio_params = [uid, date_from, date_to]
            if prio_filter:
                ph = ",".join(["%s"] * len(prio_filter))
                creati_prio_conds.append(f"t.priorita IN ({ph})")
                creati_prio_params.extend(prio_filter)
            if cat_filter:
                ph = ",".join(["%s"] * len(cat_filter))
                creati_prio_conds.append(f"t.category_id IN ({ph})")
                creati_prio_params.extend(cat_filter)
            c.execute(f"""
                SELECT t.priorita, COUNT(*) FROM tasks t
                WHERE {' AND '.join(creati_prio_conds)} GROUP BY t.priorita
            """, creati_prio_params)
            creati_by_prio = c.fetchall()

            roll_cat_conds  = ["t.user_id = %s", "rh.to_date BETWEEN %s AND %s"]
            roll_cat_params = [uid, date_from, date_to]
            if prio_filter:
                ph = ",".join(["%s"] * len(prio_filter))
                roll_cat_conds.append(f"t.priorita IN ({ph})")
                roll_cat_params.extend(prio_filter)
            if cat_filter:
                ph = ",".join(["%s"] * len(cat_filter))
                roll_cat_conds.append(f"t.category_id IN ({ph})")
                roll_cat_params.extend(cat_filter)
            c.execute(f"""
                SELECT COALESCE(cat.name,'Nessuna'), cat.color, COUNT(*)
                FROM rollover_history rh JOIN tasks t ON t.id = rh.task_id
                LEFT JOIN categories cat ON cat.id = t.category_id
                WHERE {' AND '.join(roll_cat_conds)} GROUP BY t.category_id
            """, roll_cat_params)
            rollover_by_cat = c.fetchall()

            roll_prio_conds  = ["t.user_id = %s", "rh.to_date BETWEEN %s AND %s"]
            roll_prio_params = [uid, date_from, date_to]
            if prio_filter:
                ph = ",".join(["%s"] * len(prio_filter))
                roll_prio_conds.append(f"t.priorita IN ({ph})")
                roll_prio_params.extend(prio_filter)
            if cat_filter:
                ph = ",".join(["%s"] * len(cat_filter))
                roll_prio_conds.append(f"t.category_id IN ({ph})")
                roll_prio_params.extend(cat_filter)
            c.execute(f"""
                SELECT t.priorita, COUNT(*) FROM rollover_history rh
                JOIN tasks t ON t.id = rh.task_id
                WHERE {' AND '.join(roll_prio_conds)} GROUP BY t.priorita
            """, roll_prio_params)
            rollover_by_prio = c.fetchall()

            tempo_cat_cond, tempo_cat_params = build_conditions()
            c.execute(f"""
                SELECT COALESCE(cat.name,'Nessuna'), cat.color, SUM(tc.tempo_impiegato)
                FROM task_completed tc JOIN tasks t ON t.id = tc.task_id
                LEFT JOIN categories cat ON cat.id = t.category_id
                WHERE {tempo_cat_cond} AND tc.tempo_impiegato IS NOT NULL
                GROUP BY t.category_id
            """, tempo_cat_params)
            tempo_by_cat = [(r[0], r[1], r[2] or 0) for r in c.fetchall() if r[2]]

            tempo_prio_cond, tempo_prio_params = build_conditions()
            c.execute(f"""
                SELECT t.priorita, SUM(tc.tempo_impiegato)
                FROM task_completed tc JOIN tasks t ON t.id = tc.task_id
                WHERE {tempo_prio_cond} AND tc.tempo_impiegato IS NOT NULL
                GROUP BY t.priorita
            """, tempo_prio_params)
            tempo_by_prio = [(r[0], r[1] or 0) for r in c.fetchall() if r[1]]

            return render_template_string(
                TEMPLATE_STATS,
                categories=categories,
                date_from=date_from,
                date_to=date_to,
                prio_filter=prio_filter,
                cat_filter=[str(x) for x in cat_filter],
                view_mode=view_mode,
                tot_risolti=tot_risolti,
                tot_creati=tot_creati,
                tot_rollover=tot_rollover,
                tot_tempo=tot_tempo,
                format_time=format_time,
                daily_data=daily_data,
                by_prio=by_prio,
                by_cat=by_cat,
                creati_by_cat=creati_by_cat,
                creati_by_prio=creati_by_prio,
                rollover_by_cat=rollover_by_cat,
                rollover_by_prio=rollover_by_prio,
                tempo_by_cat=tempo_by_cat,
                tempo_by_prio=tempo_by_prio,
            )
        except Exception as e:
            current_app.logger.exception("Errore in /stats: %s", e)
            return "Errore nel caricamento statistiche", 500
