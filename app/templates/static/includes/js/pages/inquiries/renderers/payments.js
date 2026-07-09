// ============================================================
// inquiries/renderers/payments.js - Payment Rendering (FIXED)
// ============================================================

import { DOM } from "../dom.js";
// ✅ PATH YANG BENAR: dari inquiries/renderers/ ke shared/payments/
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

  // Show loading state
  container.innerHTML = `
    <div style="text-align:center;padding:1rem 0;color:var(--text-muted);">
      <i class="ph ph-spinner" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;animation:spin 1s linear infinite;"></i>
      Loading payments...
    </div>
  `;

  try {
    const payments = await PaymentAPI.getByInquiry(inquiryId);
    console.log("🎨 Rendering payments for inquiry:", inquiryId, payments);

    if (!payments || payments.length === 0) {
      container.innerHTML = `
        <div style="text-align:center;padding:1rem 0;color:var(--text-muted);">
          <i class="ph ph-credit-card" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
          No payments recorded
        </div>
      `;
      if (totalDepositEl)
        totalDepositEl.textContent = PaymentFormatter.currency(0);
      if (totalPaidEl) totalPaidEl.textContent = PaymentFormatter.currency(0);
      if (totalPendingEl)
        totalPendingEl.textContent = PaymentFormatter.currency(0);
      if (remainingEl) {
        remainingEl.textContent = PaymentFormatter.currency(0);
        remainingEl.style.color = "var(--text-muted)";
      }
      return;
    }

    // ✅ FIX: Hitung summary dengan benar berdasarkan payment_type
    const summary = calculatePaymentSummary(payments);
    console.log("📊 Payment Summary:", summary);

    // ✅ Update summary cards
    if (totalDepositEl) {
      totalDepositEl.textContent = PaymentFormatter.currency(
        summary.totalDeposit,
      );
      totalDepositEl.style.color = "var(--text-primary)";
    }
    if (totalPaidEl) {
      totalPaidEl.textContent = PaymentFormatter.currency(summary.totalPaid);
      totalPaidEl.style.color = "#10b981";
    }
    if (totalPendingEl) {
      totalPendingEl.textContent = PaymentFormatter.currency(
        summary.totalPending,
      );
      totalPendingEl.style.color = "#f59e0b";
    }
    if (remainingEl) {
      const remainingAmount = summary.remaining > 0 ? summary.remaining : 0;
      remainingEl.textContent = PaymentFormatter.currency(remainingAmount);
      remainingEl.style.color = remainingAmount > 0 ? "#f59e0b" : "#10b981";
    }

    // ✅ Render payment history dengan type yang benar
    container.innerHTML = payments
      .map((p) => {
        const amount = Number(p.amount) || 0;

        // ✅ FIX: Gunakan payment_type atau type
        const type = p.payment_type || p.type || "Payment";
        const method = p.payment_method || p.method || "";
        const status = p.status || "pending";
        const reference = p.reference_number || p.reference || "";
        const date = p.paid_at || p.created_at || p.payment_date || "";

        // ✅ FIX: Tampilkan type dengan benar
        const typeLower = (type || "").toLowerCase();
        let typeIcon = "💳";
        let typeLabel = "Payment";
        if (typeLower === "deposit") {
          typeIcon = "🏦";
          typeLabel = "Deposit";
        } else if (typeLower === "refund") {
          typeIcon = "↩️";
          typeLabel = "Refund";
        } else if (typeLower === "installment") {
          typeIcon = "📊";
          typeLabel = "Installment";
        }

        // Status badge
        const statusLower = (status || "").toLowerCase();
        let statusIcon = "⏳";
        let statusLabel = "Pending";
        let statusColor = "#f59e0b";
        let statusBg = "rgba(245,158,11,0.12)";

        if (
          ["completed", "confirmed", "paid", "success", "settled"].includes(
            statusLower,
          )
        ) {
          statusIcon = "✅";
          statusLabel = "Completed";
          statusColor = "#10b981";
          statusBg = "rgba(16,185,129,0.12)";
        } else if (
          ["cancelled", "failed", "voided", "rejected"].includes(statusLower)
        ) {
          statusIcon = "❌";
          statusLabel = "Cancelled";
          statusColor = "#ef4444";
          statusBg = "rgba(239,68,68,0.12)";
        }

        const dateDisplay = date ? PaymentFormatter.dateTime(date) : "";

        return `
        <div class="payment-history-item" 
             style="display:flex;justify-content:space-between;align-items:center;
                    padding:0.6rem 0.75rem;border-bottom:1px solid var(--border);
                    border-left:3px solid ${statusColor};
                    background:${statusBg};
                    transition:background 0.2s ease;">
          <div style="display:flex;flex-direction:column;gap:0.1rem;flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
              <span style="font-size:0.9rem;">${typeIcon}</span>
              <span class="type" style="font-weight:600;color:var(--text-primary);font-size:0.85rem;">
                ${escapeHtml(typeLabel)}  <!-- ✅ Tampilkan label yang benar -->
              </span>
              <span style="font-size:0.6rem;color:${statusColor};font-weight:600;background:${statusBg};padding:0.1rem 0.5rem;border-radius:var(--radius-full);">
                ${statusIcon} ${statusLabel}
              </span>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:0.25rem 0.75rem;font-size:0.65rem;color:var(--text-muted);">
              ${dateDisplay ? `<span>📅 ${dateDisplay}</span>` : ""}
              ${method ? `<span>💳 ${escapeHtml(method)}</span>` : ""}
              ${reference ? `<span>📋 Ref: ${escapeHtml(reference)}</span>` : ""}
              ${p.id ? `<span>🆔 ${escapeHtml(p.id.substring(0, 8))}</span>` : ""}
            </div>
          </div>
          <div style="text-align:right;flex-shrink:0;margin-left:0.5rem;">
            <span style="font-weight:700;font-size:0.95rem;color:${statusColor};">
              ${PaymentFormatter.currency(amount)}
            </span>
          </div>
        </div>
      `;
      })
      .join("");

    // ✅ Total summary
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
        Failed to load payments
      </div>
    `;
  }
}
