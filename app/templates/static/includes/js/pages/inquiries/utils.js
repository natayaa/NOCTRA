// ============================================================
// inquiries/utils.js - Utility Functions
// ============================================================

import { state } from "./config.js";

export function getItemName(itemId) {
  if (!itemId) return "Unknown";
  if (state.inventoryItems && state.inventoryItems.length > 0) {
    const found = state.inventoryItems.find((i) => i.id === itemId);
    if (found) return found.name;
  }
  return `Item ${itemId.substring(0, 8)}`;
}

export function getItemUnit(itemId) {
  if (!itemId) return "";
  if (state.inventoryItems && state.inventoryItems.length > 0) {
    const found = state.inventoryItems.find((i) => i.id === itemId);
    if (found) return found.unit || "";
  }
  return "";
}

export function getItemCost(itemId) {
  if (!itemId) return 0;
  if (state.inventoryItems && state.inventoryItems.length > 0) {
    const found = state.inventoryItems.find((i) => i.id === itemId);
    if (found) return found.cost_price || 0;
  }
  return 0;
}

export function calculateFinancialFromData(
  inquiry,
  labor,
  materials,
  payments,
) {
  // Calculate total labor cost
  const totalLaborCost = labor.reduce((sum, item) => {
    return sum + (Number(item.hours) || 0) * (Number(item.rate_per_hour) || 0);
  }, 0);

  // Calculate total material cost
  const totalMaterialCost = materials.reduce((sum, item) => {
    const qty = Number(item.quantity) || 0;
    const price = Number(item.cost_price) || Number(item.unit_price) || 0;
    return sum + qty * price;
  }, 0);

  // Calculate total payments
  const totalDeposit = payments
    .filter((p) => p.type === "deposit" || p.payment_type === "deposit")
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalPaid = payments
    .filter(
      (p) =>
        p.status === "completed" ||
        p.status === "confirmed" ||
        p.status === "paid",
    )
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalPending = payments
    .filter(
      (p) => p.status === "pending" || p.status === "awaiting_confirmation",
    )
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  // Get project financials from inquiry if available
  const project = inquiry?.project || {};
  const estimatedCost = Number(project.estimated_cost) || 0;
  const estimatedRevenue = Number(project.estimated_revenue) || 0;
  const depositAmount = Number(project.deposit_amount) || totalDeposit || 0;
  const depositPaid = project.deposit_paid || depositAmount > 0;

  return {
    estimated_cost: estimatedCost,
    actual_cost: totalLaborCost + totalMaterialCost,
    estimated_revenue: estimatedRevenue,
    actual_revenue: totalPaid || 0,
    deposit_amount: depositAmount,
    deposit_paid: depositPaid,
    material_cost: totalMaterialCost,
    labor_cost: totalLaborCost,
    other_expenses: 0,
    total_paid: totalPaid,
    total_deposit: totalDeposit,
    total_pending: totalPending,
  };
}
