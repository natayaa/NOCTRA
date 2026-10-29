/* ============================================================
   NOCTRA — Global JS
   ============================================================ */
(function () {
  'use strict';

  /* ── Sidebar drawer (mobile) ──────────────────── */
  function initSidebarToggle() {
    const toggle  = document.querySelector('[data-sidebar-toggle]');
    const sidebar = document.querySelector('.admin-sidebar');
    const scrim   = document.querySelector('[data-sidebar-scrim]');
    if (!toggle || !sidebar) return;

    function syncAria(open) {
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    }
    function open() {
      sidebar.classList.add('open');
      if (scrim) scrim.classList.add('open');
      document.body.style.overflow = 'hidden';
      syncAria(true);
    }
    function close() {
      sidebar.classList.remove('open');
      if (scrim) scrim.classList.remove('open');
      document.body.style.overflow = '';
      syncAria(false);
    }
    function isOpen() { return sidebar.classList.contains('open'); }

    toggle.addEventListener('click', (e) => {
      e.preventDefault();
      isOpen() ? close() : open();
    });

    if (scrim) scrim.addEventListener('click', close);

    const closeBtn = sidebar.querySelector('[data-sidebar-close]');
    if (closeBtn) closeBtn.addEventListener('click', close);

    sidebar.querySelectorAll('.sidebar-link').forEach((link) => {
      link.addEventListener('click', () => {
        if (isOpen()) close();
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isOpen()) {
        close();
        toggle.focus();
      }
    });

    document.addEventListener('htmx:beforeSwap', close);

    window.addEventListener('resize', () => {
      if (window.innerWidth > 900 && isOpen()) close();
    });
  }

  /* ── Collapsible sidebar groups ───────────────── */
  const NAV_STORAGE_KEY = 'noctra.nav.collapsed';

  function readCollapsedNav() {
    try {
      const raw = localStorage.getItem(NAV_STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (err) {
      return {};
    }
  }

  function initSidebarGroups() {
    const groups = document.querySelectorAll('[data-nav-key]');
    if (!groups.length) return;

    const collapsed = readCollapsedNav();

    groups.forEach((group) => {
      const key = group.getAttribute('data-nav-key');
      const toggle = group.querySelector('[data-nav-toggle]');
      const panel = group.querySelector('.sidebar-group-items');
      if (!toggle || !panel) return;

      function apply(isCollapsed) {
        group.classList.toggle('is-collapsed', isCollapsed);
        toggle.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
      }

      apply(collapsed[key] === true);

      toggle.addEventListener('click', () => {
        const next = !group.classList.contains('is-collapsed');
        apply(next);
        collapsed[key] = next;
        try {
          localStorage.setItem(NAV_STORAGE_KEY, JSON.stringify(collapsed));
        } catch (err) { /* storage unavailable — collapse still works */ }
      });
    });
  }

  /* ── Active sidebar link ──────────────────────── */
  function normalize(p) {
    if (!p) return '';
    let s = String(p).split('?')[0].split('#')[0];
    if (s.length > 1 && s.endsWith('/')) s = s.slice(0, -1);
    return s;
  }

  function initActiveNav() {
    const path = normalize(window.location.pathname);
    let bestMatch = null;

    document.querySelectorAll('.sidebar-link').forEach((link) => {
      const href = link.getAttribute('href');
      if (!href) return;
      const target = normalize(href);
      if (!target) return;

      const matches =
        path === target ||
        (target !== '/' && path.startsWith(target + '/'));

      if (matches) {
        if (!bestMatch || target.length > bestMatch.target.length) {
          bestMatch = { link, target };
        }
      }
    });

    document.querySelectorAll('.sidebar-link').forEach((el) => {
      el.classList.remove('active');
      el.removeAttribute('aria-current');
    });
    document.querySelectorAll('.sidebar-group').forEach((el) => {
      el.classList.remove('has-active');
    });

    if (bestMatch) {
      bestMatch.link.classList.add('active');
      bestMatch.link.setAttribute('aria-current', 'page');

      // Mark the owning group so the section stays recognisable even when
      // the group is collapsed, and keep the link inside the scroll viewport.
      const group = bestMatch.link.closest('.sidebar-group');
      if (group) group.classList.add('has-active');
      bestMatch.link.scrollIntoView({ block: 'nearest' });
    }
  }

  /* ── Flash binding ────────────────────────────── */
  function bindFlash(el) {
    if (!el || el.__noctraFlashBound) return;
    el.__noctraFlashBound = true;

    const closeBtn = el.querySelector('.flash-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        if (window.__noctraFlashDismiss) window.__noctraFlashDismiss(el);
        else el.remove();
      });
    }

    const delay = parseInt(el.getAttribute('data-auto-dismiss') || '0', 10);
    if (delay > 0) {
      setTimeout(() => {
        if (window.__noctraFlashDismiss) window.__noctraFlashDismiss(el);
        else el.remove();
      }, delay);
    }
  }

  function initFlash() {
    document.querySelectorAll('.flash').forEach(bindFlash);
  }

  function watchFlashMutations() {
    if (!window.MutationObserver) return;
    const observer = new MutationObserver((mutations) => {
      for (let i = 0; i < mutations.length; i++) {
        const added = mutations[i].addedNodes;
        if (!added) continue;
        for (let j = 0; j < added.length; j++) {
          const node = added[j];
          if (!(node instanceof Element)) continue;
          if (node.classList && node.classList.contains('flash')) bindFlash(node);
          if (node.querySelectorAll) node.querySelectorAll('.flash').forEach(bindFlash);
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  /* ── Rupiah formatter (global) ────────────────── */
  function formatRupiah(n) {
    if (n == null || isNaN(n)) return 'Rp 0';
    const s = Math.round(Number(n)).toString();
    return 'Rp ' + s.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }
  window.formatRupiah = formatRupiah;

  /* ── Filter tabs: keep the active tab visible ─── */
  function initFilterTabs() {
    const bars = document.querySelectorAll('.filter-tabs');
    if (!bars.length) return;

    bars.forEach((bar) => {
      const active = bar.querySelector('.filter-tab.is-active');
      if (!active) return;
      const start = active.offsetLeft - 16;
      const end = start + active.offsetWidth + 32;
      if (start < bar.scrollLeft) {
        bar.scrollLeft = start;
      } else if (end > bar.scrollLeft + bar.clientWidth) {
        bar.scrollLeft = end - bar.clientWidth;
      }
    });
  }

  /* ── Dropdown dismiss ─────────────────────────── */
  function initDropdownDismiss() {
    if (window.__noctraDropdowns) return;
    window.__noctraDropdowns = true;

    // Escape menutup semua <details> dropdown
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      document.querySelectorAll('details[open]').forEach((d) => (d.open = false));
    });

    // Klik di luar menutup dropdown (user menu, quick-create)
    document.addEventListener('click', (e) => {
      document
        .querySelectorAll('details.user-menu[open], details.topbar-menu[open]')
        .forEach((d) => {
          if (!d.contains(e.target)) d.open = false;
        });

      // A selected menu item leaves the panel behind when navigation is slow.
      const item = e.target.closest &&
        e.target.closest('.user-menu-panel a, .topbar-menu-panel a');
      if (item) {
        const menu = item.closest('details');
        if (menu) menu.open = false;
      }
    });

    // Only one header disclosure stays open at a time.
    document
      .querySelectorAll('details.user-menu, details.topbar-menu')
      .forEach((d) => {
        d.addEventListener('toggle', () => {
          if (!d.open) return;
          document
            .querySelectorAll('details.user-menu[open], details.topbar-menu[open]')
            .forEach((other) => {
              if (other !== d) other.open = false;
            });
        });
      });
  }

  /* ── Password visibility toggles ──────────────── */
  function initPasswordToggles() {
    document.querySelectorAll('[data-password-toggle]').forEach((btn) => {
      if (btn.__noctraPwBound) return;
      btn.__noctraPwBound = true;

      btn.addEventListener('click', () => {
        const wrap = btn.closest('.input-wrap, .auth-input');
        const input = wrap ? wrap.querySelector('input') : null;
        if (!input) return;

        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        btn.classList.toggle('is-visible', show);
        btn.setAttribute('aria-pressed', show ? 'true' : 'false');
        btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
      });
    });
  }

  /* ── Form guards (prevent double-submit) ──────── */
  function initFormGuards() {
    document.querySelectorAll('form[data-guard]').forEach((form) => {
      if (form.__noctraGuardBound) return;
      form.__noctraGuardBound = true;

      form.addEventListener('submit', () => {
        const btn = form.querySelector('button[type="submit"]');
        if (!btn || btn.disabled) return;
        btn.disabled = true;
        btn.dataset.originalHtml = btn.innerHTML;
        btn.innerHTML = '<span class="spinner"></span> <span>Processing…</span>';
      });

      form.addEventListener('invalid', () => {
        const btn = form.querySelector('button[type="submit"]');
        if (btn && btn.dataset.originalHtml) {
          btn.disabled = false;
          btn.innerHTML = btn.dataset.originalHtml;
        }
      }, true);

      form.addEventListener('submit', () => {
        const btn = form.querySelector('button[type="submit"]');
        setTimeout(() => {
          if (btn && btn.disabled && document.contains(form)) {
            btn.disabled = false;
            if (btn.dataset.originalHtml) btn.innerHTML = btn.dataset.originalHtml;
          }
        }, 15000);
      });
    });
  }

  function resetGuard(form) {
    if (!form) return;
    const btn = form.querySelector('button[type="submit"]');
    if (btn && btn.dataset.originalHtml) {
      btn.disabled = false;
      btn.innerHTML = btn.dataset.originalHtml;
    }
  }

  document.addEventListener('htmx:afterRequest', (e) => {
    const form = e.target.closest && e.target.closest('form[data-guard]');
    if (form) resetGuard(form);
  });

  /* ── Boot ─────────────────────────────────────── */
  function initAll() {
    initSidebarToggle();
    initSidebarGroups();
    initActiveNav();
    initFilterTabs();
    initFlash();
    watchFlashMutations();
    initDropdownDismiss();
    initPasswordToggles();
    initFormGuards();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  document.addEventListener('htmx:afterSwap', initActiveNav);
})();