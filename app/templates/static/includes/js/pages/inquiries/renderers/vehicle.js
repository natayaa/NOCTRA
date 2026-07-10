// inquiries/renderers/vehicle.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { Formatter } from "../formatters.js";

export function renderDrawerVehicle(inquiry) {
  if (!inquiry) return;

  const fields = {
    drawerBrand: inquiry.vehicle_brand,
    drawerModel: inquiry.vehicle_model,
    drawerYear: inquiry.vehicle_year,
    drawerPlate: inquiry.vehicle_license_plate,
    drawerPrevRepaint: inquiry.previous_repaint,
    drawerBikeModified: inquiry.bike_modified,
    drawerCondition: inquiry.vehicle_condition,
    drawerType: inquiry.project_type,
    drawerServices: inquiry.services,
    drawerFinish: inquiry.desired_finish,
    drawerColor: inquiry.desired_color,
    drawerBudget: inquiry.estimated_budget,
    drawerDeadline: inquiry.deadline,
    drawerPriority: inquiry.priority,
  };

  Object.keys(fields).forEach((key) => {
    const el = DOM[key]();
    if (el) {
      const value = fields[key];
      if (key === "drawerBudget" && value) {
        el.textContent = Formatter.currency(value);
      } else {
        el.textContent = value || "-";
      }
    }
  });

  const desc = DOM.drawerDescription();
  if (desc) {
    desc.textContent =
      inquiry.project_description || "No description provided.";
  }

  const ref = DOM.drawerReference();
  if (ref) {
    if (inquiry.reference_link) {
      ref.href = inquiry.reference_link;
      ref.style.display = "inline-flex";
      ref.textContent = "🔗 View Reference Link";
      ref.target = "_blank";
    } else {
      ref.style.display = "none";
    }
  }

  // ✅ Render vehicle info summary card
  const summaryEl = document.getElementById("drawerVehicleSummary");
  if (summaryEl) {
    const brand = inquiry.vehicle_brand || "-";
    const model = inquiry.vehicle_model || "-";
    const year = inquiry.vehicle_year || "-";
    const plate = inquiry.vehicle_license_plate || "-";

    summaryEl.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;padding:0.5rem 0;">
        <div><span style="color:var(--text-muted);font-size:0.7rem;">Brand</span><br><strong>${escapeHtml(brand)}</strong></div>
        <div><span style="color:var(--text-muted);font-size:0.7rem;">Model</span><br><strong>${escapeHtml(model)}</strong></div>
        <div><span style="color:var(--text-muted);font-size:0.7rem;">Year</span><br><strong>${escapeHtml(year)}</strong></div>
        <div><span style="color:var(--text-muted);font-size:0.7rem;">Plate</span><br><strong>${escapeHtml(plate)}</strong></div>
      </div>
    `;
  }
}

export function renderVehicleSummary(inquiry) {
  if (!inquiry) return;
  const el = document.getElementById("drawerVehicleSummary");
  if (!el) return;

  el.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;padding:0.5rem 0;">
      <div><span style="color:var(--text-muted);font-size:0.7rem;">Brand</span><br><strong>${escapeHtml(inquiry.vehicle_brand || "-")}</strong></div>
      <div><span style="color:var(--text-muted);font-size:0.7rem;">Model</span><br><strong>${escapeHtml(inquiry.vehicle_model || "-")}</strong></div>
      <div><span style="color:var(--text-muted);font-size:0.7rem;">Year</span><br><strong>${escapeHtml(inquiry.vehicle_year || "-")}</strong></div>
      <div><span style="color:var(--text-muted);font-size:0.7rem;">Plate</span><br><strong>${escapeHtml(inquiry.vehicle_license_plate || "-")}</strong></div>
      ${
        inquiry.project_type
          ? `
        <div style="grid-column:span 2;">
          <span style="color:var(--text-muted);font-size:0.7rem;">Project Type</span>
          <br><strong>${escapeHtml(inquiry.project_type)}</strong>
        </div>
      `
          : ""
      }
    </div>
  `;
}
