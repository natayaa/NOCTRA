// ============================================================
// inventories.js - NOCTRA Inventory Management
// Version: 2.0 - Refactored & Clean
// ============================================================

// ============================================================
// 1. CONFIGURATION
// ============================================================
const CONFIG = {
  API_BASE_URL: "/api/api",
  ITEMS_PER_PAGE: 10,
  TOAST_DURATION: 4000,
  MAX_MOVEMENTS: 5,
};

// ============================================================
// 2. STATE
// ============================================================
const state = {
  items: [],
  currentPage: 1,
  totalPages: 1,
  totalItems: 0,
  selectedItemId: null,
  selectedItemData: null,
  editingId: null,
  filters: {
    search: "",
    category: "",
    status: "",
    stock_status: "",
    low_stock_only: false,
  },
  categories: [],
  suppliers: [],
  isLoading: false,
};

// ============================================================
// 3. DOM UTILITIES (Safe access)
// ============================================================
const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

const $$ = (selector) => document.querySelectorAll(selector);

// ============================================================
// 4. DOM REFERENCES
// ============================================================
const DOM = {
  // Dashboard
  totalValue: () => $("totalValue"),
  totalItems: () => $("totalItems"),
  lowStockCount: () => $("lowStockCount"),
  monthlyUsage: () => $("monthlyUsage"),

  // Alerts
  alertList: () => $("alertList"),
  refreshAlertsBtn: () => $("refreshAlertsBtn"),

  // Sidebar
  searchInventory: () => $("searchInventory"),
  categoryFilter: () => $("categoryFilter"),
  stockFilter: () => $("stockFilter"),
  statusFilter: () => $("statusFilter"),
  categoryList: () => $("categoryList"),
  recentMovements: () => $("recentMovements"),

  // Table
  inventoryItemsList: () => $("inventoryItemsList"),

  // Pagination
  prevPageBtn: () => $("prevPageBtn"),
  nextPageBtn: () => $("nextPageBtn"),
  pageInfo: () => $("pageInfo"),

  // Buttons
  exportInventoryBtn: () => $("exportInventoryBtn"),
  addItemBtn: () => $("addItemBtn"),

  // Detail Panel
  itemDetailContent: () => $("itemDetailContent"),
  editItemBtn: () => $("editItemBtn"),
  deleteItemBtn: () => $("deleteItemBtn"),
  detailActionsBottom: () => $("detailActionsBottom"),
  reorderBtn: () => $("reorderBtn"),
  historyBtn: () => $("historyBtn"),
  adjustStockBtn: () => $("adjustStockBtn"),

  // Inventory Modal
  inventoryModal: () => $("inventoryModal"),
  modalTitle: () => $("modalTitle"),
  editId: () => $("editId"),
  inventoryForm: () => $("inventoryForm"),
  itemName: () => $("itemName"),
  itemCategory: () => $("itemCategory"),
  itemSubCategory: () => $("itemSubCategory"),
  itemUnit: () => $("itemUnit"),
  itemStock: () => $("itemStock"),
  reorderLevel: () => $("reorderLevel"),
  itemCost: () => $("itemCost"),
  itemSellingPrice: () => $("itemSellingPrice"),
  itemSku: () => $("itemSku"),
  itemBarcode: () => $("itemBarcode"),
  itemLocation: () => $("itemLocation"),
  itemSupplier: () => $("itemSupplier"),
  itemDescription: () => $("itemDescription"),
  submitBtn: () => $("submitBtn"),
  cancelModalBtn: () => $("cancelModalBtn"),
  closeInventoryModal: () => $("closeInventoryModal"),

  // Stock Adjust Modal
  stockAdjustModal: () => $("stockAdjustModal"),
  stockAdjustForm: () => $("stockAdjustForm"),
  adjustItemId: () => $("adjustItemId"),
  adjustCurrentStock: () => $("adjustCurrentStock"),
  adjustNewStock: () => $("adjustNewStock"),
  adjustReasonSelect: () => $("adjustReasonSelect"),
  adjustNotes: () => $("adjustNotes"),
  cancelStockAdjustBtn: () => $("cancelStockAdjustBtn"),
  closeStockAdjustModal: () => $("closeStockAdjustModal"),

  // History Modal
  historyModal: () => $("historyModal"),
  historyBody: () => $("historyBody"),
  historyItemName: () => $("historyItemName"),
  closeHistoryModal: () => $("closeHistoryModal"),
  closeHistoryModalBtn: () => $("closeHistoryModalBtn"),

  // Reorder Modal
  reorderModal: () => $("reorderModal"),
  reorderForm: () => $("reorderForm"),
  reorderItemId: () => $("reorderItemId"),
  reorderItemName: () => $("reorderItemName"),
  reorderCurrentStock: () => $("reorderCurrentStock"),
  reorderThreshold: () => $("reorderThreshold"),
  reorderQuantity: () => $("reorderQuantity"),
  reorderSupplier: () => $("reorderSupplier"),
  cancelReorderBtn: () => $("cancelReorderBtn"),
  closeReorderModal: () => $("closeReorderModal"),

  // Toast
  toastContainer: () => $("toastContainer"),
};

