/* ============================================================
   NOCTRA — Command palette (⌘K / Ctrl+K)
   Indexes the sidebar plus a handful of quick-create actions.
   ============================================================ */
(function () {
  'use strict';

  function svg(path) {
    return '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
      '<path d="' + path + '" stroke="currentColor" stroke-width="1.75" ' +
      'stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }

  var ACTIONS = [
    { label: 'New inquiry', href: '/admin/inquiries/new', icon: svg('M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2zM12 8v6M9 11h6') },
    { label: 'New customer', href: '/admin/customers/new', icon: svg('M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM19 8v6M16 11h6') },
    { label: 'New project', href: '/admin/projects/new', icon: svg('M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2zM12 10v6M9 13h6') },
    { label: 'New invoice', href: '/admin/invoices/new', icon: svg('M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M12 12v6M9 15h6') },
    { label: 'New purchase order', href: '/admin/purchase-orders/new', icon: svg('M9 22a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm11 0a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6M14 9v4M12 11h4') },
    { label: 'New expense', href: '/admin/expenses/new', icon: svg('M4 2v20l4-2 4 2 4-2 4 2V2l-4 2-4-2-4 2zM12 8v6M9 11h6') },
  ];

  function init() {
    var dialog = document.querySelector('[data-command-dialog]');
    var input = document.querySelector('[data-command-input]');
    var results = document.querySelector('[data-command-results]');
    if (!dialog || !input || !results) return;

    var items = [];
    var filtered = [];
    var activeIndex = 0;
    var built = false;

    function buildIndex() {
      if (built) return;
      built = true;

      ACTIONS.forEach(function (a) {
        items.push({ label: a.label, href: a.href, group: 'Create', hint: '', icon: a.icon });
      });

      document.querySelectorAll('.sidebar-link').forEach(function (link) {
        var label = (link.textContent || '').trim();
        var href = link.getAttribute('href');
        if (!label || !href) return;
        var groupEl = link.closest('[data-nav-group]');
        var iconEl = link.querySelector('svg');
        items.push({
          label: label,
          href: href,
          group: groupEl ? groupEl.getAttribute('data-nav-group') : 'Pages',
          hint: '',
          icon: iconEl ? iconEl.outerHTML : '',
        });
      });
    }

    function normalize(v) {
      return String(v || '').toLowerCase();
    }

    function filter(query) {
      var tokens = normalize(query).split(/\s+/).filter(Boolean);
      if (!tokens.length) return items.slice();

      var scored = [];
      items.forEach(function (item, order) {
        var label = normalize(item.label);
        var hay = label + ' ' + normalize(item.group) + ' ' + normalize(item.href);
        var score = 0;
        for (var i = 0; i < tokens.length; i++) {
          var t = tokens[i];
          if (hay.indexOf(t) === -1) return;
          if (label.indexOf(t) === 0) score += 60;
          else if (label.indexOf(t) !== -1) score += 30;
          else score += 10;
        }
        scored.push({ item: item, score: score, order: order });
      });

      scored.sort(function (a, b) {
        return b.score - a.score || a.order - b.order;
      });
      return scored.map(function (s) { return s.item; });
    }

    function emptyMarkup() {
      return '<div class="cmd-empty">' +
        svg('M21 21l-4.35-4.35M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z') +
        '<div class="cmd-empty-title">No matches</div>' +
        '<div class="cmd-empty-sub">Try a page name like “invoices” or an action like “new”.</div>' +
        '</div>';
    }

    function render() {
      results.innerHTML = '';

      if (!filtered.length) {
        results.innerHTML = emptyMarkup();
        input.removeAttribute('aria-activedescendant');
        return;
      }

      var currentGroup = null;
      filtered.forEach(function (item, index) {
        if (item.group !== currentGroup) {
          currentGroup = item.group;
          var label = document.createElement('div');
          label.className = 'cmd-group-label';
          label.setAttribute('role', 'presentation');
          label.textContent = item.group;
          results.appendChild(label);
        }

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'cmd-item';
        btn.id = 'cmd-option-' + index;
        btn.dataset.index = String(index);
        btn.setAttribute('role', 'option');
        btn.setAttribute('aria-selected', 'false');

        var icon = document.createElement('span');
        icon.className = 'cmd-icon';
        if (item.icon) icon.innerHTML = item.icon;

        var body = document.createElement('span');
        body.className = 'cmd-item-body';
        var text = document.createElement('span');
        text.className = 'cmd-item-label';
        text.textContent = item.label;
        body.appendChild(text);

        var hint = document.createElement('span');
        hint.className = 'cmd-item-hint';
        hint.textContent = item.hint || '';

        btn.appendChild(icon);
        btn.appendChild(body);
        if (item.hint) btn.appendChild(hint);
        results.appendChild(btn);
      });

      results.scrollTop = 0;
      setActive(0, true);
    }

    function setActive(index, skipScroll) {
      if (!filtered.length) return;
      activeIndex = Math.max(0, Math.min(index, filtered.length - 1));

      var nodes = results.querySelectorAll('.cmd-item');
      nodes.forEach(function (node) {
        var isActive = Number(node.dataset.index) === activeIndex;
        node.classList.toggle('is-active', isActive);
        node.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });

      var active = document.getElementById('cmd-option-' + activeIndex);
      if (active) {
        input.setAttribute('aria-activedescendant', active.id);
        if (!skipScroll) active.scrollIntoView({ block: 'nearest' });
      }
    }

    function activate(index) {
      var item = filtered[index];
      if (!item) return;
      window.location.href = item.href;
    }

    function refresh() {
      filtered = filter(input.value);
      render();
    }

    function open() {
      buildIndex();
      if (!dialog.open) dialog.showModal();
      input.value = '';
      refresh();
      requestAnimationFrame(function () { input.focus(); });
    }

    function close() {
      if (dialog.open) dialog.close();
    }

    function toggle() {
      if (dialog.open) close();
      else open();
    }

    /* Triggers */
    document.addEventListener('click', function (e) {
      var trigger = e.target.closest && e.target.closest('[data-command-open]');
      if (trigger) {
        e.preventDefault();
        open();
      }
    });

    /* Filtering */
    input.addEventListener('input', refresh);

    /* Keyboard navigation */
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActive(activeIndex + 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActive(activeIndex - 1);
      } else if (e.key === 'Home') {
        e.preventDefault();
        setActive(0);
      } else if (e.key === 'End') {
        e.preventDefault();
        setActive(filtered.length - 1);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        activate(activeIndex);
      }
    });

    results.addEventListener('click', function (e) {
      var btn = e.target.closest && e.target.closest('.cmd-item');
      if (btn) activate(Number(btn.dataset.index));
    });

    results.addEventListener('mouseover', function (e) {
      var btn = e.target.closest && e.target.closest('.cmd-item');
      if (!btn) return;
      var index = Number(btn.dataset.index);
      if (index !== activeIndex) setActive(index, true);
    });

    dialog.addEventListener('close', function () {
      input.value = '';
    });

    dialog.addEventListener('click', function (e) {
      if (e.target === dialog) close();
    });

    /* Global shortcut — also handles "/" outside form fields */
    document.addEventListener('keydown', function (e) {
      var mod = e.metaKey || e.ctrlKey;
      if (mod && !e.altKey && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        toggle();
        return;
      }

      if (e.key === '/' && !mod && !e.altKey && !dialog.open) {
        var el = document.activeElement;
        var tag = el && el.tagName ? el.tagName.toLowerCase() : '';
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || (el && el.isContentEditable)) return;
        e.preventDefault();
        open();
      }
    });

    /* Platform-aware shortcut hint */
    var platform = (navigator.userAgentData && navigator.userAgentData.platform) ||
      navigator.platform || '';
    var isMac = /mac|iphone|ipad|ipod/i.test(platform);
    document.querySelectorAll('[data-shortcut-hint]').forEach(function (el) {
      el.textContent = isMac ? '⌘K' : 'Ctrl K';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
