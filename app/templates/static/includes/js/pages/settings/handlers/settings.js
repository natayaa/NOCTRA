// static/js/pages/settings/handlers/settings.js

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { SettingsAPI } from "../api.js";
import { showToast } from "../../../pages/shared/toast.js";
import { renderTemplates } from "../renderers/templates.js";

// ============================================================
// LOAD SETTINGS
// ============================================================

export async function loadAllSettings() {
  const statusEl = DOM.saveStatus();
  if (statusEl) {
    statusEl.textContent = "Loading settings...";
    statusEl.className = "save-status loading";
  }

  try {
    const data = await SettingsAPI.getAllSettings();
    if (!data) return;

    // Update state
    state.workshop = data.workshop;
    state.pricing = data.pricing;
    state.security = data.security;
    state.whatsappTemplates = data.whatsapp_templates || [];
    state.projectTypes = data.project_types || [];
    state.paymentMethods = data.payment_methods || [];

    // Populate forms
    populateWorkshopForm(data.workshop);
    populatePricingForm(data.pricing);
    populateSecurityForm(data.security);
    populateSystemForm(data.pricing);

    // Render lists
    renderTemplates(data.whatsapp_templates || []);
    renderProjectTypes(data.project_types || []);
    renderPaymentMethods(data.payment_methods || []);

    if (statusEl) {
      statusEl.textContent = "✓ Settings loaded";
      statusEl.className = "save-status success";
      setTimeout(() => {
        statusEl.textContent = "Ready";
        statusEl.className = "save-status";
      }, 2000);
    }

    console.log("✅ All settings loaded successfully");
  } catch (error) {
    console.error("Failed to load settings:", error);
    if (statusEl) {
      statusEl.textContent = "❌ Failed to load settings";
      statusEl.className = "save-status error";
    }
    showToast("Failed to load settings: " + error.message, "error");
  }
}

// ============================================================
// POPULATE FORMS
// ============================================================

function populateWorkshopForm(data) {
  if (!data) return;
  const fields = {
    workshop_name: data.name,
    workshop_address: data.address,
    workshop_phone: data.phone,
    workshop_email: data.email,
    workshop_website: data.website,
  };
  Object.keys(fields).forEach((key) => {
    const el = document.getElementById(key);
    if (el) el.value = fields[key] || "";
  });
}

function populatePricingForm(data) {
  if (!data) return;
  const fields = {
    paint_base_price: data.paint_base_price,
    restoration_base_price: data.restoration_base_price,
    detailing_base_price: data.detailing_base_price,
    custom_color_price: data.custom_color_surcharge,
    labor_painter: data.labor_painter_per_day,
    labor_body: data.labor_body_per_day,
    labor_assembly: data.labor_assembly_per_day,
    labor_supervisor: data.labor_supervisor_per_day,
    tax_percent: data.tax_percent,
    default_margin: data.default_margin_percent,
    default_duration: data.default_duration_days,
    currency: data.currency,
  };
  Object.keys(fields).forEach((key) => {
    const el = document.getElementById(key);
    if (el) el.value = fields[key] ?? "";
  });
}

function populateSecurityForm(data) {
  if (!data) return;
  const checkboxes = {
    require_mfa: data.require_mfa,
    remember_me: data.allow_remember_me,
    force_password_change: data.force_password_change_days,
  };
  Object.keys(checkboxes).forEach((key) => {
    const el = document.getElementById(key);
    if (el) {
      if (typeof checkboxes[key] === "boolean") {
        el.checked = checkboxes[key] || false;
      } else {
        el.value = checkboxes[key] || "";
      }
    }
  });
}

function populateSystemForm(data) {
  if (!data) return;
  const checkboxes = {
    email_notifications: data.email_notifications_enabled,
    whatsapp_notifications: data.whatsapp_notifications_enabled,
    auto_invoice: data.auto_generate_invoice,
  };
  Object.keys(checkboxes).forEach((key) => {
    const el = document.getElementById(key);
    if (el) el.checked = checkboxes[key] || false;
  });
}

// ============================================================
// RENDER HELPERS (dipindah ke renderers/)
// ============================================================

function renderProjectTypes(types) {
  const container = document.getElementById("projectTypeList");
  if (!container) return;
  if (!types || types.length === 0) {
    container.innerHTML = `<div class="empty-state-sm"><p>No project types defined.</p></div>`;
    return;
  }
  container.innerHTML = types
    .map(
      (type) => `
        <div class="project-type-item" data-id="${type.id}">
            <div class="item-info">
                <span style="font-weight:500;">${escapeHtml(type.name)}</span>
                ${type.base_price ? `<span style="color:var(--text-muted);font-size:0.75rem;">${formatCurrency(type.base_price)}</span>` : ""}
                ${!type.is_active ? `<span class="badge-inactive">Inactive</span>` : ""}
            </div>
            <div class="item-actions">
                <button class="btn-edit" data-id="${type.id}" title="Edit"><i class="ph ph-pencil"></i></button>
                <button class="btn-delete" data-id="${type.id}" title="Delete"><i class="ph ph-trash"></i></button>
            </div>
        </div>
    `,
    )
    .join("");
}

