"""
TEMPLATE_API: pagina "API e integrazioni" (solo server, route in server/api_keys.py).
Chiavi API dell'utente (create, rigenerate, revocate) e istruzioni per /api/tasks.
"""

TEMPLATE_API = r'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>TaskPlanner — {{ _("API e integrazioni") }}</title>
<style>
    :root { --bg: #f0f4f8; --card: #fff; --text: #222; --muted: #666; --border: #e3e6ea;
            --accent: #007bff; --danger: #dc3545; --code: #f5f7fa; }
    body.dark { --bg: #151821; --card: #1f2430; --text: #f5f5f5; --muted: #aaa; --border: #3a3f4b;
                --accent: #4da3ff; --danger: #ff6b6b; --code: #2a3040; }
    * { box-sizing: border-box; }
    body { font-family: Arial, sans-serif; margin: 0; background: var(--bg); color: var(--text); line-height: 1.45; }
    .container { max-width: 820px; margin: 32px auto; background: var(--card); padding: 24px;
                 border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .page-header { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; flex-wrap: wrap; }
    .page-header h1 { margin: 0; font-size: 1.5rem; }
    .btn-back { padding: 7px 16px; border-radius: 7px; border: 1px solid #ccc; background: transparent; color: var(--text);
                font-size: 0.88rem; text-decoration: none; }
    .btn-back:hover { background: var(--border); }
    h2 { font-size: 1.15rem; margin: 30px 0 10px; padding-top: 18px; border-top: 1px solid var(--border); }
    p, li { font-size: 0.93rem; }
    .muted { color: var(--muted); font-size: 0.85rem; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--border); vertical-align: top; }
    th { font-size: 0.8rem; color: var(--muted); }
    code, pre { font-family: Consolas, "Courier New", monospace; background: var(--code); border-radius: 5px; }
    code { padding: 1px 5px; font-size: 0.85rem; }
    pre { padding: 12px; overflow-x: auto; font-size: 0.82rem; white-space: pre; margin: 6px 0 0; }
    button, .btn { padding: 7px 14px; cursor: pointer; background: var(--accent); color: #fff; border: none;
                   border-radius: 6px; font-size: 0.88rem; }
    button.secondary { background: transparent; color: var(--accent); border: 1px solid var(--accent); }
    button.danger { background: transparent; color: var(--danger); border: 1px solid var(--danger); }
    input[type="text"] { padding: 8px; border: 1px solid #ccc; border-radius: 6px; font-size: 0.95rem;
                         background: var(--card); color: var(--text); }
    .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .row input[type="text"] { flex: 1; min-width: 200px; }
    .box { border-radius: 8px; padding: 12px 14px; margin: 12px 0; font-size: 0.92rem; }
    .box-ok { background: #e8f5e9; border: 1px solid #a5d6a7; }
    .box-warn { background: #fff8e1; border: 1px solid #ffe082; }
    .box-err { background: #fdecea; border: 1px solid #f5c2c0; color: #b3261e; }
    body.dark .box-ok { background: #1e3a24; border-color: #2e6b3a; }
    body.dark .box-warn { background: #3d3418; border-color: #6b5a1e; }
    body.dark .box-err { background: #4a1f1f; border-color: #7a2e2e; color: #ffb4ab; }
    .newkey { font-family: Consolas, "Courier New", monospace; font-size: 0.95rem; }
    details { border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; margin: 10px 0; }
    summary { cursor: pointer; font-weight: 600; }
    details ol, details ul { padding-left: 20px; }
    .actions form { display: inline; }
    @media (max-width: 640px) {
        .container { margin: 0; border-radius: 0; padding: 16px; }
        .keys thead { display: none; }
        .keys tr { display: block; padding: 8px 0; border-bottom: 1px solid var(--border); }
        .keys td { display: block; border: none; padding: 2px 0; }
        .keys td.actions { padding-top: 6px; }
    }
</style>
</head>
<body>
<script>
    if (localStorage.getItem('taskplanner_theme') === 'dark') document.body.classList.add('dark');
</script>
<div class="container">
    <div class="page-header">
        <a href="/" class="btn-back">← {{ _("Torna alla Home") }}</a>
        <h1>🔌 {{ _("API e integrazioni") }}</h1>
    </div>

    <p>{{ _("Con una chiave API puoi creare task da altre app: Outlook, le scorciatoie dello smartphone, script e servizi di automazione.") }}
       {{ _("La chiave permette solo di creare task: non può leggere, modificare o cancellare quelli che hai già.") }}</p>

    {% if error %}<div class="box box-err">{{ error }}</div>{% endif %}

    {% if new_key %}
    <div class="box box-ok">
        <strong>{{ _("Ecco la chiave «%(name)s».", name=new_key_name) }}</strong>
        {{ _("Copiala adesso e incollala nell'app che la userà: per sicurezza non verrà più mostrata. Se la perdi, rigenerala.") }}
        <div class="row" style="margin-top:10px;">
            <input type="text" id="new-key" class="newkey" value="{{ new_key }}" readonly autocomplete="off" spellcheck="false" onclick="this.select()">
            <button type="button" onclick="copyText('new-key', this)">📋 {{ _("Copia") }}</button>
        </div>
    </div>
    {% endif %}

    <h2>🔑 {{ _("Le tue chiavi") }}</h2>
    {% if keys %}
    <table class="keys">
        <thead><tr><th>{{ _("Nome") }}</th><th>{{ _("Chiave") }}</th><th>{{ _("Creata") }}</th><th>{{ _("Ultimo utilizzo") }}</th><th></th></tr></thead>
        <tbody>
        {% for k in keys %}
        <tr>
            <td><strong>{{ k.name }}</strong></td>
            <td><code>…{{ k.hint }}</code></td>
            <td>{{ k.created or "—" }}</td>
            <td>{{ k.last_used or _("Mai") }}</td>
            <td class="actions">
                <form method="post" action="/account/api/{{ k.id }}/regenerate" onsubmit='return confirm({{ _("Rigenerare la chiave? Quella attuale smetterà subito di funzionare e dovrai aggiornarla nell'app che la usa.")|tojson }})'>
                    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                    <button type="submit" class="secondary">🔄 {{ _("Rigenera") }}</button>
                </form>
                <form method="post" action="/account/api/{{ k.id }}/delete" onsubmit='return confirm({{ _("Revocare la chiave? Le app che la usano non potranno più creare task.")|tojson }})'>
                    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                    <button type="submit" class="danger">🗑️ {{ _("Revoca") }}</button>
                </form>
            </td>
        </tr>
        {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p class="muted">{{ _("Non hai ancora nessuna chiave.") }}</p>
    {% endif %}

    {% if keys|length < max_keys %}
    <form method="post" action="/account/api/create" style="margin-top:14px;">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <div class="row">
            <input type="text" name="name" maxlength="{{ max_name_len }}" required placeholder="{{ _("Nome della chiave, es. Telefono o Outlook ufficio") }}">
            <button type="submit">➕ {{ _("Crea chiave") }}</button>
        </div>
    </form>
    {% else %}
    <p class="muted">{{ _("Hai raggiunto il massimo di %(n)s chiavi.", n=max_keys) }}</p>
    {% endif %}
    <p class="muted">💡 {{ _("Usa una chiave diversa per ogni dispositivo o app: se ne perdi uno, revochi solo quella e le altre continuano a funzionare.") }}</p>

    <h2>🛡️ {{ _("Sicurezza") }}</h2>
    <ul>
        <li>{{ _("Tratta la chiave come una password: chi la conosce può creare task a tuo nome.") }}</li>
        <li>{{ _("Mandala sempre nell'intestazione X-API-Key, mai nell'indirizzo: gli indirizzi finiscono nei log e nella cronologia.") }}</li>
        <li>{{ _("Non condividerla in screenshot, chat o macro che dai ad altri.") }}</li>
        <li>{{ _("Se perdi un dispositivo o pensi che la chiave sia stata vista, revocala o rigenerala qui.") }}</li>
        <li>{{ _("Controlla ogni tanto la colonna «Ultimo utilizzo»: se una chiave risulta usata quando non l'hai fatto tu, revocala.") }}</li>
    </ul>

    <h2>📡 {{ _("Come funziona") }}</h2>
    {% if not is_https %}
    <div class="box box-warn">⚠️ {{ _("Questo indirizzo non usa HTTPS: la chiave viaggerebbe in chiaro. Usa l'API solo dietro HTTPS.") }}</div>
    {% endif %}
    <p>{{ _("Invia una richiesta POST con un corpo JSON a questo indirizzo:") }}</p>
    <div class="row">
        <input type="text" id="endpoint" value="{{ endpoint }}" readonly onclick="this.select()">
        <button type="button" class="secondary" onclick="copyText('endpoint', this)">📋 {{ _("Copia") }}</button>
    </div>
    <p>{{ _("Intestazioni della richiesta:") }}</p>
    <pre>X-API-Key: {{ _("LA_TUA_CHIAVE") }}
Content-Type: application/json</pre>
    <p class="muted">{{ _("In alternativa a X-API-Key è accettata anche l'intestazione Authorization: Bearer LA_TUA_CHIAVE. Il vecchio indirizzo /add_from_mail continua a funzionare.") }}</p>

    <p>{{ _("Campi del JSON (solo il titolo è obbligatorio):") }}</p>
    <table>
        <thead><tr><th>{{ _("Campo") }}</th><th>{{ _("Valore") }}</th><th>{{ _("Se manca") }}</th></tr></thead>
        <tbody>
            <tr><td><code>titolo</code></td><td>{{ _("Testo, al massimo 500 caratteri") }}</td><td>{{ _("obbligatorio") }}</td></tr>
            <tr><td><code>note</code></td><td>{{ _("Testo, senza limiti di lunghezza") }}</td><td>{{ _("nessuna nota") }}</td></tr>
            <tr><td><code>data_prevista</code></td><td><code>2026-12-31</code>, <code>today</code>/<code>oggi</code>, <code>tomorrow</code>/<code>domani</code>, <code>+3</code> ({{ _("tra 3 giorni") }})</td><td>{{ _("oggi") }}</td></tr>
            <tr><td><code>ora</code></td><td>{{ _("Orario HH:MM, es. 09:30") }}</td><td>{{ _("nessun orario") }}</td></tr>
            <tr><td><code>priorita</code></td><td><code>Bassa</code>, <code>Media</code>, <code>Alta</code>, <code>Urgente</code> ({{ _("anche in inglese: Low, Medium, High, Urgent") }})</td><td><code>Media</code></td></tr>
            <tr><td><code>categoria</code></td><td>{{ _("Nome di una tua categoria, maiuscole e minuscole indifferenti") }}</td><td>{{ _("senza categoria") }}</td></tr>
            <tr><td><code>url</code></td><td>{{ _("Link che inizia con http:// o https://") }}</td><td>{{ _("nessun link") }}</td></tr>
        </tbody>
    </table>
    <p>{{ _("Risposta se il task è stato creato:") }}</p>
    <pre>{"ok": true, "task_id": 123, "titolo": "...", "data_prevista": "2026-10-17", ...}</pre>
    <p>{{ _("Se un dato è sbagliato il task non viene creato e la risposta (in inglese) dice quale campo correggere:") }}</p>
    <pre>{"ok": false, "field": "categoria", "error": "Category 'Lavro' not found. Your categories: Generale, Lavoro"}</pre>

    <h2>💡 {{ _("Esempi e idee") }}</h2>

    <details>
        <summary>📱 HTTP Shortcuts (Android)</summary>
        <p>{{ _("Configurazione base, da fare una volta:") }}</p>
        <ol>
            <li>{{ _("Menu ⋮ → Variabili → + → Costante: nome api_key, valore la tua chiave. Quando la rigeneri, la cambi solo qui.") }}</li>
            <li>{{ _("Nuova scorciatoia → Richiesta HTTP normale: metodo POST, indirizzo quello indicato sopra.") }}</li>
            <li>{{ _("Intestazioni della richiesta → aggiungi X-API-Key con valore {api_key} (scegli la variabile con l'icona {}).") }}</li>
            <li>{{ _("Corpo della richiesta → JSON (application/json), per esempio:") }}<pre>{"titolo": "{titolo}", "data_prevista": "domani"}</pre></li>
            <li>{{ _("Per far chiedere il titolo a ogni avvio, crea una variabile titolo di tipo Testo.") }}</li>
            <li>{{ _("Gestione risposta → mostra la risposta in una finestra: vedi subito se il task è stato creato o cosa correggere.") }}</li>
        </ol>
        <p>{{ _("Idee:") }}</p>
        <ul>
            <li><strong>{{ _("Condividi con TaskPlanner") }}</strong>: {{ _("nelle impostazioni della scorciatoia attiva la ricezione di testo condiviso. Da Chrome, YouTube, Gmail o WhatsApp scegli Condividi → la scorciatoia: il link o il testo diventano un task (mettilo in url o in titolo).") }}</li>
            <li><strong>{{ _("Dettatura") }}</strong>: {{ _("con la variabile di tipo Testo usa il microfono della tastiera: parli e il task viene creato.") }}</li>
            <li><strong>{{ _("Widget sulla home") }}</strong>: {{ _("aggiungi la scorciatoia come widget, ad esempio «Task per domani» con data_prevista impostata a domani.") }}</li>
            <li><strong>{{ _("Promemoria veloci") }}</strong>: {{ _("una scorciatoia per ogni categoria, con categoria e priorità già impostate.") }}</li>
        </ul>
    </details>

    <details>
        <summary>🍎 {{ _("Comandi rapidi (iPhone, iPad, Mac)") }}</summary>
        <ol>
            <li>{{ _("Nuovo comando → azione «Chiedi input» (testo) per il titolo.") }}</li>
            <li>{{ _("Azione «Ottieni contenuti dell'URL»: indirizzo quello indicato sopra, metodo POST.") }}</li>
            <li>{{ _("Intestazioni: X-API-Key con la tua chiave. Corpo della richiesta: JSON, campo titolo = Input fornito.") }}</li>
            <li>{{ _("Aggiungi «Mostra risultato» per vedere la risposta.") }}</li>
        </ol>
        <p>{{ _("Attivando «Mostra nel foglio di condivisione» puoi creare task da Safari o da altre app, come su Android.") }}</p>
    </details>

    <details>
        <summary>✉️ {{ _("Outlook (macro VBA)") }}</summary>
        <p>{{ _("Crea un task dall'email selezionata: oggetto come titolo, testo come note. In Outlook: Alt+F11, inserisci un modulo, incolla il codice e metti la tua chiave in TP_KEY. Poi aggiungi la macro alla barra multifunzione.") }}</p>
<pre>Const TP_URL = "{{ endpoint }}"
Const TP_KEY = "{{ _("LA_TUA_CHIAVE") }}"

Sub InviaATaskPlanner()
    Dim m As Object, http As Object, body As String
    Set m = Application.ActiveExplorer.Selection.Item(1)
    body = "{""titolo"":""" &amp; JsonEsc(Left(m.Subject, 500)) &amp; """," &amp; _
           """note"":""" &amp; JsonEsc(m.Body) &amp; """}"
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.Open "POST", TP_URL, False
    http.setRequestHeader "Content-Type", "application/json; charset=utf-8"
    http.setRequestHeader "X-API-Key", TP_KEY
    http.send body
    MsgBox http.responseText
End Sub

Function JsonEsc(ByVal s As String) As String
    s = Replace(s, "\", "\\")
    s = Replace(s, """", "\""")
    s = Replace(s, vbCrLf, "\n")
    s = Replace(s, vbCr, "\n")
    s = Replace(s, vbLf, "\n")
    s = Replace(s, vbTab, "\t")
    JsonEsc = s
End Function</pre>
    </details>

    <details>
        <summary>💻 {{ _("curl e PowerShell") }}</summary>
<pre>curl -X POST "{{ endpoint }}" \
  -H "X-API-Key: {{ _("LA_TUA_CHIAVE") }}" \
  -H "Content-Type: application/json" \
  -d '{"titolo": "{{ _("Chiamare il dentista") }}", "data_prevista": "tomorrow", "ora": "09:30", "priorita": "Alta"}'</pre>
<pre>$body = @{ titolo = "{{ _("Chiamare il dentista") }}"; data_prevista = "tomorrow"; priorita = "Alta" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "{{ endpoint }}" `
  -Headers @{ "X-API-Key" = "{{ _("LA_TUA_CHIAVE") }}" } `
  -ContentType "application/json; charset=utf-8" `
  -Body ([Text.Encoding]::UTF8.GetBytes($body))</pre>
        <p class="muted">{{ _("Utile anche negli script programmati: per esempio un task «Backup fallito» quando un backup non va a buon fine.") }}</p>
    </details>

    <details>
        <summary>🤖 {{ _("Altre idee") }}</summary>
        <ul>
            <li><strong>Tasker</strong> (Android): {{ _("azione HTTP Request, per esempio un task quando arrivi in ufficio o quando la batteria è carica.") }}</li>
            <li><strong>Home Assistant</strong>: {{ _("un rest_command richiamato da un'automazione, per esempio «Lavatrice finita, stendere».") }}</li>
            <li><strong>n8n, Zapier, IFTTT, Make</strong>: {{ _("un'azione webhook per creare task da moduli, calendari, feed RSS o email filtrate.") }}</li>
        </ul>
    </details>
</div>
<script>
function copyText(id, btn) {
    var el = document.getElementById(id);
    var done = function () {
        var old = btn.textContent;
        btn.textContent = {{ _("✔ Copiato")|tojson }};
        setTimeout(function () { btn.textContent = old; }, 1500);
    };
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(el.value).then(done);
    } else {
        el.select();
        document.execCommand('copy');
        done();
    }
}
</script>
</body>
</html>
'''
