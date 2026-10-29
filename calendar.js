(() => {
  const dataNode = document.getElementById('calendar-data');
  const grid = document.getElementById('cal-grid');
  if (!dataNode || !grid) return;

  const removedKey = 'career-alerts.removed.v1';
  const titleNode = document.getElementById('cal-title');
  const list = document.getElementById('cal-list');
  const listTitle = document.getElementById('cal-list-title');
  const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const MAX_PER_DAY = 3;

  let events = [];
  try { events = JSON.parse(dataNode.textContent) || []; } catch (_) { events = []; }

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  let view = new Date(today.getFullYear(), today.getMonth(), 1);

  function removedIds() {
    try {
      const stored = JSON.parse(localStorage.getItem(removedKey) || '[]');
      return new Set(Array.isArray(stored) ? stored.map(item => item && item.id) : []);
    } catch (_) {
      return new Set();
    }
  }

  function visibleEvents() {
    const hidden = removedIds();
    return events.filter(e => !hidden.has(e.id));
  }

  function iso(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  function parseIso(s) {
    const [y, m, d] = s.split('-').map(Number);
    return new Date(y, m - 1, d);
  }

  function validLink(url) {
    try {
      const p = new URL(url);
      return p.protocol === 'https:' || p.protocol === 'http:';
    } catch (_) {
      return false;
    }
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function chip(e) {
    const past = parseIso(e.date) < today;
    const node = validLink(e.url) ? el('a') : el('span');
    node.className = `cal-ev ${e.tag}${e.tentative ? ' tentative' : ''}${past ? ' past' : ''}`;
    node.textContent = e.title;
    node.title = `${e.label}: ${e.title}${e.tentative ? ' (date not confirmed)' : ''}`;
    if (node.tagName === 'A') {
      node.href = e.url;
      node.target = '_blank';
      node.rel = 'noopener';
    }
    return node;
  }

  function render() {
    const all = visibleEvents();
    const byDay = new Map();
    for (const e of all) {
      if (!byDay.has(e.date)) byDay.set(e.date, []);
      byDay.get(e.date).push(e);
    }

    titleNode.textContent = view.toLocaleDateString(undefined, {month: 'long', year: 'numeric'});
    grid.replaceChildren();
    for (const name of DOW) grid.append(el('div', 'cal-dow', name));

    const start = new Date(view);
    start.setDate(1 - view.getDay());
    const end = new Date(view.getFullYear(), view.getMonth() + 1, 0);
    const cells = Math.ceil((view.getDay() + end.getDate()) / 7) * 7;
    for (let i = 0; i < cells; i++) {
      const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
      const key = iso(d);
      const cell = el('div', 'cal-day');
      cell.setAttribute('role', 'gridcell');
      if (d.getMonth() !== view.getMonth()) cell.classList.add('out');
      if (d.getTime() === today.getTime()) cell.classList.add('today');
      cell.append(el('span', 'cal-num', String(d.getDate())));
      const dayEvents = byDay.get(key) || [];
      dayEvents.slice(0, MAX_PER_DAY).forEach(e => cell.append(chip(e)));
      if (dayEvents.length > MAX_PER_DAY) {
        cell.append(el('span', 'cal-more', `+${dayEvents.length - MAX_PER_DAY} more`));
      }
      if (dayEvents.length) {
        cell.setAttribute('aria-label', `${key}: ${dayEvents.map(e => e.title).join('; ')}`);
      }
      grid.append(cell);
    }

    const monthKey = iso(view).slice(0, 7);
    const monthEvents = all.filter(e => e.date.startsWith(monthKey));
    listTitle.textContent = `Deadlines in ${titleNode.textContent} (${monthEvents.length})`;
    list.replaceChildren();
    if (!monthEvents.length) {
      list.append(el('p', 'empty', 'No dated deadlines this month.'));
      return;
    }
    for (const e of monthEvents) {
      const days = Math.round((parseIso(e.date) - today) / 86400000);
      const row = el('li', 'dlrow' + (days < 0 ? ' past' : days <= 45 ? ' hot' : days <= 120 ? ' soon' : ''));
      row.append(el('span', 'left', days < 0 ? 'past' : days === 0 ? 'today' : `${days}d`));
      const mid = el('div', 'mid');
      const tag = el('span', `tag ${e.tag}`, e.label);
      const link = validLink(e.url) ? el('a', 't', e.title) : el('span', 't', e.title);
      if (link.tagName === 'A') {
        link.href = e.url;
        link.target = '_blank';
        link.rel = 'noopener';
      }
      mid.append(tag, link);
      if (e.tentative) mid.append(el('span', 'conf warn', 'unconfirmed'));
      const date = parseIso(e.date).toLocaleDateString(undefined, {weekday: 'short', month: 'short', day: 'numeric'});
      mid.append(el('p', 'note', `Due ${date}${e.detail ? ' · ' + e.detail : ''}`));
      row.append(mid);
      list.append(row);
    }
  }

  function icsText(s) {
    return String(s || '').replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/([,;])/g, '\\$1');
  }

  function downloadIcs() {
    const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
    const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Career Alerts//Deadlines//EN', 'CALSCALE:GREGORIAN'];
    for (const e of visibleEvents()) {
      const start = e.date.replace(/-/g, '');
      const next = parseIso(e.date);
      next.setDate(next.getDate() + 1);
      lines.push(
        'BEGIN:VEVENT',
        `UID:${e.id}-${start}@career-alerts`,
        `DTSTAMP:${stamp}`,
        `DTSTART;VALUE=DATE:${start}`,
        `DTEND;VALUE=DATE:${iso(next).replace(/-/g, '')}`,
        `SUMMARY:${icsText(`[${e.label}] ${e.title}${e.tentative ? ' (unconfirmed)' : ''}`)}`,
        `DESCRIPTION:${icsText([e.detail, e.url].filter(Boolean).join('\n'))}`,
      );
      if (validLink(e.url)) lines.push(`URL:${e.url}`);
      lines.push('END:VEVENT');
    }
    lines.push('END:VCALENDAR');
    const blob = new Blob([lines.join('\r\n')], {type: 'text/calendar'});
    const a = el('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'career-deadlines.ics';
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  function move(delta) {
    view = new Date(view.getFullYear(), view.getMonth() + delta, 1);
    render();
  }

  document.getElementById('cal-prev').addEventListener('click', () => move(-1));
  document.getElementById('cal-next').addEventListener('click', () => move(1));
  document.getElementById('cal-today').addEventListener('click', () => {
    view = new Date(today.getFullYear(), today.getMonth(), 1);
    render();
  });
  document.getElementById('cal-ics').addEventListener('click', downloadIcs);
  addEventListener('career-alerts:removed-changed', render);
  render();
})();
