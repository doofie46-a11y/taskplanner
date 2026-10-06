"""Configurazione server: legge variabili d'ambiente per PostgreSQL, Google OAuth e login locale."""
import os

# Obbligatoria: nessun default con credenziali nel codice
DATABASE_URL = os.environ.get("DATABASE_URL", "")

GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_ENABLED       = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

# Login con username e password (account creati da CLI: python -m server.manage).
# Non impostata = attivo solo se Google OAuth non è configurato.
_local_auth = os.environ.get("LOCAL_AUTH", "").strip().lower()
LOCAL_AUTH_ENABLED = (
    _local_auth in ("1", "true", "yes", "on") if _local_auth else not GOOGLE_ENABLED
)

# URL base per costruire il redirect URI OAuth (senza slash finale)
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")

# Email di contatto mostrata nell'informativa privacy (/privacy)
PRIVACY_CONTACT_EMAIL = os.environ.get("PRIVACY_CONTACT_EMAIL", "")
