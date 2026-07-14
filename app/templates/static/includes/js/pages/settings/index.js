// static/js/pages/settings/index.js

import { state } from "./config.js";
import { bindEvents } from "./handlers/events.js";
import { loadAllSettings } from "./handlers/settings.js";
import { loadUsers } from "./handlers/users.js";
import { showToast } from "../../pages/shared/toast.js";
import { bindTemplateForm } from "./handlers/templates.js";
import { bindUserForm } from "./handlers/users.js";

// ============================================================
// INITIALIZATION
// ============================================================

export async function initSettings() {
  console.log("🚀 Initializing Settings page...");

  try {
    // Bind events first
    bindEvents();

    // Bind form submissions
    const templateForm = document.getElementById("templateForm");
    if (templateForm) {
      templateForm.addEventListener(
        "submit",
        window.saveTemplate ||
          ((e) => {
            e.preventDefault();
            console.warn("saveTemplate not defined yet");
          }),
      );
    }

    const userForm = document.getElementById("userForm");
    if (userForm) {
      userForm.addEventListener(
        "submit",
        window.saveUser ||
          ((e) => {
            e.preventDefault();
            console.warn("saveUser not defined yet");
          }),
      );
    }

    // Bind close buttons
    document
      .getElementById("closeTemplateModal")
      ?.addEventListener("click", window.closeTemplateModal);
    document
      .getElementById("cancelTemplateBtn")
      ?.addEventListener("click", window.closeTemplateModal);
    document
      .getElementById("closeUserModal")
      ?.addEventListener("click", window.closeUserModal);
    document
      .getElementById("cancelUserBtn")
      ?.addEventListener("click", window.closeUserModal);

    // Bind add buttons
    document.getElementById("addTemplateBtn")?.addEventListener("click", () => {
      window.openTemplateModal(null);
    });
    document.getElementById("addUserBtn")?.addEventListener("click", () => {
      window.openUserModal(null);
    });

    // Load all data
    await Promise.all([loadAllSettings(), loadUsers()]);

    console.log("📋 Settings page initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize settings page:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

// ============================================================
// AUTO-INIT ON DOM READY
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
  initSettings();
});

// ============================================================
// EXPOSE FOR INLINE USAGE
// ============================================================

window.initSettings = initSettings;
