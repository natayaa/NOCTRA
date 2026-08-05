// ============================================================
// shared/formatters.js - Common Formatting Functions
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

  currencyShort: (amount) => {
    if (!amount && amount !== 0) return "Rp 0";
    const num = Number(amount);
    if (num >= 1_000_000) return `Rp ${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `Rp ${(num / 1_000).toFixed(0)}K`;
    return Formatter.currency(num);
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

  timeAgo: (dateString) => {
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
      return Formatter.date(dateString);
    } catch {
      return "-";
    }
  },

  // ---- Inquiry Status ----
  statusLabel: (status) => {
    const map = {
      new: "New",
      under_review: "Under Review",
      contacted: "Contacted",
      quoted: "Quoted",
      approved: "Approved",
      converted: "Converted",
      rejected: "Rejected",
      closed: "Closed",
      completed: "Completed",
      has_project: "Has Project",
      no_project: "No Project",
      project_completed: "Project Completed",
    };
    return map[status] || status || "Unknown";
  },

  statusBadgeClass: (status) => {
    const map = {
      new: "new",
      under_review: "under_review",
      contacted: "contacted",
      quoted: "quoted",
      approved: "approved",
      converted: "converted",
      rejected: "rejected",
      closed: "closed",
      completed: "completed",
      has_project: "has_project",
      no_project: "no_project",
      project_completed: "project_completed",
    };
    return map[status] || "new";
  },

  statusColor: (status) => {
    const map = {
      new: "#3b82f6",
      under_review: "#8b5cf6",
      contacted: "#0ea5e9",
      quoted: "#f59e0b",
      approved: "#10b981",
      converted: "#8b5cf6",
      rejected: "#ef4444",
      closed: "#6b7280",
      completed: "#10b981",
      has_project: "#3b82f6",
      no_project: "#94a3b8",
      project_completed: "#10b981",
    };
    return map[status] || "#94a3b8";
  },

  // ---- Priority ----
  priorityLabel: (priority) => {
    const map = {
      low: "Low",
      medium: "Medium",
      high: "High",
      urgent: "Urgent",
    };
    return map[priority] || priority || "Medium";
  },

  priorityBadgeClass: (priority) => {
    const map = {
      low: "low",
      medium: "medium",
      high: "high",
      urgent: "urgent",
    };
    return map[priority] || "medium";
  },

  priorityColor: (priority) => {
    const map = {
      low: "#94a3b8",
      medium: "#3b82f6",
      high: "#f59e0b",
      urgent: "#ef4444",
    };
    return map[priority] || "#94a3b8";
  },

  // ---- Project Status ----
  projectStatusLabel: (status) => {
    const map = {
      draft: "Draft",
      active: "Active",
      in_progress: "In Progress",
      on_hold: "On Hold",
      completed: "Completed",
      cancelled: "Cancelled",
      preparation: "Preparation",
      painting: "Painting",
      assembly: "Assembly",
    };
    return map[status] || status || "No Project";
  },

  projectStatusBadgeClass: (status) => {
    const map = {
      draft: "draft",
      active: "active",
      in_progress: "in_progress",
      on_hold: "on_hold",
      completed: "completed",
      cancelled: "cancelled",
      preparation: "preparation",
      painting: "painting",
      assembly: "assembly",
    };
    return map[status] || "no-project";
  },

  projectStatusColor: (status) => {
    const map = {
      draft: "#94a3b8",
      active: "#3b82f6",
      in_progress: "#f59e0b",
      on_hold: "#94a3b8",
      completed: "#10b981",
      cancelled: "#ef4444",
      preparation: "#8b5cf6",
      painting: "#f59e0b",
      assembly: "#3b82f6",
    };
    return map[status] || "#94a3b8";
  },

  // ---- Utils ----
  truncate: (text, length = 50) => {
    if (!text) return "";
    if (text.length <= length) return text;
    return text.substring(0, length) + "...";
  },

  capitalize: (text) => {
    if (!text) return "";
    return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
  },

  pluralize: (count, singular, plural = null) => {
    if (!plural) plural = singular + "s";
    return count === 1 ? singular : plural;
  },

  phone: (phone) => {
    if (!phone) return "-";
    const cleaned = phone.replace(/\D/g, "");
    if (cleaned.length >= 11) {
      return `${cleaned.substring(0, 4)}-${cleaned.substring(4, 8)}-${cleaned.substring(8)}`;
    }
    return phone;
  },

  number: (num, decimals = 0) => {
    if (!num && num !== 0) return "-";
    return new Intl.NumberFormat("id-ID", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(Number(num));
  },

  percentage: (value, total) => {
    if (!total || total === 0) return "0%";
    return ((value / total) * 100).toFixed(0) + "%";
  },

  getInitials: (name) => {
    if (!name) return "?";
    const parts = name.split(" ");
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (
      parts[0].charAt(0) + parts[parts.length - 1].charAt(0)
    ).toUpperCase();
  },

  getRandomColor: (seed) => {
    const colors = [
      "#3b82f6",
      "#10b981",
      "#f59e0b",
      "#ef4444",
      "#8b5cf6",
      "#ec4899",
      "#14b8a6",
      "#f97316",
      "#6366f1",
      "#84cc16",
      "#06b6d4",
      "#d946ef",
    ];
    if (!seed) return colors[0];
    const hash = seed
      .split("")
      .reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  },
};

// ---- Ekspor fungsi individual untuk kemudahan ----
export const {
  currency,
  date,
  dateTime,
  timeAgo,
  statusLabel,
  statusBadgeClass,
  statusColor,
  priorityLabel,
  priorityBadgeClass,
  priorityColor,
  projectStatusLabel,
  projectStatusBadgeClass,
  projectStatusColor,
  truncate,
  capitalize,
  pluralize,
  phone,
  number,
  percentage,
  getInitials,
  getRandomColor,
} = Formatter;

// ---- HTML escaping ----
export function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

export function safeHtml(text) {
  return escapeHtml(text);
}
