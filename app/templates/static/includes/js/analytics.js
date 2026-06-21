/**
 * NOCTRA Analytics Dashboard
 * Terintegrasi dengan backend API `/api/analytics/full`
 * 
 * Refactored to be more modular, maintainable, and efficient.
 * All functionality is encapsulated within a single class.
 */
(function() {
    'use strict';

    // ============================================================
    // CONSTANTS & HELPERS
    // ============================================================
    const PERIOD_LABELS = {
        today: 'Today',
        week: 'This Week',
        month: 'This Month',
        quarter: 'Last 3 Months',
        year: 'This Year'
    };

    const CHART_COLORS = {
        revenue: '#ff7b2c',
        profit: '#10b981',
        inquiries: '#3b82f6',
        conversions: '#f59e0b'
    };

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
        return PERIOD_LABELS[period] || period;
    }

    function showToast(msg, isError = false) {
        const toast = document.querySelector('.app-toast') || (() => {
            const el = document.createElement('div');
            el.className = 'app-toast';
            document.body.appendChild(el);
            return el;
        })();
        toast.textContent = msg;
        toast.className = 'app-toast' + (isError ? ' error' : '');
        clearTimeout(toast._timeout);
        requestAnimationFrame(() => toast.classList.add('show'));
        toast._timeout = setTimeout(() => toast.classList.remove('show'), 3000);
    }

    // ============================================================
    // DASHBOARD CLASS (modular core)
    // ============================================================
    class Dashboard {
        // Private fields
        #state = {
            period: 'week',
            chartPeriod: {
                revenueProfit: 'week',
                conversion: 'week'
            },
            data: null,
            isLoading: false
        };

        #dom = {};
        #chartInstances = {
            revenueProfit: null,
            conversion: null,
            service: null,
            material: null
        };

        // ─── Constructor ──────────────────────────────────────────
        constructor() {
            this.#cacheDomRefs();
            this.#bindEvents();
        }

        // ─── DOM Caching ──────────────────────────────────────────
        #cacheDomRefs() {
            const ids = [
                'periodFilter',
                'refreshAnalytics',
                'lastUpdated',
                'statsGrid',
                'insightGrid',
                'loadingSkeleton',
                'topServicesBody',
                'kpiList',
                'revenueProfitChart',
                'conversionChart',
                'serviceChart',
                'materialChart'
            ];
            const refs = {};
            ids.forEach(id => {
                refs[id] = document.getElementById(id);
            });
            // Additional elements by class/data attributes can be added here.
            this.#dom = refs;
        }

        // ─── Event Binding ────────────────────────────────────────
        #bindEvents() {
            // Global period filter
            this.#dom.periodFilter?.addEventListener('change', (e) => {
                this.#state.period = e.target.value;
                // Reset chart period buttons to default (week)
                this.#resetChartPeriodButtons();
                this.#loadData();
            });

            // Refresh button
            this.#dom.refreshAnalytics?.addEventListener('click', () => {
                this.#loadData(true);
            });

            // Chart period buttons (if they exist)
            document.querySelectorAll('.chart-controls').forEach(container => {
                const chartType = container.dataset.chart;
                container.querySelectorAll('.chart-period').forEach(btn => {
                    btn.addEventListener('click', () => {
                        container.querySelectorAll('.chart-period')
                            .forEach(b => b.classList.remove('active'));
                        btn.classList.add('active');
                        const period = btn.dataset.period;
                        this.#state.chartPeriod[chartType] = period;
                        // Reload data – note: currently only global period is sent to API.
                        // Chart period buttons only update UI; if you want to filter data,
                        // you need to implement that logic on the backend or frontend.
                        // For now, we refresh the chart with the same data.
                        this.#loadData(false);
                    });
                });
            });
        }

        #resetChartPeriodButtons() {
            document.querySelectorAll('.chart-controls').forEach(c => {
                c.querySelectorAll('.chart-period').forEach(b => {
                    const isWeek = b.dataset.period === 'week';
                    b.classList.toggle('active', isWeek);
                    if (isWeek) {
                        const chartType = c.dataset.chart;
                        this.#state.chartPeriod[chartType] = 'week';
                    }
                });
            });
        }

        // ─── API ──────────────────────────────────────────────────
        async #fetchAnalytics(period) {
            const response = await fetch(`/api/analytics/full?period=${period}`);
            if (!response.ok) {
                const err = await response.text();
                throw new Error(err || `HTTP ${response.status}`);
            }
            const result = await response.json();
            return result.data; // backend returns { success, data, ... }
        }

        // ─── Main Load ────────────────────────────────────────────
        async #loadData(forceRefresh = false) {
            if (this.#state.isLoading) return;
            this.#state.isLoading = true;

            // Show skeleton
            const skeleton = this.#dom.loadingSkeleton;
            const statsGrid = this.#dom.statsGrid;
            const insightGrid = this.#dom.insightGrid;
            if (skeleton) skeleton.classList.add('show');
            if (statsGrid) statsGrid.style.display = 'none';
            if (insightGrid) insightGrid.style.display = 'none';

            try {
                const data = await this.#fetchAnalytics(this.#state.period);
                this.#state.data = data;

                // Render all sections
                this.#renderKPIs(data.kpis);
                this.#renderInsights(data.insights?.items || []);
                this.#renderTopServices(data.top_services?.items || []);
                this.#renderOperationalKPIs(data.operational_kpis?.items || []);

                // Charts – initialize or update
                if (!this.#chartInstances.revenueProfit) {
                    this.#initCharts(data);
                } else {
                    this.#updateCharts(data);
                }

                // Update timestamp
                if (this.#dom.lastUpdated) {
                    this.#dom.lastUpdated.textContent = 'Last updated: ' + new Date().toLocaleTimeString();
                }
            } catch (err) {
                console.error('Analytics load error:', err);
                showToast('Failed to load analytics: ' + err.message, true);
            } finally {
                this.#state.isLoading = false;
                if (skeleton) skeleton.classList.remove('show');
                if (statsGrid) statsGrid.style.display = 'grid';
                if (insightGrid) insightGrid.style.display = 'grid';
            }
        }

        // ─── Renderers ────────────────────────────────────────────
        #renderKPIs(kpis) {
            // Revenue
            const revenue = kpis.total_revenue;
            this.#setText('totalRevenue', formatCurrency(revenue.value));
            this.#setTrend('revenueTrend', revenue.trend_percent);

            // Profit
            const profit = kpis.net_profit;
            this.#setText('netProfit', formatCurrency(profit.value));
            this.#setTrend('profitTrend', profit.trend_percent);

            // Conversion Rate
            const conv = kpis.conversion_rate;
            this.#setText('conversionRate', formatPercent(conv.value));
            this.#setTrend('conversionTrend', conv.trend_percent);

            // Completed Projects
            const completed = kpis.completed_projects;
            this.#setText('completedProjects', completed.value);
            this.#setTrend('completedTrend', completed.trend_percent);
        }

        #setText(elementId, value) {
            const el = document.getElementById(elementId);
            if (el) el.textContent = value;
        }

        #setTrend(elementId, value) {
            const el = document.getElementById(elementId);
            if (!el) return;
            const num = value ?? 0;
            const sign = num >= 0 ? '+' : '';
            el.textContent = sign + (Number.isInteger(num) ? num : num.toFixed(1)) + '%';
            el.className = 'stat-trend ' + (num >= 0 ? 'positive' : 'negative');
        }

        #renderInsights(insights) {
            const container = this.#dom.insightGrid;
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

        #renderTopServices(services) {
            const body = this.#dom.topServicesBody;
            if (!body) return;
            if (!services || services.length === 0) {
                body.innerHTML = `<tr><td colspan="4" class="text-center">No data</td></tr>`;
                return;
            }
            body.innerHTML = services.map(s => {
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

        #renderOperationalKPIs(kpis) {
            const container = this.#dom.kpiList;
            if (!container) return;
            if (!kpis || kpis.length === 0) {
                container.innerHTML = '<p class="text-center">No KPIs available</p>';
                return;
            }
            container.innerHTML = kpis.map(k => `
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

        // ─── Charts ────────────────────────────────────────────────
        #initCharts(data) {
            this.#chartInstances.revenueProfit = this.#createLineChart(
                this.#dom.revenueProfitChart,
                data.revenue_profit,
                'Revenue (Rp M)',
                'profit',
                CHART_COLORS.revenue,
                CHART_COLORS.profit
            );

            this.#chartInstances.conversion = this.#createLineChart(
                this.#dom.conversionChart,
                data.conversion,
                'Count',
                'conversions',
                CHART_COLORS.inquiries,
                CHART_COLORS.conversions
            );

            // Service Breakdown (doughnut)
            this.#chartInstances.service = this.#createDoughnutChart(
                this.#dom.serviceChart,
                data.service_breakdown?.items || [],
                '#ff7b2c'
            );

            // Material Consumption (doughnut)
            this.#chartInstances.material = this.#createDoughnutChart(
                this.#dom.materialChart,
                data.material_consumption?.items || [],
                '#10b981'
            );
        }

        #updateCharts(data) {
            // Update line charts
            this.#updateLineChart(this.#chartInstances.revenueProfit, data.revenue_profit);
            this.#updateLineChart(this.#chartInstances.conversion, data.conversion);
            // Doughnut charts: data is static for the period, but if needed we can update them.
            // For simplicity, we can destroy and recreate if data changes significantly.
            // However, the current implementation does not change pie data on period change,
            // so we skip updating them.
        }

        #createLineChart(canvas, chartData, yLabel, datasetKey, color1, color2) {
            if (!canvas) return null;
            const ctx = canvas.getContext('2d');
            const periodData = chartData?.data || [];
            return new Chart(ctx, {
                type: 'line',
                data: {
                    labels: periodData.map(d => d.label),
                    datasets: [
                        {
                            label: chartData?.label1 || 'Dataset 1',
                            data: periodData.map(d => d[Object.keys(d)[1]]), // dynamic; but we'll fix
                            borderColor: color1,
                            backgroundColor: 'transparent',
                            borderWidth: 2.5,
                            pointRadius: 3,
                            tension: 0.2
                        },
                        {
                            label: chartData?.label2 || 'Dataset 2',
                            data: periodData.map(d => d[Object.keys(d)[2]]), // dynamic
                            borderColor: color2,
                            backgroundColor: 'transparent',
                            borderWidth: 2.5,
                            pointRadius: 3,
                            tension: 0.2
                        }
                    ]
                },
                options: this.#getLineChartOptions(yLabel)
            });
        }

        #updateLineChart(chartInstance, chartData) {
            if (!chartInstance) return;
            const periodData = chartData?.data || [];
            // Update labels and datasets
            chartInstance.data.labels = periodData.map(d => d.label);
            // Assuming datasets are in the same order: first dataset is the second key (revenue/inquiries), second is third key (profit/conversions)
            const keys = Object.keys(periodData[0] || {});
            const key1 = keys[1] || 'value1';
            const key2 = keys[2] || 'value2';
            chartInstance.data.datasets[0].data = periodData.map(d => d[key1]);
            chartInstance.data.datasets[1].data = periodData.map(d => d[key2]);
            chartInstance.update();
        }

        #createDoughnutChart(canvas, items, defaultColor) {
            if (!canvas) return null;
            const ctx = canvas.getContext('2d');
            return new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: items.map(i => `${i.name} (${i.value}%)`),
                    datasets: [{
                        data: items.map(i => i.value),
                        backgroundColor: items.map(i => i.color || defaultColor),
                        borderWidth: 0,
                        hoverOffset: 8
                    }]
                },
                options: this.#getPieChartOptions()
            });
        }

        #getLineChartOptions(yLabel) {
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
                            text: yLabel,
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

        #getPieChartOptions() {
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

        // ─── Public initializer ──────────────────────────────────
        init() {
            this.#loadData();
        }
    }

    // ============================================================
    // INSTANTIATE AND RUN
    // ============================================================
    document.addEventListener('DOMContentLoaded', () => {
        const dashboard = new Dashboard();
        dashboard.init();
    });

})();