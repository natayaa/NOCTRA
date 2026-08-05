// inquiries/dom.js - DOM References & Utilities (FIXED & IMPROVED)

// ============================================================
// DOM HELPERS
// ============================================================

export const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

export const $$ = (selector) => document.querySelectorAll(selector);

export const $exists = (id) => {
  return !!document.getElementById(id);
};

export const $safe = (id, fallback = null) => {
  const el = document.getElementById(id);
  return el || fallback;
};

// ============================================================
// DRAWER BACKDROP
// ============================================================

export const drawerBackdrop = document.createElement("div");
drawerBackdrop.className = "drawer-backdrop";
drawerBackdrop.id = "drawerBackdrop";
document.body.appendChild(drawerBackdrop);

// ============================================================
// DOM REFERENCES
// ============================================================

export const DOM = {
  // ==================== Dashboard ====================
  totalCount: () => $("totalCount"),
  newCount: () => $("newCount"),
  quotedCount: () => $("quotedCount"),
  convertedCount: () => $("convertedCount"),

  // ==================== Toolbar ====================
  searchInquiry: () => $("searchInquiry"),
  statusFilter: () => $("statusFilter"),
  exportInquiriesBtn: () => $("exportInquiriesBtn"),

  // ==================== Table ====================
  inquiriesBody: () => $("inquiriesBody"),
  prevPage: () => $("prevPage"),
  nextPage: () => $("nextPage"),
  pageInfo: () => $("pageInfo"),

  // ==================== Drawer ====================
  drawer: () => $("inquiryDrawer"),
  drawerCustomerName: () => $("drawerCustomerName"),
  drawerStatusBadge: () => $("drawerStatusBadge"),
  closeDrawer: () => $("closeDrawer"),
  drawerBackdrop: () => $("drawerBackdrop"),

  // ==================== Drawer - Customer ====================
  drawerName: () => $("drawerName"),
  drawerPhone: () => $("drawerPhone"),
  drawerEmail: () => $("drawerEmail"),
  drawerProvince: () => $("drawerProvince"),
  drawerCity: () => $("drawerCity"),

  // ==================== Drawer - Vehicle & Project ====================
  drawerBrand: () => $("drawerBrand"),
  drawerModel: () => $("drawerModel"),
  drawerYear: () => $("drawerYear"),
  drawerPlate: () => $("drawerPlate"),
  drawerPrevRepaint: () => $("drawerPrevRepaint"),
  drawerBikeModified: () => $("drawerBikeModified"),
  drawerCondition: () => $("drawerCondition"),
  drawerType: () => $("drawerType"),
  drawerServices: () => $("drawerServices"),
  drawerFinish: () => $("drawerFinish"),
  drawerColor: () => $("drawerColor"),
  drawerBudget: () => $("drawerBudget"),
  drawerDeadline: () => $("drawerDeadline"),
  drawerPriority: () => $("drawerPriority"),
  drawerDescription: () => $("drawerDescription"),
  drawerReference: () => $("drawerReference"),

  // ==================== Drawer - Financial ====================
  drawerEstCost: () => $("drawerEstCost"),
  drawerActualCost: () => $("drawerActualCost"),
  drawerEstRevenue: () => $("drawerEstRevenue"),
  drawerActualRevenue: () => $("drawerActualRevenue"),
  drawerDeposit: () => $("drawerDeposit"),
  drawerDepositStatus: () => $("drawerDepositStatus"),
  drawerProfit: () => $("drawerProfit"),
  drawerMargin: () => $("drawerMargin"),
  drawerMaterialCost: () => $("drawerMaterialCost"),
  drawerLaborCost: () => $("drawerLaborCost"),
  drawerOtherExpenses: () => $("drawerOtherExpenses"),
  drawerTotalCost: () => $("drawerTotalCost"),
  budgetPercentage: () => $("budgetPercentage"),
  budgetProgressFill: () => $("budgetProgressFill"),

  // ==================== Drawer - Labor ====================
  drawerLaborItems: () => $("drawerLaborItems"),

  // ==================== Drawer - Material ====================
  drawerMaterialUsages: () => $("drawerMaterialUsages"),

  // ==================== Drawer - Payment ====================
  drawerTotalDeposit: () => $("drawerTotalDeposit"),
  drawerTotalPaid: () => $("drawerTotalPaid"),
  drawerTotalPending: () => $("drawerTotalPending"),
  drawerRemaining: () => $("drawerRemaining"),
  drawerPaymentHistory: () => $("drawerPaymentHistory"),
  addDepositBtn: () => $("addDepositBtn"),
  addPaymentBtn: () => $("addPaymentBtn"),
  viewInvoicesBtn: () => $("viewInvoicesBtn"),

  // ==================== Drawer - Timeline ====================
  drawerTimeline: () => $("drawerTimeline"),

  // ==================== Drawer - Notes ====================
  drawerNotes: () => $("drawerNotes"),
  noteCounter: () => $("noteCounter"),

  // ==================== Drawer - Before/After ====================
  beforeTrack: () => $("beforeTrack"),
  afterTrack: () => $("afterTrack"),

  // ==================== Drawer - Actions ====================
  drawerApproveBtn: () => $("drawerApproveBtn"),
  drawerQuoteBtn: () => $("drawerQuoteBtn"),
  drawerRejectBtn: () => $("drawerRejectBtn"),
  drawerWhatsappBtn: () => $("drawerWhatsappBtn"),
  drawerConvertBtn: () => $("drawerConvertBtn"),
  drawerViewProjectBtn: () => $("drawerViewProjectBtn"),
  drawerCompleteBtn: () => $("drawerCompleteBtn"),

  // ==================== Convert Modal ====================
  convertModal: () => $("convertModal"),
  convertForm: () => $("convertForm"),
  convertStartDate: () => $("convertStartDate"),
  convertTargetDelivery: () => $("convertTargetDelivery"),
  closeConvertModal: () => $("closeConvertModal"),
  cancelConvertBtn: () => $("cancelConvertBtn"),

  // ==================== Quote Modal ====================
  quoteModal: () => $("quoteModal"),
  quoteForm: () => $("quoteForm"),
  quoteCost: () => $("quoteCost"),
  quoteNotes: () => $("quoteNotes"),
  closeQuoteModal: () => $("closeQuoteModal"),
  cancelQuoteBtn: () => $("cancelQuoteBtn"),

  // ==================== Reject Modal ====================
  rejectModal: () => $("rejectModal"),
  rejectForm: () => $("rejectForm"),
  rejectReason: () => $("rejectReason"),
  closeRejectModal: () => $("closeRejectModal"),
  cancelRejectBtn: () => $("cancelRejectBtn"),

  // ==================== Confirm Payment Modal ====================
  confirmPaymentModal: () => $("confirmPaymentModal"),
  confirmPaymentDetails: () => $("confirmPaymentDetails"),
  closeConfirmPaymentModal: () => $("closeConfirmPaymentModal"),
  cancelConfirmPaymentBtn: () => $("cancelConfirmPaymentBtn"),
  confirmPaymentBtn: () => $("confirmPaymentBtn"),

  // ==================== Delete Payment Modal ====================
  deletePaymentModal: () => $("deletePaymentModal"),
  deletePaymentDetails: () => $("deletePaymentDetails"),
  closeDeletePaymentModal: () => $("closeDeletePaymentModal"),
  cancelDeletePaymentBtn: () => $("cancelDeletePaymentBtn"),
  deletePaymentBtn: () => $("deletePaymentBtn"),

  // ==================== Payment Modal ====================
  paymentModal: () => $("paymentModal"),
  paymentForm: () => $("paymentForm"),
  paymentInquiryId: () => $("paymentInquiryId"),
  paymentProjectId: () => $("paymentProjectId"),
  paymentInvoiceId: () => $("paymentInvoiceId"),
  paymentType: () => $("paymentType"),
  paymentAmount: () => $("paymentAmount"),
  paymentMethod: () => $("paymentMethod"),
  paymentReference: () => $("paymentReference"),
  paymentDate: () => $("paymentDate"),
  paymentDueDate: () => $("paymentDueDate"),
  paymentNotes: () => $("paymentNotes"),
  closePaymentModal: () => $("closePaymentModal"),
  cancelPaymentBtn: () => $("cancelPaymentBtn"),

  // ==================== Invoice Modal ====================
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

  // ==================== Lightbox ====================
  lightboxOverlay: () => $("lightboxOverlay"),
  lightboxImage: () => $("lightboxImage"),
  lightboxClose: () => $("lightboxClose"),
  lightboxPrev: () => $("lightboxPrev"),
  lightboxNext: () => $("lightboxNext"),

  // ==================== Toast ====================
  toastContainer: () => $("toastContainer"),
};

