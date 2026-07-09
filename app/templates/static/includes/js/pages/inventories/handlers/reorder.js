// ============================================================
// inventories/handlers/reorder.js - Reorder / Purchase Order
// ============================================================

import { DOM } from "../dom.js";
import { InventoryAPI } from "../api.js";
import { showToast } from "../toast.js";
import { escapeHtml } from "../formatters.js";
import { loadInventoryItems } from "../index.js";

export async function openReorderModal(itemId) {
  const item = await InventoryAPI.fetchItemDetail(itemId);
  if (!item) return;

  const modal = DOM.reorderModal();
  const id = DOM.reorderItemId();
  const name = DOM.reorderItemName();
  const current = DOM.reorderCurrentStock();
  const threshold = DOM.reorderThreshold();
  const qty = DOM.reorderQuantity();

  if (id) id.value = itemId;
  if (name) name.textContent = item.name;
  if (current) current.textContent = `${item.current_stock} ${item.unit || ""}`;
  if (threshold)
    threshold.textContent = `${item.min_stock_threshold || 0} ${item.unit || ""}`;
  if (qty) {
    qty.value =
      Math.max((item.min_stock_threshold || 5) - (item.current_stock || 0), 0) +
      10;
  }

  const suppliers = await InventoryAPI.fetchSuppliers();
  const select = DOM.reorderSupplier();
  if (select) {
    if (suppliers && suppliers.length > 0) {
      select.innerHTML = `
                <option value="">Select Supplier</option>
                ${suppliers
                  .map(
                    (s) => `
                    <option value="${s.id}" ${s.id === item.supplier_id ? "selected" : ""}>${escapeHtml(s.name)}</option>
                `,
                  )
                  .join("")}
            `;
    } else {
      select.innerHTML = '<option value="">No suppliers available</option>';
    }
  }

  if (modal) modal.classList.add("active");
}

export function closeReorderModal() {
  const modal = DOM.reorderModal();
  const id = DOM.reorderItemId();
  if (modal) modal.classList.remove("active");
  if (id) id.value = "";
}

export async function handleReorderSubmit(e) {
  e.preventDefault();

  const itemId = DOM.reorderItemId()?.value;
  const quantity = parseFloat(DOM.reorderQuantity()?.value);
  const supplierId = DOM.reorderSupplier()?.value;

  if (!itemId) return showToast("No item selected", "error");
  if (!quantity || quantity <= 0)
    return showToast("Please enter a valid quantity", "error");

  const result = await InventoryAPI.createPurchaseOrder({
    supplier_id: supplierId || null,
    items: [{ item_id: itemId, quantity: quantity, unit_price: 0 }],
    notes: `Reorder for item ${itemId}`,
  });

  if (result) {
    showToast("Purchase order created successfully!", "success");
    closeReorderModal();
    await loadInventoryItems();
  }
}
