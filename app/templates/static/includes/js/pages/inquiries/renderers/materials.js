// inquiries/renderers/materials.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../formatters.js";
import { getItemName, getItemUnit, getItemCost } from "../utils.js";
import { state } from "../config.js";

export function renderDrawerMaterialUsages(materials) {
  const container = DOM.drawerMaterialUsages();
  if (!container) return;

  if (!materials || materials.length === 0) {
    container.innerHTML = `
      <div class="material-empty" style="text-align:center;padding:1rem 0;color:var(--text-muted);">
        <i class="ph ph-box" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
        <p>No material usage recorded</p>
      </div>
    `;
    return;
  }

  // ✅ Enrich materials with inventory data
  const enrichedMaterials = materials.map((item) => {
    const enriched = { ...item };
    const itemId = enriched.item_id || enriched.material_id;

    if (
      itemId &&
      (!enriched.item_name ||
        enriched.item_name === itemId ||
        enriched.item_name.startsWith("{"))
    ) {
      const foundItem = state.inventoryItems?.find((i) => i.id === itemId);
      if (foundItem) {
        enriched.item_name = foundItem.name || enriched.item_name;
        enriched.unit = foundItem.unit || enriched.unit || "";
        enriched.cost_price =
          foundItem.cost_price ||
          foundItem.selling_price ||
          enriched.cost_price ||
          0;
        enriched.category = foundItem.category || "";
      } else {
        enriched.item_name = getItemName(itemId);
        const unit = getItemUnit(itemId);
        if (unit) enriched.unit = unit;
        const cost = getItemCost(itemId);
        if (cost) enriched.cost_price = cost;
      }
    }
    return enriched;
  });

  // ✅ Group by material name
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
        category: item.category || "",
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
    <div class="material-list">
      ${materialList
        .map(
          (g) => `
        <div class="material-list-item" style="display:flex;justify-content:space-between;align-items:center;
                    padding:0.5rem 0.75rem;background:var(--bg-input);border-radius:var(--radius-sm);
                    margin-bottom:0.25rem;font-size:0.85rem;transition:background 0.2s ease;
                    border-left:3px solid var(--warning, #f59e0b);">
          <div style="display:flex;flex-direction:column;gap:0.1rem;flex:1;min-width:0;">
            <span class="name" style="font-weight:500;color:var(--text-primary);">
              ${escapeHtml(g.name)}
              ${g.category ? `<span style="font-size:0.6rem;color:var(--text-muted);background:var(--bg-card);padding:0.05rem 0.4rem;border-radius:var(--radius-full);">${escapeHtml(g.category)}</span>` : ""}
            </span>
            <span style="font-size:0.7rem;color:var(--text-muted);">
              ${g.items.length} transaction${g.items.length > 1 ? "s" : ""}
              ${g.cost > 0 ? `· Total: ${Formatter.currency(g.cost)}` : ""}
            </span>
          </div>
          <span class="qty" style="font-weight:600;color:var(--text-secondary);font-size:0.85rem;">
            ${g.total_qty} ${escapeHtml(g.unit)}
          </span>
        </div>
      `,
        )
        .join("")}
    </div>
    ${
      totalMaterialCost > 0
        ? `
      <div style="display:flex;justify-content:space-between;padding:0.6rem 0.75rem;margin-top:0.5rem;
                  border-top:2px solid var(--border);font-weight:600;color:var(--text-primary);
                  background:var(--bg-input);border-radius:var(--radius-sm);font-size:0.85rem;">
        <span>Total Material Cost</span>
        <span style="color:var(--warning, #f59e0b);">${Formatter.currency(totalMaterialCost)}</span>
      </div>
    `
        : ""
    }
  `;
}
