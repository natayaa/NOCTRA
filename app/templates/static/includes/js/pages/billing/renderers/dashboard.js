// ============================================================
// billing/renderers/dashboard.js
// ============================================================

import { DOM } from "../dom.js";
import { PaymentFormatter } from "../../shared/payments/formatters.js";

export function updateDashboard(stats) {
  const { totalQuotes, pendingQuotes, outstandingInvoices, overdueInvoices } =
    DOM;

  if (!stats) {
    // Set default empty state
    if (totalQuotes()) totalQuotes().textContent = "0";
    if (pendingQuotes()) pendingQuotes().textContent = "0";
    if (outstandingInvoices()) outstandingInvoices().textContent = "0";
    if (overdueInvoices()) overdueInvoices().textContent = "0";
    return;
  }

  // stats structure: { totalQuotes, pendingQuotes, outstandingInvoices, overdueInvoices }
  if (totalQuotes()) totalQuotes().textContent = stats.totalQuotes || 0;
  if (pendingQuotes()) pendingQuotes().textContent = stats.pendingQuotes || 0;
  if (outstandingInvoices())
    outstandingInvoices().textContent = stats.outstandingInvoices || 0;
  if (overdueInvoices())
    overdueInvoices().textContent = stats.overdueInvoices || 0;
}

export function updateBadgeCounts(quoteCount, invoiceCount) {
  const quoteBadge = DOM.quoteBadge();
  const invoiceBadge = DOM.invoiceBadge();
  if (quoteBadge) quoteBadge.textContent = quoteCount || 0;
  if (invoiceBadge) invoiceBadge.textContent = invoiceCount || 0;
}
