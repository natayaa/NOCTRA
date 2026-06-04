// ==========================================================
// NOCTRA INVENTORY MANAGEMENT
// ==========================================================

let selectedInventoryId = null;

const inventoryData = [
    {
        id: 1,
        name: "Epoxy Primer",
        category: "Paint",
        stock: 4,
        unit: "Liter",
        cost: 200000,
        reorderLevel: 10,
        supplier: "CV Sinar Paint",
        icon: "fa-paint-roller"
    },
    {
        id: 2,
        name: "Clear Coat Premium",
        category: "Paint",
        stock: 8,
        unit: "Liter",
        cost: 350000,
        reorderLevel: 10,
        supplier: "PT Auto Color",
        icon: "fa-spray-can"
    },
    {
        id: 3,
        name: "Sandpaper P800",
        category: "Consumable",
        stock: 50,
        unit: "PCS",
        cost: 3500,
        reorderLevel: 20,
        supplier: "Sinar Abrasive",
        icon: "fa-layer-group"
    },
    {
        id: 4,
        name: "Body Filler",
        category: "Consumable",
        stock: 12,
        unit: "KG",
        cost: 85000,
        reorderLevel: 5,
        supplier: "Putty Indonesia",
        icon: "fa-toolbox"
    }
];

// ==========================================================
// UTILITIES
// ==========================================================

function formatCurrency(value) {
    return new Intl.NumberFormat("id-ID", {
        style: "currency",
        currency: "IDR",
        maximumFractionDigits: 0
    }).format(value);
}

function getStockStatus(item) {

    const criticalLevel = Math.floor(item.reorderLevel / 2);

    if (item.stock <= criticalLevel) {
        return {
            label: "Critical",
            className: "status-critical"
        };
    }

    if (item.stock <= item.reorderLevel) {
        return {
            label: "Low Stock",
            className: "status-low"
        };
    }

    return {
        label: "Normal",
        className: "status-normal"
    };
}

// ==========================================================
// TABLE RENDER
// ==========================================================

function renderInventoryTable(items = inventoryData) {

    const tbody =
        document.getElementById("inventoryItemsList");

    if (!tbody) return;

    tbody.innerHTML = "";

    items.forEach(item => {

        const status = getStockStatus(item);
        const totalValue = item.stock * item.cost;

        const row = document.createElement("tr");

        row.innerHTML = `
            <td>
                <strong>${item.name}</strong>
            </td>

            <td>${item.category}</td>

            <td>${item.stock}</td>

            <td>${item.unit}</td>

            <td>
                <span class="${status.className}">
                    ${status.label}
                </span>
            </td>

            <td>
                ${formatCurrency(totalValue)}
            </td>

            <td>
                <button
                    class="table-view-btn"
                    data-id="${item.id}"
                >
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        `;

        tbody.appendChild(row);
    });

    document
        .querySelectorAll(".table-view-btn")
        .forEach(button => {

            button.addEventListener("click", () => {
                const id =
                    Number(button.dataset.id);

                showItemDetails(id);
            });

        });
}

// ==========================================================
// DETAILS
// ==========================================================

function showItemDetails(id) {

    const item =
        inventoryData.find(x => x.id === id);

    if (!item) return;

    selectedInventoryId = id;

    const detailContent =
        document.getElementById("itemDetailContent");

    const totalValue =
        item.stock * item.cost;

    const status =
        getStockStatus(item);

    detailContent.innerHTML = `
        <div class="detail-grid">

            <div class="detail-card">
                <label>Item Name</label>
                <strong>${item.name}</strong>
            </div>

            <div class="detail-card">
                <label>Category</label>
                <strong>${item.category}</strong>
            </div>

            <div class="detail-card">
                <label>Current Stock</label>
                <strong>${item.stock} ${item.unit}</strong>
            </div>

            <div class="detail-card">
                <label>Reorder Level</label>
                <strong>${item.reorderLevel}</strong>
            </div>

            <div class="detail-card">
                <label>Unit Cost</label>
                <strong>${formatCurrency(item.cost)}</strong>
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
                <label>Supplier</label>
                <strong>${item.supplier || "-"}</strong>
            </div>

        </div>
    `;

    document.getElementById(
        "detailActionsBottom"
    ).style.display = "flex";

    document.getElementById(
        "editItemBtn"
    ).style.display = "inline-flex";

    document.getElementById(
        "deleteItemBtn"
    ).style.display = "inline-flex";
}

// ==========================================================
// STATS
// ==========================================================

function updateStats() {

    const totalItems =
        inventoryData.length;

    const totalValue =
        inventoryData.reduce(
            (acc, item) =>
                acc + (item.stock * item.cost),
            0
        );

    const lowStockCount =
        inventoryData.filter(
            item => item.stock <= item.reorderLevel
        ).length;

    const totalValueEl =
        document.getElementById("totalValue");

    const totalItemsEl =
        document.getElementById("totalItems");

    const lowStockEl =
        document.getElementById("lowStockCount");

    if (totalValueEl)
        totalValueEl.textContent =
            formatCurrency(totalValue);

    if (totalItemsEl)
        totalItemsEl.textContent =
            totalItems;

    if (lowStockEl)
        lowStockEl.textContent =
            lowStockCount;
}

