// ============================================================
// payments/renderers/table.js - Table Rendering
// ============================================================

import { DOM } from "../dom.js";
import {
  PaymentFormatter,
  escapeHtml,
} from "../../shared/payments/formatters.js";

export function showLoadingState(tableType = "payments") {
  const body =
    tableType === "payments" ? DOM.paymentsBody() : DOM.invoicesBody();
  if (!body) return;

  body.innerHTML = `
        <tr>
            <td colspan="8" style="text-align:center;padding:2rem;">
                <i class="ph ph-spinner" style="font-size:1.5rem;animation:spin 1s linear infinite;display:block;margin-bottom:0.5rem;"></i>
                <p style="color:var(--text-muted);">Loading ${tableType}...</p>
            </td>
        </tr>
    `;
}

export function renderPayments(payments) {
  const body = DOM.paymentsBody();
  if (!body) return;

  if (!payments || payments.length === 0) {
    body.innerHTML = `
            <tr>
                <td colspan="8" style="text-align:center;padding:2rem;color:var(--text-muted);">
                    <i class="ph ph-credit-card" style="font-size:2rem;display:block;margin-bottom:0.5rem;"></i>
                    No payments found
                </td>
            </tr>
        `;
    return;
  }

  body.innerHTML = payments
    .map(
      (payment) => `
        <tr class="fade-in">
            <td>
                <strong style="font-size:0.8rem;">${escapeHtml(payment.id?.substring(0, 8) || "N/A")}</strong>
                ${payment.reference_number ? `<br><small style="color:var(--text-muted);">${escapeHtml(payment.reference_number)}</small>` : ""}
            </td>
            <td>
                <span class="type-badge">${PaymentFormatter.paymentTypeLabel(payment.type || payment.payment_type || "payment")}</span>
            </td>
            <td style="font-weight:600;color:var(--text-primary);">
                ${PaymentFormatter.currency(payment.amount)}
            </td>
            <td>${escapeHtml(payment.method || payment.payment_method || "-")}</td>
            <td>
                <span class="status-badge ${PaymentFormatter.paymentStatusBadge(payment.status)}">
                    ${PaymentFormatter.paymentStatusLabel(payment.status)}
                </span>
            </td>
            <td style="font-size:0.8rem;color:var(--text-secondary);">
                ${payment.inquiry_id ? `Inq: ${escapeHtml(payment.inquiry_id?.substring(0, 8))}` : ""}
                ${payment.project_id ? `<br>Proj: ${escapeHtml(payment.project_id?.substring(0, 8))}` : ""}
            </td>
            <td style="font-size:0.8rem;color:var(--text-muted);">
                ${PaymentFormatter.date(payment.created_at || payment.paid_at)}
            </td>
            <td style="text-align:center;white-space:nowrap;">
                <button class="action-btn" onclick="window.confirmPayment('${payment.id}')" title="Confirm" ${payment.status === "completed" ? "disabled" : ""}>
                    <i class="ph ph-check-circle"></i>
                </button>
                <button class="action-btn" onclick="window.viewPayment('${payment.id}')" title="View">
                    <i class="ph ph-eye"></i>
                </button>
                ${
                  payment.status === "pending"
                    ? `
                    <button class="action-btn danger" onclick="window.cancelPayment('${payment.id}')" title="Cancel">
                        <i class="ph ph-x-circle"></i>
                    </button>
                `
                    : ""
                }
            </td>
        </tr>
    `,
    )
    .join("");
}

export function renderInvoices(invoices) {
  const body = DOM.invoicesBody();
  if (!body) return;

  if (!invoices || invoices.length === 0) {
    body.innerHTML = `
            <tr>
                <td colspan="7" style="text-align:center;padding:2rem;color:var(--text-muted);">
                    <i class="ph ph-file-text" style="font-size:2rem;display:block;margin-bottom:0.5rem;"></i>
                    No invoices found
                </td>
            </tr>
        `;
    return;
  }

  body.innerHTML = invoices
    .map(
      (invoice) => `
        <tr class="fade-in">
            <td>
                <strong>${escapeHtml(invoice.invoice_number || "#")}</strong>
            </td>
            <td>${escapeHtml(invoice.customer_name || invoice.inquiry?.customer_name || "-")}</td>
            <td style="font-weight:600;color:var(--text-primary);">
                ${PaymentFormatter.currency(invoice.total || 0)}
            </td>
            <td>${PaymentFormatter.currency(invoice.paid_amount || 0)}</td>
            <td>
                <span class="status-badge ${PaymentFormatter.invoiceStatusBadge(invoice.status)}">
                    ${PaymentFormatter.invoiceStatusLabel(invoice.status)}
                </span>
            </td>
            <td style="font-size:0.8rem;color:${invoice.status === "overdue" ? "#ef4444" : "var(--text-muted)"};">
                ${PaymentFormatter.date(invoice.due_date)}
                ${invoice.status === "overdue" ? " ⚠️" : ""}
            </td>
            <td style="text-align:center;white-space:nowrap;">
                <button class="action-btn" onclick="window.viewInvoice('${invoice.id}')" title="View">
                    <i class="ph ph-eye"></i>
                </button>
                ${
                  invoice.status === "draft"
                    ? `
                    <button class="action-btn" onclick="window.sendInvoice('${invoice.id}')" title="Send">
                        <i class="ph ph-paper-plane"></i>
                    </button>
                `
                    : ""
                }
                ${
                  invoice.status !== "paid" && invoice.status !== "cancelled"
                    ? `
                    <button class="action-btn success" onclick="window.markInvoicePaid('${invoice.id}')" title="Mark Paid">
                        <i class="ph ph-check-circle"></i>
                    </button>
                `
                    : ""
                }
                ${
                  invoice.status === "overdue"
                    ? `
                    <button class="action-btn warning" onclick="window.sendInvoiceReminder('${invoice.id}')" title="Send Reminder">
                        <i class="ph ph-bell"></i>
                    </button>
                `
                    : ""
                }
            </td>
        </tr>
    `,
    )
    .join("");
}

export function updatePagination(
  page,
  totalPages,
  totalItems,
  type = "payments",
) {
  const info =
    type === "payments" ? DOM.pageInfoPayments() : DOM.pageInfoInvoices();
  const prev =
    type === "payments" ? DOM.prevPagePayments() : DOM.prevPageInvoices();
  const next =
    type === "payments" ? DOM.nextPagePayments() : DOM.nextPageInvoices();

  if (info)
    info.textContent = `Page ${page} of ${Math.max(1, totalPages)} (${totalItems} items)`;
  if (prev) {
    prev.disabled = page <= 1;
    prev.style.opacity = page <= 1 ? "0.5" : "1";
  }
  if (next) {
    const isLast = page >= totalPages || totalPages === 0;
    next.disabled = isLast;
    next.style.opacity = isLast ? "0.5" : "1";
  }
}
