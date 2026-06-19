/**
 * NOCTRA Budgeting Dashboard
 * Terintegrasi dengan backend API `/api/budgeting`
 */
(function() {
    'use strict';

    // ============================================================
    // STATE
    // ============================================================
    const state = {
        period: 'month',
        expenses: [],
        totalExpenses: 0,
        summary: null,
        kpis: null,
        monthlyExpenses: [],
        expenseBreakdown: [],
        cashflow: [],
        profitability: [],
        currentPage: 1,
        pageSize: 20
    };

    // ============================================================
    // DOM REFS
    // ============================================================
    const dom = {
        periodFilter: document.getElementById('periodFilter'),
        refreshBtn: document.getElementById('refreshBudget'),
        addExpenseBtn: document.getElementById('addExpenseBtn'),
        expenseModal: document.getElementById('expenseModal'),
        closeModal: document.getElementById('closeExpenseModal'),
        expenseForm: document.getElementById('expenseForm'),
        expenseDate: document.getElementById('expenseDate'),
        expenseProject: document.getElementById('expenseProject'),
        expenseCategory: document.getElementById('expenseCategory'),
        expenseDescription: document.getElementById('expenseDescription'),
        expenseAmount: document.getElementById('expenseAmount'),
        expenseTable: document.getElementById('expenseTable'),
        expenseSearch: document.getElementById('expenseSearch'),
        expenseFilter: document.getElementById('expenseFilter'),
        expenseTotal: document.getElementById('expenseTotal'),
        profitabilityBody: document.getElementById('profitabilityBody'),
        // Summary elements
        activeProjects: document.getElementById('activeProjects'),
        pendingPayments: document.getElementById('pendingPayments'),
        materialRatio: document.getElementById('materialRatio'),
        avgProfit: document.getElementById('avgProfit'),
        // KPI elements
        totalRevenue: document.getElementById('totalRevenue'),
        totalExpensesKpi: document.getElementById('totalExpenses'),
        netProfit: document.getElementById('netProfit'),
        cashAvailable: document.getElementById('cashAvailable')
    };

    // Chart instances
    let expenseChart, expensePieChart, cashflowChart;

    // ============================================================
    // HELPERS
    // ============================================================
    function formatCurrency(amount) {
        return 'Rp ' + Number(amount).toLocaleString('id-ID');
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

    function getPeriodLabel(period) {
        const map = {
            month: 'This Month',
            last_month: 'Last Month',
            quarter: 'This Quarter',
            year: 'This Year'
        };
        return map[period] || period;
    }

    // ============================================================
    // API FETCH
    // ============================================================
    async function fetchJSON(url, options = {}) {
        const res = await fetch(url, {
            ...options,
            headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
        });
        if (!res.ok) {
            const err = await res.text();
            throw new Error(err || `HTTP ${res.status}`);
        }
        const result = await res.json();
        return result.data;
    }

    async function loadAllData(period) {
        try {
            // Load all data in parallel
            const [summary, kpis, monthlyExpenses, expenseBreakdown, cashflow, profitability, expensesData] = await Promise.all([
                fetchJSON(`/api/budgeting/summary?period=${period}`),
                fetchJSON(`/api/budgeting/kpis?period=${period}`),
                fetchJSON(`/api/budgeting/charts/monthly-expenses?period=${period}`),
                fetchJSON(`/api/budgeting/charts/expense-breakdown?period=${period}`),
                fetchJSON(`/api/budgeting/charts/cashflow?period=${period}`),
                fetchJSON(`/api/budgeting/profitability`),
                fetchJSON(`/api/budgeting/expenses?period=${period}&page=1&limit=100`)
            ]);

            state.summary = summary;
            state.kpis = kpis;
            state.monthlyExpenses = monthlyExpenses || [];
            state.expenseBreakdown = expenseBreakdown || [];
            state.cashflow = cashflow || [];
            state.profitability = profitability || [];
            state.expenses = expensesData.items || [];
            state.totalExpenses = expensesData.total || 0;
            state.currentPage = expensesData.page || 1;
            state.pageSize = expensesData.page_size || 20;

            renderAll();
            return true;
        } catch (err) {
            console.error('Failed to load budgeting data:', err);
            showToast('Failed to load data: ' + err.message, true);
            return false;
        }
    }

    // ============================================================
    // RENDER FUNCTIONS
    // ============================================================

    function renderAll() {
        renderSummary();
        renderKPIs();
        renderExpenses();
        renderProfitability();
        renderCharts();
    }

    function renderSummary() {
        const s = state.summary;
        if (!s) return;
        dom.activeProjects.textContent = s.active_projects || 0;
        dom.pendingPayments.textContent = formatCurrency(s.pending_payments || 0);
        dom.materialRatio.textContent = (s.material_cost_ratio || 0) + '%';
        dom.avgProfit.textContent = formatCurrency(s.avg_project_profit || 0);
    }

    function renderKPIs() {
        const k = state.kpis;
        if (!k) return;
        dom.totalRevenue.textContent = formatCurrency(k.revenue || 0);
        dom.totalExpensesKpi.textContent = formatCurrency(k.expenses || 0);
        dom.netProfit.textContent = formatCurrency(k.net_profit || 0);
        dom.cashAvailable.textContent = formatCurrency(k.cash_available || 0);
    }

    function renderExpenses() {
        const filtered = filterExpenses();
        dom.expenseTable.innerHTML = '';
        let total = 0;
        filtered.forEach(exp => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${exp.expense_date}</td>
                <td>${exp.project_name || '—'}</td>
                <td>${exp.category}</td>
                <td>${exp.description}</td>
                <td>${formatCurrency(exp.amount)}</td>
                <td style="text-align:center;">
                    <button class="btn-delete-expense" data-id="${exp.id}" title="Delete expense">×</button>
                </td>
            `;
            dom.expenseTable.appendChild(row);
            total += Number(exp.amount);
        });
        dom.expenseTotal.textContent = `Total: ${formatCurrency(total)}`;

        // Delete event listeners
        dom.expenseTable.querySelectorAll('.btn-delete-expense').forEach(btn => {
            btn.addEventListener('click', function() {
                const id = this.dataset.id;
                deleteExpense(id);
            });
        });
    }

    function filterExpenses() {
        const search = dom.expenseSearch.value.toLowerCase();
        const category = dom.expenseFilter.value;
        return state.expenses.filter(exp => {
            const matchSearch = (exp.description || '').toLowerCase().includes(search) ||
                                (exp.project_name || '').toLowerCase().includes(search);
            const matchCategory = !category || exp.category === category;
            return matchSearch && matchCategory;
        });
    }

    function renderProfitability() {
        const items = state.profitability || [];
        dom.profitabilityBody.innerHTML = items.map(p => {
            const margin = p.margin || 0;
            const statusClass = p.status || 'success';
            return `
                <tr>
                    <td>${p.project_name}</td>
                    <td>${formatCurrency(p.revenue)}</td>
                    <td>${formatCurrency(p.cost)}</td>
                    <td>${formatCurrency(p.profit)}</td>
                    <td>${margin}%</td>
                    <td><span class="status-badge ${statusClass}">${statusClass === 'success' ? 'Highly Profitable' : statusClass === 'warning' ? 'Good' : 'Needs Review'}</span></td>
                </tr>
            `;
        }).join('');
    }

    // ============================================================
    // CHARTS
    // ============================================================

    function renderCharts() {
        // Destroy existing charts if any
        if (expenseChart) { expenseChart.destroy(); expenseChart = null; }
        if (expensePieChart) { expensePieChart.destroy(); expensePieChart = null; }
        if (cashflowChart) { cashflowChart.destroy(); cashflowChart = null; }

        // Monthly Expense Chart (line)
        const ctx1 = document.getElementById('expenseChart').getContext('2d');
        const monthlyData = state.monthlyExpenses || [];
        expenseChart = new Chart(ctx1, {
            type: 'line',
            data: {
                labels: monthlyData.map(d => d.month),
                datasets: [{
                    label: 'Expenses',
                    data: monthlyData.map(d => Number(d.amount)),
                    borderColor: '#ff7b2c',
                    backgroundColor: 'rgba(255,123,44,0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4
                }]
            },
            options: getLineOptions()
        });

        // Expense Breakdown Pie
        const ctx2 = document.getElementById('expensePieChart').getContext('2d');
        const breakdown = state.expenseBreakdown || [];
        expensePieChart = new Chart(ctx2, {
            type: 'doughnut',
            data: {
                labels: breakdown.map(d => `${d.category} (${d.percentage}%)`),
                datasets: [{
                    data: breakdown.map(d => Number(d.amount)),
                    backgroundColor: ['#ff7b2c', '#10b981', '#3b82f6', '#f59e0b', '#8b5cf6'],
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: getPieOptions()
        });

        // Cashflow Bar Chart
        const ctx3 = document.getElementById('cashflowChart').getContext('2d');
        const cashflowData = state.cashflow || [];
        cashflowChart = new Chart(ctx3, {
            type: 'bar',
            data: {
                labels: cashflowData.map(d => d.month),
                datasets: [
                    { label: 'Revenue', data: cashflowData.map(d => Number(d.revenue)), backgroundColor: '#22c55e' },
                    { label: 'Expenses', data: cashflowData.map(d => Number(d.expenses)), backgroundColor: '#ef4444' }
                ]
            },
            options: getBarOptions()
        });
    }

    function getLineOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => `Rp ${ctx.raw.toLocaleString()}`
                    }
                }
            },
            scales: {
                y: {
                    ticks: { callback: v => `Rp ${(v/1000000).toFixed(1)}M` }
                }
            }
        };
    }

    function getPieOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: { position: 'bottom' }
            }
        };
    }

    function getBarOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' }
            },
            scales: {
                y: {
                    ticks: { callback: v => `Rp ${(v/1000000).toFixed(1)}M` }
                }
            }
        };
    }

    // ============================================================
    // CRUD OPERATIONS
    // ============================================================

    async function deleteExpense(id) {
        if (!confirm('Delete this expense?')) return;
        try {
            await fetchJSON(`/api/budgeting/expenses/${id}`, { method: 'DELETE' });
            showToast('Expense deleted');
            loadAllData(state.period);
        } catch (err) {
            showToast('Failed to delete expense', true);
        }
    }

    async function handleExpenseSubmit(e) {
        e.preventDefault();
        const payload = {
            project_id: dom.expenseProject.value || null,
            category: dom.expenseCategory.value,
            description: dom.expenseDescription.value.trim(),
            amount: parseFloat(dom.expenseAmount.value),
            expense_date: dom.expenseDate.value
        };
        if (!payload.category || !payload.amount) {
            showToast('Please fill all required fields', true);
            return;
        }
        try {
            await fetchJSON('/api/budgeting/expenses', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            showToast('Expense added successfully');
            dom.expenseForm.reset();
            dom.expenseModal.classList.remove('active');
            loadAllData(state.period);
        } catch (err) {
            showToast('Failed to add expense', true);
        }
    }

    // ============================================================
    // EVENT HANDLERS
    // ============================================================

    function setupModal() {
        dom.addExpenseBtn.addEventListener('click', () => {
            dom.expenseModal.classList.add('active');
            dom.expenseDate.value = new Date().toISOString().slice(0,10);
            // Load projects for dropdown
            fetch('/api/projects/')
                .then(res => res.json())
                .then(data => {
                    const projects = data.data || [];
                    dom.expenseProject.innerHTML = '<option value="">Select Project</option>' +
                        projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
                })
                .catch(() => {
                    dom.expenseProject.innerHTML = '<option value="">Select Project</option>';
                });
        });
        dom.closeModal.addEventListener('click', () => dom.expenseModal.classList.remove('active'));
        dom.expenseModal.addEventListener('click', e => {
            if (e.target === dom.expenseModal) dom.expenseModal.classList.remove('active');
        });
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') dom.expenseModal.classList.remove('active');
        });
        dom.expenseForm.addEventListener('submit', handleExpenseSubmit);
    }

    function setupFilters() {
        dom.periodFilter.addEventListener('change', function() {
            state.period = this.value;
            loadAllData(state.period);
        });
        dom.expenseSearch.addEventListener('input', renderExpenses);
        dom.expenseFilter.addEventListener('change', renderExpenses);
        dom.refreshBtn.addEventListener('click', function() {
            loadAllData(state.period);
        });
    }

    // ============================================================
    // INIT
    // ============================================================
    async function init() {
        setupModal();
        setupFilters();
        await loadAllData(state.period);
        // Resize charts after initial render
        setTimeout(() => {
            if (expenseChart) expenseChart.resize();
            if (expensePieChart) expensePieChart.resize();
            if (cashflowChart) cashflowChart.resize();
        }, 200);
    }

    document.addEventListener('DOMContentLoaded', init);
})();