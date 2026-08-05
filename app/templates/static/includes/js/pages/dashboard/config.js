// ============================================================
// dashboard/config.js - State & Konfigurasi
// ============================================================

export const CONFIG = {
  API_BASE_URL: "/api/api",
  RECENT_LIMIT: 5,
  TOAST_DURATION: 4000,
};

export const state = {
  // Stats
  stats: {
    revenue: 0,
    activeProjects: 0,
    inProduction: 0,
    pendingInquiries: 0,
    overdueInvoices: 0,
    lowStockItems: 0,
    completedProjects: 0,
    quotesSent: 0,
    totalCustomers: 0,
  },

  // Chart data
  revenueTrend: {
    labels: [],
    values: [],
  },
  projectStatus: {
    labels: [],
    values: [],
  },

  // Recent data
  recentActivities: [],
  recentProjects: [],
  recentInvoices: [],

  isLoading: false,
  lastRefresh: null,
};

// Chart instances (untuk destroy/recreate)
export let revenueChartInstance = null;
export let projectStatusChartInstance = null;
