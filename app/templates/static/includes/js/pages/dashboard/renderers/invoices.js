// ============================================================
// dashboard/renderers/invoices.js - Recent Invoices
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";

const formatter = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export function renderRecentInvoices() {
  const container = DOM.recentInvoices();
  if (!container) return;

  const invoices = state.recentInvoices;

  if (!invoices || invoices.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="loading-placeholder">No recent invoices</td></tr>`;
    return;
  }

  container.innerHTML = invoices
    .map((inv) => {
      const number = inv.invoice_number || inv.number || "N/A";
      const customer = inv.customer_name || inv.customer || "-";
      const amount = inv.total_amount || inv.total || 0;
      const status = inv.status || "draft";

      return `
        <tr>
          <td><strong style="color:var(--text-primary);">${escapeHtml(number)}</strong></td>
          <td>${escapeHtml(customer)}</td>
          <td>${formatter.format(amount)}</td>
          <td><span class="status-badge-mini ${status}">${statusLabel(status)}</span></td>
        </tr>
      `;
    })
    .join("");
}

function statusLabel(status) {
  const map = {
    draft: "Draft",
    sent: "Sent",
    paid: "Paid",
    overdue: "Overdue",
    cancelled: "Cancelled",
    partial: "Partial",
  };
  return map[status] || status;
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

export function updateInvoicesFromData(invoices) {
  state.recentInvoices = invoices;
}
