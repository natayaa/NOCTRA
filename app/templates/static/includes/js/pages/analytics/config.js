// static/js/pages/analytics/config.js
// ============================================================
// Analytics Configuration
// ============================================================

export const CONFIG = {
  // API
  API_BASE_URL: "/api",

  // Toast
  TOAST_DURATION: 4000,

  // Chart colors
  CHART_COLORS: {
    primary: "#ff6b00",
    primaryLight: "rgba(255, 107, 0, 0.1)",
    success: "#00d578",
    successLight: "rgba(0, 213, 120, 0.1)",
    danger: "#ef4444",
    dangerLight: "rgba(239, 68, 68, 0.1)",
    warning: "#f59e0b",
    warningLight: "rgba(245, 158, 11, 0.1)",
    info: "#3b82f6",
    infoLight: "rgba(59, 130, 246, 0.1)",
    purple: "#8b5cf6",
    purpleLight: "rgba(139, 92, 246, 0.1)",
    teal: "#14b8a6",
    tealLight: "rgba(20, 184, 166, 0.1)",
    pink: "#ec4899",
    pinkLight: "rgba(236, 72, 153, 0.1)",
    gray: "#94a3b8",
    grayLight: "rgba(148, 163, 184, 0.1)",
  },

  STATUS_COLORS: {
    draft: "#94a3b8",
    active: "#3b82f6",
    in_progress: "#f59e0b",
    on_hold: "#94a3b8",
    completed: "#00d578",
    cancelled: "#ef4444",
  },

  PERIOD_OPTIONS: [
    { value: "today", label: "Today" },
    { value: "week", label: "This Week" },
    { value: "month", label: "This Month" },
    { value: "quarter", label: "Last 3 Months" },
    { value: "year", label: "This Year" },
    { value: "custom", label: "Custom Range" },
  ],

  EXPENSE_CATEGORIES: [
    { value: "materials", label: "Materials" },
    { value: "labor", label: "Labor" },
    { value: "equipment", label: "Equipment" },
    { value: "rental", label: "Rental" },
    { value: "transportation", label: "Transportation" },
    { value: "utilities", label: "Utilities" },
    { value: "other", label: "Other" },
  ],

  CHART_PERIODS: ["week", "month", "year"],
  MAX_EXPENSES_DISPLAY: 100,
  MAX_PROFITABILITY_DISPLAY: 50,
};

export default CONFIG;
