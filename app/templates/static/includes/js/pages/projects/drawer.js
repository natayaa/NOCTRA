// projects/drawer.js (FIXED - switchTab function)

import { DOM, drawerBackdrop } from "./dom.js";
import { state } from "./config.js";
import { ProjectAPI } from "./api.js";
import { showToast } from "./toast.js";
import { renderOverview } from "./renderers/detail/overview.js";
import { renderMaterials } from "./renderers/detail/materials.js";
import { renderLabor } from "./renderers/detail/labor.js";
import { renderTimeline } from "./renderers/detail/timeline.js";
import { renderTasks } from "./renderers/detail/tasks.js";
import { loadMaterialItems, loadLaborTypes } from "./handlers/dropdowns.js";

let isLoading = false;

// ============================================================
// REFRESH TERPUSAT (agar handler tidak usah render ulang manual)
// ============================================================
export async function refreshCurrentProjectContext() {
  if (state.currentProjectId && isDrawerOpen()) {
    const projectData = await ProjectAPI.fetchDetail(state.currentProjectId);
    if (projectData) {
      state._currentProjectData = projectData;
      state._currentProject = projectData.project || projectData;

      // Render ulang semua tab
      renderOverview(projectData);
      renderTimeline(projectData);
      renderMaterials(projectData);
      renderLabor(projectData);
      renderTasks(projectData);
      return true;
    }
  }
  return false;
}

export function switchTab(tabName) {
  const btns = DOM.tabBtns();
  const panels = DOM.tabPanels; // ✅ BUKAN function, langsung object

  if (btns) {
    btns.forEach((btn) => {
      const isActive = btn.dataset.tab === tabName;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", isActive);
    });
  }

  // ✅ panels adalah object, bukan function
  if (panels && typeof panels === "object") {
    Object.keys(panels).forEach((key) => {
      const panel = panels[key](); // ✅ panels[key] adalah function
      if (panel) {
        panel.classList.toggle("active", key === tabName);
      }
    });
  }
}

export async function openProjectDrawer(projectId, force = false) {
  if (isLoading) return;

  if (!projectId) {
    showToast("No project selected", "error");
    return;
  }

  // Jika drawer sudah terbuka dengan project yang sama, dan tidak dipaksa refresh, skip
  if (
    !force &&
    state.currentProjectId === projectId &&
    DOM.drawer()?.classList.contains("active")
  ) {
    console.log("📌 Drawer already open for this project (cached)");
    return;
  }

  isLoading = true;
  state.currentProjectId = projectId;

  const drawer = DOM.drawer();
  const backdrop = DOM.drawerBackdrop();
  if (drawer) drawer.classList.add("active");
  if (backdrop) backdrop.classList.add("active");
  document.body.style.overflow = "hidden";

  try {
    const projectData = await ProjectAPI.fetchDetail(projectId);
    if (!projectData) {
      showToast("Failed to load project details", "error");
      closeDrawer();
      return;
    }

    state._currentProjectData = projectData;
    state._currentProject = projectData.project || projectData;

    switchTab("overview");
    renderOverview(projectData);
    renderTimeline(projectData);
    renderMaterials(projectData);
    renderLabor(projectData);
    renderTasks(projectData);

    await loadMaterialItems();
    await loadLaborTypes();

    const isComplete =
      projectData.status === "completed" || projectData.progress >= 100;
    toggleDrawerActions(!isComplete);

    console.log("✅ Project drawer loaded:", projectId);
  } catch (error) {
    console.error("Failed to open project drawer:", error);
    showToast("Failed to load project details: " + error.message, "error");
    closeDrawer();
  } finally {
    isLoading = false;
  }
}

export function closeDrawer() {
  const drawer = DOM.drawer();
  const backdrop = DOM.drawerBackdrop();
  if (drawer) drawer.classList.remove("active");
  if (backdrop) backdrop.classList.remove("active");
  document.body.style.overflow = "";
  state.currentProjectId = null;
  state._currentProjectData = null;
  state._currentProject = null;
  isLoading = false;
}

export function isDrawerOpen() {
  const drawer = DOM.drawer();
  return drawer ? drawer.classList.contains("active") : false;
}

export function getCurrentProject() {
  return state._currentProject || null;
}

export function getCurrentProjectData() {
  return state._currentProjectData || null;
}

export async function refreshDrawer() {
  if (state.currentProjectId && isDrawerOpen()) {
    await openProjectDrawer(state.currentProjectId);
  }
}

function toggleDrawerActions(enabled) {
  const drawer = DOM.drawer();
  if (!drawer) return;
  if (enabled) {
    drawer.classList.remove("drawer-actions-disabled");
  } else {
    drawer.classList.add("drawer-actions-disabled");
    showToast(
      "🔒 This project is completed. Actions are disabled.",
      "info",
      4000,
    );
  }
}
