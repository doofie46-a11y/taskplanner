"""Pagina API e integrazioni (server): chiavi API per utente, istruzioni, esempi."""
import os
from datetime import datetime, timezone

from flask import current_app, make_response, redirect, render_template_string, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from core.api_keys import (
    MAX_KEY_NAME_LEN, MAX_KEYS_PER_USER, count_keys, create_key, delete_key, list_keys,
    regenerate_key,
)
from core.db import get_db
from core.templates import TEMPLATE_API
from server.auth import _csrf_ok, _csrf_token


def _fmt_ts(value):
    """Timestamp del DB (NOW() in UTC, senza fuso) → gg/mm/aaaa hh:mm nel fuso dell'app."""
    if not value:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    local = value.replace(tzinfo=timezone.utc).astimezone(current_app.config['TIMEZONE'])
    return local.strftime('%d/%m/%Y %H:%M')


def register(app):

    def _render(new_key=None, new_key_name=None, error=None, status=200):
        # APP_BASE_URL solo se impostata davvero: il default di config (localhost) non
        # servirebbe a niente a chi copia l'indirizzo sul telefono
        base = (os.environ.get('APP_BASE_URL') or request.host_url).rstrip('/')
        resp = make_response(render_template_string(
            TEMPLATE_API,
            keys=[
                {'id': k[0], 'name': k[1], 'hint': k[2], 'created': _fmt_ts(k[3]),
                 'last_used': _fmt_ts(k[4])}
                for k in list_keys(get_db(), current_user.id)
            ],
            max_keys=MAX_KEYS_PER_USER,
            max_name_len=MAX_KEY_NAME_LEN,
            endpoint=base + '/api/tasks',
            is_https=base.startswith('https://'),
            new_key=new_key,
            new_key_name=new_key_name,
            error=error,
            csrf_token=_csrf_token(),
        ), status)
        # La pagina può contenere una chiave appena creata: niente cache, né del browser né di proxy
        resp.headers['Cache-Control'] = 'no-store'
        return resp

    @app.route("/account/api")
    @login_required
    def api_page():
        return _render()

    @app.route("/account/api/create", methods=["POST"])
    @login_required
    def api_key_create():
        db   = get_db()
        name = request.form.get("name", "").strip()
        if not _csrf_ok():
            return _render(error=_("Sessione scaduta, riprova."), status=400)
        if not name:
            return _render(error=_("Dai un nome alla chiave, per esempio il dispositivo che la userà."), status=400)
        if len(name) > MAX_KEY_NAME_LEN:
            return _render(error=_("Il nome può avere al massimo %(n)s caratteri.", n=MAX_KEY_NAME_LEN), status=400)
        if count_keys(db, current_user.id) >= MAX_KEYS_PER_USER:
            return _render(error=_("Hai già %(n)s chiavi: revocane una prima di crearne un'altra.", n=MAX_KEYS_PER_USER), status=400)
        key = create_key(db, current_user.id, name)
        current_app.logger.info("API key creata per user %s: '%s'", current_user.id, name)
        return _render(new_key=key, new_key_name=name)

    @app.route("/account/api/<int:kid>/regenerate", methods=["POST"])
    @login_required
    def api_key_regenerate(kid):
        if not _csrf_ok():
            return _render(error=_("Sessione scaduta, riprova."), status=400)
        db  = get_db()
        key = regenerate_key(db, current_user.id, kid)
        if not key:
            return redirect(url_for("api_page"))
        name = next((k[1] for k in list_keys(db, current_user.id) if k[0] == kid), "")
        current_app.logger.info("API key #%d rigenerata per user %s", kid, current_user.id)
        return _render(new_key=key, new_key_name=name)

    @app.route("/account/api/<int:kid>/delete", methods=["POST"])
    @login_required
    def api_key_delete(kid):
        if not _csrf_ok():
            return _render(error=_("Sessione scaduta, riprova."), status=400)
        if delete_key(get_db(), current_user.id, kid):
            current_app.logger.info("API key #%d revocata per user %s", kid, current_user.id)
        return redirect(url_for("api_page"))
