/* ============================================================
   NOCTRA — Flash message API
   ============================================================ */
(function () {
  'use strict';

  function ensureStack() {
    let stack = document.querySelector('.flash-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.className = 'flash-stack';
      stack.setAttribute('role', 'region');
      stack.setAttribute('aria-label', 'Notifications');
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

    const stack = ensureStack();
    const el = document.createElement('div');
    el.className = `flash flash-${kind}`;
    el.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    if (timeout > 0) el.setAttribute('data-auto-dismiss', String(timeout));
    el.innerHTML = `
      <div class="flash-body">${escapeHtml(message)}</div>
      <button type="button" class="flash-close" aria-label="Dismiss">×</button>
    `;
    stack.appendChild(el);

    const closeBtn = el.querySelector('.flash-close');
    if (closeBtn) closeBtn.addEventListener('click', () => dismiss(el));

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