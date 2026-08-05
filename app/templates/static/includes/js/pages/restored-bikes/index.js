// ============================================================
// restored-bikes/index.js - Main Entry Point
// ============================================================

import { state, CONFIG } from "./config.js";
import { DOM } from "./dom.js";
import { RestoredBikeAPI } from "./api.js";
import { showToast } from "../../shared/toast.js";
import { renderList, updatePagination, updateStats } from "./renderers/list.js";
import { bindEvents } from "./handlers/events.js";
import { refreshDrawer } from "./handlers/restorations.js";

// ============================================================
// LOAD DATA
// ============================================================

export async function loadRestoredBikes() {
  if (state.isLoading) return;
  state.isLoading = true;

  console.log("🔄 Loading restored bikes...");

  try {
    const data = await RestoredBikeAPI.list(state.currentPage, state.filters);

    if (!data) {
      renderList();
      return;
    }

    let bikes = data.data || data.items || data || [];
    let totalItems = data.total || data.total_items || bikes.length;
    let totalPages =
      data.total_pages ||
      data.totalPages ||
      Math.ceil(totalItems / CONFIG.ITEMS_PER_PAGE) ||
      1;

    state.bikes = bikes;
    state.totalItems = totalItems;
    state.totalPages = Math.max(1, totalPages);

    renderList();
    updatePagination(state.currentPage, state.totalPages, state.totalItems);

    // Load stats
    const stats = await RestoredBikeAPI.stats();
    updateStats(stats);

    console.log(`✅ Loaded ${totalItems} restored bikes`);
  } catch (error) {
    console.error("Failed to load restored bikes:", error);
    showToast("Failed to load data: " + error.message, "error");
    renderList();
  } finally {
    state.isLoading = false;
  }
}

// ============================================================
// EXPOSE FOR REFRESH
// ============================================================

export { refreshDrawer };

// ============================================================
// INITIALIZATION
// ============================================================

export async function initRestoredBikes() {
  console.log("🚀 Initializing Restored Bikes...");

  try {
    bindEvents();
    await loadRestoredBikes();
    console.log("✅ Restored Bikes initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

// ============================================================
// EXPOSE GLOBALS
// ============================================================

window.initRestoredBikes = initRestoredBikes;
window.loadRestoredBikes = loadRestoredBikes;
window.openRestoredDrawer = async (id) => {
  const { openDrawer } = await import("./handlers/restorations.js");
  openDrawer(id);
};
window.openAddRestoredModal = async () => {
  const { openAddModal } = await import("./handlers/modals.js");
  openAddModal();
};
window.deleteGalleryPhoto = async (id) => {
  const { handleDeletePhoto } = await import("./handlers/documents.js");
  handleDeletePhoto(id);
};
window.deleteDocument = async (id) => {
  const { handleDeleteDocument } = await import("./handlers/documents.js");
  handleDeleteDocument(id);
};
window.downloadDocument = async (id) => {
  const { handleDownloadDocument } = await import("./handlers/documents.js");
  handleDownloadDocument(id);
};
