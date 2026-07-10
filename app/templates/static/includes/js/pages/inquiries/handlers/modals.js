// inquiries/handlers/modals.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { InquiryAPI } from "../api.js";
import { showToast } from "../toast.js";
import { state } from "../config.js";
import { loadInquiries } from "../index.js";
import { loadInquiryDetail } from "../drawer.js";
import { handleUpdateStatus } from "./actions.js";

// ============================================================
// CONVERT MODAL
// ============================================================

export function openConvertModal(inquiryId) {
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  state._convertInquiryId = inquiryId;

  const startDate = DOM.convertStartDate();
  const targetDate = DOM.convertTargetDelivery();
  const modal = DOM.convertModal();

  if (startDate) {
    startDate.value = new Date().toISOString().split("T")[0];
  }
  if (targetDate) {
    // ✅ Default target: 14 days from now
    const target = new Date();
    target.setDate(target.getDate() + 14);
    targetDate.value = target.toISOString().split("T")[0];
  }
  if (modal) modal.classList.add("active");
}

export function closeConvertModal() {
  const modal = DOM.convertModal();
  if (modal) modal.classList.remove("active");
  state._convertInquiryId = null;
}

export async function handleConvert(e) {
  if (e) e.preventDefault();

  const inquiryId = state._convertInquiryId;
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  const startDate = DOM.convertStartDate()?.value || null;
  const targetDelivery = DOM.convertTargetDelivery()?.value || null;

  if (!startDate) {
    showToast("Please select a start date", "warning");
    DOM.convertStartDate()?.focus();
    return;
  }

  try {
    const result = await InquiryAPI.convertToProject(
      inquiryId,
      startDate,
      targetDelivery,
    );

    if (result) {
      const projectId = result.id || result.project_id;
      showToast(
        `🎉 Project created successfully! ${projectId ? `ID: ${projectId.substring(0, 8)}` : ""}`,
        "success",
      );
      closeConvertModal();
      await loadInquiries();

      if (DOM.drawer()?.classList.contains("active")) {
        await loadInquiryDetail(inquiryId);
      }
    }
  } catch (error) {
    console.error("Convert error:", error);
    showToast("❌ Failed to convert to project: " + error.message, "error");
  }
}

// ============================================================
// QUOTE MODAL
// ============================================================

export function openQuoteModal(inquiryId) {
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  state._quoteInquiryId = inquiryId;

  const costEl = DOM.quoteCost();
  const notesEl = DOM.quoteNotes();
  const modal = DOM.quoteModal();

  if (costEl) costEl.value = "";
  if (notesEl) notesEl.value = "";
  if (modal) {
    modal.classList.add("active");
    // ✅ Focus on cost field
    setTimeout(() => costEl?.focus(), 100);
  }
}

export function closeQuoteModal() {
  const modal = DOM.quoteModal();
  if (modal) modal.classList.remove("active");
  state._quoteInquiryId = null;
}

export async function handleSendQuote(e) {
  if (e) e.preventDefault();

  const inquiryId = state._quoteInquiryId;
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  const cost = parseFloat(DOM.quoteCost()?.value);
  if (!cost || cost <= 0) {
    showToast("Please enter a valid estimated cost", "error");
    DOM.quoteCost()?.focus();
    return;
  }

  const notes = DOM.quoteNotes()?.value?.trim() || "";

  try {
    const result = await InquiryAPI.sendQuotation(inquiryId, cost, notes);
    if (result) {
      showToast(
        `📄 Quotation sent! (${new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR" }).format(cost)})`,
        "success",
      );
      closeQuoteModal();
      await handleUpdateStatus(
        inquiryId,
        "quoted",
        `Quotation sent: Rp ${cost.toLocaleString()}`,
      );
    }
  } catch (error) {
    console.error("Quote error:", error);
    showToast("❌ Failed to send quotation: " + error.message, "error");
  }
}

// ============================================================
// REJECT MODAL
// ============================================================

export function openRejectModal(inquiryId) {
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  state._rejectInquiryId = inquiryId;

  const reasonEl = DOM.rejectReason();
  const modal = DOM.rejectModal();

  if (reasonEl) reasonEl.value = "";
  if (modal) {
    modal.classList.add("active");
    setTimeout(() => reasonEl?.focus(), 100);
  }
}

export function closeRejectModal() {
  const modal = DOM.rejectModal();
  if (modal) modal.classList.remove("active");
  state._rejectInquiryId = null;
}

export async function handleReject(e) {
  if (e) e.preventDefault();

  const inquiryId = state._rejectInquiryId;
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  const reason = DOM.rejectReason()?.value?.trim() || "No reason provided";

  if (!confirm(`Reject this inquiry?\n\nReason: ${reason}`)) return;

  try {
    const result = await InquiryAPI.reject(inquiryId, reason);
    if (result) {
      showToast("❌ Inquiry rejected", "info");
      closeRejectModal();
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
