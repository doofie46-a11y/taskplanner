"""
Logica di business condivisa.

Nessuna dipendenza da psycopg2, authlib o win32com.
Tutte le funzioni operano nell'app context Flask e usano get_db() per il DB.
"""
import os
from datetime import date, datetime, timedelta

from flask import current_app
from flask_login import current_user

from core.db import get_db
from core.models import PRIO_LEVELS
from core.utils import app_timezone, get_icon_for_filename


# ---------------------------------------------------------------- escalation

def calcola_priorita_effettiva(prio_base, posticipato_da, escalation):
    """
    Calcola la priorità effettiva tenendo conto dell'escalation automatica.
    Restituisce (priorita_effettiva, livelli_scalati, giorni_ritardo).
    Se escalation è None o 0, restituisce (prio_base, 0, 0).
    """
    if not escalation or escalation <= 0 or not posticipato_da:
        return prio_base, 0, 0

    try:
        post_date = datetime.strptime(str(posticipato_da), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return prio_base, 0, 0

    giorni_ritardo = (date.today() - post_date).days
    if giorni_ritardo <= 0:
        return prio_base, 0, 0

    livelli_scalati = giorni_ritardo // escalation
    if livelli_scalati <= 0:
        return prio_base, 0, giorni_ritardo

    base_idx = PRIO_LEVELS.index(prio_base) if prio_base in PRIO_LEVELS else 1
    new_idx   = min(base_idx + livelli_scalati, len(PRIO_LEVELS) - 1)
    return PRIO_LEVELS[new_idx], livelli_scalati, giorni_ritardo


# ---------------------------------------------------------------- categorie

def get_all_categories(user_id=None):
    """Restituisce tutte le categorie dell'utente ordinate per nome."""
    uid = user_id or (current_user.id if current_user.is_authenticated else None)
    db  = get_db()
    c   = db.cursor()
    c.execute(
        "SELECT id, name, color, group_name FROM categories WHERE user_id = %s ORDER BY name ASC",
        (uid,),
    )
    return c.fetchall()


# ---------------------------------------------------------------- tasks

def get_tasks_for_date(selected_date, user_id=None):
    """
    Carica i task per la data indicata, eseguendo il rollover automatico se necessario.

    Restituisce (tasks_to_show, total_time) dove tasks_to_show è una lista di tuple con 22 elementi:
    0=id, 1=titolo, 2=ora, 3=completed, 4=ric, 5=data_orig, 6=tempo, 7=in_scadenza,
    8=posticipato_da, 9=prio_effettiva, 10=allegati, 11=cat_id, 12=cat_name, 13=cat_color,
    14=url, 15=prio_base, 16=livelli_scalati, 17=giorni_ritardo, 18=pinned, 19=note,
    20=card_color, 21=escalation
    """
    uid = user_id or (current_user.id if current_user.is_authenticated else None)
    db  = get_db()
    try:
        c = db.cursor()
        sel_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

        # 1. Rollover dei task scaduti (solo se si visualizza oggi)
        if selected_date == date.today().isoformat():
            oggi = date.today().isoformat()
            c.execute("""
                SELECT id, titolo, ora_prevista, ricorrenza, data_prevista, posticipato_da, priorita
                FROM tasks
                WHERE ricorrenza = 'none' AND data_prevista < %s AND user_id = %s
                  AND deleted_at IS NULL
            """, (oggi, uid))
            vecchi = c.fetchall()

            for tid, tit, ora, ric, d_prev, p_da, prio in vecchi:
                c.execute(
                    "SELECT 1 FROM task_completed WHERE task_id=%s AND data_completata=%s",
                    (tid, d_prev),
                )
                if not c.fetchone():
                    new_posticipato = d_prev if p_da is None else p_da
                    c.execute(
                        "UPDATE tasks SET data_prevista=%s, posticipato_da=%s WHERE id=%s",
                        (oggi, new_posticipato, tid),
                    )
                    c.execute(
                        "INSERT INTO rollover_history (task_id, from_date, to_date) VALUES (%s, %s, %s)",
                        (tid, d_prev, oggi),
                    )
            db.commit()

        # 2. Caricamento task con categorie (LEFT JOIN)
        c.execute("""
            SELECT t.id, t.titolo, t.ora_prevista, t.ricorrenza, t.data_prevista,
                   t.posticipato_da, t.priorita, t.category_id, c.name, c.color, t.url, t.escalation,
                   COALESCE(t.pinned,0), t.note, t.card_color
            FROM tasks t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = %s AND t.deleted_at IS NULL
        """, (uid,))
        raw = c.fetchall()

        tasks_to_show = []
        for t in raw:
            (tid, titolo, ora, ric, data_orig, post_da, prio,
             cat_id, cat_name, cat_color, url, escalation, pinned, note, card_color) = t

            prio_effettiva, livelli_scalati, giorni_ritardo = calcola_priorita_effettiva(
                prio, post_da, escalation
            )

            task_date = datetime.strptime(str(data_orig), "%Y-%m-%d").date()
            show = False

            # Ricorrenza_fine e ricorrenza_occorrenze
            c2 = db.cursor()
            c2.execute(
                "SELECT ricorrenza_fine, ricorrenza_occorrenze FROM tasks WHERE id=%s", (tid,)
            )
            ric_extra = c2.fetchone()
            ric_fine = ric_extra[0] if ric_extra else None
            ric_occ  = ric_extra[1] if ric_extra else None

            # Controlla data fine ricorrenza
            if ric_fine:
                try:
                    if sel_date > datetime.strptime(str(ric_fine), "%Y-%m-%d").date():
                        continue
                except (ValueError, TypeError):
                    pass

            # Logica di visualizzazione per ricorrenza
            if   ric == "none"         and task_date == sel_date: show = True
            elif ric == "daily"        and task_date <= sel_date: show = True
            elif ric == "every2days"   and task_date <= sel_date and (sel_date - task_date).days % 2  == 0: show = True
            elif ric == "weekly"       and task_date <= sel_date and (sel_date - task_date).days % 7  == 0: show = True
            elif ric == "every2weeks"  and task_date <= sel_date and (sel_date - task_date).days % 14 == 0: show = True
            elif ric == "monthly"      and task_date <= sel_date and task_date.day == sel_date.day:    show = True
            elif ric == "monthly_first_monday" and task_date <= sel_date:
                first_day = sel_date.replace(day=1)
                dtm = (7 - first_day.weekday()) % 7 if first_day.weekday() != 0 else 0
                if sel_date == first_day + timedelta(days=dtm):
                    show = True
            elif ric == "monthly_last_friday" and task_date <= sel_date:
                if sel_date.month == 12:
                    last_day = sel_date.replace(day=31)
                else:
                    last_day = sel_date.replace(month=sel_date.month + 1, day=1) - timedelta(days=1)
                days_back = (last_day.weekday() - 4) % 7
                if sel_date == last_day - timedelta(days=days_back):
                    show = True

            # Limite occorrenze per task ricorrenti
            if show and ric != "none" and ric_occ is not None and ric_occ > 0:
                occ_scattate = 0
                cur_check    = task_date
                sel_minus1   = sel_date - timedelta(days=1)
                while cur_check <= sel_minus1:
                    cade_check = False
                    if   ric == "daily": cade_check = True
                    elif ric == "every2days"  and (cur_check - task_date).days % 2  == 0: cade_check = True
                    elif ric == "weekly"      and (cur_check - task_date).days % 7  == 0: cade_check = True
                    elif ric == "every2weeks" and (cur_check - task_date).days % 14 == 0: cade_check = True
                    elif ric == "monthly" and cur_check.day == task_date.day: cade_check = True
                    elif ric == "monthly_first_monday":
                        fd  = cur_check.replace(day=1)
                        dtm = (7 - fd.weekday()) % 7 if fd.weekday() != 0 else 0
                        if cur_check == fd + timedelta(days=dtm): cade_check = True
                    elif ric == "monthly_last_friday":
                        ld = (cur_check.replace(day=31) if cur_check.month == 12
                              else cur_check.replace(month=cur_check.month + 1, day=1) - timedelta(days=1))
                        db_days = (ld.weekday() - 4) % 7
                        if cur_check == ld - timedelta(days=db_days): cade_check = True
                    if cade_check:
                        occ_scattate += 1
                    if occ_scattate >= ric_occ:
                        show = False
                        break
                    if   ric == "daily":       cur_check += timedelta(days=1)
                    elif ric == "every2days":  cur_check += timedelta(days=2)
                    elif ric == "weekly":      cur_check += timedelta(days=7)
                    elif ric == "every2weeks": cur_check += timedelta(days=14)
                    else:                      cur_check += timedelta(days=1)

            if show:
                c.execute(
                    "SELECT tempo_impiegato FROM task_completed WHERE task_id=%s AND data_completata=%s",
                    (tid, selected_date),
                )
                res       = c.fetchone()
                completed = res is not None
                tempo     = res[0] if res else None

                in_scadenza = False
                if ora and not completed:
                    try:
                        h, m = map(int, ora.split(":"))
                        task_time = datetime.strptime(
                            f"{selected_date} {h:02d}:{m:02d}", "%Y-%m-%d %H:%M"
                        )
                        now_it = datetime.now(app_timezone()).replace(tzinfo=None)
                        if now_it >= task_time:
                            in_scadenza = True
                    except Exception:
                        pass

                c.execute("SELECT id, original_name FROM attachments WHERE task_id=%s", (tid,))
                allegati = [
                    {"id": aid, "name": fname, "icon": get_icon_for_filename(fname)}
                    for aid, fname in c.fetchall()
                ]

                tasks_to_show.append((
                    tid, titolo, ora, completed, ric, data_orig, tempo, in_scadenza,
                    post_da, prio_effettiva, allegati, cat_id, cat_name, cat_color,
                    url, prio, livelli_scalati, giorni_ritardo, pinned, note, card_color, escalation,
                ))

        # 3. Ordinamento
        prio_map = {"Urgente": 0, "Alta": 1, "Media": 2, "Bassa": 3}

        def _sort_key(t):
            return (
                t[3],                              # completed (False < True)
                0 if t[18] else 1,                 # pinned first
                0 if t[7]  else 1,                 # in_scadenza first
                prio_map.get(t[9], 2),             # priorità effettiva
                t[2] if t[2] else "23:59",         # ora (senza ora → fondo)
                -t[0],                             # id decrescente
            )

        tasks_to_show.sort(key=_sort_key)

        c.execute("""
            SELECT SUM(tc.tempo_impiegato)
            FROM task_completed tc
            JOIN tasks t ON t.id = tc.task_id
            WHERE tc.data_completata = %s AND t.user_id = %s
        """, (selected_date, uid))
        total_time = c.fetchone()[0] or 0

        return tasks_to_show, total_time

    except Exception as e:
        current_app.logger.exception("Errore get_tasks_for_date: %s", e)
        raise


# ---------------------------------------------------------------- cleanup

_last_cleanup: dict = {}  # uid -> date


def _daily_cleanup(uid):
    """
    Pulizia giornaliera (eseguita una volta al giorno per utente):
    1. Elimina definitivamente i task nel cestino da più di 7 giorni (+ file allegati)
    2. Rimuove gli allegati di task completati da più di 7 giorni
    """
    today = date.today()
    if _last_cleanup.get(uid) == today:
        return
    _last_cleanup[uid] = today

    db = get_db()
    c  = db.cursor()
    try:
        # 1. Task cestino > 7 giorni
        c.execute(f"""
            SELECT id FROM tasks
            WHERE user_id = %s AND deleted_at IS NOT NULL
              AND deleted_at < {db.interval_ago(7)}
        """, (uid,))
        old_trash = [r[0] for r in c.fetchall()]

        for tid in old_trash:
            c.execute("SELECT stored_name FROM attachments WHERE task_id=%s", (tid,))
            for (fname,) in c.fetchall():
                _remove_file(fname)
            c.execute("DELETE FROM task_completed  WHERE task_id=%s", (tid,))
            c.execute("DELETE FROM rollover_history WHERE task_id=%s", (tid,))
            c.execute("DELETE FROM tasks           WHERE id=%s",       (tid,))

        # 2. Allegati di task completati > 7 giorni
        cutoff = (today - timedelta(days=7)).isoformat()
        c.execute("""
            SELECT a.id, a.stored_name
            FROM attachments a
            JOIN task_completed tc ON tc.task_id = a.task_id
            JOIN tasks t           ON t.id        = a.task_id
            WHERE t.user_id = %s
              AND tc.data_completata <= %s
              AND t.deleted_at IS NULL
        """, (uid, cutoff))
        old_attach = c.fetchall()

        for aid, fname in old_attach:
            _remove_file(fname)
            c.execute("DELETE FROM attachments WHERE id=%s", (aid,))

        db.commit()
        current_app.logger.info(
            "Cleanup uid=%s: %d task cestino eliminati, %d allegati rimossi",
            uid, len(old_trash), len(old_attach),
        )
    except Exception:
        current_app.logger.exception("Errore in _daily_cleanup")
        try:
            db.rollback()
        except Exception:
            pass


def _remove_file(fname: str):
    """Rimuove un file allegato dal disco, senza sollevare eccezioni."""
    try:
        from flask import current_app
        fpath = os.path.join(current_app.config['UPLOAD_FOLDER'], fname)
        if os.path.exists(fpath):
            os.remove(fpath)
    except Exception:
        pass


def _get_cestino_count(uid) -> int:
    """Restituisce il numero di task nel cestino per l'utente."""
    try:
        c = get_db().cursor()
        c.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=%s AND deleted_at IS NOT NULL",
            (uid,),
        )
        return c.fetchone()[0]
    except Exception:
        return 0


