// static/js/shared/utils.js

/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
export function escapeHtml(text) {
  if (!text) return "";
  if (typeof text !== "string") return String(text);

  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, function (m) {
    return map[m];
  });
}

/**
 * Format currency for display
 * @param {number} amount - Amount to format
 * @param {string} currency - Currency code (default: IDR)
 * @returns {string} Formatted currency string
 */
export function formatCurrency(amount, currency = "IDR") {
  if (!amount && amount !== 0) return "Rp 0";

  const num = Number(amount);

  const symbols = {
    IDR: "Rp",
    USD: "$",
    EUR: "€",
    GBP: "£",
    JPY: "¥",
    SGD: "S$",
    MYR: "RM",
  };

  const symbol = symbols[currency] || "Rp";

  if (currency === "IDR") {
    return `${symbol} ${num.toLocaleString("id-ID")}`;
  }

  return `${symbol}${num.toFixed(2)}`;
}

/**
 * Format date for display
 * @param {string|Date} date - Date to format
 * @param {string} locale - Locale (default: id-ID)
 * @returns {string} Formatted date string
 */
export function formatDate(date, locale = "id-ID") {
  if (!date) return "-";
  try {
    const d = typeof date === "string" ? new Date(date) : date;
    return d.toLocaleDateString(locale, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "-";
  }
}

/**
 * Format datetime for display
 * @param {string|Date} date - Date to format
 * @param {string} locale - Locale (default: id-ID)
 * @returns {string} Formatted datetime string
 */
export function formatDateTime(date, locale = "id-ID") {
  if (!date) return "-";
  try {
    const d = typeof date === "string" ? new Date(date) : date;
    return d.toLocaleString(locale, {
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
 * Get time ago string (e.g. "2 hours ago")
 * @param {string|Date} date - Date to compare
 * @returns {string} Time ago string
 */
export function timeAgo(date) {
  if (!date) return "-";
  try {
    const now = new Date();
    const past = typeof date === "string" ? new Date(date) : date;
    const diffMs = now - past;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(date);
  } catch {
    return "-";
  }
}

/**
 * Truncate text to specified length
 * @param {string} text - Text to truncate
 * @param {number} length - Maximum length (default: 50)
 * @param {string} suffix - Suffix to add (default: ...)
 * @returns {string} Truncated text
 */
export function truncate(text, length = 50, suffix = "...") {
  if (!text) return "";
  if (text.length <= length) return text;
  return text.substring(0, length) + suffix;
}

/**
 * Capitalize first letter of each word
 * @param {string} text - Text to capitalize
 * @returns {string} Capitalized text
 */
export function capitalize(text) {
  if (!text) return "";
  return text
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Get initials from name
 * @param {string} name - Full name
 * @returns {string} Initials (max 2 characters)
 */
export function getInitials(name) {
  if (!name) return "?";
  const parts = name.trim().split(" ");
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/**
 * Get random color based on seed
 * @param {string} seed - Seed for consistent color
 * @returns {string} Hex color
 */
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
  const hash = String(seed)
    .split("")
    .reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

/**
 * Pluralize a word based on count
 * @param {number} count - Item count
 * @param {string} singular - Singular form
 * @param {string} plural - Plural form (optional)
 * @returns {string} Pluralized word
 */
export function pluralize(count, singular, plural = null) {
  if (!plural) plural = singular + "s";
  return count === 1 ? singular : plural;
}

/**
 * Debounce function for performance optimization
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(fn, delay = 300) {
  let timeoutId;
  return function (...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn.apply(this, args), delay);
  };
}

/**
 * Generate random ID (UUID v4 like)
 * @returns {string} Random ID
 */
export function generateId() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Safely parse JSON
 * @param {string} str - JSON string
 * @param {*} fallback - Fallback value if parsing fails
 * @returns {*} Parsed JSON or fallback
 */
export function safeJsonParse(str, fallback = null) {
  try {
    return JSON.parse(str);
  } catch {
    return fallback;
  }
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for older browsers
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
      document.body.removeChild(textarea);
      return true;
    } catch {
      document.body.removeChild(textarea);
      return false;
    }
  }
}

/**
 * Download file from blob
 * @param {Blob} blob - File blob
 * @param {string} filename - File name
 */
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} Valid email
 */
export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * Validate phone number format (Indonesian)
 * @param {string} phone - Phone number to validate
 * @returns {boolean} Valid phone number
 */
export function isValidPhone(phone) {
  const cleaned = phone.replace(/[^0-9+]/g, "");
  return /^(\+62|62|08)\d{8,13}$/.test(cleaned);
}

/**
 * Clean phone number (remove non-digits)
 * @param {string} phone - Phone number to clean
 * @returns {string} Cleaned phone number
 */
export function cleanPhone(phone) {
  if (!phone) return "";
  return phone.replace(/[^0-9]/g, "");
}

/**
 * Format phone number for display (Indonesian)
 * @param {string} phone - Phone number to format
 * @returns {string} Formatted phone number
 */
export function formatPhone(phone) {
  if (!phone) return "-";
  const cleaned = phone.replace(/\D/g, "");
  if (cleaned.length === 11) {
    return `${cleaned.substring(0, 4)}-${cleaned.substring(4, 8)}-${cleaned.substring(8)}`;
  }
  if (cleaned.length === 12) {
    return `${cleaned.substring(0, 4)}-${cleaned.substring(4, 8)}-${cleaned.substring(8)}`;
  }
  if (cleaned.length === 13) {
    return `${cleaned.substring(0, 4)}-${cleaned.substring(4, 8)}-${cleaned.substring(8, 12)}`;
  }
  return phone;
}

/**
 * Format number with thousand separators
 * @param {number} num - Number to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted number
 */
export function formatNumber(num, decimals = 0) {
  if (!num && num !== 0) return "0";
  return Number(num).toLocaleString("id-ID", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format percentage
 * @param {number} value - Value
 * @param {number} total - Total
 * @param {number} decimals - Decimal places
 * @returns {string} Formatted percentage
 */
export function formatPercentage(value, total, decimals = 0) {
  if (!total || total === 0) return "0%";
  return ((value / total) * 100).toFixed(decimals) + "%";
}

/**
 * Get status color from status string
 * @param {string} status - Status string
 * @returns {string} Color hex
 */
export function getStatusColor(status) {
  const colors = {
    new: "#3b82f6",
    under_review: "#8b5cf6",
    contacted: "#0ea5e9",
    quoted: "#f59e0b",
    approved: "#10b981",
    converted: "#10b981",
    rejected: "#ef4444",
    closed: "#6b7280",
    completed: "#00d578",
    pending: "#f59e0b",
    paid: "#10b981",
    cancelled: "#ef4444",
    active: "#3b82f6",
    in_progress: "#f59e0b",
    on_hold: "#6b7280",
    draft: "#94a3b8",
    preparation: "#8b5cf6",
    painting: "#f59e0b",
    assembly: "#3b82f6",
  };
  return colors[status] || "#94a3b8";
}

/**
 * Get status label from status string
 * @param {string} status - Status string
 * @returns {string} Status label
 */
export function getStatusLabel(status) {
  const labels = {
    new: "New",
    under_review: "Under Review",
    contacted: "Contacted",
    quoted: "Quoted",
    approved: "Approved",
    converted: "Converted",
    rejected: "Rejected",
    closed: "Closed",
    completed: "Completed",
    pending: "Pending",
    paid: "Paid",
    cancelled: "Cancelled",
    active: "Active",
    in_progress: "In Progress",
    on_hold: "On Hold",
    draft: "Draft",
    preparation: "Preparation",
    painting: "Painting",
    assembly: "Assembly",
  };
  return labels[status] || status || "Unknown";
}

/**
 * Deep clone an object
 * @param {*} obj - Object to clone
 * @returns {*} Cloned object
 */
export function deepClone(obj) {
  if (obj === null || typeof obj !== "object") return obj;
  if (obj instanceof Date) return new Date(obj);
  if (obj instanceof Array) return obj.map((item) => deepClone(item));
  if (obj instanceof Object) {
    const cloned = {};
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        cloned[key] = deepClone(obj[key]);
      }
    }
    return cloned;
  }
  return obj;
}

/**
 * Check if object is empty
 * @param {Object} obj - Object to check
 * @returns {boolean} Is empty
 */
export function isEmpty(obj) {
  if (!obj) return true;
  if (Array.isArray(obj)) return obj.length === 0;
  if (typeof obj === "object") return Object.keys(obj).length === 0;
  return false;
}

/**
 * Group array by key
 * @param {Array} array - Array to group
 * @param {string} key - Key to group by
 * @returns {Object} Grouped object
 */
export function groupBy(array, key) {
  if (!array || !Array.isArray(array)) return {};
  return array.reduce((result, item) => {
    const groupKey = item[key] || "undefined";
    if (!result[groupKey]) {
      result[groupKey] = [];
    }
    result[groupKey].push(item);
    return result;
  }, {});
}

// ============================================================
// EXPORT ALL FUNCTIONS
// ============================================================

export default {
  escapeHtml,
  formatCurrency,
  formatDate,
  formatDateTime,
  timeAgo,
  truncate,
  capitalize,
  getInitials,
  getRandomColor,
  pluralize,
  debounce,
  generateId,
  safeJsonParse,
  copyToClipboard,
  downloadBlob,
  isValidEmail,
  isValidPhone,
  cleanPhone,
  formatPhone,
  formatNumber,
  formatPercentage,
  getStatusColor,
  getStatusLabel,
  deepClone,
  isEmpty,
  groupBy,
};
