// ============================================================
// inventories/handlers/actions.js - CRUD Actions
// ============================================================

import { InventoryAPI } from "../api.js";
import { showToast } from "../toast.js";
import { state } from "../config.js";
import { getItemById } from "../utils.js";
import { renderDetailPanel } from "../renderers/detail.js";
import { loadInventoryItems } from "../index.js";

export async function confirmDelete(itemId) {
  const item = getItemById(itemId);
  if (!item) return;

  if (
    !confirm(
      `Are you sure you want to delete "${item.name}"? This action cannot be undone.`,
    )
  )
    return;

  const result = await InventoryAPI.deleteItem(itemId);
  if (result) {
    showToast("Item deleted!", "success");
    if (state.selectedItemId === itemId) {
      state.selectedItemId = null;
      renderDetailPanel(null);
    }
    await loadInventoryItems();
  }
}

export function filterByCategory(category) {
  const filter = DOM.categoryFilter();
  if (filter) {
    filter.value = category;
    filter.dispatchEvent(new Event("change"));
  }
}

export function exportInventory() {
  if (!state.items || state.items.length === 0) {
    showToast("No data to export", "warning");
    return;
  }

  const data = state.items.map((item) => ({
    name: item.name,
    category: item.category || "",
    sub_category: item.sub_category || "",
    sku: item.sku || "",
    unit: item.unit || "",
    current_stock: item.current_stock || 0,
    min_stock_threshold: item.min_stock_threshold || 0,
    cost_price: item.cost_price || 0,
    selling_price: item.selling_price || 0,
    value: (item.current_stock || 0) * (item.cost_price || 0),
    location: item.location || "",
    status: item.status || "active",
  }));

  const headers = [
    "Name",
    "Category",
    "Sub Category",
    "SKU",
    "Unit",
    "Stock",
    "Min Stock",
    "Cost Price",
    "Selling Price",
    "Total Value",
    "Location",
    "Status",
  ];
  const rows = data.map((d) => [
    d.name,
    d.category,
    d.sub_category,
    d.sku,
    d.unit,
    d.current_stock,
    d.min_stock_threshold,
    d.cost_price,
    d.selling_price,
    d.value,
    d.location,
    d.status,
  ]);

  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `inventory_export_${new Date().toISOString().split("T")[0]}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);

  showToast("Export completed!", "success");
}
