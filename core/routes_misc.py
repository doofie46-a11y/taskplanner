"""Route miscellanee: asset statici, PWA, changelog."""
import os

from flask import Response, current_app, json as _json
from flask_login import login_required

from core.templates import _OUTLOOK_JS, TEMPLATE_CHANGELOG, TEMPLATE_PRIVACY
from core.templates.calendar import _CALENDAR_JS


CHANGELOG = [
    {
        "version": "1.5.0",
        "codename": "Aglianico",
        "date": "2026-09-10",
        "notes": [
            "🔍 Contaschei: ricerca movimenti anche per descrizione (nota e tipologia)",
            "📋 Contaschei: pulsante duplica movimento — riapre la maschera precompilata con data odierna, modificabile prima di salvare",
        ]
    },
    {
        "version": "1.4.5",
        "codename": "Vermentino",
        "date": "2026-08-22",
        "notes": [
            "🐧 Fix eseguibile Linux: backend finestra passato da GTK+WebKit2GTK a Qt/PySide6 — l'eseguibile standalone non partiva su macchine senza i binding gi/GTK installati",
        ]
    },
    {
        "version": "1.4.4",
        "codename": "Cannonau",
        "date": "2026-07-18",
        "notes": [
            "💰 Contaschei: filtri movimenti per tipo e tipologia",
            "🔍 Filtri movimenti in modale richiamabile con tasto Filtri",
            "🔢 Badge sul tasto Filtri con contatore filtri attivi",
        ]
    },
    {
        "version": "1.4.3",
        "codename": "Syrah",
        "date": "2026-05-25",
        "notes": [
            "🖥️ Launcher desktop riscritto con pywebview: finestra nativa senza browser esterno",
            "🔌 Porta localhost casuale (socket) per evitare conflitti tra istanze",
            "📁 Data dir cross-platform via platformdirs (%APPDATA%, ~/Library, ~/.local/share)",
            "📦 Spec PyInstaller one-file con bundle traduzioni e icone cross-platform",
            "🚀 GitHub Actions: build automatico Win/macOS/Linux su tag v*.*.* con GitHub Release",
        ]
    },
    {
        "version": "1.4.0",
        "codename": "Syrah",
        "date": "2026-05-25",
        "notes": [
            "🌍 Internazionalizzazione (i18n): interfaccia disponibile in italiano e inglese",
            "🔤 Switch lingua IT/EN nella sidebar con memorizzazione in sessione",
            "🔔 Notifiche Chrome tradotte (titolo 'Tasks due' in inglese)",
            "🌑 Pulsante dark/light mode tradotto",
            "💬 Tutti i popup (confirm, prompt, alert) tradotti in entrambe le lingue",
            "🗑️ Cestino: avviso automatico eliminazione dopo 7 giorni",
            "🏗️ Migrazione architettura shared-core: logica comune in `core/`, adapter separati per server (PostgreSQL + OAuth) e desktop (SQLite)",
        ]
    },
    {
        "version": "1.3.0",
        "codename": "Primitivo",
        "date": "2026-05-24",
        "notes": [
            "🗂️ Gruppi di categorie: assegna le categorie a gruppi in Gestione Categorie",
            "⚡ Selezioni rapide nel sidebar: clic sul gruppo per selezionare/deselezionare tutte le sue categorie",
            "🔢 Contatori live accanto a ogni categoria e gruppo, aggiornati in base ai filtri attivi",
            "⚠️ Indicatore anomalia 'Senza categoria' nel sidebar con badge rosso",
        ]
    },
    {
        "version": "1.2.1",
        "codename": "Nebbiolo",
        "date": "2026-05-24",
        "notes": [
            "🗑️ Cestino: i task eliminati sono recuperabili per 7 giorni prima della cancellazione definitiva",
            "🧹 Pulizia automatica: allegati dei task completati da più di 7 giorni rimossi dal disco",
            "📎 Fix upload allegati: rimosso limite 1 MB (ora 20 MB) — fix errore 413 nginx",
        ]
    },
    {
        "version": "1.2.0",
        "codename": "Nebbiolo",
        "date": "2026-05-24",
        "notes": [
            "🔐 Autenticazione Google OAuth — accesso sicuro con account Google",
            "🗄️ Migrazione database da SQLite a PostgreSQL",
            "📱 Interfaccia mobile-responsive con sidebar a cassetto hamburger",
            "📲 Supporto PWA — installabile come app su smartphone (Android e iOS)",
            "📋 Form nuovo task e modifica adattate per smartphone",
            "🔔 Fix notifiche in scadenza su PWA Android tramite Service Worker",
            "🎨 Fix tema scuro e filtri: non più visibili al caricamento (FOUC rimosso)",
        ]
    },
    {
        "version": "1.1.8",
        "codename": "Barolo",
        "date": "2026-04-30",
        "notes": [
            "🌡️ Fix caratteri invalidi su inoltra a Taskplanner",
        ]
    },
    {
        "version": "1.1.7",
        "codename": "Barolo",
        "date": "2026-04-28",
        "notes": [
            "📨 Inoltra a Taskplanner da Outlook",
            "📝 Modifica Task con doppio click",
            "↩️ Drag and Drop allegati",
        ]
    },
    {
        "version": "1.1.6",
        "codename": "Teroldego",
        "date": "2026-04-15",
        "notes": [
            "👯 Implementazioni sulla copia dei task",
            "📝 Memorizzata in sessione data di consultazione",
        ]
    },
    {
        "version": "1.1.5",
        "codename": "Amarone",
        "date": "2026-03-24",
        "notes": [
            "🔗 Aggiunto sync del database con Github",
            "📱 Prevista versione mobile per inserimento e completamento task da remoto",
        ]
    },
    {
        "version": "1.1.4",
        "codename": "Dolcetto d'Alba",
        "date": "2026-03-19",
        "notes": [
            "🔗 Fix Copia task: riporta URL e propone di copiare anche gli allegati",
            "🕓 Fix attività Outlook: ReminderTime impostato con orario del task (default 09:00)",
            "📎 Export: filtro 'Solo task con allegati' e colonna Allegati",
            "🗂️ Sidebar: sezioni Stato/Priorità/Categorie collassabili con memoria di sessione",
            "📌 Task fissati in cima: pin/unpin dalla card",
            "📝 Note libere per task: collassate sulla card, espandibili con click",
            "🎨 Colore bordo card personalizzabile per task",
        ]
    },
    {
        "version": "1.1.3",
        "codename": "Barbera",
        "date": "2026-03-09",
        "notes": [
            "⏫ Escalation automatica priorità",
            "🏷️ Badge ⏫ visivo sulla card con tooltip",
            "📝 Nuovo campo 'Escalation (giorni)' nel form",
            "✨ Maschere inserimento e modifica task ridisegnate",
            "🎨 Gestione Categorie: modifica inline",
        ]
    },
    {
        "version": "1.1.2",
        "codename": "Grignolino",
        "date": "2026-03-06",
        "notes": [
            "📆 Creazione eventi e attività su Outlook",
            "✨ Sezione Export nella sidebar",
            "🔁 I task ricorrenti vengono espansi nelle giornate previste",
        ]
    },
    {
        "version": "1.1.1",
        "codename": "Grignolino",
        "date": "2026-03-05",
        "notes": [
            "🎉 Prima release pubblica stabile",
            "📊 Statistiche avanzate",
            "🔔 Notifiche browser per task in scadenza",
            "📎 Allegati ai task",
            "🌙 Dark mode persistente",
        ]
    },
]


