// ============================================================
// billing/index.js - Main Entry Point
// ============================================================

import { state, CONFIG } from "./config.js";
import { DOM } from "./dom.js";
import { InquiryAPI, PaymentAPI } from "./api.js";
import { showToast } from "../../pages/shared/toast.js";
import { PaymentFormatter } from "../../pages/shared/payments/formatters.js";
import { Formatter } from "../../pages/shared/formatters.js";
import { updateDashboard, updateBadgeCounts } from "./renderers/dashboard.js";
import { renderQuotations } from "./renderers/quotations.js";
import { renderInvoices } from "./renderers/invoices.js";
import { bindEvents } from "./handlers/events.js";
import { calculateInvoiceTotal } from "./handlers/modals.js";
import { BillingAPI } from "./api.js";

// ============================================================
// LOAD DATA
// ============================================================

export async function loadBillingData() {
  console.log("🔄 Loading billing data...");

  if (state.isLoading) return;
  state.isLoading = true;

  try {
    const isQuotesTab = state.activeTab === "quotations";

    // 1. Load Quotations
    const quoteFilters = {
      search: state.filters.search,
      status: ["quoted", "approved"].includes(state.filters.status)
        ? state.filters.status
        : "",
    };

    const loadQuotes = state.filters.type !== "invoice";
    let quotes = [];
    let quoteTotal = 0;
    let quotePages = 1;

    if (loadQuotes) {
      const quoteData = await InquiryAPI.fetchInquiries(
        state.quotePage,
        quoteFilters,
      );
      if (quoteData) {
        quotes = quoteData.data || quoteData.items || quoteData || [];
        quoteTotal = quoteData.total || quoteData.total_items || quotes.length;
        quotePages =
          quoteData.total_pages ||
          quoteData.totalPages ||
          Math.ceil(quoteTotal / CONFIG.QUOTES_PER_PAGE) ||
          1;
      }
    }

    state.quotations = quotes;
    state.quoteTotalItems = quoteTotal;
    state.quoteTotalPages = Math.max(1, quotePages);

    // 2. Load Invoices - menggunakan endpoint yang tersedia
    // Karena GET /payments/invoices/ tidak ada, kita gunakan outstanding
    // dan kita tidak bisa filter by status selain overdue & outstanding
    const loadInvoices = state.filters.type !== "quotation";
    let invoices = [];
    let invoiceTotal = 0;
    let invoicePages = 1;

    if (loadInvoices) {
      let invoiceData = [];

      // Jika status filter = overdue, ambil overdue
      if (state.filters.status === "overdue") {
        invoiceData = await PaymentAPI.getInvoices({ status: "overdue" });
      } else {
        // Default: ambil outstanding (sent, partial)
        invoiceData = await PaymentAPI.getInvoices({ status: "outstanding" });
        // Jika status filter = sent atau partial, kita filter di frontend
        if (
          state.filters.status &&
          ["sent", "partial"].includes(state.filters.status)
        ) {
          invoiceData = invoiceData.filter(
            (inv) => inv.status === state.filters.status,
          );
        }
      }

      invoices = invoiceData || [];
      invoiceTotal = invoices.length;
      invoicePages = 1; // No pagination for now
    }

    state.invoices = invoices;
    state.invoiceTotalItems = invoiceTotal;
    state.invoiceTotalPages = Math.max(1, invoicePages);

    // 3. Render
    if (isQuotesTab) {
      renderQuotations(quotes);
      updatePagination(
        "quote",
        state.quotePage,
        state.quoteTotalPages,
        state.quoteTotalItems,
      );
    } else {
      renderInvoices(invoices);
      updatePagination(
        "invoice",
        state.invoicePage,
        state.invoiceTotalPages,
        state.invoiceTotalItems,
      );
    }

    // 4. Badges
    updateBadgeCounts(state.quotations.length, state.invoices.length);

    // 5. Dashboard stats
    const stats = await calculateDashboardStats();
    updateDashboard(stats);

    console.log(
      `✅ Billing loaded: ${quotes.length} quotes, ${invoices.length} invoices`,
    );
  } catch (error) {
    console.error("❌ Failed to load billing data:", error);
    showToast("Failed to load billing data: " + error.message, "error");
    if (state.activeTab === "quotations") {
      renderQuotations([]);
    } else {
      renderInvoices([]);
    }
  } finally {
    state.isLoading = false;
  }
}

// ============================================================
// CALCULATE DASHBOARD STATS
// ============================================================

async function calculateDashboardStats() {
  try {
    // Quotes stats
    const quoteData = await InquiryAPI.fetchInquiries(1, {
      status: "",
      search: "",
      limit: 1000,
    });
    const allQuotes = quoteData?.data || quoteData?.items || quoteData || [];

    // Invoice stats - gunakan outstanding & overdue
    const [outstandingData, overdueData] = await Promise.all([
      PaymentAPI.getInvoices({ status: "outstanding" }),
      PaymentAPI.getInvoices({ status: "overdue" }),
    ]);

    const outstanding = outstandingData || [];
    const overdue = overdueData || [];

    const totalQuotes = allQuotes.length;
    const pendingQuotes = allQuotes.filter((q) => q.status === "quoted").length;
    const outstandingInvoices = outstanding.length;
    const overdueInvoices = overdue.length;

    return {
      totalQuotes,
      pendingQuotes,
      outstandingInvoices,
      overdueInvoices,
    };
  } catch (error) {
    console.warn("Failed to calculate dashboard stats:", error);
    return {
      totalQuotes: 0,
      pendingQuotes: 0,
      outstandingInvoices: 0,
      overdueInvoices: 0,
    };
  }
}

