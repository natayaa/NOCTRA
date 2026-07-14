// static/js/pages/settings/renderers/templates.js

import { escapeHtml } from "../../../pages/shared/utils.js";

export function renderTemplates(templates) {
  const container = document.getElementById("templateList");
  if (!container) return;

  if (!templates || templates.length === 0) {
    container.innerHTML = `
            <div class="empty-state-sm">
                <p>No WhatsApp templates yet. Create your first one.</p>
            </div>
        `;
    return;
  }

  container.innerHTML = templates
    .map(
      (template) => `
        <div class="template-card" data-template-id="${template.id}">
            <div class="template-header">
                <div class="template-name">
                    ${template.is_default ? '<span class="default-badge">Default</span>' : ""}
                    <h4>${escapeHtml(template.name)}</h4>
                </div>
                <div class="template-actions">
                    <button class="btn-secondary btn-sm edit-template" data-id="${template.id}" title="Edit">
                        <i class="ph ph-pencil"></i>
                    </button>
                    ${
                      !template.is_default
                        ? `
                        <button class="btn-secondary btn-sm set-default-template" data-id="${template.id}" title="Set as default">
                            <i class="ph ph-star"></i>
                        </button>
                    `
                        : ""
                    }
                    <button class="btn-danger btn-sm delete-template" data-id="${template.id}" title="Delete">
                        <i class="ph ph-trash"></i>
                    </button>
                </div>
            </div>
            <div class="template-preview">
                <div class="preview-label">Preview</div>
                <div class="preview-content">${escapeHtml(template.template).replace(/\n/g, "<br>")}</div>
            </div>
            ${
              template.variables && Object.keys(template.variables).length > 0
                ? `
                <div class="template-variables">
                    ${Object.keys(template.variables)
                      .map(
                        (key) => `
                        <span class="variable-tag">{{${escapeHtml(key)}}}</span>
                    `,
                      )
                      .join("")}
                </div>
            `
                : ""
            }
            ${
              template.description
                ? `
                <div class="template-description">
                    <small>${escapeHtml(template.description)}</small>
                </div>
            `
                : ""
            }
        </div>
    `,
    )
    .join("");

  // Bind events
  container.querySelectorAll(".edit-template").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const template = templates.find((t) => t.id === id);
      if (template) window.openTemplateModal(template);
    });
  });

  container.querySelectorAll(".set-default-template").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      if (confirm("Set this as default template?")) {
        window.setDefaultTemplate(id);
      }
    });
  });

  container.querySelectorAll(".delete-template").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const template = templates.find((t) => t.id === id);
      if (template && confirm(`Delete template "${template.name}"?`)) {
        window.deleteTemplate(id);
      }
    });
  });
}