# ---------------------------------------------------------------- export

def _expand_recurring(tasks_rows, date_from: str, date_to: str) -> list:
    """
    Espande i task ricorrenti su tutte le date nel range [date_from, date_to].
    I task non ricorrenti compaiono una sola volta se data_prevista è nel range.
    Restituisce lista di dict con occurrence_date aggiunto.
    """
    try:
        d_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        d_to   = datetime.strptime(date_to,   "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return []

    result = []
    for row in tasks_rows:
        (tid, titolo, data_prev, ora, ric, prio, cat_name, url,
         created_at, ric_fine, ric_occ, stato) = row

        try:
            dp = datetime.strptime(str(data_prev), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        ric_fine_date = None
        if ric_fine:
            try:
                ric_fine_date = datetime.strptime(str(ric_fine), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        base = {
            "id":           tid,
            "titolo":       titolo,
            "data_prevista": data_prev or "",
            "ora_prevista": ora        or "",
            "ricorrenza":   ric        or "none",
            "priorita":     prio       or "",
            "categoria":    cat_name   or "",
            "url":          url        or "",
            "created_at":   created_at or "",
            "stato":        stato      or "aperto",
        }

        if ric == "none":
            if d_from <= dp <= d_to:
                result.append({**base, "occurrence_date": str(dp)})
        else:
            cur       = max(dp, d_from)
            occ_count = 0
            while cur <= d_to:
                if ric_fine_date and cur > ric_fine_date:
                    break
                cade = False
                if   ric == "daily"          and dp <= cur: cade = True
                elif ric == "every2days"     and dp <= cur and (cur - dp).days % 2  == 0: cade = True
                elif ric == "weekly"         and dp <= cur and (cur - dp).days % 7  == 0: cade = True
                elif ric == "every2weeks"    and dp <= cur and (cur - dp).days % 14 == 0: cade = True
                elif ric == "monthly"        and dp <= cur and dp.day == cur.day:          cade = True
                elif ric == "monthly_first_monday" and dp <= cur:
                    first_day = cur.replace(day=1)
                    dtm = (7 - first_day.weekday()) % 7 if first_day.weekday() != 0 else 0
                    if cur == first_day + timedelta(days=dtm): cade = True
                elif ric == "monthly_last_friday" and dp <= cur:
                    last_day = (cur.replace(day=31) if cur.month == 12
                                else cur.replace(month=cur.month + 1, day=1) - timedelta(days=1))
                    days_back = (last_day.weekday() - 4) % 7
                    if cur == last_day - timedelta(days=days_back): cade = True

                if cade:
                    if ric_occ and occ_count >= int(ric_occ):
                        break
                    result.append({**base, "occurrence_date": str(cur)})
                    occ_count += 1

                cur += timedelta(days=1)

    return result


# ---------------------------------------------------------------- contaschei

def get_all_movement_categories(user_id=None, type_filter=None):
    """Restituisce le tipologie di movimento dell'utente, opzionalmente filtrate per tipo."""
    uid = user_id or (current_user.id if current_user.is_authenticated else None)
    db  = get_db()
    c   = db.cursor()
    if type_filter:
        c.execute(
            "SELECT id, name, type, color FROM movement_categories "
            "WHERE user_id = %s AND type = %s ORDER BY name ASC",
            (uid, type_filter),
        )
    else:
        c.execute(
            "SELECT id, name, type, color FROM movement_categories "
            "WHERE user_id = %s ORDER BY name ASC",
            (uid,),
        )
    return c.fetchall()


def get_movement_exceptions_map(movement_ids, date_from: str, date_to: str) -> dict:
    """
    Carica le eccezioni (skip/override) per un insieme di movimenti nel range indicato.
    Restituisce un dict {(movement_id, occurrence_date_str): (action, override_amount, override_note)}.
    """
    if not movement_ids:
        return {}
    db = get_db()
    c  = db.cursor()
    ph = ",".join(["%s"] * len(movement_ids))
    c.execute(f"""
        SELECT movement_id, occurrence_date, action, override_amount, override_note
        FROM movement_exceptions
        WHERE movement_id IN ({ph}) AND occurrence_date BETWEEN %s AND %s
    """, (*movement_ids, date_from, date_to))
    return {
        (mid, str(occ_date)): (action, override_amount, override_note)
        for mid, occ_date, action, override_amount, override_note in c.fetchall()
    }


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _expand_recurring_movements(rows, date_from: str, date_to: str, exceptions: dict = None) -> list:
    """
    Espande i movimenti ricorrenti su tutte le date nel range [date_from, date_to],
    applicando le eccezioni (skip/override) per le singole occorrenze.

    rows: tuple (id, category_id, cat_name, cat_color, tipo, amount, date,
                 ricorrenza, ricorrenza_fine, ricorrenza_occorrenze, note)
    exceptions: dict {(movement_id, occurrence_date_str): (action, override_amount, override_note)}
    Restituisce lista di dict con occurrence_date aggiunto.
    """
    exceptions = exceptions or {}
    try:
        d_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        d_to   = datetime.strptime(date_to,   "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return []

    result = []
    for row in rows:
        (mid, cat_id, cat_name, cat_color, tipo, amount, mdate,
         ric, ric_fine, ric_occ, note) = row

        try:
            dp = datetime.strptime(str(mdate), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        ric_fine_date = None
        if ric_fine:
            try:
                ric_fine_date = datetime.strptime(str(ric_fine), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        def emit(occ_date):
            exc = exceptions.get((mid, str(occ_date)))
            amt, nt = float(amount), (note or "")
            if exc:
                action, override_amount, override_note = exc
                if action == "skip":
                    return
                if action == "override":
                    if override_amount is not None:
                        amt = float(override_amount)
                    if override_note is not None:
                        nt = override_note
            result.append({
                "id": mid, "category_id": cat_id, "categoria": cat_name or "",
                "color": cat_color or "", "tipo": tipo, "amount": amt, "note": nt,
                "occurrence_date": str(occ_date), "has_exception": bool(exc),
                "is_recurring": ric != "none",
            })

        if ric == "none":
            if d_from <= dp <= d_to:
                emit(dp)
            continue

        cur       = max(dp, d_from)
        occ_count = 0
        while cur <= d_to:
            if ric_fine_date and cur > ric_fine_date:
                break
            cade = False
            if   ric == "daily"          and dp <= cur: cade = True
            elif ric == "every2days"     and dp <= cur and (cur - dp).days % 2  == 0: cade = True
            elif ric == "weekly"         and dp <= cur and (cur - dp).days % 7  == 0: cade = True
            elif ric == "every2weeks"    and dp <= cur and (cur - dp).days % 14 == 0: cade = True
            elif ric == "monthly"        and dp <= cur and dp.day == cur.day:          cade = True
            elif ric == "monthly_first_monday" and dp <= cur:
                first_day = cur.replace(day=1)
                dtm = (7 - first_day.weekday()) % 7 if first_day.weekday() != 0 else 0
                if cur == first_day + timedelta(days=dtm): cade = True
            elif ric == "monthly_last_friday" and dp <= cur:
                last_day = (cur.replace(day=31) if cur.month == 12
                            else cur.replace(month=cur.month + 1, day=1) - timedelta(days=1))
                days_back = (last_day.weekday() - 4) % 7
                if cur == last_day - timedelta(days=days_back): cade = True
            elif ric == "yearly" and dp <= cur:
                if dp.month == cur.month and dp.day == cur.day:
                    cade = True
                elif dp.month == 2 and dp.day == 29 and cur.month == 2 and cur.day == 28 \
                        and not _is_leap_year(cur.year):
                    cade = True

            if cade:
                if ric_occ and occ_count >= int(ric_occ):
                    break
                emit(cur)
                occ_count += 1

            cur += timedelta(days=1)

    return result


def get_period_bounds(period_type: str, period_offset: int = 0, ref_date=None):
    """
    Calcola (date_from, date_to) ISO per period_type in
    {month, bimonth, quarter, fourmonth, semester, year}, a blocchi fissi da
    inizio anno (es. bimestri = gen-feb, mar-apr, ...). period_offset sposta
    il blocco avanti/indietro (0 = corrente, -1 = precedente, +1 = successivo).
    """
    sizes = {"month": 1, "bimonth": 2, "quarter": 3,
             "fourmonth": 4, "semester": 6, "year": 12}
    n_months = sizes.get(period_type, 1)
    ref = ref_date or date.today()

    block_start_month0 = (ref.month - 1) // n_months * n_months
    total_start = ref.year * 12 + block_start_month0 + period_offset * n_months

    start_year, start_month0 = divmod(total_start, 12)
    d_from = date(start_year, start_month0 + 1, 1)

    total_end = total_start + n_months
    end_year, end_month0 = divmod(total_end, 12)
    d_to = date(end_year, end_month0 + 1, 1) - timedelta(days=1)

    return d_from.isoformat(), d_to.isoformat()
