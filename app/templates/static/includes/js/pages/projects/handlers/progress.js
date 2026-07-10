// projects/handlers/progress.js (FIXED & IMPROVED)

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
  if (noteEl) {
    noteEl.value = "";
    noteEl.placeholder = "Add a quick update note...";
  }
  if (checkbox) checkbox.checked = progress >= 100;

  if (milestonesEl) {
    milestonesEl.innerHTML = `
      <div class="milestone-item">
        <input type="checkbox" class="checkbox" ${progress >= 25 ? "checked" : ""} disabled />
        <span class="label ${progress >= 25 ? "done" : ""}">25% - Initial Phase</span>
      </div>
      <div class="milestone-item">
        <input type="checkbox" class="checkbox" ${progress >= 50 ? "checked" : ""} disabled />
        <span class="label ${progress >= 50 ? "done" : ""}">50% - Midway</span>
      </div>
      <div class="milestone-item">
        <input type="checkbox" class="checkbox" ${progress >= 75 ? "checked" : ""} disabled />
        <span class="label ${progress >= 75 ? "done" : ""}">75% - Almost Done</span>
      </div>
      <div class="milestone-item">
        <input type="checkbox" class="checkbox" ${progress >= 100 ? "checked" : ""} disabled />
        <span class="label ${progress >= 100 ? "done" : ""}">100% - Complete</span>
      </div>
    `;
  }

  if (popup) {
    popup.classList.add("active");
    document.body.style.overflow = "hidden";
    // Focus slider
    setTimeout(() => slider?.focus(), 100);
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

  const slider = DOM.progressPopupSlider();
  const progress = slider ? parseInt(slider.value) || 0 : 0;
  const noteEl = DOM.progressPopupNote();
  const note = noteEl ? noteEl.value?.trim() || "" : "";
  const checkbox = DOM.markCompleteCheckbox();

  if (isNaN(progress) || progress < 0 || progress > 100) {
    showToast("Progress must be between 0 and 100", "error");
    return;
  }

  // Konfirmasi jika progress turun signifikan
  const currentProject = getProjectById(projectId);
  if (
    currentProject &&
    progress < currentProject.progress &&
    currentProject.progress - progress > 20
  ) {
    if (
      !confirm(
        `⚠️ You are reducing progress from ${currentProject.progress}% to ${progress}%. Continue?`,
      )
    ) {
      return;
    }
  }

  const saveBtn = DOM.saveProgressBtn();
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";
  }

  try {
    const result = await ProjectAPI.updateProgress(projectId, progress, note);
    if (result) {
      showToast(`✅ Progress updated to ${progress}%`, "success");

      // Auto-complete if 100% and checkbox checked
      if (progress >= 100 && checkbox && checkbox.checked) {
        const completeResult = await ProjectAPI.complete(projectId);
        if (completeResult) {
          showToast("🎉 Project marked as completed!", "success");
        }
      }

      closeProgressPopup();
      await loadProjects();

      // Refresh drawer
      const drawer = DOM.drawer();
      if (
        drawer &&
        drawer.classList.contains("active") &&
        state.currentProjectId === projectId
      ) {
        await openProjectDrawer(projectId);
      }
    } else {
      showToast("❌ Failed to update progress", "error");
    }
  } catch (error) {
    console.error("Progress update error:", error);
    showToast("❌ " + (error.message || "Failed to update progress"), "error");
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save Progress";
    }
  }
}
