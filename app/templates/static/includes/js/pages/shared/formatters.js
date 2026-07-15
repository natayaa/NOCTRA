// ============================================================
// shared/formatters.js - Universal Formatting Functions
// ============================================================

/**
 * Currency formatter for IDR
 */
export function formatCurrency(amount) {
  if (!amount && amount !== 0) return "Rp 0";
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Number(amount));
}

/**
 * Short currency (Rp 1.2M, Rp 500K, etc)
 */
export function formatCurrencyShort(amount) {
  if (!amount && amount !== 0) return "Rp 0";
  const num = Number(amount);
  if (num >= 1_000_000) return `Rp ${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `Rp ${(num / 1_000).toFixed(0)}K`;
  return formatCurrency(num);
}

/**
 * Date formatter (dd MMM yyyy)
 */
export function formatDate(dateString) {
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
}

/**
 * Date time formatter (dd MMM yyyy, HH:mm)
 */
export function formatDateTime(dateString) {
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
}

/**
 * Time ago (just now, 5m ago, 2h ago, 3d ago)
 */
export function formatTimeAgo(dateString) {
  if (!dateString) return "-";
  try {
    const now = new Date();
    const past = new Date(dateString);
    const diffMs = now - past;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(dateString);
  } catch {
    return "-";
  }
}

/**
 * Number formatter with thousand separators
 */
export function formatNumber(num, decimals = 0) {
  if (num === undefined || num === null) return "-";
  return new Intl.NumberFormat("id-ID", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Number(num));
}

/**
 * Percentage formatter
 */
export function formatPercentage(value, total) {
  if (!total || total === 0) return "0%";
  return ((value / total) * 100).toFixed(0) + "%";
}

/**
 * Phone number formatter (0812-3456-7890)
 */
export function formatPhone(phone) {
  if (!phone) return "-";
  const cleaned = phone.replace(/\D/g, "");
  if (cleaned.length >= 11) {
    return `${cleaned.substring(0, 4)}-${cleaned.substring(4, 8)}-${cleaned.substring(8)}`;
  }
  return phone;
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(text, length = 50) {
  if (!text) return "";
  if (text.length <= length) return text;
  return text.substring(0, length) + "...";
}

/**
 * Capitalize first letter
 */
export function capitalize(text) {
  if (!text) return "";
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
}

/**
 * Get initials from name
 */
export function getInitials(name) {
  if (!name) return "?";
  const parts = name.trim().split(" ");
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/**
 * Escape HTML to prevent XSS
 */
export function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Pluralize a word based on count
 */
export function pluralize(count, singular, plural = null) {
  if (!plural) plural = singular + "s";
  return count === 1 ? singular : plural;
}

/**
 * Get status color for various statuses
 */
export function getStatusColor(status) {
  const map = {
    // Inquiry status
    new: "#3b82f6",
    under_review: "#6366f1",
    contacted: "#0ea5e9",
    quoted: "#f59e0b",
    approved: "#10b981",
    converted: "#8b5cf6",
    rejected: "#ef4444",
    closed: "#6b7280",
    completed: "#00d578",

    // Project status
    draft: "#94a3b8",
    active: "#3b82f6",
    in_progress: "#f59e0b",
    on_hold: "#94a3b8",
    cancelled: "#ef4444",

    // Invoice status
    sent: "#3b82f6",
    paid: "#10b981",
    overdue: "#ef4444",
    draft: "#94a3b8",
    partial: "#f59e0b",
  };
  return map[status] || "#94a3b8";
}

/**
 * Get status label for various statuses
 */
export function getStatusLabel(status) {
  const map = {
    // Inquiry
    new: "New",
    under_review: "Under Review",
    contacted: "Contacted",
    quoted: "Quoted",
    approved: "Approved",
    converted: "Converted",
    rejected: "Rejected",
    closed: "Closed",
    completed: "Completed",
    // Project
    draft: "Draft",
    active: "Active",
    in_progress: "In Progress",
    on_hold: "On Hold",
    cancelled: "Cancelled",
    // Invoice
    sent: "Sent",
    paid: "Paid",
    overdue: "Overdue",
    partial: "Partial",
  };
  return map[status] || status;
}

/**
 * Get badge class for status (for CSS)
 */
export function getStatusBadgeClass(status) {
  const map = {
    // Inquiry
    new: "new",
    under_review: "under_review",
    contacted: "contacted",
    quoted: "quoted",
    approved: "approved",
    converted: "converted",
    rejected: "rejected",
    closed: "closed",
    completed: "completed",
    // Project
    draft: "draft",
    active: "active",
    in_progress: "in_progress",
    on_hold: "on_hold",
    cancelled: "cancelled",
    // Invoice
    sent: "sent",
    paid: "paid",
    overdue: "overdue",
    partial: "partial",
  };
  return map[status] || "draft";
}

/**
 * Get priority label
 */
export function getPriorityLabel(priority) {
  const map = {
    low: "Low",
    medium: "Medium",
    high: "High",
    urgent: "Urgent",
  };
  return map[priority] || priority;
}

/**
 * Get priority color
 */
export function getPriorityColor(priority) {
  const map = {
    low: "#94a3b8",
    medium: "#3b82f6",
    high: "#f59e0b",
    urgent: "#ef4444",
  };
  return map[priority] || "#94a3b8";
}

// ============================================================
// EXPORT ALL AS FORMATTER (for backward compatibility)
// ============================================================

export const Formatter = {
  currency: formatCurrency,
  currencyShort: formatCurrencyShort,
  date: formatDate,
  dateTime: formatDateTime,
  timeAgo: formatTimeAgo,
  number: formatNumber,
  percentage: formatPercentage,
  phone: formatPhone,
  truncate: truncateText,
  capitalize: capitalize,
  pluralize: pluralize,
  getInitials,
  escapeHtml,
  getStatusColor,
  getStatusLabel,
  getStatusBadgeClass,
  getPriorityLabel,
  getPriorityColor,
};

export default Formatter;
