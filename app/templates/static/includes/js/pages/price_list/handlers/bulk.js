// ============================================================
// price_list/handlers/bulk.js - Bulk Update
// ============================================================

import { DOM } from "../dom.js";
import { PriceAPI } from "../api.js";
import { showToast } from "../toast.js";
import { getAffectedItemsCount } from "../utils.js";
import { loadPriceItems } from "../index.js";
import { state } from "../config.js";

export function openBulkModal() {
  const form = DOM.bulkForm();
  const preview = DOM.bulkPreview();
  const modal = DOM.bulkModal();

  if (form) form.reset();
  if (preview) preview.style.display = "none";
  if (modal) modal.classList.add("active");
}

export function closeBulkModal() {
  const modal = DOM.bulkModal();
  if (modal) modal.classList.remove("active");
}

export function updateBulkPreview() {
  const category = DOM.bulkCategory()?.value || "";
  const vehicleBrand = DOM.bulkVehicleBrand()?.value || null;
  const preview = DOM.bulkPreview();
  const previewText = DOM.bulkPreviewText();

  if (!category) {
    if (preview) preview.style.display = "none";
    return;
  }

  const count = getAffectedItemsCount(category, vehicleBrand);
  if (previewText) {
    previewText.textContent = `${count} items will be updated (${count > 0 ? "active" : "no active"} items)`;
  }
  if (preview) {
    preview.style.display = "block";
    preview.style.borderColor = count > 0 ? "var(--success)" : "var(--danger)";
  }
}

export async function handleBulkSubmit(e) {
  e.preventDefault();

  const category = DOM.bulkCategory()?.value || "";
  const percentage = parseFloat(DOM.bulkPercentage()?.value) || 0;
  const vehicleBrand = DOM.bulkVehicleBrand()?.value || null;

  if (!category) {
    showToast("Please select a category", "error");
    return;
  }
  if (!percentage || isNaN(percentage)) {
    showToast("Please enter a valid percentage", "error");
    return;
  }

  const affectedItems = state.items.filter(
    (item) =>
      item.category === category &&
      item.is_active !== false &&
      (!vehicleBrand || item.vehicle_brand === vehicleBrand),
  );

  if (affectedItems.length === 0) {
    showToast("No active items found matching the criteria", "warning");
    return;
  }

  if (
    !confirm(`Update ${affectedItems.length} items with ${percentage}% change?`)
  )
    return;

  const result = await PriceAPI.bulkUpdate({
    category,
    percentage,
    vehicle_brand: vehicleBrand,
  });
  if (result) {
    showToast(`Successfully updated ${affectedItems.length} items!`, "success");
    closeBulkModal();
    await loadPriceItems();
  }
}

// Bind bulk preview events
export function bindBulkEvents() {
  const category = DOM.bulkCategory();
  const vehicleBrand = DOM.bulkVehicleBrand();

  if (category) {
    category.addEventListener("change", updateBulkPreview);
  }
  if (vehicleBrand) {
    vehicleBrand.addEventListener("change", updateBulkPreview);
  }
}
