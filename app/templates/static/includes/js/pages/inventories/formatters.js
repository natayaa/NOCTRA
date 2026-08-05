// ============================================================
// inventories/formatters.js - Formatting Functions
// ============================================================

export const Formatter = {
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
    return new Date(dateString).toLocaleDateString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  },

  dateTime: (dateString) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  },

  stockStatus: (quantity, threshold) => {
    const qty = Number(quantity) || 0;
    const thresh = Number(threshold) || 5;

    if (qty <= 0)
      return { status: "out_of_stock", label: "Out of Stock", dot: "out" };
    if (qty <= thresh * 0.25)
      return { status: "critical", label: "Critical", dot: "critical" };
    if (qty <= thresh) return { status: "low", label: "Low Stock", dot: "low" };
    return { status: "normal", label: "Normal", dot: "normal" };
  },

  statusBadge: (status) => {
    const map = {
      active: "active",
      inactive: "inactive",
      out_of_stock: "out",
    };
    return map[status] || "inactive";
  },

  statusLabel: (status) => {
    const map = {
      active: "Active",
      inactive: "Inactive",
      out_of_stock: "Out of Stock",
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
