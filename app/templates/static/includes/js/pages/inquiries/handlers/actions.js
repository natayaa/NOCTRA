// ============================================================
// inquiries/handlers/actions.js - FULL FIXED
// ============================================================

import { InquiryAPI } from "../api.js";
import { showToast } from "../toast.js";
import { Formatter } from "../formatters.js";
import { state } from "../config.js";
import { DOM } from "../dom.js";
import { loadInquiryDetail, closeDrawer } from "../drawer.js";
import { loadInquiries } from "../index.js";

/**
 * Update status dengan validasi transisi
 */
export async function handleUpdateStatus(inquiryId, status, note = "") {
  if (!inquiryId || !status) {
    showToast("Missing required fields", "error");
    return;
  }

  // ✅ HAPUS validasi client-side, serahkan ke server
  try {
    const result = await InquiryAPI.updateStatus(inquiryId, status, note);
    if (result) {
      showToast(
        `✅ Status updated to ${Formatter.statusLabel(status)}`,
        "success",
      );
      await loadInquiries();
      if (DOM.drawer()?.classList.contains("active")) {
        await loadInquiryDetail(inquiryId);
      }
    }
  } catch (error) {
    console.error("Status update error:", error);
    showToast("❌ Failed to update status: " + error.message, "error");
  }
}
/**
 * Mark as Under Review
 */
export async function handleUnderReview(inquiryId, note = "") {
  await handleUpdateStatus(inquiryId, "under_review", note || "Started review");
}

/**
 * Mark as Contacted
 */
export async function handleContacted(inquiryId, note = "") {
  await handleUpdateStatus(
    inquiryId,
    "contacted",
    note || "Customer contacted",
  );
}

/**
 * Mark as Approved
 */
export async function handleApprove(inquiryId, note = "") {
  await handleUpdateStatus(
    inquiryId,
    "approved",
    note || "Approved by customer",
  );
}

export async function handleApproveA(inquiryId) {
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  if (!confirm("Approve this inquiry?")) return;

  try {
    const result = await InquiryAPI.updateStatus(
      inquiryId,
      "approved",
      "Approved by staff",
    );
    if (result) {
      showToast("✅ Inquiry approved!", "success");
      await loadInquiries();
      if (DOM.drawer()?.classList.contains("active")) {
        await loadInquiryDetail(inquiryId);
      }
    }
  } catch (error) {
    console.error("Approve error:", error);
    showToast("❌ Failed to approve inquiry: " + error.message, "error");
  }
}

export async function handleMarkComplete(inquiryId) {
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  if (!confirm("Mark this inquiry as completed?")) return;

  try {
    const result = await InquiryAPI.updateStatus(
      inquiryId,
      "completed",
      "Project completed",
    );
    if (result) {
      showToast("✅ Inquiry marked as completed!", "success");
      await loadInquiries();
      if (DOM.drawer()?.classList.contains("active")) {
        await loadInquiryDetail(inquiryId);
      }
    }
  } catch (error) {
    console.error("Complete error:", error);
    showToast("❌ Failed to mark as completed: " + error.message, "error");
  }
}

export function handleWhatsApp(inquiry) {
  if (!inquiry) {
    showToast("No inquiry data available", "error");
    return;
  }

  const phone = inquiry.customer_phone_number;
  if (!phone) {
    showToast("No phone number available", "error");
    return;
  }

  const cleanPhone = phone.replace(/[^0-9]/g, "");
  if (cleanPhone.length < 8) {
    showToast("Invalid phone number", "error");
    return;
  }

  const name = inquiry.customer_name || "Customer";
  const brand = inquiry.vehicle_brand || "";
  const model = inquiry.vehicle_model || "";
  const type = inquiry.project_type || "";

  const message = encodeURIComponent(
    `Halo ${name},\n\n` +
      `Kami dari NOCTRA ingin menindaklanjuti inquiry Anda mengenai:\n` +
      `• Kendaraan: ${brand} ${model}\n` +
      `• Tipe Proyek: ${type}\n\n` +
      `Ada yang bisa kami bantu? 😊`,
  );

  window.open(`https://wa.me/${cleanPhone}?text=${message}`, "_blank");
  showToast("📱 Opening WhatsApp...", "info");
}

export async function handleSaveNote() {
  const inquiryId = state.currentInquiryId;
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  const noteEl = DOM.drawerNotes();
  if (!noteEl) {
    showToast("Note input not found", "error");
    return;
  }

  const note = noteEl.value?.trim();
  if (!note) {
    showToast("Please enter a note", "error");
    noteEl.focus();
    return;
  }

  if (note.length > 500) {
    showToast("Note is too long (max 500 characters)", "warning");
    return;
  }

  try {
    const result = await InquiryAPI.addNote(inquiryId, note, "internal", false);
    if (result) {
      showToast("✅ Note saved!", "success");
      const counter = DOM.noteCounter();
      if (counter) counter.textContent = note.length;

      // ✅ Refresh activities to show note was added
      const activities = await InquiryAPI.fetchActivities(inquiryId, 50);
      const timelineContainer = DOM.drawerTimeline();
      if (timelineContainer) {
        import("../renderers/timeline.js").then(({ renderDrawerTimeline }) => {
          renderDrawerTimeline(activities);
        });
      }
    }
  } catch (error) {
    console.error("Save note error:", error);
    showToast("❌ Failed to save note: " + error.message, "error");
  }
}

// ============================================================
// ✅ EXPORT: handleClose - FIXED
// ============================================================

/**
 * Close inquiry with reason
 */
export async function handleClose(inquiryId, reason = "") {
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  const reasonText = reason || prompt("Enter reason for closing this inquiry:");
  if (reasonText === null) return; // User cancelled

  if (!reasonText.trim()) {
    showToast("Please provide a reason for closing", "warning");
    return;
  }

  await handleUpdateStatus(inquiryId, "closed", reasonText.trim());
}

/**
 * Close inquiry with confirmation
 */
export async function handleCloseInquiry(inquiryId, reason = "") {
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  if (!confirm("Are you sure you want to close this inquiry?")) return;

  const reasonText = reason || prompt("Enter reason for closing this inquiry:");
  if (reasonText === null) return;

  if (!reasonText.trim()) {
    showToast("Please provide a reason for closing", "warning");
    return;
  }

  await handleUpdateStatus(inquiryId, "closed", reasonText.trim());
}

// ============================================================
// ✅ EXPORT: Reject Inquiry
// ============================================================

export async function handleReject(inquiryId, reason = "") {
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  const reasonText =
    reason || prompt("Enter reason for rejecting this inquiry:");
  if (reasonText === null) return;

  if (!reasonText.trim()) {
    showToast("Please provide a reason for rejection", "warning");
    return;
  }

  if (!confirm("Reject this inquiry?")) return;

  try {
    const result = await InquiryAPI.reject(inquiryId, reasonText.trim());
    if (result) {
      showToast("Inquiry rejected", "info");
      await loadInquiries();
      if (DOM.drawer()?.classList.contains("active")) {
        await loadInquiryDetail(inquiryId);
      }
    }
  } catch (error) {
    console.error("Reject error:", error);
    showToast("❌ Failed to reject inquiry: " + error.message, "error");
  }
}
