"""
Modelli condivisi — nessuna dipendenza da DB o auth provider.

User è usato da Flask-Login in entrambe le varianti (server e desktop).
Il user_loader che istanzia User dal DB risiede in server/auth.py e desktop/auth.py.
"""
from flask_login import UserMixin

# Livelli di priorità in ordine crescente — usati anche da core/logic.py
PRIO_LEVELS = ["Bassa", "Media", "Alta", "Urgente"]

# Tipi di movimento Contaschei
MOVEMENT_TYPES = ["income", "expense"]


class User(UserMixin):
    """
    Utente autenticato.

    Server:  id = PK PostgreSQL, google_id valorizzato, picture da Google
    Desktop: id = '1' (utente locale fisso), google_id = None, picture = None
    Server con login locale: google_id = None, username valorizzato, has_password = True
    """

    def __init__(self, id, google_id, email, name, picture, api_key,
                 username=None, has_password=False):
        self.id        = str(id)
        self.google_id = google_id
        self.email     = email
        self.name      = name
        self.picture   = picture
        self.api_key   = api_key
        self.username  = username
        self.has_password = bool(has_password)

    def __repr__(self):
        return f"<User id={self.id} email={self.email!r}>"
