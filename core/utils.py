"""Funzioni di utilità condivise — nessuna dipendenza da DB o auth."""

from flask import current_app

ALLOWED_EXTENSIONS = {
    'txt', 'log', 'pdf', 'docx', 'doc', 'msg', 'odt',
    'png', 'jpg', 'jpeg', 'bmp', 'gif', 'svg', 'webp',
    'xlsx', 'xls', 'xlsm', 'csv', 'json', 'sql', 'xml',
    'pptx', 'ppt', 'zip', '7z', 'rar', 'py', 'html', 'css', 'js',
}

_ICON_MAP = {
    frozenset(['txt', 'log', 'pdf', 'docx', 'doc', 'odt']): '📄',
    frozenset(['msg']):                                        '📬',
    frozenset(['png', 'jpg', 'jpeg', 'bmp', 'gif', 'svg', 'webp']): '🖼️',
    frozenset(['zip', '7z', 'rar']):                          '🗜️',
    frozenset(['py', 'html', 'css', 'js', 'sql']):            '🪄',
}


def allowed_file(filename: str) -> bool:
    """Restituisce True se l'estensione del file è tra quelle ammesse."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_icon_for_filename(filename: str) -> str:
    """Restituisce un'emoji che rappresenta il tipo di file."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    for exts, icon in _ICON_MAP.items():
        if ext in exts:
            return icon
    return '📎'


def format_time(minutes: int) -> str:
    """Converte minuti in stringa leggibile: 90 → '1h 30m', 60 → '1h', 5 → '5m'."""
    h = minutes // 60
    m = minutes % 60
    if h > 0:
        return f"{h}h {m}m" if m else f"{h}h"
    return f"{m}m"


def app_timezone():
    """Restituisce il ZoneInfo configurato nell'app (default Europe/Rome)."""
    return current_app.config['TIMEZONE']
