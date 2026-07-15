// ============================================================
// billing/handlers/events.js - Event Bindings
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { loadBillingData } from "../index.js";
import {
  closeInvoiceModal,
  closeInvoiceDetailModal,
  closeConfirmActionModal,
  openInvoiceModal,
  openInvoiceDetailModal,
  calculateInvoiceTotal,
  addInvoiceItemRow,
  openConfirmActionModal,
} from "./modals.js";
import {
  handleSendInvoice,
  handleMarkInvoicePaid,
  handleDeleteInvoice,
  handleSendInvoiceReminder,
} from "./invoices.js";
import {
  handleViewQuotation,
  handleConvertQuoteToInvoice,
  handleResendQuote,
  handleRejectQuote,
} from "./quotations.js";
import { showToast } from "../../shared/toast.js";

// ============================================================
// TAB SWITCHING
// ============================================================

function switchTab(tab) {
  const tabQuotes = DOM.tabQuotations();
  const tabInvoices = DOM.tabInvoices();
  const panelQuotes = DOM.panelQuotations();
  const panelInvoices = DOM.panelInvoices();

  // Update tabs
  if (tabQuotes) tabQuotes.classList.toggle("active", tab === "quotations");
  if (tabInvoices) tabInvoices.classList.toggle("active", tab === "invoices");

  // Update panels
  if (panelQuotes) panelQuotes.classList.toggle("active", tab === "quotations");
  if (panelInvoices)
    panelInvoices.classList.toggle("active", tab === "invoices");

  state.activeTab = tab;

  // Reload data for the active tab
  loadBillingData();
}

// ============================================================
// EXPOSE GLOBAL FUNCTIONS (for inline onclick)
// ============================================================

function exposeGlobals() {
  // Quotations
  window.viewQuotation = handleViewQuotation;
  window.convertQuoteToInvoice = handleConvertQuoteToInvoice;
  window.resendQuote = handleResendQuote;
  window.rejectQuote = handleRejectQuote;

  // Invoices
  window.sendInvoiceAction = handleSendInvoice;
  window.markInvoicePaidAction = handleMarkInvoicePaid;
  window.deleteInvoiceAction = handleDeleteInvoice;
  window.sendInvoiceReminderAction = handleSendInvoiceReminder;
  window.viewInvoiceDetail = openInvoiceDetailModal;

  // Modals
  window.closeInvoiceDetailModal = closeInvoiceDetailModal;
  window.closeConfirmActionModal = closeConfirmActionModal;
}

// ============================================================
// BIND ALL EVENTS
// ============================================================

