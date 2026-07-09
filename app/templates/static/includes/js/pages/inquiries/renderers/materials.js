// ============================================================
// inquiries/renderers/materials.js - Material Usage Rendering
// ============================================================

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../formatters.js";
import { getItemName, getItemUnit, getItemCost } from "../utils.js";
import { state } from "../config.js";

export function renderDrawerMaterialUsages(materials) {
  const container = DOM.drawerMaterialUsages();
  if (!container) return;

  if (!materials || materials.length === 0) {
    container.innerHTML = `
            <div style="text-align:center;padding:0.5rem 0;color:var(--text-muted);">
                <i class="ph ph-box" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
                No material usage recorded
            </div>
        `;
    return;
  }

  const enrichedMaterials = materials.map((item) => {
    const enriched = { ...item };
    if (
      !enriched.item_name ||
      enriched.item_name === enriched.item_id ||
      enriched.item_name.startsWith("{")
    ) {
      const foundItem = state.inventoryItems?.find(
        (i) => i.id === enriched.item_id,
      );
      if (foundItem) {
        enriched.item_name = foundItem.name;
        enriched.unit = foundItem.unit || enriched.unit || "";
        enriched.cost_price = foundItem.cost_price || enriched.cost_price || 0;
      } else {
        enriched.item_name = getItemName(enriched.item_id);
        const unit = getItemUnit(enriched.item_id);
        if (unit) enriched.unit = unit;
        const cost = getItemCost(enriched.item_id);
        if (cost) enriched.cost_price = cost;
      }
    }
    return enriched;
  });

  const grouped = {};
  enrichedMaterials.forEach((item) => {
    const key = item.item_name || item.item_id || "Unknown";
    if (!grouped[key]) {
      grouped[key] = {
        name: key,
        total_qty: 0,
        unit: item.unit || "",
        items: [],
        item_id: item.item_id,
      };
    }
    grouped[key].total_qty += Number(item.quantity) || 0;
    grouped[key].unit = item.unit || grouped[key].unit;
    grouped[key].items.push(item);
  });

  let totalMaterialCost = 0;
  const materialList = Object.values(grouped).map((g) => {
    const cost = g.items.reduce((sum, i) => {
      const price =
        Number(i.cost_price) || Number(i.unit_price) || Number(i.price) || 0;
      return sum + price * (Number(i.quantity) || 0);
    }, 0);
    totalMaterialCost += cost;
    return { ...g, cost };
  });

  container.innerHTML = `
        ${materialList
          .map(
            (g) => `
            <div class="material-list-item" style="display:flex;justify-content:space-between;align-items:center;
                        padding:0.5rem 0.75rem;background:var(--bg-input);border-radius:var(--radius-sm);
                        margin-bottom:0.25rem;font-size:0.85rem;">
                <div style="display:flex;flex-direction:column;gap:0.1rem;">
                    <span class="name" style="font-weight:500;color:var(--text-primary);">
                        ${escapeHtml(g.name)}
                    </span>
                    <span style="font-size:0.7rem;color:var(--text-muted);">
                        ${g.items.length} transaction${g.items.length > 1 ? "s" : ""}
                        ${g.cost > 0 ? `· ${Formatter.currency(g.cost)}` : ""}
                    </span>
                </div>
                <span class="qty" style="font-weight:600;color:var(--text-secondary);">
                    ${g.total_qty} ${escapeHtml(g.unit)}
                </span>
            </div>
        `,
          )
          .join("")}
        ${
          totalMaterialCost > 0
            ? `
            <div style="display:flex;justify-content:space-between;padding:0.5rem 0.75rem;margin-top:0.5rem;
                        border-top:2px solid var(--border);font-weight:600;color:var(--text-primary);">
                <span>Total Material Cost</span>
                <span>${Formatter.currency(totalMaterialCost)}</span>
            </div>
        `
            : ""
        }
    `;
}
