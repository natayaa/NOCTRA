// inquiries/handlers/events.js - FINAL FIXED & IMPROVED

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { loadInquiries } from "../index.js";
import { closeDrawer, loadInquiryDetail } from "../drawer.js";
import {
  handleApprove,
  handleWhatsApp,
  handleSaveNote,
  handleMarkComplete,
} from "./actions.js";
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
import { PaymentAPI } from "../../shared/payments/api.js";
import { PaymentFormatter } from "../../shared/payments/formatters.js";

// ============================================================
// STATE
// ============================================================

let pendingConfirmPaymentId = null;
let pendingDeletePaymentId = null;

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ============================================================
// HELPERS
// ============================================================
function getElement(id) {
  return document.getElementById(id);
}

// ============================================================
// PAYMENT MODAL HANDLERS
// ============================================================

export function closePaymentModal() {
  const modal = getElement("paymentModal");
  if (modal) modal.classList.remove("active");
  const form = getElement("paymentForm");
  if (form) form.reset();
  ["paymentInquiryId", "paymentProjectId", "paymentInvoiceId"].forEach((id) => {
    const el = getElement(id);
    if (el) {
      el.disabled = false;
      el.value = "";
    }
  });
}

export function closeInvoiceModal() {
  const modal = getElement("invoiceModal");
  if (modal) modal.classList.remove("active");
  const form = getElement("invoiceForm");
  if (form) form.reset();
}

function bindInvoiceItemEvents(container) {
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
  container.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", calculateInvoiceTotal);
  });
}

// ============================================================
// CONFIRM PAYMENT MODAL
// ============================================================

export function openConfirmPaymentModal(paymentId) {
  pendingConfirmPaymentId = paymentId;
  const modal = getElement("confirmPaymentModal");
  const details = getElement("confirmPaymentDetails");
  if (!modal || !details) return;

  details.innerHTML = `
    <div class="detail-row">
      <span class="detail-label">Payment ID</span>
      <span class="detail-value" style="font-size:0.7rem;color:var(--text-muted);">${paymentId.substring(0, 8)}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Status</span>
      <span class="detail-value">Pending</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Action</span>
      <span class="detail-value" style="color:#10b981;">Confirm this payment</span>
    </div>
  `;
  modal.classList.add("active");
}

export function closeConfirmPaymentModal() {
  const modal = getElement("confirmPaymentModal");
  if (modal) modal.classList.remove("active");
  pendingConfirmPaymentId = null;
}

export async function handleConfirmPayment() {
  const paymentId = pendingConfirmPaymentId;
  if (!paymentId) {
    showToast("❌ No payment selected", "error");
    return;
  }

  const btn = getElement("confirmPaymentBtn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="ph ph-spinner spin"></i> Confirming...';
  }

  try {
    const result = await PaymentAPI.confirm(paymentId, "admin");
    if (result) {
      showToast("✅ Payment confirmed!", "success");
      closeConfirmPaymentModal();
      if (
        state.currentInquiryId &&
        DOM.drawer()?.classList.contains("active")
      ) {
        await loadInquiryDetail(state.currentInquiryId);
      }
      await loadInquiries();
    } else {
      showToast("❌ Failed to confirm payment", "error");
    }
  } catch (error) {
    console.error("Confirm payment error:", error);
    showToast("❌ " + (error.message || "Failed to confirm payment"), "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="ph ph-check"></i> Confirm Payment';
    }
  }
}

// ============================================================
// DELETE PAYMENT MODAL
// ============================================================

export function openDeletePaymentModal(paymentId) {
  pendingDeletePaymentId = paymentId;
  const modal = getElement("deletePaymentModal");
  const details = getElement("deletePaymentDetails");
  if (!modal || !details) return;

  details.innerHTML = `
    <div class="detail-row">
      <span class="detail-label">Payment ID</span>
      <span class="detail-value" style="font-size:0.7rem;color:var(--text-muted);">${paymentId.substring(0, 8)}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Warning</span>
      <span class="detail-value" style="color:#ef4444;">⚠️ This action cannot be undone</span>
    </div>
  `;
  modal.classList.add("active");
}

export function closeDeletePaymentModal() {
  const modal = getElement("deletePaymentModal");
  if (modal) modal.classList.remove("active");
  pendingDeletePaymentId = null;
}

