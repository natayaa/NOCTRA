// inquiries/renderers/drawer-actions.js - FIXED

import { DOM } from "../dom.js";
import { Formatter } from "../formatters.js";

export function updateActionButtons(inquiry) {
  if (!inquiry) return;

  const status = inquiry.status || "new";
  const hasProject = !!inquiry.project;
  const projectStatus = inquiry.project?.status;

  // Define all buttons
  const buttons = {
    review: document.getElementById("drawerReviewBtn"),
    contact: document.getElementById("drawerContactBtn"),
    quote: DOM.drawerQuoteBtn(),
    approve: DOM.drawerApproveBtn(),
    convert: DOM.drawerConvertBtn(),
    reject: DOM.drawerRejectBtn(),
    close: document.getElementById("drawerCloseBtn"),
    complete: document.getElementById("drawerCompleteBtn"),
    viewProject: DOM.drawerViewProjectBtn(),
    whatsapp: DOM.drawerWhatsappBtn(),
  };

  // Hide all first
  Object.values(buttons).forEach((btn) => {
    if (btn) btn.style.display = "none";
  });

  // WhatsApp always show if phone exists
  if (buttons.whatsapp && inquiry.customer_phone_number) {
    buttons.whatsapp.style.display = "inline-flex";
    buttons.whatsapp.textContent = "💬 WhatsApp";
    buttons.whatsapp.className = "btn-secondary";
    buttons.whatsapp.onclick = () => {
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

  // Show buttons based on status
  switch (status) {
    case "new":
      if (buttons.review) {
        buttons.review.style.display = "inline-flex";
        buttons.review.textContent = "📋 Review";
        buttons.review.className = "btn-secondary";
        buttons.review.onclick = () => {
          if (window.handleUpdateStatus) {
            window.handleUpdateStatus(
              inquiry.id,
              "under_review",
              "Started review",
            );
          }
        };
      }
      if (buttons.reject) {
        buttons.reject.style.display = "inline-flex";
        buttons.reject.textContent = "❌ Reject";
        buttons.reject.onclick = () => {
          if (window.openRejectModal) window.openRejectModal(inquiry.id);
        };
      }
      break;

    case "under_review":
      if (buttons.contact) {
        buttons.contact.style.display = "inline-flex";
        buttons.contact.textContent = "📞 Contact";
        buttons.contact.className = "btn-secondary";
        buttons.contact.onclick = () => {
          if (window.handleUpdateStatus) {
            window.handleUpdateStatus(
              inquiry.id,
              "contacted",
              "Customer contacted",
            );
          }
        };
      }
      if (buttons.reject) {
        buttons.reject.style.display = "inline-flex";
        buttons.reject.textContent = "❌ Reject";
        buttons.reject.onclick = () => {
          if (window.openRejectModal) window.openRejectModal(inquiry.id);
        };
      }
      break;

    case "contacted":
      if (buttons.quote) {
        buttons.quote.style.display = "inline-flex";
        buttons.quote.textContent = "📄 Send Quote";
        buttons.quote.className = "btn-primary";
        buttons.quote.onclick = () => {
          if (window.openQuoteModal) window.openQuoteModal(inquiry.id);
        };
      }
      if (buttons.reject) {
        buttons.reject.style.display = "inline-flex";
        buttons.reject.textContent = "❌ Reject";
        buttons.reject.onclick = () => {
          if (window.openRejectModal) window.openRejectModal(inquiry.id);
        };
      }
      break;

    case "quoted":
      if (buttons.approve) {
        buttons.approve.style.display = "inline-flex";
        buttons.approve.textContent = "✅ Approve";
        buttons.approve.className = "btn-success";
        buttons.approve.title = "Customer approved the quote";
        buttons.approve.onclick = () => {
          if (window.handleApprove)
            window.handleApprove(inquiry.id, "Customer approved the quote");
        };
      }
      if (buttons.reject) {
        buttons.reject.style.display = "inline-flex";
        buttons.reject.textContent = "❌ Reject";
        buttons.reject.onclick = () => {
          if (window.openRejectModal) window.openRejectModal(inquiry.id);
        };
      }
      break;

    case "approved":
      if (buttons.convert) {
        buttons.convert.style.display = "inline-flex";
        buttons.convert.innerHTML =
          '<i class="ph ph-arrow-right"></i> Convert to Project';
        buttons.convert.className = "btn-primary";
        buttons.convert.onclick = () => {
          if (window.openConvertModal) window.openConvertModal(inquiry.id);
        };
      }
      if (buttons.reject) {
        buttons.reject.style.display = "inline-flex";
        buttons.reject.textContent = "❌ Reject";
        buttons.reject.onclick = () => {
          if (window.openRejectModal) window.openRejectModal(inquiry.id);
        };
      }
      break;

    case "converted":
      if (buttons.viewProject && hasProject) {
        buttons.viewProject.style.display = "inline-flex";
        buttons.viewProject.href = `/projects/${inquiry.project.id}`;
        buttons.viewProject.textContent = "📁 View Project";
      }
      if (buttons.complete && projectStatus === "completed") {
        buttons.complete.style.display = "inline-flex";
        buttons.complete.textContent = "✅ Mark as Completed";
        buttons.complete.className = "btn-success";
        buttons.complete.onclick = () => {
          if (window.handleMarkComplete) window.handleMarkComplete(inquiry.id);
        };
      }
      break;

    case "rejected":
      if (buttons.close) {
        buttons.close.style.display = "inline-flex";
        buttons.close.textContent = "🔒 Close";
        buttons.close.className = "btn-secondary";
        buttons.close.onclick = () => {
          if (window.handleClose) {
            const reason = prompt("Reason for closing:");
            if (reason !== null) window.handleClose(inquiry.id, reason);
          }
        };
      }
      break;

    case "closed":
    case "completed":
      if (buttons.viewProject && hasProject) {
        buttons.viewProject.style.display = "inline-flex";
        buttons.viewProject.href = `/projects/${inquiry.project.id}`;
        buttons.viewProject.textContent = "📁 View Project";
      }
      break;
  }
}
