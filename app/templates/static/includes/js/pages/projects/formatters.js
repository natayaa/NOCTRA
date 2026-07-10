// projects/formatters.js (FIXED & IMPROVED)

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

  statusBadge: (status) => {
    const map = {
      draft: "draft",
      active: "active",
      in_progress: "in_progress",
      on_hold: "on_hold",
      completed: "completed",
      cancelled: "cancelled",
    };
    return map[status] || "draft";
  },

  priorityBadge: (priority) => {
    const map = {
      low: "low",
      medium: "medium",
      high: "high",
      urgent: "urgent",
    };
    return map[priority] || "medium";
  },

  statusLabel: (status) => {
    const map = {
      draft: "Draft",
      active: "Active",
      in_progress: "In Progress",
      on_hold: "On Hold",
      completed: "Completed",
      cancelled: "Cancelled",
    };
    return map[status] || status;
  },

  priorityLabel: (priority) => {
    const map = {
      low: "Low",
      medium: "Medium",
      high: "High",
      urgent: "Urgent",
    };
    return map[priority] || priority;
  },

  statusColor: (status) => {
    const map = {
      draft: "#94a3b8",
      active: "#3b82f6",
      in_progress: "#f59e0b",
      on_hold: "#94a3b8",
      completed: "#10b981",
      cancelled: "#ef4444",
    };
    return map[status] || "#94a3b8";
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

  progressColor: (progress) => {
    const p = Number(progress) || 0;
    if (p >= 100) return "#10b981";
    if (p >= 75) return "#3b82f6";
    if (p >= 50) return "#f59e0b";
    if (p >= 25) return "#f97316";
    return "#94a3b8";
  },

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
};

export function getStatusBadgeClass(status) {
  const map = {
    draft: "draft",
    active: "active",
    in_progress: "in_progress",
    on_hold: "on_hold",
    completed: "completed",
    cancelled: "cancelled",
  };
  return map[status] || "draft";
}

export function getPriorityBadgeClass(priority) {
  const map = {
    low: "low",
    medium: "medium",
    high: "high",
    urgent: "urgent",
  };
  return map[priority] || "medium";
}

export function getStatusLabel(status) {
  const map = {
    draft: "Draft",
    active: "Active",
    in_progress: "In Progress",
    on_hold: "On Hold",
    completed: "Completed",
    cancelled: "Cancelled",
  };
  return map[status] || status;
}

export function getPriorityLabel(priority) {
  const map = {
    low: "Low",
    medium: "Medium",
    high: "High",
    urgent: "Urgent",
  };
  return map[priority] || priority;
}

export function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

export function getInitials(name) {
  if (!name) return "?";
  const parts = name.split(" ");
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

export function getRandomColor(seed) {
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
}
