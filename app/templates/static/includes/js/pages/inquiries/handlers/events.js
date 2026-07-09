// ============================================================
// inquiries/handlers/events.js - FULL FIXED
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { loadInquiries } from "../index.js";
import { closeDrawer, loadInquiryDetail } from "../drawer.js";
import { handleApprove, handleWhatsApp, handleSaveNote } from "./actions.js";
import {
  openConvertModal,
  closeConvertModal,
  handleConvert,
  openQuoteModal,
  closeQuoteModal,
  handleSendQuote,
  openRejectModal,
  closeRejectModal,
  handleReject,
} from "./modals.js";
import { closeLightbox, navigateLightbox } from "../renderers/carousel.js";
import { showToast } from "../toast.js";
import { exportInquiries } from "../index.js";
import { Formatter } from "../formatters.js";

// ✅ Import Payment API
import { PaymentAPI } from "../../shared/payments/api.js";

// ============================================================
// PAYMENT HANDLERS
// ============================================================

/**
 * Close Payment Modal
 */
export function closePaymentModal() {
  const modal = document.getElementById("paymentModal");
  if (modal) modal.classList.remove("active");
  // Reset form
  const form = document.getElementById("paymentForm");
  if (form) form.reset();
}

/**
 * Close Invoice Modal
 */
export function closeInvoiceModal() {
  const modal = document.getElementById("invoiceModal");
  if (modal) modal.classList.remove("active");
  // Reset form
  const form = document.getElementById("invoiceForm");
  if (form) form.reset();
  // Clear items
  const container = document.getElementById("invoiceItemsContainer");
  if (container) {
    container.innerHTML = `
      <div class="invoice-item-row">
        <input type="text" class="item-description" placeholder="Description *" />
        <input type="number" class="item-quantity" placeholder="Qty" value="1" min="1" />
        <input type="text" class="item-unit" placeholder="Unit" />
        <input type="number" class="item-unit-price" placeholder="Unit Price *" step="1000" min="0" />
        <button type="button" class="btn-danger btn-sm remove-item-btn" title="Remove item">&times;</button>
      </div>
    `;
    // Re-bind remove button
    const removeBtn = container.querySelector(".remove-item-btn");
    if (removeBtn) {
      removeBtn.addEventListener("click", function () {
        const row = this.closest(".invoice-item-row");
        if (row && container.children.length > 1) {
          row.remove();
          calculateInvoiceTotal();
        }
      });
    }
    // Re-bind inputs
    container.querySelectorAll("input").forEach((input) => {
      input.addEventListener("input", calculateInvoiceTotal);
    });
  }
  // Reset totals
  const subtotalEl = document.getElementById("invoiceSubtotal");
  const totalEl = document.getElementById("invoiceTotal");
  if (subtotalEl) subtotalEl.textContent = "Rp 0";
  if (totalEl) totalEl.textContent = "Rp 0";
}

/**
 * Calculate Invoice Total
 */
function calculateInvoiceTotal() {
  const rows = document.querySelectorAll(".invoice-item-row");
  let total = 0;

  rows.forEach((row) => {
    const qty = parseFloat(row.querySelector(".item-quantity")?.value) || 0;
    const price = parseFloat(row.querySelector(".item-unit-price")?.value) || 0;
    total += qty * price;
  });

  const subtotalEl = document.getElementById("invoiceSubtotal");
  const totalEl = document.getElementById("invoiceTotal");
  if (subtotalEl) subtotalEl.textContent = Formatter.currency(total);
  if (totalEl) totalEl.textContent = Formatter.currency(total);
}

/**
 * Handle Payment Submit (Add Deposit / Add Payment)
 */
