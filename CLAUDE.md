# TaskPlanner — CLAUDE.md

## Panoramica del progetto

TaskPlanner è un'applicazione per la gestione delle attività quotidiane, costruita con **Python + Flask**.

Supporta **due target di deployment**:

| Target | Auth | DB | Entry point | Distribuzione |
|---|---|---|---|---|
| **Server** | Google OAuth | PostgreSQL | `app_server.py` | systemd + gunicorn |
| **Desktop** | auto-login locale | SQLite | `app_desktop.py` | PyInstaller (Win/Mac/Linux) |

**Versione corrente:** `1.5.0 "Aglianico"`

**Licenza:** GPL-3.0 (`LICENSE`). Dettagli dell'istanza di produzione (server, deploy, backup) in `CLAUDE.local.md`, non versionato.

---

## Stato della migrazione verso la shared-core architecture

> Aggiornato ad ogni fase completata. Se riprendi una sessione interrotta, parti da qui.

| Fase | Descrizione | Stato |
|---|---|---|
| 1 | Scaffolding — directory, requirements, entrypoint stub | ✅ Completata |
| 2 | App factory — `core/factory.py`, `core/db.py`, `create_app(mode)` | ✅ Completata |
| 3 | Utils e modelli — `core/utils.py`, `core/models.py` | ✅ Completata |
| 4 | Logica di business — `core/logic.py` | ✅ Completata |
| 5 | Template — `core/templates/` | ✅ Completata |
| 6 | Route — `core/routes_*.py` (pattern `register(app)`) | ✅ Completata |
| 7 | Adapter server e desktop — `server/`, `desktop/`, entrypoint reali | ✅ Completata |
| Cutover | Aggiornamento systemd, archiviazione `app_web.py` | ✅ Completata |

**Migrazione completata.** Il server gira su `app_server:app` (shared-core architecture).
`app_web.py` archiviato come `app_web.py.bak` — eliminabile quando non serve più come riferimento.

---

## Struttura dei file (post-migrazione)

```
taskplanner/
├── core/                      # logica condivisa — ZERO dipendenze da postgres/oauth
│   ├── factory.py             # create_app(mode) — app factory
│   ├── db.py                  # get_db(), placeholder abstraction
│   ├── models.py              # User(UserMixin), costanti
│   ├── utils.py               # allowed_file, get_icon_for_filename, format_time
│   ├── logic.py               # get_tasks_for_date, calcola_priorita_effettiva,
│   │                          # _daily_cleanup, _get_cestino_count, _expand_recurring
│   ├── routes_tasks.py        # /, /add, /new, /edit, /done, /posticipa, /pin, /delete
│   ├── routes_attachments.py  # /upload, /download, /delete_attachment
│   ├── routes_cestino.py      # /cestino e sub-routes
│   ├── routes_api.py          # /tasks_stato, /tasks_in_scadenza, /add_from_mail
│   ├── routes_setup.py        # /setup/categories CRUD
│   ├── routes_stats.py        # /stats
│   ├── routes_export.py       # /export
│   ├── routes_misc.py         # /changelog, /favicon.ico, PWA assets
│   └── routes_contaschei.py   # /contaschei e sub-routes (entrate/spese personali)
│
├── core/templates/            # template inline (render_template_string)
│   ├── index.py               # TEMPLATE_INDEX
│   ├── forms.py               # TEMPLATE_NEW, TEMPLATE_EDIT
│   ├── setup.py               # TEMPLATE_SETUP
│   ├── stats.py               # TEMPLATE_STATS
│   ├── export.py              # TEMPLATE_EXPORT, TEMPLATE_CHANGELOG
│   ├── cestino.py             # TEMPLATE_CESTINO
│   ├── contaschei.py          # TEMPLATE_CONTASCHEI, TEMPLATE_CONTASCHEI_CATEGORIES, TEMPLATE_CONTASCHEI_BILANCIO
│   └── login.py               # _LOGIN_PAGE (base, senza provider-specific HTML)
│
├── server/                    # server-only: postgres + google oauth
│   ├── db.py                  # psycopg2 factory, init_db() PostgreSQL
│   ├── auth.py                # Google OAuth routes + user loader
│   └── config.py              # DATABASE_URL, GOOGLE_CLIENT_ID/SECRET, APP_BASE_URL
│
├── desktop/                   # desktop-only: sqlite + local auth
│   ├── db.py                  # sqlite3 factory, init_db() SQLite
│   ├── auth.py                # auto-login utente locale
│   ├── config.py              # SQLITE_PATH (pathlib.Path), DATA_DIR cross-platform
│   ├── routes_outlook.py      # /outlook/crea_evento, /outlook/crea_attivita (win32com)
│   └── launcher.py            # apre browser in --app mode, avvia Flask su thread
│
├── app_server.py              # entrypoint server (gunicorn: app_server:app)
├── app_desktop.py             # entrypoint desktop (PyInstaller target)
├── app_web.py                 # LEGACY — monolite originale, rimane fino al cutover
└── requirements/
    ├── base.txt               # flask, flask-login, werkzeug, requests
    ├── server.txt             # + psycopg2-binary, authlib, gunicorn
    └── desktop.txt            # + pywebview, pyinstaller, platformdirs
```

