// ============================================================
// shared/toast.js - Toast Notification
// ============================================================

let activeToasts = [];
const MAX_TOASTS = 5;

export function showToast(message, type = "info", duration = 4000) {
  const container = document.getElementById("toastContainer");
  if (!container) {
    console.warn("Toast container not found");
    return;
  }

  // Limit active toasts
  if (activeToasts.length >= MAX_TOASTS) {
    const oldest = activeToasts.shift();
    if (oldest?.parentNode) oldest.remove();
  }

  const icons = {
    success: "✅",
    error: "❌",
    warning: "⚠️",
    info: "ℹ️",
  };

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div class="toast-content">
      <span class="toast-icon">${icons[type] || "ℹ️"}</span>
      <span class="toast-message">${message}</span>
    </div>
    <button class="toast-close">&times;</button>
  `;

  container.appendChild(toast);
  activeToasts.push(toast);

  // Close button
  toast.querySelector(".toast-close").addEventListener("click", () => {
    removeToast(toast);
  });

  // Auto remove
  setTimeout(() => removeToast(toast), duration);

  return toast;
}

function removeToast(toast) {
  if (!toast?.parentNode) return;
  toast.style.opacity = "0";
  toast.style.transform = "translateY(-10px)";
  setTimeout(() => {
    if (toast.parentNode) {
      toast.remove();
      const index = activeToasts.indexOf(toast);
      if (index > -1) activeToasts.splice(index, 1);
    }
  }, 300);
}

// Shortcuts
export const showSuccess = (msg, duration) =>
  showToast(msg, "success", duration);
export const showError = (msg, duration) => showToast(msg, "error", duration);
export const showWarning = (msg, duration) =>
  showToast(msg, "warning", duration);
export const showInfo = (msg, duration) => showToast(msg, "info", duration);
