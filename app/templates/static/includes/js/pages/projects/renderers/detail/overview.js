// ============================================================
// projects/renderers/detail/overview.js - Overview Tab
// ============================================================

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

  const title = DOM.drawerTitle();
  const subtitle = DOM.drawerSubtitle();
  if (title) title.textContent = project.name || "Project Details";
  if (subtitle)
    subtitle.textContent = `ID: ${project.id?.substring(0, 8) || "N/A"}`;

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

  const statusEl = DOM.drawerStatus();
  const priorityEl = DOM.drawerPriority();
  if (statusEl) {
    statusEl.innerHTML = `<span class="status-badge ${getStatusBadgeClass(project.status)}">${getStatusLabel(project.status)}</span>`;
  }
  if (priorityEl) {
    priorityEl.innerHTML = `<span class="priority-badge ${getPriorityBadgeClass(project.priority)}">${getPriorityLabel(project.priority)}</span>`;
  }

  const progress = project.progress || 0;
  const fillEl = DOM.drawerProgressFill();
  const textEl = DOM.drawerProgressText();
  const notesEl = DOM.drawerNotes();
  if (fillEl) fillEl.style.width = `${progress}%`;
  if (textEl) textEl.textContent = `${progress}%`;
  if (notesEl) notesEl.textContent = project.notes || "-";
}
