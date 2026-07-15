// projects/handlers/tasks.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { ProjectAPI } from "../api.js";
import { showToast } from "../toast.js";
import { state } from "../config.js";
import { loadProjects } from "../index.js";
import { renderTasks } from "../renderers/detail/tasks.js";
import { getProjectById, isProjectComplete } from "../utils.js";

export function openTaskModal(projectId) {
  const projectIdEl = DOM.taskProjectId();
  const form = DOM.taskForm();
  const modal = DOM.taskModal();

  if (projectIdEl) projectIdEl.value = projectId;
  if (form) {
    form.reset();
    // Set default priority
    const priorityEl = DOM.taskPriority();
    if (priorityEl) priorityEl.value = "medium";
  }
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
    setTimeout(() => DOM.taskTitle()?.focus(), 100);
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

  const project = getProjectById(projectId);
  if (isProjectComplete(project)) {
    showToast("⚠️ Cannot add task: Project is completed.", "error");
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
    DOM.taskTitle()?.focus();
    return;
  }

  // Validasi due date
  if (data.due_date) {
    const dueDate = new Date(data.due_date);
    if (dueDate < new Date()) {
      if (!confirm("⚠️ Due date is in the past. Continue anyway?")) {
        return;
      }
    }
  }

  const submitBtn = DOM.taskForm()?.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Adding...";
  }

  try {
    const result = await ProjectAPI.addTask(projectId, data);
    if (result) {
      showToast("✅ Task added successfully", "success");
      closeTaskModal();

      if (state.currentProjectId) {
        const projectData = await ProjectAPI.fetchDetail(
          state.currentProjectId,
        );
        if (projectData) {
          state._currentProjectData = projectData;
          renderTasks(projectData);
        }
      }
      await loadProjects();
    } else {
      showToast("❌ Failed to add task", "error");
    }
  } catch (error) {
    console.error("Add task error:", error);
    showToast("❌ " + (error.message || "Failed to add task"), "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Add Task";
    }
  }
}

export async function handleCompleteTask(taskId) {
  if (!taskId) {
    showToast("Task ID missing", "error");
    return;
  }

  if (!confirm("Mark this task as completed?")) return;

  try {
    const result = await ProjectAPI.completeTask(taskId);
    if (result) {
      showToast("✅ Task completed! 🎉", "success");

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
    } else {
      showToast("❌ Failed to complete task", "error");
    }
  } catch (error) {
    console.error("Complete task error:", error);
    showToast("❌ " + (error.message || "Failed to complete task"), "error");
  }
}

export async function handleDeleteTask(taskId) {
  if (!taskId) {
    showToast("Task ID missing", "error");
    return;
  }

  if (!confirm("Delete this task?")) return;

  try {
    // Note: May need to implement deleteTask endpoint
    const result = await ProjectAPI.deleteTask(taskId);
    if (result) {
      showToast("🗑️ Task deleted", "success");

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
    } else {
      showToast("❌ Failed to delete task", "error");
    }
  } catch (error) {
    console.error("Delete task error:", error);
    showToast("❌ " + (error.message || "Failed to delete task"), "error");
  }
}
