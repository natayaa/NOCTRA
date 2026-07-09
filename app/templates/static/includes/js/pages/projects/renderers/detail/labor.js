// ============================================================
// projects/renderers/detail/labor.js - Labor Tab
// ============================================================
// projects/renderers/detail/labor.js

import { DOM } from "../../dom.js";
import { Formatter, escapeHtml } from "../../formatters.js";
import { updateLaborSummary } from "../../handlers/labor.js";

export function renderLabor(projectData) {
  const container = DOM.laborList();
  if (!container) return;

  const financial = projectData?.financial_summary || {};
  const laborItems = financial.labor_items || [];

  // Update summary
  updateLaborSummary(laborItems);

  // Update count
  const countEl = document.getElementById("laborCount");
  if (countEl) {
    countEl.textContent = `${laborItems.length} entry${laborItems.length !== 1 ? "s" : ""}`;
  }

  if (!laborItems || laborItems.length === 0) {
    container.innerHTML = `
      <div class="labor-empty">
        <i class="ph ph-users"></i>
        <p>No labor recorded yet.</p>
        <small style="font-size:0.8rem;">Add labor using the form above</small>
      </div>
    `;
    return;
  }

  container.innerHTML = laborItems
    .map((item) => {
      const name = item.labor_type || item.name || item.type || "Unknown Labor";
      const hours = item.hours || 0;
      const rate = item.rate_per_hour || item.rate || 0;
      const total = hours * rate;
      const id = item.id;
      const technician = item.technician_name || item.technical_name || "";
      const datePerformed = item.date_performed
        ? new Date(item.date_performed).toLocaleDateString("id-ID")
        : "";

      // Build display string
      let details = `${hours}h`;
      if (rate > 0) details += ` @ ${Formatter.currency(rate)}`;
      if (technician) details += ` · ${escapeHtml(technician)}`;
      if (datePerformed) details += ` · ${datePerformed}`;

      return `
        <div class="labor-list-item" data-id="${id}">
          <div class="labor-info">
            <span class="name">${escapeHtml(name)}</span>
            <span class="details">${escapeHtml(details)}</span>
          </div>
          <span class="labor-total">${Formatter.currency(total)}</span>
          <button onclick="window.handleDeleteLabor('${id}')" class="btn-danger btn-sm" title="Delete labor entry">
            <i class="ph ph-trash"></i>
          </button>
        </div>
      `;
    })
    .join("");
}
