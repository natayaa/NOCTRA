// ===== DATA STORAGE =====
let inventoryData = [
    {
        id: 1,
        name: "Clear Coat",
        category: "Paint",
        stock: 2,
        unit: "Liter",
        cost: 450000,
        reorderLevel: 5,
        lastRestocked: "2026-05-15"
    },
    {
        id: 2,
        name: "Premium Paint Red",
        category: "Paint",
        stock: 15,
        unit: "Liter",
        cost: 180000,
        reorderLevel: 5,
        lastRestocked: "2026-05-20"
    },
    {
        id: 3,
        name: "Primer",
        category: "Consumable",
        stock: 3,
        unit: "Liter",
        cost: 95000,
        reorderLevel: 5,
        lastRestocked: "2026-05-10"
    },
    {
        id: 4,
        name: "Sandpaper #1500",
        category: "Consumable",
        stock: 1,
        unit: "Pack",
        cost: 25000,
        reorderLevel: 3,
        lastRestocked: "2026-05-05"
    },
    {
        id: 5,
        name: "Spray Gun",
        category: "Tool",
        stock: 5,
        unit: "Unit",
        cost: 850000,
        reorderLevel: 2,
        lastRestocked: "2026-04-28"
    }
];

let nextId = 6;
let currentSelectedId = 1;

// ===== HELPER FUNCTIONS =====
function getStockStatus(stock, reorderLevel) {
    if (stock <= 2) return { status: "critical", label: "CRITICAL", class: "critical" };
    if (stock <= reorderLevel) return { status: "low", label: "LOW", class: "low" };
    return { status: "ok", label: "OK", class: "ok" };
}

function formatCurrency(value) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0
    }).format(value);
}

