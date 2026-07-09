// ============================================================
// inquiries/utils.js - Utility Functions
// ============================================================

// inquiries/utils.js

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
    if (found) return found.cost_price || found.selling_price || 0;
  }
  return 0;
}

/**
 * ✅ FIX: Calculate financial data from inquiry, labor, materials, and payments
 */
export function calculateFinancialFromData(
  inquiry,
  labor,
  materials,
  payments,
) {
  console.log("📊 Calculating financial from:", {
    inquiry,
    labor,
    materials,
    payments,
  });

  // ✅ Ambil data dari inquiry
  const project = inquiry?.project || {};

  // ✅ Estimated Cost - dari project atau inquiry
  const estimatedCost =
    Number(project.estimated_cost) || Number(inquiry.estimated_cost) || 0;
  const estimatedRevenue =
    Number(project.estimated_revenue) || Number(inquiry.estimated_revenue) || 0;

  // ✅ Deposit
  const depositAmount =
    Number(project.deposit_amount) || Number(inquiry.deposit_amount) || 0;
  const depositPaid = project.deposit_paid || inquiry.deposit_paid || false;

  // ✅ Labor Cost - hitung dari labor items
  const totalLaborCost = (labor || []).reduce((sum, item) => {
    const hours = Number(item.hours) || 0;
    const rate = Number(item.rate_per_hour) || Number(item.rate) || 0;
    return sum + hours * rate;
  }, 0);

  console.log("💰 Labor Cost calculated:", totalLaborCost);

  // ✅ Material Cost - hitung dari material usages
  const totalMaterialCost = (materials || []).reduce((sum, item) => {
    const qty = Number(item.quantity) || 0;
    // Coba ambil dari berbagai field
    let price =
      Number(item.cost_price) ||
      Number(item.unit_price) ||
      Number(item.price) ||
      0;

    // Jika price masih 0, coba cari dari inventory items
    if (price === 0 && item.item_id) {
      price = getItemCost(item.item_id);
    }

    console.log(
      `📦 Material: ${item.item_name || item.item_id}, qty: ${qty}, price: ${price}`,
    );
    return sum + qty * price;
  }, 0);

  console.log("💰 Material Cost calculated:", totalMaterialCost);

  // ✅ Other Expenses - dari project expenses
  const otherExpenses =
    Number(project.other_expenses) || Number(inquiry.other_expenses) || 0;

  // ✅ Total Actual Cost
  const actualCost = totalLaborCost + totalMaterialCost + otherExpenses;

  // ✅ Payments summary
  const paymentsList = payments || [];
  const totalDeposit = paymentsList
    .filter((p) => {
      const type = (p.payment_type || p.type || "").toLowerCase();
      return type === "deposit";
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalPaid = paymentsList
    .filter((p) => {
      const status = (p.status || "").toLowerCase();
      return ["completed", "confirmed", "paid", "success", "settled"].includes(
        status,
      );
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalPending = paymentsList
    .filter((p) => {
      const status = (p.status || "").toLowerCase();
      return ["pending", "awaiting_confirmation", "processing"].includes(
        status,
      );
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  console.log("💰 Payment summary:", { totalDeposit, totalPaid, totalPending });

  // ✅ Return financial data
  return {
    estimated_cost: estimatedCost,
    actual_cost: actualCost,
    estimated_revenue: estimatedRevenue,
    actual_revenue: totalPaid,
    deposit_amount: depositAmount || totalDeposit,
    deposit_paid: depositPaid || totalDeposit > 0,
    material_cost: totalMaterialCost,
    labor_cost: totalLaborCost,
    other_expenses: otherExpenses,
    total_paid: totalPaid,
    total_deposit: totalDeposit,
    total_pending: totalPending,
  };
}
