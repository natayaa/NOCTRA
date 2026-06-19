/**
 * NOCTRA Analytics Dashboard
 * Terintegrasi dengan backend API `/api/analytics/full`
 */
(function() {
    'use strict';

    // ============================================================
    // STATE
    // ============================================================
    const state = {
        period: 'week',          // today, week, month, quarter, year
        chartPeriod: {
            revenueProfit: 'week',
            conversion: 'week'
        },
        data: null,              // full data from backend
        isLoading: false
    };

    // ============================================================
    // DOM REFS
    // ============================================================
    const dom = {
        periodFilter: document.getElementById('periodFilter'),
        refreshBtn: document.getElementById('refreshAnalytics'),
        lastUpdated: document.getElementById('lastUpdated'),
        statsGrid: document.getElementById('statsGrid'),
        insightGrid: document.getElementById('insightGrid'),
        skeleton: document.getElementById('loadingSkeleton'),
        topServicesBody: document.getElementById('topServicesBody'),
        kpiList: document.getElementById('kpiList'),
        revenueProfitChart: document.getElementById('revenueProfitChart'),
        conversionChart: document.getElementById('conversionChart'),
        serviceChart: document.getElementById('serviceChart'),
        materialChart: document.getElementById('materialChart')
    };

    // ============================================================
    // HELPERS
    // ============================================================
    function formatCurrency(amount) {
        return 'Rp ' + Number(amount).toLocaleString('id-ID');
    }

    function formatCurrencyM(amount) {
        const num = Number(amount);
        if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(0) + 'K';
        return formatCurrency(num);
    }

    function formatPercent(value) {
        return Number(value).toFixed(1) + '%';
    }

    function getPeriodLabel(period) {
        const map = {
            today: 'Today',
            week: 'This Week',
            month: 'This Month',
            quarter: 'Last 3 Months',
            year: 'This Year'
        };
        return map[period] || period;
    }

    function showToast(msg, isError = false) {
        const t = document.querySelector('.app-toast') || (() => {
            const el = document.createElement('div');
            el.className = 'app-toast';
            document.body.appendChild(el);
            return el;
        })();
        t.textContent = msg;
        t.className = 'app-toast' + (isError ? ' error' : '');
        setTimeout(() => t.classList.add('show'), 10);
        clearTimeout(t._timeout);
        t._timeout = setTimeout(() => t.classList.remove('show'), 3000);
    }

    // ============================================================
    // API FETCH
    // ============================================================
    async function fetchAnalyticsData(period) {
        const response = await fetch(`/api/analytics/full?period=${period}`);
        if (!response.ok) {
            const err = await response.text();
            throw new Error(err || `HTTP ${response.status}`);
        }
        const result = await response.json();
        // Backend mengembalikan BaseResponse dengan data di dalamnya
        return result.data;
    }

    // ============================================================
    // RENDER FUNCTIONS
    // ============================================================

    function renderKPIs(kpis) {
        // Revenue
        const revenue = kpis.total_revenue;
        document.getElementById('totalRevenue').textContent = formatCurrency(revenue.value);
        const revTrend = revenue.trend_percent ?? 0;
        document.getElementById('revenueTrend').textContent = (revTrend >= 0 ? '+' : '') + revTrend.toFixed(1) + '%';
        document.getElementById('revenueTrend').className = 'stat-trend ' + (revTrend >= 0 ? 'positive' : 'negative');

        // Profit
        const profit = kpis.net_profit;
        document.getElementById('netProfit').textContent = formatCurrency(profit.value);
        const profitTrend = profit.trend_percent ?? 0;
        document.getElementById('profitTrend').textContent = (profitTrend >= 0 ? '+' : '') + profitTrend.toFixed(1) + '%';
        document.getElementById('profitTrend').className = 'stat-trend ' + (profitTrend >= 0 ? 'positive' : 'negative');

        // Conversion Rate
        const conv = kpis.conversion_rate;
        document.getElementById('conversionRate').textContent = formatPercent(conv.value);
        const convTrend = conv.trend_percent ?? 0;
        document.getElementById('conversionTrend').textContent = (convTrend >= 0 ? '+' : '') + convTrend.toFixed(1) + '%';
        document.getElementById('conversionTrend').className = 'stat-trend ' + (convTrend >= 0 ? 'positive' : 'negative');

        // Completed Projects
        const completed = kpis.completed_projects;
        document.getElementById('completedProjects').textContent = completed.value;
        const compTrend = completed.trend_percent ?? 0;
        document.getElementById('completedTrend').textContent = (compTrend >= 0 ? '+' : '') + compTrend;
        document.getElementById('completedTrend').className = 'stat-trend ' + (compTrend >= 0 ? 'positive' : 'negative');
    }

    function renderInsights(insights) {
        const container = dom.insightGrid;
        if (!container) return;
        if (!insights || insights.length === 0) {
            container.innerHTML = `<div class="insight-card neutral">
                <div class="insight-icon"><i class="fas fa-info-circle"></i></div>
                <div class="insight-content"><p>No insights available</p></div>
            </div>`;
            return;
        }
        container.innerHTML = insights.map(item => `
            <div class="insight-card ${item.type}">
                <div class="insight-icon"><i class="fas ${item.icon}"></i></div>
                <div class="insight-content">
                    <p>${item.message}</p>
                    ${item.link ? `<a href="${item.link}" class="insight-link">View →</a>` : ''}
                </div>
            </div>
        `).join('');
    }

    function renderTopServices(services) {
        if (!dom.topServicesBody) return;
        if (!services || services.length === 0) {
            dom.topServicesBody.innerHTML = `<tr><td colspan="4" class="text-center">No data</td></tr>`;
            return;
        }
        dom.topServicesBody.innerHTML = services.map(s => {
            const trend = s.trend ?? 0;
            const trendClass = trend >= 0 ? 'trend-up' : 'trend-down';
            const arrow = trend >= 0 ? '↑' : '↓';
            return `
                <tr>
                    <td>${s.name}</td>
                    <td>${s.projects}</td>
                    <td>${formatCurrency(s.revenue)}</td>
                    <td><span class="${trendClass}">${arrow} ${Math.abs(trend).toFixed(1)}%</span></td>
                </tr>
            `;
        }).join('');
    }

    function renderOperationalKPIs(kpis) {
        if (!dom.kpiList) return;
        if (!kpis || kpis.length === 0) {
            dom.kpiList.innerHTML = '<p class="text-center">No KPIs available</p>';
            return;
        }
        dom.kpiList.innerHTML = kpis.map(k => `
            <div class="kpi-item">
                <div class="kpi-info">
                    <span>${k.label}</span>
                    <strong>${k.value}</strong>
                </div>
                <div class="kpi-progress">
                    <div class="progress-bar ${k.color || ''}" style="width: ${Math.min(k.progress || 0, 100)}%;"></div>
                </div>
            </div>
        `).join('');
    }

    // ============================================================
    // CHARTS
    // ============================================================
    let revenueProfitChart = null;
    let conversionChart = null;
    let serviceChart = null;
    let materialChart = null;

    function initCharts(data) {
        // Revenue vs Profit
        if (dom.revenueProfitChart) {
            const ctx = dom.revenueProfitChart.getContext('2d');
            const chartData = data.revenue_profit;
            const periodData = chartData.data || [];
            revenueProfitChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: periodData.map(d => d.label),
                    datasets: [
                        {
                            label: 'Revenue (Rp M)',
                            data: periodData.map(d => d.revenue),
                            borderColor: '#ff7b2c',
                            backgroundColor: 'transparent',
                            borderWidth: 2.5,
                            pointRadius: 3,
                            tension: 0.2
                        },
                        {
                            label: 'Profit (Rp M)',
                            data: periodData.map(d => d.profit),
                            borderColor: '#10b981',
                            backgroundColor: 'transparent',
                            borderWidth: 2.5,
                            pointRadius: 3,
                            tension: 0.2
                        }
                    ]
                },
                options: getLineChartOptions('Amount (Rp Million)')
            });
        }

        // Conversion
        if (dom.conversionChart) {
            const ctx = dom.conversionChart.getContext('2d');
            const chartData = data.conversion;
            const periodData = chartData.data || [];
            conversionChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: periodData.map(d => d.label),
                    datasets: [
                        {
                            label: 'Inquiries',
                            data: periodData.map(d => d.inquiries),
                            borderColor: '#3b82f6',
                            backgroundColor: 'transparent',
                            borderWidth: 2.5,
                            pointRadius: 3,
                            tension: 0.2
                        },
                        {
                            label: 'Conversions',
                            data: periodData.map(d => d.conversions),
                            borderColor: '#f59e0b',
                            backgroundColor: 'transparent',
                            borderWidth: 2.5,
                            pointRadius: 3,
                            tension: 0.2
                        }
                    ]
                },
                options: getLineChartOptions('Count')
            });
        }

        // Service Breakdown (doughnut)
        if (dom.serviceChart) {
            const ctx = dom.serviceChart.getContext('2d');
            const items = data.service_breakdown?.items || [];
            serviceChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: items.map(i => `${i.name} (${i.value}%)`),
                    datasets: [{
                        data: items.map(i => i.value),
                        backgroundColor: items.map(i => i.color || '#ff7b2c'),
                        borderWidth: 0,
                        hoverOffset: 8
                    }]
                },
                options: getPieChartOptions()
            });
        }

        // Material Consumption
        if (dom.materialChart) {
            const ctx = dom.materialChart.getContext('2d');
            const items = data.material_consumption?.items || [];
            materialChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: items.map(i => `${i.name} (${i.value}%)`),
                    datasets: [{
                        data: items.map(i => i.value),
                        backgroundColor: items.map(i => i.color || '#10b981'),
                        borderWidth: 0,
                        hoverOffset: 8
                    }]
                },
                options: getPieChartOptions()
            });
        }
    }

    function updateCharts(data) {
        // Update revenue-profit
        if (revenueProfitChart) {
            const chartData = data.revenue_profit;
            const periodData = chartData.data || [];
            revenueProfitChart.data.labels = periodData.map(d => d.label);
            revenueProfitChart.data.datasets[0].data = periodData.map(d => d.revenue);
            revenueProfitChart.data.datasets[1].data = periodData.map(d => d.profit);
            revenueProfitChart.update();
        }

        // Update conversion
        if (conversionChart) {
            const chartData = data.conversion;
            const periodData = chartData.data || [];
            conversionChart.data.labels = periodData.map(d => d.label);
            conversionChart.data.datasets[0].data = periodData.map(d => d.inquiries);
            conversionChart.data.datasets[1].data = periodData.map(d => d.conversions);
            conversionChart.update();
        }

        // Pie charts tidak perlu update karena data statis (tidak bergantung period)
    }

    function getLineChartOptions(yAxisLabel) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        font: { size: 11 },
                        padding: 12
                    }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f1f5f9',
                    bodyColor: '#cbd5e1',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    border: { display: false },
                    ticks: { font: { size: 11 } },
                    title: {
                        display: true,
                        text: yAxisLabel,
                        font: { size: 11 },
                        padding: { bottom: 8 }
                    }
                },
                x: {
                    grid: { display: false },
                    border: { display: false },
                    ticks: { font: { size: 11 } }
                }
            },
            interaction: { mode: 'index', intersect: false }
        };
    }

    function getPieChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: { size: 11 },
                        padding: 12,
                        usePointStyle: true,
                        boxWidth: 8
                    }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    callbacks: {
                        label: ctx => `${ctx.label}: ${ctx.raw}%`
                    }
                }
            },
            cutout: '60%',
            radius: '80%'
        };
    }

    // ============================================================
    // PERIOD SWITCHING (chart internal)
    // ============================================================
    function setupPeriodButtons() {
        document.querySelectorAll('.chart-controls').forEach(container => {
            const chartType = container.dataset.chart;
            container.querySelectorAll('.chart-period').forEach(btn => {
                btn.addEventListener('click', function() {
                    container.querySelectorAll('.chart-period').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    const period = this.dataset.period;
                    state.chartPeriod[chartType] = period;
                    // Reload data with new period for the specific chart
                    loadAnalytics(false);
                });
            });
        });
    }

    // ============================================================
    // GLOBAL PERIOD FILTER
    // ============================================================
    function setupPeriodFilter() {
        dom.periodFilter.addEventListener('change', function() {
            state.period = this.value;
            // Reset chart period to default
            state.chartPeriod.revenueProfit = 'week';
            state.chartPeriod.conversion = 'week';
            // Reset active states on chart buttons
            document.querySelectorAll('.chart-controls').forEach(c => {
                c.querySelectorAll('.chart-period').forEach(b => {
                    b.classList.toggle('active', b.dataset.period === 'week');
                });
            });
            loadAnalytics();
        });
    }

    // ============================================================
    // REFRESH
    // ============================================================
    dom.refreshBtn.addEventListener('click', function() {
        loadAnalytics(true);
    });

    // ============================================================
    // MAIN LOAD FUNCTION
    // ============================================================
    async function loadAnalytics(forceRefresh = false) {
        if (state.isLoading) return;
        state.isLoading = true;
        dom.skeleton.classList.add('show');
        dom.statsGrid.style.display = 'none';
        dom.insightGrid.style.display = 'none';

        try {
            const data = await fetchAnalyticsData(state.period);
            state.data = data;

            // Render all sections
            renderKPIs(data.kpis);
            renderInsights(data.insights?.items || []);
            renderTopServices(data.top_services?.items || []);
            renderOperationalKPIs(data.operational_kpis?.items || []);

            // Charts
            if (!revenueProfitChart) {
                initCharts(data);
            } else {
                updateCharts(data);
            }

            dom.lastUpdated.textContent = 'Last updated: ' + new Date().toLocaleTimeString();
        } catch (err) {
            console.error('Failed to load analytics:', err);
            showToast('Failed to load analytics data: ' + err.message, true);
        } finally {
            state.isLoading = false;
            dom.skeleton.classList.remove('show');
            dom.statsGrid.style.display = 'grid';
            dom.insightGrid.style.display = 'grid';
        }
    }

    // ============================================================
    // INIT
    // ============================================================
    function init() {
        setupPeriodFilter();
        setupPeriodButtons();
        loadAnalytics();
    }

    document.addEventListener('DOMContentLoaded', init);
})();