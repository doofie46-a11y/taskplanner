"""Template pagina informativa privacy (pubblica, nessun login richiesto)."""

from core.templates.contaschei import _CONTASCHEI_CSS, _THEME_SCRIPT, _THEME_TOGGLE_JS

TEMPLATE_PRIVACY = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ _("Informativa privacy") }} - TaskPlanner</title>
<style>''' + _CONTASCHEI_CSS + '''
.privacy-body h3 { font-size: 1rem; font-weight: 700; margin: 24px 0 8px 0; border-left: 3px solid var(--accent); padding-left: 10px; }
.privacy-body p  { margin-bottom: 10px; line-height: 1.65; font-size: 0.93rem; }
.privacy-body ul { margin: 6px 0 10px 20px; font-size: 0.93rem; line-height: 1.65; }
.privacy-body li { margin-bottom: 4px; }
.privacy-body a  { color: var(--accent); }
.privacy-intro   { font-size: 0.85rem; color: var(--muted); margin-bottom: 20px; }
</style>
</head>
<body>''' + _THEME_SCRIPT + '''
<div class="container" style="max-width: 720px;">
    <div class="page-header">
        <a href="/" class="btn-back">&larr; {{ _("Torna alla Home") }}</a>
        <h1>&#128274; {{ _("Informativa privacy") }}</h1>
    </div>

    <div class="section">
        <p class="privacy-intro">{{ _("Ultimo aggiornamento: giugno 2026") }}</p>

        <div class="privacy-body">

            <h3>1. {{ _("Titolare del trattamento") }}</h3>
            <p>{{ _("TaskPlanner è un&#39;applicazione ad uso privato. Per esercitare i diritti previsti dal GDPR o per qualsiasi richiesta relativa ai dati personali, è possibile contattare il titolare all&#39;indirizzo:") }} {% if privacy_contact %}<a href="mailto:{{ privacy_contact }}">{{ privacy_contact }}</a>{% endif %}</p>

            <h3>2. {{ _("Dati raccolti") }}</h3>
            {% if google_auth %}
            <p>{{ _("Al momento dell&#39;accesso tramite Google OAuth, l&#39;applicazione riceve e conserva i seguenti dati forniti da Google:") }}</p>
            <ul>
                <li>{{ _("Nome e cognome") }}</li>
                <li>{{ _("Indirizzo email") }}</li>
                <li>{{ _("Foto del profilo") }}</li>
            </ul>
            {% endif %}
            {% if local_auth %}
            <p>{{ _("Con l&#39;accesso tramite username e password, l&#39;applicazione conserva lo username, il nome visualizzato e la password, salvata solo come hash irreversibile e mai in chiaro.") }}</p>
            {% endif %}
            <p>{{ _("Non vengono raccolti dati sanitari, dati di geolocalizzazione o altri dati appartenenti a categorie particolari ai sensi dell&#39;art. 9 GDPR.") }}</p>

            <h3>3. {{ _("Finalità del trattamento") }}</h3>
            <p>{{ _("I dati vengono utilizzati esclusivamente per:") }}</p>
            <ul>
                <li>{{ _("Autenticazione: identificare l&#39;utente e consentire l&#39;accesso all&#39;applicazione") }}</li>
                <li>{{ _("Personalizzazione dell&#39;interfaccia (visualizzazione di nome e foto)") }}</li>
            </ul>

            <h3>4. {{ _("Base giuridica") }}</h3>
            <p>{{ _("Il trattamento è basato sul legittimo interesse del titolare a garantire un accesso sicuro e personalizzato all&#39;applicazione (art. 6.1.f GDPR).") }}</p>

            <h3>5. {{ _("Terze parti") }}</h3>
            {% if google_auth %}
            <p>{{ _("L&#39;autenticazione è gestita tramite Google OAuth (Google LLC). Durante il processo di login, Google tratta i dati secondo la propria informativa:") }} <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">policies.google.com/privacy</a></p>
            {% endif %}
            <p>{{ _("TaskPlanner non condivide dati personali con altre terze parti.") }}</p>

            <h3>6. {{ _("Conservazione dei dati") }}</h3>
            <p>{{ _("I dati vengono conservati finché l&#39;utente mantiene un accesso attivo all&#39;applicazione. È possibile richiedere la cancellazione dell&#39;account e di tutti i dati associati contattando il titolare.") }}</p>

            <h3>7. {{ _("Cookie") }}</h3>
            <p>{{ _("L&#39;applicazione utilizza esclusivamente un cookie tecnico di sessione, necessario per mantenere l&#39;utente autenticato tra una pagina e l&#39;altra. Non vengono utilizzati cookie di profilazione, tracking o advertising.") }}</p>
            <p>{{ _("I cookie tecnici necessari sono esenti dall&#39;obbligo di consenso ai sensi della direttiva ePrivacy e del Provvedimento del Garante Privacy dell&#39;8 maggio 2014.") }}</p>

            <h3>8. {{ _("Diritti dell&#39;interessato") }}</h3>
            <p>{{ _("In base agli articoli 15–22 del GDPR, l&#39;utente ha diritto di:") }}</p>
            <ul>
                <li>{{ _("Accedere ai propri dati (art. 15)") }}</li>
                <li>{{ _("Richiederne la rettifica (art. 16)") }}</li>
                <li>{{ _("Ottenerne la cancellazione (art. 17)") }}</li>
                <li>{{ _("Limitarne il trattamento (art. 18)") }}</li>
                <li>{{ _("Richiedere la portabilità dei dati (art. 20)") }}</li>
                <li>{{ _("Opporsi al trattamento (art. 21)") }}</li>
            </ul>
            {% if privacy_contact %}<p>{{ _("Per esercitare questi diritti, scrivere a:") }} <a href="mailto:{{ privacy_contact }}">{{ privacy_contact }}</a></p>{% endif %}
            <p>{{ _("È inoltre possibile presentare reclamo al Garante per la protezione dei dati personali:") }} <a href="https://www.garanteprivacy.it" target="_blank" rel="noopener">www.garanteprivacy.it</a></p>

        </div>
    </div>
</div>''' + _THEME_TOGGLE_JS + '''
</body>
</html>
'''
