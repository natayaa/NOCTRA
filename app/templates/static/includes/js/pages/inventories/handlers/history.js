// ============================================================
// inventories/handlers/history.js - Movement History
// ============================================================

import { DOM } from "../dom.js";
import { InventoryAPI } from "../api.js";
import { Formatter, escapeHtml } from "../formatters.js";
import { state } from "../config.js";
import { getItemById } from "../utils.js";
import { ensureArray } from "../utils.js";

export async function openHistoryModal(itemId) {
  const item = getItemById(itemId);
  if (!item) return showToast("Item not found", "error");

  const name = DOM.historyItemName();
  if (name) name.textContent = item.name;

  const movementsData = await InventoryAPI.fetchItemMovements(itemId);
  const movements = ensureArray(movementsData);

  const body = DOM.historyBody();
  if (!body) return;

  if (!movements || movements.length === 0) {
    body.innerHTML =
      '<tr><td colspan="6" class="no-data">No movement history</td></tr>';
  } else {
    body.innerHTML = movements
      .map(
        (m) => `
            <tr>
                <td>${Formatter.dateTime(m.created_at)}</td>
                <td><span class="status-badge ${m.type === "in" ? "active" : "inactive"}">${escapeHtml(m.movement_type || m.type || "")}</span></td>
                <td><strong>${m.type === "in" ? "+" : "-"}${m.quantity}</strong></td>
                <td>${m.previous_stock || "-"}</td>
                <td>${m.new_stock || "-"}</td>
                <td>${escapeHtml(m.performed_by || "system")}</td>
            </tr>
        `,
      )
      .join("");
  }

  const modal = DOM.historyModal();
  if (modal) modal.classList.add("active");
}

export function closeHistoryModal() {
  const modal = DOM.historyModal();
  if (modal) modal.classList.remove("active");
}