// ============================================================
// UPDATE PAGINATION
// ============================================================

function updatePagination(type, page, totalPages, totalItems) {
  const info = type === "quote" ? DOM.quotePageInfo() : DOM.invoicePageInfo();
  const prev = type === "quote" ? DOM.prevQuotePage() : DOM.prevInvoicePage();
  const next = type === "quote" ? DOM.nextQuotePage() : DOM.nextInvoicePage();

  if (info) {
    info.textContent = `Page ${page} of ${Math.max(1, totalPages)} (${totalItems} items)`;
  }
  if (prev) {
    prev.disabled = page <= 1;
    prev.style.opacity = page <= 1 ? "0.4" : "1";
  }
  if (next) {
    const isLast = page >= totalPages || totalPages === 0;
    next.disabled = isLast;
    next.style.opacity = isLast ? "0.4" : "1";
  }
}

// ============================================================
// SUBMIT INVOICE FORM
// ============================================================

async function handleInvoiceSubmit(e) {
  e.preventDefault();

  const form = DOM.invoiceForm();
  const submitBtn = DOM.saveInvoiceBtn();

  const inquiryId = DOM.invoiceInquiryId()?.value;
  const projectId = DOM.invoiceProjectId()?.value || null;
  const invoiceNumber = DOM.invoiceNumber()?.value?.trim();
  const paymentTerms = DOM.invoicePaymentTerms()?.value?.trim() || null;
  const invoiceDate =
    DOM.invoiceDate()?.value || new Date().toISOString().split("T")[0];
  const dueDate = DOM.invoiceDueDate()?.value || null;
  const notes = DOM.invoiceNotes()?.value?.trim() || null;

  // Collect items
  const rows = document.querySelectorAll(".invoice-item-row");
  const items = [];
  let hasError = false;

  rows.forEach((row) => {
    const desc = row.querySelector(".item-description")?.value?.trim();
    const qty = parseFloat(row.querySelector(".item-quantity")?.value) || 1;
    const unit = row.querySelector(".item-unit")?.value?.trim() || "";
    const price = parseFloat(row.querySelector(".item-unit-price")?.value) || 0;

    if (desc && price > 0) {
      items.push({ description: desc, quantity: qty, unit, unit_price: price });
    } else if (desc || price > 0) {
      hasError = true;
    }
  });

  if (items.length === 0) {
    showToast("Please add at least one valid invoice item", "warning");
    return;
  }

  if (hasError) {
    showToast("Some items have missing description or price", "warning");
    return;
  }

  if (!inquiryId) {
    showToast("Inquiry ID is required", "error");
    return;
  }

  if (!invoiceNumber) {
    showToast("Invoice Number is required", "error");
    return;
  }

  const total = items.reduce(
    (sum, item) => sum + item.quantity * item.unit_price,
    0,
  );

  if (
    !confirm(
      `Create invoice ${invoiceNumber} for ${PaymentFormatter.currency(total)}?`,
    )
  ) {
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
  }

  try {
    const result = await BillingAPI.createInvoice({
      inquiry_id: inquiryId,
      project_id: projectId,
      invoice_number: invoiceNumber,
      invoice_date: invoiceDate,
      due_date: dueDate,
      payment_terms: paymentTerms,
      notes: notes,
      items: items,
      status: "draft",
    });

    if (result) {
      showToast(
        `✅ Invoice ${invoiceNumber} created! (${PaymentFormatter.currency(total)})`,
        "success",
      );
      closeInvoiceModal();
      await loadBillingData();
    } else {
      showToast("❌ Failed to create invoice", "error");
    }
  } catch (error) {
    console.error("Invoice creation error:", error);
    showToast("❌ " + (error.message || "Failed to create invoice"), "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-save"></i> Create Invoice';
    }
  }
}

// ============================================================
// CLOSE INVOICE MODAL (wrapper for events)
// ============================================================

function closeInvoiceModal() {
  const modal = DOM.invoiceModal();
  if (modal) modal.classList.remove("active");
  document.body.style.overflow = "";
  const form = DOM.invoiceForm();
  if (form) form.reset();
}

// ============================================================
// INITIALIZATION
// ============================================================

export async function initBilling() {
  console.log("🚀 Initializing Billing page...");

  try {
    // Bind events
    bindEvents();

    // Bind invoice form submit
    const form = DOM.invoiceForm();
    if (form) {
      form.addEventListener("submit", handleInvoiceSubmit);
    }

    // Load data
    await loadBillingData();

    console.log("✅ Billing page initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize billing page:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

// ============================================================
// EXPOSE TO GLOBAL (for inline onclick)
// ============================================================

window.initBilling = initBilling;
window.loadBillingData = loadBillingData;

// Re-export for handlers
export { closeInvoiceModal, handleInvoiceSubmit };
