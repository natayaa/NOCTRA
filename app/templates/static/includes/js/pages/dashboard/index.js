// ============================================================
// dashboard/index.js - Main Entry Point (FIXED)
// ============================================================

import { state, CONFIG } from "./config.js";
import { DashboardAPI } from "./api.js";
import { showToast } from "../../shared/toast.js";
import { renderStats, updateStatsFromResponse } from "./renderers/stats.js";
import {
  initCharts,
  destroyCharts,
  updateRevenueChart,
  updateProjectStatusChart,
} from "./renderers/charts.js";
import {
  renderActivities,
  updateActivitiesFromData,
} from "./renderers/activities.js";
import {
  renderRecentProjects,
  updateProjectsFromData,
} from "./renderers/projects.js";
import {
  renderRecentInvoices,
  updateInvoicesFromData,
} from "./renderers/invoices.js";
import { bindEvents } from "./handlers/events.js";

// ============================================================
// LOAD DASHBOARD DATA
// ============================================================

export async function loadDashboardData() {
  if (state.isLoading) return;
  state.isLoading = true;

  console.log("🔄 Loading dashboard data...");

  try {
    // Fetch all data in parallel
    const [
      projectStats,
      inquiryStats,
      paymentStats,
      overdueInvoices,
      outstandingInvoices,
      inventoryAlerts,
      recentProjects,
      recentInvoices,
      revenueTrend,
    ] = await Promise.all([
      DashboardAPI.getProjectStats(),
      DashboardAPI.getInquiryStats(),
      DashboardAPI.getPaymentStats(),
      DashboardAPI.getOverdueInvoices(),
      DashboardAPI.getOutstandingInvoices(),
      DashboardAPI.getInventoryAlerts(),
      DashboardAPI.getRecentProjects(CONFIG.RECENT_LIMIT),
      DashboardAPI.getRecentInvoices(CONFIG.RECENT_LIMIT),
      DashboardAPI.getRevenueTrend(),
    ]);

    // Process stats
    processStats(
      projectStats,
      inquiryStats,
      paymentStats,
      overdueInvoices,
      outstandingInvoices,
      inventoryAlerts,
    );
    processRevenueTrend(revenueTrend);
    processProjectStatus(projectStats);

    // Recent data
    processProjects(recentProjects);
    processInvoices(recentInvoices);

    // Activities - fallback to empty
    state.recentActivities = [];

    // Render everything
    renderStats();
    renderActivities();
    renderRecentProjects();
    renderRecentInvoices();

    // Destroy and recreate charts
    destroyCharts();
    initCharts();

    state.lastRefresh = new Date();
    console.log("✅ Dashboard data loaded successfully");
  } catch (error) {
    console.error("❌ Failed to load dashboard data:", error);
    showToast("Failed to load dashboard data: " + error.message, "error");
  } finally {
    state.isLoading = false;
  }
}

// ============================================================
// DATA PROCESSORS
// ============================================================

function processStats(
  projectStats,
  inquiryStats,
  paymentStats,
  overdueInvoices,
  outstandingInvoices,
  inventoryAlerts,
) {
  const byStatus = projectStats?.by_status || {};

  const activeProjects = (byStatus.active || 0) + (byStatus.in_progress || 0);
  const inProduction = byStatus.in_progress || 0;
  const completedProjects = byStatus.completed || 0;

  const inquiryByStatus = inquiryStats?.by_status || {};
  const pendingInquiries =
    (inquiryByStatus.new || 0) + (inquiryByStatus.under_review || 0);
  const quotesSent = inquiryByStatus.quoted || 0;
  const totalCustomers =
    inquiryStats?.unique_customers || inquiryStats?.total_customers || 0;

  const revenue = paymentStats?.total_revenue || paymentStats?.total_paid || 0;

  const overdueCount = Array.isArray(overdueInvoices)
    ? overdueInvoices.length
    : 0;
  const outstandingCount = Array.isArray(outstandingInvoices)
    ? outstandingInvoices.length
    : 0;
  const lowStockCount = Array.isArray(inventoryAlerts)
    ? inventoryAlerts.length
    : 0;

  updateStatsFromResponse({
    revenue,
    activeProjects,
    inProduction,
    pendingInquiries,
    overdueInvoices: overdueCount,
    lowStockItems: lowStockCount,
    completedProjects,
    quotesSent,
    totalCustomers,
    outstandingInvoices: outstandingCount,
  });
}

function processRevenueTrend(trendData) {
  if (!trendData || !Array.isArray(trendData) || trendData.length === 0) {
    state.revenueTrend.labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"];
    state.revenueTrend.values = [0, 0, 0, 0, 0, 0];
    return;
  }

  state.revenueTrend.labels = trendData.map(
    (item) => item.month || item.label || "",
  );
  state.revenueTrend.values = trendData.map(
    (item) => item.total || item.value || 0,
  );
}

function processProjectStatus(projectStats) {
  const byStatus = projectStats?.by_status || {};
  const statusMap = {
    active: "Active",
    in_progress: "In Progress",
    completed: "Completed",
    on_hold: "On Hold",
    draft: "Draft",
    cancelled: "Cancelled",
  };

  const labels = [];
  const values = [];
  Object.keys(statusMap).forEach((key) => {
    const count = byStatus[key] || 0;
    if (count > 0 || Object.keys(byStatus).length === 0) {
      labels.push(statusMap[key]);
      values.push(count);
    }
  });

  if (values.every((v) => v === 0)) {
    labels.length = 0;
    values.length = 0;
    labels.push("No Data");
    values.push(1);
  }

  state.projectStatus.labels = labels;
  state.projectStatus.values = values;
}

function processProjects(projects) {
  state.recentProjects = projects || [];
}

function processInvoices(invoices) {
  state.recentInvoices = invoices || [];
}

// ============================================================
// INITIALIZATION
// ============================================================

export async function initDashboard() {
  console.log("🚀 Initializing Dashboard...");

  try {
    bindEvents();
    await loadDashboardData();
    console.log("✅ Dashboard initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize dashboard:", error);
    showToast("Failed to initialize dashboard: " + error.message, "error");
  }
}

// ============================================================
// EXPOSE
// ============================================================

window.initDashboard = initDashboard;
window.loadDashboardData = loadDashboardData;
