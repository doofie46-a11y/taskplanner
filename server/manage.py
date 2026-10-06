"""
Gestione account locali (login con username e password) da riga di comando.

Usa le stesse variabili d'ambiente del server (DATABASE_URL, SECRET_KEY, …).

    python -m server.manage create-user mario --name "Mario Rossi"
    python -m server.manage set-password mario      # reimposta e sblocca
    python -m server.manage list-users

La password viene chiesta in modo interattivo; con --password-stdin la legge
dalla prima riga dello standard input (utile negli script e in Docker).
"""
import argparse
import getpass
import sys

from server.users import (
    MIN_PASSWORD_LEN, create_local_user, normalize_username, set_password,
)


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Ripeti la password: "):
            sys.exit("Le due password non coincidono.")
    if len(password) < MIN_PASSWORD_LEN:
        sys.exit(f"La password deve avere almeno {MIN_PASSWORD_LEN} caratteri.")
    return password


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m server.manage")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create-user", help="crea un account locale")
    p_create.add_argument("username")
    p_create.add_argument("--name", help="nome visualizzato (default: username)")
    p_create.add_argument("--email", help="email, opzionale")
    p_create.add_argument("--password-stdin", action="store_true")

    p_pw = sub.add_parser("set-password", help="reimposta la password e sblocca l'account")
    p_pw.add_argument("username")
    p_pw.add_argument("--password-stdin", action="store_true")

    sub.add_parser("list-users", help="elenca gli utenti")

    args = parser.parse_args(argv)

    from core.db import get_db
    from core.factory import create_app
    app = create_app("server")

    with app.app_context():
        db = get_db()
        c  = db.cursor()

        if args.cmd == "create-user":
            password = _read_password(args.password_stdin)
            try:
                uid = create_local_user(db, args.username, password, args.name, args.email)
            except ValueError as e:
                sys.exit(f"Errore: {e}")
            print(f"Utente '{normalize_username(args.username)}' creato (id {uid}).")
            if not app.config['LOCAL_AUTH_ENABLED']:
                print("Attenzione: il login locale è disattivato, imposta LOCAL_AUTH=true.")

        elif args.cmd == "set-password":
            username = normalize_username(args.username)
            c.execute("SELECT id FROM users WHERE username = %s", (username,))
            row = c.fetchone()
            if not row:
                sys.exit(f"Utente locale '{username}' non trovato.")
            set_password(db, row[0], _read_password(args.password_stdin))
            print(f"Password di '{username}' aggiornata.")

        elif args.cmd == "list-users":
            c.execute(
                "SELECT id, COALESCE(username, ''), email, "
                "CASE WHEN google_id IS NOT NULL THEN 'google' ELSE 'locale' END, "
                "COALESCE(locked_until > NOW(), FALSE) "
                "FROM users ORDER BY id"
            )
            print(f"{'ID':>4}  {'TIPO':<7} {'USERNAME':<20} EMAIL")
            for uid, username, email, kind, locked in c.fetchall():
                print(f"{uid:>4}  {kind:<7} {username:<20} {email}"
                      + ("  [bloccato]" if locked else ""))


if __name__ == "__main__":
    main()