async function handlePaymentSubmit(e) {
  e.preventDefault();

  const form = document.getElementById("paymentForm");
  const submitBtn = form.querySelector('button[type="submit"]');

  // Get form data
  const paymentData = {
    inquiry_id: document.getElementById("paymentInquiryId")?.value || null,
    project_id: document.getElementById("paymentProjectId")?.value || null,
    invoice_id:
      document.getElementById("paymentInvoiceId")?.value?.trim() || null, // added
    type: document.getElementById("paymentType")?.value || "payment",
    amount: parseFloat(document.getElementById("paymentAmount")?.value) || 0,
    method: document.getElementById("paymentMethod")?.value || "bank_transfer",
    reference_number:
      document.getElementById("paymentReference")?.value || null,
    payment_date: document.getElementById("paymentDate")?.value || null,
    due_date: document.getElementById("paymentDueDate")?.value || null,
    notes: document.getElementById("paymentNotes")?.value || null,
    status: "pending", // Default status
    payment_proof: null, // ✅ Tambahkan field yang required
  };

  // ✅ Debug: Log payload
  console.log("📤 Payment Payload:", JSON.stringify(paymentData, null, 2));

  // ✅ Validasi
  if (!paymentData.inquiry_id) {
    showToast("❌ Inquiry ID is required", "error");
    return;
  }

  if (paymentData.amount <= 0) {
    showToast("❌ Amount must be greater than 0", "error");
    return;
  }

  // ✅ Konfirmasi untuk deposit
  const typeLabel = paymentData.type === "deposit" ? "Deposit" : "Payment";
  const confirmMsg = `Record ${typeLabel} of ${Formatter.currency(paymentData.amount)} for this inquiry?`;
  if (!confirm(confirmMsg)) return;

  // Disable button
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="ph ph-spinner spin"></i> Saving...';

  try {
    // ✅ Panggil API Create Payment
    const result = await PaymentAPI.create(paymentData);

    if (result) {
      const typeIcon = paymentData.type === "deposit" ? "🏦" : "💳";
      showToast(
        `${typeIcon} ${typeLabel} of ${Formatter.currency(paymentData.amount)} recorded successfully!`,
        "success",
      );
      closePaymentModal();

      // ✅ Refresh drawer jika masih terbuka
      if (
        state.currentInquiryId &&
        DOM.drawer()?.classList.contains("active")
      ) {
        await loadInquiryDetail(state.currentInquiryId);
      }

      // ✅ Refresh table
      await loadInquiries();
    } else {
      showToast("❌ Failed to save payment. Please try again.", "error");
    }
  } catch (error) {
    console.error("Payment error:", error);
    showToast("❌ Failed to save payment: " + error.message, "error");
  } finally {
    // Enable button
    submitBtn.disabled = false;
    submitBtn.innerHTML = "Save Payment";
  }
}

/**
 * Handle Invoice Submit
 */
async function handleInvoiceSubmit(e) {
  e.preventDefault();

  const form = document.getElementById("invoiceForm");
  const submitBtn = form.querySelector('button[type="submit"]');

  // Get invoice items
  const itemRows = document.querySelectorAll(".invoice-item-row");
  const items = [];
  let hasError = false;

  itemRows.forEach((row) => {
    const desc = row.querySelector(".item-description")?.value?.trim();
    const qty = parseFloat(row.querySelector(".item-quantity")?.value) || 1;
    const unit = row.querySelector(".item-unit")?.value?.trim() || "";
    const price = parseFloat(row.querySelector(".item-unit-price")?.value) || 0;

    if (desc && price > 0) {
      items.push({
        description: desc,
        quantity: qty,
        unit: unit,
        unit_price: price,
      });
    } else if (desc || price > 0) {
      hasError = true;
    }
  });

  if (items.length === 0) {
    showToast("❌ Please add at least one valid invoice item", "error");
    return;
  }

  if (hasError) {
    showToast("⚠️ Some items have missing description or price", "warning");
    return;
  }

  // Get invoice data
  const invoiceData = {
    inquiry_id: document.getElementById("invoiceInquiryId")?.value || null,
    project_id: document.getElementById("invoiceProjectId")?.value || null,
    invoice_number:
      document.getElementById("invoiceNumber")?.value?.trim() || null,
    payment_terms:
      document.getElementById("invoicePaymentTerms")?.value?.trim() || null,
    invoice_date: document.getElementById("invoiceDate")?.value || null,
    due_date: document.getElementById("invoiceDueDate")?.value || null,
    notes: document.getElementById("invoiceNotes")?.value?.trim() || null,
    items: items,
    status: "draft",
  };

  // ✅ Validasi
  if (!invoiceData.inquiry_id) {
    showToast("❌ Inquiry ID is required", "error");
    return;
  }

  if (!invoiceData.invoice_number) {
    showToast("❌ Invoice Number is required", "error");
    return;
  }

  // ✅ Konfirmasi
  const totalAmount = items.reduce(
    (sum, item) => sum + item.quantity * item.unit_price,
    0,
  );
  const confirmMsg = `Create invoice ${invoiceData.invoice_number} for ${Formatter.currency(totalAmount)}?`;
  if (!confirm(confirmMsg)) return;

  // Disable button
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="ph ph-spinner spin"></i> Creating...';

  try {
    // ✅ Panggil API Create Invoice
    const result = await PaymentAPI.createInvoice(invoiceData);

    if (result) {
      showToast(
        `✅ Invoice ${invoiceData.invoice_number} created successfully! (${Formatter.currency(totalAmount)})`,
        "success",
      );
      closeInvoiceModal();

      // ✅ Refresh drawer jika masih terbuka
      if (
        state.currentInquiryId &&
        DOM.drawer()?.classList.contains("active")
      ) {
        await loadInquiryDetail(state.currentInquiryId);
      }

      // ✅ Refresh table
      await loadInquiries();
    } else {
      showToast("❌ Failed to create invoice. Please try again.", "error");
    }
  } catch (error) {
    console.error("Invoice error:", error);
    showToast("❌ Failed to create invoice: " + error.message, "error");
  } finally {
    // Enable button
    submitBtn.disabled = false;
    submitBtn.innerHTML = "Create Invoice";
  }
}

