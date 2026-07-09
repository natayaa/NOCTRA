// ============================================================
// payments/index.js - Main Entry Point
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
    // Get data based on active tab
    let payments = [];
    let invoices = [];
    let stats = null;

    if (isPaymentsTab) {
      // Try to get payments - use a dummy inquiry ID or get all
      // Note: API可能需要inquiry_id, jika tidak ada bisa gunakan endpoint lain
      // Untuk sekarang kita coba dengan string kosong atau 'all'
      try {
        const paymentsData = await PaymentAPI.getByInquiry("all");
        payments = ensureArray(paymentsData);
      } catch (e) {
        console.warn("Could not fetch payments, using empty array:", e);
        payments = [];
      }
    } else {
      try {
        // Get invoices
        const invoicesData = await PaymentAPI.getOutstandingInvoices();
        invoices = ensureArray(invoicesData);
      } catch (e) {
        console.warn("Could not fetch invoices, using empty array:", e);
        invoices = [];
      }
    }

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

    // Update state
    if (isPaymentsTab) {
      state.payments = payments;
      state.paymentsTotalItems = payments.length;
      state.paymentsTotalPages =
        Math.ceil(payments.length / CONFIG.PAYMENTS_PER_PAGE) || 1;

      // Update payments count badge
      const countEl = document.getElementById("paymentsCount");
      if (countEl) countEl.textContent = payments.length;

      renderPayments(payments.slice(0, CONFIG.PAYMENTS_PER_PAGE));
      updatePagination(
        state.paymentsCurrentPage,
        state.paymentsTotalPages,
        state.paymentsTotalItems,
        "payments",
      );
    } else {
      state.invoices = invoices;
      state.invoicesTotalItems = invoices.length;
      state.invoicesTotalPages =
        Math.ceil(invoices.length / CONFIG.INVOICES_PER_PAGE) || 1;

      // Update invoices count badge
      const countEl = document.getElementById("invoicesCount");
      if (countEl) countEl.textContent = invoices.length;

      renderInvoices(invoices.slice(0, CONFIG.INVOICES_PER_PAGE));
      updatePagination(
        state.invoicesCurrentPage,
        state.invoicesTotalPages,
        state.invoicesTotalItems,
        "invoices",
      );
    }

    // Update dashboard
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
  if (!confirm("Confirm this payment?")) return;
  const result = await PaymentAPI.confirm(paymentId, "admin");
  if (result) {
    showToast("Payment confirmed!", "success");
    await loadPayments();
  }
}

export async function cancelPayment(paymentId) {
  const reason = prompt("Reason for cancellation:");
  if (reason === null) return;
  if (!confirm("Cancel this payment?")) return;
  const result = await PaymentAPI.cancel(paymentId, reason);
  if (result) {
    showToast("Payment cancelled", "info");
    await loadPayments();
  }
}

export async function viewPayment(paymentId) {
  const payment = await PaymentAPI.getDetail(paymentId);
  if (payment) {
    showToast(`Payment: ${payment.id} - ${payment.amount}`, "info", 5000);
    // Bisa dibuka detail drawer di sini
  }
}

export async function viewInvoice(invoiceId) {
  const invoice = await PaymentAPI.getInvoice(invoiceId);
  if (invoice) {
    showToast(
      `Invoice: ${invoice.invoice_number} - ${invoice.total}`,
      "info",
      5000,
    );
    // Bisa dibuka detail drawer di sini
  }
}

export async function sendInvoice(invoiceId) {
  if (!confirm("Send this invoice to customer?")) return;
  const result = await PaymentAPI.sendInvoice(invoiceId);
  if (result) {
    showToast("Invoice sent!", "success");
    await loadPayments();
  }
}

export async function markInvoicePaid(invoiceId) {
  if (!confirm("Mark this invoice as paid?")) return;
  const result = await PaymentAPI.markInvoicePaid(invoiceId, {
    payment_method: "manual",
    notes: "Marked as paid manually",
  });
  if (result) {
    showToast("Invoice marked as paid!", "success");
    await loadPayments();
  }
}

export async function sendInvoiceReminder(invoiceId) {
  if (!confirm("Send reminder for this overdue invoice?")) return;
  const result = await PaymentAPI.sendInvoiceReminder(invoiceId);
  if (result) {
    showToast("Reminder sent!", "success");
    await loadPayments();
  }
}

// ============================================================
// EXPORT FUNCTION
// ============================================================
export function exportPayments() {
  const data = state.payments.map((p) => ({
    id: p.id,
    type: p.type || p.payment_type,
    amount: p.amount,
    method: p.method || p.payment_method,
    status: p.status,
    reference: p.reference_number || "",
    date: p.created_at || p.paid_at,
  }));

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
    d.id?.substring(0, 8) || "N/A",
    d.type || "-",
    d.amount || 0,
    d.method || "-",
    d.status || "-",
    d.reference || "-",
    d.date ? new Date(d.date).toLocaleDateString("id-ID") : "-",
  ]);

  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `payments_export_${new Date().toISOString().split("T")[0]}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);

  showToast("Export completed!", "success");
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
