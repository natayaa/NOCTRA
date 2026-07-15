// ============================================================
// billing/handlers/modals.js - Modal Handlers
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { BillingAPI, InquiryAPI, PaymentAPI } from "../api.js";
import { showToast } from "../../shared/toast.js";
import { PaymentFormatter } from "../../shared/payments/formatters.js";
import { loadBillingData } from "../index.js";

// ============================================================
// INVOICE CREATE/EDIT MODAL
// ============================================================

export function openInvoiceModal(inquiryId = null, prefillData = null) {
  const modal = DOM.invoiceModal();
  const title = DOM.invoiceModalTitle();
  const subtitle = DOM.invoiceModalSubtitle();
  const form = DOM.invoiceForm();
  const editId = DOM.invoiceEditId();
  const submitBtn = DOM.saveInvoiceBtn();

  if (!modal) return;

  // Reset form
  if (form) form.reset();
  if (editId) editId.value = "";

  // Clear items
  const container = DOM.invoiceItemsContainer();
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
    bindInvoiceItemEvents(container);
  }

  // Generate invoice number
  generateInvoiceNumber();

  // Set date
  const dateInput = DOM.invoiceDate();
  if (dateInput) {
    dateInput.value = new Date().toISOString().split("T")[0];
  }

  // Pre-fill from inquiry if provided
  if (inquiryId) {
    const inquiryInput = DOM.invoiceInquiryId();
    if (inquiryInput) {
      inquiryInput.value = inquiryId;
      inquiryInput.disabled = true;
    }
    if (title) title.textContent = "Create Invoice from Quotation";
    if (subtitle)
      subtitle.textContent = `Converting quotation ${inquiryId.substring(0, 8)} to invoice`;
    loadInquiryItems(inquiryId);
  } else {
    const inquiryInput = DOM.invoiceInquiryId();
    if (inquiryInput) {
      inquiryInput.disabled = false;
      inquiryInput.value = "";
    }
    if (title) title.textContent = "Create Invoice";
    if (subtitle) subtitle.textContent = "Generate a new invoice";
  }

  if (submitBtn) submitBtn.textContent = "Create Invoice";

  modal.classList.add("active");
  document.body.style.overflow = "hidden";
}

export function closeInvoiceModal() {
  const modal = DOM.invoiceModal();
  if (modal) modal.classList.remove("active");
  document.body.style.overflow = "";
  const form = DOM.invoiceForm();
  if (form) form.reset();
}

async function generateInvoiceNumber() {
  const input = DOM.invoiceNumber();
  if (!input) return;
  try {
    const result = await BillingAPI.generateInvoiceNumber();
    if (result) {
      input.value = result.invoice_number || result.data?.invoice_number || "";
    }
  } catch (error) {
    console.warn("Failed to generate invoice number:", error);
  }
}

async function loadInquiryItems(inquiryId) {
  try {
    const inquiry = await InquiryAPI.fetchDetail(inquiryId);
    if (!inquiry) return;

    const container = DOM.invoiceItemsContainer();
    if (!container) return;
    container.innerHTML = "";

    // Add items from inquiry - use estimated cost as one item
    const cost = inquiry.estimated_cost || 0;
    const desc = inquiry.project_type || "Project";
    const customer = inquiry.customer_name || "Customer";

    addInvoiceItemRow(container, {
      description: `${desc} for ${customer}`,
      quantity: 1,
      unit: "project",
      unit_price: cost,
    });

    // If there are specific services
    if (inquiry.services) {
      const services = inquiry.services.split(",");
      services.forEach((service) => {
        const trimmed = service.trim();
        if (trimmed && trimmed.length > 0) {
          addInvoiceItemRow(container, {
            description: trimmed,
            quantity: 1,
            unit: "service",
            unit_price: 0,
          });
        }
      });
    }

    calculateInvoiceTotal();
  } catch (error) {
    console.error("Failed to load inquiry items:", error);
  }
}

export function addInvoiceItemRow(container, prefill = null) {
  const row = document.createElement("div");
  row.className = "invoice-item-row";
  row.innerHTML = `
    <input type="text" class="item-description" placeholder="Description *" value="${prefill?.description || ""}" />
    <input type="number" class="item-quantity" placeholder="Qty" value="${prefill?.quantity || 1}" min="1" />
    <input type="text" class="item-unit" placeholder="Unit" value="${prefill?.unit || ""}" />
    <input type="number" class="item-unit-price" placeholder="Unit Price *" step="1000" min="0" value="${prefill?.unit_price || ""}" />
    <button type="button" class="btn-danger btn-sm remove-item-btn" title="Remove item">&times;</button>
  `;

  container.appendChild(row);
  bindInvoiceItemRowEvents(row);
  calculateInvoiceTotal();
}

function bindInvoiceItemEvents(container) {
  container.querySelectorAll(".remove-item-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      const row = this.closest(".invoice-item-row");
      if (row && container.children.length > 1) {
        row.remove();
        calculateInvoiceTotal();
      } else {
        showToast("Cannot remove the last item", "warning");
      }
    });
  });
  container.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", calculateInvoiceTotal);
  });
}

