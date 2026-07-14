// static/js/pages/settings/handlers/events.js

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { loadAllSettings, saveAllSettings } from "./settings.js";
import {
  openTemplateModal,
  closeTemplateModal,
  saveTemplate,
  deleteTemplate,
  setDefaultTemplate,
} from "./templates.js";
import {
  openUserModal,
  closeUserModal,
  saveUser,
  deleteUser,
  loadUsers,
} from "./users.js";
import { showToast } from "../../../pages/shared/toast.js";

// ============================================================
// NAVIGATION
// ============================================================

export function setupNavigation() {
  const navItems = DOM.navItems();
  const sections = DOM.sections();

  navItems.forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();

      // Update active nav
      navItems.forEach((n) => n.classList.remove("active"));
      item.classList.add("active");

      // Show corresponding section
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
}

// ============================================================
// SAVE & RESET
// ============================================================

export function setupSaveButton() {
  DOM.saveBtn()?.addEventListener("click", saveAllSettings);
}

export function setupResetButton() {
  DOM.resetBtn()?.addEventListener("click", async () => {
    if (
      confirm(
        "Are you sure you want to reset all settings to default? This cannot be undone.",
      )
    ) {
      showToast("⚠️ Reset functionality coming soon", "warning");
    }
  });
}

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================

export function setupKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    // Ctrl+S - Save
    if (e.ctrlKey && e.key === "s") {
      e.preventDefault();
      saveAllSettings();
    }

    // Escape - Close modals
    if (e.key === "Escape") {
      if (DOM.templateModal()?.classList.contains("active")) {
        closeTemplateModal();
      }
      if (DOM.userModal()?.classList.contains("active")) {
        closeUserModal();
      }
    }
  });
}

// ============================================================
// MODAL CLOSE ON OVERLAY CLICK
// ============================================================

export function setupModalOverlays() {
  // Template modal
  const templateModal = DOM.templateModal();
  if (templateModal) {
    templateModal.addEventListener("click", (e) => {
      if (e.target === templateModal) {
        closeTemplateModal();
      }
    });
  }

  // User modal
  const userModal = DOM.userModal();
  if (userModal) {
    userModal.addEventListener("click", (e) => {
      if (e.target === userModal) {
        closeUserModal();
      }
    });
  }
}

// ============================================================
// EXPOSE GLOBAL FUNCTIONS
// ============================================================

export function exposeGlobals() {
  window.openTemplateModal = openTemplateModal;
  window.closeTemplateModal = closeTemplateModal;
  window.saveTemplate = saveTemplate;
  window.deleteTemplate = deleteTemplate;
  window.setDefaultTemplate = setDefaultTemplate;

  window.openUserModal = openUserModal;
  window.closeUserModal = closeUserModal;
  window.saveUser = saveUser;
  window.deleteUser = deleteUser;

  window.loadAllSettings = loadAllSettings;
  window.saveAllSettings = saveAllSettings;
}

// ============================================================
// BIND ALL EVENTS
// ============================================================

export function bindEvents() {
  setupNavigation();
  setupSaveButton();
  setupResetButton();
  setupKeyboardShortcuts();
  setupModalOverlays();
  exposeGlobals();

  console.log("✅ Settings events bound successfully!");
}
