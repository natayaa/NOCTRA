// static/js/pages/settings/renderers/project-types.js

import { escapeHtml } from "../../../shared/utils.js";

export function renderProjectTypes(types) {
  const container = document.getElementById("projectTypeList");
  if (!container) return;

  if (!types || types.length === 0) {
    container.innerHTML = `
      <div class="empty-state-sm">
        <p>No project types defined. Click "Add Project Type" to create one.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = types
    .map(
      (type) => `
      <div class="project-type-item" data-id="${type.id}">
        <div class="item-info">
          <span style="font-weight:500;">${escapeHtml(type.name)}</span>
          ${
            type.base_price
              ? `<span style="color:var(--text-muted);font-size:0.75rem;">${formatCurrency(type.base_price)}</span>`
              : ""
          }
          ${
            !type.is_active
              ? `<span class="badge-inactive" style="font-size:0.6rem;padding:0.1rem 0.4rem;border-radius:var(--radius-full);background:rgba(239,68,68,0.12);color:#ef4444;">Inactive</span>`
              : ""
          }
        </div>
        <div class="item-actions">
          <button class="btn-edit" data-id="${type.id}" title="Edit"><i class="ph ph-pencil"></i></button>
          <button class="btn-delete" data-id="${type.id}" title="Delete"><i class="ph ph-trash"></i></button>
        </div>
      </div>
    `,
    )
    .join("");

  // Bind events for edit/delete
  container.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const item = types.find((t) => t.id === id);
      if (item) {
        // Open modal with data
        const modal = document.getElementById("projectTypeModal");
        const idInput = document.getElementById("editProjectTypeId");
        const nameInput = document.getElementById("projectTypeName");
        const priceInput = document.getElementById("projectTypeBasePrice");
        if (idInput) idInput.value = item.id;
        if (nameInput) nameInput.value = item.name || "";
        if (priceInput) priceInput.value = item.base_price || "";
        if (modal) modal.classList.add("active");
      }
    });
  });

  container.querySelectorAll(".btn-delete").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const item = types.find((t) => t.id === id);
      if (item && confirm(`Delete project type "${item.name}"?`)) {
        window.deleteProjectType(id);
      }
    });
  });
}

function formatCurrency(amount) {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
  }).format(amount);
}
