// inquiries/renderers/financial.js

import { DOM } from "../dom.js";
import { Formatter } from "../formatters.js";

export function renderDrawerFinancial(financial) {
  console.log("💰 Rendering financial data:", financial);

  const elements = {
    estCost: DOM.drawerEstCost(),
    actualCost: DOM.drawerActualCost(),
    estRevenue: DOM.drawerEstRevenue(),
    actualRevenue: DOM.drawerActualRevenue(),
    deposit: DOM.drawerDeposit(),
    depositStatus: DOM.drawerDepositStatus(),
    profit: DOM.drawerProfit(),
    margin: DOM.drawerMargin(),
    materialCost: DOM.drawerMaterialCost(),
    laborCost: DOM.drawerLaborCost(),
    otherExpenses: DOM.drawerOtherExpenses(),
    totalCost: DOM.drawerTotalCost(),
    budgetPercent: DOM.budgetPercentage(),
    budgetFill: DOM.budgetProgressFill(),
  };

  if (!financial) {
    Object.values(elements).forEach((el) => {
      if (el) el.textContent = "-";
    });
    if (elements.budgetPercent) elements.budgetPercent.textContent = "0%";
    if (elements.budgetFill) {
      elements.budgetFill.style.width = "0%";
      elements.budgetFill.className = "budget-progress-fill";
    }
    return;
  }

  // ✅ Ambil semua nilai dengan default 0
  const estCost = Number(financial.estimated_cost) || 0;
  const actualCost = Number(financial.actual_cost) || 0;
  const estRevenue = Number(financial.estimated_revenue) || 0;
  const actualRevenue = Number(financial.actual_revenue) || 0;
  const deposit = Number(financial.deposit_amount) || 0;
  const depositPaid = financial.deposit_paid || false;
  const materialCost = Number(financial.material_cost) || 0;
  const laborCost = Number(financial.labor_cost) || 0;
  const otherExpenses = Number(financial.other_expenses) || 0;

  // ✅ Total cost = material + labor + other
  const totalCost = materialCost + laborCost + otherExpenses;

  // ✅ Jika actualCost masih 0 tapi totalCost > 0, gunakan totalCost
  const displayActualCost = actualCost > 0 ? actualCost : totalCost;

  console.log("💰 Values:", {
    estCost,
    actualCost,
    displayActualCost,
    totalCost,
    materialCost,
    laborCost,
  });

  // ✅ Update DOM
  if (elements.estCost)
    elements.estCost.textContent = Formatter.currency(estCost);
  if (elements.actualCost)
    elements.actualCost.textContent = Formatter.currency(displayActualCost);
  if (elements.estRevenue)
    elements.estRevenue.textContent = Formatter.currency(estRevenue);
  if (elements.actualRevenue)
    elements.actualRevenue.textContent = Formatter.currency(actualRevenue);
  if (elements.deposit)
    elements.deposit.textContent = Formatter.currency(deposit);

  if (elements.depositStatus) {
    elements.depositStatus.textContent = depositPaid
      ? "✅ Paid"
      : "❌ Not Paid";
    elements.depositStatus.style.color = depositPaid
      ? "var(--success, #10b981)"
      : "var(--danger, #ef4444)";
  }

  // ✅ Profit & Margin
  const profit = actualRevenue - displayActualCost;
  const margin = actualRevenue > 0 ? (profit / actualRevenue) * 100 : 0;

  if (elements.profit) {
    elements.profit.textContent = Formatter.currency(profit);
    elements.profit.style.color =
      profit >= 0 ? "var(--success, #10b981)" : "var(--danger, #ef4444)";
  }
  if (elements.margin) {
    elements.margin.textContent = margin.toFixed(1) + "%";
    elements.margin.style.color =
      margin >= 0 ? "var(--success, #10b981)" : "var(--danger, #ef4444)";
  }

  // ✅ Cost Breakdown
  if (elements.materialCost)
    elements.materialCost.textContent = Formatter.currency(materialCost);
  if (elements.laborCost)
    elements.laborCost.textContent = Formatter.currency(laborCost);
  if (elements.otherExpenses)
    elements.otherExpenses.textContent = Formatter.currency(otherExpenses);
  if (elements.totalCost)
    elements.totalCost.textContent = Formatter.currency(displayActualCost);

  // ✅ Budget Progress
  const budgetPercent =
    estCost > 0 ? Math.min((displayActualCost / estCost) * 100, 100) : 0;
  if (elements.budgetPercent)
    elements.budgetPercent.textContent = budgetPercent.toFixed(0) + "%";
  if (elements.budgetFill) {
    elements.budgetFill.style.width = `${budgetPercent}%`;
    elements.budgetFill.className = "budget-progress-fill";
    if (budgetPercent > 90) elements.budgetFill.classList.add("danger");
    else if (budgetPercent > 75) elements.budgetFill.classList.add("warning");
  }
}
