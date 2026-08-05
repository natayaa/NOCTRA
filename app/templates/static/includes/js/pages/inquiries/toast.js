// inquiries/toast.js - Toast Notification System (IMPROVED)

import { CONFIG } from "./config.js";
import { DOM } from "./dom.js";

// ✅ Toast type configuration
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

// ✅ Track active toasts untuk limit
let activeToasts = [];
const MAX_TOASTS = 5;

/**
 * Show toast notification
 * @param {string} message - Pesan yang akan ditampilkan
 * @param {string} type - 'success', 'error', 'warning', 'info'
 * @param {number} duration - Durasi dalam ms (optional)
 */
export function showToast(message, type = "info", duration = null) {
  const container = DOM.toastContainer();
  // ✅ Jika container tidak ada, buat secara dinamis
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    document.body.appendChild(container);
    // Tapi pastikan tidak ada duplikasi
  }

  // ✅ Limit active toasts
  if (activeToasts.length >= MAX_TOASTS) {
    const oldest = activeToasts.shift();
    if (oldest && oldest.parentNode) {
      oldest.remove();
    }
  }

  // ✅ Get config for type
  const config = TOAST_CONFIG[type] || TOAST_CONFIG.info;
  const toastDuration = duration || config.duration;

  // ✅ Create toast dengan icon
  const toast = document.createElement("div");
  toast.className = `toast ${config.className}`;
  toast.style.cssText = `
    animation: toastSlideIn 0.3s ease forwards;
  `;

  toast.innerHTML = `
    <div class="toast-content">
      <span class="toast-icon">${config.icon}</span>
      <span class="toast-message">${message}</span>
    </div>
    <button class="toast-close" aria-label="Close notification">&times;</button>
  `;

  // ✅ Add to container
  container.appendChild(toast);
  activeToasts.push(toast);

  // ✅ Close button
  const closeBtn = toast.querySelector(".toast-close");
  closeBtn.addEventListener("click", () => {
    removeToast(toast);
  });

  // ✅ Auto remove after duration
  const timeoutId = setTimeout(() => {
    removeToast(toast);
  }, toastDuration);

  // ✅ Store timeout ID untuk cleanup
  toast._timeoutId = timeoutId;

  // ✅ Click outside to close (optional)
  toast.addEventListener("click", (e) => {
    if (e.target === toast) {
      removeToast(toast);
    }
  });

  return toast;
}

/**
 * Remove toast with animation
 */
function removeToast(toast) {
  if (!toast || !toast.parentNode) return;

  // ✅ Clear timeout
  if (toast._timeoutId) {
    clearTimeout(toast._timeoutId);
    toast._timeoutId = null;
  }

  // ✅ Animate out
  toast.style.animation = "toastSlideOut 0.3s ease forwards";

  setTimeout(() => {
    if (toast.parentNode) {
      toast.remove();
      // Remove from active toasts
      const index = activeToasts.indexOf(toast);
      if (index > -1) {
        activeToasts.splice(index, 1);
      }
    }
  }, 300);
}

/**
 * Clear all toasts
 */
export function clearAllToasts() {
  const container = DOM.toastContainer();
  if (!container) return;

  // Clear all active toasts
  activeToasts.forEach((toast) => {
    if (toast._timeoutId) {
      clearTimeout(toast._timeoutId);
      toast._timeoutId = null;
    }
  });
  activeToasts = [];

  // Clear container
  container.innerHTML = "";
}

/**
 * Show success toast (shortcut)
 */
export function showSuccess(message, duration = null) {
  return showToast(message, "success", duration);
}

/**
 * Show error toast (shortcut)
 */
export function showError(message, duration = null) {
  return showToast(message, "error", duration);
}

/**
 * Show warning toast (shortcut)
 */
export function showWarning(message, duration = null) {
  return showToast(message, "warning", duration);
}

/**
 * Show info toast (shortcut)
 */
export function showInfo(message, duration = null) {
  return showToast(message, "info", duration);
}

// ✅ Add toast animations to document
const style = document.createElement("style");
style.textContent = `
  @keyframes toastSlideIn {
    from {
      opacity: 0;
      transform: translateX(30px) scale(0.95);
    }
    to {
      opacity: 1;
      transform: translateX(0) scale(1);
    }
  }

  @keyframes toastSlideOut {
    from {
      opacity: 1;
      transform: translateX(0) scale(1);
    }
    to {
      opacity: 0;
      transform: translateX(30px) scale(0.95);
    }
  }

  .toast {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-radius: var(--radius-md, 8px);
    background: var(--bg-card, #1e293b);
    border: 1px solid var(--border, #334155);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
    margin-bottom: 8px;
    min-width: 300px;
    max-width: 450px;
    font-size: 0.9rem;
    color: var(--text-primary, #f1f5f9);
    pointer-events: auto;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
  }

  .toast::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
  }

  .toast-success::before {
    background: #10b981;
  }
  .toast-error::before {
    background: #ef4444;
  }
  .toast-warning::before {
    background: #f59e0b;
  }
  .toast-info::before {
    background: #3b82f6;
  }

  .toast:hover {
    transform: translateX(4px);
    border-color: var(--border-hover, #475569);
  }

  .toast-content {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
  }

  .toast-icon {
    font-size: 1.2rem;
    line-height: 1;
    flex-shrink: 0;
  }

  .toast-message {
    flex: 1;
    line-height: 1.4;
    word-break: break-word;
  }

  .toast-close {
    background: none;
    border: none;
    color: var(--text-muted, #94a3b8);
    font-size: 1.3rem;
    cursor: pointer;
    padding: 0 4px;
    line-height: 1;
    transition: color 0.2s ease;
    flex-shrink: 0;
    margin-left: 8px;
  }

  .toast-close:hover {
    color: var(--text-primary, #f1f5f9);
  }

  /* Toast Container */
  #toastContainer {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 99999;
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-width: 450px;
    pointer-events: none;
  }

  #toastContainer .toast {
    pointer-events: auto;
  }

  /* Mobile responsive */
  @media (max-width: 480px) {
    #toastContainer {
      top: 10px;
      right: 10px;
      left: 10px;
      max-width: none;
    }

    .toast {
      min-width: unset;
      max-width: none;
      width: 100%;
      padding: 10px 14px;
      font-size: 0.85rem;
    }
  }
`;

// ✅ Inject styles if not already present
if (!document.querySelector("#toast-styles")) {
  style.id = "toast-styles";
  document.head.appendChild(style);
}

// ✅ Export default
export default {
  showToast,
  showSuccess,
  showError,
  showWarning,
  showInfo,
  clearAllToasts,
};
