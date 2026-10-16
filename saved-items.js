(() => {
  const storageKey = 'career-alerts.saved.v1';
  const removedKey = 'career-alerts.removed.v1';
  const tabs = [...document.querySelectorAll('[data-tab]')];
  const controls = [...document.querySelectorAll('button[data-save]')];
  const removeControls = [...document.querySelectorAll('button[data-remove-feed]')];
  const sourceItems = new Map();
  const savedContent = document.getElementById('saved-content');
  const savedCount = document.getElementById('saved-tab-count');
  const storageError = document.getElementById('storage-error');
  let saved = new Map();
  let removed = new Map();
  let storageAvailable = true;

  try {
    const probe = storageKey + '.probe';
    localStorage.setItem(probe, '1');
    localStorage.removeItem(probe);
    const stored = JSON.parse(localStorage.getItem(storageKey) || '[]');
    if (Array.isArray(stored)) {
      for (const item of stored) {
        if (item && typeof item.id === 'string' &&
            (item.source === 'career' || item.source === 'ai') &&
            typeof item.title === 'string') saved.set(item.id, item);
      }
    }
    const hidden = JSON.parse(localStorage.getItem(removedKey) || '[]');
    if (Array.isArray(hidden)) {
      for (const item of hidden) {
        if (item && typeof item.id === 'string' &&
            (item.source === 'career' || item.source === 'ai') &&
            typeof item.title === 'string') removed.set(item.id, item);
      }
    }
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
  for (const button of removeControls) {
    if (!storageAvailable || !sourceItems.has(button.dataset.removeFeed)) button.disabled = true;
  }

  function validLink(url) {
    try {
      const parsed = new URL(url);
      return parsed.protocol === 'https:' || parsed.protocol === 'http:';
    } catch (_) {
      return false;
    }
  }

  function syncButtons() {
    for (const button of controls) {
      if (!button.saveItem) continue;
      const active = saved.has(button.saveItem.id);
      button.textContent = active ? 'Saved' : 'Save';
      button.setAttribute('aria-pressed', String(active));
      button.setAttribute('aria-label', (active ? 'Unsave ' : 'Save ') + button.saveItem.title);
    }
    savedCount.textContent = saved.size ? `(${saved.size})` : '';
  }

  function renderSaved() {
    savedContent.replaceChildren();
    if (!saved.size) {
      const empty = document.createElement('p');
      empty.className = 'empty';
      empty.textContent = 'No saved items yet. Use Save beside an item in either tab.';
      savedContent.append(empty);
      return;
    }

    const all = [...saved.values()].sort((a, b) =>
      String(b.savedAt || '').localeCompare(String(a.savedAt || '')));
    for (const [source, heading] of [
      ['career', 'Career Opportunities'], ['ai', 'AI Watch']
    ]) {
      const entries = all.filter(item => item.source === source);
      if (!entries.length) continue;
      const section = document.createElement('section');
      section.className = 'saved-group';
      const title = document.createElement('h3');
      title.textContent = `${heading} (${entries.length})`;
      const list = document.createElement('ul');
      list.className = 'saved-list';
      for (const item of entries) {
        const row = document.createElement('li');
        row.className = 'item';
        const tag = document.createElement('span');
        tag.className = 'tag ' + String(item.tag || '');
        tag.textContent = String(item.category || heading);
        row.append(tag);
        const itemTitle = validLink(item.url) ? document.createElement('a') : document.createElement('span');
        itemTitle.className = 't';
        itemTitle.textContent = item.title;
        if (itemTitle.tagName === 'A') {
          itemTitle.href = item.url;
          itemTitle.target = '_blank';
          itemTitle.rel = 'noopener';
        }
        row.append(itemTitle);
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'save-btn';
        remove.textContent = 'Remove';
        remove.dataset.removeId = item.id;
        remove.setAttribute('aria-label', 'Remove ' + item.title + ' from Saved');
        row.append(remove);
        if (item.note) {
          const note = document.createElement('p');
          note.className = 'note';
          note.textContent = item.note;
          row.append(note);
        }
        if (item.seenDate) {
          const meta = document.createElement('p');
          meta.className = 'saved-meta';
          meta.textContent = (source === 'ai' ? 'AI scan ' : 'Career scan ') + item.seenDate;
          row.append(meta);
        }
        list.append(row);
      }
      section.append(title, list);
      savedContent.append(section);
    }
  }

  function renderRemoved() {
    for (const source of ['career', 'ai']) {
      const panel = document.getElementById(source + '-removed');
      const list = document.getElementById(source + '-removed-list');
      const count = document.getElementById(source + '-removed-count');
      const entries = [...removed.values()].filter(item => item.source === source)
        .sort((a, b) => String(b.removedAt || '').localeCompare(String(a.removedAt || '')));
      list.replaceChildren();
      count.textContent = `(${entries.length})`;
      panel.hidden = entries.length === 0;
      for (const item of entries) {
        const row = document.createElement('li');
        row.className = 'item';
        const tag = document.createElement('span');
        tag.className = 'tag ' + String(item.tag || '');
        tag.textContent = String(item.category || 'Item');
        row.append(tag);
        const title = validLink(item.url) ? document.createElement('a') : document.createElement('span');
        title.className = 't';
        title.textContent = item.title;
        if (title.tagName === 'A') {
          title.href = item.url;
          title.target = '_blank';
          title.rel = 'noopener';
        }
        row.append(title);
        const restore = document.createElement('button');
        restore.type = 'button';
        restore.className = 'save-btn';
        restore.textContent = 'Restore';
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

  function persistSaved(next) {
    try {
      localStorage.setItem(storageKey, JSON.stringify([...next.values()]));
      saved = next;
      syncButtons();
      renderSaved();
    } catch (_) {
      storageError.hidden = false;
    }
  }

  function persistRemoved(next) {
    try {
      localStorage.setItem(removedKey, JSON.stringify([...next.values()]));
      removed = next;
      syncRemoved();
    } catch (_) {
      storageError.hidden = false;
    }
  }

  document.addEventListener('click', event => {
    const button = event.target.closest('button[data-save], button[data-remove-id], button[data-remove-feed], button[data-restore-id]');
    if (!button || !storageAvailable) return;
    if (button.dataset.removeFeed || button.dataset.restoreId) {
      const next = new Map(removed);
      if (button.dataset.restoreId) next.delete(button.dataset.restoreId);
      else {
        const item = sourceItems.get(button.dataset.removeFeed);
        if (!item) return;
        next.set(item.id, {...item, removedAt: new Date().toISOString()});
      }
      persistRemoved(next);
      return;
    }
    const next = new Map(saved);
    if (button.dataset.removeId) next.delete(button.dataset.removeId);
    else if (button.saveItem) {
      const item = button.saveItem;
      if (next.has(item.id)) next.delete(item.id);
      else next.set(item.id, {...item, savedAt: new Date().toISOString()});
    } else return;
    persistSaved(next);
  });

  function showTab(name) {
    const selected = ['career', 'ai', 'saved'].includes(name) ? name : 'career';
    for (const button of tabs) {
      const active = button.dataset.tab === selected;
      button.setAttribute('aria-selected', String(active));
      document.getElementById(button.getAttribute('aria-controls')).hidden = !active;
    }
  }

  function tabFromHash() {
    return location.hash === '#ai-watch' ? 'ai' :
      location.hash === '#saved' ? 'saved' : 'career';
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
  syncRemoved();
  showTab(tabFromHash());
})();
