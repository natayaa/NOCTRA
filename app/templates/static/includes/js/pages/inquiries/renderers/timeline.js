// ============================================================
// inquiries/renderers/timeline.js - Timeline Rendering
// ============================================================

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../formatters.js";

export function renderDrawerTimeline(activities) {
  const container = DOM.drawerTimeline();
  if (!container) return;

  if (!activities || activities.length === 0) {
    container.innerHTML = `
            <div class="timeline-item">
                <span>—</span>
                <p>No activity yet</p>
            </div>
        `;
    return;
  }

  container.innerHTML = activities
    .map(
      (activity) => `
        <div class="timeline-item">
            <span class="time">${Formatter.date(activity.created_at)}</span>
            <p class="content">${escapeHtml(activity.activity || activity.description || activity.action || "Activity")}</p>
        </div>
    `,
    )
    .join("");
}
