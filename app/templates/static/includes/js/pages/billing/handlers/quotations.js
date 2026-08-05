// ============================================================
// billing/handlers/quotations.js - Quotation Actions
// ============================================================

import { InquiryAPI } from "../api.js";
import { showToast } from "../../shared/toast.js";
import { openInvoiceModal } from "./modals.js";
import { loadBillingData } from "../index.js";

// ============================================================
// VIEW QUOTATION
// ============================================================

export async function handleViewQuotation(inquiryId) {
  // Open the inquiry drawer from inquiries module
  if (window.openInquiryDrawer) {
    window.openInquiryDrawer(inquiryId);
  } else {
    // Fallback
    try {
      const inquiry = await InquiryAPI.fetchDetail(inquiryId);
      if (inquiry) {
        showToast(
          `Quotation for ${inquiry.customer_name || "Customer"}: ${inquiry.estimated_cost || 0}`,
          "info",
          5000,
        );
      }
    } catch (error) {
      showToast("Failed to load quotation details", "error");
    }
  }
}

// ============================================================
// CONVERT QUOTE TO INVOICE
// ============================================================

export async function handleConvertQuoteToInvoice(inquiryId) {
  if (!inquiryId) {
    showToast("No quotation selected", "error");
    return;
  }

  // Verify the inquiry is approved
  try {
    const inquiry = await InquiryAPI.fetchDetail(inquiryId);
    if (!inquiry) {
      showToast("Quotation not found", "error");
      return;
    }

    if (inquiry.status !== "approved") {
      showToast(
        "Only approved quotations can be converted to invoices",
        "warning",
      );
      return;
    }

    // Check if already converted
    if (inquiry.status === "converted") {
      showToast("This quotation has already been converted", "info");
      return;
    }

    // Open modal with pre-filled data
    openInvoiceModal(inquiryId);
  } catch (error) {
    console.error("Failed to convert quote:", error);
    showToast("Failed to prepare conversion: " + error.message, "error");
  }
}

// ============================================================
// RESEND QUOTE
// ============================================================

export async function handleResendQuote(inquiryId) {
  if (!inquiryId) return;

  if (!confirm("Resend quotation to customer?")) return;

  try {
    // Re-fetch and trigger send quote endpoint
    // Assuming there's a way to resend - we can use the sendQuotation endpoint again
    const inquiry = await InquiryAPI.fetchDetail(inquiryId);
    if (!inquiry) {
      showToast("Quotation not found", "error");
      return;
    }

    // Use the sendQuotation endpoint with existing data
    const result = await InquiryAPI.sendQuotation(
      inquiryId,
      inquiry.estimated_cost || 0,
      "Resent quotation from Billing page",
    );

    if (result) {
      showToast("✅ Quotation resent successfully!", "success");
      await loadBillingData();
    } else {
      showToast("❌ Failed to resend quotation", "error");
    }
  } catch (error) {
    showToast("❌ " + (error.message || "Failed to resend"), "error");
  }
}

// ============================================================
// REJECT QUOTE
// ============================================================

export async function handleRejectQuote(inquiryId) {
  if (!inquiryId) return;

  if (!confirm("Reject this quotation?")) return;

  try {
    const result = await InquiryAPI.reject(
      inquiryId,
      "Rejected from Billing page",
    );
    if (result) {
      showToast("❌ Quotation rejected", "info");
      await loadBillingData();
    } else {
      showToast("❌ Failed to reject quotation", "error");
    }
  } catch (error) {
    showToast("❌ " + (error.message || "Failed to reject"), "error");
  }
}
