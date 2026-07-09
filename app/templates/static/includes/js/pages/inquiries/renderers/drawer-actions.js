// ============================================================
// inquiries/renderers/drawer-actions.js - Drawer Action Buttons
// ============================================================

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
