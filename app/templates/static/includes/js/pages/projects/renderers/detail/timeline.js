// ============================================================
// projects/renderers/detail/timeline.js - Timeline Tab
// ============================================================

import { DOM } from "../../dom.js";
import { Formatter, escapeHtml } from "../../formatters.js";

export function renderTimeline(projectData) {
  const project = projectData?.project || projectData;
  if (!project) return;

  const startDateEl = DOM.drawerStartDate();
  const deliveryEl = DOM.drawerDelivery();
  const actualDeliveryEl = DOM.drawerActualDelivery();
  const completedAtEl = DOM.drawerCompletedAt();
  const activitiesEl = DOM.drawerActivities();
  const milestonesEl = DOM.drawerMilestones();

  if (startDateEl)
    startDateEl.textContent = Formatter.date(project.project_start_date);
  if (deliveryEl)
    deliveryEl.textContent = Formatter.date(project.project_target_delivery);
  if (actualDeliveryEl)
    actualDeliveryEl.textContent = Formatter.date(project.actual_delivery_date);
  if (completedAtEl)
    completedAtEl.textContent = Formatter.date(project.completed_at);

  const activities = projectData?.activities || [];
  if (activitiesEl) {
    if (activities.length === 0) {
      activitiesEl.innerHTML =
        '<p style="color:var(--text-muted);">No activities recorded.</p>';
    } else {
      activitiesEl.innerHTML = activities
        .map(
          (activity) => `
                <div class="timeline-item">
                    <div class="timeline-icon"><i class="ph ph-clock"></i></div>
                    <div class="timeline-content">
                        <div class="title">${escapeHtml(activity.activity || "Activity")}</div>
                        <div class="desc">${escapeHtml(activity.activity_type || "")}</div>
                        <div class="time">${Formatter.dateTime(activity.created_at)}</div>
                    </div>
                </div>
            `,
        )
        .join("");
    }
  }

  if (milestonesEl) {
    const progress = project.progress || 0;
    const milestones = [
      { label: "25% - Initial Phase", done: progress >= 25 },
      { label: "50% - Midway", done: progress >= 50 },
      { label: "75% - Almost Done", done: progress >= 75 },
      { label: "100% - Complete", done: progress >= 100 },
    ];
    if (milestones.some((m) => m.done)) {
      milestonesEl.innerHTML = milestones
        .map(
          (m) => `
                <div class="milestone-item">
                    <span class="label ${m.done ? "done" : ""}">${m.done ? "✅" : "⬜"} ${m.label}</span>
                </div>
            `,
        )
        .join("");
    } else {
      milestonesEl.innerHTML =
        '<p style="color:var(--text-muted);">No milestones reached yet.</p>';
    }
  }
}
