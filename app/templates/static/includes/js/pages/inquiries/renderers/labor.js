// inquiries/renderers/labor.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../formatters.js";

export function renderDrawerLabor(laborItems) {
  const container = DOM.drawerLaborItems();
  if (!container) return;

  if (!laborItems || laborItems.length === 0) {
    container.innerHTML = `
      <div class="labor-empty" style="text-align:center;padding:1rem 0;color:var(--text-muted);">
        <i class="ph ph-user" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
        <p>No labor items recorded</p>
      </div>
    `;
    return;
  }

  let totalLaborCost = 0;
  const laborList = laborItems.map((item) => {
    const hours = Number(item.hours) || 0;
    const rate = Number(item.rate_per_hour) || Number(item.rate) || 0;
    const cost = hours * rate;
    totalLaborCost += cost;
    return { ...item, hours, rate, cost };
  });

  container.innerHTML = `
    <div class="labor-list">
      ${laborList
        .map(
          (item) => `
        <div class="labor-list-item" style="display:flex;justify-content:space-between;align-items:center;
                    padding:0.5rem 0.75rem;background:var(--bg-input);border-radius:var(--radius-sm);
                    margin-bottom:0.25rem;font-size:0.85rem;transition:background 0.2s ease;
                    border-left:3px solid var(--primary);">
          <div style="display:flex;flex-direction:column;gap:0.1rem;flex:1;min-width:0;">
            <span class="name" style="font-weight:500;color:var(--text-primary);">
              ${escapeHtml(item.labor_type || "Unknown Labor")}
            </span>
            <span style="font-size:0.7rem;color:var(--text-muted);display:flex;gap:0.5rem;flex-wrap:wrap;">
              ${item.technician_name ? `👤 ${escapeHtml(item.technician_name)}` : ""}
              ${item.date_performed ? `📅 ${Formatter.date(item.date_performed)}` : ""}
              ${item.description ? `📝 ${escapeHtml(item.description.substring(0, 50))}` : ""}
            </span>
          </div>
          <div style="text-align:right;flex-shrink:0;margin-left:0.5rem;">
            <div style="font-weight:600;color:var(--text-secondary);font-size:0.8rem;">
              ${item.hours}h @ ${Formatter.currency(item.rate)}
            </div>
            <div style="font-weight:700;color:var(--text-primary);font-size:0.85rem;">
              ${Formatter.currency(item.cost)}
            </div>
          </div>
        </div>
      `,
        )
        .join("")}
    </div>
    ${
      totalLaborCost > 0
        ? `
      <div style="display:flex;justify-content:space-between;padding:0.6rem 0.75rem;margin-top:0.5rem;
                  border-top:2px solid var(--border);font-weight:600;color:var(--text-primary);
                  background:var(--bg-input);border-radius:var(--radius-sm);font-size:0.85rem;">
        <span>Total Labor Cost</span>
        <span style="color:var(--primary);">${Formatter.currency(totalLaborCost)}</span>
      </div>
    `
        : ""
    }
  `;
}
