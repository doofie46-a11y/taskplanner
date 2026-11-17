"""Login tramite Cloudflare Access (opzionale).

Cloudflare Access sta davanti all'app (sull'edge Cloudflare) e, dopo il login, allega a ogni
richiesta un JWT firmato con l'identità dell'utente: header ``Cf-Access-Jwt-Assertion`` e
cookie ``CF_Authorization``. Qui il JWT viene verificato davvero (firma con le chiavi
pubbliche del team, ``aud``, ``iss``, scadenza): l'header con la sola email
(``Cf-Access-Authenticated-User-Email``) non è usato perché chi raggiunge l'origin
direttamente potrebbe falsificarlo.

Due modi di configurare Access (stesso codice):
  A. Access su tutto il dominio: l'utente entra in automatico, la pagina di login non si vede.
  B. Access solo su /auth/cloudflare: la pagina di login mostra il pulsante
     «Accedi con Cloudflare» accanto agli altri metodi.

Una sessione aperta via Cloudflare dura finché le richieste portano un JWT valido: se la
sessione Access scade, o il JWT è di un altro utente, la sessione dell'app si chiude o cambia.
"""
import threading
import time

import requests
from flask import current_app, request
from joserfc import jws, jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet

JWT_HEADER = "Cf-Access-Jwt-Assertion"
JWT_COOKIE = "CF_Authorization"

# Chiavi pubbliche del team: Cloudflare le ruota periodicamente (le vecchie restano
# valide per un po'), quindi cache con scadenza + rilettura se arriva un kid sconosciuto.
_KEYS_TTL         = 3600
_KEYS_MIN_REFRESH = 60      # mai più di una rilettura al minuto (kid sconosciuti a raffica)
_LEEWAY           = 60      # secondi di tolleranza sugli orologi

_lock       = threading.Lock()
_keys       = None
_keys_kids  = set()
_keys_ts    = 0.0


def normalize_team_domain(value: str) -> str:
    """'https://mioteam.cloudflareaccess.com/' → 'mioteam.cloudflareaccess.com'."""
    value = (value or "").strip().lower()
    for prefix in ("https://", "http://"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value.strip("/")


def _certs_url(team_domain):
    return f"https://{team_domain}/cdn-cgi/access/certs"


def _fetch_keys(team_domain):
    resp = requests.get(_certs_url(team_domain), timeout=5)
    resp.raise_for_status()
    return KeySet.import_key_set({"keys": resp.json()["keys"]})


def _get_keys(team_domain, kid=None):
    """KeySet in cache; riletto se scaduto o se il kid non è tra quelli noti."""
    global _keys, _keys_kids, _keys_ts
    with _lock:
        age   = time.monotonic() - _keys_ts
        stale = _keys is None or age > _KEYS_TTL
        unknown_kid = kid is not None and kid not in _keys_kids
        if stale or (unknown_kid and age > _KEYS_MIN_REFRESH):
            try:
                keys = _fetch_keys(team_domain)
                _keys      = keys
                _keys_kids = {k.kid for k in keys.keys}
                _keys_ts   = time.monotonic()
            except Exception:
                current_app.logger.exception("Cloudflare Access: lettura chiavi pubbliche fallita")
        return _keys


def _reset_cache():
    """Solo per i test."""
    global _keys, _keys_kids, _keys_ts
    with _lock:
        _keys, _keys_kids, _keys_ts = None, set(), 0.0


def get_token():
    """JWT dalla richiesta corrente: header (modo A) o cookie (anche modo B)."""
    return request.headers.get(JWT_HEADER) or request.cookies.get(JWT_COOKIE) or None


def verify_token(token, team_domain, audiences):
    """Ritorna i claims se il JWT è valido e contiene un'email, altrimenti None."""
    if not token:
        return None
    try:
        kid = jws.extract_compact(token.encode()).headers().get("kid")
    except (JoseError, ValueError):
        current_app.logger.warning("Cloudflare Access: JWT non leggibile")
        return None
    keys = _get_keys(team_domain, kid)
    if keys is None:
        return None
    try:
        tok = jwt.decode(token, keys, algorithms=["RS256"])
        jwt.JWTClaimsRegistry(
            leeway=_LEEWAY,
            iss={"essential": True, "value": f"https://{team_domain}"},
            aud={"essential": True, "values": list(audiences)},
            exp={"essential": True},
        ).validate(tok.claims)
    except (JoseError, ValueError) as e:
        current_app.logger.warning("Cloudflare Access: JWT rifiutato (%s)", type(e).__name__)
        return None
    email = (tok.claims.get("email") or "").strip().lower()
    if not email:
        # Service token (accesso machine-to-machine): nessun utente da associare
        return None
    tok.claims["email"] = email
    return tok.claims


def current_identity():
    """Claims Cloudflare della richiesta corrente (None se assenti o non validi)."""
    cfg = current_app.config
    return verify_token(get_token(), cfg["CF_ACCESS_TEAM_DOMAIN"], cfg["CF_ACCESS_AUD"])


def find_or_create_user(db, email, auto_create):
    """Id dell'utente con questa email (creato se manca e auto_create). None se non esiste."""
    from server.users import create_default_categories
    c = db.cursor()
    c.execute(
        "SELECT id FROM users WHERE lower(email) = %s ORDER BY id LIMIT 2",
        (email,),
    )
    rows = c.fetchall()
    if len(rows) > 1:
        current_app.logger.warning(
            "Cloudflare Access: più utenti con email %s, uso il più vecchio (id %s)",
            email, rows[0][0],
        )
    if rows:
        return rows[0][0]
    if not auto_create:
        return None
    c.execute(
        "INSERT INTO users (email, name) VALUES (%s, %s) RETURNING id",
        (email, email.split("@")[0]),
    )
    user_id = c.fetchone()[0]
    create_default_categories(c, user_id)
    db.commit()
    current_app.logger.info("Cloudflare Access: creato utente %s per %s", user_id, email)
    return user_id
