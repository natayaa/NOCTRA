// ============================================================
// inquiries/formatters.js - Formatting Functions
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

  statusBadge: (status) => {
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
    return map[status] || status;
  },

  projectStatusBadge: (status) => {
    const map = {
      preparation: "preparation",
      painting: "painting",
      assembly: "assembly",
      completed: "completed",
      active: "active",
      in_progress: "in_progress",
      draft: "draft",
    };
    return map[status] || "no-project";
  },
};

export function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