---

## Desktop — sviluppo locale e distribuzione

### Avvio rapido in locale

```bash
# Dalla root del progetto con venv attivo
pip install -r requirements/desktop.txt
python app_desktop.py
```

Si apre direttamente una finestra nativa (pywebview). Flask parte su una porta casuale libera;
pywebview la interroga con polling finché non risponde, poi apre la finestra.
Chiudere la finestra termina anche Flask.

**Data dir in locale** (platformdirs):
| OS | Percorso |
|---|---|
| Windows | `%APPDATA%\TaskPlanner\TaskPlanner\` |
| macOS | `~/Library/Application Support/TaskPlanner/` |
| Linux | `~/.local/share/TaskPlanner/` |

Override con variabile d'ambiente: `TASKPLANNER_DATA=/mio/path python app_desktop.py`

### Build PyInstaller (bundle standalone)

```bash
pip install -r requirements/desktop.txt pillow
python desktop/make_icons.py      # genera desktop/icons/taskplanner.{png,ico,…}
pyinstaller taskplanner_desktop.spec
# Output: dist/TaskPlanner  (o dist/TaskPlanner.exe su Windows)
```

Le traduzioni (`translations/`) sono bundlate come dati; i template Python sono compilati nella PYZ.
`sys._MEIPASS` è il root di estrazione runtime — `factory.py` lo risolve automaticamente via `Path(__file__)`.

### Rilascio tramite GitHub Actions

> **IMPORTANTE** — Ogni modifica a `core/` o `translations/` deve essere seguita da un nuovo tag semver per aggiornare gli eseguibili desktop. Senza tag i file `.exe`/`.app`/binario Linux su GitHub rimangono alla versione precedente.

**Checklist rilascio desktop:**
1. Commit e push di tutte le modifiche su `master`
2. Aggiorna `**Versione corrente:**` in questo CLAUDE.md
3. Crea e pusha il tag:
```bash
git tag v1.X.Y
git push origin v1.X.Y
```
4. Il workflow `.github/workflows/desktop_release.yml` builda in parallelo Windows, macOS e Linux e crea automaticamente la GitHub Release con i tre eseguibili allegati.
5. Verifica su `github.com/doofie46-a11y/taskplanner/releases` che la release sia comparsa (~5-10 min).

**Regola versioning:** patch (`.Z`) per bugfix e traduzioni — minor (`.Y`) per nuove funzionalità.

### Dipendenze sistema pywebview

| OS | Backend | Note |
|---|---|---|
| Windows | WebView2 (Edge) | Preinstallato su Win 10 21H2+; versioni precedenti richiedono il runtime WebView2 |
| macOS | WebKit (WKWebView) | Nativo, nessuna dipendenza aggiuntiva |
| Linux | Qt/PySide6 (QtWebEngine) | Bundlato nell'eseguibile via pip (`qtpy` + `PySide6`), nessuna dipendenza di sistema. GTK+WebKit2GTK abbandonato: PyInstaller non riusciva a bundlare i binding `gi` (introspection dinamica) → eseguibile rotto su macchine senza `python3-gi`/`gir1.2-webkit2-*` installati |

---

## Regole architetturali (da rispettare in ogni fase)

- `core/` ha **zero import** da `psycopg2`, `authlib`, `win32com`
- Il DB viene iniettato via `app.config['DB_FACTORY']` dall'entrypoint
- Le route in `core/` usano `from core.db import get_db` — mai `psycopg2.connect()` direttamente
- Route registrate con pattern `register(app)` — **NO Flask Blueprints** (evita prefissi che romperebbero `url_for` nei template inline da 78k char)
- `CursorAdapter` normalizza automaticamente: `%s`→`?`, `RETURNING id`→`lastrowid`, `ON CONFLICT ... DO NOTHING`→`INSERT OR IGNORE`
- Per `NOW()` nelle UPDATE/INSERT usare `db.now_expr()` in f-string: `f"UPDATE ... SET ts={db.now_expr()}"`
- Path cross-platform: usare `pathlib.Path` e `os.path.join`, mai stringhe con `/` hardcoded
- Pomodoro timer: **rimosso** (non migrato — funzione non usata)
- Timezone default: `Europe/Rome`; configurabile via `app.config['TIMEZONE']`

---

## Schema del database

### `tasks`
| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER PK | |
| `titolo` | TEXT | |
| `data_prevista` | DATE | formato `YYYY-MM-DD` |
| `ora_prevista` | TEXT | formato `HH:MM` |
| `ricorrenza` | TEXT | `none` / `daily` / `every2days` / `weekly` / `every2weeks` / `monthly` / `monthly_first_monday` / `monthly_last_friday` |
| `ricorrenza_fine` | DATE | data fine ricorrenza (opzionale) |
| `ricorrenza_occorrenze` | INTEGER | numero massimo occorrenze (opzionale) |
| `posticipato_da` | DATE | data originale prima del primo rollover |
| `priorita` | TEXT | `Bassa` / `Media` / `Alta` / `Urgente` |
| `category_id` | INTEGER FK | → `categories.id` |
| `url` | TEXT | link opzionale |
| `escalation` | INTEGER | giorni per scalare priorità automaticamente |
| `pinned` | INTEGER | 0/1 |
| `note` | TEXT | |
| `card_color` | TEXT | colore HEX personalizzato |
| `created_at` | DATE | |
| `deleted_at` | TIMESTAMP | NULL = attivo; valorizzato = nel cestino |

### `categories`
`id`, `user_id`, `name`, `color` (HEX), `group_name`

### `task_completed`
`task_id`, `data_completata` (DATE), `tempo_impiegato` (minuti) — PK composta

### `rollover_history`
`id`, `task_id`, `from_date`, `to_date`, `moved_at`

### `attachments`
`id`, `task_id`, `stored_name`, `original_name`, `uploaded_at`

### `users` (server only)
`id`, `google_id`, `email`, `name`, `picture`, `api_key`, `created_at`

### `movement_categories` (Contaschei)
`id`, `user_id`, `name`, `type` (`income`/`expense`), `color` (HEX)

### `movements` (Contaschei)
| Colonna | Tipo | Note |
|---|---|---|
| `id` | INTEGER PK | |
| `user_id` | INTEGER FK | |
| `category_id` | INTEGER FK | → `movement_categories.id`, `ON DELETE SET NULL` |
| `tipo` | TEXT | `income` / `expense` — denormalizzato dalla categoria al momento del salvataggio |
| `amount` | NUMERIC(12,2) | |
| `date` | DATE | data origine del movimento |
| `ricorrenza` | TEXT | `none` / `daily` / `weekly` / `monthly` / `yearly` |
| `ricorrenza_fine` | DATE | opzionale |
| `ricorrenza_occorrenze` | INTEGER | opzionale |
| `note` | TEXT | |
| `created_at` | DATE | |

Nessun soft-delete: `DELETE` diretto (stesso pattern di `delete_category()`).

### `movement_exceptions` (Contaschei)
`id`, `movement_id` FK (`ON DELETE CASCADE`), `occurrence_date`, `action` (`skip`/`override`), `override_amount`, `override_note` — eccezione a una singola occorrenza di un movimento ricorrente, consultata da `_expand_recurring_movements()` prima di emettere ogni occorrenza.

---

## Route Flask

| Route | Metodo | Blueprint | Descrizione |
|---|---|---|---|
| `/` | GET | tasks | Vista giornaliera (`?date=YYYY-MM-DD`) |
| `/new` | GET | tasks | Form nuovo task |
| `/add` | POST | tasks | Salva nuovo task |
| `/edit/<tid>` | GET/POST | tasks | Modifica task |
| `/done/<tid>` | POST | tasks | Segna completato |
| `/posticipa/<tid>` | POST | tasks | Posticipa a domani |
| `/pin/<tid>` | POST | tasks | Toggle pin |
| `/delete/<tid>` | POST | tasks | Soft-delete (cestino) |
| `/cestino` | GET | cestino | Vista cestino |
| `/cestino/restore/<tid>` | POST | cestino | Ripristina |
| `/cestino/elimina/<tid>` | POST | cestino | Elimina definitivo |
| `/cestino/svuota` | POST | cestino | Svuota cestino |
| `/upload/<tid>` | POST | attachments | Upload allegato |
| `/download/<aid>` | GET | attachments | Download allegato |
| `/delete_attachment/<aid>` | POST | attachments | Elimina allegato |
| `/tasks_stato` | GET | api | JSON stato task |
| `/tasks_in_scadenza` | GET | api | JSON task in scadenza |
| `/add_from_mail` | POST | api | Crea task da macro VBA (api_key) |
| `/stats` | GET | stats | Statistiche |
| `/export` | GET/POST | export | Export CSV/JSON/TXT/MD |
| `/setup/categories` | GET/POST | setup | Gestione categorie |
| `/changelog` | GET | misc | Changelog |
| `/contaschei` | GET | contaschei | Dashboard movimenti mese corrente (`?edit=<mid>` per modificare la serie) |
| `/contaschei/add` | POST | contaschei | Crea movimento (singolo o ricorrente) |
| `/contaschei/edit/<mid>` | POST | contaschei | Modifica la serie |
| `/contaschei/delete/<mid>` | POST | contaschei | Elimina movimento (no soft-delete) |
| `/contaschei/exception/<mid>` | POST | contaschei | Crea/aggiorna eccezione occorrenza (`skip`/`override`) |
| `/contaschei/exception/<mid>/delete` | POST | contaschei | Rimuove eccezione, ripristina occorrenza originale |
| `/contaschei/categories` | GET | contaschei | Gestione tipologie movimento |
| `/contaschei/categories/add` | POST | contaschei | Crea tipologia |
| `/contaschei/categories/update/<cid>` | POST | contaschei | Aggiorna tipologia (blocca cambio `type` se ha movimenti collegati) |
| `/contaschei/categories/delete/<cid>` | POST | contaschei | Elimina tipologia (`category_id=NULL` sui movimenti collegati) |
| `/contaschei/bilancio` | GET | contaschei | Bilancio per periodo (mese/bimestre/trimestre/quadrimestre/semestre/anno), filtri tipo/tipologia |
| `/login` | GET | auth | Pagina login |
| `/logout` | POST | auth | Logout |
| `/auth/google/login` | GET | auth | (server only) Avvia OAuth |
| `/auth/google/callback` | GET | auth | (server only) Callback OAuth |
| `/outlook/crea_evento` | POST | outlook | (desktop only) Crea evento Outlook |
| `/outlook/crea_attivita` | POST | outlook | (desktop only) Crea attività Outlook |

---

## UX e interazioni frontend

### Doppio click sulle card
`ondblclick="cardDblClick(event, tid, selDate)"` su `.card`; ignora click su `a,button,input,label,form,textarea,select`.

### Drag & drop allegati
Supportato su card (vista giornaliera), form modifica e form nuovo task. Usa sempre `fetch POST /upload/<tid>` con `FormData` — mai `form.submit()`.

### Filtri e contatori sidebar
- Contatori per categoria aggiornati live da `updateFilters()` in JS
- Gruppi di categorie: click sull'header seleziona/deseleziona tutte; click sulla freccia espande/collassa
- Sezione "⚠️ Senza categoria" visibile solo se esistono task senza categoria

### Inoltro email da Outlook (macro VBA)
`POST /add_from_mail` con JSON `{titolo, note, data_prevista, api_key}` (o header `X-API-Key` al posto del campo nel body). Disponibile su server (HTTPS) e desktop (localhost).
La macro VBA non è più nel repo (rimossa il 2026-09-30: puntava a una porta fissa, incompatibile con la porta casuale del desktop); l'endpoint resta disponibile per client esterni.


### Contaschei — ottimizzazione mobile
Le pagine `core/templates/contaschei.py` hanno meta `viewport` dedicato e breakpoint `@media (max-width: 640px)`: header e form si impilano in colonna, le righe movimento (`.mv-row`) si riordinano in mini-card (data+importo in alto, tipologia e azioni su righe proprie con tap target più larghi), la tabella tipologie scrolla in orizzontale (`.table-wrap`), il grafico a barre del bilancio riduce le label.

---

## Logica di business chiave

### Rollover automatico
Task non completati con `data_prevista < oggi` e `ricorrenza = 'none'` vengono spostati a oggi alla prima visualizzazione della data corrente. Il primo `posticipato_da` viene preservato. Ogni spostamento è registrato in `rollover_history`.

### Escalation priorità
Se `escalation > 0` e `posticipato_da` è valorizzato, la priorità effettiva scala di un livello ogni `escalation` giorni di ritardo. `calcola_priorita_effettiva()` calcola senza modificare il DB.

### Ordinamento task
`(is_completed, is_pinned DESC, in_scadenza DESC, priorita, ora_prevista, -id)`

### Cestino (soft delete)
`deleted_at` valorizzato = task nel cestino. Cleanup automatico dopo 7 giorni (+ allegati su disco). `_daily_cleanup()` gira una volta al giorno per utente.

### Timezone
Default `Europe/Rome`; configurabile via `app.config['TIMEZONE']`. Usare sempre `datetime.now(app_tz).replace(tzinfo=None)` per confronti con orari task.

### Contaschei — movimenti ricorrenti ed eccezioni
Stesso modello "lazy" dei task: nessuna materializzazione, `_expand_recurring_movements()` (`core/logic.py`) calcola le occorrenze a runtime nel range richiesto, branch aggiuntivo `yearly` rispetto a `_expand_recurring`. Prima di emettere un'occorrenza controlla `movement_exceptions`: `skip` la salta, `override` ne sostituisce importo/nota. Nessun saldo cumulativo: solo flusso entrate/uscite nel periodo (`get_period_bounds()` calcola `date_from`/`date_to` per i 6 tipi di periodo, gestendo l'attraversamento di anno).

---

## Internazionalizzazione (Flask-Babel)

> **REGOLA OBBLIGATORIA** — Qualsiasi stringa visibile all'utente aggiunta o modificata **deve** essere avvolta in `{{ _("...") }}` nel template **e** tradotta in `translations/en/LC_MESSAGES/messages.po`. Non esistono eccezioni: testi di form, label, bottoni, popup JS (`confirm`, `prompt`, `alert`), notifiche, tooltip, messaggi di stato.

Le traduzioni sono gestite da **Flask-Babel 4.0**.

| Elemento | Dettaglio |
|---|---|
| Lingue supportate | `it` (default), `en` |
| Selezione lingua | `session['lang']` → `Accept-Language` header |
| Switch UI | Route `/lang/<code>` — bottoni IT / EN nella sidebar |
| Directory traduzioni | `translations/` (root progetto) |
| Config pybabel | `babel.cfg` |
| Compilazione | `pybabel compile -f -d translations` |
| Jinja2 | `{{ _("stringa") }}` — **virgolette doppie** (safe in stringhe Python single-quoted) |
| Stringhe con apostrofo | Usare `&#39;`: `_("dall&#39;export")` |

