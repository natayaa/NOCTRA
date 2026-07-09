// ============================================================
// price_list/index.js - Main Entry Point
// ============================================================

import { state, CONFIG } from "./config.js";
import { DOM } from "./dom.js";
import { PriceAPI } from "./api.js";
import { showToast } from "./toast.js";
import {
  renderItems,
  showLoadingState,
  updatePagination,
  updateDashboard,
  updateCategoryFilter,
} from "./renderers/table.js";
import {
  openCreateModal,
  openEditModal,
  closeModal,
} from "./handlers/modals.js";
import { openHistoryModal, closeHistoryModal } from "./handlers/history.js";
import { openBulkModal, closeBulkModal } from "./handlers/bulk.js";
import { confirmDelete, exportPriceItems } from "./handlers/actions.js";
import { bindEvents, bindKeyboardShortcuts } from "./handlers/events.js";

// ============================================================
// MAIN LOAD FUNCTION
// ============================================================
export async function loadPriceItems() {
  console.log("🔄 Loading price items...");

  const data = await PriceAPI.fetchItems(state.currentPage, state.filters);

  if (!data) {
    const body = DOM.priceTableBody();
    if (body) {
      body.innerHTML = `
                <tr>
                    <td colspan="8" class="no-data">
                        <i class="fas fa-exclamation-triangle" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                        Failed to load price items. Please try again.
                        <br><br>
                        <button class="btn-primary" onclick="window.loadPriceItems()">
                            <i class="fas fa-rotate"></i> Retry
                        </button>
                    </td>
                </tr>
            `;
    }
    updatePagination(1, 1, 0);
    return;
  }

  // Handle different response structures
  let items = [];
  let totalPages = 1;
  let totalItems = 0;

  if (data.data) {
    items = Array.isArray(data.data) ? data.data : [data.data];
    totalItems =
      data.total || data.total_items || data.totalItems || items.length;
    totalPages =
      data.total_pages ||
      data.totalPages ||
      data.pages ||
      Math.ceil(totalItems / CONFIG.ITEMS_PER_PAGE);
  } else if (Array.isArray(data)) {
    items = data;
    totalItems = items.length;
    totalPages = Math.ceil(totalItems / CONFIG.ITEMS_PER_PAGE);
  } else if (data.items) {
    items = Array.isArray(data.items) ? data.items : [data.items];
    totalItems =
      data.total || data.total_items || data.totalItems || items.length;
    totalPages =
      data.total_pages ||
      data.totalPages ||
      Math.ceil(totalItems / CONFIG.ITEMS_PER_PAGE);
  } else {
    items = Array.isArray(data) ? data : [];
    totalItems = items.length;
    totalPages = Math.ceil(totalItems / CONFIG.ITEMS_PER_PAGE);
  }

  state.items = items || [];
  state.totalPages = Math.max(1, totalPages);
  state.totalItems = totalItems;

  renderItems(state.items);
  updatePagination(state.currentPage, state.totalPages, state.totalItems);

  // Load statistics and categories in parallel
  const [stats, categories] = await Promise.all([
    PriceAPI.fetchStatistics(),
    PriceAPI.fetchCategories(),
  ]);

  updateDashboard(stats);
  if (categories) updateCategoryFilter(categories);

  console.log("✅ Price items loaded successfully");
}

// ============================================================
// INITIALIZATION
// ============================================================
export async function initPriceList() {
  console.log("🚀 Initializing Price List page...");
  try {
    bindEvents();
    bindKeyboardShortcuts();
    await loadPriceItems();
    console.log("📋 Price List page initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize Price List page:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

// ============================================================
// EXPOSE TO GLOBAL (for inline onclick handlers)
// ============================================================
window.openCreateModal = openCreateModal;
window.openEditModal = openEditModal;
window.openHistoryModal = openHistoryModal;
window.openBulkModal = openBulkModal;
window.confirmDelete = confirmDelete;
window.loadPriceItems = loadPriceItems;
window.closeModal = closeModal;
window.closeHistoryModal = closeHistoryModal;
window.closeBulkModal = closeBulkModal;
window.exportPriceItems = exportPriceItems;

console.log("📋 Price List page module ready");
