// static/js/pages/settings/index.js - FULL FIXED (Tanpa Users)

import { state } from "./config.js";
import { DOM } from "./dom.js";
import { loadAllSettings, saveAllSettings } from "./handlers/settings.js";
// ✅ Path toast diperbaiki
import { showToast } from "../../pages/shared/toast.js";

// ============================================================
// EXPOSE FUNCTIONS DARI TEMPLATES
// ============================================================

import {
  openTemplateModal,
  closeTemplateModal,
  saveTemplate,
  deleteTemplate,
  setDefaultTemplate,
} from "./handlers/templates.js";

// ============================================================
// BIND SEMUA EVENTS DI SATU TEMPAT
// ============================================================

function bindAllEvents() {
  console.log("🔗 Binding settings events...");

  // 1. Save Button
  const saveBtn = document.getElementById("saveSettings");
  if (saveBtn) {
    saveBtn.addEventListener("click", (e) => {
      e.preventDefault();
      saveAllSettings();
    });
  } else {
    console.warn("⚠️ Save button not found");
  }

  // 2. Reset Button
  const resetBtn = document.getElementById("resetSettings");
  if (resetBtn) {
    resetBtn.addEventListener("click", (e) => {
      e.preventDefault();
      if (confirm("Are you sure you want to reset all settings?")) {
        showToast("⚠️ Reset functionality coming soon", "warning");
      }
    });
  }

  // 3. Template Form Submit
  const templateForm = document.getElementById("templateForm");
  if (templateForm) {
    templateForm.addEventListener("submit", saveTemplate);
  }

  // 4. Add Template Button
  const addTemplateBtn = document.getElementById("addTemplateBtn");
  if (addTemplateBtn) {
    addTemplateBtn.addEventListener("click", () => openTemplateModal(null));
  }

  // 5. Close Template Modal
  document
    .getElementById("closeTemplateModal")
    ?.addEventListener("click", closeTemplateModal);
  document
    .getElementById("cancelTemplateBtn")
    ?.addEventListener("click", closeTemplateModal);
  const templateModal = document.getElementById("templateModal");
  if (templateModal) {
    templateModal.addEventListener("click", (e) => {
      if (e.target === templateModal) closeTemplateModal();
    });
  }

  // 6. Project Type Modal
  document
    .getElementById("addProjectTypeBtn")
    ?.addEventListener("click", () => {
      document.getElementById("projectTypeModal")?.classList.add("active");
    });
  document
    .getElementById("closeProjectTypeModal")
    ?.addEventListener("click", () => {
      document.getElementById("projectTypeModal")?.classList.remove("active");
    });
  document
    .getElementById("cancelProjectTypeBtn")
    ?.addEventListener("click", () => {
      document.getElementById("projectTypeModal")?.classList.remove("active");
    });
  const projectTypeModal = document.getElementById("projectTypeModal");
  if (projectTypeModal) {
    projectTypeModal.addEventListener("click", (e) => {
      if (e.target === projectTypeModal)
        projectTypeModal.classList.remove("active");
    });
  }

  // 7. Payment Method Modal
  document
    .getElementById("addPaymentMethodBtn")
    ?.addEventListener("click", () => {
      document.getElementById("paymentMethodModal")?.classList.add("active");
    });
  document
    .getElementById("closePaymentMethodModal")
    ?.addEventListener("click", () => {
      document.getElementById("paymentMethodModal")?.classList.remove("active");
    });
  document
    .getElementById("cancelPaymentMethodBtn")
    ?.addEventListener("click", () => {
      document.getElementById("paymentMethodModal")?.classList.remove("active");
    });
  const paymentMethodModal = document.getElementById("paymentMethodModal");
  if (paymentMethodModal) {
    paymentMethodModal.addEventListener("click", (e) => {
      if (e.target === paymentMethodModal)
        paymentMethodModal.classList.remove("active");
    });
  }

  // 8. Navigation (Tabs/Sections)
  const navItems = document.querySelectorAll(".settings-nav .nav-item");
  const sections = document.querySelectorAll(".settings-section");
  navItems.forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      navItems.forEach((n) => n.classList.remove("active"));
      item.classList.add("active");
      const target = item.getAttribute("href")?.replace("#", "");
      sections.forEach((section) => {
        section.classList.remove("active");
        if (section.id === target) {
          section.classList.add("active");
        }
      });
      state.activeSection = target;
    });
  });

  // 9. Keyboard Shortcuts
  document.addEventListener("keydown", (e) => {
    // Ctrl+S -> Save
    if (e.ctrlKey && e.key === "s") {
      e.preventDefault();
      saveAllSettings();
    }
    // Escape -> Close modals
    if (e.key === "Escape") {
      if (
        document.getElementById("templateModal")?.classList.contains("active")
      )
        closeTemplateModal();
      if (
        document
          .getElementById("projectTypeModal")
          ?.classList.contains("active")
      )
        document.getElementById("projectTypeModal").classList.remove("active");
      if (
        document
          .getElementById("paymentMethodModal")
          ?.classList.contains("active")
      )
        document
          .getElementById("paymentMethodModal")
          .classList.remove("active");
    }
    // Ctrl+F -> Focus search (if exists)
    if (e.ctrlKey && e.key === "f") {
      e.preventDefault();
      const search = document.getElementById("searchSettings");
      if (search) search.focus();
    }
  });

  console.log("✅ Settings events bound successfully!");
}

// ============================================================
// EXPOSE GLOBAL FUNCTIONS
// ============================================================

function exposeGlobals() {
  window.openTemplateModal = openTemplateModal;
  window.closeTemplateModal = closeTemplateModal;
  window.saveTemplate = saveTemplate;
  window.deleteTemplate = deleteTemplate;
  window.setDefaultTemplate = setDefaultTemplate;
  window.loadAllSettings = loadAllSettings;
  window.saveAllSettings = saveAllSettings;

  // Project Types & Payment Methods (untuk inline onclick di renderer)
  // Nanti akan diisi oleh handler masing-masing
}

// ============================================================
// INITIALIZATION
// ============================================================

export async function initSettings() {
  console.log("🚀 Initializing Settings page...");

  try {
    // 1. Bind semua event
    bindAllEvents();

    // 2. Expose global functions
    exposeGlobals();

    // 3. Load data
    await loadAllSettings();

    console.log("📋 Settings page initialized successfully");
    showToast("Settings loaded", "info", 2000);
  } catch (error) {
    console.error("❌ Failed to initialize settings page:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

// ============================================================
// AUTO-INIT ON DOM READY
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
  console.log("📄 DOM Content Loaded, initializing settings...");
  initSettings();
});

export default { initSettings };
