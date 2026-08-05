// ============================================================
// restored-bikes/config.js - Configuration & State
// ============================================================

export const CONFIG = {
  API_BASE_URL: "/api/api",
  ITEMS_PER_PAGE: 12,
  TOAST_DURATION: 4000,
  MAX_PHOTOS: 20,
  MAX_DOCUMENTS: 10,
};

export const state = {
  bikes: [],
  currentPage: 1,
  totalPages: 1,
  totalItems: 0,
  currentBikeId: null,
  editingId: null,
  filters: {
    search: "",
    status: "",
    brand: "",
  },
  gallery: {
    photos: [],
    uploading: false,
  },
  documents: [],
  isLoading: false,
};

export function resetState() {
  state.bikes = [];
  state.currentPage = 1;
  state.totalPages = 1;
  state.totalItems = 0;
  state.currentBikeId = null;
  state.editingId = null;
  state.filters.search = "";
  state.filters.status = "";
  state.filters.brand = "";
  state.isLoading = false;
}