function renderPaymentMethods(methods) {
  const container = document.getElementById("paymentMethodList");
  if (!container) return;
  if (!methods || methods.length === 0) {
    container.innerHTML = `<div class="empty-state-sm"><p>No payment methods defined.</p></div>`;
    return;
  }
  container.innerHTML = methods
    .map(
      (method) => `
        <div class="payment-method-item" data-id="${method.id}">
            <div class="item-info">
                ${method.icon ? `<span>${method.icon}</span>` : ""}
                <span style="font-weight:500;">${escapeHtml(method.name)}</span>
                <span style="color:var(--text-muted);font-size:0.7rem;">${escapeHtml(method.code)}</span>
                ${!method.is_active ? `<span class="badge-inactive">Inactive</span>` : ""}
            </div>
            <div class="item-actions">
                <button class="btn-edit" data-id="${method.id}" title="Edit"><i class="ph ph-pencil"></i></button>
                <button class="btn-delete" data-id="${method.id}" title="Delete"><i class="ph ph-trash"></i></button>
            </div>
        </div>
    `,
    )
    .join("");
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatCurrency(amount) {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
  }).format(amount);
}

// ============================================================
// SAVE SETTINGS
// ============================================================

export async function saveAllSettings() {
  const statusEl = DOM.saveStatus();
  if (statusEl) {
    statusEl.textContent = "Saving settings...";
    statusEl.className = "save-status loading";
  }

  let hasError = false;

  try {
    // 1. Save Workshop
    const workshopData = {
      name: document.getElementById("workshop_name")?.value,
      address: document.getElementById("workshop_address")?.value,
      phone: document.getElementById("workshop_phone")?.value,
      email: document.getElementById("workshop_email")?.value,
      website: document.getElementById("workshop_website")?.value,
    };
    const workshop = await SettingsAPI.updateWorkshop(workshopData);
    if (!workshop) hasError = true;

    // 2. Save Pricing
    const pricingData = {
      paint_base_price:
        parseInt(document.getElementById("paint_base_price")?.value) || 0,
      restoration_base_price:
        parseInt(document.getElementById("restoration_base_price")?.value) || 0,
      detailing_base_price:
        parseInt(document.getElementById("detailing_base_price")?.value) || 0,
      custom_color_surcharge:
        parseInt(document.getElementById("custom_color_price")?.value) || 0,
      labor_painter_per_day:
        parseInt(document.getElementById("labor_painter")?.value) || 0,
      labor_body_per_day:
        parseInt(document.getElementById("labor_body")?.value) || 0,
      labor_assembly_per_day:
        parseInt(document.getElementById("labor_assembly")?.value) || 0,
      labor_supervisor_per_day:
        parseInt(document.getElementById("labor_supervisor")?.value) || 0,
      tax_percent:
        parseFloat(document.getElementById("tax_percent")?.value) || 0,
      default_margin_percent:
        parseFloat(document.getElementById("default_margin")?.value) || 0,
      default_duration_days:
        parseInt(document.getElementById("default_duration")?.value) || 14,
      currency: document.getElementById("currency")?.value || "IDR",
      email_notifications_enabled:
        document.getElementById("email_notifications")?.checked || true,
      whatsapp_notifications_enabled:
        document.getElementById("whatsapp_notifications")?.checked || true,
      auto_generate_invoice:
        document.getElementById("auto_invoice")?.checked || true,
    };
    const pricing = await SettingsAPI.updatePricing(pricingData);
    if (!pricing) hasError = true;

    // 3. Save Security
    const securityData = {
      require_mfa: document.getElementById("require_mfa")?.checked || false,
      allow_remember_me:
        document.getElementById("remember_me")?.checked || true,
      force_password_change_days:
        parseInt(document.getElementById("force_password_change")?.value) || 90,
      session_timeout_minutes:
        parseInt(document.getElementById("session_timeout")?.value) || 60,
      max_login_attempts:
        parseInt(document.getElementById("max_login_attempts")?.value) || 5,
    };
    const security = await SettingsAPI.updateSecurity(securityData);
    if (!security) hasError = true;

    if (statusEl) {
      if (hasError) {
        statusEl.textContent = "⚠️ Some settings failed to save";
        statusEl.className = "save-status error";
        showToast("Some settings failed to save.", "warning");
      } else {
        statusEl.textContent = "✓ All settings saved successfully!";
        statusEl.className = "save-status success";
        showToast("✅ All settings saved successfully!", "success");
        setTimeout(() => {
          statusEl.textContent = "Ready";
          statusEl.className = "save-status";
        }, 3000);
      }
    }
  } catch (error) {
    console.error("Failed to save settings:", error);
    if (statusEl) {
      statusEl.textContent = "❌ Failed to save settings";
      statusEl.className = "save-status error";
    }
    showToast("Failed to save settings: " + error.message, "error");
  }
}
