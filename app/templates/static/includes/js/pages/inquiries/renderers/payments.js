// inquiries/renderers/payments.js (FIXED)

import { DOM } from "../dom.js";
import { PaymentAPI } from "../../shared/payments/api.js";
import {
  PaymentFormatter,
  escapeHtml,
} from "../../shared/payments/formatters.js";
import { calculatePaymentSummary } from "../../shared/payments/utils.js";

export async function renderDrawerPayments(inquiryId) {
  const container = DOM.drawerPaymentHistory();
  const totalDepositEl = DOM.drawerTotalDeposit();
  const totalPaidEl = DOM.drawerTotalPaid();
  const totalPendingEl = DOM.drawerTotalPending();
  const remainingEl = DOM.drawerRemaining();

  if (!container) return;

  // Show loading
  container.innerHTML = `
    <div style="text-align:center;padding:1rem 0;color:var(--text-muted);">
      <i class="ph ph-spinner" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;animation:spin 1s linear infinite;"></i>
      Loading payments...
    </div>
  `;

  try {
    const payments = await PaymentAPI.getByInquiry(inquiryId);
    // console.log("🎨 Rendering payments:", payments);

    if (!payments || payments.length === 0) {
      container.innerHTML = `
        <div style="text-align:center;padding:1rem 0;color:var(--text-muted);">
          <i class="ph ph-credit-card" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
          No payments recorded
        </div>
      `;
      updateSummaryCards(
        totalDepositEl,
        totalPaidEl,
        totalPendingEl,
        remainingEl,
        null,
      );
      return;
    }

    const summary = calculatePaymentSummary(payments);
    //console.log("📊 Payment Summary:", summary);

    // Update summary cards
    updateSummaryCards(
      totalDepositEl,
      totalPaidEl,
      totalPendingEl,
      remainingEl,
      summary,
    );

    // ✅ Render payment history
    container.innerHTML = payments
      .map((p) => {
        const amount = Number(p.amount) || 0;
        const type = p.payment_type || p.type || "payment";
        const method = p.payment_method || p.method || "-";
        const status = p.status || "pending";
        const date = p.paid_at || p.created_at || "";

        const typeLabel = type === "deposit" ? "Deposit" : "Payment";
        const typeIcon = type === "deposit" ? "🏦" : "💳";

        let statusColor = "#f59e0b";
        let statusLabel = "Pending";
        let statusIcon = "⏳";
        let isPending = true;
        let isCompleted = false;

        if (["completed", "confirmed", "paid", "settled"].includes(status)) {
          statusColor = "#10b981";
          statusLabel = "Completed";
          statusIcon = "✅";
          isPending = false;
          isCompleted = true;
        } else if (["cancelled", "failed", "voided"].includes(status)) {
          statusColor = "#ef4444";
          statusLabel = "Cancelled";
          statusIcon = "❌";
          isPending = false;
          isCompleted = true;
        }

        const dateDisplay = date ? PaymentFormatter.dateTime(date) : "";

        // ✅ Show delete button only for pending payments
        const showDelete = isPending;

        return `
        <div class="payment-item" style="display:flex;justify-content:space-between;align-items:center;
                    padding:0.6rem 0.75rem;border-bottom:1px solid var(--border);
                    border-left:3px solid ${statusColor};
                    background:${isPending ? "rgba(245,158,11,0.04)" : "transparent"};
                    transition:background 0.2s ease;">
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
              <span style="font-weight:600;font-size:0.85rem;">
                ${typeIcon} ${escapeHtml(typeLabel)}
              </span>
              <span class="payment-status-badge" style="font-size:0.6rem;color:${statusColor};font-weight:600;
                          background:${statusColor}15;padding:0.1rem 0.5rem;
                          border-radius:var(--radius-full);">
                ${statusIcon} ${statusLabel}
              </span>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:0.25rem 0.75rem;font-size:0.65rem;color:var(--text-muted);margin-top:0.1rem;">
              ${dateDisplay ? `<span>📅 ${dateDisplay}</span>` : ""}
              ${method && method !== "-" ? `<span>💳 ${escapeHtml(method)}</span>` : ""}
              ${p.reference_number ? `<span>📋 Ref: ${escapeHtml(p.reference_number)}</span>` : ""}
              ${p.id ? `<span>🆔 ${escapeHtml(p.id.substring(0, 8))}</span>` : ""}
            </div>
          </div>
          <div style="text-align:right;flex-shrink:0;margin-left:0.5rem;display:flex;flex-direction:column;align-items:flex-end;gap:0.25rem;">
            <span style="font-weight:700;font-size:0.95rem;color:${statusColor};">
              ${PaymentFormatter.currency(amount)}
            </span>
            <div style="display:flex;gap:0.25rem;">
              ${
                isPending
                  ? `
                <button onclick="event.stopPropagation(); window.openConfirmPaymentModal('${p.id}')" 
                        class="btn-confirm-payment"
                        style="font-size:0.6rem;padding:0.15rem 0.5rem;background:#10b981;color:white;border:none;border-radius:var(--radius-sm);cursor:pointer;display:flex;align-items:center;gap:0.15rem;">
                  <i class="ph ph-check" style="font-size:0.7rem;"></i> Confirm
                </button>
              `
                  : ""
              }
              ${
                showDelete
                  ? `
                <button onclick="event.stopPropagation(); window.openDeletePaymentModal('${p.id}')" 
                        class="btn-delete-payment"
                        style="font-size:0.6rem;padding:0.15rem 0.5rem;background:transparent;color:var(--text-muted);border:1px solid var(--border);border-radius:var(--radius-sm);cursor:pointer;display:flex;align-items:center;gap:0.15rem;">
                  <i class="ph ph-trash" style="font-size:0.7rem;"></i>
                </button>
              `
                  : ""
              }
            </div>
          </div>
        </div>
      `;
      })
      .join("");

    // Total summary
    if (summary.totalAll > 0) {
      container.innerHTML += `
        <div style="display:flex;justify-content:space-between;padding:0.6rem 0.75rem;margin-top:0.5rem;
                    border-top:2px solid var(--border);font-weight:600;color:var(--text-primary);
                    background:var(--bg-input);border-radius:var(--radius-sm);font-size:0.85rem;">
          <span>Total All Payments</span>
          <span>${PaymentFormatter.currency(summary.totalAll)}</span>
        </div>
      `;
    }
  } catch (error) {
    console.error("Failed to render payments:", error);
    container.innerHTML = `
      <div style="text-align:center;padding:1rem 0;color:#ef4444;">
        <i class="ph ph-warning" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
        Failed to load payments: ${error.message}
      </div>
    `;
  }
}

