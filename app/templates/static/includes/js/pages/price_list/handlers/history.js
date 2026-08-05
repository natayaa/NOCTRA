// ============================================================
// price_list/handlers/history.js - Price History
// ============================================================

import { DOM } from "../dom.js";
import { PriceAPI } from "../api.js";
import { Formatter, escapeHtml } from "../formatters.js";
import { state } from "../config.js";
import { getItemById } from "../utils.js";

export async function openHistoryModal(itemId) {
  const historyData = await PriceAPI.fetchHistory(itemId);
  if (!historyData) return;

  // ✅ FIX: Ensure history is always an array
  let history = [];
  if (Array.isArray(historyData)) {
    history = historyData;
  } else if (historyData.data && Array.isArray(historyData.data)) {
    history = historyData.data;
  } else if (historyData.items && Array.isArray(historyData.items)) {
    history = historyData.items;
  } else if (historyData.history && Array.isArray(historyData.history)) {
    history = historyData.history;
  } else if (typeof historyData === "object" && historyData !== null) {
    // If it's a single object, wrap it in array
    history = [historyData];
  } else {
    history = [];
  }

  console.log("📊 History data processed:", history);

  const item = getItemById(itemId);
  const nameEl = DOM.historyItemName();
  const totalChangesEl = DOM.totalChanges();
  const currentPriceEl = DOM.currentPrice();
  const firstPriceEl = DOM.firstPrice();
  const avgChangeEl = DOM.avgChange();
  const bodyEl = DOM.historyBody();
  const modal = DOM.historyModal();

  if (nameEl) nameEl.textContent = item ? item.name : "Item";

  // Summary
  if (totalChangesEl) totalChangesEl.textContent = history.length || 0;
  if (currentPriceEl) {
    currentPriceEl.textContent =
      history.length > 0
        ? Formatter.currency(history[history.length - 1]?.new_price)
        : "-";
  }
  if (firstPriceEl) {
    firstPriceEl.textContent =
      history.length > 0 ? Formatter.currency(history[0]?.new_price) : "-";
  }

  // Calculate average change
  let totalChange = 0;
  if (history.length > 0) {
    history.forEach((h) => {
      const change = (h.new_price || 0) - (h.old_price || 0);
      totalChange += change;
    });
  }
  const avgChange = history.length > 0 ? totalChange / history.length : 0;
  if (avgChangeEl) avgChangeEl.textContent = Formatter.currency(avgChange);

  // Render history rows
  if (!history || history.length === 0) {
    if (bodyEl) {
      bodyEl.innerHTML =
        '<tr><td colspan="6" class="no-data">No price history available</td></tr>';
    }
  } else {
    if (bodyEl) {
      bodyEl.innerHTML = history
        .map((h) => {
          const oldPrice = h.old_price || 0;
          const newPrice = h.new_price || 0;
          const change = newPrice - oldPrice;
          const changePercent =
            oldPrice > 0 ? ((change / oldPrice) * 100).toFixed(1) : 0;

          return `
                    <tr>
                        <td>${Formatter.dateTime(h.changed_at || h.created_at || h.updated_at)}</td>
                        <td>${Formatter.currency(oldPrice)}</td>
                        <td><strong>${Formatter.currency(newPrice)}</strong></td>
                        <td style="color:${change >= 0 ? "var(--success, #10b981)" : "var(--danger, #ef4444)"};">
                            ${change >= 0 ? "+" : ""}${Formatter.currency(change)} (${change >= 0 ? "+" : ""}${changePercent}%)
                        </td>
                        <td>${escapeHtml(h.changed_by || h.updated_by || "system")}</td>
                        <td style="max-width:150px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                            ${escapeHtml(h.reason || "-")}
                        </td>
                    </tr>
                `;
        })
        .join("");
    }
  }

  if (modal) modal.classList.add("active");
}

export function closeHistoryModal() {
  const modal = DOM.historyModal();
  if (modal) modal.classList.remove("active");
}
