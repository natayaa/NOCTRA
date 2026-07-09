// ============================================================
// inventories/handlers/stock.js - Stock Adjustment
// ============================================================

import { DOM } from "../dom.js";
import { InventoryAPI } from "../api.js";
import { showToast } from "../toast.js";
import { state } from "../config.js";
import { loadInventoryItems } from "../index.js";
import { selectItem } from "../index.js";

export async function openStockAdjustModal(itemId) {
  const item = await InventoryAPI.fetchItemDetail(itemId);
  if (!item) return;

  const modal = DOM.stockAdjustModal();
  const id = DOM.adjustItemId();
  const current = DOM.adjustCurrentStock();
  const newStock = DOM.adjustNewStock();
  const reason = DOM.adjustReasonSelect();
  const notes = DOM.adjustNotes();

  if (id) id.value = itemId;
  if (current) current.textContent = `${item.current_stock} ${item.unit || ""}`;
  if (newStock) newStock.value = item.current_stock || 0;
  if (reason) reason.value = "";
  if (notes) notes.value = "";
  if (modal) modal.classList.add("active");
}

export function closeStockAdjustModal() {
  const modal = DOM.stockAdjustModal();
  const id = DOM.adjustItemId();
  if (modal) modal.classList.remove("active");
  if (id) id.value = "";
}

export async function handleStockAdjust(e) {
  e.preventDefault();

  const itemId = DOM.adjustItemId()?.value;
  const newStock = parseFloat(DOM.adjustNewStock()?.value);
  const reason = DOM.adjustReasonSelect()?.value;
  const notes = DOM.adjustNotes()?.value?.trim() || "";

  if (!itemId) return showToast("No item selected", "error");
  if (isNaN(newStock) || newStock < 0)
    return showToast("Please enter a valid stock quantity", "error");
  if (!reason) return showToast("Please select a reason", "error");

  const result = await InventoryAPI.adjustStock({
    item_id: itemId,
    quantity: newStock,
    movement_type: reason,
    reference_type: "adjustment",
    note: notes || reason,
    performed_by: "admin",
  });

  if (result) {
    showToast("Stock updated successfully!", "success");
    closeStockAdjustModal();
    await loadInventoryItems();
    if (state.selectedItemId) await selectItem(state.selectedItemId);
  }
}
