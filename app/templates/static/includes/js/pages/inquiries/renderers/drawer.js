// inquiries/renderers/drawer.js (FIXED & IMPROVED)

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
  const hasProject = !!inquiry.project;
  const projectStatus = inquiry.project?.status;

  const approveBtn = DOM.drawerApproveBtn();
  const quoteBtn = DOM.drawerQuoteBtn();
  const rejectBtn = DOM.drawerRejectBtn();
  const convertBtn = DOM.drawerConvertBtn();
  const viewProjectBtn = DOM.drawerViewProjectBtn();
  const completeBtn = document.getElementById("drawerCompleteBtn");
  const whatsappBtn = DOM.drawerWhatsappBtn();

  // ✅ Approve button
  if (approveBtn) {
    approveBtn.style.display = ["new", "under_review"].includes(status)
      ? "inline-flex"
      : "none";
  }

  // ✅ Quote button
  if (quoteBtn) {
    quoteBtn.style.display = ["new", "under_review", "contacted"].includes(
      status,
    )
      ? "inline-flex"
      : "none";
  }

  // ✅ Reject button
  if (rejectBtn) {
    rejectBtn.style.display = ![
      "rejected",
      "converted",
      "completed",
      "closed",
    ].includes(status)
      ? "inline-flex"
      : "none";
  }

  // ✅ Convert button
  if (convertBtn) {
    if (["approved", "quoted"].includes(status) && !hasProject) {
      convertBtn.style.display = "inline-flex";
      convertBtn.disabled = false;
      convertBtn.innerHTML =
        '<i class="ph ph-arrow-right"></i> Convert to Project';
    } else if (status === "converted" || hasProject) {
      convertBtn.style.display = "inline-flex";
      convertBtn.disabled = true;
      convertBtn.textContent = "✓ Converted";
      convertBtn.style.opacity = "0.6";
      convertBtn.style.cursor = "not-allowed";
    } else {
      convertBtn.style.display = "none";
    }
  }

  // ✅ Complete button (when project is completed but inquiry isn't)
  if (completeBtn) {
    if (hasProject && projectStatus === "completed" && status !== "completed") {
      completeBtn.style.display = "inline-flex";
      completeBtn.onclick = () => {
        if (window.handleMarkComplete) {
          window.handleMarkComplete(inquiry.id);
        }
      };
    } else {
      completeBtn.style.display = "none";
    }
  }

  // ✅ View Project button
  if (viewProjectBtn) {
    if (hasProject && inquiry.project?.id) {
      viewProjectBtn.style.display = "inline-flex";
      viewProjectBtn.href = `/projects/${inquiry.project.id}`;
      viewProjectBtn.target = "_blank";
    } else {
      viewProjectBtn.style.display = "none";
    }
  }

  // ✅ WhatsApp button
  if (whatsappBtn) {
    if (inquiry.customer_phone_number) {
      whatsappBtn.style.display = "inline-flex";
      whatsappBtn.onclick = () => {
        const phone = inquiry.customer_phone_number.replace(/\D/g, "");
        const msg = encodeURIComponent(
          `Halo ${inquiry.customer_name || "Customer"},\n\n` +
            `Kami dari NOCTRA ingin menindaklanjuti inquiry Anda.\n` +
            `Ada yang bisa kami bantu? 😊`,
        );
        window.open(`https://wa.me/${phone}?text=${msg}`, "_blank");
      };
    } else {
      whatsappBtn.style.display = "none";
    }
  }
}
