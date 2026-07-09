// ============================================================
// payments/config.js - Configuration & State
// ============================================================

export const CONFIG = {
  API_BASE_URL: "/api/api",
  PAYMENTS_PER_PAGE: 10,
  INVOICES_PER_PAGE: 10,
  TOAST_DURATION: 4000,
};

export const state = {
  // Payments
  payments: [],
  paymentsCurrentPage: 1,
  paymentsTotalPages: 1,
  paymentsTotalItems: 0,

  // Invoices
  invoices: [],
  invoicesCurrentPage: 1,
  invoicesTotalPages: 1,
  invoicesTotalItems: 0,

  // Filters
  filters: {
    search: "",
    status: "",
    type: "",
    startDate: "",
    endDate: "",
  },

  // Active tab
  activeTab: "payments",

  isLoading: false,
};
