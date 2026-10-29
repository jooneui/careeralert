(() => {
  const storageKey = 'career-alerts.saved.v1';
  const removedKey = 'career-alerts.removed.v1';
  const pastKey = 'career-alerts.past.v1';
  const SOURCES = [
    ['career', 'Career Opportunities', 'Career scan '],
    ['ai', 'AI Watch', 'AI scan '],
    ['news', 'Transportation News', 'News scan '],
    ['econ', 'Economy', 'Economy scan '],
  ];
  const sourceIds = SOURCES.map(s => s[0]);
  const tabNames = ['career', 'calendar', 'ai', 'news', 'econ', 'saved', 'past'];
  const tabs = [...document.querySelectorAll('[data-tab]')];
  const controls = [...document.querySelectorAll('button[data-save]')];
  const removeControls = [...document.querySelectorAll('button[data-remove-feed]')];
  const pastControls = [...document.querySelectorAll('button[data-past]')];
  const sourceItems = new Map();
  const savedContent = document.getElementById('saved-content');
  const savedCount = document.getElementById('saved-tab-count');
  const pastContent = document.getElementById('past-content');
  const pastCount = document.getElementById('past-tab-count');
  const storageError = document.getElementById('storage-error');
  let saved = new Map();
  let removed = new Map();
  let past = new Map();
  let storageAvailable = true;

  function loadList(key) {
    const out = new Map();
    const stored = JSON.parse(localStorage.getItem(key) || '[]');
    if (Array.isArray(stored)) {
      for (const item of stored) {
        if (item && typeof item.id === 'string' &&
            sourceIds.includes(item.source) &&
            typeof item.title === 'string') out.set(item.id, item);
      }
    }
    return out;
  }

  try {
    const probe = storageKey + '.probe';
    localStorage.setItem(probe, '1');
    localStorage.removeItem(probe);
    saved = loadList(storageKey);
    removed = loadList(removedKey);
    past = loadList(pastKey);
  } catch (_) {
    storageAvailable = false;
    storageError.hidden = false;
  }

  for (const button of controls) {
    try {
      button.saveItem = JSON.parse(button.dataset.save);
      button.dataset.saveId = button.saveItem.id;
      if (!sourceItems.has(button.saveItem.id)) sourceItems.set(button.saveItem.id, button.saveItem);
    } catch (_) {
      button.disabled = true;
    }
    if (!storageAvailable) button.disabled = true;
  }
  for (const button of [...removeControls, ...pastControls]) {
    const id = button.dataset.removeFeed || button.dataset.past;
    if (!storageAvailable || !sourceItems.has(id)) button.disabled = true;
  }

  function validLink(url) {
    try {
      const parsed = new URL(url);
      return parsed.protocol === 'https:' || parsed.protocol === 'http:';
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

  function titleNode(item) {
    const node = validLink(item.url) ? el('a', 't', item.title) : el('span', 't', item.title);
    if (node.tagName === 'A') {
      node.href = item.url;
      node.target = '_blank';
      node.rel = 'noopener';
    }
    return node;
  }

  function sourceMeta(source) {
    return SOURCES.find(s => s[0] === source) || SOURCES[0];
  }

  // "Topic: CAV | Salary: $100k | Location: TX" -> [[Topic, CAV], ...]
  function parseFacts(text) {
    return String(text || '').split('|').map(part => part.trim()).filter(Boolean).map(part => {
      const at = part.indexOf(':');
      return at > 0 ? [part.slice(0, at).trim(), part.slice(at + 1).trim()] : ['Info', part];
    });
  }

  function syncButtons() {
    for (const button of controls) {
      if (!button.saveItem) continue;
      const active = saved.has(button.saveItem.id);
      button.textContent = active ? 'Saved' : 'Save';
      button.setAttribute('aria-pressed', String(active));
      button.setAttribute('aria-label', (active ? 'Unsave ' : 'Save ') + button.saveItem.title);
    }
    for (const button of pastControls) {
      const active = past.has(button.dataset.past);
      button.textContent = active ? 'In Past' : 'Past save';
      button.setAttribute('aria-pressed', String(active));
    }
    savedCount.textContent = saved.size ? `(${saved.size})` : '';
    pastCount.textContent = past.size ? `(${past.size})` : '';
  }

  function renderSaved() {
    savedContent.replaceChildren();
    if (!saved.size) {
      savedContent.append(el('p', 'empty', 'No saved items yet. Use Save beside an item in any tab.'));
      return;
    }
    const all = [...saved.values()].sort((a, b) =>
      String(b.savedAt || '').localeCompare(String(a.savedAt || '')));
    for (const [source, heading, scanLabel] of SOURCES) {
      const entries = all.filter(item => item.source === source);
      if (!entries.length) continue;
      const section = el('section', 'saved-group');
      const list = el('ul', 'saved-list');
      for (const item of entries) {
        const row = el('li', 'item');
        row.append(el('span', 'tag ' + String(item.tag || ''), String(item.category || heading)));
        row.append(titleNode(item));
        const remove = el('button', 'save-btn', 'Remove');
        remove.type = 'button';
        remove.dataset.removeId = item.id;
        remove.setAttribute('aria-label', 'Remove ' + item.title + ' from Saved');
        row.append(remove);
        if (item.note) row.append(el('p', 'note', item.note));
        if (item.keyInfo) row.append(el('p', 'keyinfo', item.keyInfo));
        if (item.seenDate) row.append(el('p', 'saved-meta', scanLabel + item.seenDate));
        list.append(row);
      }
      section.append(el('h3', '', `${heading} (${entries.length})`), list);
      savedContent.append(section);
    }
  }

  function renderPast() {
    pastContent.replaceChildren();
    if (!past.size) {
      pastContent.append(el('p', 'empty',
        'Nothing kept yet. Click Past save beside a career item to keep its summary here.'));
      return;
    }
    const list = el('ul', 'saved-list');
    const all = [...past.values()].sort((a, b) =>
      String(b.archivedAt || '').localeCompare(String(a.archivedAt || '')));
    for (const item of all) {
      const row = el('li', 'item');
      row.append(el('span', 'tag ' + String(item.tag || ''), String(item.category || 'Item')));
      row.append(el('span', 't', item.title));
      const remove = el('button', 'save-btn', 'Remove');
      remove.type = 'button';
      remove.dataset.pastRemoveId = item.id;
      remove.setAttribute('aria-label', 'Remove ' + item.title + ' from Past');
      row.append(remove);

      const facts = parseFacts(item.keyInfo);
      if (item.deadline && !facts.some(f => /deadline/i.test(f[0]))) facts.push(['Deadline', item.deadline]);
      if (facts.length) {
        const dl = el('dl', 'facts');
        for (const [k, v] of facts) dl.append(el('dt', '', k), el('dd', '', v));
        row.append(dl);
      }
      if (item.note) row.append(el('p', 'note', item.note));
      const meta = el('p', 'saved-meta',
        sourceMeta(item.source)[2] + (item.seenDate || '?') +
        ' · kept ' + String(item.archivedAt || '').slice(0, 10));
      if (validLink(item.url)) {
        meta.append(' · ');
        const link = el('a', '', 'original link (may no longer work)');
        link.href = item.url;
        link.target = '_blank';
        link.rel = 'noopener';
        meta.append(link);
      }
      row.append(meta);
      list.append(row);
    }
    pastContent.append(list);
  }

  function renderRemoved() {
    for (const source of sourceIds) {
      const panel = document.getElementById(source + '-removed');
      const list = document.getElementById(source + '-removed-list');
      const count = document.getElementById(source + '-removed-count');
      if (!panel || !list || !count) continue;
      const entries = [...removed.values()].filter(item => item.source === source)
        .sort((a, b) => String(b.removedAt || '').localeCompare(String(a.removedAt || '')));
      list.replaceChildren();
      count.textContent = `(${entries.length})`;
      panel.hidden = entries.length === 0;
      for (const item of entries) {
        const row = el('li', 'item');
        row.append(el('span', 'tag ' + String(item.tag || ''), String(item.category || 'Item')));
        row.append(titleNode(item));
        const restore = el('button', 'save-btn', 'Restore');
        restore.type = 'button';
        restore.dataset.restoreId = item.id;
        restore.setAttribute('aria-label', 'Restore ' + item.title);
        row.append(restore);
        list.append(row);
      }
    }
  }

  function syncRemoved() {
    for (const button of removeControls) {
      button.closest('li').hidden = removed.has(button.dataset.removeFeed);
    }
    renderRemoved();
  }

  function persist(key, next) {
    try {
      localStorage.setItem(key, JSON.stringify([...next.values()]));
      return true;
    } catch (_) {
      storageError.hidden = false;
      return false;
    }
  }

  document.addEventListener('click', event => {
    const button = event.target.closest(
      'button[data-save], button[data-remove-id], button[data-remove-feed], ' +
      'button[data-restore-id], button[data-past], button[data-past-remove-id]');
    if (!button || !storageAvailable) return;

    if (button.dataset.past || button.dataset.pastRemoveId) {
      const next = new Map(past);
      const id = button.dataset.past || button.dataset.pastRemoveId;
      if (next.has(id)) next.delete(id);
      else {
        const item = sourceItems.get(id);
        if (!item) return;
        next.set(id, {...item, archivedAt: new Date().toISOString()});
      }
      if (persist(pastKey, next)) { past = next; syncButtons(); renderPast(); }
      return;
    }

    if (button.dataset.removeFeed || button.dataset.restoreId) {
      const next = new Map(removed);
      if (button.dataset.restoreId) next.delete(button.dataset.restoreId);
      else {
        const item = sourceItems.get(button.dataset.removeFeed);
        if (!item) return;
        next.set(item.id, {...item, removedAt: new Date().toISOString()});
      }
      if (persist(removedKey, next)) {
        removed = next;
        syncRemoved();
        dispatchEvent(new Event('career-alerts:removed-changed'));
      }
      return;
    }

    const next = new Map(saved);
    if (button.dataset.removeId) next.delete(button.dataset.removeId);
    else if (button.saveItem) {
      const item = button.saveItem;
      if (next.has(item.id)) next.delete(item.id);
      else next.set(item.id, {...item, savedAt: new Date().toISOString()});
    } else return;
    if (persist(storageKey, next)) { saved = next; syncButtons(); renderSaved(); }
  });

  function showTab(name) {
    const selected = tabNames.includes(name) ? name : 'career';
    for (const button of tabs) {
      const active = button.dataset.tab === selected;
      button.setAttribute('aria-selected', String(active));
      document.getElementById(button.getAttribute('aria-controls')).hidden = !active;
    }
  }

  function tabFromHash() {
    const hash = location.hash.replace('#', '');
    if (hash === 'ai-watch') return 'ai';
    return tabNames.includes(hash) ? hash : 'career';
  }

  for (const button of tabs) {
    button.addEventListener('click', () => {
      location.hash = button.dataset.tab === 'ai' ? 'ai-watch' : button.dataset.tab;
      showTab(button.dataset.tab);
    });
  }
  addEventListener('hashchange', () => showTab(tabFromHash()));
  syncButtons();
  renderSaved();
  renderPast();
  syncRemoved();
  showTab(tabFromHash());
})();
