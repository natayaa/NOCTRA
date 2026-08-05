// ============================================================
// price_list/handlers/events.js - Event Bindings
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { loadPriceItems } from "../index.js";
import {
  openCreateModal,
  openEditModal,
  closeModal,
  handleFormSubmit,
} from "./modals.js";
import { openHistoryModal, closeHistoryModal } from "./history.js";
import {
  openBulkModal,
  closeBulkModal,
  handleBulkSubmit,
  bindBulkEvents,
} from "./bulk.js";
import { confirmDelete, exportPriceItems } from "./actions.js";

export function bindEvents() {
  // Pagination
  DOM.prevPageBtn()?.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage--;
      loadPriceItems();
    }
  });

  DOM.nextPageBtn()?.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      state.currentPage++;
      loadPriceItems();
    }
  });

  // Search with debounce
  let searchTimeout;
  DOM.searchPrice()?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.currentPage = 1;
      loadPriceItems();
    }, 300);
  });

  // Filters
  DOM.categoryFilter()?.addEventListener("change", (e) => {
    state.filters.category = e.target.value;
    state.currentPage = 1;
    loadPriceItems();
  });

  DOM.statusFilter()?.addEventListener("change", (e) => {
    const value = e.target.value;
    state.filters.status = value;
    state.filters.active_only = value === "" ? true : value === "active";
    state.currentPage = 1;
    loadPriceItems();
  });

  DOM.vehicleFilter()?.addEventListener("change", (e) => {
    state.filters.vehicle_brand = e.target.value;
    state.currentPage = 1;
    loadPriceItems();
  });

  // Buttons
  DOM.addPriceBtn()?.addEventListener("click", openCreateModal);
  DOM.exportPriceBtn()?.addEventListener("click", exportPriceItems);

  // Price Modal
  DOM.closeModalBtn()?.addEventListener("click", closeModal);
  DOM.cancelModalBtn()?.addEventListener("click", closeModal);
  DOM.priceModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.priceModal()) closeModal();
  });
  DOM.priceForm()?.addEventListener("submit", handleFormSubmit);

  // History Modal
  DOM.closeHistoryModal()?.addEventListener("click", closeHistoryModal);
  DOM.closeHistoryModalBtn()?.addEventListener("click", closeHistoryModal);
  DOM.historyModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.historyModal()) closeHistoryModal();
  });

  // Bulk Modal
  DOM.closeBulkModal()?.addEventListener("click", closeBulkModal);
  DOM.cancelBulkBtn()?.addEventListener("click", closeBulkModal);
  DOM.bulkModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.bulkModal()) closeBulkModal();
  });
  DOM.bulkForm()?.addEventListener("submit", handleBulkSubmit);

  // Bulk preview events
  bindBulkEvents();
}

// Keyboard shortcuts
export function bindKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    // Escape
    if (e.key === "Escape") {
      if (DOM.priceModal()?.classList.contains("active")) closeModal();
      if (DOM.historyModal()?.classList.contains("active")) closeHistoryModal();
      if (DOM.bulkModal()?.classList.contains("active")) closeBulkModal();
    }

    // Ctrl+N - New item
    if (e.ctrlKey && e.key === "n") {
      e.preventDefault();
      openCreateModal();
    }

    // Ctrl+F - Focus search
    if (e.ctrlKey && e.key === "f") {
      e.preventDefault();
      DOM.searchPrice()?.focus();
    }

    // Ctrl+E - Export
    if (e.ctrlKey && e.key === "e") {
      e.preventDefault();
      exportPriceItems();
    }

    // Ctrl+B - Bulk update
    if (e.ctrlKey && e.key === "b") {
      e.preventDefault();
      openBulkModal();
    }
  });
}
