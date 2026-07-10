// shared/payments/api.js

// ✅ Gunakan API_BASE_URL dari config atau langsung
const API_BASE_URL = "/api/api";

// ✅ Base API fetch - independen dari module lain

async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : "/" + endpoint}`;
  // console.log("🌐 [PaymentAPI] Fetching:", url);

  const config = {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);

    // ✅ Coba parse response
    let data;
    const text = await response.text();
    try {
      data = JSON.parse(text);
    } catch (e) {
      // Jika bukan JSON, gunakan text
      data = { message: text || `HTTP ${response.status}` };
    }

    // console.log("📦 [PaymentAPI] Response:", { status: response.status, data });

    if (!response.ok) {
      // ✅ Format error dengan benar
      const errorMsg =
        data.detail || data.message || data.error || `HTTP ${response.status}`;
      const error = new Error(errorMsg);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  } catch (error) {
    // ✅ Pastikan error selalu string
    if (error instanceof Error) {
      console.error("❌ [PaymentAPI] Error:", error.message);
      throw error;
    }
    // Jika error bukan Error object
    const errorMsg = typeof error === "string" ? error : JSON.stringify(error);
    console.error("❌ [PaymentAPI] Error:", errorMsg);
    throw new Error(errorMsg);
  }
}

export const PaymentAPI = {
  // ============================================================
  // PAYMENTS
  // ============================================================

  // ✅ GET /api/payments/
  getAll: async (params = {}) => {
    try {
      const query = new URLSearchParams(params).toString();
      const response = await apiFetch(`/payments/?${query}`);
      return response.data || response;
    } catch (error) {
      console.error("Failed to fetch payments:", error);
      return null;
    }
  },

  // ✅ GET /api/payments/{payment_id}
  getById: async (paymentId) => {
    try {
      if (!paymentId) return null;
      const response = await apiFetch(`/payments/${paymentId}`);
      return response.data || response;
    } catch (error) {
      console.error("Failed to fetch payment:", error);
      return null;
    }
  },

  // ✅ GET /api/payments/inquiry/{inquiry_id}
  getByInquiry: async (inquiryId) => {
    try {
      if (!inquiryId) return [];
      const response = await apiFetch(`/payments/inquiry/${inquiryId}`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to fetch payments for inquiry:", error);
      return [];
    }
  },

  // ✅ GET /api/payments/project/{project_id}
  getByProject: async (projectId) => {
    try {
      if (!projectId) return [];
      const response = await apiFetch(`/payments/project/${projectId}`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to fetch payments for project:", error);
      return [];
    }
  },

  // ✅ POST /api/payments/
  create: async (data) => {
    try {
      // ✅ Pastikan data valid
      const payload = {
        inquiry_id: data.inquiry_id || data.inquiryId || null,
        project_id: data.project_id || data.projectId || null,
        invoice_id: data.invoice_id || data.invoiceId || null,
        payment_type: data.payment_type || data.type || "payment",
        amount: parseFloat(data.amount) || 0,
        payment_method: data.payment_method || data.method || "bank_transfer",
        reference_number: data.reference_number || data.reference || null,
        notes: data.notes || null,
        paid_at: data.paid_at || data.payment_date || new Date().toISOString(),
        due_date: data.due_date || null,
        payment_proof: data.payment_proof || null,
        status: data.status || "pending",
      };

      // console.log("📤 Creating payment:", payload);

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

  // ✅ PATCH /api/payments/{payment_id}
  update: async (paymentId, data) => {
    try {
      const response = await apiFetch(`/payments/${paymentId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      console.error("Failed to update payment:", error);
      throw error;
    }
  },

  // ✅ DELETE /api/payments/{payment_id}
  delete: async (paymentId) => {
    try {
      const response = await apiFetch(`/payments/${paymentId}`, {
        method: "DELETE",
      });
      return response.data || response;
    } catch (error) {
      console.error("Failed to delete payment:", error);
      throw error;
    }
  },

  // ✅ POST /api/payments/{payment_id}/confirm
  confirm: async (paymentId, confirmedBy = "system", notes = null) => {
    try {
      if (!paymentId) {
        throw new Error("Payment ID is required");
      }

      const payload = {
        confirmed_by: confirmedBy || "system",
        notes: notes || null,
      };

      // console.log("📤 [PaymentAPI] Confirming payment:", {
      //  paymentId,
      //  payload,
      //});

      const response = await apiFetch(`/payments/${paymentId}/confirm`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      // console.log("✅ [PaymentAPI] Payment confirmed:", response);
      return response.data || response;
    } catch (error) {
      console.error(
        "❌ [PaymentAPI] Failed to confirm payment:",
        error.message || error,
      );
      throw error;
    }
  },

  // ✅ POST /api/payments/{payment_id}/cancel
  cancel: async (paymentId, reason = null) => {
    try {
      if (!paymentId) {
        throw new Error("Payment ID is required");
      }

      // ✅ Cek status payment terlebih dahulu
      const payment = await PaymentAPI.getById(paymentId);
      if (
        payment &&
        ["completed", "confirmed", "paid", "settled"].includes(payment.status)
      ) {
        throw new Error("Cannot cancel a completed payment");
      }

      const response = await apiFetch(`/payments/${paymentId}/cancel`, {
        method: "POST",
        body: JSON.stringify({ reason: reason || "Cancelled by admin" }),
      });
      return response.data || response;
    } catch (error) {
      console.error("Failed to cancel payment:", error);
      throw error;
    }
  },

  // ✅ POST /api/payments/deposit
  createDeposit: async (data) => {
    try {
      const response = await apiFetch("/payments/deposit", {
        method: "POST",
        body: JSON.stringify({
          inquiry_id: data.inquiry_id || data.inquiryId,
          project_id: data.project_id || data.projectId,
          amount: parseFloat(data.amount) || 0,
          payment_method: data.payment_method || data.method || "bank_transfer",
          reference_number: data.reference_number || data.reference || null,
          notes: data.notes || null,
        }),
      });
      return response.data || response;
    } catch (error) {
      console.error("Failed to create deposit:", error);
      throw error;
    }
  },

  // ============================================================
  // INVOICES
  // ============================================================

  // ✅ GET /api/payments/invoices/
  getInvoices: async (params = {}) => {
    try {
      const query = new URLSearchParams(params).toString();
      const response = await apiFetch(`/payments/invoices/?${query}`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to fetch invoices:", error);
      return [];
    }
  },

  // ✅ GET /api/payments/invoices/inquiry/{inquiry_id}
  getInvoicesByInquiry: async (inquiryId) => {
    try {
      if (!inquiryId) return [];
      const response = await apiFetch(
        `/payments/invoices/inquiry/${inquiryId}`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to fetch invoices for inquiry:", error);
      return [];
    }
  },

  // ✅ GET /api/payments/invoices/project/{project_id}
  getInvoicesByProject: async (projectId) => {
    try {
      if (!projectId) return [];
      const response = await apiFetch(
        `/payments/invoices/project/${projectId}`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to fetch invoices for project:", error);
      return [];
    }
  },

  // ✅ GET /api/payments/invoices/{invoice_id}
  getInvoiceById: async (invoiceId) => {
    try {
      const response = await apiFetch(`/payments/invoices/${invoiceId}`);
      return response.data || response;
    } catch (error) {
      console.error("Failed to fetch invoice:", error);
      return null;
    }
  },

  // ✅ POST /api/payments/invoices/
  createInvoice: async (data) => {
    try {
      const payload = {
        inquiry_id: data.inquiry_id || data.inquiryId || null,
        project_id: data.project_id || data.projectId || null,
        invoice_number: data.invoice_number || data.number || null,
        payment_terms: data.payment_terms || data.terms || null,
        invoice_date:
          data.invoice_date ||
          data.date ||
          new Date().toISOString().split("T")[0],
        due_date: data.due_date || null,
        notes: data.notes || null,
        items: data.items || [],
        status: data.status || "draft",
      };

      // console.log("📤 Creating invoice:", payload);

      const response = await apiFetch("/payments/invoices/", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      return response.data || response;
    } catch (error) {
      console.error("Failed to create invoice:", error);
      throw error;
    }
  },

  // ✅ PATCH /api/payments/invoices/{invoice_id}
  updateInvoice: async (invoiceId, data) => {
    try {
      const response = await apiFetch(`/payments/invoices/${invoiceId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      console.error("Failed to update invoice:", error);
      throw error;
    }
  },

  // ✅ POST /api/payments/invoices/{invoice_id}/send
  sendInvoice: async (invoiceId) => {
    try {
      const response = await apiFetch(`/payments/invoices/${invoiceId}/send`, {
        method: "POST",
      });
      return response.data || response;
    } catch (error) {
      console.error("Failed to send invoice:", error);
      throw error;
    }
  },

  // ✅ POST /api/payments/invoices/{invoice_id}/pay
  markInvoiceAsPaid: async (invoiceId) => {
    try {
      const response = await apiFetch(`/payments/invoices/${invoiceId}/pay`, {
        method: "POST",
      });
      return response.data || response;
    } catch (error) {
      console.error("Failed to mark invoice as paid:", error);
      throw error;
    }
  },

  // ✅ GET /api/payments/invoices/generate-number
  generateInvoiceNumber: async () => {
    try {
      const response = await apiFetch("/payments/invoices/generate-number");
      return response.data || response;
    } catch (error) {
      console.error("Failed to generate invoice number:", error);
      return null;
    }
  },

  // ============================================================
  // FINANCIAL SUMMARY
  // ============================================================

  // ✅ GET /api/payments/financial/inquiry/{inquiry_id}
  getFinancialSummary: async (inquiryId) => {
    try {
      if (!inquiryId) return null;
      const response = await apiFetch(
        `/payments/financial/inquiry/${inquiryId}`,
      );
      return response.data || response;
    } catch (error) {
      console.error("Failed to fetch financial summary:", error);
      return null;
    }
  },

  // ✅ GET /api/payments/financial/project/{project_id}
  getFinancialSummaryByProject: async (projectId) => {
    try {
      if (!projectId) return null;
      const response = await apiFetch(
        `/payments/financial/project/${projectId}`,
      );
      return response.data || response;
    } catch (error) {
      console.error("Failed to fetch financial summary:", error);
      return null;
    }
  },
};
