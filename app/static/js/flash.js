/* ============================================================
   NOCTRA — Flash message API
   ============================================================ */
(function () {
  'use strict';

  const ICONS = {
    success: 'M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4L12 14.01l-3-3',
    error:   'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM15 9l-6 6M9 9l6 6',
    warning: 'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01',
    info:    'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 16v-4M12 8h.01',
  };

  function ensureStack() {
    let stack = document.querySelector('.flash-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.className = 'flash-stack';
      stack.setAttribute('role', 'region');
      stack.setAttribute('aria-label', 'Notifications');
      stack.setAttribute('aria-live', 'polite');
      document.body.appendChild(stack);
    }
    return stack;
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function dismiss(el) {
    if (!el || el.__noctraDismissed) return;
    el.__noctraDismissed = true;
    el.style.transition = 'opacity 200ms ease, transform 200ms ease';
    el.style.opacity = '0';
    el.style.transform = 'translateY(-6px)';
    setTimeout(() => el.remove(), 220);
  }

  function push(kind, message, opts) {
    opts = opts || {};
    const timeout = opts.timeout == null
      ? (kind === 'error' ? 6000 : 4000)
      : opts.timeout;
    const icon = ICONS[kind] || ICONS.info;

    const stack = ensureStack();
    const el = document.createElement('div');
    el.className = `flash flash-${kind}`;
    el.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    if (timeout > 0) {
      el.setAttribute('data-auto-dismiss', String(timeout));
      el.style.setProperty('--flash-duration', `${timeout}ms`);
    }

    el.innerHTML = `
      <svg class="flash-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="${icon}" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <div class="flex-1">${escapeHtml(message)}</div>
      <button type="button" class="flash-close" aria-label="Dismiss">×</button>
    `;

    /* Cegah MutationObserver di main.js melakukan double-bind */
    el.__noctraFlashBound = true;

    stack.appendChild(el);

    el.querySelector('.flash-close')?.addEventListener('click', () => dismiss(el));
    if (timeout > 0) setTimeout(() => dismiss(el), timeout);
    return el;
  }

  window.noctraFlash = {
    success: (m, o) => push('success', m, o),
    error:   (m, o) => push('error',   m, o),
    warning: (m, o) => push('warning', m, o),
    info:    (m, o) => push('info',    m, o),
  };
  window.__noctraFlashDismiss = dismiss;
})();