/**
 * Add Invoice Item Row
 */
function addInvoiceItemRow() {
  const container = document.getElementById("invoiceItemsContainer");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "invoice-item-row";
  row.style.cssText = `
    display: grid;
    grid-template-columns: 2fr 80px 80px 120px 40px;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;
  `;

  row.innerHTML = `
    <input type="text" class="item-description" placeholder="Description *" style="padding:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-input);color:var(--text-primary);width:100%;" />
    <input type="number" class="item-quantity" placeholder="Qty" value="1" min="1" style="padding:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-input);color:var(--text-primary);width:100%;" />
    <input type="text" class="item-unit" placeholder="Unit" style="padding:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-input);color:var(--text-primary);width:100%;" />
    <input type="number" class="item-unit-price" placeholder="Price *" step="1000" min="0" style="padding:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-input);color:var(--text-primary);width:100%;" />
    <button type="button" class="btn-danger btn-sm remove-item-btn" style="padding:4px 8px;background:#ef4444;color:white;border:none;border-radius:var(--radius-sm);cursor:pointer;font-size:1.2rem;">&times;</button>
  `;

  container.appendChild(row);

  // ✅ Bind events
  row.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", calculateInvoiceTotal);
  });

  const removeBtn = row.querySelector(".remove-item-btn");
  removeBtn.addEventListener("click", function () {
    if (container.children.length > 1) {
      row.remove();
      calculateInvoiceTotal();
    } else {
      showToast("Cannot remove the last item", "warning");
    }
  });

  calculateInvoiceTotal();
}

// ============================================================
// BIND EVENTS - MAIN FUNCTION
// ============================================================