function showToast(message, type = "success") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i> ${message}`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function updateStats() {
    const totalValue = inventoryData.reduce((sum, item) => sum + (item.stock * item.cost), 0);
    const totalItems = inventoryData.length;
    const lowStockCount = inventoryData.filter(item => {
        const status = getStockStatus(item.stock, item.reorderLevel);
        return status.status === "low" || status.status === "critical";
    }).length;
    
    document.getElementById("totalValue").innerHTML = formatCurrency(totalValue);
    document.getElementById("totalItems").innerHTML = totalItems;
    document.getElementById("lowStockCount").innerHTML = lowStockCount;
}

function renderInventoryList() {
    const searchTerm = document.getElementById("searchInventory").value.toLowerCase();
    const categoryFilter = document.getElementById("categoryFilter").value;
    const stockFilter = document.getElementById("stockFilter").value;
    
    const filteredItems = inventoryData.filter(item => {
        const matchesSearch = item.name.toLowerCase().includes(searchTerm);
        const matchesCategory = !categoryFilter || item.category === categoryFilter;
        const stockStatus = getStockStatus(item.stock, item.reorderLevel);
        const matchesStock = !stockFilter || 
            (stockFilter === "low" && stockStatus.status === "low") ||
            (stockFilter === "critical" && stockStatus.status === "critical") ||
            (stockFilter === "normal" && stockStatus.status === "ok");
        return matchesSearch && matchesCategory && matchesStock;
    });
    
    const container = document.getElementById("inventoryItemsList");
    container.innerHTML = "";
    
    filteredItems.forEach(item => {
        const stockStatus = getStockStatus(item.stock, item.reorderLevel);
        const itemDiv = document.createElement("div");
        itemDiv.className = `inventory-item ${currentSelectedId === item.id ? "active" : ""}`;
        itemDiv.setAttribute("data-id", item.id);
        itemDiv.innerHTML = `
            <div class="item-icon">
                <i class="fas ${getCategoryIcon(item.category)}"></i>
            </div>
            <div class="item-info">
                <div class="item-name">
                    ${escapeHtml(item.name)}
                    <span class="stock-badge ${stockStatus.class}">${stockStatus.label}</span>
                </div>
                <div class="item-details">
                    <span class="item-category">${item.category}</span>
                    <span>Stock: ${item.stock} ${item.unit}</span>
                </div>
            </div>
            <div class="item-meta">
                <div class="item-cost">${formatCurrency(item.cost)}</div>
            </div>
        `;
        itemDiv.addEventListener("click", () => selectItem(item.id));
        container.appendChild(itemDiv);
    });
}

function getCategoryIcon(category) {
    const icons = {
        "Paint": "fa-fill-drip",
        "Consumable": "fa-paint-roller",
        "Part": "fa-microchip",
        "Tool": "fa-wrench"
    };
    return icons[category] || "fa-box";
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function selectItem(id) {
    currentSelectedId = id;
    const item = inventoryData.find(i => i.id === id);
    if (!item) return;
    
    renderInventoryList();
    
    const stockStatus = getStockStatus(item.stock, item.reorderLevel);
    
    document.getElementById("itemDetailContent").innerHTML = `
        <div class="detail-field">
            <label>Item Name</label>
            <p>${escapeHtml(item.name)}</p>
        </div>
        <div class="detail-field">
            <label>Category</label>
            <p>${item.category}</p>
        </div>
        <div class="detail-field">
            <label>Current Stock</label>
            <p>${item.stock} ${item.unit}</p>
        </div>
        <div class="detail-field">
            <label>Unit Price</label>
            <p>${formatCurrency(item.cost)}</p>
        </div>
        <div class="detail-field">
            <label>Reorder Level</label>
            <p>${item.reorderLevel} ${item.unit}</p>
        </div>
        <div class="detail-field">
            <label>Status</label>
            <p><span class="status-badge-detail ${stockStatus.class}">${stockStatus.label} STOCK</span></p>
        </div>
        <div class="detail-field">
            <label>Last Restocked</label>
            <p>${item.lastRestocked || "Not recorded"}</p>
        </div>
        <div class="detail-field">
            <label>Total Value</label>
            <p>${formatCurrency(item.stock * item.cost)}</p>
        </div>
    `;
    
    document.getElementById("editItemBtn").style.display = "inline-flex";
    document.getElementById("deleteItemBtn").style.display = "inline-flex";
    document.getElementById("detailActionsBottom").style.display = "flex";
}

function openModal(editMode = false, item = null) {
    const modal = document.getElementById("inventoryModal");
    const modalTitle = document.getElementById("modalTitle");
    const form = document.getElementById("inventoryForm");
    
    if (editMode && item) {
        modalTitle.textContent = "Edit Inventory Item";
        document.getElementById("editId").value = item.id;
        document.getElementById("itemName").value = item.name;
        document.getElementById("itemCategory").value = item.category;
        document.getElementById("itemStock").value = item.stock;
        document.getElementById("itemUnit").value = item.unit;
        document.getElementById("itemCost").value = item.cost;
        document.getElementById("reorderLevel").value = item.reorderLevel;
    } else {
        modalTitle.textContent = "Add Inventory Item";
        form.reset();
        document.getElementById("editId").value = "";
    }
    modal.classList.add("active");
}

function closeModal() {
    document.getElementById("inventoryModal").classList.remove("active");
}

function saveItem(event) {
    event.preventDefault();
    
    const editId = document.getElementById("editId").value;
    const name = document.getElementById("itemName").value.trim();
    const category = document.getElementById("itemCategory").value;
    const stock = parseInt(document.getElementById("itemStock").value);
    const unit = document.getElementById("itemUnit").value.trim();
    const cost = parseInt(document.getElementById("itemCost").value);
    const reorderLevel = parseInt(document.getElementById("reorderLevel").value) || 5;
    
    if (!name || !category || !stock || !unit || !cost) {
        showToast("Please fill all required fields", "error");
        return;
    }
    
    if (editId) {
        // Edit existing item
        const index = inventoryData.findIndex(i => i.id === parseInt(editId));
        if (index !== -1) {
            inventoryData[index] = {
                ...inventoryData[index],
                name, category, stock, unit, cost, reorderLevel,
                lastRestocked: new Date().toISOString().split('T')[0]
            };
            showToast(`${name} updated successfully`, "success");
        }
    } else {
        // Add new item
        const newItem = {
            id: nextId++,
            name, category, stock, unit, cost, reorderLevel,
            lastRestocked: new Date().toISOString().split('T')[0]
        };
        inventoryData.push(newItem);
        showToast(`${name} added successfully`, "success");
    }
    
    updateStats();
    renderInventoryList();
    if (currentSelectedId) selectItem(currentSelectedId);
    closeModal();
}

function deleteItem() {
    if (!currentSelectedId) return;
    
    if (confirm("Are you sure you want to delete this item?")) {
        const index = inventoryData.findIndex(i => i.id === currentSelectedId);
        if (index !== -1) {
            const itemName = inventoryData[index].name;
            inventoryData.splice(index, 1);
            
            if (inventoryData.length > 0) {
                currentSelectedId = inventoryData[0].id;
                selectItem(currentSelectedId);
            } else {
                currentSelectedId = null;
                document.getElementById("itemDetailContent").innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-box-open"></i>
                        <p>No items in inventory</p>
                    </div>
                `;
                document.getElementById("editItemBtn").style.display = "none";
                document.getElementById("deleteItemBtn").style.display = "none";
                document.getElementById("detailActionsBottom").style.display = "none";
            }
            
            updateStats();
            renderInventoryList();
            showToast(`${itemName} deleted successfully`, "success");
        }
    }
}

function reorderItem() {
    const item = inventoryData.find(i => i.id === currentSelectedId);