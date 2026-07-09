// ============================================================
// projects/handlers/progress.js - Progress Popup
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { ProjectAPI } from "../api.js";
import { showToast } from "../toast.js";
import { loadProjects } from "../index.js";
import { openProjectDrawer } from "../drawer.js";
import { getProjectById } from "../utils.js";

export function openProgressPopup(projectId) {
  const project = getProjectById(projectId);
  if (!project) {
    showToast("Project not found", "error");
    return;
  }

  state._progressProjectId = projectId;
  const progress = project.progress || 0;

  const slider = DOM.progressPopupSlider();
  const valueEl = DOM.progressPopupValue();
  const noteEl = DOM.progressPopupNote();
  const checkbox = DOM.markCompleteCheckbox();
  const milestonesEl = DOM.progressPopupMilestones();
  const popup = DOM.progressPopup();

  if (slider) slider.value = progress;
  if (valueEl) valueEl.textContent = progress;
  if (noteEl) noteEl.value = "";
  if (checkbox) checkbox.checked = progress >= 100;

  if (milestonesEl) {
    milestonesEl.innerHTML = `
            <div class="milestone-item"><input type="checkbox" class="checkbox" ${progress >= 25 ? "checked" : ""} /><span class="label ${progress >= 25 ? "done" : ""}">25% - Initial Phase</span></div>
            <div class="milestone-item"><input type="checkbox" class="checkbox" ${progress >= 50 ? "checked" : ""} /><span class="label ${progress >= 50 ? "done" : ""}">50% - Midway</span></div>
            <div class="milestone-item"><input type="checkbox" class="checkbox" ${progress >= 75 ? "checked" : ""} /><span class="label ${progress >= 75 ? "done" : ""}">75% - Almost Done</span></div>
            <div class="milestone-item"><input type="checkbox" class="checkbox" ${progress >= 100 ? "checked" : ""} /><span class="label ${progress >= 100 ? "done" : ""}">100% - Complete</span></div>
        `;
  }

  if (popup) {
    popup.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

export function closeProgressPopup() {
  const popup = DOM.progressPopup();
  if (popup) popup.classList.remove("active");
  document.body.style.overflow = "";
  state._progressProjectId = null;
}

export async function handleSaveProgress() {
  const projectId = state._progressProjectId;
  if (!projectId) {
    showToast("No project selected", "error");
    return;
  }

  const progress = parseInt(DOM.progressPopupSlider?.value || 0);
  const note = DOM.progressPopupNote?.value?.trim() || "";

  if (isNaN(progress) || progress < 0 || progress > 100) {
    showToast("Progress must be between 0 and 100", "error");
    return;
  }

  const result = await ProjectAPI.updateProgress(projectId, progress, note);
  if (result) {
    showToast(`Progress updated to ${progress}%`, "success");
    if (progress >= 100 && DOM.markCompleteCheckbox?.checked) {
      await ProjectAPI.complete(projectId);
      showToast("Project marked as completed! 🎉", "success");
    }
    closeProgressPopup();
    await loadProjects();
    if (
      DOM.drawer?.classList.contains("active") &&
      state.currentProjectId === projectId
    ) {
      await openProjectDrawer(projectId);
    }
  }
}