function updateSummaryCards(
  totalDepositEl,
  totalPaidEl,
  totalPendingEl,
  remainingEl,
  summary,
) {
  if (!summary) {
    if (totalDepositEl) totalDepositEl.textContent = "Rp 0";
    if (totalPaidEl) totalPaidEl.textContent = "Rp 0";
    if (totalPendingEl) totalPendingEl.textContent = "Rp 0";
    if (remainingEl) remainingEl.textContent = "Rp 0";
    return;
  }

  if (totalDepositEl) {
    totalDepositEl.textContent = PaymentFormatter.currency(
      summary.totalDeposit,
    );
    totalDepositEl.style.color =
      summary.totalDeposit > 0 ? "#10b981" : "var(--text-muted)";
  }
  if (totalPaidEl) {
    totalPaidEl.textContent = PaymentFormatter.currency(summary.totalPaid);
    totalPaidEl.style.color =
      summary.totalPaid > 0 ? "#10b981" : "var(--text-muted)";
  }
  if (totalPendingEl) {
    totalPendingEl.textContent = PaymentFormatter.currency(
      summary.totalPending,
    );
    totalPendingEl.style.color =
      summary.totalPending > 0 ? "#f59e0b" : "var(--text-muted)";
  }
  if (remainingEl) {
    const remaining =
      summary.totalAll - summary.totalPaid - summary.totalDeposit;
    const displayRemaining = remaining > 0 ? remaining : 0;
    remainingEl.textContent = PaymentFormatter.currency(displayRemaining);
    remainingEl.style.color = displayRemaining > 0 ? "#ef4444" : "#10b981";
  }
}
