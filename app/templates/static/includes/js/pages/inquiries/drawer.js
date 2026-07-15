// inquiries/drawer.js (FIXED & IMPROVED)

import { DOM, drawerBackdrop } from "./dom.js";
import { state } from "./config.js";
import { InquiryAPI } from "./api.js";
import { PaymentAPI } from "../shared/payments/api.js";
import { calculateFinancialFromData } from "./utils.js";
import { showToast } from "./toast.js";

// Import renderers
import { renderDrawerCustomer } from "./renderers/customer.js";
import { renderDrawerVehicle } from "./renderers/vehicle.js";
import { renderDrawerFinancial } from "./renderers/financial.js";
import { renderDrawerLabor } from "./renderers/labor.js";
import { renderDrawerMaterialUsages } from "./renderers/materials.js";
import { renderDrawerPayments } from "./renderers/payments.js";
import { renderDrawerTimeline } from "./renderers/timeline.js";
import { renderDrawerNotes } from "./renderers/notes.js";
import { renderDrawerBeforeAfter } from "./renderers/carousel.js";
import { updateActionButtons } from "./renderers/drawer-actions.js";

let isLoading = false;

// ============================================================
// LOAD INQUIRY DETAIL
// ============================================================
export async function loadInquiryDetail(inquiryId) {
  if (isLoading) {
    console.log("⏳ Already loading, skipping...");
    return;
  }

  if (!inquiryId) {
    console.warn("⚠️ No inquiry ID provided");
    return;
  }

  isLoading = true;
  state.currentInquiryId = inquiryId;

  const drawer = DOM.drawer();
  if (drawer) drawer.classList.add("active");
  if (drawerBackdrop) drawerBackdrop.classList.add("active");
  document.body.style.overflow = "hidden";

  try {
    const inquiry = await InquiryAPI.fetchDetail(inquiryId);
    if (!inquiry) {
      showToast("Failed to load inquiry details", "error");
      isLoading = false;
      return;
    }

    // Load inventory items
    try {
      state.inventoryItems = await InquiryAPI.fetchInventoryItems();
    } catch (e) {
      console.warn("Failed to load inventory items:", e);
      state.inventoryItems = [];
    }

    // Load all related data in parallel
    const [payments, activities, notes, photos] = await Promise.all([
      PaymentAPI.getByInquiry(inquiryId).catch(() => []),
      InquiryAPI.fetchActivities(inquiryId).catch(() => []),
      InquiryAPI.fetchNotes(inquiryId, true).catch(() => []),
      InquiryAPI.fetchPhotos(inquiryId).catch(() => []),
    ]);

    // Load labor & materials if project exists
    let labor = [];
    let materials = [];

    if (inquiry.project?.id) {
      const projectId = inquiry.project.id;
      [labor, materials] = await Promise.all([
        InquiryAPI.fetchProjectLabor(projectId).catch(() => []),
        InquiryAPI.fetchProjectMaterialUsage(projectId).catch(() => []),
      ]);
    }

    // Auto-update inquiry status if project completed
    if (inquiry.project?.status === "completed") {
      if (
        inquiry.status !== "completed" &&
        inquiry.status !== "project_completed"
      ) {
        await InquiryAPI.updateStatus(
          inquiryId,
          "completed",
          "Project completed - auto-updated",
        );
        const updated = await InquiryAPI.fetchDetail(inquiryId);
        if (updated) {
          inquiry.status = updated.status;
        }
      }
    }

    // Hide skeleton, show content
    const skeleton = document.getElementById("skeletonLoader");
    const content = document.getElementById("drawerContentInner");
    if (skeleton) skeleton.style.display = "none";
    if (content) content.style.display = "block";

    // Calculate financial
    const financial = calculateFinancialFromData(
      inquiry,
      labor,
      materials,
      payments,
    );

    // Render all sections
    renderDrawerCustomer(inquiry);
    renderDrawerVehicle(inquiry);
    renderDrawerFinancial(financial);
    renderDrawerLabor(labor);
    renderDrawerMaterialUsages(materials);
    await renderDrawerPayments(inquiryId);
    renderDrawerTimeline(activities);
    renderDrawerNotes(notes);
    renderDrawerBeforeAfter(photos);
    updateActionButtons(inquiry);

    state._currentInquiry = inquiry;
  } catch (error) {
    console.error("❌ Failed to load inquiry detail:", error);
    showToast("Failed to load inquiry details: " + error.message, "error");
    closeDrawer();
  } finally {
    isLoading = false;
  }
}

// ============================================================
// CLOSE DRAWER
// ============================================================
export function closeDrawer() {
  const drawer = DOM.drawer();
  if (drawer) drawer.classList.remove("active");
  if (drawerBackdrop) drawerBackdrop.classList.remove("active");
  document.body.style.overflow = "";
  state.currentInquiryId = null;
  state._currentInquiry = null;
  isLoading = false;
}

// ============================================================
// OPEN INQUIRY DRAWER
// ============================================================
export async function openInquiryDrawer(inquiryId) {
  const drawer = DOM.drawer();
  if (
    state.currentInquiryId === inquiryId &&
    drawer?.classList.contains("active")
  ) {
    console.log("📌 Drawer already open for this inquiry");
    return;
  }
  await loadInquiryDetail(inquiryId);
}

// ============================================================
// REFRESH INQUIRY DETAIL
// ============================================================
export async function refreshInquiryDetail() {
  if (state.currentInquiryId) {
    await loadInquiryDetail(state.currentInquiryId);
  } else {
    console.warn("⚠️ No inquiry currently open to refresh");
  }
}

// ============================================================
// CHECK IF DRAWER IS OPEN
// ============================================================
export function isDrawerOpen() {
  const drawer = DOM.drawer();
  return drawer ? drawer.classList.contains("active") : false;
}

// ============================================================
// GET CURRENT INQUIRY
// ============================================================
export function getCurrentInquiry() {
  return state._currentInquiry;
}

export function getCurrentInquiryId() {
  return state.currentInquiryId;
}
