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
    state.statusWorkflows = data.status_workflows || [];

    // Render forms
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
  }
}

// ============================================================
// POPULATE FORMS
// ============================================================

function populateWorkshopForm(data) {
  if (!data) return;

  const fields = {
    workshopName: data.name,
    workshopAddress: data.address,
    workshopPhone: data.phone,
    workshopEmail: data.email,
    workshopWebsite: data.website,
  };

  Object.keys(fields).forEach((key) => {
    const el = DOM[key]();
    if (el) el.value = fields[key] || "";
  });
}

function populatePricingForm(data) {
  if (!data) return;

  const fields = {
    paintBasePrice: data.paint_base_price,
    restorationBasePrice: data.restoration_base_price,
    detailingBasePrice: data.detailing_base_price,
    customColorPrice: data.custom_color_surcharge,
    laborPainter: data.labor_painter_per_day,
    laborBody: data.labor_body_per_day,
    laborAssembly: data.labor_assembly_per_day,
    laborSupervisor: data.labor_supervisor_per_day,
    taxPercent: data.tax_percent,
    defaultMargin: data.default_margin_percent,
    defaultDuration: data.default_duration_days,
    currency: data.currency,
  };

  Object.keys(fields).forEach((key) => {
    const el = DOM[key]();
    if (el) el.value = fields[key] ?? "";
  });
}

function populateSecurityForm(data) {
  if (!data) return;

  const fields = {
    requireMFA: data.require_mfa,
    rememberMe: data.allow_remember_me,
    forcePasswordChange: data.force_password_change_days,
    sessionTimeout: data.session_timeout_minutes,
    maxLoginAttempts: data.max_login_attempts,
  };

  // Checkboxes
  ["requireMFA", "rememberMe"].forEach((key) => {
    const el = DOM[key]();
    if (el) el.checked = fields[key] || false;
  });

  // Number inputs
  ["forcePasswordChange", "sessionTimeout", "maxLoginAttempts"].forEach(
    (key) => {
      const el = DOM[key]();
      if (el) el.value = fields[key] || "";
    },
  );
}

function populateSystemForm(data) {
  if (!data) return;

  const fields = {
    emailNotifications: data.email_notifications_enabled,
    whatsappNotifications: data.whatsapp_notifications_enabled,
    autoInvoice: data.auto_generate_invoice,
  };

  ["emailNotifications", "whatsappNotifications", "autoInvoice"].forEach(
    (key) => {
      const el = DOM[key]();
      if (el) el.checked = fields[key] || false;
    },
  );
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
      name: DOM.workshopName()?.value,
      address: DOM.workshopAddress()?.value,
      phone: DOM.workshopPhone()?.value,
      email: DOM.workshopEmail()?.value,
      website: DOM.workshopWebsite()?.value,
    };
    const workshop = await SettingsAPI.updateWorkshop(workshopData);
    if (!workshop) hasError = true;
    else state.workshop = workshop;

    // 2. Save Pricing
    const pricingData = {
      paint_base_price: parseInt(DOM.paintBasePrice()?.value) || 0,
      restoration_base_price: parseInt(DOM.restorationBasePrice()?.value) || 0,
      detailing_base_price: parseInt(DOM.detailingBasePrice()?.value) || 0,
      custom_color_surcharge: parseInt(DOM.customColorPrice()?.value) || 0,
      labor_painter_per_day: parseInt(DOM.laborPainter()?.value) || 0,
      labor_body_per_day: parseInt(DOM.laborBody()?.value) || 0,
      labor_assembly_per_day: parseInt(DOM.laborAssembly()?.value) || 0,
      labor_supervisor_per_day: parseInt(DOM.laborSupervisor()?.value) || 0,
      tax_percent: parseFloat(DOM.taxPercent()?.value) || 0,
      default_margin_percent: parseFloat(DOM.defaultMargin()?.value) || 0,
      default_duration_days: parseInt(DOM.defaultDuration()?.value) || 14,
      currency: DOM.currency()?.value || "IDR",
    };
    const pricing = await SettingsAPI.updatePricing(pricingData);
    if (!pricing) hasError = true;
    else state.pricing = pricing;

    // 3. Save Security
    const securityData = {
      require_mfa: DOM.requireMFA()?.checked || false,
      allow_remember_me: DOM.rememberMe()?.checked || true,
      force_password_change_days:
        parseInt(DOM.forcePasswordChange()?.value) || 90,
      session_timeout_minutes: parseInt(DOM.sessionTimeout()?.value) || 60,
      max_login_attempts: parseInt(DOM.maxLoginAttempts()?.value) || 5,
    };
    const security = await SettingsAPI.updateSecurity(securityData);
    if (!security) hasError = true;
    else state.security = security;

    // 4. Save System Preferences (part of pricing)
    const systemData = {
      email_notifications_enabled: DOM.emailNotifications()?.checked || true,
      whatsapp_notifications_enabled:
        DOM.whatsappNotifications()?.checked || true,
      auto_generate_invoice: DOM.autoInvoice()?.checked || true,
    };
    // Merge with pricing update
    const updatedPricing = await SettingsAPI.updatePricing(systemData);
    if (!updatedPricing) hasError = true;

    if (statusEl) {
      if (hasError) {
        statusEl.textContent = "⚠️ Some settings failed to save";
        statusEl.className = "save-status error";
        showToast("Some settings failed to save. Please try again.", "warning");
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
