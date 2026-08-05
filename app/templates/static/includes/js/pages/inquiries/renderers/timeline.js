// inquiries/renderers/timeline.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../formatters.js";

export function renderDrawerTimeline(activities) {
  const container = DOM.drawerTimeline();
  if (!container) return;

  if (!activities || activities.length === 0) {
    container.innerHTML = `
      <div class="timeline-empty" style="text-align:center;padding:1rem 0;color:var(--text-muted);">
        <i class="ph ph-clock" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
        <p>No activity yet</p>
      </div>
    `;
    return;
  }

  container.innerHTML = activities
    .map((activity, index) => {
      const isLast = index === activities.length - 1;
      const date = activity.created_at
        ? Formatter.dateTime(activity.created_at)
        : "";
      const content =
        activity.activity ||
        activity.description ||
        activity.action ||
        "Activity";
      const type = activity.activity_type || "";
      const performedBy = activity.performed_by || "system";

      let icon = "📌";
      let typeClass = "";

      if (type === "creation" || type === "status_change") {
        icon = "🔄";
      } else if (type === "payment" || type === "payment_created") {
        icon = "💰";
      } else if (type === "conversion" || type === "convert") {
        icon = "🚀";
      } else if (type === "rejection") {
        icon = "❌";
      } else if (type === "approval") {
        icon = "✅";
      }

      return `
      <div class="timeline-item ${isLast ? "last" : ""}" style="display:flex;gap:0.75rem;padding:0.5rem 0;${!isLast ? "border-bottom:1px solid var(--border);" : ""}">
        <div class="timeline-icon" style="width:32px;height:32px;border-radius:50%;background:var(--bg-input);display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:0.9rem;">
          ${icon}
        </div>
        <div class="timeline-content" style="flex:1;min-width:0;">
          <div class="timeline-title" style="font-size:0.85rem;color:var(--text-primary);">
            ${escapeHtml(content)}
          </div>
          <div class="timeline-meta" style="display:flex;gap:0.5rem;flex-wrap:wrap;font-size:0.65rem;color:var(--text-muted);margin-top:0.1rem;">
            ${date ? `<span>${date}</span>` : ""}
            ${performedBy ? `<span>👤 ${escapeHtml(performedBy)}</span>` : ""}
            ${type ? `<span>🏷️ ${escapeHtml(type)}</span>` : ""}
          </div>
        </div>
      </div>
    `;
    })
    .join("");
}