def register(app):
    from flask import send_from_directory

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            current_app.config['BUNDLE_DIR'],
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )

    @app.route("/manifest.json")
    def pwa_manifest():
        manifest = {
            "name": "TaskPlanner",
            "short_name": "TaskPlanner",
            "description": "Gestione task quotidiana",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#f0f4f8",
            "theme_color": "#007bff",
            "orientation": "portrait-primary",
            "icons": [
                {"src": "/pwa-icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
                {"src": "/pwa-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            ],
        }
        return Response(_json.dumps(manifest), mimetype="application/manifest+json")

    @app.route("/sw.js")
    def pwa_sw():
        sw = r"""
const CACHE = 'tp-v1';
const STATIC = ['/manifest.json', '/pwa-icon-192.png', '/pwa-icon-512.png', '/favicon.ico'];
self.addEventListener('install', e => {
    e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
    self.skipWaiting();
});
self.addEventListener('activate', e => {
    e.waitUntil(caches.keys().then(ks =>
        Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ));
    self.clients.claim();
});
self.addEventListener('fetch', e => {
    if (e.request.method !== 'GET') return;
    const u = new URL(e.request.url);
    if (u.origin !== location.origin) return;
    if (!u.pathname.match(/\.(png|ico|json)$/)) return;
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
self.addEventListener('notificationclick', e => {
    e.notification.close();
    e.waitUntil(
        clients.matchAll({type: 'window', includeUncontrolled: true}).then(cs => {
            for (const c of cs) {
                if (c.url.startsWith(self.registration.scope) && 'focus' in c) return c.focus();
            }
            return clients.openWindow('/');
        })
    );
});
"""
        return Response(sw, mimetype="application/javascript")

    @app.route("/pwa-icon-192.png")
    def pwa_icon_192():
        return send_from_directory(
            os.path.join(current_app.config['BUNDLE_DIR'], "taskplanner-pwa"),
            "icon-192.png", mimetype="image/png",
        )

    @app.route("/pwa-icon-512.png")
    def pwa_icon_512():
        return send_from_directory(
            os.path.join(current_app.config['BUNDLE_DIR'], "taskplanner-pwa"),
            "icon-512.png", mimetype="image/png",
        )

    @app.route("/outlook.js")
    def outlook_js():
        return Response(_OUTLOOK_JS, mimetype="application/javascript")

    @app.route("/calendar.js")
    def calendar_js():
        return Response(_CALENDAR_JS, mimetype="application/javascript")

    @app.route("/privacy")
    def privacy():
        from flask import render_template_string
        return render_template_string(
            TEMPLATE_PRIVACY,
            privacy_contact=current_app.config.get('PRIVACY_CONTACT_EMAIL', ''),
        )

    @app.route("/changelog")
    @login_required
    def changelog():
        from flask import render_template_string
        return render_template_string(
            TEMPLATE_CHANGELOG,
            changelog=CHANGELOG,
            app_version=current_app.config['APP_VERSION'],
            app_codename=current_app.config['APP_CODENAME'],
        )
