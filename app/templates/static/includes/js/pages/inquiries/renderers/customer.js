// inquiries/renderers/customer.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { Formatter } from "../formatters.js";

export function renderDrawerCustomer(inquiry) {
  if (!inquiry) return;

  const name = DOM.drawerCustomerName();
  const badge = DOM.drawerStatusBadge();

  if (name) name.textContent = inquiry.customer_name || "Unknown Customer";
  if (badge) {
    badge.textContent = Formatter.statusLabel(inquiry.status);
    badge.className = `status-badge ${Formatter.statusBadge(inquiry.status)}`;
  }

  const fields = {
    drawerName: inquiry.customer_name,
    drawerPhone: inquiry.customer_phone_number,
    drawerEmail: inquiry.customer_email,
    drawerProvince: inquiry.province,
    drawerCity: inquiry.city,
  };

  Object.keys(fields).forEach((key) => {
    const el = DOM[key]();
    if (el) {
      const value = fields[key];
      if (key === "drawerPhone" && value) {
        // Format phone number
        const cleaned = value.replace(/\D/g, "");
        if (cleaned.length === 11) {
          el.textContent = `${cleaned.substring(0, 4)}-${cleaned.substring(4, 8)}-${cleaned.substring(8)}`;
        } else if (cleaned.length === 12) {
          el.textContent = `${cleaned.substring(0, 4)}-${cleaned.substring(4, 8)}-${cleaned.substring(8)}`;
        } else {
          el.textContent = value || "-";
        }
      } else {
        el.textContent = value || "-";
      }
    }
  });

  // ✅ Customer summary card
  const summaryEl = document.getElementById("drawerCustomerSummary");
  if (summaryEl) {
    const phone = inquiry.customer_phone_number || "-";
    const email = inquiry.customer_email || "-";
    const location =
      [inquiry.city, inquiry.province].filter(Boolean).join(", ") || "-";

    summaryEl.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;padding:0.5rem 0;">
        <div><span style="color:var(--text-muted);font-size:0.7rem;">Phone</span><br><strong>${escapeHtml(phone)}</strong></div>
        <div><span style="color:var(--text-muted);font-size:0.7rem;">Email</span><br><strong>${escapeHtml(email)}</strong></div>
        <div style="grid-column:span 2;"><span style="color:var(--text-muted);font-size:0.7rem;">Location</span><br><strong>${escapeHtml(location)}</strong></div>
      </div>
    `;
  }
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
