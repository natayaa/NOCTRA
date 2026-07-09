// ============================================================
// projects/drawer.js - Drawer Functions
// ============================================================

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

export function switchTab(tabName) {
  const btns = DOM.tabBtns();
  const panels = DOM.tabPanels;

  if (btns) {
    btns.forEach((btn) => {
      const isActive = btn.dataset.tab === tabName;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", isActive);
    });
  }
  if (panels) {
    Object.keys(panels).forEach((key) => {
      const panel = panels[key]();
      if (panel) panel.classList.toggle("active", key === tabName);
    });
  }
}

export async function openProjectDrawer(projectId) {
  state.currentProjectId = projectId;
  const projectData = await ProjectAPI.fetchDetail(projectId);
  if (!projectData) return;

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

  const drawer = DOM.drawer();
  const backdrop = DOM.drawerBackdrop();
  if (drawer) drawer.classList.add("active");
  if (backdrop) backdrop.classList.add("active");
  document.body.style.overflow = "hidden";
}

export function closeDrawer() {
  const drawer = DOM.drawer();
  const backdrop = DOM.drawerBackdrop();
  if (drawer) drawer.classList.remove("active");
  if (backdrop) backdrop.classList.remove("active");
  document.body.style.overflow = "";
  state.currentProjectId = null;
  state._currentProjectData = null;
}