// ============================================================
// HELPER FUNCTIONS
// ============================================================

/**
 * Toggle element visibility
 */
export function toggleElement(id, show) {
  const el = $safe(id);
  if (!el) return;
  el.style.display = show ? "" : "none";
}

/**
 * Show element
 */
export function showElement(id) {
  toggleElement(id, true);
}

/**
 * Hide element
 */
export function hideElement(id) {
  toggleElement(id, false);
}

/**
 * Get element value safely
 */
export function getValue(id, fallback = "") {
  const el = $safe(id);
  if (!el) return fallback;
  return el.value || fallback;
}

/**
 * Set element value safely
 */
export function setValue(id, value) {
  const el = $safe(id);
  if (!el) return;
  el.value = value;
}

/**
 * Get element text safely
 */
export function getText(id, fallback = "") {
  const el = $safe(id);
  if (!el) return fallback;
  return el.textContent || fallback;
}

/**
 * Set element text safely
 */
export function setText(id, text) {
  const el = $safe(id);
  if (!el) return;
  el.textContent = text;
}

/**
 * Get element HTML safely
 */
export function getHtml(id, fallback = "") {
  const el = $safe(id);
  if (!el) return fallback;
  return el.innerHTML || fallback;
}

/**
 * Set element HTML safely
 */
export function setHtml(id, html) {
  const el = $safe(id);
  if (!el) return;
  el.innerHTML = html;
}

/**
 * Add class to element
 */
export function addClass(id, className) {
  const el = $safe(id);
  if (!el) return;
  el.classList.add(className);
}

/**
 * Remove class from element
 */
export function removeClass(id, className) {
  const el = $safe(id);
  if (!el) return;
  el.classList.remove(className);
}

/**
 * Toggle class on element
 */
export function toggleClass(id, className) {
  const el = $safe(id);
  if (!el) return;
  el.classList.toggle(className);
}

/**
 * Check if element has class
 */
export function hasClass(id, className) {
  const el = $safe(id);
  if (!el) return false;
  return el.classList.contains(className);
}

// ============================================================
// EXPORT ALL
// ============================================================

export default {
  $,
  $$,
  $exists,
  $safe,
  DOM,
  drawerBackdrop,
  toggleElement,
  showElement,
  hideElement,
  getValue,
  setValue,
  getText,
  setText,
  getHtml,
  setHtml,
  addClass,
  removeClass,
  toggleClass,
  hasClass,
};
