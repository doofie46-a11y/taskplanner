"""
Template Contaschei: dashboard movimenti, gestione tipologie, bilancio per periodo.
"""

_CONTASCHEI_CSS = """
:root {
    --bg: #f0f4f8; --card: #fff; --text: #222; --muted: #666;
    --border: #ddd; --accent: #007bff; --success: #28a745;
    --warning: #ff9800; --danger: #dc3545;
}
body.dark {
    --bg: #151821; --card: #1f2430; --text: #f5f5f5; --muted: #aaa;
    --border: #3a3f4b; --accent: #4da3ff; --success: #4cd964;
    --warning: #ffc94a; --danger: #ff6b6b;
}
* { box-sizing: border-box; }
body { font-family: Arial, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; }
.container { max-width: 960px; margin: 30px auto; padding: 0 20px; }
h1 { margin-bottom: 6px; }
.btn-back { padding: 7px 16px; border-radius: 7px; border: 1px solid var(--border); background: transparent; color: var(--text); cursor: pointer; font-size: 0.88rem; text-decoration: none; display: inline-flex; align-items: center; gap: 5px; transition: background .15s; }
.btn-back:hover { background: var(--border); }
.page-header { display: flex; align-items: center; gap: 14px; margin-bottom: 24px; flex-wrap: wrap; }
.page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; }
.page-nav { display: flex; gap: 8px; margin-left: auto; }
.page-nav a { padding: 7px 14px; border-radius: 7px; border: 1px solid var(--border); background: transparent; color: var(--text); text-decoration: none; font-size: 0.85rem; }
.page-nav a:hover { background: var(--border); }
#darkToggle { padding: 5px 10px; border-radius: 20px; border: 1px solid var(--border); background-color: transparent; color: var(--text); cursor: pointer; font-size: 0.8rem; }
#darkToggle:hover { background-color: var(--accent); color: #fff; }

.kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 20px 0; }
@media (max-width: 700px) { .kpi-grid { grid-template-columns: 1fr; } }
.kpi-card { background: var(--card); border-radius: 10px; padding: 18px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; border-top: 4px solid var(--accent); }
.kpi-card.green { border-top-color: var(--success); }
.kpi-card.red   { border-top-color: var(--danger); }
.kpi-label { font-size: 0.78rem; color: var(--muted); margin-bottom: 6px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.04em; }
.kpi-value { font-size: 1.9rem; font-weight: bold; line-height: 1; }

.section { background: var(--card); border-radius: 10px; padding: 18px 20px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.section h2 { margin: 0 0 14px 0; font-size: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 8px; }

.form-grid { display: flex; flex-wrap: wrap; gap: 14px; align-items: flex-end; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-size: 0.78rem; font-weight: bold; color: var(--muted); }
.field input, .field select, .field textarea { padding: 7px 9px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font-size: 0.88rem; }
.ric-fine-block { display: flex; gap: 14px; margin-top: 10px; }
.btn-primary { padding: 9px 18px; background: var(--accent); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.btn-primary:hover { opacity: 0.85; }
.tipo-toggle { display: flex; gap: 6px; }
.tipo-toggle label { padding: 7px 14px; border: 1px solid var(--border); border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.tipo-toggle input { display: none; }
.tipo-toggle input:checked + span { font-weight: bold; }
.tipo-toggle .opt-income.checked, .tipo-toggle label:has(input:checked).opt-income { background: var(--success); color: #fff; border-color: var(--success); }
.tipo-toggle label:has(input:checked).opt-expense { background: var(--danger); color: #fff; border-color: var(--danger); }

.mv-row { display: flex; align-items: center; gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.mv-row:last-child { border-bottom: none; }
.mv-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.mv-date { width: 90px; font-size: 0.82rem; color: var(--muted); flex-shrink: 0; }
.mv-cat { flex: 1; min-width: 120px; font-size: 0.88rem; }
.mv-note { font-size: 0.78rem; color: var(--muted); }
.mv-amount { font-weight: bold; font-size: 0.95rem; width: 110px; text-align: right; flex-shrink: 0; }
.mv-amount.income { color: var(--success); }
.mv-amount.expense { color: var(--danger); }
.mv-badge { font-size: 0.7rem; padding: 1px 6px; border-radius: 10px; background: var(--border); color: var(--muted); }
.mv-actions { display: flex; gap: 4px; flex-shrink: 0; }
.mv-actions button, .mv-actions a { background: transparent; border: none; cursor: pointer; font-size: 0.95rem; padding: 2px 4px; color: var(--text); text-decoration: none; }
.empty-msg { text-align: center; color: var(--muted); padding: 30px; }

.table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }

.filter-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.btn-filter { padding: 7px 16px; border-radius: 7px; border: 1px solid var(--border); background: transparent; color: var(--text); cursor: pointer; font-size: 0.88rem; display: inline-flex; align-items: center; gap: 6px; }
.btn-filter:hover { background: var(--border); }
.btn-filter.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.filter-badge { background: #fff; color: var(--accent); border-radius: 50%; width: 18px; height: 18px; font-size: 0.7rem; font-weight: bold; display: inline-flex; align-items: center; justify-content: center; }
.filter-modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 200; align-items: center; justify-content: center; }
.filter-modal-overlay.open { display: flex; }
.filter-modal { background: var(--card); border-radius: 12px; padding: 24px 22px 20px; width: min(420px, 96vw); box-shadow: 0 8px 32px rgba(0,0,0,0.22); position: relative; }
.filter-modal h3 { margin: 0 0 18px 0; font-size: 1rem; }
.filter-modal .form-grid { display: flex; flex-direction: column; gap: 14px; }
.filter-modal-footer { display: flex; gap: 8px; margin-top: 18px; }
.sort-section { border-top: 1px solid var(--border); margin-top: 16px; padding-top: 14px; }
.sort-section-label { font-size: 0.78rem; font-weight: bold; color: var(--muted); margin-bottom: 8px; display: block; }
.sort-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.sort-row select { flex: 1; padding: 7px 9px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font-size: 0.85rem; }
.sort-row .sort-dir { flex: 0 0 auto; width: 130px; }
.btn-close-modal { position: absolute; top: 14px; right: 16px; background: none; border: none; font-size: 1.3rem; cursor: pointer; color: var(--muted); line-height: 1; }

@media (max-width: 640px) {
    .container { margin: 14px auto; padding: 0 12px; }
    .page-header { flex-direction: column; align-items: stretch; gap: 10px; }
    .page-header h1 { font-size: 1.25rem; }
    .page-nav { margin-left: 0; width: 100%; }
    .page-nav, .form-grid, .ric-fine-block, .tipo-toggle { flex-wrap: wrap; }

    .field { flex: 1 1 100%; }
    .field input, .field select, .field textarea { width: 100%; }

    .mv-row { gap: 6px 10px; }
    .mv-dot { order: 1; }
    .mv-date { order: 2; width: auto; font-size: 0.75rem; }
    .mv-amount { order: 3; margin-left: auto; width: auto; font-size: 0.9rem; }
    .mv-cat { order: 4; flex-basis: 100%; min-width: 100%; }
    .mv-actions { order: 5; flex-basis: 100%; justify-content: flex-end; margin-top: 2px; }
    .mv-actions button, .mv-actions a { padding: 6px 8px; font-size: 1.1rem; }

    table { min-width: 520px; }
}
"""

