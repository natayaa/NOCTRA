// ============================================================
// billing/dom.js - DOM References
// ============================================================

export const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

export const $$ = (selector) => document.querySelectorAll(selector);

export const DOM = {
  // Dashboard
  totalQuotes: () => $("totalQuotes"),
  pendingQuotes: () => $("pendingQuotes"),
  outstandingInvoices: () => $("outstandingInvoices"),
  overdueInvoices: () => $("overdueInvoices"),

  // Toolbar
  searchBilling: () => $("searchBilling"),
  statusFilter: () => $("statusFilter"),
  typeFilter: () => $("typeFilter"),
  refreshBillingBtn: () => $("refreshBillingBtn"),
  createInvoiceBtn: () => $("createInvoiceBtn"),

  // Tabs
  tabQuotations: () => $("tab-quotations"),
  tabInvoices: () => $("tab-invoices"),
  quoteBadge: () => $("quoteBadge"),
  invoiceBadge: () => $("invoiceBadge"),
  panelQuotations: () => $("panel-quotations"),
  panelInvoices: () => $("panel-invoices"),

  // Quotations Table
  quotationsBody: () => $("quotationsBody"),
  prevQuotePage: () => $("prevQuotePage"),
  nextQuotePage: () => $("nextQuotePage"),
  quotePageInfo: () => $("quotePageInfo"),

  // Invoices Table
  invoicesBody: () => $("invoicesBody"),
  prevInvoicePage: () => $("prevInvoicePage"),
  nextInvoicePage: () => $("nextInvoicePage"),
  invoicePageInfo: () => $("invoicePageInfo"),

  // Invoice Modal (Create/Edit)
  invoiceModal: () => $("invoiceModal"),
  invoiceModalTitle: () => $("invoiceModalTitle"),
  invoiceModalSubtitle: () => $("invoiceModalSubtitle"),
  invoiceForm: () => $("invoiceForm"),
  invoiceEditId: () => $("invoiceEditId"),
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
  saveInvoiceBtn: () => $("saveInvoiceBtn"),
  generateInvoiceNumberBtn: () => $("generateInvoiceNumberBtn"),

  // Invoice Detail Modal
  invoiceDetailModal: () => $("invoiceDetailModal"),
  detailInvoiceNumber: () => $("detailInvoiceNumber"),
  detailInvoiceStatus: () => $("detailInvoiceStatus"),
  detailCustomer: () => $("detailCustomer"),
  detailInquiryId: () => $("detailInquiryId"),
  detailInvoiceDate: () => $("detailInvoiceDate"),
  detailDueDate: () => $("detailDueDate"),
  detailPaymentTerms: () => $("detailPaymentTerms"),
  detailItemsBody: () => $("detailItemsBody"),
  detailGrandTotal: () => $("detailGrandTotal"),
  detailNotes: () => $("detailNotes"),
  closeInvoiceDetailModal: () => $("closeInvoiceDetailModal"),
  detailPrintBtn: () => $("detailPrintBtn"),
  detailSendBtn: () => $("detailSendBtn"),
  detailMarkPaidBtn: () => $("detailMarkPaidBtn"),
  detailCloseBtn: () => $("detailCloseBtn"),

  // Confirm Action Modal
  confirmActionModal: () => $("confirmActionModal"),
  confirmActionTitle: () => $("confirmActionTitle"),
  confirmActionMessage: () => $("confirmActionMessage"),
  closeConfirmActionModal: () => $("closeConfirmActionModal"),
  cancelConfirmActionBtn: () => $("cancelConfirmActionBtn"),
  executeConfirmActionBtn: () => $("executeConfirmActionBtn"),

  // Toast
  toastContainer: () => $("toastContainer"),
};
