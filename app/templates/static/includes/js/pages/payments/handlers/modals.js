// ============================================================
// payments/handlers/modals.js - Modal Functions (FIXED)
// ============================================================

import { PaymentAPI } from "../../shared/payments/api.js";
import { showToast } from "../toast.js";
import { loadPayments } from "../index.js";
import { DOM } from "../dom.js";

// ============================================================
// PAYMENT MODAL
// ============================================================
export function openPaymentModal(inquiryId = null, projectId = null) {
  const modal = DOM.paymentModal();
  const form = DOM.paymentForm();
  if (!modal || !form) return;

  // Reset form
  form.reset();

  // Set default values
  const inquiryInput = DOM.paymentInquiryId();
  const projectInput = DOM.paymentProjectId();
  const typeSelect = DOM.paymentType();
  const dateInput = DOM.paymentDate();

  if (inquiryInput) {
    inquiryInput.value = inquiryId || "";
    inquiryInput.disabled = !!inquiryId;
  }
  if (projectInput) {
    projectInput.value = projectId || "";
    projectInput.disabled = !!projectId;
  }
  if (typeSelect) typeSelect.value = "payment";
  if (dateInput) {
    dateInput.value = new Date().toISOString().split("T")[0];
  }

  modal.classList.add("active");
  document.body.style.overflow = "hidden";
}

