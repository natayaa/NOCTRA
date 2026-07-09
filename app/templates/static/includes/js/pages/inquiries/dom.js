// ============================================================
// inquiries/dom.js - DOM References & Utilities
// ============================================================

export const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

export const $$ = (selector) => document.querySelectorAll(selector);

export const DOM = {
  // Dashboard
  totalCount: () => $("totalCount"),
  newCount: () => $("newCount"),
  quotedCount: () => $("quotedCount"),
  convertedCount: () => $("convertedCount"),

  // Toolbar
  searchInquiry: () => $("searchInquiry"),
  statusFilter: () => $("statusFilter"),
  exportInquiriesBtn: () => $("exportInquiriesBtn"),

  // Table
  inquiriesBody: () => $("inquiriesBody"),
  prevPage: () => $("prevPage"),
  nextPage: () => $("nextPage"),
  pageInfo: () => $("pageInfo"),

  // Drawer
  drawer: () => $("inquiryDrawer"),
  drawerCustomerName: () => $("drawerCustomerName"),
  drawerStatusBadge: () => $("drawerStatusBadge"),
  closeDrawer: () => $("closeDrawer"),
  drawerBackdrop: () => $("drawerBackdrop"),

  // Drawer - Customer
  drawerName: () => $("drawerName"),
  drawerPhone: () => $("drawerPhone"),
  drawerEmail: () => $("drawerEmail"),
  drawerProvince: () => $("drawerProvince"),
  drawerCity: () => $("drawerCity"),

  // Drawer - Vehicle & Project
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

  // Drawer - Financial
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

  // Drawer - Labor
  drawerLaborItems: () => $("drawerLaborItems"),

  // Drawer - Material
  drawerMaterialUsages: () => $("drawerMaterialUsages"),

  // Drawer - Payment
  drawerTotalDeposit: () => $("drawerTotalDeposit"),
  drawerTotalPaid: () => $("drawerTotalPaid"),
  drawerTotalPending: () => $("drawerTotalPending"),
  drawerRemaining: () => $("drawerRemaining"),
  drawerPaymentHistory: () => $("drawerPaymentHistory"),
  addDepositBtn: () => $("addDepositBtn"),
  addPaymentBtn: () => $("addPaymentBtn"),
  viewInvoicesBtn: () => $("viewInvoicesBtn"),

  // Drawer - Timeline
  drawerTimeline: () => $("drawerTimeline"),

  // Drawer - Notes
  drawerNotes: () => $("drawerNotes"),
  noteCounter: () => $("noteCounter"),

  // Drawer - Before/After
  beforeTrack: () => $("beforeTrack"),
  afterTrack: () => $("afterTrack"),

  // Drawer - Actions
  drawerApproveBtn: () => $("drawerApproveBtn"),
  drawerQuoteBtn: () => $("drawerQuoteBtn"),
  drawerRejectBtn: () => $("drawerRejectBtn"),
  drawerWhatsappBtn: () => $("drawerWhatsappBtn"),
  drawerConvertBtn: () => $("drawerConvertBtn"),
  drawerViewProjectBtn: () => $("drawerViewProjectBtn"),

  // Modals
  convertModal: () => $("convertModal"),
  convertForm: () => $("convertForm"),
  convertStartDate: () => $("convertStartDate"),
  convertTargetDelivery: () => $("convertTargetDelivery"),
  closeConvertModal: () => $("closeConvertModal"),
  cancelConvertBtn: () => $("cancelConvertBtn"),

  quoteModal: () => $("quoteModal"),
  quoteForm: () => $("quoteForm"),
  quoteCost: () => $("quoteCost"),
  quoteNotes: () => $("quoteNotes"),
  closeQuoteModal: () => $("closeQuoteModal"),
  cancelQuoteBtn: () => $("cancelQuoteBtn"),

  rejectModal: () => $("rejectModal"),
  rejectForm: () => $("rejectForm"),
  rejectReason: () => $("rejectReason"),
  closeRejectModal: () => $("closeRejectModal"),
  cancelRejectBtn: () => $("cancelRejectBtn"),

  // Lightbox
  lightboxOverlay: () => $("lightboxOverlay"),
  lightboxImage: () => $("lightboxImage"),
  lightboxClose: () => $("lightboxClose"),
  lightboxPrev: () => $("lightboxPrev"),
  lightboxNext: () => $("lightboxNext"),

  // Toast
  toastContainer: () => $("toastContainer"),
};

// Create drawer backdrop
export const drawerBackdrop = document.createElement("div");
drawerBackdrop.className = "drawer-backdrop";
drawerBackdrop.id = "drawerBackdrop";
document.body.appendChild(drawerBackdrop);
