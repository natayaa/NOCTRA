// ============================================================
// inquiries/handlers/actions.js - Action Handlers
// ============================================================

import { InquiryAPI } from "../api.js";
import { showToast } from "../toast.js";
import { Formatter } from "../formatters.js";
import { state } from "../config.js";
import { DOM } from "../dom.js";
import { loadInquiryDetail, closeDrawer } from "../drawer.js";
import { loadInquiries } from "../index.js";

export async function handleApprove(inquiryId) {
  if (!confirm("Approve this inquiry?")) return;
  const result = await InquiryAPI.updateStatus(
    inquiryId,
    "approved",
    "Approved by staff",
  );
  if (result) {
    showToast("Inquiry approved!", "success");
    await loadInquiries();
    if (DOM.drawer()?.classList.contains("active"))
      await loadInquiryDetail(inquiryId);
  }
}

export async function handleUpdateStatus(inquiryId, status, note = "") {
  const result = await InquiryAPI.updateStatus(inquiryId, status, note);
  if (result) {
    showToast(`Status updated to ${Formatter.statusLabel(status)}`, "success");
    await loadInquiries();
    if (DOM.drawer()?.classList.contains("active"))
      await loadInquiryDetail(inquiryId);
  }
}

export function handleWhatsApp(inquiry) {
  const phone = inquiry?.customer_phone_number;
  if (!phone) {
    showToast("No phone number available", "error");
    return;
  }
  const cleanPhone = phone.replace(/[^0-9]/g, "");
  const message = encodeURIComponent(
    `Halo ${inquiry.customer_name},\n\n` +
      `Kami dari NOCTRA ingin menindaklanjuti inquiry Anda mengenai:\n` +
      `• Kendaraan: ${inquiry.vehicle_brand} ${inquiry.vehicle_model}\n` +
      `• Tipe Proyek: ${inquiry.project_type}\n\n` +
      `Ada yang bisa kami bantu? 😊`,
  );
  window.open(`https://wa.me/${cleanPhone}?text=${message}`, "_blank");
}

export async function handleSaveNote() {
  const inquiryId = state.currentInquiryId;
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }
  const note = DOM.drawerNotes()?.value?.trim();
  if (!note) {
    showToast("Please enter a note", "error");
    return;
  }
  const result = await InquiryAPI.addNote(inquiryId, note, "internal", false);
  if (result) {
    showToast("Note saved!", "success");
    if (DOM.noteCounter()) DOM.noteCounter().textContent = note.length;
  }
}
