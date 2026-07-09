// ============================================================
// projects/renderers/dashboard.js - Dashboard Stats Rendering
// ============================================================

import { DOM } from "../dom.js";
import { Formatter } from "../formatters.js";

export function updateDashboard(stats) {
  if (!stats) return;

  // Try different possible data structures
  const active = stats.active_count || stats.by_status?.active || 0;
  const inProgress =
    stats.in_production_count || stats.by_status?.in_progress || 0;
  const completed =
    stats.completed_this_month || stats.by_status?.completed || 0;
  const revenue =
    stats.estimated_revenue || stats.financial?.estimated_revenue || 0;

  const activeEl = DOM.activeCount();
  const prodEl = DOM.prodCount();
  const completedEl = DOM.completedCount();
  const revenueEl = DOM.revenueTotal();

  if (activeEl) activeEl.textContent = active;
  if (prodEl) prodEl.textContent = inProgress;
  if (completedEl) completedEl.textContent = completed;
  if (revenueEl) revenueEl.textContent = Formatter.currency(revenue);

  //console.log("📊 Dashboard updated:", {
  //  active,
  //  inProgress,
  //  completed,
  //  revenue,
  //});
}
