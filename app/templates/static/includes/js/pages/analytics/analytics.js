// static/js/pages/analytics/analytics.js
// ============================================================
// NOCTRA Analytics Dashboard - Regular Script (Non-Module)
// ============================================================

(function () {
  "use strict";

  // ============================================================
  // CONFIG (Local)
  // ============================================================
  const CONFIG = {
    API_BASE_URL: "/api",
    TOAST_DURATION: 4000,
    CHART_COLORS: {
      primary: "#ff6b00",
      primaryLight: "rgba(255, 107, 0, 0.1)",
      success: "#00d578",
      successLight: "rgba(0, 213, 120, 0.1)",
      danger: "#ef4444",
      dangerLight: "rgba(239, 68, 68, 0.1)",
      warning: "#f59e0b",
      warningLight: "rgba(245, 158, 11, 0.1)",
      info: "#3b82f6",
      infoLight: "rgba(59, 130, 246, 0.1)",
      purple: "#8b5cf6",
      purpleLight: "rgba(139, 92, 246, 0.1)",
      teal: "#14b8a6",
      tealLight: "rgba(20, 184, 166, 0.1)",
      pink: "#ec4899",
      pinkLight: "rgba(236, 72, 153, 0.1)",
      gray: "#94a3b8",
      grayLight: "rgba(148, 163, 184, 0.1)",
    },
    STATUS_COLORS: {
      draft: "#94a3b8",
      active: "#3b82f6",
      in_progress: "#f59e0b",
      on_hold: "#94a3b8",
      completed: "#00d578",
      cancelled: "#ef4444",
    },
    CHART_PERIODS: ["week", "month", "year"],
  };

  const CHART_COLORS = [
    CONFIG.CHART_COLORS.primary,
    CONFIG.CHART_COLORS.success,
    CONFIG.CHART_COLORS.warning,
    CONFIG.CHART_COLORS.info,
    CONFIG.CHART_COLORS.purple,
    CONFIG.CHART_COLORS.teal,
    CONFIG.CHART_COLORS.pink,
    CONFIG.CHART_COLORS.gray,
  ];

  // ============================================================
  // TOAST SYSTEM (Local)
  // ============================================================
  function showToast(message, type = "info", duration = 4000) {
    const container =
      document.getElementById("toastContainer") ||
      (function () {
        const c = document.createElement("div");
        c.id = "toastContainer";
        c.className = "toast-container";
        document.body.appendChild(c);
        return c;
      })();

    const configs = {
      success: { icon: "✅", className: "toast-success" },
      error: { icon: "❌", className: "toast-error" },
      warning: { icon: "⚠️", className: "toast-warning" },
      info: { icon: "ℹ️", className: "toast-info" },
    };

    const config = configs[type] || configs.info;
    const toast = document.createElement("div");
    toast.className = `toast ${config.className}`;
    toast.style.animation = "toastSlideIn 0.35s ease forwards";
    toast.innerHTML = `
      <span>${config.icon} ${message}</span>
      <button class="toast-close">&times;</button>
    `;

    container.appendChild(toast);

    toast.querySelector(".toast-close").addEventListener("click", function () {
      toast.remove();
    });

    setTimeout(function () {
      toast.style.animation = "toastSlideOut 0.3s ease forwards";
      setTimeout(function () {
        toast.remove();
      }, 300);
    }, duration);
  }

  // ============================================================
  // HELPERS
  // ============================================================
  function formatCurrency(value) {
    if (!value && value !== 0) return "Rp 0";
    return new Intl.NumberFormat("id-ID", {
      style: "currency",
      currency: "IDR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  }

  function formatNumber(value) {
    if (!value && value !== 0) return "0";
    return new Intl.NumberFormat("id-ID").format(value);
  }

  function formatPercentage(value) {
    if (!value && value !== 0) return "0%";
    return value.toFixed(1) + "%";
  }

  function formatDate(dateString) {
    if (!dateString) return "-";
    try {
      return new Date(dateString).toLocaleDateString("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return "-";
    }
  }

  function getStatusBadge(status) {
    const labels = {
      draft: "Draft",
      active: "Active",
      in_progress: "In Progress",
      on_hold: "On Hold",
      completed: "Completed",
      cancelled: "Cancelled",
    };
    return labels[status] || status;
  }

  function getStatusColor(status) {
    return CONFIG.STATUS_COLORS[status] || CONFIG.STATUS_COLORS.draft;
  }

  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // ============================================================
  // STATE
  // ============================================================
  const state = {
    period: "week",
    startDate: null,
    endDate: null,
    data: {
      insights: null,
      budget: null,
      revenueProfit: null,
      conversion: null,
      expenseBreakdown: null,
      projectStatus: null,
      profitability: null,
      expenses: null,
      kpis: null,
    },
    charts: {
      revenueProfit: null,
      conversion: null,
      expensePie: null,
      projectStatus: null,
    },
    isLoading: false,
  };

  // ============================================================
  // DOM REFS
  // ============================================================
  function getEl(id) {
    return document.getElementById(id);
  }

  const DOM = {
    // Toolbar
    periodFilter: getEl("periodFilter"),
    dateRangePicker: getEl("dateRangePicker"),
    startDate: getEl("startDate"),
    endDate: getEl("endDate"),
    applyDateRange: getEl("applyDateRange"),
    refreshBtn: getEl("refreshAnalytics"),
    lastUpdated: getEl("lastUpdated"),
    exportBtn: getEl("exportAnalytics"),

    // Insights
    totalRevenue: getEl("totalRevenue"),
    netProfit: getEl("netProfit"),
    profitMargin: getEl("profitMargin"),
    conversionRate: getEl("conversionRate"),
    completedProjects: getEl("completedProjects"),
    avgDuration: getEl("avgDuration"),
    revenueTrend: getEl("revenueTrend"),
    profitTrend: getEl("profitTrend"),
    marginTrend: getEl("marginTrend"),
    conversionTrend: getEl("conversionTrend"),
    completedTrend: getEl("completedTrend"),
    durationTrend: getEl("durationTrend"),

    // Budget
    budgetRevenue: getEl("budgetRevenue"),
    budgetExpenses: getEl("budgetExpenses"),
    budgetProfit: getEl("budgetProfit"),
    budgetMargin: getEl("budgetMargin"),

    // Tables
    profitabilityBody: getEl("profitabilityBody"),
    expenseTableBody: getEl("expenseTableBody"),
    expenseTotal: getEl("expenseTotal"),
    expenseSearch: getEl("expenseSearch"),
    expenseCategoryFilter: getEl("expenseCategoryFilter"),
    profitSortFilter: getEl("profitSortFilter"),

    // KPIs
    avgRevenuePerProject: getEl("avgRevenuePerProject"),
    avgCostPerProject: getEl("avgCostPerProject"),
    avgProfitPerProject: getEl("avgProfitPerProject"),
    avgProjectDuration: getEl("avgProjectDuration"),
    materialCostRatio: getEl("materialCostRatio"),
    laborCostRatio: getEl("laborCostRatio"),
    onTimeDelivery: getEl("onTimeDelivery"),
    customerReturnRate: getEl("customerReturnRate"),

    // Modal
    exportModal: getEl("exportModal"),
    closeExportModal: getEl("closeExportModal"),
    cancelExportBtn: getEl("cancelExportBtn"),
    confirmExportBtn: getEl("confirmExportBtn"),
    exportFormat: getEl("exportFormat"),

    // Loading
    loadingSkeleton: getEl("loadingSkeleton"),
    insightGrid: getEl("insightGrid"),
  };

  // ============================================================
  // CHART HELPERS
  // ============================================================
  function getChartDefaults() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: "#94a3b8",
            font: { family: "Inter, sans-serif", size: 11 },
            boxWidth: 12,
            padding: 12,
          },
        },
        tooltip: {
          backgroundColor: "rgba(0,0,0,0.8)",
          titleColor: "#f1f5f9",
          bodyColor: "#94a3b8",
          borderColor: "rgba(255,255,255,0.05)",
          borderWidth: 1,
          cornerRadius: 8,
          padding: 12,
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || "";
              let value =
                context.parsed.y !== undefined
                  ? context.parsed.y
                  : context.parsed;
              if (typeof value === "number") {
                if (
                  label.toLowerCase().includes("revenue") ||
                  label.toLowerCase().includes("profit") ||
                  label.toLowerCase().includes("cost") ||
                  label.toLowerCase().includes("expense")
                ) {
                  return label + ": " + formatCurrency(value);
                }
                return label + ": " + formatNumber(value);
              }
              return label + ": " + value;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.03)", drawBorder: false },
          ticks: {
            color: "#64748b",
            font: { family: "Inter, sans-serif", size: 10 },
          },
        },
        y: {
          grid: { color: "rgba(255,255,255,0.03)", drawBorder: false },
          ticks: {
            color: "#64748b",
            font: { family: "Inter, sans-serif", size: 10 },
            callback: function (value) {
              if (value >= 1000000)
                return "Rp" + (value / 1000000).toFixed(1) + "M";
              if (value >= 1000) return "Rp" + (value / 1000).toFixed(0) + "K";
              return "Rp" + value;
            },
          },
        },
      },
    };
  }

  // ============================================================
  // API CALLS
  // ============================================================
  async function apiFetch(endpoint, options = {}) {
    const url = `/api${endpoint}`;
    const config = {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(
          data.detail || data.message || `HTTP ${response.status}`,
        );
      }
      return data;
    } catch (error) {
      console.error("API Error:", error);
      throw error;
    }
  }

  // ============================================================
  // DATA LOADING
  // ============================================================
  function buildParams() {
    const params = new URLSearchParams();
    params.set("period", state.period);
    if (state.startDate) params.set("start_date", state.startDate);
    if (state.endDate) params.set("end_date", state.endDate);
    return params;
  }

  async function loadAllData() {
    if (state.isLoading) return;
    state.isLoading = true;
    showLoading(true);

    try {
      const params = buildParams();

      const [
        insights,
        budget,
        revenueProfit,
        conversion,
        expenseBreakdown,
        projectStatus,
        profitability,
        expenses,
        kpis,
      ] = await Promise.all([
        apiFetch(`/analytics/insights?${params}`),
        apiFetch(`/analytics/budget?${params}`),
        apiFetch(`/analytics/revenue-profit?${params}`),
        apiFetch(`/analytics/conversion?${params}`),
        apiFetch(`/analytics/expense-breakdown?${params}`),
        apiFetch(`/analytics/project-status?${params}`),
        apiFetch(`/analytics/profitability?${params}`),
        apiFetch(`/analytics/expenses?${params}`),
        apiFetch(`/analytics/kpis?${params}`),
      ]);

      state.data = {
        insights: insights.data || insights,
        budget: budget.data || budget,
        revenueProfit: revenueProfit.data || revenueProfit,
        conversion: conversion.data || conversion,
        expenseBreakdown: expenseBreakdown.data || expenseBreakdown,
        projectStatus: projectStatus.data || projectStatus,
        profitability: profitability.data || profitability,
        expenses: expenses.data || expenses,
        kpis: kpis.data || kpis,
      };

      renderAll();
      updateLastUpdated();
    } catch (error) {
      console.error("Failed to load analytics:", error);
      showToast("Failed to load analytics data: " + error.message, "error");
    } finally {
      state.isLoading = false;
      showLoading(false);
    }
  }

  // ============================================================
  // RENDER FUNCTIONS
  // ============================================================
  function renderAll() {
    renderInsights();
    renderBudget();
    renderRevenueProfitChart();
    renderConversionChart();
    renderExpensePieChart();
    renderProjectStatusChart();
    renderProfitabilityTable();
    renderExpensesTable();
    renderKpis();
  }

  function setText(el, text) {
    if (el) el.textContent = text;
  }

  function setTrend(el, value, prefix = "", inverse = false) {
    if (!el) return;
    const isPositive = inverse ? value < 0 : value > 0;
    const sign = isPositive ? "+" : "";
    const color = isPositive ? "var(--success)" : "var(--danger)";
    const icon = isPositive ? "↑" : "↓";
    el.innerHTML = `${icon} ${sign}${value}${prefix} vs previous period`;
    el.style.color = color;
  }

  function showLoading(show) {
    if (DOM.loadingSkeleton) {
      DOM.loadingSkeleton.style.display = show ? "block" : "none";
    }
    if (DOM.insightGrid) {
      DOM.insightGrid.style.opacity = show ? "0.3" : "1";
    }
  }

  function updateLastUpdated() {
    if (!DOM.lastUpdated) return;
    const now = new Date();
    DOM.lastUpdated.textContent =
      "Last updated: " +
      now.toLocaleString("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
  }

  // ----- Insights -----
  function renderInsights() {
    const data = state.data.insights;
    if (!data) return;

    const {
      total_revenue = 0,
      net_profit = 0,
      profit_margin = 0,
      conversion_rate = 0,
      completed_projects = 0,
      avg_duration = 0,
      revenue_trend = 0,
      profit_trend = 0,
      margin_trend = 0,
      conversion_trend = 0,
      completed_trend = 0,
      duration_trend = 0,
    } = data;

    setText(DOM.totalRevenue, formatCurrency(total_revenue));
    setText(DOM.netProfit, formatCurrency(net_profit));
    setText(DOM.profitMargin, formatPercentage(profit_margin));
    setText(DOM.conversionRate, formatPercentage(conversion_rate));
    setText(DOM.completedProjects, formatNumber(completed_projects));
    setText(DOM.avgDuration, avg_duration + " days");

    setTrend(DOM.revenueTrend, revenue_trend, "Rp");
    setTrend(DOM.profitTrend, profit_trend, "Rp");
    setTrend(DOM.marginTrend, margin_trend, "%");
    setTrend(DOM.conversionTrend, conversion_trend, "%");
    setTrend(DOM.completedTrend, completed_trend, "");
    setTrend(DOM.durationTrend, duration_trend, "", true);
  }

  // ----- Budget -----
  function renderBudget() {
    const data = state.data.budget;
    if (!data) return;

    const {
      total_revenue = 0,
      total_expenses = 0,
      net_profit = 0,
      avg_margin = 0,
    } = data;

    setText(DOM.budgetRevenue, formatCurrency(total_revenue));
    setText(DOM.budgetExpenses, formatCurrency(total_expenses));
    setText(DOM.budgetProfit, formatCurrency(net_profit));
    setText(DOM.budgetMargin, formatPercentage(avg_margin));
  }

  // ----- KPIs -----
  function renderKpis() {
    const data = state.data.kpis;
    if (!data) return;

    const {
      avg_revenue_per_project = 0,
      avg_cost_per_project = 0,
      avg_profit_per_project = 0,
      avg_project_duration = 0,
      material_cost_ratio = 0,
      labor_cost_ratio = 0,
      on_time_delivery = 0,
      customer_return_rate = 0,
    } = data;

    setText(DOM.avgRevenuePerProject, formatCurrency(avg_revenue_per_project));
    setText(DOM.avgCostPerProject, formatCurrency(avg_cost_per_project));
    setText(DOM.avgProfitPerProject, formatCurrency(avg_profit_per_project));
    setText(DOM.avgProjectDuration, avg_project_duration + " days");
    setText(DOM.materialCostRatio, formatPercentage(material_cost_ratio));
    setText(DOM.laborCostRatio, formatPercentage(labor_cost_ratio));
    setText(DOM.onTimeDelivery, formatPercentage(on_time_delivery));
    setText(DOM.customerReturnRate, formatPercentage(customer_return_rate));
  }

  // ----- Tables -----
  function renderProfitabilityTable() {
    const data = state.data.profitability;
    const body = DOM.profitabilityBody;
    if (!body) return;

    if (!data || data.length === 0) {
      body.innerHTML = `<tr><td colspan="7" class="no-data">No project data available</td></tr>`;
      return;
    }

    body.innerHTML = data
      .map(function (item) {
        const revenue = item.revenue || 0;
        const cost = item.cost || 0;
        const profit = revenue - cost;
        const margin = revenue > 0 ? (profit / revenue) * 100 : 0;
        const status = item.status || "draft";
        const statusColor = getStatusColor(status);

        return `
        <tr>
          <td><strong>${escapeHtml(item.project_name || "Unknown")}</strong></td>
          <td>${escapeHtml(item.customer_name || "-")}</td>
          <td>${formatCurrency(revenue)}</td>
          <td>${formatCurrency(cost)}</td>
          <td style="color:${profit >= 0 ? "var(--success)" : "var(--danger)"};">${formatCurrency(profit)}</td>
          <td style="color:${margin >= 0 ? "var(--success)" : "var(--danger)"};">${formatPercentage(margin)}</td>
          <td><span class="status-badge" style="background:${statusColor}20;color:${statusColor};">${getStatusBadge(status)}</span></td>
        </tr>
      `;
      })
      .join("");
  }

  function renderExpensesTable() {
    const data = state.data.expenses;
    const body = DOM.expenseTableBody;
    if (!body) return;

    if (!data || data.length === 0) {
      body.innerHTML = `<tr><td colspan="6" class="no-data">No expense data available</td></tr>`;
      if (DOM.expenseTotal) DOM.expenseTotal.textContent = "Total: Rp 0";
      return;
    }

    let total = 0;
    body.innerHTML = data
      .map(function (item) {
        const amount = item.amount || 0;
        total += amount;
        const status = item.status || "approved";
        const statusColor =
          status === "approved"
            ? "var(--success)"
            : status === "pending"
              ? "var(--warning)"
              : "var(--danger)";

        return `
        <tr>
          <td>${formatDate(item.expense_date || item.created_at)}</td>
          <td>${escapeHtml(item.project_name || "-")}</td>
          <td><span class="badge badge-muted">${escapeHtml(item.category || "Other")}</span></td>
          <td>${escapeHtml(item.description || item.name || "-")}</td>
          <td>${formatCurrency(amount)}</td>
          <td><span class="badge" style="background:${statusColor}20;color:${statusColor};">${escapeHtml(status)}</span></td>
        </tr>
      `;
      })
      .join("");

    if (DOM.expenseTotal)
      DOM.expenseTotal.textContent = "Total: " + formatCurrency(total);
  }

  // ----- Charts -----
  function renderRevenueProfitChart() {
    const canvas = document.getElementById("revenueProfitChart");
    if (!canvas) return;

    const data = state.data.revenueProfit;
    if (!data || !data.labels) {
      showEmptyChart(canvas, "No revenue data available");
      return;
    }

    const labels = data.labels || [];
    const revenue = data.revenue || [];
    const profit = data.profit || [];

    if (state.charts.revenueProfit) {
      state.charts.revenueProfit.destroy();
    }

    const ctx = canvas.getContext("2d");
    state.charts.revenueProfit = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Revenue",
            data: revenue,
            backgroundColor: "rgba(255, 107, 0, 0.7)",
            borderColor: "#ff6b00",
            borderWidth: 1,
            borderRadius: 4,
          },
          {
            label: "Profit",
            data: profit,
            backgroundColor: "rgba(0, 213, 120, 0.7)",
            borderColor: "#00d578",
            borderWidth: 1,
            borderRadius: 4,
          },
        ],
      },
      options: {
        ...getChartDefaults(),
        plugins: {
          ...getChartDefaults().plugins,
          legend: {
            ...getChartDefaults().plugins.legend,
            position: "top",
          },
        },
        scales: {
          ...getChartDefaults().scales,
          x: { ...getChartDefaults().scales.x, grid: { display: false } },
          y: { ...getChartDefaults().scales.y, beginAtZero: true },
        },
      },
    });
  }

  function renderConversionChart() {
    const canvas = document.getElementById("conversionChart");
    if (!canvas) return;

    const data = state.data.conversion;
    if (!data || !data.labels) {
      showEmptyChart(canvas, "No conversion data available");
      return;
    }

    const labels = data.labels || [];
    const inquiries = data.inquiries || [];
    const converted = data.converted || [];

    if (state.charts.conversion) {
      state.charts.conversion.destroy();
    }

    const ctx = canvas.getContext("2d");
    state.charts.conversion = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Inquiries",
            data: inquiries,
            borderColor: "#3b82f6",
            backgroundColor: "rgba(59, 130, 246, 0.1)",
            fill: true,
            tension: 0.4,
            pointRadius: 3,
            pointBackgroundColor: "#3b82f6",
          },
          {
            label: "Converted",
            data: converted,
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            fill: true,
            tension: 0.4,
            pointRadius: 3,
            pointBackgroundColor: "#10b981",
          },
        ],
      },
      options: {
        ...getChartDefaults(),
        plugins: {
          ...getChartDefaults().plugins,
          legend: {
            ...getChartDefaults().plugins.legend,
            position: "top",
          },
        },
        scales: {
          ...getChartDefaults().scales,
          x: { ...getChartDefaults().scales.x, grid: { display: false } },
          y: {
            ...getChartDefaults().scales.y,
            beginAtZero: true,
            ticks: { stepSize: 1 },
          },
        },
      },
    });
  }

  function renderExpensePieChart() {
    const canvas = document.getElementById("expensePieChart");
    if (!canvas) return;

    const data = state.data.expenseBreakdown;
    if (!data || !data.labels) {
      showEmptyChart(canvas, "No expense data available");
      return;
    }

    const labels = data.labels || [];
    const values = data.values || [];

    if (state.charts.expensePie) {
      state.charts.expensePie.destroy();
    }

    const ctx = canvas.getContext("2d");
    state.charts.expensePie = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            data: values,
            backgroundColor: CHART_COLORS.slice(0, values.length),
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: {
              color: "#94a3b8",
              font: { family: "Inter, sans-serif", size: 11 },
              boxWidth: 12,
              padding: 12,
            },
          },
          tooltip: {
            backgroundColor: "rgba(0,0,0,0.8)",
            titleColor: "#f1f5f9",
            bodyColor: "#94a3b8",
            borderColor: "rgba(255,255,255,0.05)",
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12,
            callbacks: {
              label: function (context) {
                const total = context.dataset.data.reduce(function (a, b) {
                  return a + b;
                }, 0);
                const percentage =
                  total > 0 ? ((context.parsed / total) * 100).toFixed(1) : 0;
                return (
                  context.label +
                  ": " +
                  formatCurrency(context.parsed) +
                  " (" +
                  percentage +
                  "%)"
                );
              },
            },
          },
        },
        cutout: "65%",
      },
    });
  }

  function renderProjectStatusChart() {
    const canvas = document.getElementById("projectStatusChart");
    if (!canvas) return;

    const data = state.data.projectStatus;
    if (!data || !data.labels) {
      showEmptyChart(canvas, "No project status data available");
      return;
    }

    const labels = data.labels || [];
    const values = data.values || [];

    if (state.charts.projectStatus) {
      state.charts.projectStatus.destroy();
    }

    const statusColors = {
      draft: CONFIG.STATUS_COLORS.draft,
      active: CONFIG.STATUS_COLORS.active,
      in_progress: CONFIG.STATUS_COLORS.in_progress,
      on_hold: CONFIG.STATUS_COLORS.on_hold,
      completed: CONFIG.STATUS_COLORS.completed,
      cancelled: CONFIG.STATUS_COLORS.cancelled,
    };

    const colors = labels.map(function (label) {
      return statusColors[label.toLowerCase()] || CONFIG.STATUS_COLORS.draft;
    });

    const ctx = canvas.getContext("2d");
    state.charts.projectStatus = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            data: values,
            backgroundColor: colors,
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: {
              color: "#94a3b8",
              font: { family: "Inter, sans-serif", size: 11 },
              boxWidth: 12,
              padding: 12,
            },
          },
          tooltip: {
            backgroundColor: "rgba(0,0,0,0.8)",
            titleColor: "#f1f5f9",
            bodyColor: "#94a3b8",
            borderColor: "rgba(255,255,255,0.05)",
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12,
            callbacks: {
              label: function (context) {
                const total = context.dataset.data.reduce(function (a, b) {
                  return a + b;
                }, 0);
                const percentage =
                  total > 0 ? ((context.parsed / total) * 100).toFixed(1) : 0;
                return (
                  context.label +
                  ": " +
                  context.parsed +
                  " (" +
                  percentage +
                  "%)"
                );
              },
            },
          },
        },
        cutout: "65%",
      },
    });
  }

  function showEmptyChart(canvas, message) {
    const parent = canvas.parentElement;
    if (!parent) return;

    // Destroy existing chart
    Object.keys(state.charts).forEach(function (key) {
      if (state.charts[key] && state.charts[key].canvas === canvas) {
        state.charts[key].destroy();
        state.charts[key] = null;
      }
    });

    // Remove existing empty message
    const existing = parent.querySelector(".chart-empty");
    if (existing) existing.remove();

    const empty = document.createElement("div");
    empty.className = "chart-empty";
    empty.style.cssText = `
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: var(--text-muted);
      font-size: 0.9rem;
    `;
    empty.textContent = message || "No data available";
    parent.appendChild(empty);
  }

  // ============================================================
  // FILTER & SORT
  // ============================================================
  function filterExpenses() {
    const search = DOM.expenseSearch?.value?.toLowerCase() || "";
    const category = DOM.expenseCategoryFilter?.value || "";
    const rows = DOM.expenseTableBody?.querySelectorAll("tr");
    if (!rows) return;

    rows.forEach(function (row) {
      const text = row.textContent?.toLowerCase() || "";
      const rowCategory =
        row.querySelector("td:nth-child(3)")?.textContent?.toLowerCase() || "";
      const match =
        text.includes(search) && (!category || rowCategory.includes(category));
      row.style.display = match ? "" : "none";
    });
  }

  function sortProfitability() {
    const sort = DOM.profitSortFilter?.value || "profit_desc";
    const body = DOM.profitabilityBody;
    if (!body) return;

    const rows = Array.from(body.querySelectorAll("tr"));
    if (rows.length === 0 || rows[0].classList.contains("no-data")) return;

    const sorted = rows.sort(function (a, b) {
      function getValue(row, index) {
        const cell = row.querySelectorAll("td")[index];
        if (!cell) return 0;
        const text = cell.textContent.replace(/[Rp,.]/g, "").trim();
        const num = parseFloat(text);
        return isNaN(num) ? 0 : num;
      }

      var aVal, bVal;
      switch (sort) {
        case "profit_desc":
          aVal = getValue(a, 4);
          bVal = getValue(b, 4);
          return bVal - aVal;
        case "profit_asc":
          aVal = getValue(a, 4);
          bVal = getValue(b, 4);
          return aVal - bVal;
        case "margin_desc":
          aVal = getValue(a, 5);
          bVal = getValue(b, 5);
          return bVal - aVal;
        case "revenue_desc":
          aVal = getValue(a, 2);
          bVal = getValue(b, 2);
          return bVal - aVal;
        default:
          return 0;
      }
    });

    sorted.forEach(function (row) {
      body.appendChild(row);
    });
  }

  // ============================================================
  // EXPORT
  // ============================================================
  function closeExportModal() {
    if (DOM.exportModal) DOM.exportModal.classList.remove("active");
  }

  function handleExport() {
    const format = DOM.exportFormat?.value || "excel";
    const options = {
      revenue: document.getElementById("exportRevenue")?.checked || false,
      projects: document.getElementById("exportProjects")?.checked || false,
      expenses: document.getElementById("exportExpenses")?.checked || false,
      kpis: document.getElementById("exportKpis")?.checked || false,
    };

    if (
      !options.revenue &&
      !options.projects &&
      !options.expenses &&
      !options.kpis
    ) {
      showToast("Please select at least one data type to export", "warning");
      return;
    }

    // Show loading
    if (DOM.confirmExportBtn) {
      DOM.confirmExportBtn.disabled = true;
      DOM.confirmExportBtn.textContent = "Exporting...";
    }

    // Simulate export
    setTimeout(function () {
      closeExportModal();
      showToast("Export completed! (" + format.toUpperCase() + ")", "success");
      if (DOM.confirmExportBtn) {
        DOM.confirmExportBtn.disabled = false;
        DOM.confirmExportBtn.textContent = "Export";
      }

      if (format === "csv") {
        generateCSV();
      }
    }, 1500);
  }

  function generateCSV() {
    // Simple CSV generation
    var csv = "NOCTRA Analytics Export\n";
    csv += "Date: " + new Date().toISOString() + "\n\n";

    // Add data sections
    if (state.data.profitability && state.data.profitability.length > 0) {
      csv += "Project Profitability\n";
      csv += "Project,Customer,Revenue,Cost,Profit,Margin,Status\n";
      state.data.profitability.forEach(function (p) {
        var revenue = p.revenue || 0;
        var cost = p.cost || 0;
        var profit = revenue - cost;
        var margin = revenue > 0 ? (profit / revenue) * 100 : 0;
        csv +=
          (p.project_name || "Unknown") +
          "," +
          (p.customer_name || "-") +
          "," +
          revenue +
          "," +
          cost +
          "," +
          profit +
          "," +
          margin.toFixed(1) +
          "%," +
          (p.status || "draft") +
          "\n";
      });
      csv += "\n";
    }

    // Download CSV
    var blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download =
      "analytics_export_" + new Date().toISOString().split("T")[0] + ".csv";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  // ============================================================
  // EVENT BINDING
  // ============================================================
  function bindEvents() {
    // Period filter
    if (DOM.periodFilter) {
      DOM.periodFilter.addEventListener("change", function () {
        state.period = this.value;
        if (state.period === "custom") {
          if (DOM.dateRangePicker) DOM.dateRangePicker.style.display = "flex";
          if (DOM.startDate) DOM.startDate.value = "";
          if (DOM.endDate) DOM.endDate.value = "";
        } else {
          if (DOM.dateRangePicker) DOM.dateRangePicker.style.display = "none";
          state.startDate = null;
          state.endDate = null;
          loadAllData();
        }
      });
    }

    // Apply date range
    if (DOM.applyDateRange) {
      DOM.applyDateRange.addEventListener("click", function () {
        var start = DOM.startDate?.value;
        var end = DOM.endDate?.value;
        if (!start || !end) {
          showToast("Please select both start and end dates", "warning");
          return;
        }
        if (new Date(start) > new Date(end)) {
          showToast("Start date must be before end date", "error");
          return;
        }
        state.startDate = start;
        state.endDate = end;
        loadAllData();
      });
    }

    // Refresh button
    if (DOM.refreshBtn) {
      DOM.refreshBtn.addEventListener("click", function () {
        var icon = this.querySelector("i");
        if (icon) {
          icon.style.animation = "spin 0.6s linear";
          setTimeout(function () {
            icon.style.animation = "";
          }, 600);
        }
        loadAllData();
        showToast("Refreshing analytics data...", "info");
      });
    }

    // Export button
    if (DOM.exportBtn) {
      DOM.exportBtn.addEventListener("click", function () {
        if (DOM.exportModal) DOM.exportModal.classList.add("active");
      });
    }

    // Export modal close
    if (DOM.closeExportModal) {
      DOM.closeExportModal.addEventListener("click", closeExportModal);
    }
    if (DOM.cancelExportBtn) {
      DOM.cancelExportBtn.addEventListener("click", closeExportModal);
    }
    if (DOM.exportModal) {
      DOM.exportModal.addEventListener("click", function (e) {
        if (e.target === this) closeExportModal();
      });
    }

    // Confirm export
    if (DOM.confirmExportBtn) {
      DOM.confirmExportBtn.addEventListener("click", handleExport);
    }

    // Expense search
    var searchTimeout;
    if (DOM.expenseSearch) {
      DOM.expenseSearch.addEventListener("input", function () {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(filterExpenses, 300);
      });
    }

    // Expense category filter
    if (DOM.expenseCategoryFilter) {
      DOM.expenseCategoryFilter.addEventListener("change", filterExpenses);
    }

    // Profit sort filter
    if (DOM.profitSortFilter) {
      DOM.profitSortFilter.addEventListener("change", sortProfitability);
    }

    // Chart period controls
    document.querySelectorAll(".chart-period").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var parent = this.closest(".chart-controls");
        if (!parent) return;
        parent.querySelectorAll(".chart-period").forEach(function (b) {
          b.classList.remove("active");
          b.setAttribute("aria-pressed", "false");
        });
        this.classList.add("active");
        this.setAttribute("aria-pressed", "true");

        var chartType = parent.dataset.chart;
        if (chartType === "revenueProfit" || chartType === "conversion") {
          loadAllData();
        }
      });
    });

    // Keyboard shortcuts
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (DOM.exportModal?.classList.contains("active")) {
          closeExportModal();
        }
      }
      if (e.ctrlKey && e.key === "r") {
        e.preventDefault();
        if (DOM.refreshBtn) DOM.refreshBtn.click();
      }
    });

    console.log("✅ Analytics events bound");
  }

  // ============================================================
  // INITIALIZATION
  // ============================================================
  function initAnalytics() {
    console.log("🚀 Initializing Analytics page...");

    if (!document.querySelector(".analytics-toolbar")) {
      console.log("Not on analytics page, skipping initialization");
      return;
    }

    try {
      bindEvents();
      loadAllData();
      console.log("✅ Analytics page initialized successfully");
    } catch (error) {
      console.error("❌ Failed to initialize analytics:", error);
      showToast("Failed to initialize analytics: " + error.message, "error");
    }
  }

  // ============================================================
  // EXPOSE TO GLOBAL
  // ============================================================
  window.initAnalytics = initAnalytics;
  window.loadAnalytics = loadAllData;
  window.refreshAnalytics = loadAllData;

  // ============================================================
  // AUTO-INIT
  // ============================================================
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAnalytics);
  } else {
    initAnalytics();
  }

  console.log("📊 Analytics module loaded");
})();
