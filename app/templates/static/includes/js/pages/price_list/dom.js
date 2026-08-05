// ============================================================
// price_list/dom.js - DOM References
// ============================================================

export const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

export const $$ = (selector) => document.querySelectorAll(selector);

export const DOM = {
  // Dashboard
  totalItems: () => $("totalItems"),
  activeItems: () => $("activeItems"),
  expiringItems: () => $("expiringItems"),
  categoryCount: () => $("categoryCount"),

  // Toolbar
  searchPrice: () => $("searchPrice"),
  categoryFilter: () => $("categoryFilter"),
  statusFilter: () => $("statusFilter"),
  vehicleFilter: () => $("vehicleFilter"),
  exportPriceBtn: () => $("exportPriceBtn"),
  addPriceBtn: () => $("addPriceBtn"),

  // Table
  priceTableBody: () => $("priceTableBody"),

  // Pagination
  prevPageBtn: () => $("prevPageBtn"),
  nextPageBtn: () => $("nextPageBtn"),
  pageInfo: () => $("pageInfo"),

  // Price Modal
  priceModal: () => $("priceModal"),
  modalTitle: () => $("modalTitle"),
  modalSubtitle: () => $("modalSubtitle"),
  editId: () => $("editId"),
  priceForm: () => $("priceForm"),
  category: () => $("category"),
  subCategory: () => $("subCategory"),
  name: () => $("name"),
  price: () => $("price"),
  costPrice: () => $("costPrice"),
  unit: () => $("unit"),
  sku: () => $("sku"),
  vehicleBrand: () => $("vehicleBrand"),
  vehicleModel: () => $("vehicleModel"),
  effectiveDate: () => $("effectiveDate"),
  expiryDate: () => $("expiryDate"),
  minQuantity: () => $("minQuantity"),
  maxQuantity: () => $("maxQuantity"),
  discountPercentage: () => $("discountPercentage"),
  estimatedDuration: () => $("estimatedDuration"),
  isActive: () => $("isActive"),
  isTaxable: () => $("isTaxable"),
  isDiscountAllowed: () => $("isDiscountAllowed"),
  description: () => $("description"),
  submitBtn: () => $("submitBtn"),
  cancelModalBtn: () => $("cancelModalBtn"),
  closeModalBtn: () => $("closeModalBtn"),

  // History Modal
  historyModal: () => $("historyModal"),
  historyItemName: () => $("historyItemName"),
  historyBody: () => $("historyBody"),
  totalChanges: () => $("totalChanges"),
  currentPrice: () => $("currentPrice"),
  firstPrice: () => $("firstPrice"),
  avgChange: () => $("avgChange"),
  closeHistoryModal: () => $("closeHistoryModal"),
  closeHistoryModalBtn: () => $("closeHistoryModalBtn"),

  // Bulk Modal
  bulkModal: () => $("bulkModal"),
  bulkForm: () => $("bulkForm"),
  bulkCategory: () => $("bulkCategory"),
  bulkPercentage: () => $("bulkPercentage"),
  bulkVehicleBrand: () => $("bulkVehicleBrand"),
  bulkReason: () => $("bulkReason"),
  bulkPreview: () => $("bulkPreview"),
  bulkPreviewText: () => $("bulkPreviewText"),
  cancelBulkBtn: () => $("cancelBulkBtn"),
  closeBulkModal: () => $("closeBulkModal"),

  // Toast
  toastContainer: () => $("toastContainer"),
};
