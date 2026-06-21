/**
 * NOCTRA Budgeting Dashboard
 * Terintegrasi dengan backend API `/api/budgeting`
 * 
 * Refactored to be modular, maintainable, and performant.
 * All logic is encapsulated in a single class.
 */
(function() {
    'use strict';

    // ─── Constants ──────────────────────────────────────────────
    const PERIOD_LABELS = {
        month: 'This Month',
        last_month: 'Last Month',
        quarter: 'This Quarter',
        year: 'This Year'
    };

    const CHART_COLORS = {
        expense: '#ff7b2c',
        revenue: '#22c55e',
        expenseRed: '#ef4444',
        pie: ['#ff7b2c', '#10b981', '#3b82f6', '#f59e0b', '#8b5cf6']
    };

    // ─── Main Class ──────────────────────────────────────────────
    class BudgetingDashboard {
        // ─── Private fields ──────────────────────────────────────
        #state = {
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

        #dom = {};
        #charts = {
            expense: null,
            pie: null,
            cashflow: null
        };
        #searchDebounceTimer = null;
        #isLoading = false;

        // ─── Constructor ──────────────────────────────────────────
        constructor() {
            this.#cacheDomRefs();
            this.#bindEvents();
            this.#loadData();
        }

        // ─── DOM Caching ──────────────────────────────────────────
        #cacheDomRefs() {
            const ids = [
                'periodFilter',
                'refreshBudget',
                'addExpenseBtn',
                'expenseModal',
                'closeExpenseModal',
                'expenseForm',
                'expenseDate',
                'expenseProject',
                'expenseCategory',
                'expenseDescription',
                'expenseAmount',
                'expenseTable',
                'expenseSearch',
                'expenseFilter',
                'expenseTotal',
                'profitabilityBody',
                'activeProjects',
                'pendingPayments',
                'materialRatio',
                'avgProfit',
                'totalRevenue',
                'totalExpenses',
                'netProfit',
                'cashAvailable',
                'expenseChart',
                'expensePieChart',
                'cashflowChart'
            ];
            const refs = {};
            ids.forEach(id => {
                refs[id] = document.getElementById(id);
            });
            this.#dom = refs;
        }

        // ─── Event Binding ────────────────────────────────────────
        #bindEvents() {
            const { periodFilter, refreshBudget, expenseSearch, expenseFilter } = this.#dom;

            // Period filter
            periodFilter?.addEventListener('change', (e) => {
                this.#state.period = e.target.value;
                this.#loadData();
            });

            // Refresh button
            refreshBudget?.addEventListener('click', () => this.#loadData(true));

            // Search & filter (debounced search)
            expenseSearch?.addEventListener('input', () => {
                clearTimeout(this.#searchDebounceTimer);
                this.#searchDebounceTimer = setTimeout(() => this.#renderExpenses(), 250);
            });
            expenseFilter?.addEventListener('change', () => this.#renderExpenses());

            // Modal setup
            this.#setupModal();
        }

        // ─── Modal Setup ──────────────────────────────────────────
        #setupModal() {
            const { addExpenseBtn, expenseModal, closeExpenseModal, expenseForm } = this.#dom;

            if (!addExpenseBtn || !expenseModal) return;

            // Open modal
            addExpenseBtn.addEventListener('click', () => {
                expenseModal.classList.add('active');
                this.#populateProjectDropdown();
                // Set default date to today
                const dateInput = this.#dom.expenseDate;
                if (dateInput) dateInput.value = new Date().toISOString().slice(0, 10);
            });

            // Close modal
            const closeModal = () => expenseModal.classList.remove('active');
            closeExpenseModal?.addEventListener('click', closeModal);
            expenseModal.addEventListener('click', (e) => {
                if (e.target === expenseModal) closeModal();
            });
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && expenseModal.classList.contains('active')) closeModal();
            });

            // Form submit
            expenseForm?.addEventListener('submit', (e) => this.#handleExpenseSubmit(e));
        }

        // ─── Project Dropdown (lazy load) ────────────────────────
        async #populateProjectDropdown() {
            const select = this.#dom.expenseProject;
            if (!select) return;
            // Avoid re-fetching if already populated
            if (select.dataset.loaded) return;

            try {
                const response = await fetch('/api/projects/');
                if (!response.ok) throw new Error('Failed to load projects');
                const result = await response.json();
                const projects = result.data || [];
                select.innerHTML = '<option value="">Select Project</option>' +
                    projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
                select.dataset.loaded = 'true';
            } catch (err) {
                console.warn('Could not load projects:', err);
                select.innerHTML = '<option value="">Select Project</option>';
            }
        }

        // ─── Data Loading ─────────────────────────────────────────
        async #loadData(forceRefresh = false) {
            if (this.#isLoading) return;
            this.#isLoading = true;

            // Show loading state (optional)
            const skeleton = document.getElementById('loadingSkeleton');
            if (skeleton) skeleton.classList.add('show');

            try {
                const period = this.#state.period;
                // Parallel fetch all endpoints
                const [summary, kpis, monthlyExpenses, expenseBreakdown, cashflow, profitability, expensesData] =
                    await Promise.all([
                        this.#fetchJSON(`/api/budgeting/summary?period=${period}`),
                        this.#fetchJSON(`/api/budgeting/kpis?period=${period}`),
                        this.#fetchJSON(`/api/budgeting/charts/monthly-expenses?period=${period}`),
                        this.#fetchJSON(`/api/budgeting/charts/expense-breakdown?period=${period}`),
                        this.#fetchJSON(`/api/budgeting/charts/cashflow?period=${period}`),
                        this.#fetchJSON(`/api/budgeting/profitability`),
                        this.#fetchJSON(`/api/budgeting/expenses?period=${period}&page=1&limit=100`)
                    ]);

                // Update state
                this.#state.summary = summary;
                this.#state.kpis = kpis;
                this.#state.monthlyExpenses = monthlyExpenses || [];
                this.#state.expenseBreakdown = expenseBreakdown || [];
                this.#state.cashflow = cashflow || [];
                this.#state.profitability = profitability || [];
                this.#state.expenses = expensesData.items || [];
                this.#state.totalExpenses = expensesData.total || 0;
                this.#state.currentPage = expensesData.page || 1;
                this.#state.pageSize = expensesData.page_size || 20;

                // Render everything
                this.#renderAll();
            } catch (err) {
                console.error('Budgeting load error:', err);
                this.#showToast('Failed to load data: ' + err.message, true);
            } finally {
                this.#isLoading = false;
                if (skeleton) skeleton.classList.remove('show');
            }
        }

        // ─── Fetch helper ─────────────────────────────────────────
        async #fetchJSON(url, options = {}) {
            const response = await fetch(url, {
                ...options,
                headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
            });
            if (!response.ok) {
                const errText = await response.text();
                throw new Error(errText || `HTTP ${response.status}`);
            }
            const result = await response.json();
            return result.data;
        }

        // ─── Rendering ────────────────────────────────────────────
        #renderAll() {
            this.#renderSummary();
            this.#renderKPIs();
            this.#renderExpenses();
            this.#renderProfitability();
            this.#renderCharts();
        }

        #renderSummary() {
            const s = this.#state.summary;
            if (!s) return;
            this.#setText('activeProjects', s.active_projects ?? 0);
            this.#setText('pendingPayments', this.#formatCurrency(s.pending_payments ?? 0));
            this.#setText('materialRatio', (s.material_cost_ratio ?? 0) + '%');
            this.#setText('avgProfit', this.#formatCurrency(s.avg_project_profit ?? 0));
        }

        #renderKPIs() {
            const k = this.#state.kpis;
            if (!k) return;
            this.#setText('totalRevenue', this.#formatCurrency(k.revenue ?? 0));
            this.#setText('totalExpenses', this.#formatCurrency(k.expenses ?? 0));
            this.#setText('netProfit', this.#formatCurrency(k.net_profit ?? 0));
            this.#setText('cashAvailable', this.#formatCurrency(k.cash_available ?? 0));
        }

        #renderExpenses() {
            const { expenseTable, expenseSearch, expenseFilter, expenseTotal } = this.#dom;
            if (!expenseTable) return;

            const search = expenseSearch?.value?.toLowerCase() || '';
            const category = expenseFilter?.value || '';

            const filtered = this.#state.expenses.filter(exp => {
                const matchSearch = (exp.description || '').toLowerCase().includes(search) ||
                                    (exp.project_name || '').toLowerCase().includes(search);
                const matchCategory = !category || exp.category === category;
                return matchSearch && matchCategory;
            });

            let total = 0;
            const rows = filtered.map(exp => {
                total += Number(exp.amount);
                return `
                    <tr>
                        <td>${exp.expense_date}</td>
                        <td>${exp.project_name || '—'}</td>
                        <td>${exp.category}</td>
                        <td>${exp.description}</td>
                        <td>${this.#formatCurrency(exp.amount)}</td>
                        <td style="text-align:center;">
                            <button class="btn-delete-expense" data-id="${exp.id}" title="Delete expense">×</button>
                        </td>
                    </tr>
                `;
            }).join('');

            expenseTable.innerHTML = rows || '<tr><td colspan="6" class="text-center">No expenses found</td></tr>';
            if (expenseTotal) expenseTotal.textContent = `Total: ${this.#formatCurrency(total)}`;

            // Attach delete events
            expenseTable.querySelectorAll('.btn-delete-expense').forEach(btn => {
                btn.addEventListener('click', () => {
                    const id = btn.dataset.id;
                    this.#deleteExpense(id);
                });
            });
        }

        #renderProfitability() {
            const body = this.#dom.profitabilityBody;
            if (!body) return;
            const items = this.#state.profitability || [];
            body.innerHTML = items.map(p => {
                const margin = p.margin ?? 0;
                const statusClass = p.status || 'success';
                const statusLabel = statusClass === 'success' ? 'Highly Profitable' :
                                    statusClass === 'warning' ? 'Good' : 'Needs Review';
                return `
                    <tr>
                        <td>${p.project_name}</td>
                        <td>${this.#formatCurrency(p.revenue)}</td>
                        <td>${this.#formatCurrency(p.cost)}</td>
                        <td>${this.#formatCurrency(p.profit)}</td>
                        <td>${margin}%</td>
                        <td><span class="status-badge ${statusClass}">${statusLabel}</span></td>
                    </tr>
                `;
            }).join('');
        }

        // ─── Charts ────────────────────────────────────────────────
        #renderCharts() {
            // Destroy existing charts
            Object.values(this.#charts).forEach(chart => {
                if (chart) { chart.destroy(); }
            });
            this.#charts = { expense: null, pie: null, cashflow: null };

            // Monthly Expense Chart (line)
            const monthlyCtx = this.#dom.expenseChart?.getContext('2d');
            if (monthlyCtx) {
                const data = this.#state.monthlyExpenses || [];
                this.#charts.expense = new Chart(monthlyCtx, {
                    type: 'line',
                    data: {
                        labels: data.map(d => d.month),
                        datasets: [{
                            label: 'Expenses',
                            data: data.map(d => Number(d.amount)),
                            borderColor: CHART_COLORS.expense,
                            backgroundColor: 'rgba(255,123,44,0.1)',
                            fill: true,
                            tension: 0.4,
                            pointRadius: 4
                        }]
                    },
                    options: this.#getLineOptions()
                });
            }

            // Expense Breakdown Pie
            const pieCtx = this.#dom.expensePieChart?.getContext('2d');
            if (pieCtx) {
                const breakdown = this.#state.expenseBreakdown || [];
                this.#charts.pie = new Chart(pieCtx, {
                    type: 'doughnut',
                    data: {
                        labels: breakdown.map(d => `${d.category} (${d.percentage}%)`),
                        datasets: [{
                            data: breakdown.map(d => Number(d.amount)),
                            backgroundColor: CHART_COLORS.pie.slice(0, breakdown.length),
                            borderWidth: 0,
                            hoverOffset: 8
                        }]
                    },
                    options: this.#getPieOptions()
                });
            }

            // Cashflow Bar Chart
            const cashCtx = this.#dom.cashflowChart?.getContext('2d');
            if (cashCtx) {
                const cashflow = this.#state.cashflow || [];
                this.#charts.cashflow = new Chart(cashCtx, {
                    type: 'bar',
                    data: {
                        labels: cashflow.map(d => d.month),
                        datasets: [
                            {
                                label: 'Revenue',
                                data: cashflow.map(d => Number(d.revenue)),
                                backgroundColor: CHART_COLORS.revenue
                            },
                            {
                                label: 'Expenses',
                                data: cashflow.map(d => Number(d.expenses)),
                                backgroundColor: CHART_COLORS.expenseRed
                            }
                        ]
                    },
                    options: this.#getBarOptions()
                });
            }

            // Resize charts after a small delay to ensure container is rendered
            setTimeout(() => {
                Object.values(this.#charts).forEach(chart => {
                    if (chart && chart.resize) chart.resize();
                });
            }, 100);
        }

        #getLineOptions() {
            return {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        ticks: {
                            callback: v => `Rp ${(v / 1e6).toFixed(1)}M`
                        }
                    }
                }
            };
        }

        #getPieOptions() {
            return {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: { legend: { position: 'bottom' } }
            };
        }

        #getBarOptions() {
            return {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } },
                scales: {
                    y: {
                        ticks: {
                            callback: v => `Rp ${(v / 1e6).toFixed(1)}M`
                        }
                    }
                }
            };
        }

        // ─── CRUD ──────────────────────────────────────────────────
        async #deleteExpense(id) {
            if (!confirm('Delete this expense?')) return;
            try {
                await this.#fetchJSON(`/api/budgeting/expenses/${id}`, { method: 'DELETE' });
                this.#showToast('Expense deleted');
                this.#loadData(true);
            } catch (err) {
                this.#showToast('Failed to delete expense: ' + err.message, true);
            }
        }

        async #handleExpenseSubmit(e) {
            e.preventDefault();
            const { expenseDate, expenseProject, expenseCategory, expenseDescription, expenseAmount } = this.#dom;
            const payload = {
                project_id: expenseProject?.value || null,
                category: expenseCategory?.value || '',
                description: expenseDescription?.value.trim() || '',
                amount: parseFloat(expenseAmount?.value || 0),
                expense_date: expenseDate?.value || ''
            };
            if (!payload.category || !payload.amount || !payload.expense_date) {
                this.#showToast('Please fill all required fields', true);
                return;
            }
            try {
                await this.#fetchJSON('/api/budgeting/expenses', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                });
                this.#showToast('Expense added successfully');
                this.#dom.expenseForm?.reset();
                this.#dom.expenseModal?.classList.remove('active');
                this.#loadData(true);
            } catch (err) {
                this.#showToast('Failed to add expense: ' + err.message, true);
            }
        }

        // ─── Helpers ──────────────────────────────────────────────
        #formatCurrency(amount) {
            return 'Rp ' + Number(amount).toLocaleString('id-ID');
        }

        #setText(elementId, value) {
            const el = this.#dom[elementId];
            if (el) el.textContent = value;
        }

        // Toast – fallback to global if exists, else local
        #showToast(message, isError = false) {
            if (typeof window.showToast === 'function') {
                window.showToast(message, isError ? 'error' : 'success');
            } else {
                // Fallback simple toast
                const toast = document.querySelector('.app-toast') || (() => {
                    const el = document.createElement('div');
                    el.className = 'app-toast';
                    document.body.appendChild(el);
                    return el;
                })();
                toast.textContent = message;
                toast.className = 'app-toast' + (isError ? ' error' : '');
                clearTimeout(toast._timeout);
                requestAnimationFrame(() => toast.classList.add('show'));
                toast._timeout = setTimeout(() => toast.classList.remove('show'), 3000);
            }
        }
    }

    // ─── Instantiate ─────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', () => {
        new BudgetingDashboard();
    });

})();