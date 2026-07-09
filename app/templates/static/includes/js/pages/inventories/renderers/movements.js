// ============================================================
// inventories/renderers/movements.js - Recent Movements Rendering
// ============================================================

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../formatters.js";
import { state } from "../config.js";

export function renderRecentMovements(movements) {
  const list = DOM.recentMovements();
  if (!list) return;

  if (!movements || movements.length === 0) {
    list.innerHTML =
      '<div class="loading-placeholder-sm">No recent movements</div>';
    return;
  }

  list.innerHTML = movements
    .map((m) => {
      let itemName = m.item_name || m.name || m.item?.name || m.item_id;

      if (!itemName || itemName === m.item_id) {
        const item = state.items.find((i) => i.id === m.item_id);
        itemName = item
          ? item.name
          : m.item_id
            ? m.item_id.substring(0, 8)
            : "Unknown";
      }

      const qty = Number(m.quantity) || 0;
      const type = m.movement_type || m.type || "unknown";
      const isIn = ["in", "purchase", "restock", "stock_in"].includes(type);

      return `
            <div class="movement-item ${isIn ? "stock-in" : "stock-out"}">
                <div class="movement-icon">
                    <i class="fas ${isIn ? "fa-arrow-down" : "fa-arrow-up"}"></i>
                </div>
                <div class="movement-info">
                    <strong>${escapeHtml(itemName)}</strong>
                    <span>${Formatter.date(m.created_at)} · ${escapeHtml(m.reference_type || type)}</span>
                </div>
                <span class="movement-qty ${isIn ? "positive" : "negative"}">
                    ${isIn ? "+" : "-"}${qty} ${escapeHtml(m.unit || "")}
                </span>
            </div>
        `;
    })
    .join("");
}
