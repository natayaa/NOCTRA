// projects/renderers/detail/tasks.js (FIXED & IMPROVED)

import { DOM } from "../../dom.js";
import { escapeHtml } from "../../formatters.js";

export function renderTasks(projectData) {
  const container = DOM.drawerTasks();
  if (!container) return;

  const tasks = projectData?.tasks || [];

  // Update count
  const countEl = document.getElementById("taskCount");
  if (countEl) {
    const completed = tasks.filter((t) => t.status === "completed").length;
    countEl.textContent = `${completed}/${tasks.length} done`;
  }

  if (!tasks || tasks.length === 0) {
    container.innerHTML = `
      <div class="task-empty" style="display:flex;flex-direction:column;align-items:center;gap:0.5rem;padding:1.5rem 0;color:var(--text-muted);">
        <i class="ph ph-check-square" style="font-size:1.5rem;opacity:0.4;"></i>
        <p>No tasks created yet.</p>
        <small style="font-size:0.8rem;">Click "Add Task" to create one</small>
      </div>
    `;
    return;
  }

  container.innerHTML = tasks
    .map((task) => {
      const isCompleted = task.status === "completed";
      const priority = task.priority || "medium";
      const priorityColor =
        {
          low: "#94a3b8",
          medium: "#3b82f6",
          high: "#f59e0b",
          urgent: "#ef4444",
        }[priority] || "#94a3b8";

      return `
      <div class="task-item" style="display:flex;justify-content:space-between;align-items:center;padding:0.5rem 0.75rem;
                  background:var(--bg-input);border-radius:var(--radius-sm);margin-bottom:0.25rem;
                  border-left:3px solid ${isCompleted ? "#10b981" : priorityColor};
                  transition:all 0.2s ease;
                  ${isCompleted ? "opacity:0.7;" : ""}">
        <div style="flex:1;min-width:0;">
          <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
            <strong style="color:var(--text-primary);${isCompleted ? "text-decoration:line-through;" : ""}">
              ${escapeHtml(task.title)}
            </strong>
            <span style="font-size:0.65rem;color:var(--text-muted);background:var(--bg-card);padding:0.05rem 0.4rem;border-radius:var(--radius-full);">
              ${escapeHtml(task.priority || "medium")}
            </span>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:0.25rem 0.75rem;font-size:0.7rem;color:var(--text-muted);margin-top:0.1rem;">
            ${task.assigned_to ? `<span>👤 ${escapeHtml(task.assigned_to)}</span>` : ""}
            ${task.due_date ? `<span>📅 ${new Date(task.due_date).toLocaleDateString("id-ID")}</span>` : ""}
            ${task.status ? `<span>📌 ${escapeHtml(task.status)}</span>` : ""}
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:0.5rem;">
          <span class="status-badge ${isCompleted ? "completed" : "in_progress"}">
            ${isCompleted ? "✅ Done" : "⏳ Pending"}
          </span>
          ${
            !isCompleted
              ? `
            <button onclick="window.handleCompleteTask('${task.id}')" class="btn-primary btn-sm" style="padding:2px 8px;font-size:0.7rem;">
              <i class="ph ph-check"></i>
            </button>
          `
              : ""
          }
        </div>
      </div>
    `;
    })
    .join("");
}
