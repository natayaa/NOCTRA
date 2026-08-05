// ============================================================
// billing/renderers/invoices.js
// ============================================================

import { DOM } from "../dom.js";
import {
  PaymentFormatter,
  escapeHtml,
} from "../../shared/payments/formatters.js";

export function renderInvoices(invoices) {
  const body = DOM.invoicesBody();
  if (!body) return;

  if (!invoices || invoices.length === 0) {
    body.innerHTML = `
      <tr>
        <td colspan="7" class="no-data">
          <i class="fas fa-file-invoice" style="display:block;font-size:1.5rem;margin-bottom:0.5rem;opacity:0.3;"></i>
          No invoices found
        </td>
      </tr>
    `;
    return;
  }

  body.innerHTML = invoices
    .map((inv) => {
      const status = inv.status || "draft";
      const total = inv.total_amount || inv.total || 0;
      const paid = inv.paid_amount || 0;
      const isOverdue = status === "overdue";

      return `
        <tr class="fade-in" data-id="${inv.id}">
          <td>
            <strong style="color:var(--text-primary);">${escapeHtml(inv.invoice_number || "N/A")}</strong>
          </td>
          <td>
            ${escapeHtml(inv.customer_name || inv.inquiry?.customer_name || "-")}
            ${inv.inquiry_id ? `<br><small style="color:var(--text-muted);">${escapeHtml(inv.inquiry_id.substring(0, 8))}</small>` : ""}
          </td>
          <td style="font-weight:600;color:var(--text-primary);">
            ${PaymentFormatter.currency(total)}
          </td>
          <td style="color:${paid > 0 ? "var(--success)" : "var(--text-muted)"};">
            ${PaymentFormatter.currency(paid)}
          </td>
          <td>
            <span class="status-badge ${status}">
              ${PaymentFormatter.invoiceStatusLabel(status)}
            </span>
          </td>
          <td style="font-size:0.8rem;${isOverdue ? "color:var(--danger);" : "color:var(--text-muted);"}">
            ${PaymentFormatter.date(inv.due_date)}
            ${isOverdue ? " ⚠️" : ""}
          </td>
          <td style="text-align:center;white-space:nowrap;">
            <button class="action-btn view" onclick="window.viewInvoiceDetail('${inv.id}')" title="View Details">
              <i class="fas fa-eye"></i>
            </button>
            ${
              status === "draft" || status === "sent"
                ? `
              <button class="action-btn send" onclick="window.sendInvoiceAction('${inv.id}')" title="Send Invoice">
                <i class="fas fa-paper-plane"></i>
              </button>
            `
                : ""
            }
            ${
              status === "sent" || status === "partial"
                ? `
              <button class="action-btn paid" onclick="window.markInvoicePaidAction('${inv.id}')" title="Mark as Paid">
                <i class="fas fa-check-circle"></i>
              </button>
            `
                : ""
            }
            ${
              status === "overdue"
                ? `
              <button class="action-btn reminder" onclick="window.sendInvoiceReminderAction('${inv.id}')" title="Send Reminder">
                <i class="fas fa-bell"></i>
              </button>
            `
                : ""
            }
            ${
              status === "draft"
                ? `
              <button class="action-btn delete" onclick="window.deleteInvoiceAction('${inv.id}')" title="Delete">
                <i class="fas fa-trash"></i>
              </button>
            `
                : ""
            }
          </td>
        </tr>
      `;
    })
    .join("");
}
