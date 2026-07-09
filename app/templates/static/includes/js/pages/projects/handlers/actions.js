// ============================================================
// projects/handlers/actions.js - CRUD Actions
// ============================================================

import { ProjectAPI } from "../api.js";
import { showToast } from "../toast.js";
import { state } from "../config.js";
import { getProjectById } from "../utils.js";
import { loadProjects } from "../index.js";
import { closeDrawer } from "../drawer.js";

export async function confirmDeleteProject(projectId) {
  if (confirm("Are you sure you want to delete this project?")) {
    await handleDeleteProject(projectId);
  }
}

export async function handleDeleteProject(projectId) {
  const result = await ProjectAPI.delete(projectId);
  if (result) {
    showToast("Project deleted successfully", "success");
    await loadProjects();
    if (DOM.drawer?.classList.contains("active")) closeDrawer();
  }
}
