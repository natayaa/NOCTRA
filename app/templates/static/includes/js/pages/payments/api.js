// ============================================================
// shared/payments/api.js - Core Payment API
// Digunakan oleh semua module (Projects, Inquiries, Payments)
// ============================================================

// ============================================================
// Base API Helper
// ============================================================
const API_BASE_URL = "/api/api";

async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
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
      throw new Error(data.message || data.detail || `HTTP ${response.status}`);
    }
    return data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

// ============================================================
// PAYMENT API - CORE
// ============================================================
export const PaymentAPI = {
  // ============================================================
  // PAYMENTS ENDPOINTS
  // ============================================================

  // Create payment
  create: async (data) => {
    const response = await apiFetch("/payments/", {
      method: "POST",
      body: JSON.stringify(data),
    });
    return response.data || response;
  },

  // Create deposit
  createDeposit: async (data) => {
    const response = await apiFetch("/payments/deposit", {
      method: "POST",
      body: JSON.stringify(data),
    });
    return response.data || response;
  },

  // Get payments by inquiry
  getByInquiry: async (inquiryId) => {
    try {
      const response = await apiFetch(`/payments/inquiry/${inquiryId}`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load payments by inquiry:", error);
      return [];
    }
  },

  // Get payments by project
  getByProject: async (projectId) => {
    try {
      const response = await apiFetch(`/payments/project/${projectId}`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load payments by project:", error);
      return [];
    }
  },

  // Get payment detail
  getDetail: async (paymentId) => {
    const response = await apiFetch(`/payments/${paymentId}`);
    return response.data || response;
  },

  // Update payment
  update: async (paymentId, data) => {
    const response = await apiFetch(`/payments/${paymentId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
    return response.data || response;
  },

  // Confirm payment
  confirm: async (paymentId, confirmedBy, notes = "") => {
    const response = await apiFetch(`/payments/${paymentId}/confirm`, {
      method: "POST",
      body: JSON.stringify({ confirmed_by: confirmedBy, notes }),
    });
    return response.data || response;
  },

  // Cancel payment
  cancel: async (paymentId, reason = "") => {
    const response = await apiFetch(`/payments/${paymentId}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
    return response.data || response;
  },

  // Get financial summary for inquiry
  getFinancialSummary: async (inquiryId) => {
    try {
      const response = await apiFetch(
        `/payments/inquiry/${inquiryId}/financial-summary`,
      );
      return response.data || response;
    } catch (error) {
      console.error("Failed to load financial summary:", error);
      return null;
    }
  },

  // ============================================================
  // INVOICES ENDPOINTS
  // ============================================================

  // Create invoice
  createInvoice: async (data) => {
    const response = await apiFetch("/payments/invoices", {
      method: "POST",
      body: JSON.stringify(data),
    });
    return response.data || response;
  },

  // Generate invoice number
  generateInvoiceNumber: async () => {
    const response = await apiFetch("/payments/invoices/generate-number");
    return response.data || response;
  },

  // Get invoice detail
  getInvoice: async (invoiceId) => {
    const response = await apiFetch(`/payments/invoices/${invoiceId}`);
    return response.data || response;
  },

  // Update invoice
  updateInvoice: async (invoiceId, data) => {
    const response = await apiFetch(`/payments/invoices/${invoiceId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
    return response.data || response;
  },

  // Get invoices by inquiry
  getInvoicesByInquiry: async (inquiryId) => {
    try {
      const response = await apiFetch(
        `/payments/invoices/inquiry/${inquiryId}`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load invoices by inquiry:", error);
      return [];
    }
  },

  // Get invoices by project
  getInvoicesByProject: async (projectId) => {
    try {
      const response = await apiFetch(
        `/payments/invoices/project/${projectId}`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load invoices by project:", error);
      return [];
    }
  },

  // Get outstanding invoices
  getOutstandingInvoices: async () => {
    try {
      const response = await apiFetch("/payments/invoices/outstanding");
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load outstanding invoices:", error);
      return [];
    }
  },

  // Get overdue invoices
  getOverdueInvoices: async () => {
    try {
      const response = await apiFetch("/payments/invoices/overdue");
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load overdue invoices:", error);
      return [];
    }
  },

  // Send invoice
  sendInvoice: async (invoiceId) => {
    const response = await apiFetch(`/payments/invoices/${invoiceId}/send`, {
      method: "POST",
    });
    return response.data || response;
  },

  // Mark invoice as paid
  markInvoicePaid: async (invoiceId, data) => {
    const response = await apiFetch(
      `/payments/invoices/${invoiceId}/mark-paid`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    );
    return response.data || response;
  },

  // Send invoice reminder
  sendInvoiceReminder: async (invoiceId, note = "") => {
    const response = await apiFetch(
      `/payments/invoices/${invoiceId}/reminder`,
      {
        method: "POST",
        body: JSON.stringify({ note }),
      },
    );
    return response.data || response;
  },

  // Add invoice item
  addInvoiceItem: async (invoiceId, data) => {
    const response = await apiFetch(`/payments/invoices/${invoiceId}/items`, {
      method: "POST",
      body: JSON.stringify(data),
    });
    return response.data || response;
  },

  // Remove invoice item
  removeInvoiceItem: async (itemId) => {
    const response = await apiFetch(`/payments/invoices/items/${itemId}`, {
      method: "DELETE",
    });
    return response.data || response;
  },

  // ============================================================
  // STATISTICS ENDPOINTS
  // ============================================================

  // Get payment statistics
  getStatistics: async (startDate = null, endDate = null) => {
    try {
      const params = new URLSearchParams();
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);

      const response = await apiFetch(
        `/payments/statistics?${params.toString()}`,
      );
      return response.data || response;
    } catch (error) {
      console.error("Failed to load payment statistics:", error);
      return null;
    }
  },

  // Get invoice summary
  getInvoiceSummary: async () => {
    try {
      const response = await apiFetch("/payments/invoices/summary");
      return response.data || response;
    } catch (error) {
      console.error("Failed to load invoice summary:", error);
      return null;
    }
  },
};

export default PaymentAPI;
