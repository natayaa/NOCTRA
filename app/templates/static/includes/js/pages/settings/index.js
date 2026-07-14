// static/js/pages/settings/index.js - FULL FIXED

import { state } from "./config.js";
import { loadAllSettings, saveAllSettings } from "./handlers/settings.js";
import { loadUsers } from "./handlers/users.js";
import { showToast } from "../../pages/shared/toast.js";

// ============================================================
// EXPOSE GLOBAL FUNCTIONS
// ============================================================

import {
  openTemplateModal,
  closeTemplateModal,
  saveTemplate,
  deleteTemplate,
  setDefaultTemplate,
} from "./handlers/templates.js";

import {
  openUserModal,
  closeUserModal,
  saveUser,
  deleteUser,
} from "./handlers/users.js";

// ✅ HAPUS import bindTemplateForm - TIDAK DIPERLUKAN

// ============================================================
// INITIALIZATION
// ============================================================

export async function initSettings() {
  console.log("🚀 Initializing Settings page...");

  try {
    // ✅ CEK ELEMEN PENTING
    const saveBtn = document.getElementById("saveSettings");
    const resetBtn = document.getElementById("resetSettings");
    const addTemplateBtn = document.getElementById("addTemplateBtn");
    const addUserBtn = document.getElementById("addUserBtn");

    console.log("🔍 Elements found:", {
      saveBtn: !!saveBtn,
      resetBtn: !!resetBtn,
      addTemplateBtn: !!addTemplateBtn,
      addUserBtn: !!addUserBtn,
    });

    // ✅ 1. BIND SAVE BUTTON - PALING PENTING
    if (saveBtn) {
      console.log("✅ Save button found, binding click event...");
      saveBtn.addEventListener("click", function (e) {
        console.log("🔄 Save button clicked!");
        e.preventDefault();
        saveAllSettings();
      });
    } else {
      console.error("❌ Save button NOT found! Check ID: saveSettings");
    }

    // ✅ 2. BIND RESET BUTTON
    if (resetBtn) {
      resetBtn.addEventListener("click", function (e) {
        e.preventDefault();
        if (confirm("Are you sure you want to reset all settings?")) {
          showToast("⚠️ Reset functionality coming soon", "warning");
        }
      });
    }

    // ✅ 3. BIND FORM SUBMISSIONS
    const templateForm = document.getElementById("templateForm");
    if (templateForm) {
      templateForm.addEventListener("submit", saveTemplate);
    }

    const userForm = document.getElementById("userForm");
    if (userForm) {
      userForm.addEventListener("submit", saveUser);
    }

    // ✅ 4. BIND MODAL CLOSE BUTTONS
    document
      .getElementById("closeTemplateModal")
      ?.addEventListener("click", closeTemplateModal);
    document
      .getElementById("cancelTemplateBtn")
      ?.addEventListener("click", closeTemplateModal);

    document
      .getElementById("closeUserModal")
      ?.addEventListener("click", closeUserModal);
    document
      .getElementById("cancelUserBtn")
      ?.addEventListener("click", closeUserModal);

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

    document
      .getElementById("closePaymentMethodModal")
      ?.addEventListener("click", () => {
        document
          .getElementById("paymentMethodModal")
          ?.classList.remove("active");
      });
    document
      .getElementById("cancelPaymentMethodBtn")
      ?.addEventListener("click", () => {
        document
          .getElementById("paymentMethodModal")
          ?.classList.remove("active");
      });

    // ✅ 5. BIND ADD BUTTONS
    if (addTemplateBtn) {
      addTemplateBtn.addEventListener("click", () => openTemplateModal(null));
    }
    if (addUserBtn) {
      addUserBtn.addEventListener("click", () => openUserModal(null));
    }

    document
      .getElementById("addProjectTypeBtn")
      ?.addEventListener("click", () => {
        document.getElementById("projectTypeModal")?.classList.add("active");
      });
    document
      .getElementById("addPaymentMethodBtn")
      ?.addEventListener("click", () => {
        document.getElementById("paymentMethodModal")?.classList.add("active");
      });

    // ✅ 6. EXPOSE GLOBALS
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

    // ✅ 7. LOAD DATA
    await Promise.all([loadAllSettings(), loadUsers()]);

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
