// ============================================================
// projects/handlers/labor.js - Labor Management
// ============================================================

import { DOM } from "../dom.js";
import { ProjectAPI } from "../api.js";
import { showToast } from "../toast.js";
import { Formatter } from "../formatters.js";
import { state } from "../config.js";
import { loadProjects } from "../index.js";
import { renderLabor } from "../renderers/detail/labor.js";
import { autoFillLaborRate } from "./dropdowns.js";

export function updateLaborSummary(laborItems) {
  const container = document.getElementById("laborSummaryContainer");
  const totalEl = document.getElementById("totalLaborCost");

  if (!laborItems || laborItems.length === 0) {
    if (container) container.style.display = "none";
    return;
  }

  let total = 0;
  laborItems.forEach((item) => {
    const hours = item.hours || 0;
    const rate = item.rate_per_hour || item.rate || 0;
    total += hours * rate;
  });

  if (container) container.style.display = "block";
  if (totalEl) totalEl.textContent = Formatter.currency(total);
}

export async function handleAddLabor() {
  const projectId = state.currentProjectId;
  if (!projectId) {
    showToast("No project selected", "error");
    return;
  }

  const typeSelect = DOM.laborTypeSelect();
  const hoursEl = DOM.laborHours();
  const rateEl = DOM.laborRate();

  const laborType = typeSelect ? typeSelect.value : "";
  const hours = parseFloat(hoursEl ? hoursEl.value : 0);
  let rate = parseFloat(rateEl ? rateEl.value : 0);

  // Validasi
  if (!laborType) {
    showToast("Please select labor type", "error");
    typeSelect?.focus();
    return;
  }
  if (!hours || hours <= 0) {
    showToast("Please enter valid hours (minimum 0.5)", "error");
    hoursEl?.focus();
    return;
  }

  // Jika rate masih 0, coba ambil dari dataset
  if (!rate || rate <= 0) {
    const selected = typeSelect?.options[typeSelect.selectedIndex];
    const rateFromDataset = parseFloat(selected?.dataset?.rate || 0);
    if (rateFromDataset > 0) {
      rate = rateFromDataset;
      if (rateEl) rateEl.value = rate;
    } else {
      showToast(
        "Rate per hour is required. Please select a valid labor type.",
        "error",
      );
      typeSelect?.focus();
      return;
    }
  }

  const totalCost = hours * rate;

  // Konfirmasi dengan format yang lebih baik
  if (
    !confirm(
      `Add ${hours}h of "${laborType}" @ ${Formatter.currency(rate)}/hour\n` +
        `Total: ${Formatter.currency(totalCost)}`,
    )
  ) {
    return;
  }

  const selected = typeSelect?.options[typeSelect.selectedIndex];
  const subCategory = selected?.dataset?.subCategory || "";
  const description = selected?.dataset?.description || "";

  const data = {
    labor_type: laborType,
    hours: hours,
    rate_per_hour: rate,
    technician_name: subCategory || laborType,
    description: description || `Labor: ${laborType} for ${hours} hours`,
  };

  const result = await ProjectAPI.addLabor(projectId, data);
  if (result) {
    showToast(
      `✅ Added: ${hours}h ${laborType} (${Formatter.currency(totalCost)})`,
      "success",
    );

    // Reset form
    if (hoursEl) hoursEl.value = "";
    if (typeSelect) typeSelect.value = "";
    if (rateEl) {
      rateEl.value = "";
      rateEl.placeholder = "Auto-filled";
      rateEl.readOnly = false;
      rateEl.style.borderColor = "";
      rateEl.style.backgroundColor = "";
      // Update hint
      const hint = document.getElementById("laborRateHint");
      if (hint) {
        hint.className = "";
        hint.innerHTML = `<span class="hint-icon">💡</span> Rate will be auto-filled from selected labor type`;
      }
    }

    // Refresh data
    if (state.currentProjectId) {
      const projectData = await ProjectAPI.fetchDetail(state.currentProjectId);
      if (projectData) {
        state._currentProjectData = projectData;
        renderLabor(projectData);
        // Update summary
        const financial = projectData?.financial_summary || {};
        updateLaborSummary(financial.labor_items || []);
      }
    }
    await loadProjects();
  }
}

export async function handleDeleteLabor(laborId) {
  if (!confirm("Are you sure you want to delete this labor entry?")) return;

  const result = await ProjectAPI.deleteLabor(laborId);
  if (result) {
    showToast("Labor entry deleted successfully", "success");
    if (state.currentProjectId) {
      const projectData = await ProjectAPI.fetchDetail(state.currentProjectId);
      if (projectData) {
        state._currentProjectData = projectData;
        renderLabor(projectData);
        const financial = projectData?.financial_summary || {};
        updateLaborSummary(financial.labor_items || []);
      }
    }
    await loadProjects();
  }
}
