// ============================================================
// shared/payments/formatters.js - Payment Formatters (FIXED)
// ============================================================

export const PaymentFormatter = {
  currency: (amount) => {
    if (!amount && amount !== 0) return "Rp 0";
    return new Intl.NumberFormat("id-ID", {
      style: "currency",
      currency: "IDR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(Number(amount));
  },

  date: (dateString) => {
    if (!dateString) return "-";
    try {
      return new Date(dateString).toLocaleDateString("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return "-";
    }
  },

  dateTime: (dateString) => {
    if (!dateString) return "-";
    try {
      return new Date(dateString).toLocaleString("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "-";
    }
  },

  statusLabel: (status) => {
    const map = {
      pending: "Pending",
      awaiting_confirmation: "Awaiting Confirmation",
      processing: "Processing",
      confirmed: "Confirmed",
      paid: "Paid",
      completed: "Completed",
      settled: "Settled",
      cancelled: "Cancelled",
      failed: "Failed",
      voided: "Voided",
      rejected: "Rejected",
      draft: "Draft",
      sent: "Sent",
      viewed: "Viewed",
      partial: "Partial",
      overdue: "Overdue",
      refunded: "Refunded",
    };
    return map[status] || status || "Unknown";
  },

  statusColor: (status) => {
    const map = {
      pending: "#f59e0b",
      awaiting_confirmation: "#f59e0b",
      processing: "#f59e0b",
      confirmed: "#3b82f6",
      paid: "#10b981",
      completed: "#10b981",
      settled: "#10b981",
      cancelled: "#ef4444",
      failed: "#ef4444",
      voided: "#ef4444",
      rejected: "#ef4444",
      draft: "#94a3b8",
      sent: "#3b82f6",
      viewed: "#3b82f6",
      partial: "#f59e0b",
      overdue: "#ef4444",
      refunded: "#94a3b8",
    };
    return map[status] || "#94a3b8";
  },

  statusIcon: (status) => {
    const map = {
      pending: "⏳",
      awaiting_confirmation: "⏳",
      processing: "⏳",
      confirmed: "✅",
      paid: "✅",
      completed: "✅",
      settled: "✅",
      cancelled: "❌",
      failed: "❌",
      voided: "❌",
      rejected: "❌",
      draft: "📄",
      sent: "📨",
      viewed: "👁️",
      partial: "💰",
      overdue: "⚠️",
      refunded: "↩️",
    };
    return map[status] || "📄";
  },

  paymentTypeLabel: (type) => {
    const map = {
      deposit: "Deposit",
      payment: "Payment",
      refund: "Refund",
      installment: "Installment",
    };
    const key = (type || "").toLowerCase();
    return map[key] || type || "Payment";
  },

  paymentTypeIcon: (type) => {
    const map = {
      deposit: "🏦",
      payment: "💳",
      refund: "↩️",
      installment: "📊",
    };
    const key = (type || "").toLowerCase();
    return map[key] || "💳";
  },

  invoiceStatusBadgeClass: (status) => {
    const map = {
      draft: "draft",
      sent: "sent",
      viewed: "sent",
      partial: "partial",
      paid: "paid",
      overdue: "danger",
      cancelled: "cancelled",
      refunded: "cancelled",
    };
    return map[status] || "draft";
  },
};

export function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