export function bindEvents() {
  // ============================================================
  // 1. PAGINATION
  // ============================================================
  DOM.prevPage()?.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage--;
      loadInquiries();
    }
  });

  DOM.nextPage()?.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      state.currentPage++;
      loadInquiries();
    }
  });

  // ============================================================
  // 2. SEARCH & FILTER
  // ============================================================
  let searchTimeout;
  DOM.searchInquiry()?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.currentPage = 1;
      loadInquiries();
    }, 300);
  });

  DOM.statusFilter()?.addEventListener("change", (e) => {
    state.filters.status = e.target.value;
    state.currentPage = 1;
    loadInquiries();
  });

  // ============================================================
  // 3. EXPORT
  // ============================================================
  DOM.exportInquiriesBtn()?.addEventListener("click", exportInquiries);

  // ============================================================
  // 4. DRAWER
  // ============================================================
  DOM.closeDrawer()?.addEventListener("click", closeDrawer);
  DOM.drawerBackdrop()?.addEventListener("click", closeDrawer);

  // ============================================================
  // 5. MODALS - Convert, Quote, Reject
  // ============================================================
  // Convert Modal
  DOM.closeConvertModal()?.addEventListener("click", closeConvertModal);
  DOM.cancelConvertBtn()?.addEventListener("click", closeConvertModal);
  DOM.convertModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.convertModal()) closeConvertModal();
  });
  DOM.convertForm()?.addEventListener("submit", handleConvert);

  // Quote Modal
  DOM.closeQuoteModal()?.addEventListener("click", closeQuoteModal);
  DOM.cancelQuoteBtn()?.addEventListener("click", closeQuoteModal);
  DOM.quoteModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.quoteModal()) closeQuoteModal();
  });
  DOM.quoteForm()?.addEventListener("submit", handleSendQuote);

  // Reject Modal
  DOM.closeRejectModal()?.addEventListener("click", closeRejectModal);
  DOM.cancelRejectBtn()?.addEventListener("click", closeRejectModal);
  DOM.rejectModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.rejectModal()) closeRejectModal();
  });
  DOM.rejectForm()?.addEventListener("submit", handleReject);

  // ============================================================
  // 6. DRAWER ACTION BUTTONS
  // ============================================================
  DOM.drawerApproveBtn()?.addEventListener("click", () => {
    if (state.currentInquiryId) handleApprove(state.currentInquiryId);
  });

  DOM.drawerQuoteBtn()?.addEventListener("click", () => {
    if (state.currentInquiryId) openQuoteModal(state.currentInquiryId);
  });

  DOM.drawerRejectBtn()?.addEventListener("click", () => {
    if (state.currentInquiryId) openRejectModal(state.currentInquiryId);
  });

  DOM.drawerWhatsappBtn()?.addEventListener("click", () => {
    if (state._currentInquiry) handleWhatsApp(state._currentInquiry);
  });

  DOM.drawerConvertBtn()?.addEventListener("click", () => {
    if (state.currentInquiryId) openConvertModal(state.currentInquiryId);
  });

  // ============================================================
  // 7. PAYMENT MODAL - Add Deposit & Add Payment
  // ============================================================
  const paymentModal = document.getElementById("paymentModal");
  const closePaymentBtn = document.getElementById("closePaymentModal");
  const cancelPaymentBtn = document.getElementById("cancelPaymentBtn");
  const paymentForm = document.getElementById("paymentForm");

  // Close modal
  closePaymentBtn?.addEventListener("click", closePaymentModal);
  cancelPaymentBtn?.addEventListener("click", closePaymentModal);
  paymentModal?.addEventListener("click", (e) => {
    if (e.target === paymentModal) closePaymentModal();
  });

  // Submit payment
  paymentForm?.addEventListener("submit", handlePaymentSubmit);

  // ✅ Tombol Add Deposit
  DOM.addDepositBtn()?.addEventListener("click", () => {
    const inquiryId = state.currentInquiryId;
    if (!inquiryId) {
      showToast("❌ No inquiry selected", "error");
      return;
    }

    // Set inquiry ID
    const inquiryInput = document.getElementById("paymentInquiryId");
    if (inquiryInput) {
      inquiryInput.value = inquiryId;
      inquiryInput.disabled = true;
    }

    // Set type ke deposit
    const typeSelect = document.getElementById("paymentType");
    if (typeSelect) {
      typeSelect.value = "deposit";
    }

    // Set default date
    const dateInput = document.getElementById("paymentDate");
    if (dateInput) {
      dateInput.value = new Date().toISOString().split("T")[0];
    }

    // Buka modal
    if (paymentModal) paymentModal.classList.add("active");
    showToast("🏦 Add deposit for this inquiry", "info", 2000);
  });

  // ✅ Tombol Add Payment
  DOM.addPaymentBtn()?.addEventListener("click", () => {
    const inquiryId = state.currentInquiryId;
    if (!inquiryId) {
      showToast("❌ No inquiry selected", "error");
      return;
    }

    // Set inquiry ID
    const inquiryInput = document.getElementById("paymentInquiryId");
    if (inquiryInput) {
      inquiryInput.value = inquiryId;
      inquiryInput.disabled = true;
    }

    // Set type ke payment
    const typeSelect = document.getElementById("paymentType");
    if (typeSelect) {
      typeSelect.value = "payment";
    }

    // Set default date
    const dateInput = document.getElementById("paymentDate");
    if (dateInput) {
      dateInput.value = new Date().toISOString().split("T")[0];
    }

    // Buka modal
    if (paymentModal) paymentModal.classList.add("active");
    showToast("💳 Add payment for this inquiry", "info", 2000);
  });

  // ============================================================
  // 8. INVOICE MODAL
  // ============================================================
  const invoiceModal = document.getElementById("invoiceModal");
  const closeInvoiceBtn = document.getElementById("closeInvoiceModal");
  const cancelInvoiceBtn = document.getElementById("cancelInvoiceBtn");
  const invoiceForm = document.getElementById("invoiceForm");

  // Close modal
  closeInvoiceBtn?.addEventListener("click", closeInvoiceModal);
  cancelInvoiceBtn?.addEventListener("click", closeInvoiceModal);
  invoiceModal?.addEventListener("click", (e) => {
    if (e.target === invoiceModal) closeInvoiceModal();
  });

  // Submit invoice
  invoiceForm?.addEventListener("submit", handleInvoiceSubmit);

  // ✅ Tombol View Invoices
  DOM.viewInvoicesBtn()?.addEventListener("click", () => {
    const inquiryId = state.currentInquiryId;
    if (!inquiryId) {
      showToast("❌ No inquiry selected", "error");
      return;
    }

    // Set inquiry ID
    const inquiryInput = document.getElementById("invoiceInquiryId");
    if (inquiryInput) {
      inquiryInput.value = inquiryId;
      inquiryInput.disabled = true;
    }

    // Generate invoice number auto
    const invoiceNumberInput = document.getElementById("invoiceNumber");
    if (invoiceNumberInput) {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, "0");
      const day = String(now.getDate()).padStart(2, "0");
      const random = String(Math.floor(Math.random() * 1000)).padStart(3, "0");
      invoiceNumberInput.value = `INV-${year}${month}${day}-${random}`;
    }

    // Set default date
    const dateInput = document.getElementById("invoiceDate");
    if (dateInput) {
      dateInput.value = new Date().toISOString().split("T")[0];
    }

    // Set default due date (30 days later)
    const dueDateInput = document.getElementById("invoiceDueDate");
    if (dueDateInput) {
      const due = new Date();
      due.setDate(due.getDate() + 30);
      dueDateInput.value = due.toISOString().split("T")[0];
    }

    // Buka modal
    if (invoiceModal) invoiceModal.classList.add("active");
    showToast("📄 Create invoice for this inquiry", "info", 2000);
  });

  // ============================================================
  // 9. ADD INVOICE ITEM
  // ============================================================
  document
    .getElementById("addInvoiceItemBtn")
    ?.addEventListener("click", addInvoiceItemRow);

  // ============================================================
  // 10. LIGHTBOX
  // ============================================================
  DOM.lightboxClose()?.addEventListener("click", closeLightbox);
  DOM.lightboxOverlay()?.addEventListener("click", (e) => {
    if (e.target === DOM.lightboxOverlay()) closeLightbox();
  });
  DOM.lightboxPrev()?.addEventListener("click", () => navigateLightbox(-1));
  DOM.lightboxNext()?.addEventListener("click", () => navigateLightbox(1));

  // Keyboard shortcuts for lightbox
  document.addEventListener("keydown", (e) => {
    if (state.lightbox.isOpen) {
      if (e.key === "ArrowLeft") navigateLightbox(-1);
      if (e.key === "ArrowRight") navigateLightbox(1);
      if (e.key === "Escape") closeLightbox();
    }
  });

  // ============================================================
  // 11. NOTES - Auto-save
  // ============================================================
  if (DOM.drawerNotes()) {
    DOM.drawerNotes().addEventListener("input", () => {
      if (DOM.noteCounter()) {
        DOM.noteCounter().textContent = DOM.drawerNotes().value.length;
      }
    });

    let noteSaveTimeout;
    DOM.drawerNotes().addEventListener("blur", () => {
      clearTimeout(noteSaveTimeout);
      noteSaveTimeout = setTimeout(() => {
        if (DOM.drawerNotes()?.value?.trim()) {
          handleSaveNote();
        }
      }, 1000);
    });
  }

  // ============================================================
  // 12. KEYBOARD SHORTCUTS
  // ============================================================
  document.addEventListener("keydown", (e) => {
    // Escape - close all modals
    if (e.key === "Escape") {
      // Close payment modal
      const paymentModal = document.getElementById("paymentModal");
      if (paymentModal?.classList.contains("active")) {
        closePaymentModal();
        return;
      }

      // Close invoice modal
      const invoiceModal = document.getElementById("invoiceModal");
      if (invoiceModal?.classList.contains("active")) {
        closeInvoiceModal();
        return;
      }

      // Close convert modal
      if (DOM.convertModal()?.classList.contains("active")) {
        closeConvertModal();
        return;
      }

      // Close quote modal
      if (DOM.quoteModal()?.classList.contains("active")) {
        closeQuoteModal();
        return;
      }

      // Close reject modal
      if (DOM.rejectModal()?.classList.contains("active")) {
        closeRejectModal();
        return;
      }

      // Close drawer
      if (DOM.drawer()?.classList.contains("active")) {
        closeDrawer();
        return;
      }

      // Close lightbox
      if (state.lightbox.isOpen) {
        closeLightbox();
        return;
      }
    }

    // Ctrl+F - Focus search
    if (e.ctrlKey && e.key === "f") {
      e.preventDefault();
      DOM.searchInquiry()?.focus();
    }

    // Ctrl+E - Export
    if (e.ctrlKey && e.key === "e") {
      e.preventDefault();
      exportInquiries();
    }
  });

  console.log("✅ All events bound successfully!");
}