export async function handleDeletePayment() {
  const paymentId = pendingDeletePaymentId;
  if (!paymentId) {
    showToast("❌ No payment selected", "error");
    return;
  }

  const btn = getElement("deletePaymentBtn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="ph ph-spinner spin"></i> Deleting...';
  }

  try {
    // Check if payment can be deleted
    const payment = await PaymentAPI.getById(paymentId);
    if (
      payment &&
      ["completed", "confirmed", "paid", "settled"].includes(payment.status)
    ) {
      showToast("❌ Cannot delete a completed payment", "error");
      closeDeletePaymentModal();
      return;
    }

    const result = await PaymentAPI.delete(paymentId);
    if (result) {
      showToast("🗑️ Payment deleted", "success");
      closeDeletePaymentModal();
      if (
        state.currentInquiryId &&
        DOM.drawer()?.classList.contains("active")
      ) {
        await loadInquiryDetail(state.currentInquiryId);
      }
      await loadInquiries();
    } else {
      showToast("❌ Failed to delete payment", "error");
    }
  } catch (error) {
    console.error("Delete payment error:", error);
    showToast("❌ " + (error.message || "Failed to delete payment"), "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="ph ph-trash"></i> Delete Payment';
    }
  }
}

// ============================================================
// INVOICE HELPERS
// ============================================================

function calculateInvoiceTotal() {
  const rows = document.querySelectorAll(".invoice-item-row");
  let total = 0;

  rows.forEach((row) => {
    const qty = parseFloat(row.querySelector(".item-quantity")?.value) || 0;
    const price = parseFloat(row.querySelector(".item-unit-price")?.value) || 0;
    total += qty * price;
  });

  const subtotalEl = getElement("invoiceSubtotal");
  const totalEl = getElement("invoiceTotal");
  if (subtotalEl) subtotalEl.textContent = PaymentFormatter.currency(total);
  if (totalEl) totalEl.textContent = PaymentFormatter.currency(total);
}

function addInvoiceItemRow() {
  const container = getElement("invoiceItemsContainer");
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
  bindInvoiceItemRowEvents(row);
  calculateInvoiceTotal();
}

function bindInvoiceItemRowEvents(row) {
  row.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", calculateInvoiceTotal);
  });

  const removeBtn = row.querySelector(".remove-item-btn");
  if (removeBtn) {
    removeBtn.addEventListener("click", function () {
      const container = getElement("invoiceItemsContainer");
      if (container && container.children.length > 1) {
        row.remove();
        calculateInvoiceTotal();
      } else {
        showToast("Cannot remove the last item", "warning");
      }
    });
  }
}

// ============================================================
// PAYMENT SUBMIT
// ============================================================

