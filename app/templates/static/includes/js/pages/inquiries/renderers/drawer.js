// ============================================================
// inquiries/renderers/drawer.js - All Drawer Renderers
// ============================================================

export { renderDrawerCustomer } from "./customer.js";
export { renderDrawerVehicle } from "./vehicle.js";
export { renderDrawerTimeline } from "./timeline.js";
export { renderDrawerNotes } from "./notes.js";
export { renderDrawerBeforeAfter } from "./carousel.js";
export { renderDrawerFinancial } from "./financial.js";
export { renderDrawerLabor } from "./labor.js";
export { renderDrawerMaterialUsages } from "./materials.js";
export { renderDrawerPayments } from "./payments.js";

import { DOM } from "../dom.js";

export function updateActionButtons(inquiry) {
  if (!inquiry) return;
  const status = inquiry.status;

  const approveBtn = DOM.drawerApproveBtn();
  const quoteBtn = DOM.drawerQuoteBtn();
  const rejectBtn = DOM.drawerRejectBtn();
  const convertBtn = DOM.drawerConvertBtn();
  const viewProjectBtn = DOM.drawerViewProjectBtn();

  if (approveBtn) {
    approveBtn.style.display = ["new", "under_review"].includes(status)
      ? "inline-flex"
      : "none";
  }
  if (quoteBtn) {
    quoteBtn.style.display = ["new", "under_review", "contacted"].includes(
      status,
    )
      ? "inline-flex"
      : "none";
  }
  if (rejectBtn) {
    rejectBtn.style.display = !["rejected", "converted", "completed"].includes(
      status,
    )
      ? "inline-flex"
      : "none";
  }
  if (convertBtn) {
    convertBtn.style.display = ["approved", "quoted"].includes(status)
      ? "inline-flex"
      : "none";
    if (status === "converted") {
      convertBtn.disabled = true;
      convertBtn.textContent = "✓ Converted";
    } else {
      convertBtn.disabled = false;
      convertBtn.innerHTML =
        '<i class="ph ph-arrow-right"></i> Convert to Project';
    }
  }

  if (viewProjectBtn) {
    if (inquiry.project) {
      viewProjectBtn.style.display = "inline-flex";
      viewProjectBtn.href = `/projects/${inquiry.project.id}`;
    } else {
      viewProjectBtn.style.display = "none";
    }
  }
}
