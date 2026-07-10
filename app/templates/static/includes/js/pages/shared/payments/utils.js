// shared/payments/utils.js

/**
 * Calculate payment summary dari list payments
 * Field names match dengan response backend
 */
// shared/payments/utils.js

export function calculatePaymentSummary(payments) {
  if (!payments || payments.length === 0) {
    return {
      totalDeposit: 0,
      totalPaid: 0,
      totalPending: 0,
      totalCancelled: 0,
      remaining: 0,
      totalAll: 0,
      count: 0,
    };
  }

  console.log("📊 Calculating payment summary from:", payments);

  // ✅ Deposit = payment_type === "deposit" DAN status completed
  const totalDeposit = payments
    .filter((p) => {
      const type = (p.payment_type || p.type || "").toLowerCase();
      const status = (p.status || "").toLowerCase();
      return (
        type === "deposit" &&
        ["completed", "confirmed", "paid", "settled"].includes(status)
      );
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  // ✅ Paid = semua payment yang status completed (termasuk deposit)
  const totalPaid = payments
    .filter((p) => {
      const status = (p.status || "").toLowerCase();
      return ["completed", "confirmed", "paid", "settled", "success"].includes(
        status,
      );
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  // ✅ Pending = status pending
  const totalPending = payments
    .filter((p) => {
      const status = (p.status || "").toLowerCase();
      return [
        "pending",
        "awaiting_confirmation",
        "processing",
        "unpaid",
      ].includes(status);
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  // ✅ Cancelled
  const totalCancelled = payments
    .filter((p) => {
      const status = (p.status || "").toLowerCase();
      return ["cancelled", "failed", "voided", "rejected"].includes(status);
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalAll = payments.reduce(
    (sum, p) => sum + (Number(p.amount) || 0),
    0,
  );

  console.log("📊 Summary result:", {
    totalDeposit,
    totalPaid,
    totalPending,
    totalAll,
  });

  return {
    totalDeposit,
    totalPaid,
    totalPending,
    totalCancelled,
    remaining: totalAll - totalPaid - totalPending - totalCancelled,
    totalAll,
    count: payments.length,
  };
}
/**
 * Calculate invoice summary dari list invoices
 * Field names match dengan response backend
 */
export function calculateInvoiceSummary(invoices) {
  if (!invoices || invoices.length === 0) {
    return {
      totalInvoices: 0,
      totalAmount: 0,
      totalPaid: 0,
      totalUnpaid: 0,
      overdueCount: 0,
      overdueAmount: 0,
    };
  }

  // ✅ Total amount dari semua invoice
  const totalAmount = invoices.reduce(
    (sum, inv) => sum + (Number(inv.total_amount) || 0),
    0,
  );

  // ✅ Total paid dari invoice
  const totalPaid = invoices
    .filter((inv) => {
      const status = (inv.status || "").toLowerCase();
      return ["paid", "settled", "completed"].includes(status);
    })
    .reduce((sum, inv) => sum + (Number(inv.total_amount) || 0), 0);

  // ✅ Overdue invoices
  const overdueInvoices = invoices.filter((inv) => inv.is_overdue === true);
  const overdueAmount = overdueInvoices.reduce(
    (sum, inv) => sum + (Number(inv.total_amount) || 0),
    0,
  );

  return {
    totalInvoices: invoices.length,
    totalAmount,
    totalPaid,
    totalUnpaid: totalAmount - totalPaid,
    overdueCount: overdueInvoices.length,
    overdueAmount,
  };
}

/**
 * Calculate financial summary from payments, invoices, and costs
 */
export function calculateFinancialSummary(payments, invoices, costs = {}) {
  const paymentSummary = calculatePaymentSummary(payments);
  const invoiceSummary = calculateInvoiceSummary(invoices);

  const estimatedCost = costs.estimated_cost || 0;
  const actualCost = costs.actual_cost || 0;
  const laborCost = costs.labor_cost || 0;
  const materialCost = costs.material_cost || 0;

  return {
    payments: paymentSummary,
    invoices: invoiceSummary,
    costs: {
      estimated: estimatedCost,
      actual: actualCost,
      labor: laborCost,
      material: materialCost,
      expenses: costs.other_expenses || 0,
    },
    profit: paymentSummary.totalPaid - actualCost,
    margin:
      paymentSummary.totalPaid > 0
        ? ((paymentSummary.totalPaid - actualCost) / paymentSummary.totalPaid) *
          100
        : 0,
  };
}
