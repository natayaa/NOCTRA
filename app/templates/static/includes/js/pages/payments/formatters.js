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

  paymentStatusBadge: (status) => {
    const map = {
      pending: "pending",
      completed: "completed",
      confirmed: "confirmed",
      cancelled: "cancelled",
      failed: "failed",
      paid: "completed",
      success: "completed",
    };
    return map[status] || "pending";
  },

  paymentStatusLabel: (status) => {
    const map = {
      pending: "Pending",
      completed: "Completed",
      confirmed: "Confirmed",
      cancelled: "Cancelled",
      failed: "Failed",
      paid: "Paid",
      success: "Success",
    };
    return map[status] || status;
  },

  invoiceStatusBadge: (status) => {
    const map = {
      draft: "draft",
      sent: "sent",
      paid: "paid",
      overdue: "overdue",
      cancelled: "cancelled",
    };
    return map[status] || "draft";
  },

  invoiceStatusLabel: (status) => {
    const map = {
      draft: "Draft",
      sent: "Sent",
      paid: "Paid",
      overdue: "Overdue",
      cancelled: "Cancelled",
    };
    return map[status] || status;
  },

  paymentTypeLabel: (type) => {
    const map = {
      deposit: "Deposit",
      payment: "Payment",
      refund: "Refund",
      installment: "Installment",
    };
    return map[type] || type;
  },
};

export function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
