/* ============================================================
   NOCTRA — Confirm dialog
   Usage:
     <a href="/x" data-confirm="Delete this item?">Delete</a>
     <form data-confirm="Delete user?">…</form>
     <button data-confirm="…">…</button>
   ============================================================ */
(function () {
  'use strict';

  function shouldCancel(el) {
    const message = el.getAttribute('data-confirm') || 'Are you sure?';
    return !window.confirm(message);
  }

  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-confirm]');
    if (!el) return;

    // A submit button inside a form[data-confirm] is handled by the submit listener.
    if (el.tagName === 'BUTTON' && (el.type === 'submit' || !el.type)) {
      if (el.closest('form[data-confirm]')) return;
    }

    if (shouldCancel(el)) {
      e.preventDefault();
      e.stopImmediatePropagation();
    }
  }, true);

  document.addEventListener('submit', (e) => {
    const form = e.target.closest('form[data-confirm]');
    if (!form) return;

    // Skip if a submit button already cancelled via the click handler.
    if (e.defaultPrevented) return;

    if (shouldCancel(form)) {
      e.preventDefault();
      e.stopImmediatePropagation();
    }
  }, true);
})();