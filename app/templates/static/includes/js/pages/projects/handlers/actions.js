// projects/handlers/actions.js (FIXED & IMPROVED)

import { ProjectAPI } from "../api.js";
import { showToast } from "../toast.js";
import { state } from "../config.js";
import { loadProjects } from "../index.js";
import { closeDrawer } from "../drawer.js";
import { DOM } from "../dom.js";
import { getProjectById, isProjectComplete } from "../utils.js";

export async function confirmDeleteProject(projectId) {
  const project = getProjectById(projectId);
  if (isProjectComplete(project)) {
    showToast("⚠️ Cannot modify a completed project.", "error");
    return;
  }

  if (
    !confirm(
      `Delete project "${project.name}"?\n\nThis action cannot be undone.`,
    )
  ) {
    return;
  }

  await handleDeleteProject(projectId);
}

export async function handleDeleteProject(projectId) {
  const project = getProjectById(projectId);
  if (isProjectComplete(project)) {
    showToast("⚠️ Cannot modify a completed project.", "error");
    return;
  }
  try {
    const result = await ProjectAPI.delete(projectId);
    if (result) {
      showToast("✅ Project deleted successfully", "success");
      await loadProjects();

      // Close drawer if open
      const drawer = DOM.drawer();
      if (drawer && drawer.classList.contains("active")) {
        closeDrawer();
      }
    } else {
      showToast("❌ Failed to delete project", "error");
    }
  } catch (error) {
    console.error("Delete project error:", error);
    showToast("❌ " + (error.message || "Failed to delete project"), "error");
  }
}

export async function handleArchiveProject(projectId) {
  const project = getProjectById(projectId);
  if (isProjectComplete(project)) {
    showToast("⚠️ Cannot modify a completed project.", "error");
    return;
  }

  try {
    const result = await ProjectAPI.archive(projectId);
    if (result) {
      showToast("📦 Project archived", "success");
      await loadProjects();
    } else {
      showToast("❌ Failed to archive project", "error");
    }
  } catch (error) {
    console.error("Archive project error:", error);
    showToast("❌ " + (error.message || "Failed to archive project"), "error");
  }
}

export async function handleUnarchiveProject(projectId) {
  const project = getProjectById(projectId);
  if (isProjectComplete(project)) {
    showToast("⚠️ Cannot modify a completed project.", "error");
    return;
  }
  try {
    const result = await ProjectAPI.unarchive(projectId);
    if (result) {
      showToast("📦 Project unarchived", "success");
      await loadProjects();
    } else {
      showToast("❌ Failed to unarchive project", "error");
    }
  } catch (error) {
    console.error("Unarchive project error:", error);
    showToast(
      "❌ " + (error.message || "Failed to unarchive project"),
      "error",
    );
  }
}

export async function handleDuplicateProject(projectId) {
  const project = getProjectById(projectId);
  if (isProjectComplete(project)) {
    showToast("⚠️ Cannot modify a completed project.", "error");
    return;
  }

  if (!confirm(`Duplicate project "${project.name}"?`)) return;

  try {
    // Create copy with new name
    const copyData = {
      name: `${project.name} (Copy)`,
      customer_name: project.customer_name,
      customer_phone: project.customer_phone,
      customer_email: project.customer_email,
      vehicle_brand: project.vehicle_brand,
      vehicle_model: project.vehicle_model,
      vehicle_year: project.vehicle_year,
      vehicle_license_plate: project.vehicle_license_plate,
      estimated_cost: project.estimated_cost,
      estimated_revenue: project.estimated_revenue,
      priority: project.priority || "medium",
      notes: `Duplicated from project ${project.name}`,
    };

    const result = await ProjectAPI.create(copyData);
    if (result) {
      showToast("✅ Project duplicated successfully", "success");
      await loadProjects();
    } else {
      showToast("❌ Failed to duplicate project", "error");
    }
  } catch (error) {
    console.error("Duplicate project error:", error);
    showToast(
      "❌ " + (error.message || "Failed to duplicate project"),
      "error",
    );
  }
}