### Checklist per ogni nuova stringa

1. Nel template: `{{ _("testo") }}` con virgolette doppie
2. In `translations/en/LC_MESSAGES/messages.po`: aggiungi `msgid` + `msgstr`
3. Ricompila: `pybabel compile -f -d translations` (dalla root con venv attivo)

### Pattern per contesti specifici

**Template Jinja2** (stringa Python single-quoted — `\'` per apostrofi JS):
```
{{ _("Testo normale") }}
{{ _("Testo con apostrofo: dall&#39;export") }}
```

**Popup JS** (`confirm`, `prompt`, `alert`) — dentro onclick/onsubmit:
```
onsubmit="return confirm('{{ _("Testo conferma?") }}')"
onclick="if(confirm('{{ _("Eliminare?") }}')) ..."
let r = prompt('{{ _("Inserisci valore:") }}')
```
> I `\'` intorno al testo in stringhe Python single-quoted diventano `\'` in HTML; il `{{ _("...") }}` interno usa virgolette doppie.

**Popup JS nel file `outlook.js`** (servito statico, non processato da Jinja2):
Non usare `{{ _() }}` direttamente. Le traduzioni vanno iniettate tramite l'oggetto `window.OL_STRINGS` definito in `index.py` (già presente). Aggiungere lì la nuova chiave con `{{ _("...") }}` e referenziarla in `outlook.js` come `window.OL_STRINGS.nomeChiave`.

