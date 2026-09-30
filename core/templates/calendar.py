"""
JS per integrazione calendario web (ICS download + Google Calendar).
"""

_CALENDAR_JS = r"""
// -------- DROPDOWN CALENDARIO (web) --------
function pad2c(n) { return String(n).padStart(2, '0'); }

function addHourCal(dateStr, timeStr) {
    var dt = new Date(dateStr + 'T' + timeStr + ':00');
    dt.setHours(dt.getHours() + 1);
    var d = dt.getFullYear() + '-' + pad2c(dt.getMonth()+1) + '-' + pad2c(dt.getDate());
    var t = pad2c(dt.getHours()) + ':' + pad2c(dt.getMinutes());
    return { data: d, ora: t };
}

function toggleCalDropdown(evt, btn) {
    evt.stopPropagation();
    var wrap = btn.closest('.cal-wrap');
    var dd = wrap.querySelector('.cal-dropdown');
    var isOpen = dd.classList.contains('open');
    document.querySelectorAll('.cal-dropdown.open').forEach(function(d){ d.classList.remove('open'); });
    if (!isOpen) dd.classList.add('open');
}

document.addEventListener('click', function() {
    document.querySelectorAll('.cal-dropdown.open').forEach(function(d){ d.classList.remove('open'); });
});

document.addEventListener('click', function(e) {
    var dd = e.target.closest('.cal-dropdown');
    if (!dd) return;
    var titolo = dd.dataset.titolo || '';
    var data   = dd.dataset.data   || '';
    var ora    = dd.dataset.ora    || '';
    var url    = dd.dataset.url    || '';
    if (e.target.classList.contains('cal-ics')) {
        dd.classList.remove('open');
        downloadICS(titolo, data, ora, url);
    }
    if (e.target.classList.contains('cal-google')) {
        dd.classList.remove('open');
        openGoogleCalendar(titolo, data, ora, url);
    }
});

function escICS(s) {
    return String(s)
        .replace(/\\/g, '\\\\')
        .replace(/;/g, '\\;')
        .replace(/,/g, '\\,')
        .replace(/\n/g, '\\n');
}

function downloadICS(titolo, data, ora, url) {
    var oraI = ora || '09:00';
    var fine = addHourCal(data, oraI);
    var dtStart = data.replace(/-/g, '') + 'T' + oraI.replace(':', '') + '00';
    var dtEnd   = fine.data.replace(/-/g, '') + 'T' + fine.ora.replace(':', '') + '00';
    var now = new Date();
    var dtstamp = now.toISOString().replace(/[-:.]/g, '').slice(0, 15) + 'Z';
    var uid = dtstamp + '-' + Math.random().toString(36).slice(2) + '@taskplanner';
    var lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//TaskPlanner//IT',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'BEGIN:VEVENT',
        'UID:' + uid,
        'DTSTAMP:' + dtstamp,
        'DTSTART:' + dtStart,
        'DTEND:' + dtEnd,
        'SUMMARY:' + escICS(titolo),
        url ? 'DESCRIPTION:' + escICS(url) : null,
        'END:VEVENT',
        'END:VCALENDAR'
    ].filter(Boolean).join('\r\n');
    var blob = new Blob([lines], { type: 'text/calendar;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = titolo.replace(/[\/\\:*?"<>|]/g, '_') + '.ics';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(a.href);
}

function openGoogleCalendar(titolo, data, ora, url) {
    var oraI = ora || '09:00';
    var fine = addHourCal(data, oraI);
    var dtStart = data.replace(/-/g, '') + 'T' + oraI.replace(':', '') + '00';
    var dtEnd   = fine.data.replace(/-/g, '') + 'T' + fine.ora.replace(':', '') + '00';
    var gcUrl = 'https://calendar.google.com/calendar/render?action=TEMPLATE'
        + '&text=' + encodeURIComponent(titolo)
        + '&dates=' + dtStart + '/' + dtEnd
        + (url ? '&details=' + encodeURIComponent(url) : '');
    window.open(gcUrl, '_blank');
}
"""
