// ============================================================
// billing/config.js - Configuration & State
// ============================================================

export const CONFIG = {
  API_BASE_URL: "/api/api",
  QUOTES_PER_PAGE: 10,
  INVOICES_PER_PAGE: 10,
  TOAST_DURATION: 4000,
};

export const state = {
  // Quotations
  quotations: [],
  quotePage: 1,
  quoteTotalPages: 1,
  quoteTotalItems: 0,

  // Invoices
  invoices: [],
  invoicePage: 1,
  invoiceTotalPages: 1,
  invoiceTotalItems: 0,

  // Filters
  filters: {
    search: "",
    status: "",
    type: "", // 'quotation' | 'invoice'
  },

  // Active tab
  activeTab: "quotations", // 'quotations' | 'invoices'

  // Modals
  currentInvoiceId: null,
  currentQuotationId: null,
  pendingAction: null, // for confirm modal

  isLoading: false,
};

export function resetState() {
  state.quotations = [];
  state.invoices = [];
  state.quotePage = 1;
  state.invoicePage = 1;
  state.filters.search = "";
  state.filters.status = "";
  state.filters.type = "";
  state.activeTab = "quotations";
  state.currentInvoiceId = null;
  state.currentQuotationId = null;
  state.pendingAction = null;
}
