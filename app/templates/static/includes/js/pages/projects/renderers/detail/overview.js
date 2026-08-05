// projects/renderers/detail/overview.js (FIXED & IMPROVED)

import { DOM } from "../../dom.js";
import {
  Formatter,
  escapeHtml,
  getStatusBadgeClass,
  getPriorityBadgeClass,
  getStatusLabel,
  getPriorityLabel,
} from "../../formatters.js";

export function renderOverview(projectData) {
  const project = projectData?.project || projectData;
  if (!project) return;

  // ✅ Title
  const title = DOM.drawerTitle();
  const subtitle = DOM.drawerSubtitle();
  if (title) title.textContent = project.name || "Project Details";
  if (subtitle) {
    subtitle.textContent = `ID: ${project.id?.substring(0, 8) || "N/A"}`;
  }

  // ✅ Customer & Vehicle fields
  const fields = {
    drawerCustomer: project.customer_name,
    drawerPhone: project.customer_phone,
    drawerEmail: project.customer_email,
    drawerBrand: project.vehicle_brand,
    drawerModel: project.vehicle_model,
    drawerYear: project.vehicle_year,
    drawerPlate: project.vehicle_license_plate,
  };

  Object.keys(fields).forEach((key) => {
    const el = DOM[key]();
    if (el) {
      const value = fields[key];
      el.textContent =
        value !== undefined && value !== null && value !== "" ? value : "-";
    }
  });

  // ✅ Status & Priority
  const statusEl = DOM.drawerStatus();
  const priorityEl = DOM.drawerPriority();
  if (statusEl) {
    statusEl.innerHTML = `<span class="status-badge ${getStatusBadgeClass(project.status)}">${getStatusLabel(project.status)}</span>`;
  }
  if (priorityEl) {
    priorityEl.innerHTML = `<span class="priority-badge ${getPriorityBadgeClass(project.priority)}">${getPriorityLabel(project.priority)}</span>`;
  }

  // ✅ Progress
  const progress = project.progress || 0;
  const fillEl = DOM.drawerProgressFill();
  const textEl = DOM.drawerProgressText();
  const notesEl = DOM.drawerNotes();

  if (fillEl) {
    fillEl.style.width = `${progress}%`;
    fillEl.style.backgroundColor = getProgressColor(progress);
  }
  if (textEl) {
    textEl.textContent = `${progress}%`;
    textEl.style.color = getProgressColor(progress);
  }
  if (notesEl) {
    notesEl.textContent = project.notes || "-";
    notesEl.style.whiteSpace = "pre-wrap";
  }

  // ✅ Budget info (if available)
  const budgetEl = DOM.budgetPercentage();
  const budgetFillEl = DOM.budgetProgressFillFinancial();
  const estimatedCost = project.estimated_cost || 0;
  const actualCost = project.actual_cost || 0;

  if (budgetEl && estimatedCost > 0) {
    const percentage = Math.min((actualCost / estimatedCost) * 100, 100);
    budgetEl.textContent = `${percentage.toFixed(0)}%`;
    budgetEl.style.color =
      percentage > 90 ? "#ef4444" : percentage > 75 ? "#f59e0b" : "#10b981";
  }

  if (budgetFillEl && estimatedCost > 0) {
    const percentage = Math.min((actualCost / estimatedCost) * 100, 100);
    budgetFillEl.style.width = `${percentage}%`;
    budgetFillEl.className = "budget-progress-fill";
    if (percentage > 90) budgetFillEl.classList.add("danger");
    else if (percentage > 75) budgetFillEl.classList.add("warning");
  }

  // ✅ Total cost display
  const totalCostEl = document.getElementById("drawerTotalCostDisplay");
  if (totalCostEl) {
    totalCostEl.textContent = Formatter.currency(actualCost);
  }
}

function getProgressColor(progress) {
  if (progress >= 100) return "#10b981";
  if (progress >= 75) return "#3b82f6";
  if (progress >= 50) return "#f59e0b";
  if (progress >= 25) return "#f97316";
  return "#94a3b8";
}
