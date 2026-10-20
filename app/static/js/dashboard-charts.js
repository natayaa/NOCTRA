/* ============================================================
   NOCTRA — Dashboard charts
   ============================================================ */
(function () {
  'use strict';

  const COLORS = {
    accent:   '#0ea5e9',
    accentBg: 'rgba(14,165,233,0.12)',
    success:  '#10b981',
    successBg: 'rgba(16,185,129,0.12)',
    danger:   '#ef4444',
    border:   'rgba(148,163,184,0.06)',
    surface2: '#111827',
    muted:    '#64748b',
    text:     '#f1f5f9',
  };

  function readData() {
    const el = document.getElementById('dashboard-data');
    if (!el) return null;
    try { return JSON.parse(el.textContent); }
    catch (err) { console.error('dashboard-data parse failed', err); return null; }
  }

  function formatRupiah(n) {
    if (n == null) return 'Rp 0';
    return 'Rp ' + Math.round(Number(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function formatCompact(n) {
    const v = Math.abs(Number(n) || 0);
    if (v >= 1_000_000_000) return 'Rp ' + (n / 1_000_000_000).toFixed(1) + 'M';
    if (v >= 1_000_000)     return 'Rp ' + (n / 1_000_000).toFixed(1) + 'jt';
    if (v >= 1_000)         return 'Rp ' + (n / 1_000).toFixed(0) + 'k';
    return 'Rp ' + n;
  }

  function shortDate(iso) {
    const d = new Date(iso + 'T00:00:00');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return String(d.getDate()).padStart(2, '0') + ' ' + months[d.getMonth()];
    /* ← baris "ccccccc" penyebab SyntaxError sudah dihapus */
  }

  function linearGradient(ctx, hexRgb) {
    const g = ctx.createLinearGradient(0, 0, 0, 280);
    g.addColorStop(0, hexRgb.replace('RGBA', 'rgba'));
    g.addColorStop(1, hexRgb.replace(/,[\d.]+\)$/, ',0)'));
    return g;
  }

  function initRevenueChart(data) {
    const canvas = document.getElementById('revenueChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const fillAccent = ctx.createLinearGradient(0, 0, 0, 280);
    fillAccent.addColorStop(0, 'rgba(14,165,233,0.18)');
    fillAccent.addColorStop(1, 'rgba(14,165,233,0)');

    const fillSuccess = ctx.createLinearGradient(0, 0, 0, 280);
    fillSuccess.addColorStop(0, 'rgba(16,185,129,0.15)');
    fillSuccess.addColorStop(1, 'rgba(16,185,129,0)');

    new Chart(ctx, {
      type: 'line',
      data: {
        labels: (data.periods || []).map(shortDate),
        datasets: [
          {
            label: 'Revenue',
            data: data.revenue || [],
            borderColor: COLORS.accent,
            backgroundColor: fillAccent,
            borderWidth: 2,
            tension: 0.35,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: COLORS.accent,
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 2,
            fill: true,
          },
          {
            label: 'Gross profit',
            data: data.gross_profit || [],
            borderColor: COLORS.success,
            backgroundColor: fillSuccess,
            borderWidth: 2,
            tension: 0.35,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: COLORS.success,
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 2,
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
            borderColor: 'rgba(148,163,184,0.16)',
            borderWidth: 1,
            titleColor: COLORS.text,
            bodyColor: COLORS.text,
            padding: 12,
            cornerRadius: 8,
            titleFont: { size: 12, weight: '600' },
            bodyFont: { size: 12 },
            callbacks: {
              label: (c) => ` ${c.dataset.label}: ${formatRupiah(c.parsed.y)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: { color: COLORS.muted, font: { size: 11 }, maxRotation: 0 },
          },
          y: {
            grid: { color: COLORS.border },
            border: { display: false },
            ticks: {
              color: COLORS.muted,
              font: { size: 11 },
              callback: (v) => formatCompact(v),
              padding: 8,
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

    new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: (data.cash_periods || []).map(shortDate),
        datasets: [
          {
            label: 'In',
            data: data.cash_in || [],
            backgroundColor: 'rgba(16,185,129,0.75)',
            hoverBackgroundColor: COLORS.success,
            borderRadius: 4,
            borderSkipped: false,
          },
          {
            label: 'Out',
            data: data.cash_out || [],
            backgroundColor: 'rgba(239,68,68,0.75)',
            hoverBackgroundColor: COLORS.danger,
            borderRadius: 4,
            borderSkipped: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: COLORS.muted,
              font: { size: 11 },
              boxWidth: 8,
              boxHeight: 8,
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 14,
            },
          },
          tooltip: {
            backgroundColor: COLORS.surface2,
            borderColor: 'rgba(148,163,184,0.16)',
            borderWidth: 1,
            titleColor: COLORS.text,
            bodyColor: COLORS.text,
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              label: (c) => ` ${c.dataset.label}: ${formatRupiah(c.parsed.y)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: { color: COLORS.muted, font: { size: 11 }, maxRotation: 0 },
          },
          y: {
            grid: { color: COLORS.border },
            border: { display: false },
            ticks: {
              color: COLORS.muted,
              font: { size: 11 },
              callback: (v) => formatCompact(v),
              padding: 8,
            },
            beginAtZero: true,
          },
        },
      },
    });
  }

  function init() {
    if (typeof Chart === 'undefined') return;
    Chart.defaults.color = COLORS.muted;
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.font.size = 12;

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