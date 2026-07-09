// ============================================================
// projects/renderers/detail/materials.js - Materials Tab
// ============================================================

import { DOM } from "../../dom.js";
import { Formatter, escapeHtml } from "../../formatters.js";

export function renderMaterials(projectData) {
  const container = DOM.drawerMaterialsList();
  if (!container) return;

  const financial = projectData?.financial_summary || {};
  const materialUsages = financial.material_usages || [];

  if (!materialUsages || materialUsages.length === 0) {
    container.innerHTML =
      '<p style="color:var(--text-muted);">No materials consumed yet.</p>';
    return;
  }

  container.innerHTML = materialUsages
    .map((item) => {
      const name =
        item.item_name ||
        item.material_name ||
        item.name ||
        (item.item_id ? `ID: ${item.item_id.substring(0, 8)}` : "Unknown");
      const id = item.id;

      return `
            <div class="material-list-item" data-id="${id}">
                <span class="name">${escapeHtml(name)}</span>
                <span class="qty">${item.quantity} ${item.unit || item.item_unit || ""} (${Formatter.currency(item.total_cost)})</span>
                <button onclick="window.handleDeleteMaterial('${id}')" class="btn-danger btn-sm" title="Delete material usage">
                    <i class="ph ph-trash"></i>
                </button>
            </div>
        `;
    })
    .join("");
}
