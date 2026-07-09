// ============================================================
// inventories/config.js - Configuration & State
// ============================================================

export const CONFIG = {
  API_BASE_URL: "/api/api",
  ITEMS_PER_PAGE: 10,
  TOAST_DURATION: 4000,
  MAX_MOVEMENTS: 5,
};

export const state = {
  items: [],
  currentPage: 1,
  totalPages: 1,
  totalItems: 0,
  selectedItemId: null,
  selectedItemData: null,
  editingId: null,
  filters: {
    search: "",
    category: "",
    status: "",
    stock_status: "",
    low_stock_only: false,
  },
  categories: [],
  suppliers: [],
  isLoading: false,
};
