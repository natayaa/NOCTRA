// ============================================================
// shared/payments/api.js - Payment API Services
// ============================================================

import { apiFetch } from "../../inquiries/api.js";

export const PaymentAPI = {
  // ✅ GET /api/api/payments/inquiry/{inquiry_id}
  getByInquiry: async (inquiryId) => {
    try {
      const response = await apiFetch(`/payments/inquiry/${inquiryId}`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to get payments:", error);
      return [];
    }
  },

  // ✅ CREATE payment - FIXED
  create: async (data) => {
    try {
      // ✅ Pastikan data valid
      const payload = {
        inquiry_id: data.inquiry_id,
        project_id: data.project_id || null,
        invoice_id: data.invoice_id || null,
        payment_type: data.payment_type || "payment",
        amount: parseFloat(data.amount) || 0,
        payment_method: data.payment_method || "bank_transfer",
        reference_number: data.reference_number || null,
        notes: data.notes || null,
        paid_at: data.paid_at || new Date().toISOString(),
        due_date: data.due_date || null,
        payment_proof: data.payment_proof || null,
      };

      console.log("📤 Sending payment payload:", payload);

      const response = await apiFetch("/payments/", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      return response.data || response;
    } catch (error) {
      console.error("Failed to create payment:", error);
      throw error;
    }
  },

  // ✅ POST /api/api/payments/deposit
  createDeposit: async (data) => {
    try {
      const response = await apiFetch("/payments/deposit", {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      console.error("Failed to create deposit:", error);
      throw error;
    }
  },

  // ✅ GET /api/api/payments/invoices/inquiry/{inquiry_id}
  getInvoicesByInquiry: async (inquiryId) => {
    try {
      const response = await apiFetch(
        `/payments/invoices/inquiry/${inquiryId}`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load invoices:", error);
      return [];
    }
  },

  // ✅ CREATE invoice
  createInvoice: async (data) => {
    try {
      const response = await apiFetch("/payments/invoices", {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      console.error("Failed to create invoice:", error);
      throw error;
    }
  },

  // ✅ GET /api/api/payments/invoices/generate-number
  generateInvoiceNumber: async () => {
    try {
      const response = await apiFetch("/payments/invoices/generate-number");
      return response.data || response;
    } catch (error) {
      console.error("Failed to generate invoice number:", error);
      return null;
    }
  },
};
