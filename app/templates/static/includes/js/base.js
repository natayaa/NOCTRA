/* ==========================
   ACTIVE SIDEBAR LINK
========================== */

const currentPath = window.location.pathname;

document.querySelectorAll(".sidebar-nav a").forEach((link) => {
  const href = link.getAttribute("href");
  if (href && currentPath.startsWith(href)) {
    link.classList.add("active");
  }
});

/* ==========================
   MOBILE SIDEBAR TOGGLE
========================== */

const sidebar        = document.getElementById("sidebar");
const menuBtn        = document.getElementById("menuBtn");
const sidebarOverlay = document.getElementById("sidebarOverlay");

function openSidebar() {
  sidebar?.classList.add("open");
  sidebarOverlay?.classList.add("active");
  document.body.style.overflow = "hidden";
}

function closeSidebar() {
  sidebar?.classList.remove("open");
  sidebarOverlay?.classList.remove("active");
  document.body.style.overflow = "";
}

menuBtn?.addEventListener("click", () => {
  sidebar?.classList.contains("open") ? closeSidebar() : openSidebar();
});

sidebarOverlay?.addEventListener("click", closeSidebar);

// Close sidebar on nav link click (mobile)
document.querySelectorAll(".sidebar-nav a").forEach((link) => {
  link.addEventListener("click", () => {
    if (window.innerWidth <= 1024) closeSidebar();
  });
});

/* ==========================
   GLOBAL SEARCH
========================== */

const searchInput = document.querySelector(".search-box input");

if (searchInput) {
  let debounceTimer;

  searchInput.addEventListener("keyup", (e) => {
    clearTimeout(debounceTimer);

    debounceTimer = setTimeout(() => {
      const query = e.target.value.trim();
      if (query.length > 1) {
        console.log("Searching:", query);
        // TODO: hook into search API
      }
    }, 300);
  });
}

/* ==========================
   TOAST SYSTEM
========================== */

const TOAST_ICONS = {
  success: "ri-checkbox-circle-line",
  warning: "ri-error-warning-line",
  error:   "ri-close-circle-line",
  info:    "ri-information-line",
};

/**
 * showToast(message, type, duration)
 * type: "success" | "warning" | "error" | "info"
 * duration: ms (default 3500)
 */
function showToast(message, type = "success", duration = 3500) {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  const iconClass = TOAST_ICONS[type] || TOAST_ICONS.info;
  toast.innerHTML = `<i class="${iconClass}"></i><span>${message}</span>`;

  container.appendChild(toast);

  const remove = () => {
    toast.classList.add("removing");
    toast.addEventListener("animationend", () => toast.remove(), { once: true });
  };

  const timer = setTimeout(remove, duration);

  // Click to dismiss early
  toast.addEventListener("click", () => {
    clearTimeout(timer);
    remove();
  });
}

// Expose globally
window.showToast = showToast;