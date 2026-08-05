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
  // Normalisasi labor & materials menjadi array
  const laborArray = Array.isArray(labor) ? labor : labor?.items || [];
  const materialsArray = Array.isArray(materials)
    ? materials
    : materials?.items || [];

  const project = inquiry?.project || {};

  // Ambil dari inquiry/project (backend sudah menghitung)
  const estimatedCost = Number(inquiry.estimated_cost) || 0;
  const depositAmount = Number(inquiry.deposit_amount) || 0;
  const estimatedRevenue = Number(inquiry.estimated_revenue) || 0;
  const actualRevenue = Number(inquiry.actual_revenue) || 0;

  // Hitung actual cost dari labor + material (backend tidak menyediakan)
  const totalLaborCost = laborArray.reduce((sum, item) => {
    return sum + (Number(item.hours) || 0) * (Number(item.rate_per_hour) || 0);
  }, 0);

  const totalMaterialCost = materialsArray.reduce((sum, item) => {
    const qty = Number(item.quantity) || 0;
    const price =
      Number(item.unit_price) ||
      Number(item.price) ||
      Number(item.cost_price) ||
      0;
    return sum + qty * price;
  }, 0);

  // other_expenses tidak ada di backend, default 0
  const otherExpenses = 0;

  const actualCost = totalLaborCost + totalMaterialCost + otherExpenses;

  // Payment summary (dari payments list)
  const paymentSummary = calculatePaymentSummary(payments || []);
  const totalPaid = paymentSummary.totalPaid;
  const totalDeposit = paymentSummary.totalDeposit;
  const totalPending = paymentSummary.totalPending;

  const remaining = Math.max(0, actualCost - totalPaid);
  const depositPaid =
    totalDeposit > 0 || (depositAmount > 0 && totalDeposit >= depositAmount);

  console.log("📊 Financial calculation:", {
    estimatedCost,
    actualCost,
    estimatedRevenue,
    actualRevenue,
    depositAmount,
    totalPaid,
    remaining,
    totalLaborCost,
    totalMaterialCost,
  });

  return {
    estimated_cost: estimatedCost,
    actual_cost: actualCost,
    estimated_revenue: estimatedRevenue,
    actual_revenue: actualRevenue,
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
