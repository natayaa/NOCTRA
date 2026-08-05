// projects/renderers/detail/materials.js (FIXED & IMPROVED)

import { DOM } from "../../dom.js";
import { Formatter, escapeHtml } from "../../formatters.js";

export function renderMaterials(projectData) {
  const container = DOM.drawerMaterialsList();
  if (!container) return;

  const financial = projectData?.financial_summary || {};
  const materialUsages = financial.material_usages || [];

  // Update count
  const countEl = document.getElementById("materialCount");
  if (countEl) {
    countEl.textContent = `${materialUsages.length} entry${materialUsages.length !== 1 ? "s" : ""}`;
  }

  if (!materialUsages || materialUsages.length === 0) {
    container.innerHTML = `
      <div class="material-empty" style="display:flex;flex-direction:column;align-items:center;gap:0.5rem;padding:1.5rem 0;color:var(--text-muted);">
        <i class="ph ph-package" style="font-size:1.5rem;opacity:0.4;"></i>
        <p>No materials consumed yet.</p>
        <small style="font-size:0.8rem;">Consume materials using the form above</small>
      </div>
    `;
    return;
  }

  let totalMaterialCost = 0;

  container.innerHTML = materialUsages
    .map((item) => {
      const name =
        item.item_name ||
        item.material_name ||
        item.name ||
        (item.item_id ? `Item ${item.item_id.substring(0, 8)}` : "Unknown");
      const id = item.id;
      const quantity = item.quantity || 0;
      const unit = item.unit || item.item_unit || "";
      const totalCost = item.total_cost || 0;

      totalMaterialCost += totalCost;

      return `
      <div class="material-list-item" data-id="${id}">
        <div class="material-info" style="display:flex;align-items:center;gap:0.75rem;flex:1;min-width:0;">
          <span class="name" style="font-weight:500;color:var(--text-primary);">${escapeHtml(name)}</span>
          ${item.item_category ? `<span class="category" style="font-size:0.7rem;color:var(--text-muted);">${escapeHtml(item.item_category)}</span>` : ""}
        </div>
        <span class="qty" style="font-weight:600;color:var(--text-secondary);font-size:0.85rem;white-space:nowrap;">
          ${quantity} ${escapeHtml(unit)}
        </span>
        <span class="total" style="font-weight:600;color:var(--text-primary);font-size:0.85rem;white-space:nowrap;margin:0 0.5rem;">
          ${Formatter.currency(totalCost)}
        </span>
        <button onclick="window.handleDeleteMaterial('${id}')" class="btn-danger btn-sm" title="Delete material usage">
          <i class="ph ph-trash"></i>
        </button>
      </div>
    `;
    })
    .join("");

  // ✅ Add total summary
  if (materialUsages.length > 0 && totalMaterialCost > 0) {
    container.innerHTML += `
      <div class="material-summary-footer" style="display:flex;justify-content:space-between;padding:0.6rem 0.75rem;margin-top:0.5rem;
                  border-top:2px solid var(--border);font-weight:600;color:var(--text-primary);
                  background:var(--bg-input);border-radius:var(--radius-sm);font-size:0.85rem;">
        <span>Total Material Cost</span>
        <span style="color:var(--warning, #f59e0b);">${Formatter.currency(totalMaterialCost)}</span>
      </div>
    `;
  }
}

export function updateMaterialTotal(materialUsages) {
  if (!materialUsages || materialUsages.length === 0) return 0;
  return materialUsages.reduce((sum, item) => sum + (item.total_cost || 0), 0);
}
