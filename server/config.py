"""Configurazione server: legge variabili d'ambiente per PostgreSQL, Google OAuth, Cloudflare Access e login locale."""
import os

# Obbligatoria: nessun default con credenziali nel codice
DATABASE_URL = os.environ.get("DATABASE_URL", "")

GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_ENABLED       = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

# Login tramite Cloudflare Access (vedi server/cf_access.py): servono entrambe.
# CF_ACCESS_TEAM_DOMAIN = "<team>.cloudflareaccess.com"; CF_ACCESS_AUD = Application Audience
# (AUD) tag dell'applicazione Access, anche più di uno separati da virgola.
from server.cf_access import normalize_team_domain  # noqa: E402

CF_ACCESS_TEAM_DOMAIN = normalize_team_domain(os.environ.get("CF_ACCESS_TEAM_DOMAIN", ""))
CF_ACCESS_AUD         = [a.strip() for a in os.environ.get("CF_ACCESS_AUD", "").split(",") if a.strip()]
CF_ACCESS_ENABLED     = bool(CF_ACCESS_TEAM_DOMAIN and CF_ACCESS_AUD)
CF_ACCESS_PARTIAL     = bool(CF_ACCESS_TEAM_DOMAIN) != bool(CF_ACCESS_AUD)
# Crea l'account al primo accesso di un'email nuova (chi entra lo decide la policy Access)
CF_ACCESS_AUTO_CREATE = os.environ.get("CF_ACCESS_AUTO_CREATE", "true").strip().lower() in ("1", "true", "yes", "on")

# Login con username e password (account creati da CLI: python -m server.manage).
# Non impostata = attivo solo se né Google né Cloudflare Access sono configurati.
_local_auth = os.environ.get("LOCAL_AUTH", "").strip().lower()
LOCAL_AUTH_ENABLED = (
    _local_auth in ("1", "true", "yes", "on") if _local_auth
    else not (GOOGLE_ENABLED or CF_ACCESS_ENABLED)
)

# URL base per costruire il redirect URI OAuth (senza slash finale)
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")

# Email di contatto mostrata nell'informativa privacy (/privacy)
PRIVACY_CONTACT_EMAIL = os.environ.get("PRIVACY_CONTACT_EMAIL", "")

# Demo pubblica: account usa e getta con dati di esempio (vedi server/demo.py).
# Disattiva login normale, allegati e API.
DEMO_MODE         = os.environ.get("DEMO_MODE", "").strip().lower() in ("1", "true", "yes", "on")
DEMO_MAX_PER_HOUR = int(os.environ.get("DEMO_MAX_PER_HOUR", "200"))
