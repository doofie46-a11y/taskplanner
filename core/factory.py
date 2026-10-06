"""
App factory — crea e configura l'istanza Flask.

Utilizzo:
    from core.factory import create_app
    app = create_app('server')   # PostgreSQL + Google OAuth
    app = create_app('desktop')  # SQLite + local auth
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, redirect, request, session, url_for
from flask_babel import Babel
from flask_login import LoginManager
from werkzeug.exceptions import HTTPException

APP_VERSION  = '1.6.0'
APP_CODENAME = 'Raboso'

# Link "offrimi una birra" mostrato in sidebar e changelog (vuoto = nascosto).
# Override via env TASKPLANNER_SUPPORT_URL.
SUPPORT_URL = 'https://ko-fi.com/claudioruffina'


def create_app(mode: str, config_override: dict = None) -> Flask:
    """
    Crea l'app Flask configurata per il mode indicato.

    mode: 'server'  — PostgreSQL + Google OAuth (produzione)
          'desktop' — SQLite + auto-login locale (PyInstaller)

    config_override: dizionario opzionale per sovrascrivere valori di config
                     (utile per test o configurazioni speciali).
    """
    if mode not in ('server', 'desktop'):
        raise ValueError(f"Mode non valido: {mode!r}. Deve essere 'server' o 'desktop'.")

    app = Flask(__name__)

    # ------------------------------------------------------------------ config
    # Radice del pacchetto (es. /var/www/taskplanner) — per serve_from_directory
    app.config['BUNDLE_DIR'] = str(Path(__file__).parent.parent)
    # SECRET_KEY: il server la richiede via env, il desktop la genera al primo avvio
    # (vedi desktop/__init__.py) — nessuna chiave di default condivisa nel codice.
    app.secret_key = os.environ.get('SECRET_KEY')
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB

    # Timezone: default Europe/Rome, override via env TZ_NAME
    tz_name = os.environ.get('TZ_NAME', 'Europe/Rome')
    app.config['TIMEZONE'] = ZoneInfo(tz_name)

    app.config['APP_VERSION']  = APP_VERSION
    app.config['APP_CODENAME'] = APP_CODENAME
    app.config['SUPPORT_URL']  = os.environ.get('TASKPLANNER_SUPPORT_URL', SUPPORT_URL)

    # ------------------------------------------------------------------ Babel
    app.config['BABEL_DEFAULT_LOCALE'] = 'it'
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = str(Path(__file__).parent.parent / 'translations')

    # Data dir e cartella allegati — cross-platform via pathlib
    data_dir = Path(os.environ.get('TASKPLANNER_DATA', Path.home() / '.taskplanner'))
    upload_folder = data_dir / 'attachments'
    data_dir.mkdir(parents=True, exist_ok=True)
    upload_folder.mkdir(parents=True, exist_ok=True)
    app.config['DATA_DIR']      = data_dir
    app.config['UPLOAD_FOLDER'] = str(upload_folder)

    # Override espliciti (es. test)
    if config_override:
        app.config.update(config_override)

    # ----------------------------------------------------------------- logging
    log_path = data_dir / 'taskplanner.log'
    handler = RotatingFileHandler(
        str(log_path), maxBytes=5_000_000, backupCount=3, encoding='utf-8'
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.DEBUG)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    app.logger.info('create_app mode=%s tz=%s', mode, tz_name)

    def _get_locale():
        lang = session.get('lang') or request.args.get('lang')
        if lang in ('it', 'en'):
            return lang
        return request.accept_languages.best_match(['it', 'en'], default='it')

    Babel(app, locale_selector=_get_locale)

    # --------------------------------------------------------------- filtro Jinja
    @app.template_filter('fmt_date')
    def fmt_date(value):
        """Converte yyyy-mm-dd → dd/mm/yyyy. Restituisce il valore invariato se non valido."""
        if not value:
            return value
        try:
            return datetime.strptime(str(value), '%Y-%m-%d').strftime('%d/%m/%Y')
        except (ValueError, TypeError):
            return value

    @app.context_processor
    def _inject_globals():
        return {'support_url': app.config['SUPPORT_URL'], 'is_desktop': mode == 'desktop'}

    # ------------------------------------------------------------ Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login_page'

    # --------------------------------------------------------- before_request
    @app.before_request
    def _log_request():
        try:
            app.logger.info(
                'Richiesta: %s %s da %s', request.method, request.path, request.remote_addr
            )
        except Exception:
            pass

    # ---------------------------------------------------------- error handler
    @app.errorhandler(Exception)
    def _handle_exception(e):
        if isinstance(e, HTTPException):
            app.logger.warning(
                'HTTPException %s su %s %s: %s',
                e.code, request.method, request.path, e.description,
            )
            return e
        app.logger.exception('Eccezione non gestita su %s %s', request.method, request.path)
        return 'Errore interno.', 500

    # ---------------------------------------------------------- DB teardown
    from core.db import close_db
    app.teardown_appcontext(close_db)

    # ------------------------------------------------- init mode-specifico
    # Ogni modulo espone init_app(app, login_manager) che:
    #   - imposta app.config['DB_FACTORY'] e app.config['DB_DIALECT']
    #   - registra il user_loader su login_manager
    #   - registra il Blueprint 'auth' con le route di login
    if mode == 'server':
        from server import init_app as _init
    else:
        from desktop import init_app as _init
    _init(app, login_manager)
    if not app.secret_key:
        raise RuntimeError('SECRET_KEY non impostata (variabile d\'ambiente obbligatoria in modalità server).')

    # --------------------------------------------------------- route core
    from core.routes_misc        import register as _reg_misc
    from core.routes_tasks       import register as _reg_tasks
    from core.routes_api         import register as _reg_api
    from core.routes_attachments import register as _reg_attachments
    from core.routes_cestino     import register as _reg_cestino
    from core.routes_stats       import register as _reg_stats
    from core.routes_setup       import register as _reg_setup
    from core.routes_export      import register as _reg_export
    from core.routes_contaschei  import register as _reg_contaschei
    _reg_misc(app)
    _reg_tasks(app)
    _reg_api(app)
    _reg_attachments(app)
    _reg_cestino(app)
    _reg_stats(app)
    _reg_setup(app)
    _reg_export(app)
    _reg_contaschei(app)

    @app.route('/lang/<code>')
    def set_language(code):
        if code in ('it', 'en'):
            session['lang'] = code
        return redirect(request.referrer or url_for('home'))

    return app
