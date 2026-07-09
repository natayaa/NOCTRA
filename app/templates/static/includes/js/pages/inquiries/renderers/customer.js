// ============================================================
// inquiries/renderers/customer.js - Customer Rendering
// ============================================================

import { DOM } from "../dom.js";
import { Formatter } from "../formatters.js";

export function renderDrawerCustomer(inquiry) {
  if (!inquiry) return;
  const name = DOM.drawerCustomerName();
  const badge = DOM.drawerStatusBadge();

  if (name) name.textContent = inquiry.customer_name || "Unknown";
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
    if (el) el.textContent = fields[key] || "-";
  });
}
