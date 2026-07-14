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

  const status = inquiry.status || "new";
  const hasProject = !!inquiry.project;
  const projectStatus = inquiry.project?.status;

  // Ambil semua button
  const reviewBtn = document.getElementById("drawerReviewBtn");
  const contactBtn = document.getElementById("drawerContactBtn");
  const quoteBtn = DOM.drawerQuoteBtn();
  const approveBtn = DOM.drawerApproveBtn();
  const convertBtn = DOM.drawerConvertBtn();
  const rejectBtn = DOM.drawerRejectBtn();
  const closeBtn = document.getElementById("drawerCloseBtn");
  const completeBtn = document.getElementById("drawerCompleteBtn");
  const viewProjectBtn = DOM.drawerViewProjectBtn();
  const whatsappBtn = DOM.drawerWhatsappBtn();

  // ✅ Sembunyikan semua dulu
  [
    reviewBtn,
    contactBtn,
    quoteBtn,
    approveBtn,
    convertBtn,
    rejectBtn,
    closeBtn,
    completeBtn,
    viewProjectBtn,
    whatsappBtn,
  ].forEach((btn) => {
    if (btn) btn.style.display = "none";
  });

  // ✅ Tampilkan berdasarkan status (URUTAN YANG BENAR)
  switch (status) {
    case "new":
      // NEW → hanya bisa review atau reject
      if (reviewBtn) {
        reviewBtn.style.display = "inline-flex";
        reviewBtn.textContent = "📋 Review";
        reviewBtn.className = "btn-secondary";
        reviewBtn.onclick = () => {
          if (window.handleUpdateStatus) {
            window.handleUpdateStatus(
              inquiry.id,
              "under_review",
              "Started review",
            );
          }
        };
      }
      if (rejectBtn) {
        rejectBtn.style.display = "inline-flex";
        rejectBtn.textContent = "❌ Reject";
      }
      break;

    case "under_review":
      // UNDER_REVIEW → contact atau reject
      if (contactBtn) {
        contactBtn.style.display = "inline-flex";
        contactBtn.textContent = "📞 Contact";
        contactBtn.className = "btn-secondary";
        contactBtn.onclick = () => {
          if (window.handleUpdateStatus) {
            window.handleUpdateStatus(
              inquiry.id,
              "contacted",
              "Customer contacted",
            );
          }
        };
      }
      if (rejectBtn) {
        rejectBtn.style.display = "inline-flex";
        rejectBtn.textContent = "❌ Reject";
      }
      break;

    case "contacted":
      // CONTACTED → send quote atau reject
      if (quoteBtn) {
        quoteBtn.style.display = "inline-flex";
        quoteBtn.textContent = "📄 Send Quote";
        quoteBtn.className = "btn-primary";
        // Quote akan buka modal quote
      }
      if (rejectBtn) {
        rejectBtn.style.display = "inline-flex";
        rejectBtn.textContent = "❌ Reject";
      }
      break;

    case "quoted":
      // QUOTED → approve (customer) atau reject
      if (approveBtn) {
        approveBtn.style.display = "inline-flex";
        approveBtn.textContent = "✅ Approve";
        approveBtn.className = "btn-success";
        approveBtn.title = "Customer approved the quote";
        approveBtn.onclick = () => {
          if (window.handleApprove) {
            window.handleApprove(inquiry.id, "Customer approved the quote");
          }
        };
      }
      if (rejectBtn) {
        rejectBtn.style.display = "inline-flex";
        rejectBtn.textContent = "❌ Reject";
      }
      break;

    case "approved":
      // APPROVED → convert ke project atau reject
      if (convertBtn) {
        convertBtn.style.display = "inline-flex";
        convertBtn.innerHTML =
          '<i class="ph ph-arrow-right"></i> Convert to Project';
        convertBtn.className = "btn-primary";
        // Convert akan buka modal convert
      }
      if (rejectBtn) {
        rejectBtn.style.display = "inline-flex";
        rejectBtn.textContent = "❌ Reject";
      }
      break;

    case "converted":
      // CONVERTED → view project (jika ada)
      if (viewProjectBtn && hasProject) {
        viewProjectBtn.style.display = "inline-flex";
        viewProjectBtn.href = `/projects/${inquiry.project.id}`;
        viewProjectBtn.textContent = "📁 View Project";
      }
      // Jika project sudah completed, tampilkan tombol Complete
      if (completeBtn && projectStatus === "completed") {
        completeBtn.style.display = "inline-flex";
        completeBtn.textContent = "✅ Mark as Completed";
        completeBtn.className = "btn-success";
        completeBtn.onclick = () => {
          if (window.handleMarkComplete) {
            window.handleMarkComplete(inquiry.id);
          }
        };
      }
      break;

    case "rejected":
      // REJECTED → close
      if (closeBtn) {
        closeBtn.style.display = "inline-flex";
        closeBtn.textContent = "🔒 Close";
        closeBtn.className = "btn-secondary";
        closeBtn.onclick = () => {
          if (window.handleClose) {
            const reason = prompt("Reason for closing:");
            if (reason !== null) {
              window.handleClose(inquiry.id, reason);
            }
          }
        };
      }
      break;

    case "closed":
    case "completed":
      // Final status → view project (jika ada) atau tidak ada action
      if (viewProjectBtn && hasProject) {
        viewProjectBtn.style.display = "inline-flex";
        viewProjectBtn.href = `/projects/${inquiry.project.id}`;
        viewProjectBtn.textContent = "📁 View Project";
      }
      break;
  }

  // ✅ WhatsApp selalu tampil jika ada nomor
  if (whatsappBtn && inquiry.customer_phone_number) {
    whatsappBtn.style.display = "inline-flex";
    whatsappBtn.textContent = "💬 WhatsApp";
    whatsappBtn.className = "btn-secondary";
    whatsappBtn.onclick = () => {
      const phone = inquiry.customer_phone_number.replace(/\D/g, "");
      const msg = encodeURIComponent(
        `Halo ${inquiry.customer_name || "Customer"},\n\n` +
          `Kami dari NOCTRA ingin menindaklanjuti inquiry Anda mengenai:\n` +
          `• Kendaraan: ${inquiry.vehicle_brand} ${inquiry.vehicle_model}\n` +
          `• Tipe Proyek: ${inquiry.project_type}\n\n` +
          `Ada yang bisa kami bantu? 😊`,
      );
      window.open(`https://wa.me/${phone}?text=${msg}`, "_blank");
    };
  }
}
