/**
 * NOCTRA UI Helpers
 * Sidebar navigation, mobile toggle, global search, and toast system.
 * Fully modular – all in one file.
 */
(function () {
  "use strict";

  // ============================================================
  // CONSTANTS
  // ============================================================
  const TOAST_ICONS = {
    success: "ri-checkbox-circle-line",
    warning: "ri-error-warning-line",
    error: "ri-close-circle-line",
    info: "ri-information-line",
  };

  const MOBILE_BREAKPOINT = 1024;

  // ============================================================
  // MAIN UI CLASS
  // ============================================================
  class AppUI {
    // ─── Private fields ──────────────────────────────────────
    #dom = {
      sidebar: null,
      menuBtn: null,
      overlay: null,
      navLinks: null,
      searchInput: null,
      toastContainer: null,
    };
    #searchDebounceTimer = null;
    #isSidebarOpen = false;
    #closeSidebar = null;

    // ─── Constructor ──────────────────────────────────────────
    constructor() {
      this.#cacheDOMElements();
      this.#initActiveLink();
      this.#initSidebarToggle();
      this.#initSearch();
      // Toast container is not created here; it's assumed to exist in HTML.
      // But if not, we could create it dynamically.
      // We'll just expose the showToast method.
    }

    // ─── DOM Caching ──────────────────────────────────────────
    #cacheDOMElements() {
      this.#dom.sidebar = document.getElementById("sidebar");
      this.#dom.menuBtn = document.getElementById("menuBtn");
      this.#dom.overlay = document.getElementById("sidebarOverlay");
      this.#dom.navLinks = document.querySelectorAll(".sidebar-nav a");
      this.#dom.searchInput = document.querySelector(".search-box input");
      this.#dom.toastContainer = document.getElementById("toastContainer");
    }

    // ─── 1. ACTIVE SIDEBAR LINK ──────────────────────────────
    #initActiveLink() {
      const currentPath = window.location.pathname;
      this.#dom.navLinks.forEach((link) => {
        const href = link.getAttribute("href");
        if (href && currentPath.startsWith(href)) {
          link.classList.add("active");
        }
      });
    }

    // ─── 2. MOBILE SIDEBAR TOGGLE ────────────────────────────
    #initSidebarToggle() {
      const { sidebar, menuBtn, overlay, navLinks } = this.#dom;

      if (!sidebar || !menuBtn || !overlay) return;

      // Open / close functions
      const open = () => {
        sidebar.classList.add("open");
        overlay.classList.add("active");
        document.body.style.overflow = "hidden";
        this.#isSidebarOpen = true;
      };

      const close = () => {
        sidebar.classList.remove("open");
        overlay.classList.remove("active");
        document.body.style.overflow = "";
        this.#isSidebarOpen = false;
      };

      // Toggle on menu button click
      menuBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.#isSidebarOpen ? close() : open();
      });

      // Close on overlay click
      overlay.addEventListener("click", close);

      // Close on nav link click (mobile only)
      navLinks.forEach((link) => {
        link.addEventListener("click", () => {
          if (window.innerWidth <= MOBILE_BREAKPOINT) {
            close();
          }
        });
      });

      // Optional: close on Escape key
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && this.#isSidebarOpen) {
          close();
        }
      });

      // Store close function for potential external use (optional)
      this.#closeSidebar = close;
    }

    // ─── 3. GLOBAL SEARCH (with debounce) ────────────────────
    #initSearch() {
      const input = this.#dom.searchInput;
      if (!input) return;

      input.addEventListener("keyup", (e) => {
        const query = e.target.value.trim();
        clearTimeout(this.#searchDebounceTimer);

        if (query.length > 1) {
          this.#searchDebounceTimer = setTimeout(() => {
            // Perform search
            this.#performSearch(query);
          }, 300);
        } else {
          // Optionally clear results if query too short
          // this.#clearSearchResults();
        }
      });

      // Also trigger search on 'Enter' immediately (optional)
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          const query = e.target.value.trim();
          if (query.length > 0) {
            clearTimeout(this.#searchDebounceTimer);
            this.#performSearch(query);
          }
        }
      });
    }

    #performSearch(query) {
      // TODO: Integrate with search API
      console.log("🔍 Searching for:", query);
      // Example: fetch(`/api/search?q=${encodeURIComponent(query)}`)
      //   .then(res => res.json())
      //   .then(data => this.#renderSearchResults(data));
      // For now, just show a toast with the query
      this.showToast(`Searching for "${query}"...`, "info", 2000);
    }

    // ─── 4. TOAST SYSTEM ──────────────────────────────────────
    /**
     * Public method to show a toast notification.
     * @param {string} message - The message to display.
     * @param {string} type - 'success', 'warning', 'error', 'info'.
     * @param {number} duration - Duration in milliseconds.
     */
    showToast(message, type = "success", duration = 3500) {
      const container = this.#dom.toastContainer;
      if (!container) {
        // Fallback: create container if missing
        this.#createToastContainer();
        return this.showToast(message, type, duration);
      }

      const toast = document.createElement("div");
      toast.className = `toast ${type}`;
      const iconClass = TOAST_ICONS[type] || TOAST_ICONS.info;
      toast.innerHTML = `<i class="${iconClass}"></i><span>${message}</span>`;

      container.appendChild(toast);

      // Remove after duration
      const remove = () => {
        toast.classList.add("removing");
        toast.addEventListener("animationend", () => toast.remove(), {
          once: true,
        });
      };

      const timer = setTimeout(remove, duration);

      // Dismiss on click
      toast.addEventListener("click", () => {
        clearTimeout(timer);
        remove();
      });
    }

    #createToastContainer() {
      const container = document.createElement("div");
      container.id = "toastContainer";
      container.className = "toast-container";
      document.body.appendChild(container);
      this.#dom.toastContainer = container;
    }
  }

  // ============================================================
  // INSTANTIATE AND EXPOSE GLOBALLY
  // ============================================================
  let appUI = null;

  document.addEventListener("DOMContentLoaded", () => {
    appUI = new AppUI();

    // Expose showToast globally (backward compatibility)
    window.showToast = (message, type, duration) => {
      if (appUI) {
        appUI.showToast(message, type, duration);
      } else {
        console.warn("AppUI not ready yet. Toast delayed.");
        // Fallback: if appUI not ready, queue toast or just console.log
        setTimeout(() => {
          if (appUI) {
            appUI.showToast(message, type, duration);
          }
        }, 100);
      }
    };
  });
})();
