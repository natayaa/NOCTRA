// ============================================================
// payments/index.js - Main Entry Point (FIXED)
// ============================================================

import { state, CONFIG } from "./config.js";
import { DOM } from "./dom.js";
import { PaymentAPI } from "../shared/payments/api.js";
import { showToast } from "./toast.js";
import {
  renderPayments,
  renderInvoices,
  updatePagination,
  showLoadingState,
} from "./renderers/table.js";
import { renderDashboard } from "./renderers/dashboard.js";
import { bindEvents, bindKeyboardShortcuts } from "./handlers/events.js";
import { ensureArray } from "../shared/payments/utils.js";

// ============================================================
// MAIN LOAD FUNCTION
// ============================================================
export async function loadPayments() {
  console.log("🔄 Loading payments data...");

  const isPaymentsTab = state.activeTab === "payments";

  try {
    showLoadingState(isPaymentsTab ? "payments" : "invoices");

    let payments = [];
    let invoices = [];
    let stats = null;

    // Get statistics
    try {
      stats = await PaymentAPI.getStatistics(
        state.filters.startDate || null,
        state.filters.endDate || null,
      );
    } catch (e) {
      console.warn("Could not fetch statistics:", e);
      stats = null;
    }

    if (isPaymentsTab) {
      try {
        // Try to get payments with filters
        const params = {
          status: state.filters.status || undefined,
          type: state.filters.type || undefined,
          search: state.filters.search || undefined,
          limit: CONFIG.PAYMENTS_PER_PAGE,
          page: state.paymentsCurrentPage,
        };
        const response = await PaymentAPI.getAll(params);
        payments = ensureArray(response?.data || response || []);
      } catch (e) {
        console.warn("Could not fetch payments:", e);
        payments = [];
      }

      state.payments = payments;
      state.paymentsTotalItems = payments.length;
      state.paymentsTotalPages =
        Math.ceil(payments.length / CONFIG.PAYMENTS_PER_PAGE) || 1;

      const countEl = document.getElementById("paymentsCount");
      if (countEl) countEl.textContent = payments.length;

      const startIndex =
        (state.paymentsCurrentPage - 1) * CONFIG.PAYMENTS_PER_PAGE;
      const pageItems = payments.slice(
        startIndex,
        startIndex + CONFIG.PAYMENTS_PER_PAGE,
      );
      renderPayments(pageItems);
      updatePagination(
        state.paymentsCurrentPage,
        state.paymentsTotalPages,
        state.paymentsTotalItems,
        "payments",
      );
    } else {
      try {
        const response = await PaymentAPI.getInvoices({
          status: state.filters.status || undefined,
          search: state.filters.search || undefined,
          limit: CONFIG.INVOICES_PER_PAGE,
          page: state.invoicesCurrentPage,
        });
        invoices = ensureArray(response?.data || response || []);
      } catch (e) {
        console.warn("Could not fetch invoices:", e);
        invoices = [];
      }

      state.invoices = invoices;
      state.invoicesTotalItems = invoices.length;
      state.invoicesTotalPages =
        Math.ceil(invoices.length / CONFIG.INVOICES_PER_PAGE) || 1;

      const countEl = document.getElementById("invoicesCount");
      if (countEl) countEl.textContent = invoices.length;

      const startIndex =
        (state.invoicesCurrentPage - 1) * CONFIG.INVOICES_PER_PAGE;
      const pageItems = invoices.slice(
        startIndex,
        startIndex + CONFIG.INVOICES_PER_PAGE,
      );
      renderInvoices(pageItems);
      updatePagination(
        state.invoicesCurrentPage,
        state.invoicesTotalPages,
        state.invoicesTotalItems,
        "invoices",
      );
    }

    renderDashboard(stats, payments, invoices);
    console.log("✅ Payments loaded successfully");
  } catch (error) {
    console.error("❌ Failed to load payments:", error);
    showToast("Failed to load payments data", "error");
  }
}

// ============================================================
// ACTION HANDLERS (Exposed to window)
// ============================================================

export async function confirmPayment(paymentId) {
  if (!paymentId) {
    showToast("❌ Payment ID is required", "error");
    return;
  }
  if (!confirm("Confirm this payment?")) return;

  try {
    const result = await PaymentAPI.confirm(paymentId, "admin");
    if (result) {
      showToast("✅ Payment confirmed!", "success");
      await loadPayments();
    } else {
      showToast("❌ Failed to confirm payment", "error");
    }
  } catch (error) {
    showToast("❌ " + (error.message || "Failed to confirm payment"), "error");
  }
}

export async function cancelPayment(paymentId) {
  if (!paymentId) {
    showToast("❌ Payment ID is required", "error");
    return;
  }

  const reason = prompt("Reason for cancellation:");
  if (reason === null) return;

  if (!confirm("Cancel this payment?")) return;

  try {
    const result = await PaymentAPI.cancel(paymentId, reason);
    if (result) {
      showToast("🗑️ Payment cancelled", "info");
      await loadPayments();
    } else {
      showToast("❌ Failed to cancel payment", "error");
    }
  } catch (error) {
    showToast("❌ " + (error.message || "Failed to cancel payment"), "error");
  }
}

