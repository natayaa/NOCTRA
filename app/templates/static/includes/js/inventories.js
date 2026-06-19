/* =========================================================
   inventories.js – Full Inventory Management with Project Integration
   ========================================================= */

// ---------------------------------------------------------
// State
// ---------------------------------------------------------
let inventoryData = [];
let selectedInventoryId = null;
let isSubmitting = false;

// ---------------------------------------------------------
// DOM Refs
// ---------------------------------------------------------
const tbody = document.getElementById('inventoryItemsList');
const searchInput = document.getElementById('searchInventory');
const categoryFilter = document.getElementById('categoryFilter');
const stockFilter = document.getElementById('stockFilter');
const totalValueEl = document.getElementById('totalValue');
const totalItemsEl = document.getElementById('totalItems');
const lowStockCountEl = document.getElementById('lowStockCount');

// Modal refs
const modal = document.getElementById('inventoryModal');
const modalTitle = document.getElementById('modalTitle');
const editId = document.getElementById('editId');
const itemName = document.getElementById('itemName');
const itemCategory = document.getElementById('itemCategory');
const itemStock = document.getElementById('itemStock');
const itemUnit = document.getElementById('itemUnit');
const itemCost = document.getElementById('itemCost');
const reorderLevel = document.getElementById('reorderLevel');
const itemSupplier = document.getElementById('itemSupplier');
const inventoryForm = document.getElementById('inventoryForm');

// Detail panel refs
const detailContent = document.getElementById('itemDetailContent');
const editItemBtn = document.getElementById('editItemBtn');
const deleteItemBtn = document.getElementById('deleteItemBtn');
const detailActionsBottom = document.getElementById('detailActionsBottom');
const reorderBtn = document.getElementById('reorderBtn');
const historyBtn = document.getElementById('historyBtn');

// ---------------------------------------------------------
// Helpers
// ---------------------------------------------------------
function formatCurrency(value) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        maximumFractionDigits: 0
    }).format(value || 0);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

function getStockStatus(item) {
    const threshold = item.min_stock_threshold || 0;
    const criticalLevel = Math.floor(threshold / 2);
    if (item.current_stock <= criticalLevel && threshold > 0) {
        return { label: 'Critical', className: 'status-critical' };
    }
    if (item.current_stock <= threshold && threshold > 0) {
        return { label: 'Low Stock', className: 'status-low' };
    }
    return { label: 'Normal', className: 'status-normal' };
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) {
        // Create container if it doesn't exist
        const newContainer = document.createElement('div');
        newContainer.id = 'toastContainer';
        newContainer.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 99999;
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-width: 400px;
        `;
        document.body.appendChild(newContainer);
        return showToast(message, type);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.style.cssText = `
        padding: 12px 18px;
        border-radius: 12px;
        background: ${type === 'error' ? '#7f1d1d' : '#111827'};
        color: #fff;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        transform: translateX(100%);
        opacity: 0;
        transition: all 0.3s ease;
    `;
    toast.textContent = message;
    container.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
        toast.style.transform = 'translateX(0)';
        toast.style.opacity = '1';
    });

    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ---------------------------------------------------------
// API Helpers
// ---------------------------------------------------------
async function fetchJSON(url, options = {}) {
    const res = await fetch(url, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    if (!res.ok) {
        const err = await res.text();
        throw new Error(err || res.statusText);
    }
    return res.json();
}

// ---------------------------------------------------------
// Load Data
// ---------------------------------------------------------
async function loadInventoryItems() {
    try {
        const data = await fetchJSON('/api/inventory/');
        inventoryData = data.data || [];
        renderTable(inventoryData);
        applyFilters();
    } catch (err) {
        console.error('Failed to load inventory:', err);
        showToast('Error loading inventory', 'error');
        tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">Error loading inventory</td></tr>`;
    }
}

async function loadDashboardStats() {
    try {
        const [kpis, usage, alerts] = await Promise.all([
            fetchJSON('/api/inventory/dashboard/kpis'),
            fetchJSON('/api/inventory/dashboard/monthly-usage'),
            fetchJSON('/api/inventory/alerts')
        ]);

        if (kpis.data) {
            totalValueEl.textContent = formatCurrency(kpis.data.total_value || 0);
            totalItemsEl.textContent = kpis.data.total_skus || 0;
            lowStockCountEl.textContent = kpis.data.low_stock_count || 0;
        }

        if (usage.data) {
            const usageEl = document.querySelector('.overview-card.usage h2');
            if (usageEl) usageEl.textContent = formatCurrency(usage.data.monthly_usage || 0);
        }

        if (alerts.data) {
            renderAlerts(alerts.data);
        }
    } catch (err) {
        console.error('Failed to load dashboard stats:', err);
    }
}

