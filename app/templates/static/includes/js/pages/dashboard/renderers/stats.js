// ============================================================
// dashboard/renderers/stats.js - Update Stat Cards
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";

const formatter = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export function renderStats() {
  const {
    revenue,
    activeProjects,
    inProduction,
    pendingInquiries,
    overdueInvoices,
    lowStockItems,
    completedProjects,
    quotesSent,
    totalCustomers,
  } = state.stats;

  // Main stats
  setText(DOM.statRevenue(), formatter.format(revenue));
  setText(DOM.statActiveProjects(), activeProjects);
  setText(DOM.statInProduction(), inProduction);
  setText(DOM.statPendingInquiries(), pendingInquiries);
  setText(DOM.statOverdueInvoices(), overdueInvoices);
  setText(DOM.statLowStock(), lowStockItems);

  // Change indicators (sederhana)
  setChangeText(
    DOM.statActiveProjectsChange(),
    activeProjects > 0 ? "📈 Active" : "—",
  );
  setChangeText(
    DOM.statInProductionChange(),
    inProduction > 0 ? "⚙️ Running" : "—",
  );
  setChangeText(
    DOM.statPendingInquiriesChange(),
    pendingInquiries > 0 ? "📩 Awaiting" : "—",
  );
  setChangeText(
    DOM.statOverdueInvoicesChange(),
    overdueInvoices > 0 ? "⚠️ Overdue" : "✅ All paid",
  );
  setChangeText(
    DOM.statLowStockChange(),
    lowStockItems > 0 ? "⚠️ Need reorder" : "✅ Stock OK",
  );

  // Mini stats
  setText(DOM.miniCompleted(), completedProjects);
  setText(DOM.miniQuotesSent(), quotesSent);
  setText(DOM.miniCustomers(), totalCustomers);
}

function setText(el, value) {
  if (!el) return;
  el.textContent = value !== undefined && value !== null ? value : 0;
}

function setChangeText(el, value) {
  if (!el) return;
  el.textContent = value || "—";
}

export function updateStatsFromResponse(data) {
  // Digunakan untuk mengupdate state sebelum render
  if (data) {
    Object.assign(state.stats, data);
  }
}
