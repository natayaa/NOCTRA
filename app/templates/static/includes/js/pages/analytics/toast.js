// static/js/pages/analytics/toast.js
// ============================================================
// Analytics Toast System
// ============================================================

import { CONFIG } from "./config.js";

// ============================================================
// TOAST CONFIG
// ============================================================

const TOAST_CONFIG = {
  success: {
    icon: "✅",
    className: "toast-success",
    duration: CONFIG.TOAST_DURATION || 4000,
  },
  error: {
    icon: "❌",
    className: "toast-error",
    duration: (CONFIG.TOAST_DURATION || 4000) + 1000,
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

// ============================================================
// TOAST CONTAINER
// ============================================================

function getContainer() {
  let container = document.getElementById("analyticsToastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "analyticsToastContainer";
    container.className = "analytics-toast-container";
    container.setAttribute("aria-live", "polite");
    container.setAttribute("aria-atomic", "true");
    document.body.appendChild(container);
  }
  return container;
}

// ============================================================
// MAIN TOAST FUNCTION
// ============================================================

export function showToast(message, type = "info", duration = null) {
  const container = getContainer();
  if (!container) {
    console.warn("Analytics toast container not found");
    return;
  }

  // Limit active toasts
  if (activeToasts.length >= MAX_TOASTS) {
    const oldest = activeToasts.shift();
    if (oldest?.parentNode) {
      oldest.remove();
    }
  }

  const config = TOAST_CONFIG[type] || TOAST_CONFIG.info;
  const toastDuration = duration || config.duration;

  // Create toast element
  const toast = document.createElement("div");
  toast.className = `analytics-toast ${config.className}`;
  toast.style.animation = "analyticsToastSlideIn 0.35s ease forwards";
  toast.setAttribute("role", "alert");

  toast.innerHTML = `
    <div class="analytics-toast-content">
      <span class="analytics-toast-icon">${config.icon}</span>
      <span class="analytics-toast-message">${message}</span>
    </div>
    <button class="analytics-toast-close" aria-label="Close notification">&times;</button>
  `;

  container.appendChild(toast);
  activeToasts.push(toast);

  // Close button
  const closeBtn = toast.querySelector(".analytics-toast-close");
  closeBtn.addEventListener("click", () => removeToast(toast));

  // Auto remove after duration
  const timeoutId = setTimeout(() => removeToast(toast), toastDuration);
  toast._timeoutId = timeoutId;

  // Click on toast body to close
  toast.addEventListener("click", (e) => {
    if (e.target === toast || e.target.closest(".analytics-toast-content")) {
      removeToast(toast);
    }
  });

  return toast;
}

// ============================================================
// REMOVE TOAST
// ============================================================

function removeToast(toast) {
  if (!toast?.parentNode) return;

  if (toast._timeoutId) {
    clearTimeout(toast._timeoutId);
    toast._timeoutId = null;
  }

  toast.style.animation = "analyticsToastSlideOut 0.3s ease forwards";

  setTimeout(() => {
    if (toast.parentNode) {
      toast.remove();
      const index = activeToasts.indexOf(toast);
      if (index > -1) {
        activeToasts.splice(index, 1);
      }
    }
  }, 300);
}

// ============================================================
// CLEAR ALL TOASTS
// ============================================================

export function clearAllToasts() {
  const container = getContainer();
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

// ============================================================
// SHORTCUT FUNCTIONS
// ============================================================

export const showSuccess = (message, duration = null) =>
  showToast(message, "success", duration);

export const showError = (message, duration = null) =>
  showToast(message, "error", duration);

export const showWarning = (message, duration = null) =>
  showToast(message, "warning", duration);

export const showInfo = (message, duration = null) =>
  showToast(message, "info", duration);

// ============================================================
// INJECT TOAST STYLES
// ============================================================

function injectStyles() {
  if (document.querySelector("#analytics-toast-styles")) return;

  const style = document.createElement("style");
  style.id = "analytics-toast-styles";
  style.textContent = `
    .analytics-toast-container {
      position: fixed;
      bottom: 28px;
      right: 28px;
      z-index: 99999;
      display: flex;
      flex-direction: column;
      gap: 10px;
      pointer-events: none;
      max-width: 450px;
      width: 100%;
    }
    
    @keyframes analyticsToastSlideIn {
      from { opacity: 0; transform: translateX(30px) scale(0.95); }
      to { opacity: 1; transform: translateX(0) scale(1); }
    }
    
    @keyframes analyticsToastSlideOut {
      from { opacity: 1; transform: translateX(0) scale(1); }
      to { opacity: 0; transform: translateX(30px) scale(0.95); }
    }
    
    .analytics-toast {
      pointer-events: auto;
      padding: 14px 18px;
      border-radius: var(--radius-md, 10px);
      font-size: 0.85rem;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 10px;
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid transparent;
      min-width: 280px;
      width: 100%;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      transition: all 0.2s ease;
      background: var(--bg-card, rgba(255,255,255,0.03));
      color: var(--text-primary, #f1f5f9);
    }
    
    .analytics-toast:hover {
      transform: translateX(4px);
    }
    
    .analytics-toast-success {
      border-left: 4px solid #00d578;
      background: rgba(0, 213, 120, 0.08);
    }
    .analytics-toast-success .analytics-toast-icon {
      color: #00d578;
    }
    
    .analytics-toast-error {
      border-left: 4px solid #ef4444;
      background: rgba(239, 68, 68, 0.08);
    }
    .analytics-toast-error .analytics-toast-icon {
      color: #ef4444;
    }
    
    .analytics-toast-warning {
      border-left: 4px solid #f59e0b;
      background: rgba(245, 158, 11, 0.08);
    }
    .analytics-toast-warning .analytics-toast-icon {
      color: #f59e0b;
    }
    
    .analytics-toast-info {
      border-left: 4px solid #ff6b00;
      background: rgba(255, 107, 0, 0.08);
    }
    .analytics-toast-info .analytics-toast-icon {
      color: #ff6b00;
    }
    
    .analytics-toast-content {
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 1;
    }
    
    .analytics-toast-icon {
      font-size: 1.2rem;
      line-height: 1;
      flex-shrink: 0;
    }
    
    .analytics-toast-message {
      flex: 1;
      line-height: 1.4;
      word-break: break-word;
    }
    
    .analytics-toast-close {
      background: none;
      border: none;
      color: var(--text-muted, #94a3b8);
      font-size: 1.3rem;
      cursor: pointer;
      padding: 0 4px;
      line-height: 1;
      flex-shrink: 0;
      margin-left: 8px;
      transition: color 0.2s ease;
    }
    
    .analytics-toast-close:hover {
      color: var(--text-primary, #f1f5f9);
    }
    
    @media (max-width: 480px) {
      .analytics-toast-container {
        bottom: 12px;
        right: 12px;
        left: 12px;
        max-width: none;
      }
      .analytics-toast {
        min-width: unset;
        max-width: none;
        width: 100%;
        font-size: 0.8rem;
        padding: 12px 14px;
      }
    }
  `;
  document.head.appendChild(style);
}

// Inject styles on load
injectStyles();

// ============================================================
// EXPORT
// ============================================================

export default {
  showToast,
  showSuccess,
  showError,
  showWarning,
  showInfo,
  clearAllToasts,
};