async function loadRecentMovements() {
    try {
        const data = await fetchJSON('/api/inventory/movement/recent');
        const container = document.querySelector('.movement-list');
        if (!container) return;
        container.innerHTML = '';
        if (!data.data || data.data.length === 0) {
            container.innerHTML = '<div style="color:var(--gray-500);font-size:0.85rem;">No recent movements</div>';
            return;
        }
        data.data.slice(0, 5).forEach(move => {
            const div = document.createElement('div');
            div.className = `movement-item ${move.type === 'in' ? 'stock-in' : 'stock-out'}`;
            const icon = move.type === 'in' ? 'fa-arrow-down' : 'fa-arrow-up';
            div.innerHTML = `
                <i class="fas ${icon}"></i>
                <div>
                    <strong>${move.type === 'in' ? '+' : '-'}${move.quantity}</strong>
                    <small>${escapeHtml(move.item_name || 'Unknown')}</small>
                </div>
            `;
            container.appendChild(div);
        });
    } catch (err) {
        console.error('Failed to load movements:', err);
    }
}

// ---------------------------------------------------------
// Render Table
// ---------------------------------------------------------
function renderTable(items) {
    if (!tbody) return;
    if (!items || items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">No inventory items found</td></tr>`;
        return;
    }

    tbody.innerHTML = items.map(item => {
        const status = getStockStatus(item);
        const totalValue = item.current_stock * item.cost_price;
        return `
            <tr data-id="${item.id}">
                <td><strong>${escapeHtml(item.name)}</strong></td>
                <td>${escapeHtml(item.category)}</td>
                <td>${item.current_stock}</td>
                <td>${escapeHtml(item.unit)}</td>
                <td><span class="${status.className}">${status.label}</span></td>
                <td>${formatCurrency(totalValue)}</td>
                <td>
                    <button class="table-view-btn" data-id="${item.id}" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Attach view button events
    document.querySelectorAll('.table-view-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            showItemDetails(id);
        });
    });

    // Click row to view details
    tbody.querySelectorAll('tr').forEach(row => {
        row.addEventListener('click', () => {
            const id = row.dataset.id;
            if (id) showItemDetails(id);
        });
    });
}

// ---------------------------------------------------------
// Render Alerts
// ---------------------------------------------------------
function renderAlerts(alerts) {
    const container = document.querySelector('.alert-list');
    if (!container) return;
    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<div class="alert-item" style="color:var(--gray-500);">✅ All items are well stocked</div>';
        return;
    }
    container.innerHTML = alerts.map(alert => `
        <div class="alert-item ${alert.status === 'critical' ? 'critical' : 'warning'}">
            <div>
                <strong>${escapeHtml(alert.name)}</strong>
                <span>${escapeHtml(alert.category)} • Stock: ${alert.current_stock}</span>
            </div>
            <span class="alert-badge">${alert.status === 'critical' ? 'Critical' : 'Low Stock'}</span>
        </div>
    `).join('');
}

// ---------------------------------------------------------
// Filters
// ---------------------------------------------------------
function applyFilters() {
    const keyword = searchInput?.value.toLowerCase().trim() || '';
    const category = categoryFilter?.value || '';
    const stockStatus = stockFilter?.value || '';

    let filtered = [...inventoryData];

    if (keyword) {
        filtered = filtered.filter(item =>
            item.name.toLowerCase().includes(keyword) ||
            item.category.toLowerCase().includes(keyword)
        );
    }
    if (category) {
        filtered = filtered.filter(item => item.category === category);
    }
    if (stockStatus) {
        filtered = filtered.filter(item => {
            const threshold = item.min_stock_threshold || 0;
            const criticalLevel = Math.floor(threshold / 2);
            if (stockStatus === 'critical') return item.current_stock <= criticalLevel && threshold > 0;
            if (stockStatus === 'low') return item.current_stock <= threshold && item.current_stock > criticalLevel && threshold > 0;
            if (stockStatus === 'normal') return item.current_stock > threshold || threshold === 0;
            return true;
        });
    }
    renderTable(filtered);
}

// ---------------------------------------------------------
// Item Details
// ---------------------------------------------------------
function showItemDetails(id) {
    const item = inventoryData.find(x => x.id === id);
    if (!item) {
        showToast('Item not found', 'error');
        return;
    }

    selectedInventoryId = id;
    const status = getStockStatus(item);
    const totalValue = item.current_stock * item.cost_price;

    detailContent.innerHTML = `
        <div class="detail-grid">
            <div class="detail-card">
                <label>Item Name</label>
                <strong>${escapeHtml(item.name)}</strong>
            </div>
            <div class="detail-card">
                <label>Category</label>
                <strong>${escapeHtml(item.category)}</strong>
            </div>
            <div class="detail-card">
                <label>Current Stock</label>
                <strong>${item.current_stock} ${escapeHtml(item.unit)}</strong>
            </div>
            <div class="detail-card">
                <label>Reorder Level</label>
                <strong>${item.min_stock_threshold || 0}</strong>
            </div>
            <div class="detail-card">
                <label>Unit Cost</label>
                <strong>${formatCurrency(item.cost_price)}</strong>
            </div>
            <div class="detail-card">
                <label>Total Value</label>
                <strong>${formatCurrency(totalValue)}</strong>
            </div>
            <div class="detail-card">
                <label>Status</label>
                <strong>${status.label}</strong>
            </div>
            <div class="detail-card">
                <label>Condition</label>
                <strong>${item.status === 'active' ? 'Active' : 'Inactive'}</strong>
            </div>
            <div class="detail-card" style="grid-column: span 2;">
                <label>Supplier</label>
                <strong>${escapeHtml(item.supplier || '—')}</strong>
            </div>
        </div>
    `;

    detailActionsBottom.style.display = 'flex';
    editItemBtn.style.display = 'inline-flex';
    deleteItemBtn.style.display = 'inline-flex';
}

// ---------------------------------------------------------
// Modal (Create / Edit)
// ---------------------------------------------------------
function openModal(editMode = false, item = null) {
    if (!modal) return;
    if (editMode && item) {
        modalTitle.textContent = 'Edit Inventory Item';
        editId.value = item.id;
        itemName.value = item.name || '';
        itemCategory.value = item.category || '';
        itemStock.value = item.current_stock || 0;
        itemUnit.value = item.unit || '';
        itemCost.value = item.cost_price || 0;
        reorderLevel.value = item.min_stock_threshold || 0;
        itemSupplier.value = item.supplier || '';
    } else {
        modalTitle.textContent = 'Add Inventory Item';
        inventoryForm.reset();
        editId.value = '';
        itemStock.value = 0;
        reorderLevel.value = 5;
    }
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    if (!modal) return;
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

// ---------------------------------------------------------
// Form Submit (Create / Update)
// ---------------------------------------------------------
async function handleInventorySubmit(e) {
    e.preventDefault();
    if (isSubmitting) return;
    isSubmitting = true;

    const id = editId.value;
    const payload = {
        name: itemName.value.trim(),
        category: itemCategory.value,
        unit: itemUnit.value,
        current_stock: parseInt(itemStock.value) || 0,
        cost_price: parseFloat(itemCost.value) || 0,
        min_stock_threshold: parseInt(reorderLevel.value) || 0,
        supplier: itemSupplier.value.trim() || null
    };

    try {
        let url = '/api/inventory/';
        let method = 'POST';
        if (id) {
            url = `/api/inventory/${id}`;
            method = 'PUT';
        }
        await fetchJSON(url, { method, body: JSON.stringify(payload) });
        showToast(id ? 'Item updated' : 'Item added');
        closeModal();
        await loadInventoryItems();
        await loadDashboardStats();
        if (id && selectedInventoryId === id) {
            showItemDetails(id);
        }
    } catch (err) {
        console.error(err);
        showToast(err.message || 'Save failed', 'error');
    } finally {
        isSubmitting = false;
    }
}

// ---------------------------------------------------------
// Delete Item
// ---------------------------------------------------------
async function deleteSelectedItem() {
    if (!selectedInventoryId) return;
    if (!confirm('Delete this inventory item permanently?')) return;

    try {
        await fetchJSON(`/api/inventory/${selectedInventoryId}`, { method: 'DELETE' });
        showToast('Item deleted');
        await loadInventoryItems();
        await loadDashboardStats();
        detailContent.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-box-open"></i>
                <h4>No Item Selected</h4>
                <p>Select an inventory item to view details.</p>
            </div>
        `;
        detailActionsBottom.style.display = 'none';
        editItemBtn.style.display = 'none';
        deleteItemBtn.style.display = 'none';
        selectedInventoryId = null;
    } catch (err) {
        console.error(err);
        showToast('Delete failed', 'error');
    }
}

// ---------------------------------------------------------
// Edit Selected Item
// ---------------------------------------------------------
function editSelectedItem() {
    if (!selectedInventoryId) return;
    const item = inventoryData.find(x => x.id === selectedInventoryId);
    if (item) openModal(true, item);
}

// ---------------------------------------------------------
// Reorder / History (placeholder actions)
// ---------------------------------------------------------
function handleReorder() {
    if (!selectedInventoryId) return;
    const item = inventoryData.find(x => x.id === selectedInventoryId);
    if (!item) return;
    const qty = prompt(`Enter reorder quantity for "${item.name}":`, item.min_stock_threshold * 2 || 10);
    if (qty === null) return;
    const quantity = parseInt(qty);
    if (isNaN(quantity) || quantity < 1) {
        showToast('Invalid quantity', 'error');
        return;
    }
    // TODO: Implement reorder logic (purchase order, stock in movement)
    showToast(`Reorder for ${item.name}: ${quantity} ${item.unit} (feature coming soon)`);
}

function handleHistory() {
    if (!selectedInventoryId) return;
    const item = inventoryData.find(x => x.id === selectedInventoryId);
    if (!item) return;
    // TODO: Show movement history for this item
    showToast(`History for ${item.name} (feature coming soon)`);
}

// ---------------------------------------------------------
// Initialize Search & Filters
// ---------------------------------------------------------
function initializeFilters() {
    searchInput?.addEventListener('input', applyFilters);
    categoryFilter?.addEventListener('change', applyFilters);
    stockFilter?.addEventListener('change', applyFilters);
}

// ---------------------------------------------------------
// Initialize Modal Events
// ---------------------------------------------------------
function initializeModal() {
    const closeBtn = document.getElementById('closeInventoryModal');
    const cancelBtn = document.getElementById('cancelModalBtn');
    const addBtn = document.getElementById('addItemBtn');

    closeBtn?.addEventListener('click', closeModal);
    cancelBtn?.addEventListener('click', closeModal);
    modal?.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
    addBtn?.addEventListener('click', () => openModal(false));
    inventoryForm?.addEventListener('submit', handleInventorySubmit);
}

// ---------------------------------------------------------
// Initialize Detail Panel Actions
// ---------------------------------------------------------
function initializeDetailActions() {
    editItemBtn?.addEventListener('click', editSelectedItem);
    deleteItemBtn?.addEventListener('click', deleteSelectedItem);
    reorderBtn?.addEventListener('click', handleReorder);
    historyBtn?.addEventListener('click', handleHistory);
}

// ---------------------------------------------------------
// Category Chips
// ---------------------------------------------------------
function initializeCategoryChips() {
    document.querySelectorAll('.category-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            document.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            const category = chip.textContent.trim();
            if (category === 'All') {
                categoryFilter.value = '';
            } else {
                categoryFilter.value = category;
            }
            applyFilters();
        });
    });
}

