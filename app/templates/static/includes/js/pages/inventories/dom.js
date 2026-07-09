// ============================================================
// inventories/dom.js - DOM References
// ============================================================

export const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

export const $$ = (selector) => document.querySelectorAll(selector);

export const DOM = {
  // Dashboard
  totalValue: () => $("totalValue"),
  totalItems: () => $("totalItems"),
  lowStockCount: () => $("lowStockCount"),
  monthlyUsage: () => $("monthlyUsage"),

  // Alerts
  alertList: () => $("alertList"),
  refreshAlertsBtn: () => $("refreshAlertsBtn"),

  // Sidebar
  searchInventory: () => $("searchInventory"),
  categoryFilter: () => $("categoryFilter"),
  stockFilter: () => $("stockFilter"),
  statusFilter: () => $("statusFilter"),
  categoryList: () => $("categoryList"),
  recentMovements: () => $("recentMovements"),

  // Table
  inventoryItemsList: () => $("inventoryItemsList"),

  // Pagination
  prevPageBtn: () => $("prevPageBtn"),
  nextPageBtn: () => $("nextPageBtn"),
  pageInfo: () => $("pageInfo"),

  // Buttons
  exportInventoryBtn: () => $("exportInventoryBtn"),
  addItemBtn: () => $("addItemBtn"),

  // Detail Panel
  itemDetailContent: () => $("itemDetailContent"),
  editItemBtn: () => $("editItemBtn"),
  deleteItemBtn: () => $("deleteItemBtn"),
  detailActionsBottom: () => $("detailActionsBottom"),
  reorderBtn: () => $("reorderBtn"),
  historyBtn: () => $("historyBtn"),
  adjustStockBtn: () => $("adjustStockBtn"),

  // Inventory Modal
  inventoryModal: () => $("inventoryModal"),
  modalTitle: () => $("modalTitle"),
  editId: () => $("editId"),
  inventoryForm: () => $("inventoryForm"),
  itemName: () => $("itemName"),
  itemCategory: () => $("itemCategory"),
  itemSubCategory: () => $("itemSubCategory"),
  itemUnit: () => $("itemUnit"),
  itemStock: () => $("itemStock"),
  reorderLevel: () => $("reorderLevel"),
  itemCost: () => $("itemCost"),
  itemSellingPrice: () => $("itemSellingPrice"),
  itemSku: () => $("itemSku"),
  itemBarcode: () => $("itemBarcode"),
  itemLocation: () => $("itemLocation"),
  itemSupplier: () => $("itemSupplier"),
  itemDescription: () => $("itemDescription"),
  submitBtn: () => $("submitBtn"),
  cancelModalBtn: () => $("cancelModalBtn"),
  closeInventoryModal: () => $("closeInventoryModal"),

  // Stock Adjust Modal
  stockAdjustModal: () => $("stockAdjustModal"),
  stockAdjustForm: () => $("stockAdjustForm"),
  adjustItemId: () => $("adjustItemId"),
  adjustCurrentStock: () => $("adjustCurrentStock"),
  adjustNewStock: () => $("adjustNewStock"),
  adjustReasonSelect: () => $("adjustReasonSelect"),
  adjustNotes: () => $("adjustNotes"),
  cancelStockAdjustBtn: () => $("cancelStockAdjustBtn"),
  closeStockAdjustModal: () => $("closeStockAdjustModal"),

  // History Modal
  historyModal: () => $("historyModal"),
  historyBody: () => $("historyBody"),
  historyItemName: () => $("historyItemName"),
  closeHistoryModal: () => $("closeHistoryModal"),
  closeHistoryModalBtn: () => $("closeHistoryModalBtn"),

  // Reorder Modal
  reorderModal: () => $("reorderModal"),
  reorderForm: () => $("reorderForm"),
  reorderItemId: () => $("reorderItemId"),
  reorderItemName: () => $("reorderItemName"),
  reorderCurrentStock: () => $("reorderCurrentStock"),
  reorderThreshold: () => $("reorderThreshold"),
  reorderQuantity: () => $("reorderQuantity"),
  reorderSupplier: () => $("reorderSupplier"),
  cancelReorderBtn: () => $("cancelReorderBtn"),
  closeReorderModal: () => $("closeReorderModal"),

  // Toast
  toastContainer: () => $("toastContainer"),
};
