/* FILE: static/js/dashboard.js */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // ---------- REVENUE & PROFIT CHART ----------
    const ctx = document.getElementById('profitChart').getContext('2d');
    
    // Chart data structure
    let currentPeriod = 'week';
    
    // Sample data for different time periods
    const chartData = {
        week: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            revenue: [8.2, 9.1, 7.8, 10.2, 12.5, 14.3, 11.8],
            profit: [2.8, 3.2, 2.5, 3.6, 4.2, 5.1, 3.9]
        },
        month: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            revenue: [32.5, 38.2, 42.8, 48.2],
            profit: [11.2, 13.5, 15.0, 16.8]
        },
        year: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            revenue: [28.4, 30.2, 35.7, 38.9, 42.3, 48.2, 52.1, 55.4, 58.7, 62.3, 65.8, 68.2],
            profit: [9.8, 10.5, 12.1, 13.4, 14.8, 16.8, 18.2, 19.5, 20.8, 22.1, 23.5, 24.2]
        }
    };
    
    // Initialize Chart.js instance
    let profitChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.week.labels,
            datasets: [
                {
                    label: 'Revenue (Rp M)',
                    data: chartData.week.revenue,
                    borderColor: '#ff7b2c',
                    backgroundColor: 'rgba(255, 123, 44, 0.05)',
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#ff7b2c',
                    pointBorderColor: 'white',
                    tension: 0.3,
                    fill: true,
                },
                {
                    label: 'Profit (Rp M)',
                    data: chartData.week.profit,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: 'white',
                    tension: 0.3,
                    fill: true,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        font: { size: 12, weight: '500' }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            let value = context.raw;
                            return `${label}: Rp ${value.toFixed(1)}M`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: '#e2e8f0', drawBorder: false },
                    title: {
                        display: true,
                        text: 'Amount (Rp Million)',
                        font: { size: 11 }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 11 } }
                }
            },
            interaction: { mode: 'nearest', axis: 'x', intersect: false }
        }
    });
    
    // Function to update chart based on period
    function updateChart(period) {
        const data = chartData[period];
        if (!data) return;
        
        profitChart.data.labels = data.labels;
        profitChart.data.datasets[0].data = data.revenue;
        profitChart.data.datasets[1].data = data.profit;
        profitChart.update();
    }
    
    // Attach event listeners to period buttons
    const periodBtns = document.querySelectorAll('.chart-period');
    periodBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            // Update active state
            periodBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Get period and update chart
            const period = this.getAttribute('data-period');
            if (period === 'week') updateChart('week');
            else if (period === 'month') updateChart('month');
            else if (period === 'year') updateChart('year');
        });
    });
    
    // ---------- INVENTORY ALERTS - INTERACTIVE ACTIONS ----------
    // Add sweet interactive feedback for reorder buttons
    const reorderButtons = document.querySelectorAll('.alert-action');
    reorderButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const alertItem = this.closest('.alert-item');
            const itemName = alertItem?.querySelector('.alert-content strong')?.innerText || 'Item';
            
            // Visual feedback
            const originalText = this.innerText;
            this.innerText = '✓ Requested';
            this.style.opacity = '0.7';
            this.disabled = true;
            
            // Show toast-style notification (simple)
            showNotification(`Reorder requested for ${itemName}`, 'success');
            
            // Optional: Reset after 2 seconds if needed, but keep requested state
            setTimeout(() => {
                if (this.innerText === '✓ Requested') {
                    // For demo, you might revert but keeping as requested is better UX
                    // this.innerText = originalText;
                    // this.disabled = false;
                }
            }, 2000);
        });
    });
    
    // Helper function to show temporary notification
    function showNotification(message, type = 'info') {
        // Create notification element if it doesn't exist
        let notifContainer = document.querySelector('.toast-notification-container');
        if (!notifContainer) {
            notifContainer = document.createElement('div');
            notifContainer.className = 'toast-notification-container';
            notifContainer.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 10px;
            `;
            document.body.appendChild(notifContainer);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.style.cssText = `
            background: white;
            color: #1e293b;
            padding: 12px 20px;
            border-radius: 12px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
            font-size: 0.85rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
            border-left: 4px solid ${type === 'success' ? '#10b981' : '#ff7b2c'};
            animation: slideInRight 0.3s ease;
            pointer-events: none;
        `;
        
        const icon = document.createElement('i');
        icon.className = type === 'success' ? 'fas fa-check-circle' : 'fas fa-bell';
        icon.style.color = type === 'success' ? '#10b981' : '#ff7b2c';
        toast.appendChild(icon);
        toast.appendChild(document.createTextNode(message));
        
        notifContainer.appendChild(toast);
        
        // Auto remove after 2.5 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(30px)';
            toast.style.transition = 'all 0.2s';
            setTimeout(() => {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
                if (notifContainer.children.length === 0 && notifContainer.parentNode) {
                    notifContainer.parentNode.removeChild(notifContainer);
                }
            }, 200);
        }, 2500);
    }
    
    // Add keyframe animation for notifications dynamically
    if (!document.querySelector('#toast-keyframes')) {
        const styleSheet = document.createElement('style');
        styleSheet.id = 'toast-keyframes';
        styleSheet.textContent = `
            @keyframes slideInRight {
                from {
                    opacity: 0;
                    transform: translateX(30px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
        `;
        document.head.appendChild(styleSheet);
    }
    
    // ---------- ANIMATE STATS ON LOAD (simple entrance effect) ----------
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(12px)';
        card.style.transition = `opacity 0.3s ease ${index * 0.05}s, transform 0.3s ease ${index * 0.05}s`;
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 50);
    });
    
    // Optional: handle view all link and reorder demo logging
    const viewAllLink = document.querySelector('.view-all-link');
    if (viewAllLink) {
        viewAllLink.addEventListener('click', function(e) {
            e.preventDefault();
            showNotification('Navigate to full projects list (demo)', 'info');
        });
    }
    
    // For chart responsiveness - redraw on window resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (profitChart) profitChart.resize();
        }, 250);
    });
    
    // Optional console log that dashboard loaded
    console.log('NOCTRA Dashboard Enhanced — ready');
});