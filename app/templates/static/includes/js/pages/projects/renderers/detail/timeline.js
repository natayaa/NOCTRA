// projects/renderers/detail/timeline.js (FIXED & IMPROVED)

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

  // ✅ Dates
  if (startDateEl) {
    startDateEl.textContent = project.project_start_date
      ? Formatter.date(project.project_start_date)
      : "-";
  }
  if (deliveryEl) {
    deliveryEl.textContent = project.project_target_delivery
      ? Formatter.date(project.project_target_delivery)
      : "-";
  }
  if (actualDeliveryEl) {
    actualDeliveryEl.textContent = project.actual_delivery_date
      ? Formatter.date(project.actual_delivery_date)
      : "-";
  }
  if (completedAtEl) {
    completedAtEl.textContent = project.completed_at
      ? Formatter.date(project.completed_at)
      : "-";
  }

  // ✅ Activities
  const activities = projectData?.activities || [];
  if (activitiesEl) {
    if (activities.length === 0) {
      activitiesEl.innerHTML = `
        <div class="activity-empty" style="text-align:center;padding:1rem 0;color:var(--text-muted);">
          <i class="ph ph-clock" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
          <p>No activities recorded.</p>
        </div>
      `;
    } else {
      activitiesEl.innerHTML = activities
        .map((activity, index) => {
          const isLast = index === activities.length - 1;
          const icon =
            activity.activity_type === "creation"
              ? "🚀"
              : activity.activity_type === "status_change"
                ? "🔄"
                : activity.activity_type === "payment"
                  ? "💰"
                  : activity.activity_type === "completion"
                    ? "🎯"
                    : "📌";

          return `
          <div class="timeline-item" style="display:flex;gap:0.75rem;padding:0.5rem 0;${!isLast ? "border-bottom:1px solid var(--border);" : ""}">
            <div class="timeline-icon" style="width:32px;height:32px;border-radius:50%;background:var(--bg-input);display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:0.9rem;">
              ${icon}
            </div>
            <div class="timeline-content" style="flex:1;min-width:0;">
              <div class="title" style="font-size:0.85rem;color:var(--text-primary);">
                ${escapeHtml(activity.activity || "Activity")}
              </div>
              <div class="desc" style="font-size:0.75rem;color:var(--text-secondary);">
                ${escapeHtml(activity.activity_type || "")}
                ${activity.performed_by ? ` · 👤 ${escapeHtml(activity.performed_by)}` : ""}
              </div>
              <div class="time" style="font-size:0.65rem;color:var(--text-muted);">
                ${Formatter.dateTime(activity.created_at)}
              </div>
            </div>
          </div>
        `;
        })
        .join("");
    }
  }

  // ✅ Milestones
  if (milestonesEl) {
    const progress = project.progress || 0;
    const milestones = [
      { label: "25% - Initial Phase", done: progress >= 25 },
      { label: "50% - Midway", done: progress >= 50 },
      { label: "75% - Almost Done", done: progress >= 75 },
      { label: "100% - Complete", done: progress >= 100 },
    ];

    const reached = milestones.filter((m) => m.done).length;

    milestonesEl.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:0.25rem;">
        ${milestones
          .map(
            (m) => `
          <div class="milestone-item" style="display:flex;align-items:center;gap:0.5rem;padding:0.25rem 0.5rem;border-radius:var(--radius-sm);${m.done ? "background:rgba(16,185,129,0.06);" : ""}">
            <span style="font-size:1rem;">${m.done ? "✅" : "⬜"}</span>
            <span class="label" style="${m.done ? "text-decoration:line-through;color:#10b981;" : "color:var(--text-secondary);"}">${m.label}</span>
          </div>
        `,
          )
          .join("")}
        ${
          progress > 0
            ? `
          <div style="margin-top:0.25rem;font-size:0.7rem;color:var(--text-muted);">
            ${reached} of ${milestones.length} milestones reached
          </div>
        `
            : ""
        }
      </div>
    `;
  }
}