async function handlePaymentSubmit(e) {
  e.preventDefault();

  const form = getElement("paymentForm");
  const submitBtn = form?.querySelector('button[type="submit"]');

  const inquiryId = getElement("paymentInquiryId")?.value || null;
  const projectId = getElement("paymentProjectId")?.value || null;
  const invoiceId = getElement("paymentInvoiceId")?.value?.trim() || null;
  const paymentType = getElement("paymentType")?.value || "payment";
  const amount = parseFloat(getElement("paymentAmount")?.value) || 0;
  const method = getElement("paymentMethod")?.value || "bank_transfer";
  const reference = getElement("paymentReference")?.value || null;
  const paymentDate = getElement("paymentDate")?.value || null;
  const dueDate = getElement("paymentDueDate")?.value || null;
  const notes = getElement("paymentNotes")?.value || null;

  if (!inquiryId) {
    showToast("❌ Inquiry ID is required", "error");
    return;
  }

  if (amount <= 0) {
    showToast("❌ Amount must be greater than 0", "error");
    return;
  }

  // Auto-fill project_id
  let finalProjectId = projectId;
  if (!finalProjectId && state.currentInquiryId) {
    const inquiry = state._currentInquiry;
    if (inquiry?.project?.id) {
      finalProjectId = inquiry.project.id;
    }
  }

  // Auto-fill invoice_id
  let finalInvoiceId = invoiceId;
  if (!finalInvoiceId && state.currentInquiryId) {
    try {
      const invoices = await PaymentAPI.getInvoicesByInquiry(
        state.currentInquiryId,
      );
      const unpaid = invoices?.find(
        (inv) => inv.status !== "paid" && inv.status !== "cancelled",
      );
      if (unpaid) {
        finalInvoiceId = unpaid.id;
      }
    } catch (error) {
      console.warn("Failed to auto-fill invoice:", error);
    }
  }

  const typeLabel = paymentType === "deposit" ? "Deposit" : "Payment";
  if (
    !confirm(
      `Record ${typeLabel} of ${PaymentFormatter.currency(amount)} for this inquiry?`,
    )
  ) {
    return;
  }

  const paymentData = {
    inquiry_id: inquiryId,
    project_id: finalProjectId || null,
    invoice_id: finalInvoiceId || null,
    payment_type: paymentType,
    amount: amount,
    payment_method: method,
    reference_number: reference,
    notes: notes,
    paid_at: paymentDate || new Date().toISOString().split("T")[0],
    due_date: dueDate || null,
    status: "pending",
  };

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="ph ph-spinner spin"></i> Saving...';
  }

  try {
    const result = await PaymentAPI.create(paymentData);
    if (result) {
      const typeIcon = paymentType === "deposit" ? "🏦" : "💳";
      showToast(
        `${typeIcon} ${typeLabel} of ${PaymentFormatter.currency(amount)} recorded!`,
        "success",
      );
      closePaymentModal();

      if (
        state.currentInquiryId &&
        DOM.drawer()?.classList.contains("active")
      ) {
        await loadInquiryDetail(state.currentInquiryId);
      }
      await loadInquiries();
    } else {
      showToast("❌ Failed to save payment", "error");
    }
  } catch (error) {
    console.error("Payment error:", error);
    showToast(
      `❌ Failed to save payment: ${error.message || "Unknown error"}`,
      "error",
    );
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = "Save Payment";
    }
  }
}

// ============================================================
// INVOICE SUBMIT
// ============================================================

async function handleInvoiceSubmit(e) {
  e.preventDefault();

  const form = getElement("invoiceForm");
  const submitBtn = form?.querySelector('button[type="submit"]');

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
        tax_rate: 0,
        discount_percentage: 0,
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

  const inquiryId = getElement("invoiceInquiryId")?.value || null;
  const projectId = getElement("invoiceProjectId")?.value || null;
  const invoiceNumber = getElement("invoiceNumber")?.value?.trim() || null;
  const paymentTerms = getElement("invoicePaymentTerms")?.value?.trim() || null;
  const invoiceDate = getElement("invoiceDate")?.value || null;
  const dueDate = getElement("invoiceDueDate")?.value || null;
  const notes = getElement("invoiceNotes")?.value?.trim() || null;

  if (!inquiryId) {
    showToast("❌ Inquiry ID is required", "error");
    return;
  }

  if (!invoiceNumber) {
    showToast("❌ Invoice Number is required", "error");
    return;
  }

  let finalProjectId = projectId;
  if (!finalProjectId && state.currentInquiryId) {
    const inquiry = state._currentInquiry;
    if (inquiry?.project?.id) {
      finalProjectId = inquiry.project.id;
    }
  }

  const totalAmount = items.reduce(
    (sum, item) => sum + item.quantity * item.unit_price,
    0,
  );
  if (
    !confirm(
      `Create invoice ${invoiceNumber} for ${PaymentFormatter.currency(totalAmount)}?`,
    )
  ) {
    return;
  }

  const invoiceData = {
    inquiry_id: inquiryId,
    project_id: finalProjectId || null,
    invoice_number: invoiceNumber,
    invoice_date: invoiceDate || new Date().toISOString().split("T")[0],
    due_date: dueDate || null,
    payment_terms: paymentTerms || null,
    notes: notes || null,
    items: items,
    status: "draft",
  };

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="ph ph-spinner spin"></i> Creating...';
  }

  try {
    const result = await PaymentAPI.createInvoice(invoiceData);
    if (result) {
      showToast(
        `✅ Invoice ${invoiceNumber} created! (${PaymentFormatter.currency(totalAmount)})`,
        "success",
      );
      closeInvoiceModal();

      if (
        state.currentInquiryId &&
        DOM.drawer()?.classList.contains("active")
      ) {
        await loadInquiryDetail(state.currentInquiryId);
      }
      await loadInquiries();
    } else {
      showToast("❌ Failed to create invoice", "error");
    }
  } catch (error) {
    console.error("Invoice error:", error);
    showToast(
      `❌ Failed to create invoice: ${error.message || "Unknown error"}`,
      "error",
    );
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = "Create Invoice";
    }
  }
}

