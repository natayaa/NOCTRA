// ============================================================
// inventories/index.js - Main Entry Point
// ============================================================

import { state, CONFIG } from "./config.js";
import { DOM } from "./dom.js";
import { InventoryAPI } from "./api.js";
import { showToast } from "./toast.js";
import {
  renderItems,
  showLoadingState,
  updatePagination,
  updateDashboard,
} from "./renderers/table.js";
import { renderAlerts } from "./renderers/alerts.js";
import {
  renderCategories,
  updateCategoryFilter,
} from "./renderers/categories.js";
import { renderRecentMovements } from "./renderers/movements.js";
import { renderDetailPanel } from "./renderers/detail.js";
import {
  openCreateModal,
  openEditModal,
  closeModal,
} from "./handlers/modals.js";
import {
  openStockAdjustModal,
  closeStockAdjustModal,
} from "./handlers/stock.js";
import { openHistoryModal, closeHistoryModal } from "./handlers/history.js";
import { openReorderModal, closeReorderModal } from "./handlers/reorder.js";
import {
  confirmDelete,
  filterByCategory,
  exportInventory,
} from "./handlers/actions.js";
import { bindEvents } from "./handlers/events.js";

// ============================================================
// SELECT ITEM
// ============================================================
export async function selectItem(itemId) {
  const content = DOM.itemDetailContent();
  if (content) {
    content.innerHTML = `
            <div style="text-align:center;padding:2rem;color:var(--text-muted);">
                <i class="fas fa-spinner fa-spin" style="font-size:1.5rem;display:block;margin-bottom:0.5rem;"></i>
                Loading item details...
            </div>
        `;
  }

  const item = await InventoryAPI.fetchItemDetail(itemId);
  if (!item) {
    renderDetailPanel(null);
    return;
  }

  renderDetailPanel(item);

  document.querySelectorAll(".inventory-table tbody tr").forEach((row) => {
    row.classList.remove("selected");
    const onclick = row.getAttribute("onclick");
    if (onclick && onclick.includes(itemId)) {
      row.classList.add("selected");
    }
  });
}

// ============================================================
// MAIN LOAD FUNCTION
// ============================================================
export async function loadInventoryItems() {
  console.log("🔄 Loading inventory items...");

  const data = await InventoryAPI.fetchItems(state.currentPage, state.filters);

  if (!data) {
    const list = DOM.inventoryItemsList();
    if (list) {
      list.innerHTML = `
                <tr>
                    <td colspan="7" class="no-data">
                        <i class="fas fa-exclamation-triangle" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                        Failed to load inventory. Please try again.
                        <br><br>
                        <button class="btn-add-item" onclick="window.loadInventoryItems()">
                            <i class="fas fa-rotate"></i> Retry
                        </button>
                    </td>
                </tr>
            `;
    }
    return;
  }

  let items = data.data || data.items || data;
  let totalPages = data.total_pages || data.totalPages || 1;
  let totalItems = data.total || data.totalItems || items.length || 0;

  if (Array.isArray(data) && !data.data) {
    items = data;
    totalItems = items.length;
    totalPages = Math.ceil(totalItems / CONFIG.ITEMS_PER_PAGE);
  }

  state.items = items || [];
  state.totalPages = totalPages;
  state.totalItems = totalItems;

  renderItems(state.items);
  updatePagination(state.currentPage, state.totalPages, state.totalItems);

  // Load all side data in parallel
  const [stats, categories, alerts, movements] = await Promise.all([
    InventoryAPI.fetchStatistics(),
    InventoryAPI.fetchCategories(),
    InventoryAPI.fetchAlerts(),
    InventoryAPI.fetchRecentMovements(CONFIG.MAX_MOVEMENTS),
  ]);

  updateDashboard(stats);
  if (categories) {
    renderCategories(categories);
    updateCategoryFilter(categories);
  }
  renderAlerts(alerts);
  renderRecentMovements(movements);

  // Restore selected item if still exists
  if (state.selectedItemId) {
    const stillExists = state.items.find((i) => i.id === state.selectedItemId);
    if (stillExists) {
      await selectItem(state.selectedItemId);
    } else {
      state.selectedItemId = null;
      renderDetailPanel(null);
    }
  }

  console.log("✅ Inventory loaded successfully");
}

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (DOM.inventoryModal()?.classList.contains("active")) closeModal();
    if (DOM.stockAdjustModal()?.classList.contains("active"))
      closeStockAdjustModal();
    if (DOM.historyModal()?.classList.contains("active")) closeHistoryModal();
    if (DOM.reorderModal()?.classList.contains("active")) closeReorderModal();
  }
  if (e.ctrlKey && e.key === "n") {
    e.preventDefault();
    openCreateModal();
  }
  if (e.ctrlKey && e.key === "f") {
    e.preventDefault();
    DOM.searchInventory()?.focus();
  }
  if (e.ctrlKey && e.key === "e") {
    e.preventDefault();
    exportInventory();
  }
});

// ============================================================
// INITIALIZATION
// ============================================================
export async function initInventory() {
  console.log("🚀 Initializing Inventory page...");
  bindEvents();
  await loadInventoryItems();
  console.log("📋 Inventory page initialized successfully");
}

// ============================================================
// EXPOSE TO GLOBAL
// ============================================================
window.selectItem = selectItem;
window.openCreateModal = openCreateModal;
window.openEditModal = openEditModal;
window.openStockAdjustModal = openStockAdjustModal;
window.openHistoryModal = openHistoryModal;
window.openReorderModal = openReorderModal;
window.confirmDelete = confirmDelete;
window.filterByCategory = filterByCategory;
window.loadInventoryItems = loadInventoryItems;
window.closeModal = closeModal;
window.closeStockAdjustModal = closeStockAdjustModal;
window.closeHistoryModal = closeHistoryModal;
window.closeReorderModal = closeReorderModal;

console.log("📋 Inventory page module ready");