_THEME_SCRIPT = """
<script>
    if (localStorage.getItem('taskplanner_theme') === 'dark') {
        document.body.classList.add('dark');
    }
</script>
"""

_THEME_TOGGLE_BUTTON = '<button id="darkToggle"></button>'

_LANG_SWITCHER = (
    '<a href="/lang/it" style="font-size:0.8rem; text-decoration:none; padding:7px 10px; '
    'border-radius:7px; border:1px solid var(--border); '
    '{% if session.get(\'lang\', \'it\') == \'it\' %}background:var(--accent);color:#fff;'
    '{% else %}color:var(--text);{% endif %}">\U0001f1ee\U0001f1f9 IT</a>'
    '<a href="/lang/en" style="font-size:0.8rem; text-decoration:none; padding:7px 10px; '
    'border-radius:7px; border:1px solid var(--border); '
    '{% if session.get(\'lang\') == \'en\' %}background:var(--accent);color:#fff;'
    '{% else %}color:var(--text);{% endif %}">\U0001f1ec\U0001f1e7 EN</a>'
)

_THEME_TOGGLE_JS = """
<script>
document.addEventListener('DOMContentLoaded', function(){
    var body = document.body;
    var toggle = document.getElementById('darkToggle');
    if (!toggle) return;
    var lightLabel = '🌙 """ + "{{ _(\"Modalità scura\") }}" + """';
    var darkLabel  = '☀️ """ + "{{ _(\"Modalità chiara\") }}" + """';
    toggle.textContent = body.classList.contains('dark') ? darkLabel : lightLabel;
    toggle.addEventListener('click', function(){
        body.classList.toggle('dark');
        var isDark = body.classList.contains('dark');
        localStorage.setItem('taskplanner_theme', isDark ? 'dark' : 'light');
        toggle.textContent = isDark ? darkLabel : lightLabel;
    });
});
</script>
"""

