// projects/index.js (FIXED & IMPROVED)

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
import { openProjectDrawer, closeDrawer, refreshDrawer } from "./drawer.js";
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
import { initHoursKeypad } from "./handlers/keypad.js";
import { initMaterialQtyKeypad } from "./handlers/materialKeypad.js";

// ============================================================
// MAIN LOAD FUNCTION
// ============================================================

export async function loadProjects() {
  showLoadingState();

  try {
    const data = await ProjectAPI.fetchProjects(
      state.currentPage,
      state.filters,
    );

    if (!data) {
      renderErrorState("Failed to load projects. Please try again.");
      return;
    }

    let projects = [],
      totalPages = 1,
      totalItems = 0;

    if (data.items && Array.isArray(data.items)) {
      projects = data.items;
      totalItems = data.total || data.total_items || projects.length;
      totalPages =
        data.total_pages ||
        Math.ceil(totalItems / CONFIG.PROJECTS_PER_PAGE) ||
        1;
    } else if (Array.isArray(data)) {
      projects = data;
      totalItems = projects.length;
      totalPages = Math.ceil(totalItems / CONFIG.PROJECTS_PER_PAGE) || 1;
    } else if (data.data && Array.isArray(data.data)) {
      projects = data.data;
      totalItems = data.total || data.total_items || projects.length;
      totalPages =
        data.total_pages ||
        Math.ceil(totalItems / CONFIG.PROJECTS_PER_PAGE) ||
        1;
    }

    state.projects = projects;
    state.totalPages = Math.max(1, totalPages);
    state.totalItems = totalItems;

    renderProjects(state.projects);
    updatePagination(state.currentPage, state.totalPages, state.totalItems);

    const stats = await ProjectAPI.fetchStatistics();
    if (stats) updateDashboard(stats);

    console.log(`✅ Loaded ${totalItems} projects`);
  } catch (error) {
    console.error("Failed to load projects:", error);
    renderErrorState(error.message || "Failed to load projects");
  }
}

function renderErrorState(message) {
  const grid = DOM.projectCardGrid();
  if (!grid) return;
  grid.innerHTML = `
    <div style="grid-column:1/-1; text-align:center; padding:3rem 0; color: var(--text-muted);">
      <i class="ph ph-warning" style="font-size:2rem; display:block; margin-bottom:1rem;"></i>
      <p>${message}</p>
      <button class="btn-primary" onclick="window.loadProjects()">
        <i class="ph ph-arrow-clockwise"></i> Retry
      </button>
    </div>
  `;
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
    initHoursKeypad();
    initMaterialQtyKeypad();
    console.log("✅ Projects page initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

export const initProjectsPage = initProjects;

// ============================================================
// REFRESH FUNCTIONS
// ============================================================

export async function refreshProjects() {
  await loadProjects();
  if (DOM.drawer()?.classList.contains("active")) {
    await refreshDrawer();
  }
}

// ============================================================
// EXPOSE TO GLOBAL
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
window.refreshProjects = refreshProjects;

console.log("📋 Projects page module ready");
