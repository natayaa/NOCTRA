// ============================================================
// price_list/handlers/modals.js - Modal Handlers
// ============================================================

import { DOM } from "../dom.js";
import { PriceAPI } from "../api.js";
import { showToast } from "../toast.js";
import { loadPriceItems } from "../index.js";

// -------- Create/Edit Modal --------
export function openCreateModal() {
  const title = DOM.modalTitle();
  const subtitle = DOM.modalSubtitle();
  const editId = DOM.editId();
  const form = DOM.priceForm();
  const isActive = DOM.isActive();
  const isTaxable = DOM.isTaxable();
  const isDiscountAllowed = DOM.isDiscountAllowed();
  const effectiveDate = DOM.effectiveDate();
  const submitBtn = DOM.submitBtn();
  const modal = DOM.priceModal();

  if (title) title.textContent = "Add Price Item";
  if (subtitle) subtitle.textContent = "Create a new price list item";
  if (editId) editId.value = "";
  if (form) form.reset();
  if (isActive) isActive.checked = true;
  if (isTaxable) isTaxable.checked = true;
  if (isDiscountAllowed) isDiscountAllowed.checked = true;
  if (effectiveDate)
    effectiveDate.value = new Date().toISOString().split("T")[0];
  if (submitBtn) submitBtn.textContent = "Create";
  if (modal) modal.classList.add("active");
}

export async function openEditModal(itemId) {
  const item = await PriceAPI.fetchItemDetail(itemId);
  if (!item) return;

  const title = DOM.modalTitle();
  const subtitle = DOM.modalSubtitle();
  const editId = DOM.editId();
  const submitBtn = DOM.submitBtn();
  const modal = DOM.priceModal();

  if (title) title.textContent = "Edit Price Item";
  if (subtitle) subtitle.textContent = `Editing: ${item.name}`;
  if (editId) editId.value = itemId;
  if (submitBtn) submitBtn.textContent = "Update";

  // Fill form fields
  const fields = {
    category: item.category,
    subCategory: item.sub_category,
    name: item.name,
    price: item.price,
    costPrice: item.cost_price,
    unit: item.unit,
    sku: item.sku,
    vehicleBrand: item.vehicle_brand,
    vehicleModel: item.vehicle_model,
    effectiveDate: item.effective_date ? item.effective_date.split("T")[0] : "",
    expiryDate: item.expiry_date ? item.expiry_date.split("T")[0] : "",
    minQuantity: item.min_quantity,
    maxQuantity: item.max_quantity,
    discountPercentage: item.discount_percentage,
    estimatedDuration: item.estimated_duration_hours,
    isActive: item.is_active !== false,
    isTaxable: item.is_taxable !== false,
    isDiscountAllowed: item.is_discount_allowed !== false,
    description: item.description,
  };

  for (const [key, value] of Object.entries(fields)) {
    const el = DOM[key]();
    if (el) {
      if (typeof value === "boolean") {
        el.checked = value;
      } else {
        el.value = value || "";
      }
    }
  }

  if (modal) modal.classList.add("active");
}

export function closeModal() {
  const modal = DOM.priceModal();
  const editId = DOM.editId();
  if (modal) modal.classList.remove("active");
  if (editId) editId.value = "";
}

export async function handleFormSubmit(e) {
  e.preventDefault();

  const data = {
    category: DOM.category()?.value || "",
    sub_category: DOM.subCategory()?.value || null,
    name: DOM.name()?.value?.trim() || "",
    price: parseFloat(DOM.price()?.value) || 0,
    cost_price: DOM.costPrice()?.value
      ? parseFloat(DOM.costPrice().value)
      : null,
    unit: DOM.unit()?.value || null,
    sku: DOM.sku()?.value || null,
    vehicle_brand: DOM.vehicleBrand()?.value || null,
    vehicle_model: DOM.vehicleModel()?.value || null,
    effective_date: DOM.effectiveDate()?.value || null,
    expiry_date: DOM.expiryDate()?.value || null,
    min_quantity: DOM.minQuantity()?.value
      ? parseInt(DOM.minQuantity().value)
      : null,
    max_quantity: DOM.maxQuantity()?.value
      ? parseInt(DOM.maxQuantity().value)
      : null,
    discount_percentage: DOM.discountPercentage()?.value
      ? parseFloat(DOM.discountPercentage().value)
      : null,
    estimated_duration_hours: DOM.estimatedDuration()?.value
      ? parseFloat(DOM.estimatedDuration().value)
      : null,
    is_active: DOM.isActive()?.checked ?? true,
    is_taxable: DOM.isTaxable()?.checked ?? true,
    is_discount_allowed: DOM.isDiscountAllowed()?.checked ?? true,
    description: DOM.description()?.value?.trim() || null,
  };

  // Validate
  if (!data.category) {
    showToast("Please select a category", "error");
    return;
  }
  if (!data.name) {
    showToast("Please enter a name", "error");
    return;
  }
  if (!data.price || data.price < 0) {
    showToast("Please enter a valid price", "error");
    return;
  }

  const editId = DOM.editId()?.value || "";
  const result = editId
    ? await PriceAPI.updateItem(editId, data)
    : await PriceAPI.createItem(data);

  if (result) {
    showToast(
      editId ? "Price item updated!" : "Price item created!",
      "success",
    );
    closeModal();
    await loadPriceItems();
  }
}
