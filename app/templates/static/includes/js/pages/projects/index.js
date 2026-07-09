// ============================================================
// projects/index.js - Main Entry Point
// ============================================================

import { state, CONFIG } from "./config.js";
import { DOM } from "./dom.js";
import { ProjectAPI } from "./api.js";
import { showToast } from "./toast.js";
import {
  renderProjects,
  showLoadingState,
  updatePagination,
} from "./renderers/cards.js";
import { updateDashboard } from "./renderers/dashboard.js";
import { bindEvents, bindKeyboardShortcuts } from "./handlers/events.js";
import { loadMaterialItems, loadLaborTypes } from "./handlers/dropdowns.js";
import {
  openCreateProjectModal,
  openEditProjectModal,
  closeProjectModal,
  handleProjectFormSubmit,
} from "./handlers/modals.js";
import { confirmDeleteProject } from "./handlers/actions.js";
import { openProjectDrawer, closeDrawer } from "./drawer.js";
import {
  openProgressPopup,
  closeProgressPopup,
  handleSaveProgress,
} from "./handlers/progress.js";
import {
  openTaskModal,
  closeTaskModal,
  handleAddTask,
  handleCompleteTask,
} from "./handlers/tasks.js";
import {
  handleConsumeMaterial,
  handleDeleteMaterial,
} from "./handlers/materials.js";
import { handleAddLabor, handleDeleteLabor } from "./handlers/labor.js";
// ✅ TAMBAHKAN IMPORT KEYPAD (jika perlu di-export ke window)
import { initHoursKeypad } from "./handlers/keypad.js";

// ============================================================
// MAIN LOAD FUNCTION
// ============================================================

export async function loadProjects() {
  const data = await ProjectAPI.fetchProjects(state.currentPage, state.filters);
  if (!data) {
    const grid = DOM.projectCardGrid();
    if (grid) {
      grid.innerHTML = `
                <div style="grid-column:1/-1; text-align:center; padding:3rem 0; color: var(--text-muted);">
                    <i class="ph ph-warning" style="font-size:2rem; display:block; margin-bottom:1rem;"></i>
                    <p>Failed to load projects. Please try again.</p>
                    <button class="btn-primary" onclick="window.loadProjects()"><i class="ph ph-arrow-clockwise"></i> Retry</button>
                </div>
            `;
    }
    return;
  }

  // ✅ Response: { items, total, page, page_size, total_pages }
  let projects = [],
    totalPages = 1,
    totalItems = 0;

  if (data.items && Array.isArray(data.items)) {
    projects = data.items;
    totalItems = data.total || data.total_items || projects.length;
    totalPages =
      data.total_pages || Math.ceil(totalItems / CONFIG.PROJECTS_PER_PAGE) || 1;
  } else if (Array.isArray(data)) {
    projects = data;
    totalItems = projects.length;
    totalPages = Math.ceil(totalItems / CONFIG.PROJECTS_PER_PAGE) || 1;
  } else if (data.data && Array.isArray(data.data)) {
    projects = data.data;
    totalItems = data.total || data.total_items || projects.length;
    totalPages =
      data.total_pages || Math.ceil(totalItems / CONFIG.PROJECTS_PER_PAGE) || 1;
  }

  state.projects = projects;
  state.totalPages = Math.max(1, totalPages);
  state.totalItems = totalItems;

  renderProjects(state.projects);
  updatePagination(state.currentPage, state.totalPages, state.totalItems);

  const stats = await ProjectAPI.fetchStatistics();
  if (stats) updateDashboard(stats);
}

// ============================================================
// INITIALIZATION
// ============================================================
export async function initProjects() {
  console.log("🚀 Initializing Projects page...");
  try {
    bindEvents();
    bindKeyboardShortcuts();
    await loadProjects();
    await loadMaterialItems();
    await loadLaborTypes("labor");
    // console.log("✅ Projects page initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

// ✅ ALIAS untuk kompatibilitas
export const initProjectsPage = initProjects;

// ============================================================
// EXPOSE TO GLOBAL (untuk inline onclick di HTML)
// ============================================================
window.openCreateProjectModal = openCreateProjectModal;
window.openEditProjectModal = openEditProjectModal;
window.openProjectDrawer = openProjectDrawer;
window.confirmDeleteProject = confirmDeleteProject;
window.openProgressPopup = openProgressPopup;
window.handleCompleteTask = handleCompleteTask;
window.loadProjects = loadProjects;
window.closeDrawer = closeDrawer;
window.closeProjectModal = closeProjectModal;
window.closeProgressPopup = closeProgressPopup;
window.closeTaskModal = closeTaskModal;
window.handleDeleteMaterial = handleDeleteMaterial;
window.handleDeleteLabor = handleDeleteLabor;
window.handleConsumeMaterial = handleConsumeMaterial;
window.handleAddLabor = handleAddLabor;
window.initHoursKeypad = initHoursKeypad;

// console.log("📋 Projects page module ready");
