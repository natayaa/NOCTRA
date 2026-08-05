// shared/payments/components/FinancialSummary.js

import { PaymentAPI } from "../api.js";
import { PaymentFormatter, escapeHtml } from "../formatters.js";
import { calculatePaymentSummary, calculateInvoiceSummary } from "../utils.js";

export async function renderFinancialSummary(containerId, options = {}) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const {
    inquiryId,
    projectId,
    compact = false,
    showInvoices = true,
  } = options;

  let payments = [];
  let invoices = [];
  let financial = null;

  try {
    if (inquiryId) {
      const [paymentsRes, invoicesRes, financialRes] = await Promise.all([
        PaymentAPI.getByInquiry(inquiryId),
        showInvoices
          ? PaymentAPI.getInvoicesByInquiry(inquiryId)
          : Promise.resolve([]),
        PaymentAPI.getFinancialSummary(inquiryId).catch(() => null),
      ]);
      payments = paymentsRes || [];
      invoices = invoicesRes || [];
      financial = financialRes;
    } else if (projectId) {
      const [paymentsRes, invoicesRes] = await Promise.all([
        PaymentAPI.getByProject(projectId),
        showInvoices
          ? PaymentAPI.getInvoicesByProject(projectId)
          : Promise.resolve([]),
      ]);
      payments = paymentsRes || [];
      invoices = invoicesRes || [];
    }

    const paymentSummary = calculatePaymentSummary(payments);
    const invoiceSummary = calculateInvoiceSummary(invoices);

    if (compact) {
      container.innerHTML = renderCompactSummary(
        paymentSummary,
        invoiceSummary,
        financial,
        showInvoices,
      );
    } else {
      container.innerHTML = renderFullSummary(
        paymentSummary,
        invoiceSummary,
        financial,
        showInvoices,
      );
    }
  } catch (error) {
    console.error("Failed to load financial summary:", error);
    container.innerHTML = `
      <div class="financial-error" style="text-align:center;padding:1rem;color:var(--text-muted);">
        <i class="ph ph-warning" style="font-size:1.5rem;display:block;margin-bottom:0.5rem;"></i>
        <p>Failed to load financial data</p>
      </div>
    `;
  }
}

function renderCompactSummary(
  paymentSummary,
  invoiceSummary,
  financial,
  showInvoices,
) {
  return `
    <div class="financial-summary-compact" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:0.5rem;">
      <div class="summary-item" style="background:var(--bg-input);padding:0.5rem 0.75rem;border-radius:var(--radius-sm);text-align:center;">
        <span style="font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;">Deposit</span>
        <strong style="display:block;font-size:0.9rem;color:var(--text-primary);">${PaymentFormatter.currency(paymentSummary.totalDeposit)}</strong>
      </div>
      <div class="summary-item success" style="background:rgba(0,213,120,0.08);padding:0.5rem 0.75rem;border-radius:var(--radius-sm);text-align:center;">
        <span style="font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;">Paid</span>
        <strong style="display:block;font-size:0.9rem;color:#00d578;">${PaymentFormatter.currency(paymentSummary.totalPaid)}</strong>
      </div>
      <div class="summary-item warning" style="background:rgba(245,158,11,0.08);padding:0.5rem 0.75rem;border-radius:var(--radius-sm);text-align:center;">
        <span style="font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;">Pending</span>
        <strong style="display:block;font-size:0.9rem;color:#f59e0b;">${PaymentFormatter.currency(paymentSummary.totalPending)}</strong>
      </div>
      <div class="summary-item highlight" style="background:rgba(var(--primary-rgb),0.08);padding:0.5rem 0.75rem;border-radius:var(--radius-sm);text-align:center;">
        <span style="font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;">Remaining</span>
        <strong style="display:block;font-size:0.9rem;color:var(--primary);">${PaymentFormatter.currency(paymentSummary.remaining)}</strong>
      </div>
      ${
        showInvoices && invoiceSummary.overdueCount > 0
          ? `
        <div class="summary-item danger" style="background:rgba(239,68,68,0.08);padding:0.5rem 0.75rem;border-radius:var(--radius-sm);text-align:center;grid-column:span 2;">
          <span style="font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;">⚠️ Overdue</span>
          <strong style="display:block;font-size:0.9rem;color:#ef4444;">${invoiceSummary.overdueCount} invoices (${PaymentFormatter.currency(invoiceSummary.overdueAmount)})</strong>
        </div>
      `
          : ""
      }
    </div>
  `;
}

