/* ============================================================
   NOCTRA — Dashboard charts
   Reads data from #dashboard-data (JSON embedded by Jinja)
   and renders Chart.js line + bar charts with the dark theme.
   ============================================================ */
(function () {
  'use strict';

  const COLORS = {
    accent:   '#0ea5e9',   // cyan
    success:  '#10b981',   // green
    danger:   '#ef4444',
    border:   'rgba(148,163,184,0.08)',
    surface2: '#111827',
    muted:    '#64748b',
    text:     '#f1f5f9',
  };

  function readData() {
    const el = document.getElementById('dashboard-data');
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (err) {
      console.error('dashboard-data parse failed', err);
      return null;
    }
  }

  function formatRupiah(n) {
    if (n == null) return 'Rp 0';
    const s = Math.round(Number(n)).toString();
    return 'Rp ' + s.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function formatCompact(n) {
    const v = Math.abs(Number(n) || 0);
    if (v >= 1_000_000_000) return 'Rp ' + (n / 1_000_000_000).toFixed(1) + 'M';
    if (v >= 1_000_000)     return 'Rp ' + (n / 1_000_000).toFixed(1) + 'jt';
    if (v >= 1_000)         return 'Rp ' + (n / 1_000).toFixed(0) + 'k';
    return 'Rp ' + n;
  }

  function shortDate(iso) {
    // "2026-10-01" → "01 Oct"
    const d = new Date(iso + 'T00:00:00');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return String(d.getDate()).padStart(2, '0') + ' ' + months[d.getMonth()];
  }

  function initRevenueChart(data) {
    const canvas = document.getElementById('revenueChart');
    if (!canvas) return;

    const labels = (data.periods || []).map(shortDate);
    const revenue = data.revenue || [];
    const gp = data.gross_profit || [];

    new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Revenue',
            data: revenue,
            borderColor: COLORS.accent,
            backgroundColor: 'rgba(249,115,22,0.08)',
            borderWidth: 2,
            tension: 0.35,
            pointRadius: 3,
            pointHoverRadius: 5,
            pointBackgroundColor: COLORS.accent,
            fill: true,
          },
          {
            label: 'Gross profit',
            data: gp,
            borderColor: COLORS.success,
            backgroundColor: 'rgba(34,197,94,0.08)',
            borderWidth: 2,
            tension: 0.35,
            pointRadius: 3,
            pointHoverRadius: 5,
            pointBackgroundColor: COLORS.success,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: COLORS.surface2,
            borderColor: COLORS.border,
            borderWidth: 1,
            titleColor: COLORS.text,
            bodyColor: COLORS.text,
            padding: 12,
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${formatRupiah(ctx.parsed.y)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: 'rgba(38,38,38,0.5)', drawBorder: false },
            ticks: { color: COLORS.muted, font: { size: 11 } },
          },
          y: {
            grid: { color: 'rgba(38,38,38,0.5)', drawBorder: false },
            ticks: {
              color: COLORS.muted,
              font: { size: 11 },
              callback: (v) => formatCompact(v),
            },
            beginAtZero: true,
          },
        },
      },
    });
  }

  function initCashFlowChart(data) {
    const canvas = document.getElementById('cashFlowChart');
    if (!canvas) return;

    const labels = (data.cash_periods || []).map(shortDate);
    const inflow = data.cash_in || [];
    const outflow = data.cash_out || [];

    new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'In',
            data: inflow,
            backgroundColor: 'rgba(34,197,94,0.65)',
            borderColor: COLORS.success,
            borderWidth: 1,
            borderRadius: 3,
          },
          {
            label: 'Out',
            data: outflow,
            backgroundColor: 'rgba(239,68,68,0.65)',
            borderColor: COLORS.danger,
            borderWidth: 1,
            borderRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
            labels: {
              color: COLORS.muted,
              font: { size: 11 },
              boxWidth: 10,
              boxHeight: 10,
              padding: 12,
            },
          },
          tooltip: {
            backgroundColor: COLORS.surface2,
            borderColor: COLORS.border,
            borderWidth: 1,
            titleColor: COLORS.text,
            bodyColor: COLORS.text,
            padding: 12,
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${formatRupiah(ctx.parsed.y)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: COLORS.muted, font: { size: 11 } },
          },
          y: {
            grid: { color: 'rgba(38,38,38,0.5)', drawBorder: false },
            ticks: {
              color: COLORS.muted,
              font: { size: 11 },
              callback: (v) => formatCompact(v),
            },
            beginAtZero: true,
          },
        },
      },
    });
  }

  function init() {
    if (typeof Chart === 'undefined') {
      console.warn('Chart.js not loaded — dashboard charts skipped');
      return;
    }

    // Global Chart.js defaults for the dark theme
    Chart.defaults.color = COLORS.muted;
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;

    const data = readData();
    if (!data) return;

    initRevenueChart(data);
    initCashFlowChart(data);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();