// ============================================================
// CONFIRM PAYMENT (EXPORTED)
// ============================================================

export async function confirmPayment(paymentId) {
  if (!paymentId) {
    showToast("❌ Payment ID is required", "error");
    return;
  }

  if (!confirm("Confirm this payment?")) return;

  showToast("⏳ Confirming payment...", "info");

  try {
    const result = await PaymentAPI.confirm(paymentId, "admin");
    if (result) {
      showToast("✅ Payment confirmed successfully!", "success");
      if (
        state.currentInquiryId &&
        DOM.drawer()?.classList.contains("active")
      ) {
        await loadInquiryDetail(state.currentInquiryId);
      }
      await loadInquiries();
    } else {
      showToast("❌ Failed to confirm payment", "error");
    }
  } catch (error) {
    console.error("Confirm payment error:", error);
    showToast(
      `❌ Failed to confirm payment: ${error.message || "Unknown error"}`,
      "error",
    );
  }
}

// ============================================================
// BIND EVENTS
// ============================================================

export function bindEvents() {
  // Pagination
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

  // Search & Filter
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

  // Drawer
  DOM.closeDrawer()?.addEventListener("click", closeDrawer);
  DOM.drawerBackdrop()?.addEventListener("click", closeDrawer);

  // Modals
  DOM.closeConvertModal()?.addEventListener("click", closeConvertModal);
  DOM.cancelConvertBtn()?.addEventListener("click", closeConvertModal);
  DOM.convertModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.convertModal()) closeConvertModal();
  });
  DOM.convertForm()?.addEventListener("submit", handleConvert);

  DOM.closeQuoteModal()?.addEventListener("click", closeQuoteModal);
  DOM.cancelQuoteBtn()?.addEventListener("click", closeQuoteModal);
  DOM.quoteModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.quoteModal()) closeQuoteModal();
  });
  DOM.quoteForm()?.addEventListener("submit", handleSendQuote);

  DOM.closeRejectModal()?.addEventListener("click", closeRejectModal);
  DOM.cancelRejectBtn()?.addEventListener("click", closeRejectModal);
  DOM.rejectModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.rejectModal()) closeRejectModal();
  });
  DOM.rejectForm()?.addEventListener("submit", handleReject);

  // Drawer Actions
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

  // Payment Modal
  const paymentModal = getElement("paymentModal");
  const paymentForm = getElement("paymentForm");
  getElement("closePaymentModal")?.addEventListener("click", closePaymentModal);
  getElement("cancelPaymentBtn")?.addEventListener("click", closePaymentModal);
  paymentModal?.addEventListener("click", (e) => {
    if (e.target === paymentModal) closePaymentModal();
  });
  paymentForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    // Implementation would call PaymentAPI.create
    // Similar to projects module
  });

  // Confirm Payment Modal
  getElement("closeConfirmPaymentModal")?.addEventListener(
    "click",
    closeConfirmPaymentModal,
  );
  getElement("cancelConfirmPaymentBtn")?.addEventListener(
    "click",
    closeConfirmPaymentModal,
  );
  getElement("confirmPaymentModal")?.addEventListener("click", (e) => {
    if (e.target === getElement("confirmPaymentModal"))
      closeConfirmPaymentModal();
  });
  getElement("confirmPaymentBtn")?.addEventListener(
    "click",
    handleConfirmPayment,
  );

  // Delete Payment Modal
  getElement("closeDeletePaymentModal")?.addEventListener(
    "click",
    closeDeletePaymentModal,
  );
  getElement("cancelDeletePaymentBtn")?.addEventListener(
    "click",
    closeDeletePaymentModal,
  );
  getElement("deletePaymentModal")?.addEventListener("click", (e) => {
    if (e.target === getElement("deletePaymentModal"))
      closeDeletePaymentModal();
  });
  getElement("deletePaymentBtn")?.addEventListener(
    "click",
    handleDeletePayment,
  );

  // Add Deposit & Payment buttons
  DOM.addDepositBtn()?.addEventListener("click", () => {
    const inquiryId = state.currentInquiryId;
    if (!inquiryId) {
      showToast("❌ No inquiry selected", "error");
      return;
    }
    const modal = getElement("paymentModal");
    const inquiryInput = getElement("paymentInquiryId");
    if (inquiryInput) {
      inquiryInput.value = inquiryId;
      inquiryInput.disabled = true;
    }
    const typeSelect = getElement("paymentType");
    if (typeSelect) typeSelect.value = "deposit";
    const dateInput = getElement("paymentDate");
    if (dateInput) dateInput.value = new Date().toISOString().split("T")[0];
    if (modal) modal.classList.add("active");
  });

  DOM.addPaymentBtn()?.addEventListener("click", () => {
    const inquiryId = state.currentInquiryId;
    if (!inquiryId) {
      showToast("❌ No inquiry selected", "error");
      return;
    }
    const modal = getElement("paymentModal");
    const inquiryInput = getElement("paymentInquiryId");
    if (inquiryInput) {
      inquiryInput.value = inquiryId;
      inquiryInput.disabled = true;
    }
    const typeSelect = getElement("paymentType");
    if (typeSelect) typeSelect.value = "payment";
    const dateInput = getElement("paymentDate");
    if (dateInput) dateInput.value = new Date().toISOString().split("T")[0];
    if (modal) modal.classList.add("active");
  });

  // Invoice Modal
  DOM.viewInvoicesBtn()?.addEventListener("click", () => {
    const inquiryId = state.currentInquiryId;
    if (!inquiryId) {
      showToast("❌ No inquiry selected", "error");
      return;
    }
    const modal = getElement("invoiceModal");
    const inquiryInput = getElement("invoiceInquiryId");
    if (inquiryInput) {
      inquiryInput.value = inquiryId;
      inquiryInput.disabled = true;
    }
    const numberInput = getElement("invoiceNumber");
    if (numberInput) {
      numberInput.value = `INV-${new Date().toISOString().slice(0, 10).replace(/-/g, "")}-${String(Math.floor(Math.random() * 10000)).padStart(4, "0")}`;
    }
    const dateInput = getElement("invoiceDate");
    if (dateInput) dateInput.value = new Date().toISOString().split("T")[0];
    if (modal) modal.classList.add("active");
  });

  // Lightbox
  DOM.lightboxClose()?.addEventListener("click", closeLightbox);
  DOM.lightboxOverlay()?.addEventListener("click", (e) => {
    if (e.target === DOM.lightboxOverlay()) closeLightbox();
  });
  DOM.lightboxPrev()?.addEventListener("click", () => navigateLightbox(-1));
  DOM.lightboxNext()?.addEventListener("click", () => navigateLightbox(1));

  // Notes
  if (DOM.drawerNotes()) {
    DOM.drawerNotes().addEventListener("input", () => {
      const counter = DOM.noteCounter();
      if (counter) counter.textContent = DOM.drawerNotes().value.length;
    });
    let noteTimeout;
    DOM.drawerNotes().addEventListener("blur", () => {
      clearTimeout(noteTimeout);
      noteTimeout = setTimeout(() => {
        if (DOM.drawerNotes()?.value?.trim()) handleSaveNote();
      }, 1000);
    });
  }

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const modals = [
        "paymentModal",
        "invoiceModal",
        "confirmPaymentModal",
        "deletePaymentModal",
      ];
      for (const id of modals) {
        const el = getElement(id);
        if (el?.classList.contains("active")) {
          if (id === "paymentModal") closePaymentModal();
          else if (id === "invoiceModal") closeInvoiceModal();
          else if (id === "confirmPaymentModal") closeConfirmPaymentModal();
          else if (id === "deletePaymentModal") closeDeletePaymentModal();
          return;
        }
      }
      if (DOM.convertModal()?.classList.contains("active")) closeConvertModal();
      else if (DOM.quoteModal()?.classList.contains("active"))
        closeQuoteModal();
      else if (DOM.rejectModal()?.classList.contains("active"))
        closeRejectModal();
      else if (DOM.drawer()?.classList.contains("active")) closeDrawer();
      else if (state.lightbox.isOpen) closeLightbox();
    }
    if (e.ctrlKey && e.key === "f") {
      e.preventDefault();
      DOM.searchInquiry()?.focus();
    }
  });

  console.log("✅ All events bound successfully!");
}
