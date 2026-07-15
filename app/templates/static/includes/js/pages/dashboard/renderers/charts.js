// ============================================================
// dashboard/renderers/charts.js - Chart Management (FIXED)
// ============================================================

import { state } from "../config.js";

const Chart = window.Chart;

export function initCharts() {
  initRevenueChart();
  initProjectStatusChart();
}

export function destroyCharts() {
  if (window.revenueChartInstance) {
    window.revenueChartInstance.destroy();
    window.revenueChartInstance = null;
  }
  if (window.projectStatusChartInstance) {
    window.projectStatusChartInstance.destroy();
    window.projectStatusChartInstance = null;
  }
}

// ============================================================
// Revenue Chart (Line)
// ============================================================

function initRevenueChart() {
  const canvas = document.getElementById("revenueChart");
  if (!canvas) {
    console.warn("revenueChart canvas not found");
    return;
  }

  if (window.revenueChartInstance) {
    window.revenueChartInstance.destroy();
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    console.warn("Failed to get 2D context for revenueChart");
    return;
  }

  const gradient = ctx.createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0, "rgba(255, 107, 0, 0.3)");
  gradient.addColorStop(1, "rgba(255, 107, 0, 0)");

  const labels =
    state.revenueTrend.labels.length > 0
      ? state.revenueTrend.labels
      : ["Jan", "Feb", "Mar", "Apr", "May", "Jun"];

  const data =
    state.revenueTrend.values.length > 0
      ? state.revenueTrend.values
      : [0, 0, 0, 0, 0, 0];

  window.revenueChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Revenue",
          data: data,
          borderColor: "#ff6b00",
          backgroundColor: gradient,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: "#ff6b00",
          pointBorderColor: "#fff",
          pointBorderWidth: 2,
          pointRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (context) {
              return "Rp " + context.parsed.y.toLocaleString("id-ID");
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.05)", drawBorder: false },
          ticks: { color: "#64748b", font: { size: 10 } },
        },
        y: {
          grid: { color: "rgba(255,255,255,0.05)", drawBorder: false },
          ticks: {
            color: "#64748b",
            font: { size: 10 },
            callback: function (value) {
              if (value >= 1_000_000)
                return "Rp" + (value / 1_000_000).toFixed(0) + "M";
              if (value >= 1_000)
                return "Rp" + (value / 1_000).toFixed(0) + "K";
              return "Rp" + value.toLocaleString("id-ID");
            },
          },
        },
      },
    },
  });
}

// ============================================================
// Project Status Chart (Doughnut)
// ============================================================

function initProjectStatusChart() {
  const canvas = document.getElementById("projectStatusChart");
  if (!canvas) {
    console.warn("projectStatusChart canvas not found");
    return;
  }

  if (window.projectStatusChartInstance) {
    window.projectStatusChartInstance.destroy();
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    console.warn("Failed to get 2D context for projectStatusChart");
    return;
  }

  const colors = {
    active: "#3b82f6",
    in_progress: "#f59e0b",
    completed: "#10b981",
    on_hold: "#94a3b8",
    draft: "#64748b",
    cancelled: "#ef4444",
  };

  const labels =
    state.projectStatus.labels.length > 0
      ? state.projectStatus.labels
      : ["Active", "In Progress", "Completed", "On Hold", "Draft"];

  const data =
    state.projectStatus.values.length > 0
      ? state.projectStatus.values
      : [0, 0, 0, 0, 0];

  // Pastikan ada data untuk ditampilkan
  const hasData = data.some((v) => v > 0);
  const chartData = hasData ? data : [1];
  const chartLabels = hasData ? labels : ["No Data"];

  const backgroundColors = chartLabels.map((label) => {
    const key = label.toLowerCase().replace(" ", "_");
    return colors[key] || "#64748b";
  });

  window.projectStatusChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: chartLabels,
      datasets: [
        {
          data: chartData,
          backgroundColor: backgroundColors,
          borderColor: "#141414",
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#cbd5e1",
            font: { size: 10 },
            padding: 8,
            usePointStyle: true,
            pointStyle: "circle",
          },
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage =
                total > 0 ? ((context.parsed / total) * 100).toFixed(0) : 0;
              return `${context.label}: ${context.parsed} (${percentage}%)`;
            },
          },
        },
      },
      cutout: "65%",
    },
  });
}

export function updateRevenueChart(labels, values) {
  state.revenueTrend.labels = labels || state.revenueTrend.labels;
  state.revenueTrend.values = values || state.revenueTrend.values;

  if (window.revenueChartInstance) {
    window.revenueChartInstance.data.labels = state.revenueTrend.labels;
    window.revenueChartInstance.data.datasets[0].data =
      state.revenueTrend.values;
    window.revenueChartInstance.update();
  } else {
    initRevenueChart();
  }
}

export function updateProjectStatusChart(labels, values) {
  state.projectStatus.labels = labels || state.projectStatus.labels;
  state.projectStatus.values = values || state.projectStatus.values;

  if (window.projectStatusChartInstance) {
    window.projectStatusChartInstance.data.labels = state.projectStatus.labels;
    window.projectStatusChartInstance.data.datasets[0].data =
      state.projectStatus.values;
    window.projectStatusChartInstance.update();
  } else {
    initProjectStatusChart();
  }
}