function renderFullSummary(
  paymentSummary,
  invoiceSummary,
  financial,
  showInvoices,
) {
  return `
    <div class="financial-summary-full">
      <div class="financial-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;margin-bottom:1rem;">
        <div class="financial-item" style="background:var(--bg-input);padding:0.75rem 1rem;border-radius:var(--radius-md);">
          <span style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;">Total Deposit</span>
          <strong style="display:block;font-size:1.1rem;color:var(--text-primary);">${PaymentFormatter.currency(paymentSummary.totalDeposit)}</strong>
        </div>
        <div class="financial-item success" style="background:rgba(0,213,120,0.08);padding:0.75rem 1rem;border-radius:var(--radius-md);">
          <span style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;">Total Paid</span>
          <strong style="display:block;font-size:1.1rem;color:#00d578;">${PaymentFormatter.currency(paymentSummary.totalPaid)}</strong>
        </div>
        <div class="financial-item warning" style="background:rgba(245,158,11,0.08);padding:0.75rem 1rem;border-radius:var(--radius-md);">
          <span style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;">Pending</span>
          <strong style="display:block;font-size:1.1rem;color:#f59e0b;">${PaymentFormatter.currency(paymentSummary.totalPending)}</strong>
        </div>
        <div class="financial-item highlight" style="background:rgba(var(--primary-rgb),0.08);padding:0.75rem 1rem;border-radius:var(--radius-md);">
          <span style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;">Remaining</span>
          <strong style="display:block;font-size:1.1rem;color:var(--primary);">${PaymentFormatter.currency(paymentSummary.remaining)}</strong>
        </div>
      </div>

      ${
        financial
          ? `
        <div class="financial-breakdown" style="background:var(--bg-input);padding:0.75rem 1rem;border-radius:var(--radius-md);margin-bottom:1rem;">
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;">
            <div><span style="font-size:0.7rem;color:var(--text-muted);">Estimated Cost</span><br><strong>${PaymentFormatter.currency(financial.estimated_cost || 0)}</strong></div>
            <div><span style="font-size:0.7rem;color:var(--text-muted);">Actual Cost</span><br><strong>${PaymentFormatter.currency(financial.actual_cost || 0)}</strong></div>
            <div><span style="font-size:0.7rem;color:var(--text-muted);">Profit</span><br><strong style="color:${(financial.actual_revenue || 0) - (financial.actual_cost || 0) >= 0 ? "#00d578" : "#ef4444"};">${PaymentFormatter.currency((financial.actual_revenue || 0) - (financial.actual_cost || 0))}</strong></div>
          </div>
        </div>
      `
          : ""
      }

      ${
        showInvoices
          ? `
        <div class="invoices-summary" style="display:flex;gap:0.5rem;flex-wrap:wrap;padding:0.75rem 1rem;background:var(--bg-input);border-radius:var(--radius-md);">
          <span style="font-size:0.8rem;color:var(--text-secondary);">📄 Invoices: <strong>${invoiceSummary.totalInvoices}</strong></span>
          <span style="font-size:0.8rem;color:var(--text-secondary);">💰 Total: <strong>${PaymentFormatter.currency(invoiceSummary.totalAmount)}</strong></span>
          <span style="font-size:0.8rem;color:var(--text-secondary);">✅ Paid: <strong>${PaymentFormatter.currency(invoiceSummary.totalPaid)}</strong></span>
          ${
            invoiceSummary.overdueCount > 0
              ? `
            <span style="font-size:0.8rem;color:#ef4444;">⚠️ Overdue: <strong>${invoiceSummary.overdueCount}</strong> (${PaymentFormatter.currency(invoiceSummary.overdueAmount)})</span>
          `
              : ""
          }
        </div>
      `
          : ""
      }
    </div>
  `;
}
