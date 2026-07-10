// projects/handlers/materials.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { ProjectAPI } from "../api.js";
import { showToast } from "../toast.js";
import { state } from "../config.js";
import { loadProjects } from "../index.js";
import { renderMaterials } from "../renderers/detail/materials.js";
import { loadMaterialItems } from "./dropdowns.js";

export async function handleConsumeMaterial() {
  const projectId = state.currentProjectId;
  if (!projectId) {
    showToast("No project selected", "error");
    return;
  }

  const selectEl = DOM.materialSelect();
  const qtyEl = DOM.materialQty();
  const unitEl = DOM.materialUnit();

  if (!selectEl || !qtyEl || !unitEl) {
    showToast("Material form elements not found", "error");
    return;
  }

  const itemId = selectEl.value;
  const quantity = parseFloat(qtyEl.value);
  const unit = unitEl.value;

  // Validasi
  if (!itemId) {
    showToast("Please select a material", "error");
    selectEl.focus();
    return;
  }

  if (!quantity || quantity <= 0) {
    showToast("Please enter a valid quantity", "error");
    qtyEl.focus();
    return;
  }

  // Ambil informasi material dari option
  const selectedOption = selectEl.options[selectEl.selectedIndex];
  const materialName =
    selectedOption?.text?.split("(")[0]?.trim() || "Material";
  const stock = parseFloat(selectedOption?.dataset?.stock) || 0;
  const price = parseFloat(selectedOption?.dataset?.price) || 0;

  // Cek stok
  if (stock > 0 && quantity > stock) {
    showToast(`⚠️ Insufficient stock! Available: ${stock} ${unit}`, "error");
    return;
  }

  // Cek apakah item ada di inventory
  const inventoryItem = await ProjectAPI.checkInventoryItem(itemId);
  if (!inventoryItem) {
    showToast(`⚠️ Material "${materialName}" not found in inventory.`, "error");
    return;
  }

  const totalCost = quantity * price;

  // Konfirmasi dengan detail lengkap
  if (
    !confirm(
      `Consume ${quantity} ${unit} of "${materialName}"?\n\n` +
        `📦 Stock: ${stock} ${unit}\n` +
        `💰 Total Cost: ${formatCurrency(totalCost)}\n` +
        `📋 Project: ${projectId.substring(0, 8)}`,
    )
  ) {
    return;
  }

  // Kirim request
  const result = await ProjectAPI.consumeMaterial({
    project_id: projectId,
    item_id: itemId,
    quantity: quantity,
    note: `Consumed ${quantity} ${unit} of ${materialName} (${formatCurrency(totalCost)})`,
  });

  if (result) {
    showToast(`✅ Consumed: ${quantity} ${unit} ${materialName}`, "success");

    // Reset form
    if (qtyEl) qtyEl.value = "";
    if (selectEl) selectEl.value = "";
    if (unitEl) unitEl.value = "pcs";

    // Refresh
    await loadMaterialItems();
    if (state.currentProjectId) {
      const projectData = await ProjectAPI.fetchDetail(state.currentProjectId);
      if (projectData) {
        state._currentProjectData = projectData;
        renderMaterials(projectData);
      }
    }
    await loadProjects();
  }
}

export async function handleDeleteMaterial(usageId) {
  if (!confirm("Are you sure you want to delete this material usage?")) return;

  const result = await ProjectAPI.deleteMaterialUsage(usageId);
  if (result) {
    showToast("Material usage deleted successfully", "success");
    if (state.currentProjectId) {
      const projectData = await ProjectAPI.fetchDetail(state.currentProjectId);
      if (projectData) {
        state._currentProjectData = projectData;
        renderMaterials(projectData);
      }
    }
    await loadProjects();
  }
}

function formatCurrency(amount) {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount || 0);
}
