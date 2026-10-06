/* ============================================================
   NOCTRA — CSRF header injector
   Reads the meta tag first, cookie as fallback.
   ============================================================ */
(function () {
  'use strict';

  const metaCookie = document.querySelector('meta[name="csrf-cookie-name"]');
  const metaHeader = document.querySelector('meta[name="csrf-header-name"]');
  const metaToken  = document.querySelector('meta[name="csrf-token"]');

  const COOKIE_NAME = (metaCookie && metaCookie.content) || 'noctra_csrf';
  const HEADER_NAME = (metaHeader && metaHeader.content) || 'X-CSRF-Token';
  const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE']);

  function getCookie(name) {
    const m = document.cookie.match(
      new RegExp('(?:^|; )' + name.replace(/[.$?*|{}()[\]\\/+^]/g, '\\$&') + '=([^;]*)')
    );
    return m ? decodeURIComponent(m[1]) : null;
  }

  function getCsrfToken() {
    if (metaToken && metaToken.content) return metaToken.content;
    return getCookie(COOKIE_NAME);
  }

  function applyHeader(headers, token) {
    if (!token) return headers;
    const h = new Headers(headers || undefined);
    if (!h.has(HEADER_NAME)) h.set(HEADER_NAME, token);
    return h;
  }

  const originalFetch = window.fetch;
  window.fetch = function (input, init) {
    init = init || {};
    const method = (
      init.method ||
      (input && typeof input === 'object' && input.method) ||
      'GET'
    ).toUpperCase();

    if (!SAFE_METHODS.has(method)) {
      const token = getCsrfToken();
      if (token) {
        init.headers = applyHeader(
          init.headers || (input && typeof input === 'object' ? input.headers : undefined),
          token
        );
      }
    }
    return originalFetch.call(this, input, init);
  };

  const originalOpen = XMLHttpRequest.prototype.open;
  const originalSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function (method, url) {
    this.__noctraMethod = String(method || 'GET').toUpperCase();
    return originalOpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function () {
    if (!SAFE_METHODS.has(this.__noctraMethod || 'GET')) {
      const token = getCsrfToken();
      if (token) {
        try { this.setRequestHeader(HEADER_NAME, token); } catch (_) {}
      }
    }
    return originalSend.apply(this, arguments);
  };

  document.addEventListener('htmx:configRequest', (e) => {
    const method = (e.detail.verb || 'get').toUpperCase();
    if (!SAFE_METHODS.has(method)) {
      const token = getCsrfToken();
      if (token) e.detail.headers[HEADER_NAME] = token;
    }
  });

  window.__noctraCsrf = { getCsrfToken, COOKIE_NAME, HEADER_NAME };
})();