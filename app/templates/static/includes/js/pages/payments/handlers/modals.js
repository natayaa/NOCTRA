// ============================================================
// payments/handlers/modals.js - Payment Modal Functions
// ============================================================

import { PaymentAPI } from "../../shared/payments/api.js";
import { showToast } from "../../inquiries/toast.js";
import { loadInquiries } from "../../inquiries/index.js";

export function openPaymentModal() {
  const modal = document.getElementById("paymentModal");
  if (modal) {
    modal.style.display = "flex";
    modal.classList.add("active");
  }
  document.body.style.overflow = "hidden";
}

export function closePaymentModal() {
  const modal = document.getElementById("paymentModal");
  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("active");
  }
  document.body.style.overflow = "";
}

export function openInvoiceModal() {
  const modal = document.getElementById("invoiceModal");
  if (modal) {
    modal.style.display = "flex";
    modal.classList.add("active");
  }
  document.body.style.overflow = "hidden";
}

export function closeInvoiceModal() {
  const modal = document.getElementById("invoiceModal");
  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("active");
  }
  document.body.style.overflow = "";
}

export async function handlePaymentSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const formData = new FormData(form);

  const paymentData = {
    inquiry_id: formData.get("inquiry_id"),
    payment_type: formData.get("payment_type") || "payment",
    amount: parseFloat(formData.get("amount")),
    payment_method: formData.get("payment_method"),
    reference_number: formData.get("reference_number") || "",
    notes: formData.get("notes") || "",
    paid_at: formData.get("paid_at") || new Date().toISOString(),
  };

  if (
    !paymentData.inquiry_id ||
    !paymentData.amount ||
    !paymentData.payment_method
  ) {
    showToast("Please fill all required fields", "error");
    return;
  }

  try {
    let result;
    if (paymentData.payment_type === "deposit") {
      result = await PaymentAPI.createDeposit(paymentData);
    } else {
      result = await PaymentAPI.create(paymentData);
    }

    if (result) {
      showToast(
        `Payment ${paymentData.payment_type} created successfully!`,
        "success",
      );
      closePaymentModal();
      await loadInquiries();
    }
  } catch (error) {
    showToast("Failed to create payment: " + error.message, "error");
  }
}

export async function handleInvoiceSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const formData = new FormData(form);

  const invoiceData = {
    inquiry_id: formData.get("inquiry_id"),
    invoice_number: formData.get("invoice_number"),
    invoice_date: formData.get("invoice_date") || new Date().toISOString(),
    due_date: formData.get("due_date") || "",
    payment_terms: formData.get("payment_terms") || "",
    notes: formData.get("notes") || "",
    items: JSON.parse(formData.get("items") || "[]"),
  };

  if (
    !invoiceData.inquiry_id ||
    !invoiceData.invoice_number ||
    !invoiceData.items.length
  ) {
    showToast("Please fill all required fields", "error");
    return;
  }

  try {
    const result = await PaymentAPI.createInvoice(invoiceData);
    if (result) {
      showToast("Invoice created successfully!", "success");
      closeInvoiceModal();
      await loadInquiries();
    }
  } catch (error) {
    showToast("Failed to create invoice: " + error.message, "error");
  }
}