_OCCURRENCE_ACTIONS_JS = """
<script>
function overrideOccurrence(mid, occDate, currentAmount){
    var amt = prompt('""" + "{{ _(\"Nuovo importo per questa occorrenza:\") }}" + """', currentAmount);
    if (amt === null || amt === '') return;
    var note = prompt('""" + "{{ _(\"Nota (opzionale):\") }}" + """', '') || '';
    var f = document.createElement('form');
    f.method = 'POST';
    f.action = '/contaschei/exception/' + mid;
    function addField(name, value){
        var inp = document.createElement('input');
        inp.type = 'hidden'; inp.name = name; inp.value = value;
        f.appendChild(inp);
    }
    addField('occurrence_date', occDate);
    addField('action', 'override');
    addField('override_amount', amt);
    addField('override_note', note);
    document.body.appendChild(f);
    f.submit();
}
function toggleCategoryOptions(){
    var tipo = document.querySelector('input[name="tipo"]:checked');
    if (!tipo) return;
    var sel = document.getElementById('mv_category_id');
    if (!sel) return;
    for (var i = 0; i < sel.options.length; i++){
        var opt = sel.options[i];
        if (!opt.value) continue;
        opt.hidden = (opt.dataset.type !== tipo.value);
    }
    if (sel.selectedOptions[0] && sel.selectedOptions[0].hidden) sel.value = '';
}
function filterCategoryByTipo(){
    var tipoSel = document.getElementById('filter_tipo');
    var catSel  = document.getElementById('filter_category');
    if (!tipoSel || !catSel) return;
    var chosen = tipoSel.value;
    for (var i = 0; i < catSel.options.length; i++){
        var opt = catSel.options[i];
        var hide = chosen && opt.dataset.type !== chosen;
        opt.hidden = hide;
        if (hide) opt.selected = false;
    }
}
document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('input[name="tipo"]').forEach(function(r){
        r.addEventListener('change', toggleCategoryOptions);
    });
    toggleCategoryOptions();
    var ricSel = document.getElementById('mv_ricorrenza');
    var ricBlock = document.getElementById('mv_ric_fine_block');
    if (ricSel && ricBlock){
        ricSel.addEventListener('change', function(){
            ricBlock.style.display = this.value !== 'none' ? 'flex' : 'none';
        });
    }
    var filterTipo = document.getElementById('filter_tipo');
    if (filterTipo) filterTipo.addEventListener('change', filterCategoryByTipo);
    filterCategoryByTipo();
    var filterOverlay = document.getElementById('filterModal');
    if (filterOverlay){
        filterOverlay.addEventListener('click', function(e){
            if (e.target === filterOverlay) filterOverlay.classList.remove('open');
        });
        document.addEventListener('keydown', function(e){
            if (e.key === 'Escape') filterOverlay.classList.remove('open');
        });
    }
});
</script>
"""

