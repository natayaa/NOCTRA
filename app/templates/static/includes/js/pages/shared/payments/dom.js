// ============================================================
// payments/dom.js - DOM References
// ============================================================

export const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

export const $$ = (selector) => document.querySelectorAll(selector);

export const DOM = {
  // Dashboard
  totalRevenue: () => $("totalRevenue"),
  totalPaid: () => $("totalPaid"),
  totalPending: () => $("totalPending"),
  overdueInvoices: () => $("overdueInvoices"),

  // Toolbar
  searchPayment: () => $("searchPayment"),
  statusFilter: () => $("statusFilter"),
  typeFilter: () => $("typeFilter"),
  startDateFilter: () => $("startDateFilter"),
  endDateFilter: () => $("endDateFilter"),
  exportPaymentsBtn: () => $("exportPaymentsBtn"),
  addPaymentBtn: () => $("addPaymentBtn"),
  addInvoiceBtn: () => $("addInvoiceBtn"),

  // Tabs
  tabPayments: () => $("tab-payments"),
  tabInvoices: () => $("tab-invoices"),
  paymentsTab: () => $("payments-tab"),
  invoicesTab: () => $("invoices-tab"),

  // Payments Table
  paymentsBody: () => $("paymentsBody"),
  prevPagePayments: () => $("prevPagePayments"),
  nextPagePayments: () => $("nextPagePayments"),
  pageInfoPayments: () => $("pageInfoPayments"),

  // Invoices Table
  invoicesBody: () => $("invoicesBody"),
  prevPageInvoices: () => $("prevPageInvoices"),
  nextPageInvoices: () => $("nextPageInvoices"),
  pageInfoInvoices: () => $("pageInfoInvoices"),

  // Payment Modal
  paymentModal: () => $("paymentModal"),
  paymentForm: () => $("paymentForm"),
  paymentInquiryId: () => $("paymentInquiryId"),
  paymentProjectId: () => $("paymentProjectId"),
  paymentType: () => $("paymentType"),
  paymentAmount: () => $("paymentAmount"),
  paymentMethod: () => $("paymentMethod"),
  paymentReference: () => $("paymentReference"),
  paymentDate: () => $("paymentDate"),
  paymentDueDate: () => $("paymentDueDate"),
  paymentNotes: () => $("paymentNotes"),
  closePaymentModal: () => $("closePaymentModal"),
  cancelPaymentBtn: () => $("cancelPaymentBtn"),

  // Invoice Modal
  invoiceModal: () => $("invoiceModal"),
  invoiceForm: () => $("invoiceForm"),
  invoiceInquiryId: () => $("invoiceInquiryId"),
  invoiceProjectId: () => $("invoiceProjectId"),
  invoiceNumber: () => $("invoiceNumber"),
  invoicePaymentTerms: () => $("invoicePaymentTerms"),
  invoiceDate: () => $("invoiceDate"),
  invoiceDueDate: () => $("invoiceDueDate"),
  invoiceNotes: () => $("invoiceNotes"),
  invoiceItemsContainer: () => $("invoiceItemsContainer"),
  addInvoiceItemBtn: () => $("addInvoiceItemBtn"),
  invoiceSubtotal: () => $("invoiceSubtotal"),
  invoiceTotal: () => $("invoiceTotal"),
  closeInvoiceModal: () => $("closeInvoiceModal"),
  cancelInvoiceBtn: () => $("cancelInvoiceBtn"),

  // Toast
  toastContainer: () => $("toastContainer"),
};
