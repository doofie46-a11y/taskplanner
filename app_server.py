"""
Entrypoint server — Flask + PostgreSQL + Google OAuth.

Gunicorn: gunicorn -w 2 -b 127.0.0.1:5002 app_server:app
systemd:  ExecStart=gunicorn ... app_server:app

NOTA: Per attivare questa versione il servizio va riavviato:
    systemctl restart taskplanner
Il file app_web.py rimane in archivio finché non si è verificato
il corretto funzionamento in produzione (fase Cutover).
"""
from core.factory import create_app

app = create_app("server")
