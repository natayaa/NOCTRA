// static/js/shared/toast.js

let activeToasts = [];
const MAX_TOASTS = 5;

export function showToast(message, type = "info", duration = 4000) {
  const container = document.getElementById("toastContainer");
  if (!container) {
    console.warn("Toast container not found");
    return;
  }

  // Limit toasts
  if (activeToasts.length >= MAX_TOASTS) {
    const oldest = activeToasts.shift();
    if (oldest && oldest.parentNode) {
      oldest.remove();
    }
  }

  const config = {
    success: { icon: "✅", className: "toast-success" },
    error: { icon: "❌", className: "toast-error" },
    warning: { icon: "⚠️", className: "toast-warning" },
    info: { icon: "ℹ️", className: "toast-info" },
  };

  const cfg = config[type] || config.info;

  const toast = document.createElement("div");
  toast.className = `toast ${cfg.className}`;
  toast.innerHTML = `
    <div class="toast-content">
      <span class="toast-icon">${cfg.icon}</span>
      <span>${message}</span>
    </div>
    <button class="toast-close">&times;</button>
  `;

  container.appendChild(toast);
  activeToasts.push(toast);

  const closeBtn = toast.querySelector(".toast-close");
  closeBtn.addEventListener("click", () => removeToast(toast));

  setTimeout(() => removeToast(toast), duration);

  return toast;
}

function removeToast(toast) {
  if (!toast || !toast.parentNode) return;
  toast.style.animation = "toastSlideOut 0.3s ease forwards";
  setTimeout(() => {
    if (toast.parentNode) {
      toast.remove();
      const index = activeToasts.indexOf(toast);
      if (index > -1) activeToasts.splice(index, 1);
    }
  }, 300);
}
