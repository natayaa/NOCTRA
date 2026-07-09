// ============================================================
// projects/renderers/detail/tasks.js - Tasks Tab
// ============================================================

import { DOM } from "../../dom.js";
import { escapeHtml } from "../../formatters.js";

export function renderTasks(projectData) {
  const container = DOM.drawerTasks();
  if (!container) return;

  const tasks = projectData?.tasks || [];
  if (!tasks || tasks.length === 0) {
    container.innerHTML =
      '<p style="color:var(--text-muted);">No tasks created yet.</p>';
    return;
  }

  container.innerHTML = tasks
    .map(
      (task) => `
        <div class="material-list-item" style="justify-content:space-between;">
            <div>
                <strong>${escapeHtml(task.title)}</strong>
                <span style="font-size:0.8rem;color:var(--text-muted);"> - ${escapeHtml(task.assigned_to || "Unassigned")}</span>
            </div>
            <div style="display:flex;align-items:center;gap:0.5rem;">
                <span class="status-badge ${task.status === "completed" ? "completed" : "in_progress"}">${task.status || "pending"}</span>
                ${
                  task.status !== "completed"
                    ? `
                    <button onclick="window.handleCompleteTask('${task.id}')" class="btn-primary btn-sm" style="padding:2px 8px;font-size:0.7rem;">
                        <i class="ph ph-check"></i>
                    </button>
                `
                    : ""
                }
            </div>
        </div>
    `,
    )
    .join("");
}
