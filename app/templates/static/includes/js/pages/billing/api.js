// ============================================================
// billing/api.js - API Wrapper
// ============================================================

import { CONFIG } from "./config.js";
import { InquiryAPI } from "../../pages/inquiries/api.js";
import { PaymentAPI } from "../../pages/shared/payments/api.js";

// Re-export for convenience
export { InquiryAPI, PaymentAPI };

// Helper untuk fetch data dengan error handling
export async function apiFetch(endpoint, options = {}) {
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
      throw new Error(data.message || data.detail || `HTTP ${response.status}`);
    }
    return data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

// Additional Billing-specific API calls
export const BillingAPI = {
  // Generate invoice number (wrapper)
  generateInvoiceNumber: async () => {
    return await PaymentAPI.generateInvoiceNumber();
  },

  // Send invoice (wrapper)
  sendInvoice: async (invoiceId) => {
    return await PaymentAPI.sendInvoice(invoiceId);
  },

  // Mark invoice as paid (wrapper)
  markInvoicePaid: async (invoiceId, data = {}) => {
    return await PaymentAPI.markInvoicePaid(invoiceId, {
      payment_method: data.payment_method || "manual",
      notes: data.notes || "Marked as paid from Billing page",
    });
  },

  // Cancel/Delete invoice (draft only)
  deleteInvoice: async (invoiceId) => {
    // Use update to change status to cancelled
    return await PaymentAPI.updateInvoice(invoiceId, {
      status: "cancelled",
    });
  },

  // Send reminder
  sendInvoiceReminder: async (invoiceId, note = "") => {
    return await PaymentAPI.sendInvoiceReminder(invoiceId, note);
  },
};
