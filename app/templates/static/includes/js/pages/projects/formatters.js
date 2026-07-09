// ============================================================
// projects/formatters.js - Formatting Functions
// ============================================================

export const Formatter = {
  currency: (amount) => {
    if (!amount && amount !== 0) return "-";
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

  // === STATUS BADGE FUNCTIONS ===
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
};

// ✅ EKSPOR FUNGSI TERPISAH (untuk import seperti di overview.js)
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
