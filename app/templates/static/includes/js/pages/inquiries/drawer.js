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
  // ✅ Prevent duplicate loading
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

  // ✅ Show loading state in drawer
  const drawer = DOM.drawer();
  if (drawer) {
    drawer.classList.add("active");
  }
  if (drawerBackdrop) {
    drawerBackdrop.classList.add("active");
  }
  document.body.style.overflow = "hidden";

  try {
    // ✅ Fetch inquiry detail
    const inquiry = await InquiryAPI.fetchDetail(inquiryId);
    if (!inquiry) {
      showToast("Failed to load inquiry details", "error");
      isLoading = false;
      return;
    }

    // console.log("📋 Loaded inquiry:", inquiry.id);

    // ✅ Load inventory items for enrichment
    try {
      state.inventoryItems = await InquiryAPI.fetchInventoryItems();
      // console.log("📦 Loaded inventory items:", state.inventoryItems.length);
    } catch (e) {
      console.warn("Failed to load inventory items:", e);
      state.inventoryItems = [];
    }

    // ✅ Load all related data in parallel
    const [payments, activities, notes, photos] = await Promise.all([
      PaymentAPI.getByInquiry(inquiryId).catch(() => {
        console.warn("Failed to load payments");
        return [];
      }),
      InquiryAPI.fetchActivities(inquiryId).catch(() => {
        console.warn("Failed to load activities");
        return [];
      }),
      InquiryAPI.fetchNotes(inquiryId, true).catch(() => {
        console.warn("Failed to load notes");
        return [];
      }),
      InquiryAPI.fetchPhotos(inquiryId).catch(() => {
        console.warn("Failed to load photos");
        return [];
      }),
    ]);

    // console.log("📊 Payments:", payments?.length || 0);
    // console.log("📋 Activities:", activities?.length || 0);
    // console.log("📝 Notes:", notes?.length || 0);
    // console.log("🖼️ Photos:", photos?.length || 0);

    // ✅ Load labor and materials if project exists
    let labor = [];
    let materials = [];
    let financial = null;

    if (inquiry.project && inquiry.project.id) {
      const projectId = inquiry.project.id;
      // console.log("📌 Project found:", projectId);

      [labor, materials] = await Promise.all([
        InquiryAPI.fetchProjectLabor(projectId).catch(() => {
          console.warn("Failed to load labor for project:", projectId);
          return [];
        }),
        InquiryAPI.fetchProjectMaterialUsage(projectId).catch(() => {
          console.warn("Failed to load materials for project:", projectId);
          return [];
        }),
      ]);

      // console.log("👷 Labor items:", labor?.length || 0);
      //console.log("📦 Material usages:", materials?.length || 0);
    } else {
      console.log("📌 No project found for inquiry:", inquiryId);
    }

    // ✅ Auto-update inquiry status if project completed
    if (inquiry.project && inquiry.project.status === "completed") {
      if (
        inquiry.status !== "completed" &&
        inquiry.status !== "project_completed"
      ) {
        await InquiryAPI.updateStatus(
          inquiryId,
          "completed",
          "Project completed - auto-updated",
        );
        // Re-fetch inquiry for updated status
        const updatedInquiry = await InquiryAPI.fetchDetail(inquiryId);
        if (updatedInquiry) {
          inquiry.status = updatedInquiry.status;
        }
      }
    }

    // ✅ Calculate financial data
    financial = calculateFinancialFromData(inquiry, labor, materials, payments);
    // console.log("📊 Financial data:", financial);

    // ✅ Render all sections
    renderDrawerCustomer(inquiry);
    renderDrawerVehicle(inquiry);
    renderDrawerFinancial(financial);
    renderDrawerLabor(labor);
    renderDrawerMaterialUsages(materials);
    await renderDrawerPayments(inquiryId);
    renderDrawerTimeline(activities);
    renderDrawerNotes(notes);
    renderDrawerBeforeAfter(photos);

    // ✅ Update action buttons
    updateActionButtons(inquiry);
    state._currentInquiry = inquiry;
  } catch (error) {
    console.error("❌ Failed to load inquiry detail:", error);
    showToast("Failed to load inquiry details: " + error.message, "error");

    // ✅ Close drawer on error
    closeDrawer();
  } finally {
    isLoading = false;
  }
}

// ============================================================
// ✅ CLOSE DRAWER
// ============================================================
export function closeDrawer() {
  console.log("🔒 Closing drawer...");

  const drawer = DOM.drawer();
  if (drawer) {
    drawer.classList.remove("active");
  }

  if (drawerBackdrop) {
    drawerBackdrop.classList.remove("active");
  }

  document.body.style.overflow = "";
  state.currentInquiryId = null;
  state._currentInquiry = null;
  isLoading = false;
}

// ============================================================
// ✅ OPEN INQUIRY DRAWER
// ============================================================
export async function openInquiryDrawer(inquiryId) {
  // console.log("🔓 Opening inquiry drawer:", inquiryId);

  // ✅ Jika drawer sudah terbuka dengan inquiry yang sama, jangan reload
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
// ✅ REFRESH INQUIRY DETAIL
// ============================================================
export async function refreshInquiryDetail() {
  if (state.currentInquiryId) {
    console.log("🔄 Refreshing inquiry detail...");
    await loadInquiryDetail(state.currentInquiryId);
  } else {
    console.warn("⚠️ No inquiry currently open to refresh");
  }
}

// ============================================================
// ✅ CHECK IF DRAWER IS OPEN
// ============================================================
export function isDrawerOpen() {
  const drawer = DOM.drawer();
  return drawer ? drawer.classList.contains("active") : false;
}

// ============================================================
// ✅ GET CURRENT INQUIRY
// ============================================================
export function getCurrentInquiry() {
  return state._currentInquiry;
}

// ============================================================
// ✅ GET CURRENT INQUIRY ID
// ============================================================
export function getCurrentInquiryId() {
  return state.currentInquiryId;
}