**Notifiche Chrome / `textContent` JS**:
```javascript
elemento.textContent = '{{ _("Testo") }}';   // Jinja2 processa prima del browser
```

Per aggiungere una nuova lingua:
1. `pybabel init -d translations -l <codice>`
2. Tradurre `translations/<codice>/LC_MESSAGES/messages.po`
3. `pybabel compile -f -d translations`

---

## Dipendenze Python

### Base (entrambi i target)
- `flask`, `flask-login`, `werkzeug`, `requests`

### Server only
- `psycopg2-binary`, `authlib`, `gunicorn`

### Desktop only
- `pyinstaller`, `pystray`
- `win32com` (stdlib Windows) — solo per integrazione Outlook, import condizionale

---

## Convenzioni di sviluppo

- I template sono inline come `render_template_string` — nessun file `.html` esterno
- Il DB è versionato implicitamente: `init_db()` usa `ADD COLUMN IF NOT EXISTS` (PG) o `try/except` (SQLite)
- Le date nel DB sono sempre `YYYY-MM-DD` (ISO 8601); i template usano il filtro Jinja `fmt_date` per mostrare `DD/MM/YYYY`
- Il codice è in italiano (commenti, nomi variabili, messaggi UI)
- Non esiste una test suite formale; testare manualmente su `http://127.0.0.1:5000`
- Path cross-platform: usare `pathlib.Path` e `os.path.join`, mai separatori hardcoded