export async function viewPayment(paymentId) {
  if (!paymentId) {
    showToast("❌ Payment ID is required", "error");
    return;
  }
  try {
    const payment = await PaymentAPI.getById(paymentId);
    if (payment) {
      const amount = payment.amount || 0;
      const type = payment.payment_type || payment.type || "payment";
      showToast(
        `${PaymentFormatter.paymentTypeLabel(type)}: ${PaymentFormatter.currency(amount)}`,
        "info",
        5000,
      );
    }
  } catch (error) {
    showToast("Failed to load payment details", "error");
  }
}

export async function viewInvoice(invoiceId) {
  if (!invoiceId) {
    showToast("❌ Invoice ID is required", "error");
    return;
  }
  try {
    const invoice = await PaymentAPI.getInvoiceById(invoiceId);
    if (invoice) {
      const total = invoice.total_amount || invoice.total || 0;
      showToast(
        `Invoice ${invoice.invoice_number || "#"}: ${PaymentFormatter.currency(total)}`,
        "info",
        5000,
      );
    }
  } catch (error) {
    showToast("Failed to load invoice details", "error");
  }
}

export async function sendInvoice(invoiceId) {
  if (!invoiceId) {
    showToast("❌ Invoice ID is required", "error");
    return;
  }
  if (!confirm("Send this invoice to customer?")) return;

  try {
    const result = await PaymentAPI.sendInvoice(invoiceId);
    if (result) {
      showToast("✅ Invoice sent!", "success");
      await loadPayments();
    } else {
      showToast("❌ Failed to send invoice", "error");
    }
  } catch (error) {
    showToast("❌ " + (error.message || "Failed to send invoice"), "error");
  }
}

export async function markInvoicePaid(invoiceId) {
  if (!invoiceId) {
    showToast("❌ Invoice ID is required", "error");
    return;
  }
  if (!confirm("Mark this invoice as paid?")) return;

  try {
    const result = await PaymentAPI.markInvoiceAsPaid(invoiceId);
    if (result) {
      showToast("✅ Invoice marked as paid!", "success");
      await loadPayments();
    } else {
      showToast("❌ Failed to mark invoice as paid", "error");
    }
  } catch (error) {
    showToast(
      "❌ " + (error.message || "Failed to mark invoice as paid"),
      "error",
    );
  }
}

export async function sendInvoiceReminder(invoiceId) {
  if (!invoiceId) {
    showToast("❌ Invoice ID is required", "error");
    return;
  }
  if (!confirm("Send reminder for this overdue invoice?")) return;

  try {
    const result = await PaymentAPI.sendInvoiceReminder(invoiceId);
    if (result) {
      showToast("✅ Reminder sent!", "success");
      await loadPayments();
    } else {
      showToast("❌ Failed to send reminder", "error");
    }
  } catch (error) {
    showToast("❌ " + (error.message || "Failed to send reminder"), "error");
  }
}

// ============================================================
// EXPORT FUNCTION
// ============================================================
export function exportPayments() {
  const data = state.payments.map((p) => ({
    id: p.id?.substring(0, 8) || "N/A",
    type: p.type || p.payment_type || "-",
    amount: p.amount || 0,
    method: p.method || p.payment_method || "-",
    status: p.status || "-",
    reference: p.reference_number || "",
    date: p.created_at || p.paid_at || "",
  }));

  if (data.length === 0) {
    showToast("No data to export", "warning");
    return;
  }

  const headers = [
    "ID",
    "Type",
    "Amount",
    "Method",
    "Status",
    "Reference",
    "Date",
  ];
  const rows = data.map((d) => [
    d.id,
    d.type,
    d.amount,
    d.method,
    d.status,
    d.reference,
    d.date ? new Date(d.date).toLocaleDateString("id-ID") : "-",
  ]);

  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `payments_export_${new Date().toISOString().split("T")[0]}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);

  showToast("✅ Export completed!", "success");
}

// ============================================================
// INITIALIZATION
// ============================================================
export async function initPayments() {
  console.log("🚀 Initializing Payments page...");
  try {
    bindEvents();
    bindKeyboardShortcuts();
    await loadPayments();
    console.log("✅ Payments page initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

// ============================================================
// EXPOSE TO GLOBAL
// ============================================================
window.loadPayments = loadPayments;
window.confirmPayment = confirmPayment;
window.cancelPayment = cancelPayment;
window.viewPayment = viewPayment;
window.viewInvoice = viewInvoice;
window.sendInvoice = sendInvoice;
window.markInvoicePaid = markInvoicePaid;
window.sendInvoiceReminder = sendInvoiceReminder;
window.exportPayments = exportPayments;

console.log("📋 Payments page module ready");
