// ============================================================
// payments/handlers/events.js - Event Bindings
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { loadPayments } from "../index.js";
import {
  openPaymentModal,
  closePaymentModal,
  handlePaymentSubmit,
  openInvoiceModal,
  closeInvoiceModal,
  handleInvoiceSubmit,
  bindInvoiceItemEvents,
} from "./modals.js";

export function bindEvents() {
  // Tab switching
  const tabPayments = DOM.tabPayments();
  const tabInvoices = DOM.tabInvoices();
  const paymentsTab = DOM.paymentsTab();
  const invoicesTab = DOM.invoicesTab();

  if (tabPayments && paymentsTab) {
    tabPayments.addEventListener("click", () => {
      state.activeTab = "payments";
      tabPayments.classList.add("active");
      tabInvoices?.classList.remove("active");
      paymentsTab.classList.add("active");
      invoicesTab?.classList.remove("active");
      loadPayments();
    });
  }

  if (tabInvoices && invoicesTab) {
    tabInvoices.addEventListener("click", () => {
      state.activeTab = "invoices";
      tabInvoices.classList.add("active");
      tabPayments?.classList.remove("active");
      invoicesTab.classList.add("active");
      paymentsTab?.classList.remove("active");
      loadPayments();
    });
  }

  // Search
  let searchTimeout;
  DOM.searchPayment()?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.paymentsCurrentPage = 1;
      loadPayments();
    }, 300);
  });

  // Filters
  DOM.statusFilter()?.addEventListener("change", (e) => {
    state.filters.status = e.target.value;
    state.paymentsCurrentPage = 1;
    loadPayments();
  });

  DOM.typeFilter()?.addEventListener("change", (e) => {
    state.filters.type = e.target.value;
    state.paymentsCurrentPage = 1;
    loadPayments();
  });

  DOM.startDateFilter()?.addEventListener("change", (e) => {
    state.filters.startDate = e.target.value;
    state.paymentsCurrentPage = 1;
    loadPayments();
  });

  DOM.endDateFilter()?.addEventListener("change", (e) => {
    state.filters.endDate = e.target.value;
    state.paymentsCurrentPage = 1;
    loadPayments();
  });

  // Buttons
  DOM.addPaymentBtn()?.addEventListener("click", openPaymentModal);
  DOM.addInvoiceBtn()?.addEventListener("click", openInvoiceModal);

  // Payment Modal
  DOM.closePaymentModal()?.addEventListener("click", closePaymentModal);
  DOM.cancelPaymentBtn()?.addEventListener("click", closePaymentModal);
  DOM.paymentModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.paymentModal()) closePaymentModal();
  });
  DOM.paymentForm()?.addEventListener("submit", handlePaymentSubmit);

  // Invoice Modal
  DOM.closeInvoiceModal()?.addEventListener("click", closeInvoiceModal);
  DOM.cancelInvoiceBtn()?.addEventListener("click", closeInvoiceModal);
  DOM.invoiceModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.invoiceModal()) closeInvoiceModal();
  });
  DOM.invoiceForm()?.addEventListener("submit", handleInvoiceSubmit);

  // Invoice items
  bindInvoiceItemEvents();
  DOM.addInvoiceItemBtn()?.addEventListener("click", () => {
    // Handled in modals.js
  });

  // Pagination - Payments
  DOM.prevPagePayments()?.addEventListener("click", () => {
    if (state.paymentsCurrentPage > 1) {
      state.paymentsCurrentPage--;
      loadPayments();
    }
  });
  DOM.nextPagePayments()?.addEventListener("click", () => {
    if (state.paymentsCurrentPage < state.paymentsTotalPages) {
      state.paymentsCurrentPage++;
      loadPayments();
    }
  });

  // Pagination - Invoices
  DOM.prevPageInvoices()?.addEventListener("click", () => {
    if (state.invoicesCurrentPage > 1) {
      state.invoicesCurrentPage--;
      loadPayments();
    }
  });
  DOM.nextPageInvoices()?.addEventListener("click", () => {
    if (state.invoicesCurrentPage < state.invoicesTotalPages) {
      state.invoicesCurrentPage++;
      loadPayments();
    }
  });
}

export function bindKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (DOM.paymentModal()?.classList.contains("active")) {
        closePaymentModal();
        e.preventDefault();
      }
      if (DOM.invoiceModal()?.classList.contains("active")) {
        closeInvoiceModal();
        e.preventDefault();
      }
    }
    if (e.ctrlKey && e.key === "p") {
      e.preventDefault();
      openPaymentModal();
    }
    if (e.ctrlKey && e.key === "i") {
      e.preventDefault();
      openInvoiceModal();
    }
    if (e.ctrlKey && e.key === "f") {
      e.preventDefault();
      DOM.searchPayment()?.focus();
    }
  });
}