// ==========================================================
// FILTERS
// ==========================================================

function applyFilters() {

    const keyword =
        document
            .getElementById("searchInventory")
            ?.value
            ?.toLowerCase()
            ?.trim() || "";

    const category =
        document
            .getElementById("categoryFilter")
            ?.value || "";

    const stock =
        document
            .getElementById("stockFilter")
            ?.value || "";

    let filtered =
        [...inventoryData];

    if (keyword) {

        filtered = filtered.filter(item =>
            item.name.toLowerCase().includes(keyword) ||
            item.category.toLowerCase().includes(keyword) ||
            item.supplier.toLowerCase().includes(keyword)
        );
    }

    if (category) {

        filtered = filtered.filter(
            item => item.category === category
        );
    }

    if (stock) {

        filtered = filtered.filter(item => {

            const critical =
                item.stock <=
                Math.floor(item.reorderLevel / 2);

            const low =
                item.stock <= item.reorderLevel;

            if (stock === "critical")
                return critical;

            if (stock === "low")
                return low && !critical;

            if (stock === "normal")
                return !low;

            return true;
        });
    }

    renderInventoryTable(filtered);
}

// ==========================================================
// MODAL
// ==========================================================

function openModal() {

    const modal =
        document.getElementById(
            "inventoryModal"
        );

    if (modal)
        modal.classList.add("active");
}

function closeModal() {

    const modal =
        document.getElementById(
            "inventoryModal"
        );

    if (modal)
        modal.classList.remove("active");
}

// ==========================================================
// FORM SUBMIT
// ==========================================================

function handleInventorySubmit(event) {

    event.preventDefault();

    const item = {
        id: Date.now(),

        name:
            document.getElementById(
                "itemName"
            ).value,

        category:
            document.getElementById(
                "itemCategory"
            ).value,

        stock:
            Number(
                document.getElementById(
                    "itemStock"
                ).value
            ),

        unit:
            document.getElementById(
                "itemUnit"
            ).value,

        cost:
            Number(
                document.getElementById(
                    "itemCost"
                ).value
            ),

        reorderLevel:
            Number(
                document.getElementById(
                    "reorderLevel"
                ).value
            ),

        supplier:
            document.getElementById(
                "itemSupplier"
            ).value
    };

    inventoryData.push(item);

    renderInventoryTable();
    updateStats();

    event.target.reset();

    closeModal();

    showToast(
        "Inventory item added successfully",
        "success"
    );
}

// ==========================================================
// DELETE
// ==========================================================

function deleteSelectedItem() {

    if (!selectedInventoryId)
        return;

    const index =
        inventoryData.findIndex(
            x => x.id === selectedInventoryId
        );

    if (index === -1)
        return;

    const confirmed =
        confirm(
            "Delete selected inventory item?"
        );

    if (!confirmed)
        return;

    inventoryData.splice(index, 1);

    renderInventoryTable();
    updateStats();

    document.getElementById(
        "itemDetailContent"
    ).innerHTML = `
        <div class="empty-state">
            <i class="fas fa-box-open"></i>
            <h4>No Item Selected</h4>
            <p>Select an inventory item to view details.</p>
        </div>
    `;

    selectedInventoryId = null;

    showToast(
        "Item deleted successfully",
        "success"
    );
}

// ==========================================================
// TOAST
// ==========================================================

function showToast(message, type = "success") {

    const container =
        document.getElementById(
            "toastContainer"
        );

    if (!container)
        return;

    const toast =
        document.createElement("div");

    toast.className =
        `toast ${type}`;

    toast.innerHTML = `
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// ==========================================================
// EVENT BINDING
// ==========================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        renderInventoryTable();
        updateStats();

        document
            .getElementById("searchInventory")
            ?.addEventListener(
                "input",
                applyFilters
            );

        document
            .getElementById("categoryFilter")
            ?.addEventListener(
                "change",
                applyFilters
            );

        document
            .getElementById("stockFilter")
            ?.addEventListener(
                "change",
                applyFilters
            );

        document
            .getElementById("addItemBtn")
            ?.addEventListener(
                "click",
                openModal
            );

        document
            .getElementById(
                "closeInventoryModal"
            )
            ?.addEventListener(
                "click",
                closeModal
            );

        document
            .getElementById(
                "cancelModalBtn"
            )
            ?.addEventListener(
                "click",
                closeModal
            );

        document
            .getElementById(
                "inventoryForm"
            )
            ?.addEventListener(
                "submit",
                handleInventorySubmit
            );

        document
            .getElementById(
                "deleteItemBtn"
            )
            ?.addEventListener(
                "click",
                deleteSelectedItem
            );
    }
);