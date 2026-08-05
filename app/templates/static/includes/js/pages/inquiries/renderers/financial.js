// inquiries/renderers/financial.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { Formatter } from "../formatters.js";

export function renderDrawerFinancial(financial) {
  console.log("💰 Rendering financial data:");

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
    setEmptyState(elements);
    return;
  }

  // ✅ Extract values with defaults
  const estCost = Number(financial.estimated_cost) || 0;
  const actualCost = Number(financial.actual_cost) || 0;
  const estRevenue = Number(financial.estimated_revenue) || 0;
  const actualRevenue = Number(financial.actual_revenue) || 0;
  const deposit = Number(financial.deposit_amount) || 0;
  const depositPaid = financial.deposit_paid || false;
  const materialCost = Number(financial.material_cost) || 0;
  const laborCost = Number(financial.labor_cost) || 0;
  const otherExpenses = Number(financial.other_expenses) || 0;
  const totalCost = materialCost + laborCost + otherExpenses;
  const displayActualCost = actualCost > 0 ? actualCost : totalCost;

  // ✅ Profit & Margin
  const profit = actualRevenue - displayActualCost;
  const margin = actualRevenue > 0 ? (profit / actualRevenue) * 100 : 0;
  const isProfit = profit >= 0;

  // ✅ Budget Progress
  const budgetPercent =
    estCost > 0 ? Math.min((displayActualCost / estCost) * 100, 100) : 0;

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

  if (elements.profit) {
    elements.profit.textContent = Formatter.currency(profit);
    elements.profit.style.color = isProfit
      ? "var(--success, #10b981)"
      : "var(--danger, #ef4444)";
  }

  if (elements.margin) {
    elements.margin.textContent = margin.toFixed(1) + "%";
    elements.margin.style.color = isProfit
      ? "var(--success, #10b981)"
      : "var(--danger, #ef4444)";
  }

  if (elements.materialCost)
    elements.materialCost.textContent = Formatter.currency(materialCost);
  if (elements.laborCost)
    elements.laborCost.textContent = Formatter.currency(laborCost);
  if (elements.otherExpenses)
    elements.otherExpenses.textContent = Formatter.currency(otherExpenses);
  if (elements.totalCost)
    elements.totalCost.textContent = Formatter.currency(displayActualCost);

  if (elements.budgetPercent) {
    elements.budgetPercent.textContent = budgetPercent.toFixed(0) + "%";
    elements.budgetPercent.style.color =
      budgetPercent > 90
        ? "var(--danger, #ef4444)"
        : budgetPercent > 75
          ? "var(--warning, #f59e0b)"
          : "var(--text-primary)";
  }

  if (elements.budgetFill) {
    elements.budgetFill.style.width = `${budgetPercent}%`;
    elements.budgetFill.className = "budget-progress-fill";
    if (budgetPercent > 90) elements.budgetFill.classList.add("danger");
    else if (budgetPercent > 75) elements.budgetFill.classList.add("warning");
  }
}

function setEmptyState(elements) {
  Object.values(elements).forEach((el) => {
    if (el) el.textContent = "-";
  });
  if (elements.budgetPercent) {
    elements.budgetPercent.textContent = "0%";
    elements.budgetPercent.style.color = "";
  }
  if (elements.budgetFill) {
    elements.budgetFill.style.width = "0%";
    elements.budgetFill.className = "budget-progress-fill";
  }
}
