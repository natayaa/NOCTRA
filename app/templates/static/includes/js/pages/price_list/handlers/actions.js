// ============================================================
// price_list/handlers/actions.js - CRUD Actions
// ============================================================

import { PriceAPI } from "../api.js";
import { showToast } from "../toast.js";
import { Formatter } from "../formatters.js";
import { state } from "../config.js";
import { getItemById } from "../utils.js";
import { loadPriceItems } from "../index.js";

export async function confirmDelete(itemId) {
  const item = getItemById(itemId);
  if (!item) return;

  if (
    !confirm(
      `Are you sure you want to delete "${item.name}"? This action cannot be undone.`,
    )
  )
    return;

  const result = await PriceAPI.deleteItem(itemId);
  if (result) {
    showToast("Price item deleted!", "success");
    await loadPriceItems();
  }
}

export async function handleToggleStatus(itemId) {
  const result = await PriceAPI.toggleItem(itemId);
  if (result) {
    showToast("Status toggled!", "success");
    await loadPriceItems();
  }
}

export function exportPriceItems() {
  if (!state.items || state.items.length === 0) {
    showToast("No data to export", "warning");
    return;
  }

  const data = state.items.map((item) => ({
    category: Formatter.categoryLabel(item.category),
    sub_category: item.sub_category || "",
    name: item.name,
    description: item.description || "",
    price: item.price || 0,
    cost_price: item.cost_price || 0,
    unit: item.unit || "",
    sku: item.sku || "",
    vehicle_brand: item.vehicle_brand || "",
    vehicle_model: item.vehicle_model || "",
    status: item.is_active ? "Active" : "Inactive",
    effective_date: Formatter.date(item.effective_date),
    expiry_date: Formatter.date(item.expiry_date),
  }));

  const headers = [
    "Category",
    "Sub Category",
    "Name",
    "Description",
    "Price",
    "Cost Price",
    "Unit",
    "SKU",
    "Vehicle Brand",
    "Vehicle Model",
    "Status",
    "Effective Date",
    "Expiry Date",
  ];
  const rows = data.map((d) => [
    d.category,
    d.sub_category,
    d.name,
    d.description,
    d.price,
    d.cost_price,
    d.unit,
    d.sku,
    d.vehicle_brand,
    d.vehicle_model,
    d.status,
    d.effective_date,
    d.expiry_date,
  ]);

  const csv = [headers.join(","), ...rows.map((row) => row.join(","))].join(
    "\n",
  );
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `price_list_export_${new Date().toISOString().split("T")[0]}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);

  showToast("Export completed!", "success");
}
