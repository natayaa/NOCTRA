// ============================================================
// inventories/handlers/events.js - Event Bindings
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { loadInventoryItems } from "../index.js";
import { selectItem } from "../index.js";
import {
  openCreateModal,
  openEditModal,
  closeModal,
  handleFormSubmit,
} from "./modals.js";
import {
  openStockAdjustModal,
  closeStockAdjustModal,
  handleStockAdjust,
} from "./stock.js";
import { openHistoryModal, closeHistoryModal } from "./history.js";
import {
  openReorderModal,
  closeReorderModal,
  handleReorderSubmit,
} from "./reorder.js";
import { confirmDelete, exportInventory, filterByCategory } from "./actions.js";
import { renderAlerts } from "../renderers/alerts.js";
import { InventoryAPI } from "../api.js";
import { showToast } from "../toast.js";

export function bindEvents() {
  // Pagination
  DOM.prevPageBtn()?.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage--;
      loadInventoryItems();
    }
  });
  DOM.nextPageBtn()?.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      state.currentPage++;
      loadInventoryItems();
    }
  });

  // Search with debounce
  let searchTimeout;
  DOM.searchInventory()?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.currentPage = 1;
      loadInventoryItems();
    }, 300);
  });

  // Filters
  DOM.categoryFilter()?.addEventListener("change", (e) => {
    state.filters.category = e.target.value;
    state.currentPage = 1;
    loadInventoryItems();
  });
  DOM.stockFilter()?.addEventListener("change", (e) => {
    const value = e.target.value;
    state.filters.low_stock_only = value === "low" || value === "critical";
    state.filters.stock_status = value;
    state.currentPage = 1;
    loadInventoryItems();
  });
  DOM.statusFilter()?.addEventListener("change", (e) => {
    state.filters.status = e.target.value;
    state.currentPage = 1;
    loadInventoryItems();
  });

  // Buttons
  DOM.addItemBtn()?.addEventListener("click", openCreateModal);
  DOM.exportInventoryBtn()?.addEventListener("click", exportInventory);
  DOM.refreshAlertsBtn()?.addEventListener("click", async () => {
    const alerts = await InventoryAPI.fetchAlerts();
    renderAlerts(alerts);
    showToast("Alerts refreshed!", "success");
  });

  // Close modals
  DOM.closeInventoryModal()?.addEventListener("click", closeModal);
  DOM.cancelModalBtn()?.addEventListener("click", closeModal);
  DOM.inventoryModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.inventoryModal()) closeModal();
  });

  // Stock Adjust
  DOM.closeStockAdjustModal()?.addEventListener("click", closeStockAdjustModal);
  DOM.cancelStockAdjustBtn()?.addEventListener("click", closeStockAdjustModal);
  DOM.stockAdjustModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.stockAdjustModal()) closeStockAdjustModal();
  });

  // History
  DOM.closeHistoryModal()?.addEventListener("click", closeHistoryModal);
  DOM.closeHistoryModalBtn()?.addEventListener("click", closeHistoryModal);
  DOM.historyModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.historyModal()) closeHistoryModal();
  });

  // Reorder
  DOM.closeReorderModal()?.addEventListener("click", closeReorderModal);
  DOM.cancelReorderBtn()?.addEventListener("click", closeReorderModal);
  DOM.reorderModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.reorderModal()) closeReorderModal();
  });

  // Detail Panel Actions
  DOM.editItemBtn()?.addEventListener("click", () => {
    if (state.selectedItemId) openEditModal(state.selectedItemId);
  });
  DOM.deleteItemBtn()?.addEventListener("click", () => {
    if (state.selectedItemId) confirmDelete(state.selectedItemId);
  });
  DOM.adjustStockBtn()?.addEventListener("click", () => {
    if (state.selectedItemId) openStockAdjustModal(state.selectedItemId);
  });
  DOM.historyBtn()?.addEventListener("click", () => {
    if (state.selectedItemId) openHistoryModal(state.selectedItemId);
  });
  DOM.reorderBtn()?.addEventListener("click", () => {
    if (state.selectedItemId) openReorderModal(state.selectedItemId);
  });

  // Form submissions
  DOM.inventoryForm()?.addEventListener("submit", handleFormSubmit);
  DOM.stockAdjustForm()?.addEventListener("submit", handleStockAdjust);
  DOM.reorderForm()?.addEventListener("submit", handleReorderSubmit);
}
