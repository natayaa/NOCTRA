// ============================================================
// inquiries/renderers/labor.js - Labor Rendering
// ============================================================

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../formatters.js";

export function renderDrawerLabor(laborItems) {
  const container = DOM.drawerLaborItems();
  if (!container) return;

  if (!laborItems || laborItems.length === 0) {
    container.innerHTML = `
            <div style="text-align:center;padding:0.5rem 0;color:var(--text-muted);">
                <i class="ph ph-user" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
                No labor items recorded
            </div>
        `;
    return;
  }

  let totalLaborCost = 0;
  const laborList = laborItems.map((item) => {
    const hours = Number(item.hours) || 0;
    const rate = Number(item.rate_per_hour) || 0;
    const cost = hours * rate;
    totalLaborCost += cost;
    return { ...item, hours, rate, cost };
  });

  container.innerHTML = `
        ${laborList
          .map(
            (item) => `
            <div class="labor-list-item" style="display:flex;justify-content:space-between;align-items:center;
                        padding:0.5rem 0.75rem;background:var(--bg-input);border-radius:var(--radius-sm);
                        margin-bottom:0.25rem;font-size:0.85rem;">
                <div style="display:flex;flex-direction:column;gap:0.1rem;">
                    <span class="name" style="font-weight:500;color:var(--text-primary);">
                        ${escapeHtml(item.labor_type || "Unknown")}
                    </span>
                    <span style="font-size:0.7rem;color:var(--text-muted);">
                        ${item.technician_name ? `By: ${escapeHtml(item.technician_name)}` : ""}
                        ${item.date_performed ? `· ${Formatter.date(item.date_performed)}` : ""}
                    </span>
                </div>
                <div style="text-align:right;">
                    <span class="hours" style="font-weight:600;color:var(--text-secondary);">
                        ${item.hours}h @ ${Formatter.currency(item.rate)}
                    </span>
                    <br>
                    <span style="font-size:0.75rem;font-weight:600;color:var(--text-primary);">
                        ${Formatter.currency(item.cost)}
                    </span>
                </div>
            </div>
        `,
          )
          .join("")}
        ${
          totalLaborCost > 0
            ? `
            <div style="display:flex;justify-content:space-between;padding:0.5rem 0.75rem;margin-top:0.5rem;
                        border-top:2px solid var(--border);font-weight:600;color:var(--text-primary);">
                <span>Total Labor Cost</span>
                <span>${Formatter.currency(totalLaborCost)}</span>
            </div>
        `
            : ""
        }
    `;
}
