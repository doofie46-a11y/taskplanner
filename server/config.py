"""Configurazione server: legge variabili d'ambiente per PostgreSQL e Google OAuth."""
import os

# Obbligatoria: nessun default con credenziali nel codice
DATABASE_URL = os.environ.get("DATABASE_URL", "")

GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# URL base per costruire il redirect URI OAuth (senza slash finale)
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")

# Email di contatto mostrata nell'informativa privacy (/privacy)
PRIVACY_CONTACT_EMAIL = os.environ.get("PRIVACY_CONTACT_EMAIL", "")
