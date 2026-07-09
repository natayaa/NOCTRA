// ============================================================
// projects/handlers/events.js - Event Bindings
// ============================================================

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

// ✅ TAMBAHKAN IMPORT KEYPAD
import { initHoursKeypad } from "./keypad.js";
import { initMaterialQtyKeypad } from "./materialKeypad.js";

export function bindEvents() {
  // Pagination
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

  initHoursKeypad(); // keypad untuk hours

  // Search
  let searchTimeout;
  DOM.projectSearch()?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.currentPage = 1;
      loadProjects();
    }, 300);
  });

  // Filters
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

  // Buttons
  DOM.createProjectBtn()?.addEventListener("click", openCreateProjectModal);

  // Project Modal
  DOM.closeModal()?.addEventListener("click", closeProjectModal);
  DOM.cancelModalBtn()?.addEventListener("click", closeProjectModal);
  DOM.projectModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.projectModal()) closeProjectModal();
  });
  DOM.projectForm()?.addEventListener("submit", handleProjectFormSubmit);

  // Drawer
  DOM.closeDrawer()?.addEventListener("click", closeDrawer);
  DOM.drawerBackdrop()?.addEventListener("click", closeDrawer);

  // Progress Popup
  DOM.closeProgressPopup()?.addEventListener("click", closeProgressPopup);
  DOM.cancelProgressBtn()?.addEventListener("click", closeProgressPopup);
  DOM.progressPopup()?.addEventListener("click", (e) => {
    if (e.target === DOM.progressPopup()) closeProgressPopup();
  });
  DOM.saveProgressBtn()?.addEventListener("click", handleSaveProgress);

  // Progress Slider
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
        const checkboxEl = item.querySelector(".checkbox");
        const labelEl = item.querySelector(".label");
        const threshold = thresholds[index];
        if (checkboxEl) checkboxEl.checked = progress >= threshold;
        if (labelEl) labelEl.classList.toggle("done", progress >= threshold);
      });
    }
  });

  // Task Modal
  DOM.addTaskBtn()?.addEventListener("click", () => {
    if (state.currentProjectId) openTaskModal(state.currentProjectId);
  });
  DOM.closeTaskModal()?.addEventListener("click", closeTaskModal);
  DOM.cancelTaskBtn()?.addEventListener("click", closeTaskModal);
  DOM.taskModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.taskModal()) closeTaskModal();
  });
  DOM.taskForm()?.addEventListener("submit", handleAddTask);

  // Material & Labor
  DOM.consumeMaterialBtn()?.addEventListener("click", handleConsumeMaterial);
  DOM.addLaborBtn()?.addEventListener("click", handleAddLabor);
  setTimeout(() => {
    const laborSelect = DOM.laborTypeSelect();
    if (laborSelect && laborSelect.value) {
      autoFillLaborRate();
    }
  }, 500);

  // Tabs
  const btns = DOM.tabBtns();
  if (btns && btns.length) {
    btns.forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });
  }

  // ✅ INISIALISASI KEYPAD
  initHoursKeypad();
  initMaterialQtyKeypad();
}

export function bindKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (DOM.progressPopup()?.classList.contains("active")) {
        closeProgressPopup();
        e.preventDefault();
      }
      if (DOM.projectModal()?.classList.contains("active")) {
        closeProjectModal();
        e.preventDefault();
      }
      if (DOM.taskModal()?.classList.contains("active")) {
        closeTaskModal();
        e.preventDefault();
      }
      if (DOM.drawer()?.classList.contains("active")) {
        closeDrawer();
        e.preventDefault();
      }
    }
    if (e.ctrlKey && e.key === "n") {
      e.preventDefault();
      openCreateProjectModal();
    }
    if (e.ctrlKey && e.key === "f") {
      e.preventDefault();
      DOM.projectSearch()?.focus();
    }
  });
}
