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

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isOpen()) close();
    });

    document.addEventListener('htmx:beforeSwap', close);

    window.addEventListener('resize', () => {
      if (window.innerWidth > 900 && isOpen()) close();
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

    if (bestMatch) {
      bestMatch.link.classList.add('active');
      bestMatch.link.setAttribute('aria-current', 'page');
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

  /* ── Search shortcuts + dropdown dismiss ──────── */
  function initSearchShortcuts() {
    if (window.__noctraSearchShortcut) return;
    window.__noctraSearchShortcut = true;

    function focusSearch() {
      const input = document.querySelector('[data-search-input]');
      if (!input) return false;
      input.focus();
      if (input.select) input.select();
      return true;
    }

    document.addEventListener('keydown', (e) => {
      // ⌘K / Ctrl+K
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        if (focusSearch()) e.preventDefault();
        return;
      }
      // "/" — hanya kalau tidak sedang mengetik di input/textarea/select
      if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const a = document.activeElement;
        const tag = (a && a.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
        if (a && a.isContentEditable) return;
        if (focusSearch()) e.preventDefault();
      }
    });

    // Escape menutup semua <details> dropdown
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      document.querySelectorAll('details[open]').forEach((d) => (d.open = false));
    });

    // Klik di luar menutup dropdown user
    document.addEventListener('click', (e) => {
      document.querySelectorAll('details.user-menu[open]').forEach((d) => {
        if (!d.contains(e.target)) d.open = false;
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
    initActiveNav();
    initFlash();
    watchFlashMutations();
    initSearchShortcuts();
    initFormGuards();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  document.addEventListener('htmx:afterSwap', initActiveNav);
})();