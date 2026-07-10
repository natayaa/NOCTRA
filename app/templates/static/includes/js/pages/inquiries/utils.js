// inquiries/utils.js

import { state } from "./config.js";
// ✅ Import dari shared/payments untuk konsistensi
import { calculatePaymentSummary } from "../shared/payments/utils.js";

/**
 * Get item name by ID from inventory items state
 */
export function getItemName(itemId) {
  if (!itemId) return "Unknown";

  if (state.inventoryItems && state.inventoryItems.length > 0) {
    const found = state.inventoryItems.find((i) => i.id === itemId);
    if (found) return found.name || "Unknown";
  }

  // ✅ Fallback: tampilkan ID pendek
  return `Item ${itemId.substring(0, 8)}`;
}

/**
 * Get item unit by ID from inventory items state
 */
export function getItemUnit(itemId) {
  if (!itemId) return "";

  if (state.inventoryItems && state.inventoryItems.length > 0) {
    const found = state.inventoryItems.find((i) => i.id === itemId);
    if (found) return found.unit || "";
  }

  return "";
}

/**
 * Get item cost by ID from inventory items state
 * ✅ Cek multiple price fields
 */
export function getItemCost(itemId) {
  if (!itemId) return 0;

  if (state.inventoryItems && state.inventoryItems.length > 0) {
    const found = state.inventoryItems.find((i) => i.id === itemId);
    if (found) {
      // ✅ Cek semua kemungkinan field price
      return found.cost_price || found.selling_price || found.price || 0;
    }
  }

  return 0;
}

/**
 * Get full item details by ID
 */
export function getItemDetails(itemId) {
  if (!itemId) return null;

  if (state.inventoryItems && state.inventoryItems.length > 0) {
    const found = state.inventoryItems.find((i) => i.id === itemId);
    if (found) {
      return {
        name: found.name || "Unknown",
        unit: found.unit || "",
        cost_price: found.cost_price || 0,
        selling_price: found.selling_price || 0,
        price: found.price || 0,
        current_stock: found.current_stock || 0,
        category: found.category || "",
        sub_category: found.sub_category || "",
      };
    }
  }

  return null;
}

/**
 * Calculate financial data from inquiry, labor, materials, and payments
 * ✅ Menggunakan calculatePaymentSummary dari shared
 */
export function calculateFinancialFromData(
  inquiry,
  labor,
  materials,
  payments,
) {
  console.log("📊 Calculating financial from:", {
    //inquiry: inquiry?.id,
    //laborCount: labor?.length || 0,
    // materialsCount: materials?.length || 0,
    // paymentsCount: payments?.length || 0,
  });

  const project = inquiry?.project || {};

  // ✅ Estimated Cost - dari project atau inquiry
  const estimatedCost =
    Number(project.estimated_cost) || Number(inquiry.estimated_budget) || 0;
  const estimatedRevenue =
    Number(project.estimated_revenue) || Number(inquiry.estimated_revenue) || 0;

  // ✅ Deposit - dari inquiry atau project
  const inquiryDeposit = Number(inquiry.deposit_required) || 0;
  const projectDeposit = Number(project.deposit_amount) || 0;
  const depositAmount = projectDeposit || inquiryDeposit || 0;

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

    // Coba ambil price dari berbagai field
    let price =
      Number(item.cost_price) ||
      Number(item.unit_price) ||
      Number(item.price) ||
      0;

    // Jika price masih 0, coba cari dari inventory items
    if (price === 0 && item.item_id) {
      price = getItemCost(item.item_id);
    }

    return sum + qty * price;
  }, 0);

  console.log("💰 Material Cost calculated:", totalMaterialCost);

  // ✅ Other Expenses - dari project expenses
  const otherExpenses =
    Number(project.other_expenses) || Number(inquiry.other_expenses) || 0;

  // ✅ Total Actual Cost
  const actualCost = totalLaborCost + totalMaterialCost + otherExpenses;

  // ✅ Payments summary - pakai fungsi dari shared/payments
  const paymentSummary = calculatePaymentSummary(payments || []);
  console.log("💰 Payment Summary:", paymentSummary);

  // ✅ Total Paid = semua payment yang completed (termasuk deposit)
  const totalPaid = paymentSummary.totalPaid;
  const totalDeposit = paymentSummary.totalDeposit;
  const totalPending = paymentSummary.totalPending;

  // ✅ Remaining = actual cost - total paid (termasuk deposit)
  const remaining = Math.max(0, actualCost - totalPaid);

  // ✅ Deposit paid status
  const depositPaid =
    totalDeposit > 0 || (depositAmount > 0 && totalDeposit >= depositAmount);

  // console.log("📊 Final financial:", {
  //  estimatedCost,
  //  actualCost,
  //  totalPaid,
  //  totalDeposit,
  //  remaining,
  //});

  return {
    estimated_cost: estimatedCost,
    actual_cost: actualCost,
    estimated_revenue: estimatedRevenue,
    actual_revenue: totalPaid,
    deposit_amount: depositAmount || totalDeposit,
    deposit_paid: depositPaid,
    material_cost: totalMaterialCost,
    labor_cost: totalLaborCost,
    other_expenses: otherExpenses,
    total_paid: totalPaid,
    total_deposit: totalDeposit,
    total_pending: totalPending,
    remaining: remaining,
  };
}

/**
 * Helper: Format currency for display
 */
export function formatCurrency(amount) {
  if (!amount && amount !== 0) return "Rp 0";
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Number(amount));
}

/**
 * Helper: Get status color
 */
export function getStatusColor(status) {
  const colors = {
    new: "#3b82f6",
    under_review: "#8b5cf6",
    contacted: "#f59e0b",
    quoted: "#f59e0b",
    approved: "#10b981",
    converted: "#10b981",
    rejected: "#ef4444",
    closed: "#94a3b8",
    completed: "#10b981",
  };
  return colors[status] || "#94a3b8";
}

/**
 * Helper: Get status label
 */
export function getStatusLabel(status) {
  const labels = {
    new: "New",
    under_review: "Under Review",
    contacted: "Contacted",
    quoted: "Quoted",
    approved: "Approved",
    converted: "Converted",
    rejected: "Rejected",
    closed: "Closed",
    completed: "Completed",
  };
  return labels[status] || status;
}
