// ============================================================
// shared/payments/formatters.js - Payment Formatters
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
      confirmed: "Confirmed",
      paid: "Paid",
      completed: "Completed",
      cancelled: "Cancelled",
      failed: "Failed",
      awaiting_confirmation: "Awaiting Confirmation",
      processing: "Processing",
      settled: "Settled",
      voided: "Voided",
      rejected: "Rejected",
    };
    return map[status] || status;
  },

  statusBadge: (status) => {
    const map = {
      pending: "pending",
      awaiting_confirmation: "pending",
      processing: "pending",
      confirmed: "confirmed",
      paid: "completed",
      completed: "completed",
      settled: "completed",
      cancelled: "cancelled",
      failed: "cancelled",
      voided: "cancelled",
      rejected: "cancelled",
    };
    return map[status] || status;
  },
};

export function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
