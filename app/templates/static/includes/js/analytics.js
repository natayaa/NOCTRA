document.addEventListener('DOMContentLoaded', function() {
    
    // Helper function untuk resize observer (opsional)
    function initializeChart(ctx, config) {
        return new Chart(ctx, config);
    }
    
    // ========== 1. REVENUE VS PROFIT CHART ==========
    const revCanvas = document.getElementById('revenueProfitChart');
    if (revCanvas) {
        const revCtx = revCanvas.getContext('2d');
        
        const revenueProfitData = {
            week: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                revenue: [8.2, 9.1, 7.8, 10.2, 12.5, 14.3, 11.8],
                profit: [5.2, 5.9, 5.0, 6.6, 8.1, 9.3, 7.7]
            },
            month: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                revenue: [32.5, 38.2, 42.8, 48.2],
                profit: [21.1, 24.8, 27.8, 31.4]
            },
            year: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                revenue: [28.4, 30.2, 35.7, 38.9, 42.3, 48.2, 52.1, 55.4, 58.7, 62.3, 65.8, 68.2],
                profit: [18.5, 19.6, 23.2, 25.3, 27.5, 31.4, 33.9, 36.0, 38.2, 40.5, 42.8, 44.3]
            }
        };
        
        let revenueProfitChart = initializeChart(revCtx, {
            type: 'line',
            data: {
                labels: revenueProfitData.week.labels,
                datasets: [
                    {
                        label: 'Revenue (Rp M)',
                        data: revenueProfitData.week.revenue,
                        borderColor: '#ff7b2c',
                        backgroundColor: 'transparent',
                        borderWidth: 2.5,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        pointBackgroundColor: '#ff7b2c',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        tension: 0.2,
                        fill: false
                    },
                    {
                        label: 'Profit (Rp M)',
                        data: revenueProfitData.week.profit,
                        borderColor: '#10b981',
                        backgroundColor: 'transparent',
                        borderWidth: 2.5,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        tension: 0.2,
                        fill: false
                    }
                ]
            },
            options: getLineChartOptions('Amount (Rp Million)')
        });
        
        // Simpan chart dan data ke global scope untuk update nanti
        window.revenueProfitChart = revenueProfitChart;
        window.revenueProfitData = revenueProfitData;
    }
    
    // ========== 2. INQUIRY CONVERSION CHART ==========
    const convCanvas = document.getElementById('conversionChart');
    if (convCanvas) {
        const convCtx = convCanvas.getContext('2d');
        
        const conversionData = {
            week: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                inquiries: [12, 15, 10, 18, 22, 8, 6],
                conversions: [8, 11, 7, 14, 18, 5, 4]
            },
            month: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                inquiries: [45, 52, 48, 61],
                conversions: [32, 38, 35, 48]
            },
            year: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                inquiries: [42, 48, 55, 62, 71, 85, 92, 88, 79, 73, 68, 91],
                conversions: [30, 35, 41, 47, 55, 67, 73, 70, 62, 58, 54, 72]
            }
        };
        
        let conversionChart = initializeChart(convCtx, {
            type: 'line',
            data: {
                labels: conversionData.week.labels,
                datasets: [
                    {
                        label: 'Inquiries',
                        data: conversionData.week.inquiries,
                        borderColor: '#3b82f6',
                        backgroundColor: 'transparent',
                        borderWidth: 2.5,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        pointBackgroundColor: '#3b82f6',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        tension: 0.2,
                        fill: false
                    },
                    {
                        label: 'Conversions',
                        data: conversionData.week.conversions,
                        borderColor: '#f59e0b',
                        backgroundColor: 'transparent',
                        borderWidth: 2.5,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        pointBackgroundColor: '#f59e0b',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        tension: 0.2,
                        fill: false
                    }
                ]
            },
            options: getLineChartOptions('Count')
        });
        
        window.conversionChart = conversionChart;
        window.conversionData = conversionData;
    }
    
    // ========== 3. SERVICE BREAKDOWN PIE CHART ==========
    const serviceCanvas = document.getElementById('serviceChart');
    if (serviceCanvas) {
        const serviceCtx = serviceCanvas.getContext('2d');
        let serviceChart = new Chart(serviceCtx, {
            type: 'doughnut',
            data: {
                labels: ['Full Restoration (38%)', 'Repaint (32%)', 'Custom Design (18%)', 'Ceramic Coating (12%)'],
                datasets: [{
                    data: [38, 32, 18, 12],
                    backgroundColor: ['#ff7b2c', '#10b981', '#3b82f6', '#f59e0b'],
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: getPieChartOptions()
        });
        window.serviceChart = serviceChart;
    }
    
    // ========== 4. MATERIAL CONSUMPTION PIE CHART ==========
    const materialCanvas = document.getElementById('materialChart');
    if (materialCanvas) {
        const materialCtx = materialCanvas.getContext('2d');
        let materialChart = new Chart(materialCtx, {
            type: 'doughnut',
            data: {
                labels: ['Paint (45%)', 'Primer (25%)', 'Clear Coat (18%)', 'Sandpaper (12%)'],
                datasets: [{
                    data: [45, 25, 18, 12],
                    backgroundColor: ['#ff7b2c', '#10b981', '#3b82f6', '#f59e0b'],
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: getPieChartOptions()
        });
        window.materialChart = materialChart;
    }
    
    // Helper function untuk line chart options
    function getLineChartOptions(yAxisLabel) {
        return {
            responsive: true,
            maintainAspectRatio: false,  // Kunci: ini harus false agar chart mengikuti container
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        boxHeight: 8,
                        font: { size: 11, weight: '500' },
                        padding: 12,
                        color: '#475569'
                    }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f1f5f9',
                    bodyColor: '#cbd5e1',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            let value = context.raw;
                            return `${label}: ${value.toLocaleString()}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: '#e2e8f0', drawBorder: false, lineWidth: 1 },
                    border: { display: false },
                    ticks: { font: { size: 11 }, color: '#64748b' },
                    title: {
                        display: true,
                        text: yAxisLabel,
                        font: { size: 11, weight: '500' },
                        color: '#64748b',
                        padding: { bottom: 8 }
                    }
                },
                x: {
                    grid: { display: false },
                    border: { display: false },
                    ticks: { font: { size: 11 }, color: '#64748b' }
                }
            },
            interaction: { mode: 'index', intersect: false }
        };
    }
    
    function getPieChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,  // Kunci: false agar pie chart tidak collapse
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
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw;
                            return `${label}: ${value}%`;
                        }
                    }
                }
            },
            cutout: '60%',
            radius: '80%'
        };
    }
    
    // ========== PERIOD SWITCHING FUNCTIONALITY ==========
    function updateRevenueProfitChart(period) {
        if (window.revenueProfitChart && window.revenueProfitData) {
            const data = window.revenueProfitData[period];
            if (data) {
                window.revenueProfitChart.data.labels = data.labels;
                window.revenueProfitChart.data.datasets[0].data = data.revenue;
                window.revenueProfitChart.data.datasets[1].data = data.profit;
                window.revenueProfitChart.update();
            }
        }
    }
    
    function updateConversionChart(period) {
        if (window.conversionChart && window.conversionData) {
            const data = window.conversionData[period];
            if (data) {
                window.conversionChart.data.labels = data.labels;
                window.conversionChart.data.datasets[0].data = data.inquiries;
                window.conversionChart.data.datasets[1].data = data.conversions;
                window.conversionChart.update();
            }
        }
    }
    
    // Attach event listeners to all period buttons
    const periodButtons = document.querySelectorAll('.chart-period');
    periodButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const period = this.getAttribute('data-period');
            const chartType = this.getAttribute('data-chart');
            
            const parentControls = this.closest('.chart-controls');
            if (parentControls) {
                parentControls.querySelectorAll('.chart-period').forEach(b => {
                    b.classList.remove('active');
                });
                this.classList.add('active');
            }
            
            if (chartType === 'revenueProfit') {
                updateRevenueProfitChart(period);
            } else if (chartType === 'conversion') {
                updateConversionChart(period);
            }
        });
    });
    
    // ========== FORCE RESIZE AFTER LOAD (SOLUSI UNTUK CHART JATUH) ==========
    setTimeout(function() {
        if (window.revenueProfitChart) window.revenueProfitChart.resize();
        if (window.conversionChart) window.conversionChart.resize();
        if (window.serviceChart) window.serviceChart.resize();
        if (window.materialChart) window.materialChart.resize();
    }, 100);
    
    // ========== RESIZE HANDLER ==========
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (window.revenueProfitChart) window.revenueProfitChart.resize();
            if (window.conversionChart) window.conversionChart.resize();
            if (window.serviceChart) window.serviceChart.resize();
            if (window.materialChart) window.materialChart.resize();
        }, 250);
    });
    
    // ========== ANIMATION ON LOAD ==========
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, idx) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(12px)';
        card.style.transition = `opacity 0.3s ease ${idx * 0.05}s, transform 0.3s ease ${idx * 0.05}s`;
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 50);
    });
    
    console.log('NOCTRA Analytics Dashboard — Clean charts initialized');
});