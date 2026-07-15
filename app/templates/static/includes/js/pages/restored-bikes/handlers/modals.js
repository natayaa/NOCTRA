// ============================================================
// restored-bikes/handlers/modals.js - Modal Handlers
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { RestoredBikeAPI } from "../api.js";
import { showToast } from "../../shared/toast.js";
import { loadRestoredBikes, refreshDrawer } from "../index.js";

export function openAddModal() {
  const modal = DOM.restoredModal();
  const title = DOM.modalTitle();
  const subtitle = DOM.modalSubtitle();
  const form = DOM.restoredForm();
  const editId = DOM.editId();
  const submitBtn = DOM.submitBtn();

  if (title) title.textContent = "Add Restored Bike";
  if (subtitle)
    subtitle.textContent = "Register a completed restoration project";
  if (form) form.reset();
  if (editId) editId.value = "";
  if (submitBtn) submitBtn.textContent = "Save";
  if (modal) modal.classList.add("active");

  // Set default status
  const statusEl = DOM.restorationStatus();
  if (statusEl) statusEl.value = "completed";

  setTimeout(() => DOM.bikeBrand()?.focus(), 100);
}

export async function openEditModal(id) {
  const bike = await RestoredBikeAPI.get(id);
  if (!bike) {
    showToast("Failed to load bike data", "error");
    return;
  }

  const modal = DOM.restoredModal();
  const title = DOM.modalTitle();
  const subtitle = DOM.modalSubtitle();
  const editId = DOM.editId();
  const submitBtn = DOM.submitBtn();

  if (title) title.textContent = "Edit Restored Bike";
  if (subtitle) subtitle.textContent = `Editing ${bike.brand} ${bike.model}`;
  if (editId) editId.value = id;
  if (submitBtn) submitBtn.textContent = "Update";

  const fields = {
    bikeBrand: bike.brand,
    bikeModel: bike.model,
    bikeYear: bike.year,
    licensePlate: bike.license_plate,
    customerName: bike.customer_name,
    purchasePrice: bike.purchase_price,
    purchaseSource: bike.purchase_source,
    initialCondition: bike.initial_condition,
    restorationCost: bike.restoration_cost,
    restorationDuration: bike.restoration_duration,
    technicianName: bike.technician_name,
    restorationStatus: bike.status || "completed",
    restorationNotes: bike.restoration_notes,
  };

  Object.keys(fields).forEach((key) => {
    const el = DOM[key]();
    if (el)
      el.value =
        fields[key] !== undefined && fields[key] !== null ? fields[key] : "";
  });

  if (modal) modal.classList.add("active");
  setTimeout(() => DOM.bikeBrand()?.focus(), 100);
}

export function closeModal() {
  const modal = DOM.restoredModal();
  if (modal) modal.classList.remove("active");
  const form = DOM.restoredForm();
  if (form) form.reset();
  const editId = DOM.editId();
  if (editId) editId.value = "";
}

export async function handleFormSubmit(e) {
  e.preventDefault();

  const editId = DOM.editId()?.value || "";
  const isEdit = !!editId;

  const data = {
    brand: DOM.bikeBrand()?.value?.trim(),
    model: DOM.bikeModel()?.value?.trim(),
    year: DOM.bikeYear()?.value ? parseInt(DOM.bikeYear().value) : null,
    license_plate: DOM.licensePlate()?.value?.trim() || null,
    customer_name: DOM.customerName()?.value?.trim() || null,
    purchase_price: DOM.purchasePrice()?.value
      ? parseFloat(DOM.purchasePrice().value)
      : null,
    purchase_source: DOM.purchaseSource()?.value?.trim() || null,
    initial_condition: DOM.initialCondition()?.value || null,
    restoration_cost: DOM.restorationCost()?.value
      ? parseFloat(DOM.restorationCost().value)
      : null,
    restoration_duration: DOM.restorationDuration()?.value
      ? parseInt(DOM.restorationDuration().value)
      : null,
    technician_name: DOM.technicianName()?.value?.trim() || null,
    status: DOM.restorationStatus()?.value || "completed",
    restoration_notes: DOM.restorationNotes()?.value?.trim() || null,
  };

  // Validasi
  if (!data.brand || data.brand.length < 2) {
    showToast("Brand is required (min 2 characters)", "warning");
    DOM.bikeBrand()?.focus();
    return;
  }
  if (!data.model || data.model.length < 2) {
    showToast("Model is required (min 2 characters)", "warning");
    DOM.bikeModel()?.focus();
    return;
  }

  const submitBtn = DOM.submitBtn();
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = isEdit ? "Updating..." : "Saving...";
  }

  try {
    let result;
    if (isEdit) {
      result = await RestoredBikeAPI.update(editId, data);
    } else {
      result = await RestoredBikeAPI.create(data);
    }

    if (result) {
      showToast(isEdit ? "✅ Bike updated!" : "✅ Bike added!", "success");
      closeModal();
      await loadRestoredBikes();
      if (state.currentBikeId) {
        await refreshDrawer();
      }
    }
  } catch (error) {
    showToast("❌ " + (error.message || "Failed to save"), "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = isEdit ? "Update" : "Save";
    }
  }
}