// ---------------------------------------------------------
// Toast Container
// ---------------------------------------------------------
function ensureToastContainer() {
    if (!document.getElementById('toastContainer')) {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 99999;
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-width: 400px;
        `;
        document.body.appendChild(container);
    }
}

// ---------------------------------------------------------
// CSS for Status Badges (inject if not present)
// ---------------------------------------------------------
function injectStatusStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .status-critical {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 600;
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
        }
        .status-low {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 600;
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
        }
        .status-normal {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
        }
        .loading-placeholder {
            text-align: center;
            color: var(--gray-500);
            padding: 2rem 0;
        }
        .detail-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }
        .detail-card {
            background: rgba(255, 255, 255, 0.03);
            padding: 0.75rem;
            border-radius: 10px;
            border: 1px solid var(--gray-200);
        }
        .detail-card label {
            display: block;
            font-size: 0.7rem;
            color: var(--gray-500);
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }
        .detail-card strong {
            color: var(--gray-800);
        }
        @media (max-width: 768px) {
            .detail-grid {
                grid-template-columns: 1fr;
            }
        }
    `;
    document.head.appendChild(style);
}

// ---------------------------------------------------------
// Init
// ---------------------------------------------------------
async function init() {
    ensureToastContainer();
    injectStatusStyles();

    // Load data
    await loadInventoryItems();
    await loadDashboardStats();
    await loadRecentMovements();

    // Initialize UI
    initializeModal();
    initializeFilters();
    initializeDetailActions();
    initializeCategoryChips();

    // Show default empty state
    if (!selectedInventoryId) {
        detailContent.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-box-open"></i>
                <h4>No Item Selected</h4>
                <p>Select an inventory item to view detailed information.</p>
            </div>
        `;
        detailActionsBottom.style.display = 'none';
        editItemBtn.style.display = 'none';
        deleteItemBtn.style.display = 'none';
    }

    // Auto-refresh every 60 seconds
    setInterval(() => {
        loadInventoryItems();
        loadDashboardStats();
        loadRecentMovements();
    }, 60000);
}

// ---------------------------------------------------------
// Start when DOM ready
// ---------------------------------------------------------
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}