// static/js/pages/settings/handlers/templates.js

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { SettingsAPI } from "../api.js";
import { showToast } from "../../../pages/shared/toast.js";
import { renderTemplates } from "../renderers/templates.js";

// ============================================================
// OPEN TEMPLATE MODAL
// ============================================================

export function openTemplateModal(template = null) {
  const modal = DOM.templateModal();
  const title = DOM.templateModalTitle();
  const form = DOM.templateForm();
  const idInput = DOM.templateId();
  const nameInput = DOM.templateName();
  const descInput = DOM.templateDescription();
  const contentInput = DOM.templateContent();
  const defaultCheck = DOM.templateIsDefault();

  if (!modal) return;

  if (template) {
    // Edit mode
    title.textContent = "Edit WhatsApp Template";
    if (idInput) idInput.value = template.id;
    if (nameInput) nameInput.value = template.name || "";
    if (descInput) descInput.value = template.description || "";
    if (contentInput) contentInput.value = template.template || "";
    if (defaultCheck) defaultCheck.checked = template.is_default || false;
  } else {
    // Create mode
    title.textContent = "New WhatsApp Template";
    if (idInput) idInput.value = "";
    if (nameInput) nameInput.value = "";
    if (descInput) descInput.value = "";
    if (contentInput) contentInput.value = "";
    if (defaultCheck) defaultCheck.checked = false;
  }

  modal.classList.add("active");
  setTimeout(() => nameInput?.focus(), 100);
}

// ============================================================
// CLOSE TEMPLATE MODAL
// ============================================================

export function closeTemplateModal() {
  const modal = DOM.templateModal();
  if (modal) {
    modal.classList.remove("active");
  }
  // Reset form
  const form = DOM.templateForm();
  if (form) form.reset();
}

// ============================================================
// SAVE TEMPLATE
// ============================================================

export async function saveTemplate(e) {
  e.preventDefault();

  const idInput = DOM.templateId();
  const nameInput = DOM.templateName();
  const descInput = DOM.templateDescription();
  const contentInput = DOM.templateContent();
  const defaultCheck = DOM.templateIsDefault();

  const name = nameInput?.value?.trim();
  const content = contentInput?.value?.trim();

  if (!name) {
    showToast("Please enter a template name", "warning");
    nameInput?.focus();
    return;
  }

  if (!content) {
    showToast("Please enter the template content", "warning");
    contentInput?.focus();
    return;
  }

  // Extract variables from content
  const variables = {};
  const varMatches = content.match(/{{([^}]+)}}/g);
  if (varMatches) {
    const uniqueVars = [
      ...new Set(varMatches.map((v) => v.replace(/[{}]/g, ""))),
    ];
    uniqueVars.forEach((v) => {
      // Use variable name as label
      variables[v] = v
        .split("_")
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");
    });
  }

  const data = {
    name,
    template: content,
    description: descInput?.value?.trim() || null,
    is_default: defaultCheck?.checked || false,
    variables: Object.keys(variables).length > 0 ? variables : null,
  };

  const id = idInput?.value;
  let result;

  if (id) {
    // Update existing
    result = await SettingsAPI.updateWhatsAppTemplate(id, data);
  } else {
    // Create new
    result = await SettingsAPI.createWhatsAppTemplate(data);
  }

  if (result) {
    closeTemplateModal();
    // Reload templates
    const templates = await SettingsAPI.getWhatsAppTemplates();
    state.whatsappTemplates = templates;
    renderTemplates(templates);
  }
}

// ============================================================
// DELETE TEMPLATE
// ============================================================

export async function deleteTemplate(id) {
  const success = await SettingsAPI.deleteWhatsAppTemplate(id);
  if (success) {
    const templates = await SettingsAPI.getWhatsAppTemplates();
    state.whatsappTemplates = templates;
    renderTemplates(templates);
  }
}

// ============================================================
// SET DEFAULT TEMPLATE
// ============================================================

export async function setDefaultTemplate(id) {
  const success = await SettingsAPI.setDefaultTemplate(id);
  if (success) {
    const templates = await SettingsAPI.getWhatsAppTemplates();
    state.whatsappTemplates = templates;
    renderTemplates(templates);
  }
}
