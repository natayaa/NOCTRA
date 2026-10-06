/* ============================================================
   NOCTRA — HTMX defaults
   ============================================================ */
(function () {
  'use strict';

  if (!window.htmx) return;

  document.body.addEventListener('htmx:responseError', (e) => {
    const status = e.detail.xhr.status;
    if (status === 401) {
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = '/admin/login?next=' + next;
    } else if (status === 403) {
      window.noctraFlash && window.noctraFlash.error('You do not have permission to perform this action.');
    } else if (status >= 500) {
      window.noctraFlash && window.noctraFlash.error('Server error. Please try again or contact support.');
    }
  });

  document.body.addEventListener('htmx:sendError', () => {
    window.noctraFlash && window.noctraFlash.error('Network error. Check your connection.');
  });

  let slowTimer = null;
  let cursorActive = false;

  function clearSlow() {
    if (slowTimer) { clearTimeout(slowTimer); slowTimer = null; }
    if (cursorActive) {
      document.documentElement.style.cursor = '';
      cursorActive = false;
    }
  }

  document.body.addEventListener('htmx:beforeRequest', () => {
    clearSlow();
    slowTimer = setTimeout(() => {
      document.documentElement.style.cursor = 'progress';
      cursorActive = true;
    }, 500);
  });

  document.body.addEventListener('htmx:afterRequest', clearSlow);
  window.addEventListener('beforeunload', clearSlow);
})();