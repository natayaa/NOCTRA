// ============================================================
// inquiries/config.js - Configuration & State
// ============================================================

export const CONFIG = {
  API_BASE_URL: "/api/api",
  INQUIRIES_PER_PAGE: 10,
  TOAST_DURATION: 4000,
  MAX_ACTIVITIES: 50,
};

export const state = {
  inquiries: [],
  currentPage: 1,
  totalPages: 1,
  totalItems: 0,
  currentInquiryId: null,
  _currentInquiry: null,
  _convertInquiryId: null,
  _quoteInquiryId: null,
  _rejectInquiryId: null,
  inventoryItems: [],
  activities: [],
  notes: [],
  filters: {
    search: "",
    status: "",
  },
  carousels: {
    before: { index: 0, images: [] },
    after: { index: 0, images: [] },
  },
  lightbox: {
    images: [],
    currentIndex: 0,
    isOpen: false,
  },
  isLoading: false,
};
