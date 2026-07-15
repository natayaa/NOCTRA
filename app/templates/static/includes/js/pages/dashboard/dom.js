// ============================================================
// dashboard/dom.js - DOM References
// ============================================================

export const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

export const $$ = (selector) => document.querySelectorAll(selector);

export const DOM = {
  // Stat Cards
  statRevenue: () => $("statRevenue"),
  statActiveProjects: () => $("statActiveProjects"),
  statInProduction: () => $("statInProduction"),
  statPendingInquiries: () => $("statPendingInquiries"),
  statOverdueInvoices: () => $("statOverdueInvoices"),
  statLowStock: () => $("statLowStock"),
  statActiveProjectsChange: () => $("statActiveProjectsChange"),
  statInProductionChange: () => $("statInProductionChange"),
  statPendingInquiriesChange: () => $("statPendingInquiriesChange"),
  statOverdueInvoicesChange: () => $("statOverdueInvoicesChange"),
  statLowStockChange: () => $("statLowStockChange"),

  // Mini Stats
  miniCompleted: () => $("miniCompleted"),
  miniQuotesSent: () => $("miniQuotesSent"),
  miniCustomers: () => $("miniCustomers"),

  // Recent Activities
  recentActivities: () => $("recentActivities"),

  // Recent Projects
  recentProjects: () => $("recentProjects"),

  // Recent Invoices
  recentInvoices: () => $("recentInvoices"),

  // Refresh Button
  refreshBtn: () => document.getElementById("refreshBtn"),

  // Toast
  toastContainer: () => $("toastContainer"),
};
