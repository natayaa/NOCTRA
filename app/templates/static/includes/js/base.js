// static/js/base.js
// ============================================================
// NOCTRA Base JavaScript
// ============================================================

(function () {
  "use strict";

  // ============================================================
  // DOM READY
  // ============================================================
  document.addEventListener("DOMContentLoaded", function () {
    console.log("🚀 NOCTRA Base initialized");

    initSidebar();
    initTopbar();
    initProfileDropdown();
    initRefreshButton();
    initLogout();
    initNavActiveState();
  });

  // ============================================================
  // SIDEBAR
  // ============================================================
  function initSidebar() {
    const menuBtn = document.getElementById("menuBtn");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");

    if (!menuBtn || !sidebar || !overlay) return;

    function toggleSidebar() {
      sidebar.classList.toggle("open");
      overlay.classList.toggle("active");
      document.body.style.overflow = sidebar.classList.contains("open")
        ? "hidden"
        : "";
    }

    function closeSidebar() {
      sidebar.classList.remove("open");
      overlay.classList.remove("active");
      document.body.style.overflow = "";
    }

    menuBtn.addEventListener("click", toggleSidebar);
    overlay.addEventListener("click", closeSidebar);

    // Close on Escape key
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && sidebar.classList.contains("open")) {
        closeSidebar();
      }
    });

    // Close on window resize (desktop)
    window.addEventListener("resize", function () {
      if (window.innerWidth > 1024 && sidebar.classList.contains("open")) {
        closeSidebar();
      }
    });

    console.log("✅ Sidebar initialized");
  }

  // ============================================================
  // TOPBAR - Page Title & Subtitle
  // ============================================================
  function initTopbar() {
    // Set page title based on current URL
    const titleEl = document.getElementById("pageTitle");
    const subtitleEl = document.getElementById("pageSubtitle");

    if (!titleEl) return;

    const path = window.location.pathname;
    const pageMap = {
      "/management/": {
        title: "Dashboard",
        subtitle: "Workshop overview & key metrics",
      },
      "/management/projects": {
        title: "Projects",
        subtitle: "Manage workshop projects",
      },
      "/management/inquiries": {
        title: "Inquiries",
        subtitle: "Customer requests & quotations",
      },
      "/management/budgeting": {
        title: "Budgeting",
        subtitle: "Financial planning & tracking",
      },
      "/management/inventories": {
        title: "Inventory",
        subtitle: "Stock & materials management",
      },
      "/management/price-list": {
        title: "Price List",
        subtitle: "Service & material pricing",
      },
      "/management/customers": {
        title: "Customers",
        subtitle: "Customer management",
      },
      "/management/invoices": {
        title: "Invoices",
        subtitle: "Billing & payments",
      },
      "/management/calendars": {
        title: "Calendar",
        subtitle: "Schedule & appointments",
      },
      "/management/documents": {
        title: "Documents",
        subtitle: "File management",
      },
      "/management/work-orders": {
        title: "Work Orders",
        subtitle: "Job & task management",
      },
      "/management/quotations": {
        title: "Quotations",
        subtitle: "Quotes & estimates",
      },
      "/management/analytics": {
        title: "Analytics",
        subtitle: "Performance & insights",
      },
      "/management/reports": {
        title: "Reports",
        subtitle: "Generate & view reports",
      },
      "/management/settings": {
        title: "Settings",
        subtitle: "System configuration",
      },
      "/management/notifications": {
        title: "Notifications",
        subtitle: "Alerts & updates",
      },
    };

    const pageInfo = pageMap[path] || pageMap["/management/"];

    // Only update if using dynamic page title (not overridden by page-specific)
    if (!titleEl.dataset.custom) {
      titleEl.textContent = pageInfo.title;
    }
    if (subtitleEl && !subtitleEl.dataset.custom) {
      subtitleEl.textContent = pageInfo.subtitle;
    }

    console.log("✅ Topbar initialized");
  }

  // ============================================================
  // PROFILE DROPDOWN
  // ============================================================
  function initProfileDropdown() {
    const profile = document.getElementById("profileMenu");
    const dropdown = document.getElementById("profileDropdown");

    if (!profile || !dropdown) return;

    // Toggle dropdown
    profile.addEventListener("click", function (e) {
      e.stopPropagation();
      dropdown.classList.toggle("open");
    });

    // Close on outside click
    document.addEventListener("click", function () {
      dropdown.classList.remove("open");
    });

    // Close on Escape
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && dropdown.classList.contains("open")) {
        dropdown.classList.remove("open");
      }
    });

    console.log("✅ Profile dropdown initialized");
  }

  // ============================================================
  // REFRESH BUTTON
  // ============================================================
  function initRefreshButton() {
    const refreshBtn = document.getElementById("refreshBtn");
    if (!refreshBtn) return;

    refreshBtn.addEventListener("click", function () {
      // Add spinning animation
      const icon = this.querySelector("i");
      if (icon) {
        icon.style.animation = "spin 0.6s linear";
        setTimeout(() => {
          icon.style.animation = "";
        }, 600);
      }

      // Check if page has refresh function
      if (window.loadProjects) {
        window.loadProjects();
      } else if (window.loadInquiries) {
        window.loadInquiries();
      } else if (window.loadInventoryItems) {
        window.loadInventoryItems();
      } else if (window.loadPriceItems) {
        window.loadPriceItems();
      } else {
        // Default: reload page
        window.location.reload();
      }

      console.log("🔄 Refresh triggered");
    });

    console.log("✅ Refresh button initialized");
  }

  // ============================================================
  // LOGOUT
  // ============================================================
  function initLogout() {
    const logoutBtns = document.querySelectorAll("#logoutBtn, #logoutDropdown");

    logoutBtns.forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        handleLogout();
      });
    });

    console.log("✅ Logout initialized");
  }

  function handleLogout() {
    if (typeof Swal !== "undefined") {
      Swal.fire({
        title: "Logout?",
        text: "Are you sure you want to logout?",
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#ff6b00",
        cancelButtonColor: "#6b6b6b",
        confirmButtonText: "Yes, logout",
        background: "#0a0a0a",
        color: "#f1f5f9",
      }).then(function (result) {
        if (result.isConfirmed) {
          performLogout();
        }
      });
    } else {
      if (confirm("Are you sure you want to logout?")) {
        performLogout();
      }
    }
  }

  function performLogout() {
    // Clear any auth tokens
    localStorage.removeItem("auth_token");
    sessionStorage.removeItem("auth_token");

    // Redirect to login
    window.location.href = "/login";
  }

  // ============================================================
  // NAV ACTIVE STATE
  // ============================================================
  function initNavActiveState() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll(".sidebar-nav a");

    navLinks.forEach(function (link) {
      const href = link.getAttribute("href");
      if (!href) return;

      // Check if current path matches
      if (
        currentPath === href ||
        (href !== "/" && currentPath.startsWith(href))
      ) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });

    console.log("✅ Nav active state initialized");
  }

  // ============================================================
  // UTILITY: Show Toast (global)
  // ============================================================
  window.showToast = function (message, type = "info", duration = 4000) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toast.setAttribute("role", "alert");

    container.appendChild(toast);

    setTimeout(function () {
      toast.classList.add("removing");
      setTimeout(function () {
        if (toast.parentNode) toast.remove();
      }, 300);
    }, duration);
  };

  // ============================================================
  // UTILITY: Format Currency
  // ============================================================
  window.formatCurrency = function (amount) {
    if (!amount && amount !== 0) return "Rp 0";
    return new Intl.NumberFormat("id-ID", {
      style: "currency",
      currency: "IDR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(Number(amount));
  };

  // ============================================================
  // UTILITY: Format Date
  // ============================================================
  window.formatDate = function (dateString) {
    if (!dateString) return "-";
    try {
      return new Date(dateString).toLocaleDateString("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return "-";
    }
  };

  // ============================================================
  // UTILITY: Format DateTime
  // ============================================================
  window.formatDateTime = function (dateString) {
    if (!dateString) return "-";
    try {
      return new Date(dateString).toLocaleString("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "-";
    }
  };

  // ============================================================
  // UTILITY: Get Initials
  // ============================================================
  window.getInitials = function (name) {
    if (!name) return "?";
    const parts = name.trim().split(" ");
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (
      parts[0].charAt(0) + parts[parts.length - 1].charAt(0)
    ).toUpperCase();
  };

  // ============================================================
  // UTILITY: Update User Info
  // ============================================================
  window.updateUserInfo = function (user) {
    if (!user) return;

    const nameEl = document.getElementById("userName");
    const roleEl = document.getElementById("userRole");
    const avatarEl = document.getElementById("userAvatar");

    if (nameEl) nameEl.textContent = user.name || user.username || "User";
    if (roleEl) roleEl.textContent = user.role || "Member";
    if (avatarEl)
      avatarEl.textContent = getInitials(user.name || user.username);
  };

  // ============================================================
  // KEYBOARD SHORTCUTS (Global)
  // ============================================================
  document.addEventListener("keydown", function (e) {
    // Ctrl + / - Toggle sidebar
    if (e.ctrlKey && e.key === "/") {
      e.preventDefault();
      const sidebar = document.getElementById("sidebar");
      if (sidebar) {
        sidebar.classList.toggle("open");
        const overlay = document.getElementById("sidebarOverlay");
        if (overlay) overlay.classList.toggle("active");
      }
    }

    // Ctrl + Shift + R - Hard refresh with cache clear
    if (e.ctrlKey && e.shiftKey && e.key === "R") {
      e.preventDefault();
      // Clear cache and reload
      if (window.location.reload) {
        window.location.reload(true);
      }
    }
  });

  // ============================================================
  // CONSOLE WELCOME
  // ============================================================
  console.log(
    "%c NOCTRA Workshop OS ",
    "background:#ff6b00;color:#fff;font-size:1.2rem;font-weight:bold;padding:4px 12px;border-radius:4px;",
  );
  console.log(
    "%c Built with ❤️ by NOCTRA Team ",
    "color:#94a3b8;font-size:0.85rem;",
  );
})();
