// static/js/pages/settings/renderers/payment-methods.js

import { escapeHtml } from "../../../shared/utils.js";

export function renderPaymentMethods(methods) {
  const container = document.getElementById("paymentMethodList");
  if (!container) return;

  if (!methods || methods.length === 0) {
    container.innerHTML = `
      <div class="empty-state-sm">
        <p>No payment methods defined. Click "Add Payment Method" to create one.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = methods
    .map(
      (method) => `
      <div class="payment-method-item" data-id="${method.id}">
        <div class="item-info">
          ${method.icon ? `<span>${escapeHtml(method.icon)}</span>` : ""}
          <span style="font-weight:500;">${escapeHtml(method.name)}</span>
          <span style="color:var(--text-muted);font-size:0.7rem;">${escapeHtml(method.code)}</span>
          ${
            !method.is_active
              ? `<span class="badge-inactive" style="font-size:0.6rem;padding:0.1rem 0.4rem;border-radius:var(--radius-full);background:rgba(239,68,68,0.12);color:#ef4444;">Inactive</span>`
              : ""
          }
        </div>
        <div class="item-actions">
          <button class="btn-edit" data-id="${method.id}" title="Edit"><i class="ph ph-pencil"></i></button>
          <button class="btn-delete" data-id="${method.id}" title="Delete"><i class="ph ph-trash"></i></button>
        </div>
      </div>
    `,
    )
    .join("");

  // Bind events for edit/delete
  container.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const item = methods.find((m) => m.id === id);
      if (item) {
        const modal = document.getElementById("paymentMethodModal");
        const idInput = document.getElementById("editPaymentMethodId");
        const nameInput = document.getElementById("paymentMethodName");
        const codeInput = document.getElementById("paymentMethodCode");
        const iconInput = document.getElementById("paymentMethodIcon");
        if (idInput) idInput.value = item.id;
        if (nameInput) nameInput.value = item.name || "";
        if (codeInput) codeInput.value = item.code || "";
        if (iconInput) iconInput.value = item.icon || "";
        if (modal) modal.classList.add("active");
      }
    });
  });

  container.querySelectorAll(".btn-delete").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const item = methods.find((m) => m.id === id);
      if (item && confirm(`Delete payment method "${item.name}"?`)) {
        window.deletePaymentMethod(id);
      }
    });
  });
}
