// ============================================================
// dashboard/renderers/projects.js - Recent Projects
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";

export function renderRecentProjects() {
  const container = DOM.recentProjects();
  if (!container) return;

  const projects = state.recentProjects;

  if (!projects || projects.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="loading-placeholder">No recent projects</td></tr>`;
    return;
  }

  container.innerHTML = projects
    .map((p) => {
      const name = p.name || p.project_name || "Unnamed";
      const customer = p.customer_name || p.customer || "-";
      const status = p.status || "draft";
      const progress = p.progress || 0;

      return `
        <tr>
          <td><strong style="color:var(--text-primary);">${escapeHtml(name)}</strong></td>
          <td>${escapeHtml(customer)}</td>
          <td><span class="status-badge-mini ${status}">${statusLabel(status)}</span></td>
          <td>
            <div class="progress-mini">
              <div class="bar"><div class="fill" style="width:${progress}%;"></div></div>
              <span class="text">${progress}%</span>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

function statusLabel(status) {
  const map = {
    draft: "Draft",
    active: "Active",
    in_progress: "In Progress",
    on_hold: "On Hold",
    completed: "Completed",
    cancelled: "Cancelled",
  };
  return map[status] || status;
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

export function updateProjectsFromData(projects) {
  state.recentProjects = projects;
}
