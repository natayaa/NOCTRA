// inquiries/index.js - Main Entry Point (FIXED & IMPROVED)

import { state, CONFIG } from "./config.js";
import { DOM, drawerBackdrop } from "./dom.js";
import { InquiryAPI } from "./api.js";
import { showToast } from "./toast.js";
import {
  renderInquiries,
  showLoadingState,
  updatePagination,
  updateDashboard,
} from "./renderers/table.js";
import { openInquiryDrawer, closeDrawer, loadInquiryDetail } from "./drawer.js";
import {
  handleApprove,
  handleWhatsApp,
  handleSaveNote,
  handleMarkComplete,
  handleUnderReview,
  handleContacted,
  handleClose,
  handleUpdateStatus,
} from "./handlers/actions.js";
import {
  openConvertModal,
  closeConvertModal,
  openQuoteModal,
  closeQuoteModal,
  openRejectModal,
  closeRejectModal,
} from "./handlers/modals.js";
import {
  openLightbox,
  closeLightbox,
  navigateLightbox,
} from "./renderers/carousel.js";
import { bindEvents } from "./handlers/events.js";
import { Formatter } from "./formatters.js";
import {
  openPaymentModal,
  openInvoiceModal,
} from "../payments/handlers/modals.js";

// ✅ Import payment modal handlers
import {
  confirmPayment,
  openConfirmPaymentModal,
  closeConfirmPaymentModal,
  openDeletePaymentModal,
  closeDeletePaymentModal,
} from "./handlers/events.js";

// ============================================================
// MAIN LOAD FUNCTION
// ============================================================
export async function loadInquiries() {
  showLoadingState();

  try {
    const data = await InquiryAPI.fetchInquiries(
      state.currentPage,
      state.filters,
    );

    if (!data) {
      renderErrorState("Failed to load inquiries. Please try again.");
      return;
    }

    let inquiries = [],
      totalPages = 1,
      totalItems = 0;

    if (data.data && Array.isArray(data.data)) {
      inquiries = data.data;
      totalItems = data.total || data.total_items || inquiries.length;
      totalPages =
        data.total_pages ||
        data.totalPages ||
        Math.ceil(totalItems / CONFIG.INQUIRIES_PER_PAGE);
    } else if (Array.isArray(data)) {
      inquiries = data;
      totalItems = inquiries.length;
      totalPages = Math.ceil(totalItems / CONFIG.INQUIRIES_PER_PAGE);
    } else if (data.items && Array.isArray(data.items)) {
      inquiries = data.items;
      totalItems = data.total || data.total_items || inquiries.length;
      totalPages =
        data.total_pages ||
        data.totalPages ||
        Math.ceil(totalItems / CONFIG.INQUIRIES_PER_PAGE);
    }

    state.inquiries = inquiries;
    state.totalPages = Math.max(1, totalPages);
    state.totalItems = totalItems;

    renderInquiries(state.inquiries);
    updatePagination(state.currentPage, state.totalPages, state.totalItems);

    const stats = await InquiryAPI.fetchStatistics();
    updateDashboard(stats);
  } catch (error) {
    console.error("Error loading inquiries:", error);
    renderErrorState(error.message || "Failed to load inquiries");
  }
}

function renderErrorState(message) {
  const body = DOM.inquiriesBody();
  if (!body) return;
  body.innerHTML = `
    <tr>
      <td colspan="7" style="text-align:center; padding:2rem; color: var(--text-muted);">
        <i class="ph ph-warning" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
        ${message}
        <br><br>
        <button class="btn-primary" onclick="window.loadInquiries()">
          <i class="ph ph-arrow-clockwise"></i> Retry
        </button>
      </td>
    </tr>
  `;
}

