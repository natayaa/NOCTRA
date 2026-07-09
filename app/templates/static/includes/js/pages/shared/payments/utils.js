// ============================================================
// shared/payments/utils.js - Payment Utilities
// ============================================================

export function calculatePaymentSummary(payments) {
  if (!payments || payments.length === 0) {
    return {
      totalDeposit: 0,
      totalPaid: 0,
      totalPending: 0,
      remaining: 0,
      totalAll: 0,
    };
  }

  const totalDeposit = payments
    .filter((p) => {
      const type = (p.type || p.payment_type || "").toLowerCase();
      return type === "deposit";
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalPaid = payments
    .filter((p) => {
      const status = (p.status || "").toLowerCase();
      return ["completed", "confirmed", "paid", "settled"].includes(status);
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalPending = payments
    .filter((p) => {
      const status = (p.status || "").toLowerCase();
      return ["pending", "awaiting_confirmation", "processing"].includes(
        status,
      );
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
    remaining: totalAll - totalPaid - totalDeposit,
    totalAll,
  };
}
