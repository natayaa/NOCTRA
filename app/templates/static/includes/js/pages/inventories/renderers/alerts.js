// ============================================================
// inventories/renderers/alerts.js - Stock Alerts Rendering
// ============================================================

import { DOM } from "../dom.js";
import { escapeHtml } from "../formatters.js";

export function renderAlerts(alerts) {
  const list = DOM.alertList();
  if (!list) return;

  if (!alerts || alerts.length === 0) {
    list.innerHTML = `
            <div class="alert-item" style="text-align:center;color:var(--text-muted);padding:0.5rem;">
                <i class="fas fa-check-circle" style="color:#00d578;"></i> All items are properly stocked
            </div>
        `;
    return;
  }

  list.innerHTML = alerts
    .map(
      (alert) => `
        <div class="alert-item ${alert.severity === "critical" ? "critical" : "warning"}">
            <div class="alert-info">
                <strong>${escapeHtml(alert.item_name)}</strong>
                <span>${escapeHtml(alert.message || "Low stock")} · ${alert.current_stock} ${alert.unit || ""} remaining</span>
            </div>
            <span class="alert-badge">${alert.severity === "critical" ? "⚠️ Critical" : "⚠️ Low"}</span>
        </div>
    `,
    )
    .join("");
}
