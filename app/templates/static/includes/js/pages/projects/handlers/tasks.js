// ============================================================
// projects/handlers/tasks.js - Task Management
// ============================================================

import { DOM } from "../dom.js";
import { ProjectAPI } from "../api.js";
import { showToast } from "../toast.js";
import { state } from "../config.js";
import { loadProjects } from "../index.js";
import { renderTasks } from "../renderers/detail/tasks.js";

export function openTaskModal(projectId) {
  const projectIdEl = DOM.taskProjectId();
  const form = DOM.taskForm();
  const modal = DOM.taskModal();

  if (projectIdEl) projectIdEl.value = projectId;
  if (form) form.reset();
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

export function closeTaskModal() {
  const modal = DOM.taskModal();
  if (modal) modal.classList.remove("active");
  document.body.style.overflow = "";
}

export async function handleAddTask(e) {
  e.preventDefault();
  const projectId = DOM.taskProjectId?.value || "";
  if (!projectId) {
    showToast("Project ID missing", "error");
    return;
  }

  const data = {
    title: DOM.taskTitle?.value?.trim() || "",
    description: DOM.taskDescription?.value?.trim() || "",
    assigned_to: DOM.taskAssignee?.value?.trim() || "",
    priority: DOM.taskPriority?.value || "medium",
    due_date: DOM.taskDueDate?.value || null,
  };
  if (!data.title) {
    showToast("Task title is required", "error");
    return;
  }

  const result = await ProjectAPI.addTask(projectId, data);
  if (result) {
    showToast("Task added successfully", "success");
    closeTaskModal();
    if (state.currentProjectId) {
      const projectData = await ProjectAPI.fetchDetail(state.currentProjectId);
      if (projectData) {
        state._currentProjectData = projectData;
        renderTasks(projectData);
      }
    }
    await loadProjects();
  }
}

export async function handleCompleteTask(taskId) {
  if (confirm("Mark this task as completed?")) {
    const result = await ProjectAPI.completeTask(taskId);
    if (result) {
      showToast("Task completed! 🎉", "success");
      if (state.currentProjectId) {
        const projectData = await ProjectAPI.fetchDetail(
          state.currentProjectId,
        );
        if (projectData) {
          state._currentProjectData = projectData;
          renderTasks(projectData);
        }
        await loadProjects();
      }
    }
  }
}
