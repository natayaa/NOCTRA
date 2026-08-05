// projects/toast.js - Toast System (FIXED & IMPROVED)

import { CONFIG } from "./config.js";
import { DOM } from "./dom.js";

// ✅ Toast configuration
const TOAST_CONFIG = {
  success: {
    icon: "✅",
    className: "toast-success",
    duration: CONFIG.TOAST_DURATION || 4000,
  },
  error: {
    icon: "❌",
    className: "toast-error",
    duration: CONFIG.TOAST_DURATION || 5000,
  },
  warning: {
    icon: "⚠️",
    className: "toast-warning",
    duration: CONFIG.TOAST_DURATION || 4000,
  },
  info: {
    icon: "ℹ️",
    className: "toast-info",
    duration: CONFIG.TOAST_DURATION || 3000,
  },
};

let activeToasts = [];
const MAX_TOASTS = 5;

export function showToast(message, type = "info", duration = null) {
  const container = DOM.toastContainer();
  if (!container) {
    console.warn("Toast container not found");
    return;
  }

  // ✅ Limit active toasts
  if (activeToasts.length >= MAX_TOASTS) {
    const oldest = activeToasts.shift();
    if (oldest?.parentNode) oldest.remove();
  }

  const config = TOAST_CONFIG[type] || TOAST_CONFIG.info;
  const toastDuration = duration || config.duration;

  const toast = document.createElement("div");
  toast.className = `toast ${config.className}`;
  toast.style.animation = "toastSlideIn 0.3s ease forwards";

  toast.innerHTML = `
    <div class="toast-content">
      <span class="toast-icon">${config.icon}</span>
      <span class="toast-message">${message}</span>
    </div>
    <button class="toast-close" aria-label="Close notification">&times;</button>
  `;

  container.appendChild(toast);
  activeToasts.push(toast);

  // ✅ Close button
  const closeBtn = toast.querySelector(".toast-close");
  closeBtn.addEventListener("click", () => removeToast(toast));

  // ✅ Auto remove after duration
  const timeoutId = setTimeout(() => removeToast(toast), toastDuration);
  toast._timeoutId = timeoutId;

  // ✅ Click on toast to close
  toast.addEventListener("click", (e) => {
    if (e.target === toast) removeToast(toast);
  });

  return toast;
}

function removeToast(toast) {
  if (!toast?.parentNode) return;

  if (toast._timeoutId) {
    clearTimeout(toast._timeoutId);
    toast._timeoutId = null;
  }

  toast.style.animation = "toastSlideOut 0.3s ease forwards";

  setTimeout(() => {
    if (toast.parentNode) {
      toast.remove();
      const index = activeToasts.indexOf(toast);
      if (index > -1) activeToasts.splice(index, 1);
    }
  }, 300);
}

export function clearAllToasts() {
  const container = DOM.toastContainer();
  if (!container) return;

  activeToasts.forEach((toast) => {
    if (toast._timeoutId) {
      clearTimeout(toast._timeoutId);
      toast._timeoutId = null;
    }
  });
  activeToasts = [];
  container.innerHTML = "";
}

// ✅ Shortcut functions
export const showSuccess = (message, duration = null) =>
  showToast(message, "success", duration);
export const showError = (message, duration = null) =>
  showToast(message, "error", duration);
export const showWarning = (message, duration = null) =>
  showToast(message, "warning", duration);
export const showInfo = (message, duration = null) =>
  showToast(message, "info", duration);

// ✅ Inject styles
const style = document.createElement("style");
style.id = "toast-styles-projects";
style.textContent = `
  @keyframes toastSlideIn {
    from { opacity: 0; transform: translateX(30px) scale(0.95); }
    to { opacity: 1; transform: translateX(0) scale(1); }
  }
  @keyframes toastSlideOut {
    from { opacity: 1; transform: translateX(0) scale(1); }
    to { opacity: 0; transform: translateX(30px) scale(0.95); }
  }
  .toast {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px; border-radius: var(--radius-md, 8px);
    background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155);
    box-shadow: 0 8px 30px rgba(0,0,0,0.4); margin-bottom: 8px;
    min-width: 280px; max-width: 450px; font-size: 0.9rem;
    color: var(--text-primary, #f1f5f9); pointer-events: auto;
    position: relative; overflow: hidden;
  }
  .toast::before {
    content: ''; position: absolute; top: 0; left: 0;
    width: 4px; height: 100%;
  }
  .toast-success::before { background: #10b981; }
  .toast-error::before { background: #ef4444; }
  .toast-warning::before { background: #f59e0b; }
  .toast-info::before { background: #3b82f6; }
  .toast:hover { transform: translateX(4px); border-color: var(--border-hover, #475569); }
  .toast-content { display: flex; align-items: center; gap: 10px; flex: 1; }
  .toast-icon { font-size: 1.2rem; line-height: 1; flex-shrink: 0; }
  .toast-message { flex: 1; line-height: 1.4; word-break: break-word; }
  .toast-close {
    background: none; border: none; color: var(--text-muted, #94a3b8);
    font-size: 1.3rem; cursor: pointer; padding: 0 4px; line-height: 1;
    flex-shrink: 0; margin-left: 8px; transition: color 0.2s ease;
  }
  .toast-close:hover { color: var(--text-primary, #f1f5f9); }
  #toastContainer {
    position: fixed; top: 20px; right: 20px; z-index: 99999;
    display: flex; flex-direction: column; gap: 6px;
    max-width: 450px; pointer-events: none;
  }
  #toastContainer .toast { pointer-events: auto; }
  @media (max-width: 480px) {
    #toastContainer { top: 10px; right: 10px; left: 10px; max-width: none; }
    .toast { min-width: unset; max-width: none; width: 100%; padding: 10px 14px; font-size: 0.85rem; }
  }
`;

if (!document.querySelector("#toast-styles-projects")) {
  document.head.appendChild(style);
}

export default {
  showToast,
  showSuccess,
  showError,
  showWarning,
  showInfo,
  clearAllToasts,
};
