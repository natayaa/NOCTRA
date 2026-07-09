// ============================================================
// inquiries/drawer.js - Drawer Functions
// ============================================================

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

export async function loadInquiryDetail(inquiryId) {
  state.currentInquiryId = inquiryId;

  const inquiry = await InquiryAPI.fetchDetail(inquiryId);
  if (!inquiry) return;

  try {
    state.inventoryItems = await InquiryAPI.fetchInventoryItems();
    console.log("📦 Loaded inventory items:", state.inventoryItems.length);
  } catch (e) {
    console.warn("Failed to load inventory items:", e);
    state.inventoryItems = [];
  }

  const [payments, activities, notes, photos] = await Promise.all([
    PaymentAPI.getByInquiry(inquiryId).catch(() => []),
    InquiryAPI.fetchActivities(inquiryId).catch(() => []),
    InquiryAPI.fetchNotes(inquiryId, true).catch(() => []),
    InquiryAPI.fetchPhotos(inquiryId).catch(() => []),
  ]);

  console.log("📊 Final payments data:", payments);

  let labor = [];
  let materials = [];
  let financial = null;

  if (inquiry.project && inquiry.project.id) {
    const projectId = inquiry.project.id;
    [labor, materials] = await Promise.all([
      InquiryAPI.fetchProjectLabor(projectId).catch(() => []),
      InquiryAPI.fetchProjectMaterialUsage(projectId).catch(() => []),
    ]);
    financial = calculateFinancialFromData(inquiry, labor, materials, payments);
  } else {
    financial = {
      estimated_cost: 0,
      actual_cost: 0,
      estimated_revenue: 0,
      actual_revenue: 0,
      deposit_amount: 0,
      deposit_paid: false,
      material_cost: 0,
      labor_cost: 0,
      other_expenses: 0,
    };
  }

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

export function closeDrawer() {
  if (DOM.drawer()) DOM.drawer().classList.remove("active");
  if (drawerBackdrop) drawerBackdrop.classList.remove("active");
  document.body.style.overflow = "";
  state.currentInquiryId = null;
}

export async function openInquiryDrawer(inquiryId) {
  await loadInquiryDetail(inquiryId);
}
