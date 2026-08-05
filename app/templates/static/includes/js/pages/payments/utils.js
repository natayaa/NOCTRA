// ============================================================
// shared/payments/utils.js - Payment Utilities
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
  const totalDeposit = payments
    .filter((p) => p.type === "deposit" || p.payment_type === "deposit")
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalPaid = payments
    .filter(
      (p) =>
        p.status === "completed" ||
        p.status === "confirmed" ||
        p.status === "paid" ||
        p.status === "success",
    )
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalPending = payments
    .filter(
      (p) => p.status === "pending" || p.status === "awaiting_confirmation",
    )
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalRefund = payments
    .filter((p) => p.type === "refund")
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  return {
    totalDeposit,
    totalPaid,
    totalPending,
    totalRefund,
    remaining: totalDeposit - totalPaid,
  };
}

export function calculateInvoiceSummary(invoices) {
  const totalInvoices = invoices.length;
  const totalAmount = invoices.reduce(
    (sum, inv) => sum + (Number(inv.total) || 0),
    0,
  );
  const totalPaid = invoices
    .filter((inv) => inv.status === "paid")
    .reduce((sum, inv) => sum + (Number(inv.total) || 0), 0);
  const totalOutstanding = invoices
    .filter((inv) => inv.status !== "paid" && inv.status !== "cancelled")
    .reduce((sum, inv) => sum + (Number(inv.total) || 0), 0);
  const overdueInvoices = invoices.filter((inv) => inv.status === "overdue");

  return {
    totalInvoices,
    totalAmount,
    totalPaid,
    totalOutstanding,
    overdueCount: overdueInvoices.length,
    overdueAmount: overdueInvoices.reduce(
      (sum, inv) => sum + (Number(inv.total) || 0),
      0,
    ),
  };
}
