// projects/handlers/events.js (FIXED & IMPROVED - FULL)

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { loadProjects } from "../index.js";
import { closeDrawer, switchTab } from "../drawer.js";
import {
  openCreateProjectModal,
  openEditProjectModal,
  closeProjectModal,
  handleProjectFormSubmit,
} from "./modals.js";
import {
  openProgressPopup,
  closeProgressPopup,
  handleSaveProgress,
} from "./progress.js";
import {
  openTaskModal,
  closeTaskModal,
  handleAddTask,
  handleCompleteTask,
} from "./tasks.js";
import { handleConsumeMaterial, handleDeleteMaterial } from "./materials.js";
import { handleAddLabor, handleDeleteLabor } from "./labor.js";
import { initKeypad } from "./keypad.js";
import { autoFillLaborRate } from "./dropdowns.js";

let eventsBound = false;
export function bindEvents() {
  if (eventsBound) return;
  eventsBound = true;
  // ============================================================
  // 1. PAGINATION
  // ============================================================
  DOM.prevPageBtn()?.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage--;
      loadProjects();
    }
  });
  DOM.nextPageBtn()?.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      state.currentPage++;
      loadProjects();
    }
  });

  // ============================================================
  // 2. SEARCH & FILTER
  // ============================================================
  let searchTimeout;
  DOM.projectSearch()?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.currentPage = 1;
      loadProjects();
    }, 300);
  });

  DOM.statusFilter()?.addEventListener("change", (e) => {
    state.filters.status = e.target.value;
    state.currentPage = 1;
    loadProjects();
  });
  DOM.priorityFilter()?.addEventListener("change", (e) => {
    state.filters.priority = e.target.value;
    state.currentPage = 1;
    loadProjects();
  });

  // ============================================================
  // 3. BUTTONS
  // ============================================================
  DOM.createProjectBtn()?.addEventListener("click", openCreateProjectModal);

  // ============================================================
  // 4. PROJECT MODAL
  // ============================================================
  DOM.closeModal()?.addEventListener("click", closeProjectModal);
  DOM.cancelModalBtn()?.addEventListener("click", closeProjectModal);
  DOM.projectModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.projectModal()) closeProjectModal();
  });
  DOM.projectForm()?.addEventListener("submit", handleProjectFormSubmit);

  // ============================================================
  // 5. DRAWER
  // ============================================================
  DOM.closeDrawer()?.addEventListener("click", closeDrawer);
  DOM.drawerBackdrop()?.addEventListener("click", closeDrawer);

  // ============================================================
  // 6. PROGRESS POPUP
  // ============================================================
  DOM.closeProgressPopup()?.addEventListener("click", closeProgressPopup);
  DOM.cancelProgressBtn()?.addEventListener("click", closeProgressPopup);
  DOM.progressPopup()?.addEventListener("click", (e) => {
    if (e.target === DOM.progressPopup()) closeProgressPopup();
  });
  DOM.saveProgressBtn()?.addEventListener("click", handleSaveProgress);

  // ============================================================
  // 7. PROGRESS SLIDER
  // ============================================================
  DOM.progressPopupSlider()?.addEventListener("input", (e) => {
    const val = e.target.value;
    const valueEl = DOM.progressPopupValue();
    const checkbox = DOM.markCompleteCheckbox();
    const milestones = DOM.progressPopupMilestones();
    if (valueEl) valueEl.textContent = val;
    if (checkbox) checkbox.checked = parseInt(val) >= 100;
    if (milestones) {
      const items = milestones.querySelectorAll(".milestone-item");
      const progress = parseInt(val);
      const thresholds = [25, 50, 75, 100];
      items.forEach((item, index) => {
        const cb = item.querySelector(".checkbox");
        const label = item.querySelector(".label");
        if (cb) cb.checked = progress >= thresholds[index];
        if (label)
          label.classList.toggle("done", progress >= thresholds[index]);
      });
    }
  });

  // ============================================================
  // 8. TASK MODAL
  // ============================================================
  DOM.addTaskBtn()?.addEventListener("click", () => {
    if (state.currentProjectId) openTaskModal(state.currentProjectId);
  });
  DOM.closeTaskModal()?.addEventListener("click", closeTaskModal);
  DOM.cancelTaskBtn()?.addEventListener("click", closeTaskModal);
  DOM.taskModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.taskModal()) closeTaskModal();
  });
  DOM.taskForm()?.addEventListener("submit", handleAddTask);

  // ============================================================
  // 9. MATERIAL & LABOR
  // ============================================================
  DOM.consumeMaterialBtn()?.addEventListener("click", handleConsumeMaterial);
  DOM.addLaborBtn()?.addEventListener("click", handleAddLabor);
  DOM.laborTypeSelect()?.addEventListener("change", autoFillLaborRate);

  // ============================================================
  // 10. TABS
  // ============================================================
  const btns = DOM.tabBtns();
  if (btns && btns.length) {
    btns.forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });
  }

  // ============================================================
  // 11. KEYPADS (MERGED)
  // ============================================================
  initKeypad("laborHours", "hoursKeypad", "0", 2);
  initKeypad("materialQty", "materialQtyKeypad", "0", 2);

  console.log("✅ All events bound successfully!");
}

export function bindKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    // Escape - close modals
    if (e.key === "Escape") {
      const modals = [
        { el: DOM.progressPopup(), close: closeProgressPopup },
        { el: DOM.projectModal(), close: closeProjectModal },
        { el: DOM.taskModal(), close: closeTaskModal },
        { el: DOM.drawer(), close: closeDrawer },
      ];

      for (const modal of modals) {
        if (modal.el?.classList.contains("active")) {
          e.preventDefault();
          modal.close();
          return;
        }
      }
    }

    // Ctrl+N - New Project
    if (e.ctrlKey && e.key === "n") {
      e.preventDefault();
      openCreateProjectModal();
    }

    // Ctrl+F - Focus search
    if (e.ctrlKey && e.key === "f") {
      e.preventDefault();
      DOM.projectSearch()?.focus();
    }

    // Ctrl+R - Refresh (without page reload)
    if (e.ctrlKey && e.key === "r" && !e.shiftKey) {
      e.preventDefault();
      loadProjects();
    }
  });

  console.log("✅ Keyboard shortcuts bound");
}

// ✅ Export functions for window
export const closeProgressPopupGlobal = closeProgressPopup;
export const closeProjectModalGlobal = closeProjectModal;
export const closeTaskModalGlobal = closeTaskModal;
