// ============================================================
// inquiries/renderers/vehicle.js - Vehicle Rendering
// ============================================================

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
    drawerBudget: inquiry.estimated_budget
      ? Formatter.currency(inquiry.estimated_budget)
      : "-",
    drawerDeadline: inquiry.deadline,
    drawerPriority: inquiry.priority,
  };

  Object.keys(fields).forEach((key) => {
    const el = DOM[key]();
    if (el) el.textContent = fields[key] || "-";
  });

  const desc = DOM.drawerDescription();
  if (desc)
    desc.textContent =
      inquiry.project_description || "No description provided.";

  const ref = DOM.drawerReference();
  if (ref) {
    if (inquiry.reference_link) {
      ref.href = inquiry.reference_link;
      ref.style.display = "inline";
      ref.textContent = "🔗 View Reference Link";
    } else {
      ref.style.display = "none";
    }
  }
}
