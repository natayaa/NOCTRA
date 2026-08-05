// ============================================================
// price_list/formatters.js - Formatting Functions
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

  categoryBadgeClass: (category) => {
    const map = {
      service: "service",
      material: "material",
      labor: "labor",
      bike_model: "bike_model",
      paint: "paint",
      finish: "finish",
      accessory: "accessory",
    };
    return map[category] || "";
  },

  categoryLabel: (category) => {
    const map = {
      service: "Service",
      material: "Material",
      labor: "Labor",
      bike_model: "Bike Model",
      paint: "Paint",
      finish: "Finish",
      accessory: "Accessory",
    };
    return map[category] || category;
  },

  statusLabel: (status) => {
    return status === "active" ? "Active" : "Inactive";
  },
};

export function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