function bindInvoiceItemRowEvents(row) {
  row.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", calculateInvoiceTotal);
  });
  const removeBtn = row.querySelector(".remove-item-btn");
  if (removeBtn) {
    removeBtn.addEventListener("click", function () {
      const container = DOM.invoiceItemsContainer();
      if (container && container.children.length > 1) {
        row.remove();
        calculateInvoiceTotal();
      } else {
        showToast("Cannot remove the last item", "warning");
      }
    });
  }
}

export function calculateInvoiceTotal() {
  const rows = document.querySelectorAll(".invoice-item-row");
  let total = 0;

  rows.forEach((row) => {
    const qty = parseFloat(row.querySelector(".item-quantity")?.value) || 0;
    const price = parseFloat(row.querySelector(".item-unit-price")?.value) || 0;
    total += qty * price;
  });

  const subtotalEl = DOM.invoiceSubtotal();
  const totalEl = DOM.invoiceTotal();
  if (subtotalEl) subtotalEl.textContent = PaymentFormatter.currency(total);
  if (totalEl) totalEl.textContent = PaymentFormatter.currency(total);
}

// ============================================================
// INVOICE DETAIL MODAL
// ============================================================

export async function openInvoiceDetailModal(invoiceId) {
  const modal = DOM.invoiceDetailModal();
  if (!modal) return;

  // Show loading
  const itemsBody = DOM.detailItemsBody();
  if (itemsBody)
    itemsBody.innerHTML = `<tr><td colspan="5" class="loading-placeholder">Loading...</td></tr>`;

  modal.classList.add("active");
  document.body.style.overflow = "hidden";

  try {
    const invoice = await PaymentAPI.getInvoice(invoiceId);
    if (!invoice) {
      showToast("Failed to load invoice details", "error");
      return;
    }

    state.currentInvoiceId = invoiceId;

    // Header
    const numberEl = DOM.detailInvoiceNumber();
    if (numberEl)
      numberEl.textContent = `Invoice #${invoice.invoice_number || "N/A"}`;

    const statusEl = DOM.detailInvoiceStatus();
    if (statusEl) {
      const status = invoice.status || "draft";
      statusEl.innerHTML = `<span class="status-badge ${status}">${PaymentFormatter.invoiceStatusLabel(status)}</span>`;
    }

    // Details
    const fields = {
      detailCustomer:
        invoice.customer_name || invoice.inquiry?.customer_name || "-",
      detailInquiryId: invoice.inquiry_id || "-",
      detailInvoiceDate: PaymentFormatter.date(invoice.invoice_date),
      detailDueDate: PaymentFormatter.date(invoice.due_date),
      detailPaymentTerms: invoice.payment_terms || "-",
    };
    Object.keys(fields).forEach((key) => {
      const el = DOM[key]();
      if (el) el.textContent = fields[key];
    });

    // Items
    const items = invoice.items || [];
    if (itemsBody) {
      if (items.length === 0) {
        itemsBody.innerHTML = `<tr><td colspan="5" class="no-data">No items</td></tr>`;
      } else {
        itemsBody.innerHTML = items
          .map(
            (item) => `
            <tr>
              <td>${escapeHtml(item.description || "-")}</td>
              <td>${item.quantity || 0}</td>
              <td>${escapeHtml(item.unit || "-")}</td>
              <td>${PaymentFormatter.currency(item.unit_price || 0)}</td>
              <td><strong>${PaymentFormatter.currency((item.quantity || 0) * (item.unit_price || 0))}</strong></td>
            </tr>
          `,
          )
          .join("");
      }
    }

    // Grand total
    const totalEl = DOM.detailGrandTotal();
    if (totalEl)
      totalEl.textContent = PaymentFormatter.currency(
        invoice.total_amount || 0,
      );

    // Notes
    const notesEl = DOM.detailNotes();
    if (notesEl) notesEl.textContent = invoice.notes || "-";

    // Update action buttons based on status
    const status = invoice.status || "draft";
    const sendBtn = DOM.detailSendBtn();
    const markPaidBtn = DOM.detailMarkPaidBtn();

    if (sendBtn)
      sendBtn.style.display =
        status === "draft" || status === "sent" ? "inline-flex" : "none";
    if (markPaidBtn)
      markPaidBtn.style.display =
        status === "sent" || status === "partial" ? "inline-flex" : "none";

    // Store invoice data for actions
    modal._invoiceData = invoice;
  } catch (error) {
    console.error("Failed to load invoice detail:", error);
    showToast("Failed to load invoice details", "error");
  }
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

export function closeInvoiceDetailModal() {
  const modal = DOM.invoiceDetailModal();
  if (modal) modal.classList.remove("active");
  document.body.style.overflow = "";
  state.currentInvoiceId = null;
}

// ============================================================
// CONFIRM ACTION MODAL
// ============================================================

export function openConfirmActionModal(title, message, action) {
  const modal = DOM.confirmActionModal();
  const titleEl = DOM.confirmActionTitle();
  const messageEl = DOM.confirmActionMessage();

  if (!modal) return;

  if (titleEl) titleEl.textContent = title;
  if (messageEl) messageEl.textContent = message;

  state.pendingAction = action;

  modal.classList.add("active");
}

export function closeConfirmActionModal() {
  const modal = DOM.confirmActionModal();
  if (modal) modal.classList.remove("active");
  state.pendingAction = null;
}