TEMPLATE_CONTASCHEI = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{{ _("Contaschei") }} - TaskPlanner</title>
<style>''' + _CONTASCHEI_CSS + '''</style>
</head>
<body>''' + _THEME_SCRIPT + '''
<div class="container">
    <div class="page-header">
        <a href="/" class="btn-back">&larr; {{ _("Torna alla Home") }}</a>
        <h1>&#128176; {{ _("Contaschei") }}</h1>
        <div class="page-nav">
            <a href="{{ url_for('contaschei_bilancio') }}">&#128202; {{ _("Bilancio") }}</a>
            <a href="{{ url_for('contaschei_categories') }}">&#9881;&#65039; {{ _("Tipologie") }}</a>
            ''' + _LANG_SWITCHER + _THEME_TOGGLE_BUTTON + '''
        </div>
    </div>

    {% set _active_count = (1 if tipo_filter else 0) + cat_filter|length + (1 if search else 0) + (0 if sort_is_default else 1) %}
    <div class="filter-bar">
        <button type="button" class="btn-filter {% if _active_count %}active{% endif %}" onclick="document.getElementById('filterModal').classList.add('open')">
            &#9783; {{ _("Filtri") }}{% if _active_count %}<span class="filter-badge">{{ _active_count }}</span>{% endif %}
        </button>
        <span style="font-size:0.8rem; color:var(--muted);">
            {{ date_from | fmt_date }} &rarr; {{ date_to | fmt_date }}
            {% if _active_count %} &middot; <a href="{{ url_for('contaschei_dashboard', date_from=date_from, date_to=date_to) }}" style="color:var(--danger); font-size:0.78rem;">{{ _("Annulla") }}</a>{% endif %}
        </span>
    </div>

    <div class="filter-modal-overlay" id="filterModal">
        <div class="filter-modal">
            <button class="btn-close-modal" type="button" onclick="document.getElementById('filterModal').classList.remove('open')">&times;</button>
            <h3>&#9783; {{ _("Filtri") }}</h3>
            <form method="GET" action="{{ url_for('contaschei_dashboard') }}">
                <div class="form-grid">
                    <div class="field">
                        <label>{{ _("Dal") }}</label>
                        <input type="date" name="date_from" value="{{ date_from }}">
                    </div>
                    <div class="field">
                        <label>{{ _("Al") }}</label>
                        <input type="date" name="date_to" value="{{ date_to }}">
                    </div>
                    <div class="field">
                        <label>{{ _("Cerca per descrizione") }}</label>
                        <input type="text" name="search" placeholder="{{ _("Testo nella nota...") }}" value="{{ search }}">
                    </div>
                    <div class="field">
                        <label>{{ _("Tipo") }}</label>
                        <select name="tipo" id="filter_tipo">
                            <option value="">{{ _("Tutti") }}</option>
                            <option value="income"  {% if tipo_filter == "income"  %}selected{% endif %}>&#11014;&#65039; {{ _("Entrata") }}</option>
                            <option value="expense" {% if tipo_filter == "expense" %}selected{% endif %}>&#11015;&#65039; {{ _("Spesa") }}</option>
                        </select>
                    </div>
                    <div class="field">
                        <label>{{ _("Tipologia") }}</label>
                        <select name="category_id" id="filter_category" multiple style="min-height:72px;">
                            {% for c in categories %}
                            <option value="{{ c[0] }}" data-type="{{ c[2] }}" {% if c[0]|string in cat_filter %}selected{% endif %}>{{ c[1] }}</option>
                            {% endfor %}
                        </select>
                    </div>
                </div>
                <div class="sort-section">
                    <span class="sort-section-label">&#8597; {{ _("Ordinamento") }}</span>
                    <div class="sort-row">
                        <select name="sort1">
                            <option value="date"     {% if sort1 == "date"     %}selected{% endif %}>{{ _("Data") }}</option>
                            <option value="amount"   {% if sort1 == "amount"   %}selected{% endif %}>{{ _("Importo") }}</option>
                            <option value="tipo"     {% if sort1 == "tipo"     %}selected{% endif %}>{{ _("Tipo") }}</option>
                            <option value="categoria"{% if sort1 == "categoria"%}selected{% endif %}>{{ _("Tipologia") }}</option>
                        </select>
                        <select name="sort1_dir" class="sort-dir">
                            <option value="desc" {% if sort1_dir == "desc" %}selected{% endif %}>&#11015; {{ _("Decrescente") }}</option>
                            <option value="asc"  {% if sort1_dir == "asc"  %}selected{% endif %}>&#11014; {{ _("Crescente") }}</option>
                        </select>
                    </div>
                    <div class="sort-row">
                        <select name="sort2">
                            <option value=""         {% if not sort2           %}selected{% endif %}>{{ _("Nessuno") }}</option>
                            <option value="date"     {% if sort2 == "date"     %}selected{% endif %}>{{ _("Data") }}</option>
                            <option value="amount"   {% if sort2 == "amount"   %}selected{% endif %}>{{ _("Importo") }}</option>
                            <option value="tipo"     {% if sort2 == "tipo"     %}selected{% endif %}>{{ _("Tipo") }}</option>
                            <option value="categoria"{% if sort2 == "categoria"%}selected{% endif %}>{{ _("Tipologia") }}</option>
                        </select>
                        <select name="sort2_dir" class="sort-dir">
                            <option value="asc"  {% if sort2_dir == "asc"  %}selected{% endif %}>&#11014; {{ _("Crescente") }}</option>
                            <option value="desc" {% if sort2_dir == "desc" %}selected{% endif %}>&#11015; {{ _("Decrescente") }}</option>
                        </select>
                    </div>
                </div>
                <div class="filter-modal-footer">
                    <button type="submit" class="btn-primary">{{ _("Applica filtri") }}</button>
                    <button type="button" class="btn-back" onclick="document.getElementById('filterModal').classList.remove('open')">{{ _("Chiudi") }}</button>
                </div>
            </form>
        </div>
    </div>
    <div class="kpi-grid">
        <div class="kpi-card green">
            <div class="kpi-label">&#128200; {{ _("Entrate") }}</div>
            <div class="kpi-value">&euro; {{ "%.2f"|format(tot_income) }}</div>
        </div>
        <div class="kpi-card red">
            <div class="kpi-label">&#128201; {{ _("Uscite") }}</div>
            <div class="kpi-value">&euro; {{ "%.2f"|format(tot_expense) }}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">&#128181; {{ _("Flusso netto") }}</div>
            <div class="kpi-value" style="{% if net < 0 %}color:var(--danger);{% else %}color:var(--success);{% endif %}">&euro; {{ "%.2f"|format(net) }}</div>
        </div>
    </div>

    <div class="section">
        {% set fd = edit_movement or copy_movement %}
        <h2>{% if edit_movement %}{{ _("Modifica movimento") }}{% elif copy_movement %}{{ _("Duplica movimento") }}{% else %}{{ _("Nuovo movimento") }}{% endif %}</h2>
        <form method="POST" action="{% if edit_movement %}{{ url_for('edit_movement', mid=edit_movement.id) }}{% else %}{{ url_for('add_movement') }}{% endif %}">
            <input type="hidden" name="date_from" value="{{ date_from }}">
            <input type="hidden" name="date_to" value="{{ date_to }}">
            <input type="hidden" name="tipo_filter" value="{{ tipo_filter }}">
            <input type="hidden" name="search" value="{{ search }}">
            {% for cid in cat_filter %}<input type="hidden" name="cat_filter" value="{{ cid }}">{% endfor %}
            <input type="hidden" name="sort1" value="{{ sort1 }}">
            <input type="hidden" name="sort1_dir" value="{{ sort1_dir }}">
            <input type="hidden" name="sort2" value="{{ sort2 }}">
            <input type="hidden" name="sort2_dir" value="{{ sort2_dir }}">
            <div class="form-grid">
                <div class="field">
                    <label>{{ _("Tipo") }}</label>
                    <div class="tipo-toggle">
                        <label class="opt-income"><input type="radio" name="tipo" value="income" {% if (fd.tipo if fd else 'expense') == 'income' %}checked{% endif %}><span>&#11014;&#65039; {{ _("Entrata") }}</span></label>
                        <label class="opt-expense"><input type="radio" name="tipo" value="expense" {% if (fd.tipo if fd else 'expense') == 'expense' %}checked{% endif %}><span>&#11015;&#65039; {{ _("Spesa") }}</span></label>
                    </div>
                </div>
                <div class="field">
                    <label>{{ _("Tipologia") }}</label>
                    <select name="category_id" id="mv_category_id">
                        <option value="">{{ _("Nessuna") }}</option>
                        {% for c in categories %}
                        <option value="{{ c[0] }}" data-type="{{ c[2] }}" {% if fd and fd.category_id == c[0] %}selected{% endif %}>{{ c[1] }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="field">
                    <label>{{ _("Importo") }} (&euro;)</label>
                    <input type="number" step="0.01" min="0.01" name="amount" required value="{{ fd.amount if fd else '' }}">
                </div>
                <div class="field">
                    <label>{{ _("Data") }}</label>
                    <input type="date" name="date" required value="{{ fd.date if fd else today }}">
                </div>
                <div class="field">
                    <label>{{ _("Ricorrenza") }}</label>
                    <select name="ricorrenza" id="mv_ricorrenza">
                        <option value="none"    {% if (fd.ricorrenza if fd else 'none') == 'none'    %}selected{% endif %}>{{ _("Nessuna") }}</option>
                        <option value="daily"   {% if fd and fd.ricorrenza == 'daily'   %}selected{% endif %}>{{ _("Giornaliera") }}</option>
                        <option value="weekly"  {% if fd and fd.ricorrenza == 'weekly'  %}selected{% endif %}>{{ _("Settimanale") }}</option>
                        <option value="monthly" {% if fd and fd.ricorrenza == 'monthly' %}selected{% endif %}>{{ _("Mensile (stesso giorno)") }}</option>
                        <option value="yearly"  {% if fd and fd.ricorrenza == 'yearly'  %}selected{% endif %}>{{ _("Annuale") }}</option>
                    </select>
                </div>
                <div class="field">
                    <label>{{ _("Nota") }}</label>
                    <input type="text" name="note" value="{{ fd.note if fd else '' }}">
                </div>
                <div class="field">
                    <button type="submit" class="btn-primary">{% if edit_movement %}{{ _("Salva modifiche") }}{% elif copy_movement %}{{ _("Aggiungi copia") }}{% else %}{{ _("Aggiungi") }}{% endif %}</button>
                    {% if fd %}<a href="{{ url_for('contaschei_dashboard', date_from=date_from, date_to=date_to, tipo=tipo_filter, category_id=cat_filter, search=search, sort1=sort1, sort1_dir=sort1_dir, sort2=sort2, sort2_dir=sort2_dir) }}" class="btn-back" style="margin-top:4px;">{{ _("Annulla") }}</a>{% endif %}
                </div>
            </div>
            <div id="mv_ric_fine_block" class="ric-fine-block" style="display:{% if fd and fd.ricorrenza != 'none' %}flex{% else %}none{% endif %};">
                <div class="field">
                    <label>{{ _("Fine ricorrenza (opzionale)") }}</label>
                    <input type="date" name="ricorrenza_fine" value="{{ fd.ricorrenza_fine if fd else '' }}">
                </div>
                <div class="field">
                    <label>{{ _("N&deg; occorrenze max") }}</label>
                    <input type="number" min="1" step="1" name="ricorrenza_occorrenze" placeholder="es. 10" value="{{ fd.ricorrenza_occorrenze if fd else '' }}">
                </div>
            </div>
        </form>
    </div>

    <div class="section">
        <h2>{{ _("Movimenti del periodo") }}</h2>
        {% if occurrences %}
        {% for o in occurrences %}
        <div class="mv-row">
            <div class="mv-dot" style="background:{{ o.color or '#999' }};"></div>
            <div class="mv-date">{{ o.occurrence_date | fmt_date }}</div>
            <div class="mv-cat">
                {{ o.categoria or _("Nessuna tipologia") }}
                {% if o.note %}<span class="mv-note"> &middot; {{ o.note }}</span>{% endif %}
                {% if o.is_recurring %}<span class="mv-badge">&#128257; {{ _("ricorrente") }}</span>{% endif %}
                {% if o.has_exception %}<span class="mv-badge">&#9998;&#65039; {{ _("modificata") }}</span>{% endif %}
            </div>
            <div class="mv-amount {{ o.tipo }}">{% if o.tipo == 'income' %}+{% else %}-{% endif %}&euro; {{ "%.2f"|format(o.amount) }}</div>
            <div class="mv-actions">
                {% if o.is_recurring %}
                <button type="button" title="{{ _("Modifica solo questa occorrenza") }}" onclick="overrideOccurrence({{ o.id }}, '{{ o.occurrence_date }}', {{ o.amount }})">&#9999;&#65039;</button>
                <form method="POST" action="{{ url_for('set_movement_exception', mid=o.id) }}" style="display:inline;" onsubmit="return confirm('{{ _("Salta questa occorrenza?") }}');">
                    <input type="hidden" name="occurrence_date" value="{{ o.occurrence_date }}">
                    <input type="hidden" name="action" value="skip">
                    <button type="submit" title="{{ _("Salta questa occorrenza") }}">&#9197;&#65039;</button>
                </form>
                {% if o.has_exception %}
                <form method="POST" action="{{ url_for('delete_movement_exception', mid=o.id) }}" style="display:inline;">
                    <input type="hidden" name="occurrence_date" value="{{ o.occurrence_date }}">
                    <button type="submit" title="{{ _("Ripristina occorrenza originale") }}">&#8634;</button>
                </form>
                {% endif %}
                <a href="{{ url_for('contaschei_dashboard', date_from=date_from, date_to=date_to, tipo=tipo_filter, category_id=cat_filter, search=search, sort1=sort1, sort1_dir=sort1_dir, sort2=sort2, sort2_dir=sort2_dir, edit=o.id) }}" title="{{ _("Modifica la serie") }}">&#128221;</a>
                {% else %}
                <a href="{{ url_for('contaschei_dashboard', date_from=date_from, date_to=date_to, tipo=tipo_filter, category_id=cat_filter, search=search, sort1=sort1, sort1_dir=sort1_dir, sort2=sort2, sort2_dir=sort2_dir, edit=o.id) }}" title="{{ _("Modifica") }}">&#9999;&#65039;</a>
                {% endif %}
                <a href="{{ url_for('contaschei_dashboard', date_from=date_from, date_to=date_to, tipo=tipo_filter, category_id=cat_filter, search=search, sort1=sort1, sort1_dir=sort1_dir, sort2=sort2, sort2_dir=sort2_dir, copy=o.id) }}" title="{{ _("Duplica in un nuovo movimento") }}">&#128203;</a>
                <form method="POST" action="{{ url_for('delete_movement', mid=o.id) }}" style="display:inline;" onsubmit="return confirm('{{ _("Eliminare questo movimento?") }}');">
                    <input type="hidden" name="date_from" value="{{ date_from }}">
                    <input type="hidden" name="date_to" value="{{ date_to }}">
                    <input type="hidden" name="tipo_filter" value="{{ tipo_filter }}">
                    <input type="hidden" name="search" value="{{ search }}">
                    {% for cid in cat_filter %}<input type="hidden" name="cat_filter" value="{{ cid }}">{% endfor %}
                    <input type="hidden" name="sort1" value="{{ sort1 }}">
                    <input type="hidden" name="sort1_dir" value="{{ sort1_dir }}">
                    <input type="hidden" name="sort2" value="{{ sort2 }}">
                    <input type="hidden" name="sort2_dir" value="{{ sort2_dir }}">
                    <button type="submit" title="{{ _("Elimina") }}">&#128465;&#65039;</button>
                </form>
            </div>
        </div>
        {% endfor %}
        {% else %}
        <div class="empty-msg">{{ _("Nessun movimento nel periodo selezionato") }}</div>
        {% endif %}
    </div>
</div>''' + _OCCURRENCE_ACTIONS_JS + _THEME_TOGGLE_JS + '''
</body>
</html>
'''

TEMPLATE_CONTASCHEI_CATEGORIES = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{{ _("Tipologie movimento") }} - TaskPlanner</title>
<style>''' + _CONTASCHEI_CSS + '''</style>
</head>
<body>''' + _THEME_SCRIPT + '''
<div class="container">
    <div class="page-header">
        <a href="{{ url_for('contaschei_dashboard') }}" class="btn-back">&larr; {{ _("Torna a Contaschei") }}</a>
        <h1>&#9881;&#65039; {{ _("Tipologie movimento") }}</h1>
        <div class="page-nav">
            ''' + _LANG_SWITCHER + _THEME_TOGGLE_BUTTON + '''
        </div>
    </div>

    <div class="section">
        <h2>{{ _("Nuova tipologia") }}</h2>
        <form action="{{ url_for('add_movement_category') }}" method="POST">
            <div class="form-grid">
                <div class="field">
                    <label>{{ _("Nome") }}</label>
                    <input type="text" name="name" placeholder="{{ _("Nome tipologia") }}" required>
                </div>
                <div class="field">
                    <label>{{ _("Tipo") }}</label>
                    <select name="type">
                        <option value="income">{{ _("Entrata") }}</option>
                        <option value="expense">{{ _("Spesa") }}</option>
                    </select>
                </div>
                <div class="field">
                    <label>{{ _("Colore") }}</label>
                    <input type="color" name="color" value="#007bff">
                </div>
                <div class="field">
                    <button type="submit" class="btn-primary">{{ _("Aggiungi") }}</button>
                </div>
            </div>
        </form>
    </div>

    <div class="section">
        <h2>{{ _("Tipologie esistenti") }}</h2>
        <div class="table-wrap">
        <table style="width:100%; border-collapse: collapse;">
            <thead>
                <tr>
                    <th style="text-align:left; padding:8px; border-bottom:2px solid var(--border);">{{ _("Colore") }}</th>
                    <th style="text-align:left; padding:8px; border-bottom:2px solid var(--border);">{{ _("Nome") }}</th>
                    <th style="text-align:left; padding:8px; border-bottom:2px solid var(--border);">{{ _("Tipo") }}</th>
                    <th style="text-align:left; padding:8px; border-bottom:2px solid var(--border);">{{ _("Azioni") }}</th>
                </tr>
            </thead>
            <tbody>
                {% for c in categories %}
                <tr>
                    <form action="{{ url_for('update_movement_category', cid=c[0]) }}" method="POST">
                    <td style="padding:8px; border-bottom:1px solid var(--border);">
                        <input type="color" name="color" value="{{ c[3] }}" style="width:36px;height:28px;border:none;cursor:pointer;border-radius:4px;">
                    </td>
                    <td style="padding:8px; border-bottom:1px solid var(--border);">
                        <input type="text" name="name" value="{{ c[1] }}" required style="min-width:140px;">
                    </td>
                    <td style="padding:8px; border-bottom:1px solid var(--border);">
                        <select name="type">
                            <option value="income"  {% if c[2] == 'income'  %}selected{% endif %}>{{ _("Entrata") }}</option>
                            <option value="expense" {% if c[2] == 'expense' %}selected{% endif %}>{{ _("Spesa") }}</option>
                        </select>
                    </td>
                    <td style="padding:8px; border-bottom:1px solid var(--border); white-space:nowrap;">
                        <button type="submit" class="btn-primary">{{ _("Salva") }}</button>
                    </form>
                        <form action="{{ url_for('delete_movement_category', cid=c[0]) }}" method="POST" style="display:inline;" onsubmit="return confirm('{{ _("Eliminare questa tipologia? I movimenti collegati resteranno senza tipologia.") }}');">
                            <button type="submit" style="background:var(--danger); color:#fff; border:none; border-radius:6px; padding:9px 14px; cursor:pointer;">{{ _("Elimina") }}</button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="empty-msg">{{ _("Nessuna tipologia presente.") }}</td></tr>
                {% endfor %}
            </tbody>
        </table>
        </div>
    </div>
</div>''' + _THEME_TOGGLE_JS + '''
</body>
</html>
'''

TEMPLATE_CONTASCHEI_BILANCIO = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{{ _("Bilancio") }} - TaskPlanner</title>
<style>''' + _CONTASCHEI_CSS + '''
.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.bar-label { width: 160px; font-size: 0.82rem; text-align: right; flex-shrink: 0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.bar-track { flex: 1; background: var(--border); border-radius: 6px; height: 18px; overflow: hidden; }
.bar-fill  { height: 100%; border-radius: 6px; transition: width 0.4s ease; min-width: 4px; }
.bar-amount { font-size: 0.8rem; color: var(--muted); flex-shrink: 0; width: 90px; text-align: right; }
@media (max-width: 640px) {
    .bar-label { width: 88px; font-size: 0.72rem; }
    .bar-amount { width: 70px; font-size: 0.72rem; }
}
</style>
</head>
<body>''' + _THEME_SCRIPT + '''
<div class="container">
    <div class="page-header">
        <a href="{{ url_for('contaschei_dashboard') }}" class="btn-back">&larr; {{ _("Torna a Contaschei") }}</a>
        <h1>&#128202; {{ _("Bilancio") }}</h1>
        <div class="page-nav">
            ''' + _LANG_SWITCHER + _THEME_TOGGLE_BUTTON + '''
        </div>
    </div>

    <form method="GET" action="{{ url_for('contaschei_bilancio') }}">
    <div class="section">
        <div class="form-grid">
            <div class="field">
                <label>{{ _("Periodo") }}</label>
                <select name="period_type">
                    <option value="month"     {% if period_type == 'month'     %}selected{% endif %}>{{ _("Mese") }}</option>
                    <option value="bimonth"   {% if period_type == 'bimonth'   %}selected{% endif %}>{{ _("Bimestre") }}</option>
                    <option value="quarter"   {% if period_type == 'quarter'   %}selected{% endif %}>{{ _("Trimestre") }}</option>
                    <option value="fourmonth" {% if period_type == 'fourmonth' %}selected{% endif %}>{{ _("Quadrimestre") }}</option>
                    <option value="semester"  {% if period_type == 'semester'  %}selected{% endif %}>{{ _("Semestre") }}</option>
                    <option value="year"      {% if period_type == 'year'      %}selected{% endif %}>{{ _("Anno") }}</option>
                </select>
            </div>
            <div class="field">
                <label>{{ _("Tipo movimento") }}</label>
                <select name="tipo">
                    <option value="">{{ _("Tutti") }}</option>
                    <option value="income"  {% if tipo_filter == 'income'  %}selected{% endif %}>{{ _("Entrata") }}</option>
                    <option value="expense" {% if tipo_filter == 'expense' %}selected{% endif %}>{{ _("Spesa") }}</option>
                </select>
            </div>
            <div class="field">
                <label>{{ _("Tipologia (multi)") }}</label>
                <select name="category_id" multiple>
                    {% for c in categories %}
                    <option value="{{ c[0] }}" {% if c[0]|string in cat_filter %}selected{% endif %}>{{ c[1] }}</option>
                    {% endfor %}
                </select>
            </div>
            <input type="hidden" name="period_offset" value="{{ period_offset }}">
            <div class="field">
                <button type="submit" class="btn-primary">{{ _("Applica filtri") }}</button>
            </div>
        </div>
    </div>
    </form>

    <div class="page-nav" style="margin: -10px 0 16px 0; justify-content:flex-start;">
        <a href="{{ url_for('contaschei_bilancio', period_type=period_type, tipo=tipo_filter, category_id=cat_filter, period_offset=period_offset - 1) }}">&larr; {{ _("Periodo precedente") }}</a>
        <a href="{{ url_for('contaschei_bilancio', period_type=period_type, tipo=tipo_filter, category_id=cat_filter, period_offset=period_offset + 1) }}">{{ _("Periodo successivo") }} &rarr;</a>
    </div>

    <div style="margin-bottom: 6px; font-size: 0.8rem; color: var(--muted); font-weight: bold; text-transform: uppercase; letter-spacing: 0.04em;">
        {{ date_from | fmt_date }} &rarr; {{ date_to | fmt_date }}
    </div>
    <div class="kpi-grid">
        <div class="kpi-card green">
            <div class="kpi-label">&#128200; {{ _("Totale entrate") }}</div>
            <div class="kpi-value">&euro; {{ "%.2f"|format(tot_income) }}</div>
        </div>
        <div class="kpi-card red">
            <div class="kpi-label">&#128201; {{ _("Totale uscite") }}</div>
            <div class="kpi-value">&euro; {{ "%.2f"|format(tot_expense) }}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">&#128181; {{ _("Flusso netto del periodo") }}</div>
            <div class="kpi-value" style="{% if net < 0 %}color:var(--danger);{% else %}color:var(--success);{% endif %}">&euro; {{ "%.2f"|format(net) }}</div>
        </div>
    </div>

    {% if by_category %}
    <div class="section">
        <h2>{{ _("Per tipologia") }}</h2>
        {% set max_val = by_category | map(attribute=3) | max %}
        {% for name, color, tipo, tot in by_category %}
        <div class="bar-row">
            <div class="bar-label" title="{{ name }}">{{ name }}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{{ (tot / max_val * 100) | round | int }}%; background:{{ color or (
                    '#28a745' if tipo == 'income' else '#dc3545') }};"></div>
            </div>
            <div class="bar-amount">&euro; {{ "%.2f"|format(tot) }}</div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="section empty-msg">{{ _("Nessun movimento nel periodo selezionato") }}</div>
    {% endif %}
</div>''' + _THEME_TOGGLE_JS + '''
</body>
</html>
'''
