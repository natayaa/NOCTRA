// ============================================================
// billing/renderers/quotations.js
// ============================================================

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../../../shared/formatters.js";

export function renderQuotations(quotations) {
  const body = DOM.quotationsBody();
  if (!body) return;

  if (!quotations || quotations.length === 0) {
    body.innerHTML = `
      <tr>
        <td colspan="6" class="no-data">
          <i class="fas fa-file-signature" style="display:block;font-size:1.5rem;margin-bottom:0.5rem;opacity:0.3;"></i>
          No quotations found
        </td>
      </tr>
    `;
    return;
  }

  body.innerHTML = quotations
    .map((quote) => {
      const status = quote.status || "quoted";
      const statusClass = status === "approved" ? "approved" : status;
      const estCost = quote.estimated_cost || 0;

      return `
        <tr class="fade-in" data-id="${quote.id}">
          <td>
            <strong style="color:var(--text-primary);">${escapeHtml(quote.customer_name || "Unknown")}</strong>
            ${quote.customer_phone_number ? `<br><small style="color:var(--text-muted);">${escapeHtml(quote.customer_phone_number)}</small>` : ""}
          </td>
          <td>
            ${escapeHtml(quote.vehicle_brand || "-")}
            ${quote.vehicle_model ? `<br><small style="color:var(--text-muted);">${escapeHtml(quote.vehicle_model)}</small>` : ""}
          </td>
          <td style="font-weight:600;color:var(--text-primary);">
            ${Formatter.currency(estCost)}
          </td>
          <td>
            <span class="status-badge ${statusClass}">
              ${Formatter.statusLabel(status)}
            </span>
          </td>
          <td style="font-size:0.8rem;color:var(--text-muted);">
            ${Formatter.date(quote.created_at)}
          </td>
          <td style="text-align:center;white-space:nowrap;">
            <button class="action-btn view" onclick="window.viewQuotation('${quote.id}')" title="View Details">
              <i class="fas fa-eye"></i>
            </button>
            ${
              status === "approved"
                ? `
              <button class="action-btn convert" onclick="window.convertQuoteToInvoice('${quote.id}')" title="Convert to Invoice">
                <i class="fas fa-file-invoice"></i>
              </button>
            `
                : ""
            }
            ${
              status === "quoted"
                ? `
              <button class="action-btn edit" onclick="window.resendQuote('${quote.id}')" title="Resend Quote">
                <i class="fas fa-paper-plane"></i>
              </button>
              <button class="action-btn delete" onclick="window.rejectQuote('${quote.id}')" title="Reject">
                <i class="fas fa-times"></i>
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
