// inventories/handlers/modals.js - FIXED

import { DOM } from "../dom.js";
import { InventoryAPI } from "../api.js";
import { showToast } from "../toast.js";
import { state } from "../config.js";
import { loadInventoryItems } from "../index.js";
import { selectItem } from "../index.js";
import { escapeHtml } from "../formatters.js";

// --- Create/Edit Modal ---
export function openCreateModal() {
  const modal = DOM.inventoryModal();
  const title = DOM.modalTitle();
  const editId = DOM.editId();
  const form = DOM.inventoryForm();
  const submit = DOM.submitBtn();

  if (title) title.textContent = "Add Inventory Item";
  if (editId) editId.value = "";
  if (form) form.reset();
  if (submit) submit.textContent = "Create Item";

  // Set defaults
  const stock = DOM.itemStock();
  const reorder = DOM.reorderLevel();
  if (stock) stock.value = 0;
  if (reorder) reorder.value = 5;

  if (modal) modal.classList.add("active");

  loadSupplierOptions();
}

export async function openEditModal(itemId) {
  const item = await InventoryAPI.fetchItemDetail(itemId);
  if (!item) {
    showToast("Failed to load item", "error");
    return;
  }

  const modal = DOM.inventoryModal();
  const title = DOM.modalTitle();
  const editId = DOM.editId();
  const submit = DOM.submitBtn();

  if (title) title.textContent = "Edit Inventory Item";
  if (editId) editId.value = itemId;
  if (submit) submit.textContent = "Update Item";

  const fields = {
    itemName: item.name,
    itemCategory: item.category,
    itemSubCategory: item.sub_category,
    itemUnit: item.unit,
    itemStock: item.current_stock,
    reorderLevel: item.min_stock_threshold,
    itemCost: item.cost_price,
    itemSellingPrice: item.selling_price,
    itemSku: item.sku,
    itemBarcode: item.barcode,
    itemLocation: item.location,
    itemDescription: item.description,
  };

  for (const [key, value] of Object.entries(fields)) {
    const el = DOM[key]();
    if (el) el.value = value ?? "";
  }

  await loadSupplierOptions(item.supplier_id);
  if (modal) modal.classList.add("active");
}

export function closeModal() {
  const modal = DOM.inventoryModal();
  const editId = DOM.editId();
  if (modal) modal.classList.remove("active");
  if (editId) editId.value = "";
}

async function loadSupplierOptions(selectedId = null) {
  const suppliers = await InventoryAPI.fetchSuppliers();
  const select = DOM.itemSupplier();
  if (!select) return;

  if (!suppliers || suppliers.length === 0) {
    select.innerHTML = '<option value="">No suppliers available</option>';
    return;
  }

  select.innerHTML = `
    <option value="">Select Supplier</option>
    ${suppliers
      .map(
        (s) => `
        <option value="${s.id}" ${selectedId === s.id ? "selected" : ""}>${escapeHtml(s.name)}</option>
      `,
      )
      .join("")}
  `;
}

export async function handleFormSubmit(e) {
  e.preventDefault();

  const data = {
    name: DOM.itemName()?.value?.trim() || "",
    category: DOM.itemCategory()?.value || "",
    sub_category: DOM.itemSubCategory()?.value?.trim() || null,
    unit: DOM.itemUnit()?.value || "",
    current_stock: parseFloat(DOM.itemStock()?.value) || 0,
    min_stock_threshold: parseFloat(DOM.reorderLevel()?.value) || 5,
    cost_price: DOM.itemCost()?.value ? parseFloat(DOM.itemCost().value) : null,
    selling_price: DOM.itemSellingPrice()?.value
      ? parseFloat(DOM.itemSellingPrice().value)
      : null,
    sku: DOM.itemSku()?.value?.trim() || null,
    barcode: DOM.itemBarcode()?.value?.trim() || null,
    location: DOM.itemLocation()?.value?.trim() || null,
    supplier_id: DOM.itemSupplier()?.value || null,
    description: DOM.itemDescription()?.value?.trim() || null,
    status: "active",
  };

  if (!data.name) {
    showToast("Please enter item name", "error");
    DOM.itemName()?.focus();
    return;
  }
  if (!data.category) {
    showToast("Please select a category", "error");
    DOM.itemCategory()?.focus();
    return;
  }
  if (!data.unit) {
    showToast("Please select a unit", "error");
    DOM.itemUnit()?.focus();
    return;
  }

  const editId = DOM.editId()?.value || "";
  const submitBtn = DOM.submitBtn();
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = editId ? "Updating..." : "Creating...";
  }

  try {
    const result = editId
      ? await InventoryAPI.updateItem(editId, data)
      : await InventoryAPI.createItem(data);

    if (result) {
      showToast(editId ? "✅ Item updated!" : "✅ Item created!", "success");
      closeModal();
      await loadInventoryItems();
      if (state.selectedItemId) await selectItem(state.selectedItemId);
    }
  } catch (error) {
    showToast("❌ " + (error.message || "Failed to save item"), "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = editId ? "Update Item" : "Create Item";
    }
  }
}
