// ============================================================
// inquiries/index.js - Main Entry Point
// ============================================================

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
import { openInquiryDrawer, closeDrawer } from "./drawer.js";
import { handleApprove } from "./handlers/actions.js";
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

// ============================================================
// MAIN LOAD FUNCTION
// ============================================================
export async function loadInquiries() {
  showLoadingState();
  const data = await InquiryAPI.fetchInquiries(
    state.currentPage,
    state.filters,
  );
  if (!data) {
    const body = DOM.inquiriesBody();
    if (body) {
      body.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center; padding:2rem; color: var(--text-muted);">
                        <i class="ph ph-warning" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                        Failed to load inquiries. Please try again.
                        <br><br>
                        <button class="btn-primary" onclick="window.loadInquiries()">
                            <i class="ph ph-arrow-clockwise"></i> Retry
                        </button>
                    </td>
                </tr>
            `;
    }
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
}

// ============================================================
// EXPORT FUNCTION
// ============================================================
export function exportInquiries() {
  if (!state.inquiries || state.inquiries.length === 0) {
    showToast("No data to export", "warning");
    return;
  }

  const headers = [
    "ID",
    "Customer",
    "Phone",
    "Vehicle",
    "Project Type",
    "Status",
    "Created",
    "Has Project",
  ];
  const rows = state.inquiries.map((inq) => [
    inq.id,
    inq.customer_name,
    inq.customer_phone_number,
    `${inq.vehicle_brand} ${inq.vehicle_model}`,
    inq.project_type,
    Formatter.statusLabel(inq.status),
    Formatter.date(inq.created_at),
    inq.project ? "Yes" : "No",
  ]);

  const csv = [headers.join(","), ...rows.map((row) => row.join(","))].join(
    "\n",
  );
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `inquiries_export_${new Date().toISOString().split("T")[0]}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);

  showToast("Export completed!", "success");
}

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    const modals = [
      DOM.convertModal(),
      DOM.quoteModal(),
      DOM.rejectModal(),
      DOM.lightboxOverlay(),
      DOM.drawer(),
    ];
    modals.forEach((modal) => {
      if (
        modal?.classList.contains("active") ||
        modal?.style.display === "flex"
      ) {
        if (modal === DOM.lightboxOverlay()) closeLightbox();
        else if (modal === DOM.drawer()) closeDrawer();
        else modal.classList.remove("active");
      }
    });
  }
  if (e.ctrlKey && e.key === "f") {
    e.preventDefault();
    DOM.searchInquiry()?.focus();
  }
  if (e.ctrlKey && e.key === "e") {
    e.preventDefault();
    exportInquiries();
  }
});

// ============================================================
// INITIALIZATION
// ============================================================
export async function initInquiries() {
  console.log("🚀 Initializing Inquiries page...");
  try {
    bindEvents();
    await loadInquiries();
    console.log("📋 Inquiries page initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize inquiries page:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

// ============================================================
// EXPOSE TO GLOBAL (for inline onclick handlers)
// ============================================================
window.openInquiryDrawer = openInquiryDrawer;
window.openConvertModal = openConvertModal;
window.openQuoteModal = openQuoteModal;
window.openRejectModal = openRejectModal;
window.handleApprove = handleApprove;
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

console.log("📋 Inquiries page module ready");