// ============================================================
// EXPORT FUNCTION
// ============================================================
export async function exportInquiries() {
  try {
    showToast("⏳ Generating export...", "info");

    await InquiryAPI.exportInquiries({
      status: state.filters.status,
      search: state.filters.search,
    });

    showToast("✅ Export completed!", "success");
  } catch (error) {
    console.error("Export error:", error);
    showToast("❌ Failed to export: " + error.message, "error");
  }
}

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================
document.addEventListener("keydown", (e) => {
  // ✅ Escape - close all modals
  if (e.key === "Escape") {
    const modals = [
      DOM.convertModal(),
      DOM.quoteModal(),
      DOM.rejectModal(),
      DOM.lightboxOverlay(),
      DOM.drawer(),
      document.getElementById("confirmPaymentModal"),
      document.getElementById("deletePaymentModal"),
      document.getElementById("paymentModal"),
      document.getElementById("invoiceModal"),
    ];

    modals.forEach((modal) => {
      if (modal) {
        if (modal === DOM.lightboxOverlay() && modal.style.display === "flex") {
          closeLightbox();
        } else if (
          modal === DOM.drawer() &&
          modal.classList.contains("active")
        ) {
          closeDrawer();
        } else if (modal.classList && modal.classList.contains("active")) {
          modal.classList.remove("active");
        }
      }
    });
  }

  // ✅ Ctrl+F - Focus search
  if (e.ctrlKey && e.key === "f") {
    e.preventDefault();
    DOM.searchInquiry()?.focus();
  }

  // ✅ Ctrl+E - Export
  if (e.ctrlKey && e.key === "e") {
    e.preventDefault();
    exportInquiries();
  }

  // ✅ Ctrl+R - Refresh
  if (e.ctrlKey && e.key === "r" && !e.shiftKey) {
    e.preventDefault();
    loadInquiries();
  }
});

// ============================================================
// INITIALIZATION
// ============================================================
export async function initInquiries() {
  console.log("🚀 Initializing Inquiries page...");

  try {
    // ✅ Bind events pertama
    bindEvents();

    // ✅ Load data
    await loadInquiries();

    // ✅ Set refresh interval (optional)
    // setInterval(() => { loadInquiries(); }, 60000); // Refresh every minute

    console.log("📋 Inquiries page initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize inquiries page:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

// ============================================================
// ✅ REFRESH FUNCTIONS
// ============================================================
export async function refreshCurrentInquiry() {
  if (state.currentInquiryId) {
    await loadInquiryDetail(state.currentInquiryId);
  }
}

export async function refreshAndReload() {
  await loadInquiries();
  if (state.currentInquiryId) {
    await loadInquiryDetail(state.currentInquiryId);
  }
}

export function clearFilters() {
  state.filters.search = "";
  state.filters.status = "";
  state.currentPage = 1;

  const searchInput = DOM.searchInquiry();
  const statusSelect = DOM.statusFilter();

  if (searchInput) searchInput.value = "";
  if (statusSelect) statusSelect.value = "";

  loadInquiries();
}

// ============================================================
// ✅ EXPOSE TO GLOBAL (for inline onclick handlers)
// ============================================================
window.openInquiryDrawer = openInquiryDrawer;
window.openConvertModal = openConvertModal;
window.openQuoteModal = openQuoteModal;
window.openRejectModal = openRejectModal;
window.handleApprove = handleApprove;
window.handleMarkComplete = handleMarkComplete;
window.handleUnderReview = handleUnderReview;
window.handleContacted = handleContacted;
window.handleClose = handleClose;
window.handleUpdateStatus = handleUpdateStatus;
window.loadInquiries = loadInquiries;
window.openLightbox = openLightbox;
window.closeLightbox = closeLightbox;
window.exportInquiries = exportInquiries;
window.closeDrawer = closeDrawer;
window.closeConvertModal = closeConvertModal;
window.closeQuoteModal = closeQuoteModal;
window.closeRejectModal = closeRejectModal;
window.openPaymentModal = openPaymentModal;
window.openInvoiceModal = openInvoiceModal;
window.confirmPayment = confirmPayment;
window.openConfirmPaymentModal = openConfirmPaymentModal;
window.closeConfirmPaymentModal = closeConfirmPaymentModal;
window.openDeletePaymentModal = openDeletePaymentModal;
window.closeDeletePaymentModal = closeDeletePaymentModal;
window.refreshCurrentInquiry = refreshCurrentInquiry;
window.refreshAndReload = refreshAndReload;
window.clearFilters = clearFilters;

console.log("📋 Inquiries page module ready");
