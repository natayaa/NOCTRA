// ============================================================
// restored-bikes/renderers/detail.js - Detail Rendering
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";

const formatter = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export function renderDetail(bike) {
  if (!bike) return;

  // Title
  const title = DOM.drawerTitle();
  const subtitle = DOM.drawerSubtitle();
  if (title)
    title.textContent = `${bike.brand || "Unknown"} ${bike.model || ""}`;
  if (subtitle)
    subtitle.textContent = `Restored by NOCTRA${bike.technician_name ? ` | Lead: ${bike.technician_name}` : ""}`;

  // Vehicle Info
  const fields = {
    detailBrand: bike.brand,
    detailModel: bike.model,
    detailYear: bike.year,
    detailPlate: bike.license_plate,
    detailCustomer: bike.customer_name,
    detailPurchasePrice: bike.purchase_price
      ? formatter.format(bike.purchase_price)
      : "-",
    detailPurchaseSource: bike.purchase_source,
    detailInitialCondition: bike.initial_condition,
    detailRestorationCost: bike.restoration_cost
      ? formatter.format(bike.restoration_cost)
      : "-",
    detailRestorationDuration: bike.restoration_duration
      ? `${bike.restoration_duration} days`
      : "-",
    detailTechnician: bike.technician_name,
    detailNotes: bike.restoration_notes || "-",
  };

  Object.keys(fields).forEach((key) => {
    const el = DOM[key]();
    if (el)
      el.textContent =
        fields[key] !== undefined && fields[key] !== null ? fields[key] : "-";
  });

  // Status
  const statusEl = DOM.detailStatus();
  if (statusEl) {
    const status = bike.status || "completed";
    const label =
      status === "in_progress"
        ? "In Progress"
        : status.charAt(0).toUpperCase() + status.slice(1);
    statusEl.innerHTML = `<span class="status-badge ${status}">${label}</span>`;
  }

  // Store current bike ID
  state.currentBikeId = bike.id;
}

export function clearDetail() {
  const fields = [
    "detailBrand",
    "detailModel",
    "detailYear",
    "detailPlate",
    "detailCustomer",
    "detailPurchasePrice",
    "detailPurchaseSource",
    "detailInitialCondition",
    "detailRestorationCost",
    "detailRestorationDuration",
    "detailTechnician",
    "detailNotes",
  ];
  fields.forEach((key) => {
    const el = DOM[key]();
    if (el) el.textContent = "-";
  });
  const statusEl = DOM.detailStatus();
  if (statusEl) statusEl.innerHTML = `<span class="status-badge">-</span>`;
}
