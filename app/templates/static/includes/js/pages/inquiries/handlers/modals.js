// ============================================================
// inquiries/handlers/modals.js - Modal Functions
// ============================================================

import { DOM } from "../dom.js";
import { InquiryAPI } from "../api.js";
import { showToast } from "../toast.js";
import { state } from "../config.js";
import { loadInquiries } from "../index.js";
import { loadInquiryDetail } from "../drawer.js";
import { handleUpdateStatus } from "./actions.js";

// --- Convert Modal ---
export function openConvertModal(inquiryId) {
  state._convertInquiryId = inquiryId;
  if (DOM.convertStartDate())
    DOM.convertStartDate().value = new Date().toISOString().split("T")[0];
  if (DOM.convertTargetDelivery()) DOM.convertTargetDelivery().value = "";
  if (DOM.convertModal()) DOM.convertModal().classList.add("active");
}

export function closeConvertModal() {
  if (DOM.convertModal()) DOM.convertModal().classList.remove("active");
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

  const result = await InquiryAPI.convertToProject(
    inquiryId,
    startDate,
    targetDelivery,
  );
  if (result) {
    showToast("🎉 Project created successfully!", "success");
    closeConvertModal();
    await loadInquiries();
    if (DOM.drawer()?.classList.contains("active"))
      await loadInquiryDetail(inquiryId);
  }
}

// --- Quote Modal ---
export function openQuoteModal(inquiryId) {
  state._quoteInquiryId = inquiryId;
  if (DOM.quoteCost()) DOM.quoteCost().value = "";
  if (DOM.quoteNotes()) DOM.quoteNotes().value = "";
  if (DOM.quoteModal()) DOM.quoteModal().classList.add("active");
}

export function closeQuoteModal() {
  if (DOM.quoteModal()) DOM.quoteModal().classList.remove("active");
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
    return;
  }

  const notes = DOM.quoteNotes()?.value?.trim() || "";
  const result = await InquiryAPI.sendQuotation(inquiryId, cost, notes);
  if (result) {
    showToast("Quotation sent!", "success");
    closeQuoteModal();
    await handleUpdateStatus(inquiryId, "quoted", "Quotation sent");
  }
}

// --- Reject Modal ---
export function openRejectModal(inquiryId) {
  state._rejectInquiryId = inquiryId;
  if (DOM.rejectReason()) DOM.rejectReason().value = "";
  if (DOM.rejectModal()) DOM.rejectModal().classList.add("active");
}

export function closeRejectModal() {
  if (DOM.rejectModal()) DOM.rejectModal().classList.remove("active");
  state._rejectInquiryId = null;
}

export async function handleReject(e) {
  if (e) e.preventDefault();
  const inquiryId = state._rejectInquiryId;
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  const reason = DOM.rejectReason()?.value?.trim() || "";
  if (!confirm("Reject this inquiry?")) return;

  const result = await InquiryAPI.reject(inquiryId, reason);
  if (result) {
    showToast("Inquiry rejected", "info");
    closeRejectModal();
    await loadInquiries();
    if (DOM.drawer()?.classList.contains("active"))
      await loadInquiryDetail(inquiryId);
  }
}
