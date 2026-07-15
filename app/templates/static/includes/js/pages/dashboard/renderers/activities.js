// ============================================================
// dashboard/renderers/activities.js - Recent Activities
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";

const ICONS = [
  "fa-file-signature",
  "fa-file-invoice",
  "fa-briefcase",
  "fa-exclamation-triangle",
  "fa-check-circle",
  "fa-clock",
];

export function renderActivities() {
  const container = DOM.recentActivities();
  if (!container) return;

  const activities = state.recentActivities;

  if (!activities || activities.length === 0) {
    container.innerHTML = `
      <div class="activity-item">
        <div class="activity-icon"><i class="fas fa-check-circle" style="color:var(--success);"></i></div>
        <div class="activity-content">
          <p class="activity-text">No recent activities</p>
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = activities
    .map((activity, index) => {
      const icon = ICONS[index % ICONS.length];
      const text =
        activity.text ||
        activity.activity ||
        activity.description ||
        "Activity";
      const time = activity.time || activity.created_at || activity.date || "";
      const timeFormatted = time ? formatTimeAgo(time) : "";

      return `
        <div class="activity-item">
          <div class="activity-icon"><i class="fas ${icon}"></i></div>
          <div class="activity-content">
            <p class="activity-text">${text}</p>
            ${timeFormatted ? `<span class="activity-time">${timeFormatted}</span>` : ""}
          </div>
        </div>
      `;
    })
    .join("");
}

function formatTimeAgo(dateString) {
  try {
    const now = new Date();
    const past = new Date(dateString);
    const diffMs = now - past;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return past.toLocaleDateString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

export function updateActivitiesFromData(activities) {
  state.recentActivities = activities;
}