export function closePaymentModal() {
  const modal = DOM.paymentModal();
  if (modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

export async function handlePaymentSubmit(e) {
  e.preventDefault();

  const form = DOM.paymentForm();
  if (!form) return;

  const formData = new FormData(form);

  const paymentData = {
    inquiry_id: formData.get("inquiry_id") || null,
    project_id: formData.get("project_id") || null,
    payment_type: formData.get("payment_type") || "payment",
    amount: parseFloat(formData.get("amount")) || 0,
    payment_method: formData.get("payment_method") || "bank_transfer",
    reference_number: formData.get("reference_number") || null,
    notes: formData.get("notes") || null,
    paid_at: formData.get("paid_at") || new Date().toISOString(),
    due_date: formData.get("due_date") || null,
  };

  if (!paymentData.inquiry_id && !paymentData.project_id) {
    showToast("Please provide either Inquiry ID or Project ID", "error");
    return;
  }

  if (!paymentData.amount || paymentData.amount <= 0) {
    showToast("Please enter a valid amount", "error");
    return;
  }

  if (!paymentData.payment_method) {
    showToast("Please select a payment method", "error");
    return;
  }

  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Saving...";
  }

  try {
    let result;
    if (paymentData.payment_type === "deposit") {
      result = await PaymentAPI.createDeposit(paymentData);
    } else {
      result = await PaymentAPI.create(paymentData);
    }

    if (result) {
      const typeLabel =
        paymentData.payment_type === "deposit" ? "Deposit" : "Payment";
      showToast(`✅ ${typeLabel} created successfully!`, "success");
      closePaymentModal();
      await loadPayments();
    } else {
      showToast("❌ Failed to create payment", "error");
    }
  } catch (error) {
    console.error("Payment error:", error);
    showToast("❌ " + (error.message || "Failed to create payment"), "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Save Payment";
    }
  }
}

// ============================================================
// INVOICE MODAL
// ============================================================
export function openInvoiceModal(inquiryId = null, projectId = null) {
  const modal = DOM.invoiceModal();
  const form = DOM.invoiceForm();
  if (!modal || !form) return;

  form.reset();

  const inquiryInput = DOM.invoiceInquiryId();
  const projectInput = DOM.invoiceProjectId();
  const numberInput = DOM.invoiceNumber();
  const dateInput = DOM.invoiceDate();
  const dueDateInput = DOM.invoiceDueDate();
  const container = DOM.invoiceItemsContainer();

  if (inquiryInput) {
    inquiryInput.value = inquiryId || "";
    inquiryInput.disabled = !!inquiryId;
  }
  if (projectInput) {
    projectInput.value = projectId || "";
    projectInput.disabled = !!projectId;
  }

  // Generate invoice number if available
  if (numberInput) {
    PaymentAPI.generateInvoiceNumber()
      .then((result) => {
        if (result?.invoice_number) {
          numberInput.value = result.invoice_number;
        } else {
          numberInput.value = `INV-${new Date().toISOString().slice(0, 10).replace(/-/g, "")}-${String(Math.floor(Math.random() * 10000)).padStart(4, "0")}`;
        }
      })
      .catch(() => {
        numberInput.value = `INV-${new Date().toISOString().slice(0, 10).replace(/-/g, "")}-${String(Math.floor(Math.random() * 10000)).padStart(4, "0")}`;
      });
  }

  if (dateInput) {
    dateInput.value = new Date().toISOString().split("T")[0];
  }
  if (dueDateInput) {
    const due = new Date();
    due.setDate(due.getDate() + 14);
    dueDateInput.value = due.toISOString().split("T")[0];
  }

  // Reset items
  if (container) {
    container.innerHTML = `
      <div class="invoice-item-row" style="display:grid;grid-template-columns:2fr 80px 80px 120px 40px;gap:8px;align-items:center;margin-bottom:8px;">
        <input type="text" class="item-description" placeholder="Description *" style="padding:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-input);color:var(--text-primary);width:100%;" />
        <input type="number" class="item-quantity" placeholder="Qty" value="1" min="1" style="padding:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-input);color:var(--text-primary);width:100%;" />
        <input type="text" class="item-unit" placeholder="Unit" style="padding:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-input);color:var(--text-primary);width:100%;" />
        <input type="number" class="item-unit-price" placeholder="Price *" step="1000" min="0" style="padding:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-input);color:var(--text-primary);width:100%;" />
        <button type="button" class="btn-danger btn-sm remove-item-btn" style="padding:4px 8px;background:#ef4444;color:white;border:none;border-radius:var(--radius-sm);cursor:pointer;font-size:1.2rem;opacity:0.5;">&times;</button>
      </div>
    `;
    bindInvoiceItemEvents();
  }

  const subtotalEl = DOM.invoiceSubtotal();
  const totalEl = DOM.invoiceTotal();
  if (subtotalEl) subtotalEl.textContent = "Rp 0";
  if (totalEl) totalEl.textContent = "Rp 0";

  modal.classList.add("active");
  document.body.style.overflow = "hidden";
}

export function closeInvoiceModal() {
  const modal = DOM.invoiceModal();
  if (modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

export function bindInvoiceItemEvents() {
  const container = DOM.invoiceItemsContainer();
  if (!container) return;

  // Remove item
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

  // Input changes
  container.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", calculateInvoiceTotal);
  });

  // Add new row via button (will be handled by events.js)
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
  if (subtotalEl)
    subtotalEl.textContent = `Rp ${total.toLocaleString("id-ID")}`;
  if (totalEl) totalEl.textContent = `Rp ${total.toLocaleString("id-ID")}`;
}

export async function handleInvoiceSubmit(e) {
  e.preventDefault();

  const form = DOM.invoiceForm();
  if (!form) return;

  const formData = new FormData(form);

  const items = [];
  const itemRows = document.querySelectorAll(".invoice-item-row");

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
    }
  });

  if (items.length === 0) {
    showToast("Please add at least one valid invoice item", "error");
    return;
  }

  const invoiceData = {
    inquiry_id: formData.get("inquiry_id") || null,
    project_id: formData.get("project_id") || null,
    invoice_number: formData.get("invoice_number")?.trim(),
    payment_terms: formData.get("payment_terms")?.trim() || null,
    invoice_date:
      formData.get("invoice_date") || new Date().toISOString().split("T")[0],
    due_date: formData.get("due_date") || null,
    notes: formData.get("notes")?.trim() || null,
    items: items,
    status: "draft",
  };

  if (!invoiceData.invoice_number) {
    showToast("Invoice number is required", "error");
    return;
  }

  if (!invoiceData.inquiry_id && !invoiceData.project_id) {
    showToast("Please provide either Inquiry ID or Project ID", "error");
    return;
  }

  const totalAmount = items.reduce(
    (sum, item) => sum + item.quantity * item.unit_price,
    0,
  );

  if (
    !confirm(
      `Create invoice ${invoiceData.invoice_number} for ${new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR" }).format(totalAmount)}?`,
    )
  ) {
    return;
  }

  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Creating...";
  }

  try {
    const result = await PaymentAPI.createInvoice(invoiceData);
    if (result) {
      showToast(`✅ Invoice ${invoiceData.invoice_number} created!`, "success");
      closeInvoiceModal();
      await loadPayments();
    } else {
      showToast("❌ Failed to create invoice", "error");
    }
  } catch (error) {
    console.error("Invoice error:", error);
    showToast("❌ " + (error.message || "Failed to create invoice"), "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Create Invoice";
    }
  }
}

// ============================================================
// ADD INVOICE ITEM ROW
// ============================================================
export function addInvoiceItemRow() {
  const container = DOM.invoiceItemsContainer();
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
  bindInvoiceItemEvents();
  calculateInvoiceTotal();
}

// Expose to window for inline onclick
window.addInvoiceItemRow = addInvoiceItemRow;
window.calculateInvoiceTotal = calculateInvoiceTotal;
