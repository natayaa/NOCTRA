// ============================================================
// shared/payments/utils.js - Payment Utilities (FIXED)
// ============================================================

export function ensureArray(data) {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") {
    if (data.data && Array.isArray(data.data)) return data.data;
    if (data.items && Array.isArray(data.items)) return data.items;
    if (data.payments && Array.isArray(data.payments)) return data.payments;
    if (data.invoices && Array.isArray(data.invoices)) return data.invoices;
    return [data];
  }
  return [];
}

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

  const totalPaid = payments
    .filter((p) => {
      const status = (p.status || "").toLowerCase();
      return ["completed", "confirmed", "paid", "settled", "success"].includes(
        status,
      );
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

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

  const totalAmount = invoices.reduce(
    (sum, inv) => sum + (Number(inv.total_amount) || 0),
    0,
  );

  const totalPaid = invoices
    .filter((inv) => {
      const status = (inv.status || "").toLowerCase();
      return ["paid", "settled", "completed"].includes(status);
    })
    .reduce((sum, inv) => sum + (Number(inv.total_amount) || 0), 0);

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
