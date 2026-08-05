// ============================================================
// payments/toast.js - Toast System
// ============================================================

import { CONFIG } from "./config.js";
import { DOM } from "./dom.js";

export function showToast(
  message,
  type = "info",
  duration = CONFIG.TOAST_DURATION,
) {
  const container = DOM.toastContainer();
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
        <span>${message}</span>
        <button class="toast-close">&times;</button>
    `;

  container.appendChild(toast);

  toast.querySelector(".toast-close").addEventListener("click", () => {
    toast.remove();
  });

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-10px)";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}
