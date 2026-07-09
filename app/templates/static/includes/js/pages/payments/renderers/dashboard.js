// ============================================================
// payments/renderers/dashboard.js - Dashboard Stats
// ============================================================

import { DOM } from "../dom.js";
import { PaymentFormatter } from "../../shared/payments/formatters.js";
import {
  calculatePaymentSummary,
  calculateInvoiceSummary,
} from "../../shared/payments/utils.js";

export function renderDashboard(stats, payments = [], invoices = []) {
  if (!stats) {
    // Calculate from data if stats not available
    const paymentSummary = calculatePaymentSummary(payments);
    const invoiceSummary = calculateInvoiceSummary(invoices);

    const totalRevenue = DOM.totalRevenue();
    const totalPaid = DOM.totalPaid();
    const totalPending = DOM.totalPending();
    const overdueInvoices = DOM.overdueInvoices();

    if (totalRevenue)
      totalRevenue.textContent = PaymentFormatter.currency(
        paymentSummary.totalPaid,
      );
    if (totalPaid)
      totalPaid.textContent = PaymentFormatter.currency(
        paymentSummary.totalPaid,
      );
    if (totalPending)
      totalPending.textContent = PaymentFormatter.currency(
        paymentSummary.totalPending,
      );
    if (overdueInvoices)
      overdueInvoices.textContent = invoiceSummary.overdueCount;
    return;
  }

  const totalRevenueEl = DOM.totalRevenue();
  const totalPaidEl = DOM.totalPaid();
  const totalPendingEl = DOM.totalPending();
  const overdueInvoicesEl = DOM.overdueInvoices();

  if (totalRevenueEl)
    totalRevenueEl.textContent = PaymentFormatter.currency(
      stats.total_revenue || 0,
    );
  if (totalPaidEl)
    totalPaidEl.textContent = PaymentFormatter.currency(stats.total_paid || 0);
  if (totalPendingEl)
    totalPendingEl.textContent = PaymentFormatter.currency(
      stats.total_pending || 0,
    );
  if (overdueInvoicesEl)
    overdueInvoicesEl.textContent = stats.overdue_invoices || 0;
}