// ============================================================
// 5. TOAST SYSTEM
// ============================================================
function showToast(message, type = "info", duration = CONFIG.TOAST_DURATION) {
  const container = DOM.toastContainer();
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
        <span>${message}</span>
        <button class="toast-close">&times;</button>
    `;

  container.appendChild(toast);

  toast.querySelector(".toast-close").addEventListener("click", () => {
    toast.remove();
  });

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-10px)";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ============================================================
// 6. FORMATTERS
// ============================================================
const Formatter = {
  currency: (amount) => {
    if (!amount && amount !== 0) return "Rp 0";
    return new Intl.NumberFormat("id-ID", {
      style: "currency",
      currency: "IDR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(Number(amount));
  },

  date: (dateString) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleDateString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  },

  dateTime: (dateString) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  },

  stockStatus: (quantity, threshold) => {
    const qty = Number(quantity) || 0;
    const thresh = Number(threshold) || 5;

    if (qty <= 0)
      return { status: "out_of_stock", label: "Out of Stock", dot: "out" };
    if (qty <= thresh * 0.25)
      return { status: "critical", label: "Critical", dot: "critical" };
    if (qty <= thresh) return { status: "low", label: "Low Stock", dot: "low" };
    return { status: "normal", label: "Normal", dot: "normal" };
  },

  statusBadge: (status) => {
    const map = {
      active: "active",
      inactive: "inactive",
      out_of_stock: "out",
    };
    return map[status] || "inactive";
  },

  statusLabel: (status) => {
    const map = {
      active: "Active",
      inactive: "Inactive",
      out_of_stock: "Out of Stock",
    };
    return map[status] || status;
  },
};

// ============================================================
// 7. HTML ESCAPE
// ============================================================
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ============================================================
// 8. API HELPERS
// ============================================================
async function apiFetch(endpoint, options = {}) {
  const url = `${CONFIG.API_BASE_URL}${endpoint}`;
  const config = {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || `HTTP ${response.status}`);
    }

    return data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

// ============================================================
// 9. API SERVICES
// ============================================================
const InventoryAPI = {
  // Fetch items with pagination and filters
  fetchItems: async (page = 1, filters = {}) => {
    state.isLoading = true;
    showLoadingState();

    const params = new URLSearchParams({
      page: page,
      limit: CONFIG.ITEMS_PER_PAGE,
    });

    if (filters.search) params.set("search", filters.search);
    if (filters.category) params.set("category", filters.category);
    if (filters.status) params.set("status", filters.status);
    if (filters.low_stock_only) params.set("low_stock_only", "true");

    console.log("📡 Fetching inventory:", params.toString());

    try {
      const response = await apiFetch(`/inventory/items/?${params.toString()}`);
      return response.data || response;
    } catch (error) {
      showToast("Failed to load inventory: " + error.message, "error");
      return null;
    } finally {
      state.isLoading = false;
    }
  },

  // Fetch single item detail
  fetchItemDetail: async (itemId) => {
    try {
      const response = await apiFetch(`/inventory/items/${itemId}`);
      return response.data;
    } catch (error) {
      showToast("Failed to load item details: " + error.message, "error");
      return null;
    }
  },

  // Create new item
  createItem: async (data) => {
    try {
      const response = await apiFetch("/inventory/items/", {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data;
    } catch (error) {
      showToast("Failed to create item: " + error.message, "error");
      return null;
    }
  },

  // Update item
  updateItem: async (itemId, data) => {
    try {
      const response = await apiFetch(`/inventory/items/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      return response.data;
    } catch (error) {
      showToast("Failed to update item: " + error.message, "error");
      return null;
    }
  },

  // Delete item
  deleteItem: async (itemId) => {
    try {
      const response = await apiFetch(`/inventory/items/${itemId}`, {
        method: "DELETE",
      });
      return response.data;
    } catch (error) {
      showToast("Failed to delete item: " + error.message, "error");
      return null;
    }
  },

  // Adjust stock
  adjustStock: async (data) => {
    try {
      const response = await apiFetch("/inventory/stock/adjust", {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data;
    } catch (error) {
      showToast("Failed to adjust stock: " + error.message, "error");
      return null;
    }
  },

  // Fetch stock alerts
  fetchAlerts: async () => {
    try {
      const response = await apiFetch("/inventory/alerts");
      return response.data;
    } catch (error) {
      console.error("Failed to load alerts:", error);
      return null;
    }
  },

  // Fetch recent movements
  fetchRecentMovements: async (limit = CONFIG.MAX_MOVEMENTS) => {
    try {
      const response = await apiFetch(
        `/inventory/movements/recent?limit=${limit}`,
      );
      let movements = response.data || response || [];

      // Enrich with item names from state
      return movements.map((m) => {
        const item = state.items.find((i) => i.id === m.item_id);
        if (item) {
          m.item_name = item.name;
          m.item_sku = item.sku;
          m.unit = item.unit;
        }
        return m;
      });
    } catch (error) {
      console.error("Failed to load movements:", error);
      return null;
    }
  },

  // Fetch item movements history
  fetchItemMovements: async (itemId, limit = 20) => {
    try {
      const response = await apiFetch(
        `/inventory/movements/item/${itemId}?limit=${limit}`,
      );
      return response.data;
    } catch (error) {
      console.error("Failed to load item movements:", error);
      return null;
    }
  },

  // Fetch statistics
  fetchStatistics: async () => {
    try {
      const response = await apiFetch("/inventory/statistics");
      return response.data;
    } catch (error) {
      console.error("Failed to load statistics:", error);
      return null;
    }
  },

  // Fetch categories
  fetchCategories: async () => {
    try {
      const response = await apiFetch("/inventory/categories");
      return response.data;
    } catch (error) {
      console.error("Failed to load categories:", error);
      return null;
    }
  },

  // Fetch suppliers
  fetchSuppliers: async () => {
    try {
      const response = await apiFetch("/inventory/suppliers?active_only=true");
      return response.data;
    } catch (error) {
      console.error("Failed to load suppliers:", error);
      return null;
    }
  },

  // Create purchase order (reorder)
  createPurchaseOrder: async (data) => {
    try {
      const response = await apiFetch("/inventory/purchase-orders/", {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data;
    } catch (error) {
      showToast("Failed to create purchase order: " + error.message, "error");
      return null;
    }
  },
};

// ============================================================
// 10. RENDER FUNCTIONS
// ============================================================

function showLoadingState() {
  const list = DOM.inventoryItemsList();
  if (list) {
    list.innerHTML = `
            <tr>
                <td colspan="7" class="loading-placeholder">
                    <i class="fas fa-spinner fa-spin"></i> Loading inventory...
                </td>
            </tr>
        `;
  }
}

function renderItems(items) {
  const list = DOM.inventoryItemsList();
  if (!list) return;

  if (!items || items.length === 0) {
    list.innerHTML = `
            <tr>
                <td colspan="7" class="no-data">
                    <i class="fas fa-box-open" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                    No inventory items found
                    <br><br>
                    <button class="btn-add-item" onclick="openCreateModal()">
                        <i class="fas fa-plus"></i> Add your first item
                    </button>
                </td>
            </tr>
        `;
    return;
  }

  list.innerHTML = items
    .map((item) => {
      const stock = Number(item.current_stock) || 0;
      const threshold = Number(item.min_stock_threshold) || 0;
      const stockStatus = Formatter.stockStatus(stock, threshold);
      const value = stock * (Number(item.cost_price) || 0);
      const status = item.status || "active";

      return `
            <tr class="fade-in ${state.selectedItemId === item.id ? "selected" : ""}" 
                onclick="selectItem('${item.id}')" 
                style="cursor:pointer;">
                <td>
                    <strong style="color:var(--text-primary);">${escapeHtml(item.name)}</strong>
                    ${item.sku ? `<br><small style="color:var(--text-muted);font-size:0.7rem;">SKU: ${escapeHtml(item.sku)}</small>` : ""}
                </td>
                <td>
                    <span class="category-badge" style="background:rgba(var(--primary-rgb),0.08);color:var(--primary);padding:0.15rem 0.6rem;border-radius:var(--radius-full);font-size:0.65rem;font-weight:600;text-transform:uppercase;">
                        ${escapeHtml(item.category || "-")}
                    </span>
                    ${item.sub_category ? `<br><small style="color:var(--text-muted);font-size:0.7rem;">${escapeHtml(item.sub_category)}</small>` : ""}
                </td>
                <td>
                    <span class="stock-level">
                        <span class="dot ${stockStatus.dot}"></span>
                        ${stockStatus.label}
                    </span>
                    <br><small style="color:var(--text-muted);font-size:0.75rem;">${stock} ${escapeHtml(item.unit || "")}</small>
                </td>
                <td>${escapeHtml(item.unit || "-")}</td>
                <td>
                    <span class="status-badge ${Formatter.statusBadge(status)}">
                        ${Formatter.statusLabel(status)}
                    </span>
                </td>
                <td style="font-weight:500;color:var(--text-primary);">
                    ${Formatter.currency(value)}
                </td>
                <td style="text-align:center; white-space:nowrap;">
                    <button class="btn-action btn-edit" onclick="event.stopPropagation(); openEditModal('${item.id}')" title="Edit">
                        <i class="fas fa-pen"></i>
                    </button>
                    <button class="btn-action btn-delete" onclick="event.stopPropagation(); confirmDelete('${item.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    })
    .join("");
}

function renderAlerts(alerts) {
  const list = DOM.alertList();
  if (!list) return;

  if (!alerts || alerts.length === 0) {
    list.innerHTML = `
            <div class="alert-item" style="text-align:center;color:var(--text-muted);padding:0.5rem;">
                <i class="fas fa-check-circle" style="color:#00d578;"></i> All items are properly stocked
            </div>
        `;
    return;
  }

  list.innerHTML = alerts
    .map(
      (alert) => `
        <div class="alert-item ${alert.severity === "critical" ? "critical" : "warning"}">
            <div class="alert-info">
                <strong>${escapeHtml(alert.item_name)}</strong>
                <span>${escapeHtml(alert.message || "Low stock")} · ${alert.current_stock} ${alert.unit || ""} remaining</span>
            </div>
            <span class="alert-badge">${alert.severity === "critical" ? "⚠️ Critical" : "⚠️ Low"}</span>
        </div>
    `,
    )
    .join("");
}

function renderCategories(categories) {
  const list = DOM.categoryList();
  if (!list) return;

  if (!categories || categories.length === 0) {
    list.innerHTML = '<div class="loading-placeholder-sm">No categories</div>';
    return;
  }

  list.innerHTML = categories
    .map(
      (cat) => `
        <span class="category-chip" onclick="filterByCategory('${cat}')">${escapeHtml(cat)}</span>
    `,
    )
    .join("");
}

function renderRecentMovements(movements) {
  const list = DOM.recentMovements();
  if (!list) return;

  if (!movements || movements.length === 0) {
    list.innerHTML =
      '<div class="loading-placeholder-sm">No recent movements</div>';
    return;
  }

  list.innerHTML = movements
    .map((m) => {
      let itemName = m.item_name || m.name || m.item?.name || m.item_id;

      if (!itemName || itemName === m.item_id) {
        const item = state.items.find((i) => i.id === m.item_id);
        itemName = item
          ? item.name
          : m.item_id
            ? m.item_id.substring(0, 8)
            : "Unknown";
      }

      const qty = Number(m.quantity) || 0;
      const type = m.movement_type || m.type || "unknown";
      const isIn = ["in", "purchase", "restock", "stock_in"].includes(type);

      return `
            <div class="movement-item ${isIn ? "stock-in" : "stock-out"}">
                <div class="movement-icon">
                    <i class="fas ${isIn ? "fa-arrow-down" : "fa-arrow-up"}"></i>
                </div>
                <div class="movement-info">
                    <strong>${escapeHtml(itemName)}</strong>
                    <span>${Formatter.date(m.created_at)} · ${escapeHtml(m.reference_type || type)}</span>
                </div>
                <span class="movement-qty ${isIn ? "positive" : "negative"}">
                    ${isIn ? "+" : "-"}${qty} ${escapeHtml(m.unit || "")}
                </span>
            </div>
        `;
    })
    .join("");
}

// ============================================================
// 11. DETAIL PANEL
// ============================================================

function renderDetailPanel(item) {
  const content = DOM.itemDetailContent();
  if (!content) return;

  if (!item) {
    content.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-box-open"></i>
                <h4>No Item Selected</h4>
                <p>Select an inventory item from the table to view detailed information.</p>
            </div>
        `;
    hideDetailActions();
    return;
  }

  const stock = Number(item.current_stock) || 0;
  const threshold = Number(item.min_stock_threshold) || 5;
  const stockStatus = Formatter.stockStatus(stock, threshold);
  const costPrice = Number(item.cost_price) || 0;
  const sellingPrice = Number(item.selling_price) || 0;
  const totalValue = stock * costPrice;
  const profitMargin =
    sellingPrice > 0 ? ((sellingPrice - costPrice) / sellingPrice) * 100 : 0;
  const status = item.status || "active";

  content.innerHTML = `
        <div style="margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);">
            <h3 style="margin:0; font-size:1.1rem; color:var(--text-primary);">${escapeHtml(item.name)}</h3>
            ${item.sku ? `<span style="font-size:0.8rem; color:var(--text-muted);">SKU: ${escapeHtml(item.sku)}</span>` : ""}
        </div>
        
        <div class="detail-info-grid">
            ${createDetailRow(
              "Category",
              `
                <span class="category-badge" style="background:rgba(var(--primary-rgb),0.08);color:var(--primary);padding:0.15rem 0.6rem;border-radius:var(--radius-full);font-size:0.65rem;font-weight:600;text-transform:uppercase;">
                    ${escapeHtml(item.category || "-")}
                </span>
                ${item.sub_category ? `→ ${escapeHtml(item.sub_category)}` : ""}
            `,
            )}
            ${createDetailRow("Unit", escapeHtml(item.unit || "-"))}
            ${createDetailRow(
              "Current Stock",
              `
                <span class="stock-level">
                    <span class="dot ${stockStatus.dot}" style="display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;
                        ${
                          stockStatus.dot === "normal"
                            ? "background:#00d578;"
                            : stockStatus.dot === "low"
                              ? "background:#f59e0b;"
                              : stockStatus.dot === "critical"
                                ? "background:#ef4444;"
                                : "background:var(--text-muted);"
                        }"></span>
                    ${stockStatus.label}
                </span>
                <br><span style="font-size:0.85rem;">${stock} ${escapeHtml(item.unit || "")}</span>
            `,
            )}
            ${createDetailRow("Min Stock Threshold", `${threshold} ${escapeHtml(item.unit || "")}`)}
            ${createDetailRow("Cost Price", `<strong>${Formatter.currency(costPrice)}</strong>`)}
            ${createDetailRow("Selling Price", `<strong>${Formatter.currency(sellingPrice)}</strong>`)}
            ${createDetailRow("Total Inventory Value", `<strong style="color:var(--primary);">${Formatter.currency(totalValue)}</strong>`)}
            ${createDetailRow(
              "Profit Margin",
              `
                <span style="color:${profitMargin > 0 ? "#00d578" : "#ef4444"};">
                    ${profitMargin > 0 ? "+" : ""}${profitMargin.toFixed(1)}%
                </span>
            `,
            )}
            ${createDetailRow("Location", escapeHtml(item.location || "-"))}
            ${createDetailRow("Supplier", escapeHtml(item.supplier_name || item.supplier_id || "-"))}
            ${createDetailRow(
              "Status",
              `
                <span class="status-badge ${Formatter.statusBadge(status)}" 
                    style="display:inline-block;padding:0.15rem 0.7rem;border-radius:var(--radius-full);font-size:0.7rem;font-weight:600;
                    ${
                      status === "active"
                        ? "background:rgba(0,213,120,0.12);color:#00d578;"
                        : status === "out_of_stock"
                          ? "background:rgba(239,68,68,0.12);color:#ef4444;"
                          : "background:rgba(255,255,255,0.06);color:var(--text-muted);"
                    }">
                    ${Formatter.statusLabel(status)}
                </span>
                ${item.is_low_stock ? ' <span style="color:#f59e0b;font-size:0.8rem;">⚠️ Low Stock</span>' : ""}
                ${item.is_out_of_stock ? ' <span style="color:#ef4444;font-size:0.8rem;">🚫 Out of Stock</span>' : ""}
            `,
              "span-2",
            )}
            ${createDetailRow("Description", escapeHtml(item.description || "No description provided."), "span-2")}
            ${createDetailRow("Last Updated", Formatter.dateTime(item.updated_at || item.created_at), "span-2")}
        </div>
    `;

  showDetailActions();
  state.selectedItemData = item;
  state.selectedItemId = item.id;
}

function createDetailRow(label, value, span = "") {
  return `
        <div class="detail-info-item" style="${span === "span-2" ? "grid-column: span 2;" : ""}display:flex;flex-direction:column;gap:0.1rem;">
            <label style="font-size:0.65rem; text-transform:uppercase; letter-spacing:0.04em; color:var(--text-muted);">${label}</label>
            <p style="margin:0; font-size:0.9rem; color:var(--text-primary);">${value}</p>
        </div>
    `;
}

function showDetailActions() {
  const editBtn = DOM.editItemBtn();
  const deleteBtn = DOM.deleteItemBtn();
  const actions = DOM.detailActionsBottom();

  if (editBtn) {
    editBtn.style.display = "inline-flex";
    editBtn.title = "Edit Item";
  }
  if (deleteBtn) {
    deleteBtn.style.display = "inline-flex";
    deleteBtn.title = "Delete Item";
  }
  if (actions) {
    actions.style.display = "flex";
    actions.querySelectorAll(".btn").forEach((btn, i) => {
      btn.style.animationDelay = `${i * 0.1}s`;
    });
  }
}

function hideDetailActions() {
  const editBtn = DOM.editItemBtn();
  const deleteBtn = DOM.deleteItemBtn();
  const actions = DOM.detailActionsBottom();

  if (editBtn) editBtn.style.display = "none";
  if (deleteBtn) deleteBtn.style.display = "none";
  if (actions) actions.style.display = "none";
}

// ============================================================
// 12. PAGINATION & DASHBOARD
// ============================================================

function updatePagination(page, totalPages, totalItems) {
  const info = DOM.pageInfo();
  if (info) {
    info.textContent = `Page ${page} of ${totalPages || 1} (${totalItems} items)`;
  }
  const prev = DOM.prevPageBtn();
  const next = DOM.nextPageBtn();
  if (prev) prev.disabled = page <= 1;
  if (next) next.disabled = page >= totalPages;
}

function updateDashboard(stats) {
  if (!stats) return;
  const totalValue = DOM.totalValue();
  const totalItems = DOM.totalItems();
  const lowStockCount = DOM.lowStockCount();
  const monthlyUsage = DOM.monthlyUsage();

  if (totalValue)
    totalValue.textContent = Formatter.currency(stats.total_value || 0);
  if (totalItems) totalItems.textContent = stats.total_items || 0;
  if (lowStockCount) lowStockCount.textContent = stats.low_stock_items || 0;
  if (monthlyUsage)
    monthlyUsage.textContent = Formatter.currency(stats.monthly_usage || 0);
}

// ============================================================
// 13. SELECT ITEM
// ============================================================

async function selectItem(itemId) {
  const content = DOM.itemDetailContent();
  if (content) {
    content.innerHTML = `
            <div style="text-align:center;padding:2rem;color:var(--text-muted);">
                <i class="fas fa-spinner fa-spin" style="font-size:1.5rem;display:block;margin-bottom:0.5rem;"></i>
                Loading item details...
            </div>
        `;
  }

  const item = await InventoryAPI.fetchItemDetail(itemId);
  if (!item) {
    renderDetailPanel(null);
    return;
  }

  renderDetailPanel(item);

  $$(".inventory-table tbody tr").forEach((row) => {
    row.classList.remove("selected");
    const onclick = row.getAttribute("onclick");
    if (onclick && onclick.includes(itemId)) {
      row.classList.add("selected");
    }
  });
}

// ============================================================
// 14. MODAL FUNCTIONS
// ============================================================

// --- Create/Edit Modal ---
function openCreateModal() {
  const modal = DOM.inventoryModal();
  const title = DOM.modalTitle();
  const editId = DOM.editId();
  const form = DOM.inventoryForm();
  const submit = DOM.submitBtn();
  const stock = DOM.itemStock();
  const reorder = DOM.reorderLevel();

  if (title) title.textContent = "Add Inventory Item";
  if (editId) editId.value = "";
  if (form) form.reset();
  if (submit) submit.textContent = "Create Item";
  if (modal) modal.classList.add("active");
  if (stock) stock.value = 0;
  if (reorder) reorder.value = 5;

  loadSupplierOptions();
}

async function openEditModal(itemId) {
  const item = await InventoryAPI.fetchItemDetail(itemId);
  if (!item) return;

  const modal = DOM.inventoryModal();
  const title = DOM.modalTitle();
  const editId = DOM.editId();
  const submit = DOM.submitBtn();

  if (title) title.textContent = "Edit Inventory Item";
  if (editId) editId.value = itemId;
  if (submit) submit.textContent = "Update Item";

  // Fill form fields
  const fields = {
    itemName: item.name,
    itemCategory: item.category,
    itemSubCategory: item.sub_category,
    itemUnit: item.unit,
    itemStock: item.current_stock,
    reorderLevel: item.min_stock_threshold,
    itemCost: item.cost_price,
    itemSellingPrice: item.selling_price,
    itemSku: item.sku,
    itemBarcode: item.barcode,
    itemLocation: item.location,
    itemDescription: item.description,
  };

  for (const [key, value] of Object.entries(fields)) {
    const el = DOM[key]();
    if (el) el.value = value || "";
  }

  await loadSupplierOptions(item.supplier_id);
  if (modal) modal.classList.add("active");
}

function closeModal() {
  const modal = DOM.inventoryModal();
  const editId = DOM.editId();
  if (modal) modal.classList.remove("active");
  if (editId) editId.value = "";
}

async function loadSupplierOptions(selectedId = null) {
  const suppliers = await InventoryAPI.fetchSuppliers();
  const select = DOM.itemSupplier();
  if (!select) return;

  if (!suppliers || suppliers.length === 0) {
    select.innerHTML = '<option value="">No suppliers available</option>';
    return;
  }

  select.innerHTML = `
        <option value="">Select Supplier</option>
        ${suppliers
          .map(
            (s) => `
            <option value="${s.id}" ${selectedId === s.id ? "selected" : ""}>${escapeHtml(s.name)}</option>
        `,
          )
          .join("")}
    `;
}

async function handleFormSubmit(e) {
  e.preventDefault();

  const data = {
    name: DOM.itemName()?.value?.trim() || "",
    category: DOM.itemCategory()?.value || "",
    sub_category: DOM.itemSubCategory()?.value?.trim() || null,
    unit: DOM.itemUnit()?.value || "",
    current_stock: parseFloat(DOM.itemStock()?.value) || 0,
    min_stock_threshold: parseFloat(DOM.reorderLevel()?.value) || 5,
    cost_price: DOM.itemCost()?.value ? parseFloat(DOM.itemCost().value) : null,
    selling_price: DOM.itemSellingPrice()?.value
      ? parseFloat(DOM.itemSellingPrice().value)
      : null,
    sku: DOM.itemSku()?.value?.trim() || null,
    barcode: DOM.itemBarcode()?.value?.trim() || null,
    location: DOM.itemLocation()?.value?.trim() || null,
    supplier_id: DOM.itemSupplier()?.value || null,
    description: DOM.itemDescription()?.value?.trim() || null,
    status: "active",
  };

  if (!data.name) return showToast("Please enter item name", "error");
  if (!data.category) return showToast("Please select a category", "error");
  if (!data.unit) return showToast("Please select a unit", "error");

  const editId = DOM.editId()?.value || "";
  const result = editId
    ? await InventoryAPI.updateItem(editId, data)
    : await InventoryAPI.createItem(data);

  if (result) {
    showToast(editId ? "Item updated!" : "Item created!", "success");
    closeModal();
    await loadInventoryItems();
    if (state.selectedItemId) await selectItem(state.selectedItemId);
  }
}

// --- Stock Adjust Modal ---
async function openStockAdjustModal(itemId) {
  const item = await InventoryAPI.fetchItemDetail(itemId);
  if (!item) return;

  const modal = DOM.stockAdjustModal();
  const id = DOM.adjustItemId();
  const current = DOM.adjustCurrentStock();
  const newStock = DOM.adjustNewStock();
  const reason = DOM.adjustReasonSelect();
  const notes = DOM.adjustNotes();

  if (id) id.value = itemId;
  if (current) current.textContent = `${item.current_stock} ${item.unit || ""}`;
  if (newStock) newStock.value = item.current_stock || 0;
  if (reason) reason.value = "";
  if (notes) notes.value = "";
  if (modal) modal.classList.add("active");
}

function closeStockAdjustModal() {
  const modal = DOM.stockAdjustModal();
  const id = DOM.adjustItemId();
  if (modal) modal.classList.remove("active");
  if (id) id.value = "";
}

async function handleStockAdjust(e) {
  e.preventDefault();

  const itemId = DOM.adjustItemId()?.value;
  const newStock = parseFloat(DOM.adjustNewStock()?.value);
  const reason = DOM.adjustReasonSelect()?.value;
  const notes = DOM.adjustNotes()?.value?.trim() || "";

  if (!itemId) return showToast("No item selected", "error");
  if (isNaN(newStock) || newStock < 0)
    return showToast("Please enter a valid stock quantity", "error");
  if (!reason) return showToast("Please select a reason", "error");

  const result = await InventoryAPI.adjustStock({
    item_id: itemId,
    quantity: newStock,
    movement_type: reason,
    reference_type: "adjustment",
    note: notes || reason,
    performed_by: "admin",
  });

  if (result) {
    showToast("Stock updated successfully!", "success");
    closeStockAdjustModal();
    await loadInventoryItems();
    if (state.selectedItemId) await selectItem(state.selectedItemId);
  }
}

// --- History Modal ---
async function openHistoryModal(itemId) {
  const item = state.items.find((i) => i.id === itemId);
  if (!item) return showToast("Item not found", "error");

  const name = DOM.historyItemName();
  if (name) name.textContent = item.name;

  const movements = await InventoryAPI.fetchItemMovements(itemId);
  const body = DOM.historyBody();
  if (!body) return;

  if (!movements || movements.length === 0) {
    body.innerHTML =
      '<tr><td colspan="6" class="no-data">No movement history</td></tr>';
  } else {
    body.innerHTML = movements
      .map(
        (m) => `
            <tr>
                <td>${Formatter.dateTime(m.created_at)}</td>
                <td><span class="status-badge ${m.type === "in" ? "active" : "inactive"}">${escapeHtml(m.movement_type || m.type || "")}</span></td>
                <td><strong>${m.type === "in" ? "+" : "-"}${m.quantity}</strong></td>
                <td>${m.previous_stock || "-"}</td>
                <td>${m.new_stock || "-"}</td>
                <td>${escapeHtml(m.performed_by || "system")}</td>
            </tr>
        `,
      )
      .join("");
  }

  const modal = DOM.historyModal();
  if (modal) modal.classList.add("active");
}

function closeHistoryModal() {
  const modal = DOM.historyModal();
  if (modal) modal.classList.remove("active");
}

// --- Reorder Modal ---
async function openReorderModal(itemId) {
  const item = await InventoryAPI.fetchItemDetail(itemId);
  if (!item) return;

  const modal = DOM.reorderModal();
  const id = DOM.reorderItemId();
  const name = DOM.reorderItemName();
  const current = DOM.reorderCurrentStock();
  const threshold = DOM.reorderThreshold();
  const qty = DOM.reorderQuantity();

  if (id) id.value = itemId;
  if (name) name.textContent = item.name;
  if (current) current.textContent = `${item.current_stock} ${item.unit || ""}`;
  if (threshold)
    threshold.textContent = `${item.min_stock_threshold || 0} ${item.unit || ""}`;
  if (qty) {
    qty.value =
      Math.max((item.min_stock_threshold || 5) - (item.current_stock || 0), 0) +
      10;
  }

  const suppliers = await InventoryAPI.fetchSuppliers();
  const select = DOM.reorderSupplier();
  if (select) {
    if (suppliers && suppliers.length > 0) {
      select.innerHTML = `
                <option value="">Select Supplier</option>
                ${suppliers
                  .map(
                    (s) => `
                    <option value="${s.id}" ${s.id === item.supplier_id ? "selected" : ""}>${escapeHtml(s.name)}</option>
                `,
                  )
                  .join("")}
            `;
    } else {
      select.innerHTML = '<option value="">No suppliers available</option>';
    }
  }

  if (modal) modal.classList.add("active");
}

function closeReorderModal() {
  const modal = DOM.reorderModal();
  const id = DOM.reorderItemId();
  if (modal) modal.classList.remove("active");
  if (id) id.value = "";
}

async function handleReorderSubmit(e) {
  e.preventDefault();

  const itemId = DOM.reorderItemId()?.value;
  const quantity = parseFloat(DOM.reorderQuantity()?.value);
  const supplierId = DOM.reorderSupplier()?.value;

  if (!itemId) return showToast("No item selected", "error");
  if (!quantity || quantity <= 0)
    return showToast("Please enter a valid quantity", "error");

  const result = await InventoryAPI.createPurchaseOrder({
    supplier_id: supplierId || null,
    items: [{ item_id: itemId, quantity: quantity, unit_price: 0 }],
    notes: `Reorder for item ${itemId}`,
  });

  if (result) {
    showToast("Purchase order created successfully!", "success");
    closeReorderModal();
    await loadInventoryItems();
  }
}

// ============================================================
// 15. ACTION HANDLERS
// ============================================================

async function confirmDelete(itemId) {
  const item = state.items.find((i) => i.id === itemId);
  if (!item) return;

  if (
    !confirm(
      `Are you sure you want to delete "${item.name}"? This action cannot be undone.`,
    )
  )
    return;

  const result = await InventoryAPI.deleteItem(itemId);
  if (result) {
    showToast("Item deleted!", "success");
    if (state.selectedItemId === itemId) {
      state.selectedItemId = null;
      renderDetailPanel(null);
    }
    await loadInventoryItems();
  }
}

function filterByCategory(category) {
  const filter = DOM.categoryFilter();
  if (filter) {
    filter.value = category;
    filter.dispatchEvent(new Event("change"));
  }
}

// ============================================================
// 16. EXPORT FUNCTION
// ============================================================

function exportInventory() {
  const data = state.items.map((item) => ({
    name: item.name,
    category: item.category || "",
    sub_category: item.sub_category || "",
    sku: item.sku || "",
    unit: item.unit || "",
    current_stock: item.current_stock || 0,
    min_stock_threshold: item.min_stock_threshold || 0,
    cost_price: item.cost_price || 0,
    selling_price: item.selling_price || 0,
    value: (item.current_stock || 0) * (item.cost_price || 0),
    location: item.location || "",
    status: item.status || "active",
  }));

  const headers = [
    "Name",
    "Category",
    "Sub Category",
    "SKU",
    "Unit",
    "Stock",
    "Min Stock",
    "Cost Price",
    "Selling Price",
    "Total Value",
    "Location",
    "Status",
  ];
  const rows = data.map((d) => [
    d.name,
    d.category,
    d.sub_category,
    d.sku,
    d.unit,
    d.current_stock,
    d.min_stock_threshold,
    d.cost_price,
    d.selling_price,
    d.value,
    d.location,
    d.status,
  ]);

  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `inventory_export_${new Date().toISOString().split("T")[0]}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);

  showToast("Export completed!", "success");
}

// ============================================================
// 17. MAIN LOAD FUNCTION
// ============================================================

async function loadInventoryItems() {
  console.log("🔄 Loading inventory items...");

  const data = await InventoryAPI.fetchItems(state.currentPage, state.filters);

  if (!data) {
    const list = DOM.inventoryItemsList();
    if (list) {
      list.innerHTML = `
                <tr>
                    <td colspan="7" class="no-data">
                        <i class="fas fa-exclamation-triangle" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                        Failed to load inventory. Please try again.
                        <br><br>
                        <button class="btn-add-item" onclick="loadInventoryItems()">
                            <i class="fas fa-rotate"></i> Retry
                        </button>
                    </td>
                </tr>
            `;
    }
    return;
  }

  let items = data.data || data.items || data;
  let totalPages = data.total_pages || data.totalPages || 1;
  let totalItems = data.total || data.totalItems || items.length || 0;

  if (Array.isArray(data) && !data.data) {
    items = data;
    totalItems = items.length;
    totalPages = Math.ceil(totalItems / CONFIG.ITEMS_PER_PAGE);
  }

  state.items = items || [];
  state.totalPages = totalPages;
  state.totalItems = totalItems;

  renderItems(state.items);
  updatePagination(state.currentPage, state.totalPages, state.totalItems);

  // Load all side data in parallel
  const [stats, categories, alerts, movements] = await Promise.all([
    InventoryAPI.fetchStatistics(),
    InventoryAPI.fetchCategories(),
    InventoryAPI.fetchAlerts(),
    InventoryAPI.fetchRecentMovements(CONFIG.MAX_MOVEMENTS),
  ]);

  updateDashboard(stats);
  if (categories) {
    renderCategories(categories);
    updateCategoryFilter(categories);
  }
  renderAlerts(alerts);
  renderRecentMovements(movements);

  // Restore selected item if still exists
  if (state.selectedItemId) {
    const stillExists = state.items.find((i) => i.id === state.selectedItemId);
    if (stillExists) {
      await selectItem(state.selectedItemId);
    } else {
      state.selectedItemId = null;
      renderDetailPanel(null);
    }
  }

  console.log("✅ Inventory loaded successfully");
}

function updateCategoryFilter(categories) {
  if (!categories || categories.length === 0) return;
  const filter = DOM.categoryFilter();
  if (!filter) return;

  const currentValue = filter.value;
  filter.innerHTML = `
        <option value="">All Categories</option>
        ${categories
          .map(
            (cat) => `
            <option value="${cat}">${escapeHtml(cat)}</option>
        `,
          )
          .join("")}
    `;
  filter.value = currentValue || "";
}

// ============================================================
// 18. EVENT BINDINGS
// ============================================================

function bindEvents() {
  // Pagination
  DOM.prevPageBtn()?.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage--;
      loadInventoryItems();
    }
  });
  DOM.nextPageBtn()?.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      state.currentPage++;
      loadInventoryItems();
    }
  });

  // Search with debounce
  let searchTimeout;
  DOM.searchInventory()?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.currentPage = 1;
      loadInventoryItems();
    }, 300);
  });

  // Filters
  DOM.categoryFilter()?.addEventListener("change", (e) => {
    state.filters.category = e.target.value;
    state.currentPage = 1;
    loadInventoryItems();
  });
  DOM.stockFilter()?.addEventListener("change", (e) => {
    const value = e.target.value;
    state.filters.low_stock_only = value === "low" || value === "critical";
    state.filters.stock_status = value;
    state.currentPage = 1;
    loadInventoryItems();
  });
  DOM.statusFilter()?.addEventListener("change", (e) => {
    state.filters.status = e.target.value;
    state.currentPage = 1;
    loadInventoryItems();
  });

  // Buttons
  DOM.addItemBtn()?.addEventListener("click", openCreateModal);
  DOM.exportInventoryBtn()?.addEventListener("click", exportInventory);
  DOM.refreshAlertsBtn()?.addEventListener("click", async () => {
    const alerts = await InventoryAPI.fetchAlerts();
    renderAlerts(alerts);
    showToast("Alerts refreshed!", "success");
  });

  // Close modals
  DOM.closeInventoryModal()?.addEventListener("click", closeModal);
  DOM.cancelModalBtn()?.addEventListener("click", closeModal);
  DOM.inventoryModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.inventoryModal()) closeModal();
  });

  // Stock Adjust
  DOM.closeStockAdjustModal()?.addEventListener("click", closeStockAdjustModal);
  DOM.cancelStockAdjustBtn()?.addEventListener("click", closeStockAdjustModal);
  DOM.stockAdjustModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.stockAdjustModal()) closeStockAdjustModal();
  });

  // History
  DOM.closeHistoryModal()?.addEventListener("click", closeHistoryModal);
  DOM.closeHistoryModalBtn()?.addEventListener("click", closeHistoryModal);
  DOM.historyModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.historyModal()) closeHistoryModal();
  });

  // Reorder
  DOM.closeReorderModal()?.addEventListener("click", closeReorderModal);
  DOM.cancelReorderBtn()?.addEventListener("click", closeReorderModal);
  DOM.reorderModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.reorderModal()) closeReorderModal();
  });

  // Detail Panel Actions
  DOM.editItemBtn()?.addEventListener("click", () => {
    if (state.selectedItemId) openEditModal(state.selectedItemId);
  });
  DOM.deleteItemBtn()?.addEventListener("click", () => {
    if (state.selectedItemId) confirmDelete(state.selectedItemId);
  });
  DOM.adjustStockBtn()?.addEventListener("click", () => {
    if (state.selectedItemId) openStockAdjustModal(state.selectedItemId);
  });
  DOM.historyBtn()?.addEventListener("click", () => {
    if (state.selectedItemId) openHistoryModal(state.selectedItemId);
  });
  DOM.reorderBtn()?.addEventListener("click", () => {
    if (state.selectedItemId) openReorderModal(state.selectedItemId);
  });

  // Form submissions
  DOM.inventoryForm()?.addEventListener("submit", handleFormSubmit);
  DOM.stockAdjustForm()?.addEventListener("submit", handleStockAdjust);
  DOM.reorderForm()?.addEventListener("submit", handleReorderSubmit);
}

// ============================================================
// 19. KEYBOARD SHORTCUTS
// ============================================================

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (DOM.inventoryModal()?.classList.contains("active")) closeModal();
    if (DOM.stockAdjustModal()?.classList.contains("active"))
      closeStockAdjustModal();
    if (DOM.historyModal()?.classList.contains("active")) closeHistoryModal();
    if (DOM.reorderModal()?.classList.contains("active")) closeReorderModal();
  }
  if (e.ctrlKey && e.key === "n") {
    e.preventDefault();
    openCreateModal();
  }
  if (e.ctrlKey && e.key === "f") {
    e.preventDefault();
    DOM.searchInventory()?.focus();
  }
  if (e.ctrlKey && e.key === "e") {
    e.preventDefault();
    exportInventory();
  }
});

// ============================================================
// 20. INITIALIZATION
// ============================================================

async function init() {
  console.log("🚀 Initializing Inventory page...");
  bindEvents();
  await loadInventoryItems();
  console.log("📋 Inventory page initialized successfully");
}

// Run initialization
init();

// ============================================================
// 21. EXPOSE TO GLOBAL
// ============================================================

window.selectItem = selectItem;
window.openCreateModal = openCreateModal;
window.openEditModal = openEditModal;
window.openStockAdjustModal = openStockAdjustModal;
window.openHistoryModal = openHistoryModal;
window.openReorderModal = openReorderModal;
window.confirmDelete = confirmDelete;
window.filterByCategory = filterByCategory;
window.loadInventoryItems = loadInventoryItems;
window.closeModal = closeModal;
window.closeStockAdjustModal = closeStockAdjustModal;
window.closeHistoryModal = closeHistoryModal;
window.closeReorderModal = closeReorderModal;

console.log("📋 Inventory page fully loaded");