export function bindEvents() {
  // ----- Tabs -----
  DOM.tabQuotations()?.addEventListener("click", () => switchTab("quotations"));
  DOM.tabInvoices()?.addEventListener("click", () => switchTab("invoices"));

  // ----- Search & Filters -----
  let searchTimeout;
  DOM.searchBilling()?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.quotePage = 1;
      state.invoicePage = 1;
      loadBillingData();
    }, 300);
  });

  DOM.statusFilter()?.addEventListener("change", (e) => {
    state.filters.status = e.target.value;
    state.quotePage = 1;
    state.invoicePage = 1;
    loadBillingData();
  });

  DOM.typeFilter()?.addEventListener("change", (e) => {
    state.filters.type = e.target.value;
    state.quotePage = 1;
    state.invoicePage = 1;
    loadBillingData();
  });

  // ----- Refresh -----
  DOM.refreshBillingBtn()?.addEventListener("click", () => {
    loadBillingData();
    showToast("🔄 Refreshed", "info", 1500);
  });

  // ----- Create Invoice -----
  DOM.createInvoiceBtn()?.addEventListener("click", () => openInvoiceModal());

  // ----- Invoice Modal (Create/Edit) -----
  DOM.closeInvoiceModal()?.addEventListener("click", closeInvoiceModal);
  DOM.cancelInvoiceBtn()?.addEventListener("click", closeInvoiceModal);
  DOM.invoiceModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.invoiceModal()) closeInvoiceModal();
  });

  // Generate invoice number
  DOM.generateInvoiceNumberBtn()?.addEventListener("click", async () => {
    const input = DOM.invoiceNumber();
    if (!input) return;
    try {
      const result = await import("../api.js").then((m) =>
        m.BillingAPI.generateInvoiceNumber(),
      );
      if (result) {
        input.value =
          result.invoice_number || result.data?.invoice_number || "";
        showToast("Invoice number generated!", "success", 1500);
      }
    } catch (error) {
      showToast("Failed to generate invoice number", "error");
    }
  });

  // Add invoice item
  DOM.addInvoiceItemBtn()?.addEventListener("click", () => {
    const container = DOM.invoiceItemsContainer();
    if (container) addInvoiceItemRow(container);
  });

  // Invoice form submit - handled by index.js

  // ----- Invoice Detail Modal -----
  DOM.closeInvoiceDetailModal()?.addEventListener(
    "click",
    closeInvoiceDetailModal,
  );
  DOM.detailCloseBtn()?.addEventListener("click", closeInvoiceDetailModal);
  DOM.invoiceDetailModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.invoiceDetailModal()) closeInvoiceDetailModal();
  });

  // Detail actions (send, mark paid)
  DOM.detailSendBtn()?.addEventListener("click", () => {
    if (state.currentInvoiceId) handleSendInvoice(state.currentInvoiceId);
  });
  DOM.detailMarkPaidBtn()?.addEventListener("click", () => {
    if (state.currentInvoiceId) handleMarkInvoicePaid(state.currentInvoiceId);
  });

  // Print button
  DOM.detailPrintBtn()?.addEventListener("click", () => {
    window.print();
  });

  // ----- Confirm Action Modal -----
  DOM.closeConfirmActionModal()?.addEventListener(
    "click",
    closeConfirmActionModal,
  );
  DOM.cancelConfirmActionBtn()?.addEventListener(
    "click",
    closeConfirmActionModal,
  );
  DOM.confirmActionModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.confirmActionModal()) closeConfirmActionModal();
  });
  DOM.executeConfirmActionBtn()?.addEventListener("click", async () => {
    const action = state.pendingAction;
    if (typeof action === "function") {
      await action();
    } else {
      closeConfirmActionModal();
    }
  });

  // ----- Keyboard shortcuts -----
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (DOM.invoiceModal()?.classList.contains("active")) closeInvoiceModal();
      if (DOM.invoiceDetailModal()?.classList.contains("active"))
        closeInvoiceDetailModal();
      if (DOM.confirmActionModal()?.classList.contains("active"))
        closeConfirmActionModal();
    }
    if (e.ctrlKey && e.key === "i") {
      e.preventDefault();
      openInvoiceModal();
    }
    if (e.ctrlKey && e.key === "f") {
      e.preventDefault();
      DOM.searchBilling()?.focus();
    }
  });

  // ----- Pagination -----
  DOM.prevQuotePage()?.addEventListener("click", () => {
    if (state.quotePage > 1) {
      state.quotePage--;
      loadBillingData();
    }
  });
  DOM.nextQuotePage()?.addEventListener("click", () => {
    if (state.quotePage < state.quoteTotalPages) {
      state.quotePage++;
      loadBillingData();
    }
  });
  DOM.prevInvoicePage()?.addEventListener("click", () => {
    if (state.invoicePage > 1) {
      state.invoicePage--;
      loadBillingData();
    }
  });
  DOM.nextInvoicePage()?.addEventListener("click", () => {
    if (state.invoicePage < state.invoiceTotalPages) {
      state.invoicePage++;
      loadBillingData();
    }
  });

  // ----- Expose globals for inline onclick -----
  exposeGlobals();

  console.log("✅ Billing events bound successfully!");
}
