"""Route Outlook desktop-only: crea evento e attività via win32com."""
from datetime import datetime

from flask import current_app, jsonify, request


def register(app):

    @app.route("/outlook/crea_evento", methods=["POST"])
    def outlook_crea_evento():
        data        = request.get_json(force=True)
        titolo      = data.get("titolo", "")
        descrizione = data.get("descrizione", "")
        data_inizio = data.get("data_inizio", "")
        ora_inizio  = data.get("ora_inizio", "09:00")
        data_fine   = data.get("data_fine", "")
        ora_fine    = data.get("ora_fine", "10:00")
        fullday     = data.get("fullday", False)

        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()

            try:
                outlook = win32com.client.GetActiveObject("Outlook.Application")
            except Exception:
                outlook = win32com.client.Dispatch("Outlook.Application")

            appt         = outlook.CreateItem(1)  # olAppointmentItem
            appt.Subject = titolo
            appt.Body    = descrizione

            if fullday:
                appt.AllDayEvent = True
                appt.Start = datetime.strptime(data_inizio, "%Y-%m-%d").strftime("%m/%d/%Y")
                appt.End   = datetime.strptime(data_fine,   "%Y-%m-%d").strftime("%m/%d/%Y")
            else:
                appt.Start = datetime.strptime(f"{data_inizio} {ora_inizio}", "%Y-%m-%d %H:%M").strftime("%m/%d/%Y %H:%M")
                appt.End   = datetime.strptime(f"{data_fine} {ora_fine}",     "%Y-%m-%d %H:%M").strftime("%m/%d/%Y %H:%M")

            appt.ReminderSet = True
            appt.Save()
            return jsonify({"ok": True})

        except ImportError as e:
            current_app.logger.error("win32com non disponibile: %s", e)
            return jsonify({"ok": False, "error": f"pywin32 non disponibile: {e}"}), 503
        except Exception as e:
            current_app.logger.exception("Errore creazione evento Outlook: %s", e)
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/outlook/crea_attivita", methods=["POST"])
    def outlook_crea_attivita():
        data          = request.get_json(force=True)
        titolo        = data.get("titolo", "")
        data_scadenza = data.get("data_scadenza", "")
        ora           = data.get("ora", "09:00")
        descrizione   = data.get("descrizione", "")

        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()

            try:
                outlook = win32com.client.GetActiveObject("Outlook.Application")
            except Exception:
                outlook = win32com.client.Dispatch("Outlook.Application")

            task         = outlook.CreateItem(3)  # olTaskItem
            task.Subject = titolo
            task.Body    = descrizione

            if data_scadenza:
                try:
                    dt_obj             = datetime.strptime(f"{data_scadenza} {ora}", "%Y-%m-%d %H:%M")
                    task.DueDate       = dt_obj.strftime("%m/%d/%Y")
                    task.StartDate     = dt_obj.strftime("%m/%d/%Y")
                    task.ReminderSet   = True
                    task.ReminderTime  = dt_obj.strftime("%m/%d/%Y %H:%M")
                except ValueError:
                    pass

            task.Save()
            return jsonify({"ok": True})

        except ImportError as e:
            current_app.logger.error("win32com non disponibile: %s", e)
            return jsonify({"ok": False, "error": f"pywin32 non disponibile: {e}"}), 503
        except Exception as e:
            current_app.logger.exception("Errore creazione attività Outlook: %s", e)
            return jsonify({"ok": False, "error": str(e)}), 500
