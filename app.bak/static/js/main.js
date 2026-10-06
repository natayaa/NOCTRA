/* ============================================================
   NOCTRA — Global JS
   ============================================================ */
(function () {
  'use strict';

  function initSidebarToggle() {
    const toggle = document.querySelector('[data-sidebar-toggle]');
    const sidebar = document.querySelector('.admin-sidebar');
    const scrim = document.querySelector('[data-sidebar-scrim]');
    if (!toggle || !sidebar) return;

    function open() {
      sidebar.classList.add('open');
      if (scrim) scrim.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
    function close() {
      sidebar.classList.remove('open');
      if (scrim) scrim.classList.remove('open');
      document.body.style.overflow = '';
    }
    function isOpen() { return sidebar.classList.contains('open'); }

    toggle.addEventListener('click', (e) => {
      e.preventDefault();
      if (isOpen()) close(); else open();
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

  function bindFlash(el) {
    if (!el || el.__noctraFlashBound) return;
    el.__noctraFlashBound = true;

    const closeBtn = el.querySelector('.flash-close');
    closeBtn && closeBtn.addEventListener('click', () => {
      if (window.__noctraFlashDismiss) window.__noctraFlashDismiss(el);
      else el.remove();
    });

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

  function formatRupiah(n) {
    if (n == null || isNaN(n)) return 'Rp 0';
    const s = Math.round(Number(n)).toString();
    return 'Rp ' + s.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }
  window.formatRupiah = formatRupiah;

  function initSlashSearch() {
    document.addEventListener('keydown', (e) => {
      if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
      const active = document.activeElement;
      const tag = (active && active.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
      if (active && active.isContentEditable) return;
      const search = document.querySelector('[data-search-input]');
      if (search) {
        e.preventDefault();
        search.focus();
        if (search.select) search.select();
      }
    });
  }

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

  function initAll() {
    initSidebarToggle();
    initActiveNav();
    initFlash();
    watchFlashMutations();
    initSlashSearch();
    initFormGuards();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  document.addEventListener('htmx:afterSwap', initActiveNav);
})();