// inquiries/drawer.js

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

// ============================================================
// LOAD INQUIRY DETAIL
// ============================================================
export async function loadInquiryDetail(inquiryId) {
  state.currentInquiryId = inquiryId;

  const inquiry = await InquiryAPI.fetchDetail(inquiryId);
  if (!inquiry) return;

  // Load inventory items untuk enrichment
  try {
    state.inventoryItems = await InquiryAPI.fetchInventoryItems();
    console.log("📦 Loaded inventory items:", state.inventoryItems.length);
  } catch (e) {
    console.warn("Failed to load inventory items:", e);
    state.inventoryItems = [];
  }

  // Load semua data terkait
  const [payments, activities, notes, photos] = await Promise.all([
    PaymentAPI.getByInquiry(inquiryId).catch(() => []),
    InquiryAPI.fetchActivities(inquiryId).catch(() => []),
    InquiryAPI.fetchNotes(inquiryId, true).catch(() => []),
    InquiryAPI.fetchPhotos(inquiryId).catch(() => []),
  ]);

  console.log("📊 Payments data:", payments);

  // Load labor dan materials jika ada project
  let labor = [];
  let materials = [];
  let financial = null;

  if (inquiry.project && inquiry.project.id) {
    const projectId = inquiry.project.id;
    console.log("📌 Project found:", projectId);

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

    console.log("👷 Labor items:", labor);
    console.log("📦 Material usages:", materials);
  } else {
    console.log("📌 No project found for inquiry:", inquiryId);
  }

  // Hitung financial dengan data yang ada
  financial = calculateFinancialFromData(inquiry, labor, materials, payments);
  console.log("📊 Final financial data:", financial);

  // Render semua section
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

  if (DOM.drawer()) DOM.drawer().classList.add("active");
  if (drawerBackdrop) drawerBackdrop.classList.add("active");
  document.body.style.overflow = "hidden";
}

// ============================================================
// ✅ CLOSE DRAWER - PASTIKAN DI-EXPORT
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
}

// ============================================================
// ✅ OPEN INQUIRY DRAWER
// ============================================================
export async function openInquiryDrawer(inquiryId) {
  console.log("🔓 Opening inquiry drawer:", inquiryId);
  await loadInquiryDetail(inquiryId);
}
