"""
Tutti i template HTML inline di TaskPlanner.

Importa da qui nelle route:
    from core.templates import TEMPLATE_INDEX, TEMPLATE_NEW, ...
"""
from core.templates.login     import _LOGIN_PAGE, _PASSWORD_PAGE
from core.templates.outlook   import _OUTLOOK_JS
from core.templates.export    import TEMPLATE_EXPORT, TEMPLATE_CHANGELOG
from core.templates.cestino   import TEMPLATE_CESTINO
from core.templates.index     import TEMPLATE_INDEX
from core.templates.forms     import TEMPLATE_EDIT, TEMPLATE_NEW
from core.templates.setup     import TEMPLATE_SETUP
from core.templates.stats     import TEMPLATE_STATS
from core.templates.contaschei import (
    TEMPLATE_CONTASCHEI,
    TEMPLATE_CONTASCHEI_BILANCIO,
    TEMPLATE_CONTASCHEI_CATEGORIES,
)
from core.templates.privacy import TEMPLATE_PRIVACY

__all__ = [
    "_LOGIN_PAGE",
    "_PASSWORD_PAGE",
    "_OUTLOOK_JS",
    "TEMPLATE_EXPORT",
    "TEMPLATE_CHANGELOG",
    "TEMPLATE_CESTINO",
    "TEMPLATE_INDEX",
    "TEMPLATE_EDIT",
    "TEMPLATE_NEW",
    "TEMPLATE_SETUP",
    "TEMPLATE_STATS",
    "TEMPLATE_CONTASCHEI",
    "TEMPLATE_CONTASCHEI_BILANCIO",
    "TEMPLATE_CONTASCHEI_CATEGORIES",
    "TEMPLATE_PRIVACY",
]
