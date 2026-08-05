// ============================================================
// billing/handlers/invoices.js - Invoice Actions
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { BillingAPI } from "../api.js";
import { showToast } from "../../shared/toast.js";
import {
  openConfirmActionModal,
  closeConfirmActionModal,
  openInvoiceDetailModal,
  closeInvoiceDetailModal,
} from "./modals.js";
import { loadBillingData } from "../index.js";

// ============================================================
// SEND INVOICE
// ============================================================

export async function handleSendInvoice(invoiceId) {
  openConfirmActionModal(
    "Send Invoice",
    "Are you sure you want to send this invoice to the customer?",
    async () => {
      try {
        const result = await BillingAPI.sendInvoice(invoiceId);
        if (result) {
          showToast("✅ Invoice sent successfully!", "success");
          closeConfirmActionModal();
          await loadBillingData();
          // Refresh detail if open
          if (state.currentInvoiceId) {
            await openInvoiceDetailModal(state.currentInvoiceId);
          }
        } else {
          showToast("❌ Failed to send invoice", "error");
        }
      } catch (error) {
        showToast("❌ " + (error.message || "Failed to send invoice"), "error");
      }
    },
  );
}

// ============================================================
// MARK INVOICE AS PAID
// ============================================================

export async function handleMarkInvoicePaid(invoiceId) {
  openConfirmActionModal(
    "Mark as Paid",
    "Mark this invoice as paid? This will update the payment status.",
    async () => {
      try {
        const result = await BillingAPI.markInvoicePaid(invoiceId, {
          payment_method: "manual",
          notes: "Marked as paid from Billing page",
        });
        if (result) {
          showToast("✅ Invoice marked as paid!", "success");
          closeConfirmActionModal();
          await loadBillingData();
          if (state.currentInvoiceId) {
            await openInvoiceDetailModal(state.currentInvoiceId);
          }
        } else {
          showToast("❌ Failed to mark as paid", "error");
        }
      } catch (error) {
        showToast("❌ " + (error.message || "Failed to mark as paid"), "error");
      }
    },
  );
}

// ============================================================
// DELETE INVOICE
// ============================================================

export async function handleDeleteInvoice(invoiceId) {
  openConfirmActionModal(
    "Delete Invoice",
    "Are you sure you want to delete this invoice? This action cannot be undone.",
    async () => {
      try {
        const result = await BillingAPI.deleteInvoice(invoiceId);
        if (result) {
          showToast("🗑️ Invoice deleted", "success");
          closeConfirmActionModal();
          await loadBillingData();
          if (state.currentInvoiceId) {
            closeInvoiceDetailModal();
          }
        } else {
          showToast("❌ Failed to delete invoice", "error");
        }
      } catch (error) {
        showToast(
          "❌ " + (error.message || "Failed to delete invoice"),
          "error",
        );
      }
    },
  );
}

// ============================================================
// SEND INVOICE REMINDER
// ============================================================

export async function handleSendInvoiceReminder(invoiceId) {
  openConfirmActionModal(
    "Send Reminder",
    "Send a payment reminder for this overdue invoice?",
    async () => {
      try {
        const result = await BillingAPI.sendInvoiceReminder(
          invoiceId,
          "Reminder sent from Billing page",
        );
        if (result) {
          showToast("📨 Reminder sent!", "success");
          closeConfirmActionModal();
          await loadBillingData();
        } else {
          showToast("❌ Failed to send reminder", "error");
        }
      } catch (error) {
        showToast(
          "❌ " + (error.message || "Failed to send reminder"),
          "error",
        );
      }
    },
  );
}
