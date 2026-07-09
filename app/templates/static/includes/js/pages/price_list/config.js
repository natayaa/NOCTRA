// ============================================================
// price_list/config.js - Configuration & State
// ============================================================

export const CONFIG = {
  API_BASE_URL: "/api/api",
  ITEMS_PER_PAGE: 10,
  TOAST_DURATION: 4000,
};

export const state = {
  items: [],
  currentPage: 1,
  totalPages: 1,
  totalItems: 0,
  editingId: null,
  filters: {
    search: "",
    category: "",
    status: "",
    vehicle_brand: "",
    active_only: true,
  },
  categories: [],
  isLoading: false,
};
