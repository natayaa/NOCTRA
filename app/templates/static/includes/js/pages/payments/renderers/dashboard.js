// ============================================================
// payments/renderers/dashboard.js - Dashboard Stats (FIXED)
// ============================================================

import { DOM } from "../dom.js";
import { PaymentFormatter } from "../../shared/payments/formatters.js";
import {
  calculatePaymentSummary,
  calculateInvoiceSummary,
} from "../../shared/payments/utils.js";

export function renderDashboard(stats, payments = [], invoices = []) {
  const totalRevenueEl = DOM.totalRevenue();
  const totalPaidEl = DOM.totalPaid();
  const totalPendingEl = DOM.totalPending();
  const overdueInvoicesEl = DOM.overdueInvoices();

  if (!stats) {
    const paymentSummary = calculatePaymentSummary(payments);
    const invoiceSummary = calculateInvoiceSummary(invoices);

    if (totalRevenueEl) {
      totalRevenueEl.textContent = PaymentFormatter.currency(
        paymentSummary.totalPaid,
      );
    }
    if (totalPaidEl) {
      totalPaidEl.textContent = PaymentFormatter.currency(
        paymentSummary.totalPaid,
      );
    }
    if (totalPendingEl) {
      totalPendingEl.textContent = PaymentFormatter.currency(
        paymentSummary.totalPending,
      );
    }
    if (overdueInvoicesEl) {
      overdueInvoicesEl.textContent = invoiceSummary.overdueCount;
    }
    return;
  }

  if (totalRevenueEl) {
    totalRevenueEl.textContent = PaymentFormatter.currency(
      stats.total_revenue || 0,
    );
  }
  if (totalPaidEl) {
    totalPaidEl.textContent = PaymentFormatter.currency(stats.total_paid || 0);
  }
  if (totalPendingEl) {
    totalPendingEl.textContent = PaymentFormatter.currency(
      stats.total_pending || 0,
    );
  }
  if (overdueInvoicesEl) {
    overdueInvoicesEl.textContent = stats.overdue_invoices || 0;
  }
}
