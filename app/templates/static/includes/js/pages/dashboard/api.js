// ============================================================
// dashboard/api.js - API Calls (FIXED)
// ============================================================

import { CONFIG } from "./config.js";

// Helper fetch dengan error handling
async function apiFetch(endpoint, options = {}) {
  const url = `${CONFIG.API_BASE_URL}${endpoint}`;
  const config = {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      const errorMsg = data.message || data.detail || `HTTP ${response.status}`;
      const error = new Error(errorMsg);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data.data || data;
  } catch (error) {
    console.error("Dashboard API Error:", error);
    throw error;
  }
}

// ============================================================
// DASHBOARD API
// ============================================================

export const DashboardAPI = {
  // ===== STATISTICS =====
  getProjectStats: async () => {
    try {
      return await apiFetch("/projects/statistics");
    } catch (error) {
      console.warn("Failed to load project stats:", error.message);
      return null;
    }
  },

  getInquiryStats: async () => {
    try {
      return await apiFetch("/inquiries/statistics");
    } catch (error) {
      console.warn("Failed to load inquiry stats:", error.message);
      return null;
    }
  },

  getPaymentStats: async (startDate = null, endDate = null) => {
    try {
      const params = new URLSearchParams();
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      const query = params.toString() ? `?${params.toString()}` : "";
      return await apiFetch(`/payments/statistics${query}`);
    } catch (error) {
      console.warn("Failed to load payment stats:", error.message);
      return null;
    }
  },

  // Overdue invoices - gunakan endpoint yang valid
  getOverdueInvoices: async () => {
    try {
      const result = await apiFetch("/payments/invoices/overdue");
      return result || [];
    } catch (error) {
      console.warn("Failed to load overdue invoices:", error.message);
      return [];
    }
  },

  // Outstanding invoices
  getOutstandingInvoices: async () => {
    try {
      const result = await apiFetch("/payments/invoices/outstanding");
      return result || [];
    } catch (error) {
      console.warn("Failed to load outstanding invoices:", error.message);
      return [];
    }
  },

  getInventoryAlerts: async () => {
    try {
      const result = await apiFetch("/inventory/alerts");
      return result || [];
    } catch (error) {
      console.warn("Failed to load inventory alerts:", error.message);
      return [];
    }
  },

  // ===== RECENT DATA =====
  // Activities - gunakan endpoint activities dari inquiries dengan limit
  // Tapi tidak ada endpoint global, jadi kita bisa ambil dari beberapa inquiry terbaru
  // Untuk sementara kita gunakan data dari inquiries terbaru
  getRecentActivities: async (limit = 5) => {
    try {
      // Karena tidak ada endpoint global, kita ambil dari inquiries terbaru
      // dan ambil activities dari masing-masing inquiry secara terbatas
      // Atau kita bisa buat endpoint khusus di backend nanti
      // Untuk sekarang, kita return array kosong dengan pesan
      console.warn("Global activities endpoint not available, returning empty");
      return [];
    } catch (error) {
      console.warn("Failed to load recent activities:", error.message);
      return [];
    }
  },

  getRecentProjects: async (limit = 5) => {
    try {
      const result = await apiFetch(`/projects/?page=1&limit=${limit}`);
      return result.data || result.items || result || [];
    } catch (error) {
      console.warn("Failed to load recent projects:", error.message);
      return [];
    }
  },

  // Invoices - gunakan outstanding atau filter by status
  getRecentInvoices: async (limit = 5) => {
    try {
      // Gunakan outstanding invoices (yang belum lunas) untuk ditampilkan
      const result = await apiFetch(
        `/payments/invoices/outstanding?limit=${limit}`,
      );
      return result.data || result.items || result || [];
    } catch (error) {
      console.warn("Failed to load recent invoices:", error.message);
      return [];
    }
  },

  // ===== REVENUE TREND =====
  getRevenueTrend: async () => {
    try {
      const now = new Date();
      const sixMonthsAgo = new Date(now);
      sixMonthsAgo.setMonth(now.getMonth() - 6);
      const startDate = sixMonthsAgo.toISOString().split("T")[0];
      const endDate = now.toISOString().split("T")[0];

      const result = await apiFetch(
        `/payments/statistics?start_date=${startDate}&end_date=${endDate}`,
      );

      if (result && result.monthly_breakdown) {
        return result.monthly_breakdown;
      }
      return null;
    } catch (error) {
      console.warn("Failed to load revenue trend:", error.message);
      return null;
    }
  },
};
