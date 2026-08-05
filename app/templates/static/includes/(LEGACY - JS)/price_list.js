// ============================================================
// price_list.js - NOCTRA Price List Management
// Complete JavaScript for Price List management with API integration
// ============================================================

// ============================================================
// CONFIGURATION
// ============================================================
const API_BASE_URL = "/api/api";
const ITEMS_PER_PAGE = 10;

// ============================================================
// STATE
// ============================================================
let state = {
  items: [],
  currentPage: 1,
  totalPages: 1,
  totalItems: 0,
  editingId: null,
  filters: {
    search: "",
    category: "",
    status: "",
    vehicle_brand: "",
    active_only: true,
  },
  categories: [],
  isLoading: false,
};

// ============================================================
// DOM REFS
// ============================================================
const DOM = {
  // Dashboard
  totalItems: document.getElementById("totalItems"),
  activeItems: document.getElementById("activeItems"),
  expiringItems: document.getElementById("expiringItems"),
  categoryCount: document.getElementById("categoryCount"),

  // Toolbar
  searchPrice: document.getElementById("searchPrice"),
  categoryFilter: document.getElementById("categoryFilter"),
  statusFilter: document.getElementById("statusFilter"),
  vehicleFilter: document.getElementById("vehicleFilter"),
  exportPriceBtn: document.getElementById("exportPriceBtn"),
  addPriceBtn: document.getElementById("addPriceBtn"),

  // Table
  priceTableBody: document.getElementById("priceTableBody"),

  // Pagination
  prevPageBtn: document.getElementById("prevPageBtn"),
  nextPageBtn: document.getElementById("nextPageBtn"),
  pageInfo: document.getElementById("pageInfo"),

  // Price Modal
  priceModal: document.getElementById("priceModal"),
  modalTitle: document.getElementById("modalTitle"),
  modalSubtitle: document.getElementById("modalSubtitle"),
  editId: document.getElementById("editId"),
  priceForm: document.getElementById("priceForm"),
  category: document.getElementById("category"),
  subCategory: document.getElementById("subCategory"),
  name: document.getElementById("name"),
  price: document.getElementById("price"),
  costPrice: document.getElementById("costPrice"),
  unit: document.getElementById("unit"),
  sku: document.getElementById("sku"),
  vehicleBrand: document.getElementById("vehicleBrand"),
  vehicleModel: document.getElementById("vehicleModel"),
  effectiveDate: document.getElementById("effectiveDate"),
  expiryDate: document.getElementById("expiryDate"),
  minQuantity: document.getElementById("minQuantity"),
  maxQuantity: document.getElementById("maxQuantity"),
  discountPercentage: document.getElementById("discountPercentage"),
  estimatedDuration: document.getElementById("estimatedDuration"),
  isActive: document.getElementById("isActive"),
  isTaxable: document.getElementById("isTaxable"),
  isDiscountAllowed: document.getElementById("isDiscountAllowed"),
  description: document.getElementById("description"),
  submitBtn: document.getElementById("submitBtn"),
  cancelModalBtn: document.getElementById("cancelModalBtn"),
  closeModalBtn: document.getElementById("closeModalBtn"),

  // History Modal
  historyModal: document.getElementById("historyModal"),
  historyItemName: document.getElementById("historyItemName"),
  historyBody: document.getElementById("historyBody"),
  totalChanges: document.getElementById("totalChanges"),
  currentPrice: document.getElementById("currentPrice"),
  firstPrice: document.getElementById("firstPrice"),
  avgChange: document.getElementById("avgChange"),
  closeHistoryModal: document.getElementById("closeHistoryModal"),
  closeHistoryModalBtn: document.getElementById("closeHistoryModalBtn"),

  // Bulk Modal
  bulkModal: document.getElementById("bulkModal"),
  bulkForm: document.getElementById("bulkForm"),
  bulkCategory: document.getElementById("bulkCategory"),
  bulkPercentage: document.getElementById("bulkPercentage"),
  bulkVehicleBrand: document.getElementById("bulkVehicleBrand"),
  bulkReason: document.getElementById("bulkReason"),
  bulkPreview: document.getElementById("bulkPreview"),
  bulkPreviewText: document.getElementById("bulkPreviewText"),
  cancelBulkBtn: document.getElementById("cancelBulkBtn"),
  closeBulkModal: document.getElementById("closeBulkModal"),

  // Toast
  toastContainer: document.getElementById("toastContainer"),
};

// ============================================================
// TOAST SYSTEM
// ============================================================
function showToast(message, type = "info", duration = 4000) {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
        <span>${message}</span>
        <button class="toast-close">&times;</button>
    `;
  DOM.toastContainer.appendChild(toast);

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
// FORMATTERS
// ============================================================
function formatCurrency(amount) {
  if (!amount && amount !== 0) return "-";
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Number(amount));
}

function formatDate(dateString) {
  if (!dateString) return "-";
  const date = new Date(dateString);
  return date.toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatDateTime(dateString) {
  if (!dateString) return "-";
  const date = new Date(dateString);
  return date.toLocaleString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getCategoryBadgeClass(category) {
  const map = {
    service: "service",
    material: "material",
    labor: "labor",
    bike_model: "bike_model",
    paint: "paint",
    finish: "finish",
    accessory: "accessory",
  };
  return map[category] || "";
}

function getCategoryLabel(category) {
  const map = {
    service: "Service",
    material: "Material",
    labor: "Labor",
    bike_model: "Bike Model",
    paint: "Paint",
    finish: "Finish",
    accessory: "Accessory",
  };
  return map[category] || category;
}

function getStatusLabel(status) {
  return status === "active" ? "Active" : "Inactive";
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ============================================================
// API HELPERS
// ============================================================
async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
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
// PRICE LIST API CALLS
// ============================================================

async function fetchPriceItems(page = 1, filters = {}) {
  state.isLoading = true;
  showLoadingState();

  const params = new URLSearchParams({
    page: page,
    limit: ITEMS_PER_PAGE,
    active_only: filters.active_only !== undefined ? filters.active_only : true,
  });

  // Add filters with proper handling
  if (filters.search) params.append("search", filters.search);
  if (filters.category) params.append("category", filters.category);
  if (filters.vehicle_brand)
    params.append("vehicle_brand", filters.vehicle_brand);
  if (filters.vehicle_model)
    params.append("vehicle_model", filters.vehicle_model);

  // Handle status filter
  if (filters.status) {
    if (filters.status === "active") {
      params.set("active_only", "true");
    } else if (filters.status === "inactive") {
      params.set("active_only", "false");
    }
    // If status is empty, remove active_only filter
    if (filters.status === "") {
      params.delete("active_only");
    }
  }

  console.log("📡 Fetching price items with params:", params.toString());

  try {
    const response = await apiFetch(`/price-list/items/?${params.toString()}`);
    console.log("📦 API Response:", response);
    return response;
  } catch (error) {
    console.error("❌ Failed to load price items:", error);
    showToast("Failed to load price items: " + error.message, "error");
    return null;
  } finally {
    state.isLoading = false;
  }
}

async function fetchPriceItemDetail(itemId) {
  try {
    const response = await apiFetch(`/price-list/items/${itemId}`);
    return response.data;
  } catch (error) {
    showToast("Failed to load item details: " + error.message, "error");
    return null;
  }
}

async function createPriceItem(data) {
  try {
    const response = await apiFetch("/price-list/items/", {
      method: "POST",
      body: JSON.stringify(data),
    });
    return response.data;
  } catch (error) {
    showToast("Failed to create price item: " + error.message, "error");
    return null;
  }
}

async function updatePriceItem(itemId, data) {
  try {
    const response = await apiFetch(`/price-list/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
    return response.data;
  } catch (error) {
    showToast("Failed to update price item: " + error.message, "error");
    return null;
  }
}

async function deletePriceItem(itemId) {
  try {
    const response = await apiFetch(`/price-list/items/${itemId}`, {
      method: "DELETE",
    });
    return response.data;
  } catch (error) {
    showToast("Failed to delete price item: " + error.message, "error");
    return null;
  }
}

async function togglePriceItem(itemId) {
  try {
    const response = await apiFetch(`/price-list/items/${itemId}/toggle`, {
      method: "POST",
    });
    return response.data;
  } catch (error) {
    showToast("Failed to toggle item status: " + error.message, "error");
    return null;
  }
}

async function fetchPriceHistory(itemId, limit = 50) {
  try {
    const response = await apiFetch(
      `/price-list/items/${itemId}/price-history?limit=${limit}`,
    );
    return response.data;
  } catch (error) {
    showToast("Failed to load price history: " + error.message, "error");
    return null;
  }
}

async function changePrice(itemId, newPrice, reason = "") {
  try {
    const response = await apiFetch(
      `/price-list/items/${itemId}/change-price`,
      {
        method: "POST",
        body: JSON.stringify({
          request: { new_price: newPrice, reason },
          changed_by: "admin",
        }),
      },
    );
    return response.data;
  } catch (error) {
    showToast("Failed to change price: " + error.message, "error");
    return null;
  }
}

async function fetchStatistics() {
  try {
    const response = await apiFetch("/price-list/stats");
    return response.data;
  } catch (error) {
    console.error("Failed to load statistics:", error);
    return null;
  }
}

async function fetchCategories() {
  try {
    const response = await apiFetch("/price-list/categories/with-counts");
    return response.data;
  } catch (error) {
    console.error("Failed to load categories:", error);
    return null;
  }
}

async function bulkUpdatePrices(data) {
  try {
    const response = await apiFetch("/price-list/items/bulk-update-prices", {
      method: "POST",
      body: JSON.stringify(data),
    });
    return response.data;
  } catch (error) {
    showToast("Failed to bulk update prices: " + error.message, "error");
    return null;
  }
}

// ============================================================
// RENDER FUNCTIONS
// ============================================================

function showLoadingState() {
  if (DOM.priceTableBody) {
    DOM.priceTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="loading-placeholder">
                    <i class="fas fa-spinner fa-spin"></i> Loading prices...
                </td>
            </tr>
        `;
  }
}

function renderItems(items) {
  console.log("🎨 Rendering items:", items);

  if (!items || items.length === 0) {
    DOM.priceTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="no-data">
                    <i class="fas fa-box-open" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                    No price items found
                    <br><br>
                    <button class="btn-primary" onclick="openCreateModal()">
                        <i class="fas fa-plus"></i> Add your first price item
                    </button>
                </td>
            </tr>
        `;
    return;
  }

  DOM.priceTableBody.innerHTML = items
    .map(
      (item) => `
        <tr class="fade-in">
            <td>
                <span class="category-badge ${getCategoryBadgeClass(item.category)}">
                    ${getCategoryLabel(item.category)}
                </span>
                ${item.sub_category ? `<br><small style="color:var(--text-muted);font-size:0.7rem;">${escapeHtml(item.sub_category)}</small>` : ""}
            </td>
            <td>
                <strong style="color:var(--text-primary);">${escapeHtml(item.name)}</strong>
                ${item.sku ? `<br><small style="color:var(--text-muted);font-size:0.7rem;">SKU: ${escapeHtml(item.sku)}</small>` : ""}
            </td>
            <td style="max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                ${escapeHtml(item.description || "-")}
            </td>
            <td style="font-weight:600; color:var(--text-primary);">
                ${formatCurrency(item.price)}
                ${item.cost_price ? `<br><small style="color:var(--text-muted);font-weight:400;font-size:0.7rem;">Cost: ${formatCurrency(item.cost_price)}</small>` : ""}
            </td>
            <td>${escapeHtml(item.unit || "-")}</td>
            <td>
                ${item.vehicle_brand ? escapeHtml(item.vehicle_brand) : "-"}
                ${item.vehicle_model ? `<br><small style="color:var(--text-muted);font-size:0.7rem;">${escapeHtml(item.vehicle_model)}</small>` : ""}
            </td>
            <td>
                <span class="status-badge ${item.is_active ? "active" : "inactive"}">
                    ${item.is_active ? "Active" : "Inactive"}
                </span>
                ${item.is_expired ? '<br><small style="color:#ef4444;font-size:0.65rem;">Expired</small>' : ""}
            </td>
            <td style="text-align:center; white-space:nowrap;">
                <button class="action-btn history-btn" onclick="openHistoryModal('${item.id}')" title="Price History">
                    <i class="fas fa-history"></i>
                </button>
                <button class="action-btn edit-btn" onclick="openEditModal('${item.id}')" title="Edit">
                    <i class="fas fa-pen"></i>
                </button>
                <button class="action-btn delete-btn" onclick="confirmDelete('${item.id}')" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `,
    )
    .join("");

  console.log(`✅ Rendered ${items.length} items`);
}

function updatePagination(page, totalPages, totalItems) {
  console.log("📄 Updating pagination:", { page, totalPages, totalItems });

  if (DOM.pageInfo) {
    DOM.pageInfo.textContent = `Page ${page} of ${totalPages || 1} (${totalItems} items)`;
  }

  if (DOM.prevPageBtn) {
    DOM.prevPageBtn.disabled = page <= 1;
    DOM.prevPageBtn.style.opacity = page <= 1 ? "0.5" : "1";
    DOM.prevPageBtn.style.cursor = page <= 1 ? "not-allowed" : "pointer";
  }

  if (DOM.nextPageBtn) {
    DOM.nextPageBtn.disabled = page >= totalPages || totalPages === 0;
    DOM.nextPageBtn.style.opacity =
      page >= totalPages || totalPages === 0 ? "0.5" : "1";
    DOM.nextPageBtn.style.cursor =
      page >= totalPages || totalPages === 0 ? "not-allowed" : "pointer";
  }
}

function updateDashboard(stats) {
  if (!stats) return;
  if (DOM.totalItems) DOM.totalItems.textContent = stats.total_items || 0;
  if (DOM.activeItems) DOM.activeItems.textContent = stats.active_items || 0;
  if (DOM.expiringItems)
    DOM.expiringItems.textContent = stats.expiring_soon || 0;
  if (DOM.categoryCount)
    DOM.categoryCount.textContent = stats.total_categories || 0;
}

function updateCategoryFilter(categories) {
  if (!categories || categories.length === 0) return;

  const currentValue = DOM.categoryFilter ? DOM.categoryFilter.value : "";
  if (DOM.categoryFilter) {
    DOM.categoryFilter.innerHTML = `
            <option value="">All Categories</option>
            ${categories
              .map(
                (cat) => `
                <option value="${cat.name}">${cat.display_name || cat.name} (${cat.item_count || 0})</option>
            `,
              )
              .join("")}
        `;
    DOM.categoryFilter.value = currentValue || "";
  }
}

// ============================================================
// MODAL FUNCTIONS
// ============================================================

// -------- Create/Edit Modal --------
function openCreateModal() {
  if (DOM.modalTitle) DOM.modalTitle.textContent = "Add Price Item";
  if (DOM.modalSubtitle)
    DOM.modalSubtitle.textContent = "Create a new price list item";
  if (DOM.editId) DOM.editId.value = "";
  if (DOM.priceForm) DOM.priceForm.reset();
  if (DOM.isActive) DOM.isActive.checked = true;
  if (DOM.isTaxable) DOM.isTaxable.checked = true;
  if (DOM.isDiscountAllowed) DOM.isDiscountAllowed.checked = true;
  if (DOM.effectiveDate)
    DOM.effectiveDate.value = new Date().toISOString().split("T")[0];
  if (DOM.submitBtn) DOM.submitBtn.textContent = "Create";
  if (DOM.priceModal) DOM.priceModal.classList.add("active");
}

async function openEditModal(itemId) {
  const item = await fetchPriceItemDetail(itemId);
  if (!item) return;

  if (DOM.modalTitle) DOM.modalTitle.textContent = "Edit Price Item";
  if (DOM.modalSubtitle)
    DOM.modalSubtitle.textContent = `Editing: ${item.name}`;
  if (DOM.editId) DOM.editId.value = itemId;
  if (DOM.submitBtn) DOM.submitBtn.textContent = "Update";

  // Fill form
  if (DOM.category) DOM.category.value = item.category || "";
  if (DOM.subCategory) DOM.subCategory.value = item.sub_category || "";
  if (DOM.name) DOM.name.value = item.name || "";
  if (DOM.price) DOM.price.value = item.price || "";
  if (DOM.costPrice) DOM.costPrice.value = item.cost_price || "";
  if (DOM.unit) DOM.unit.value = item.unit || "";
  if (DOM.sku) DOM.sku.value = item.sku || "";
  if (DOM.vehicleBrand) DOM.vehicleBrand.value = item.vehicle_brand || "";
  if (DOM.vehicleModel) DOM.vehicleModel.value = item.vehicle_model || "";
  if (DOM.effectiveDate)
    DOM.effectiveDate.value = item.effective_date
      ? item.effective_date.split("T")[0]
      : "";
  if (DOM.expiryDate)
    DOM.expiryDate.value = item.expiry_date
      ? item.expiry_date.split("T")[0]
      : "";
  if (DOM.minQuantity) DOM.minQuantity.value = item.min_quantity || "";
  if (DOM.maxQuantity) DOM.maxQuantity.value = item.max_quantity || "";
  if (DOM.discountPercentage)
    DOM.discountPercentage.value = item.discount_percentage || "";
  if (DOM.estimatedDuration)
    DOM.estimatedDuration.value = item.estimated_duration_hours || "";
  if (DOM.isActive) DOM.isActive.checked = item.is_active !== false;
  if (DOM.isTaxable) DOM.isTaxable.checked = item.is_taxable !== false;
  if (DOM.isDiscountAllowed)
    DOM.isDiscountAllowed.checked = item.is_discount_allowed !== false;
  if (DOM.description) DOM.description.value = item.description || "";

  if (DOM.priceModal) DOM.priceModal.classList.add("active");
}

function closeModal() {
  if (DOM.priceModal) DOM.priceModal.classList.remove("active");
  if (DOM.editId) DOM.editId.value = "";
}

async function handleFormSubmit(e) {
  e.preventDefault();

  const data = {
    category: DOM.category ? DOM.category.value : "",
    sub_category: DOM.subCategory ? DOM.subCategory.value || null : null,
    name: DOM.name ? DOM.name.value.trim() : "",
    price: DOM.price ? parseFloat(DOM.price.value) : 0,
    cost_price:
      DOM.costPrice && DOM.costPrice.value
        ? parseFloat(DOM.costPrice.value)
        : null,
    unit: DOM.unit ? DOM.unit.value || null : null,
    sku: DOM.sku ? DOM.sku.value || null : null,
    vehicle_brand: DOM.vehicleBrand ? DOM.vehicleBrand.value || null : null,
    vehicle_model: DOM.vehicleModel ? DOM.vehicleModel.value || null : null,
    effective_date: DOM.effectiveDate ? DOM.effectiveDate.value || null : null,
    expiry_date: DOM.expiryDate ? DOM.expiryDate.value || null : null,
    min_quantity:
      DOM.minQuantity && DOM.minQuantity.value
        ? parseInt(DOM.minQuantity.value)
        : null,
    max_quantity:
      DOM.maxQuantity && DOM.maxQuantity.value
        ? parseInt(DOM.maxQuantity.value)
        : null,
    discount_percentage:
      DOM.discountPercentage && DOM.discountPercentage.value
        ? parseFloat(DOM.discountPercentage.value)
        : null,
    estimated_duration_hours:
      DOM.estimatedDuration && DOM.estimatedDuration.value
        ? parseFloat(DOM.estimatedDuration.value)
        : null,
    is_active: DOM.isActive ? DOM.isActive.checked : true,
    is_taxable: DOM.isTaxable ? DOM.isTaxable.checked : true,
    is_discount_allowed: DOM.isDiscountAllowed
      ? DOM.isDiscountAllowed.checked
      : true,
    description: DOM.description ? DOM.description.value.trim() || null : null,
  };

  // Validate
  if (!data.category) {
    showToast("Please select a category", "error");
    return;
  }
  if (!data.name) {
    showToast("Please enter a name", "error");
    return;
  }
  if (!data.price || data.price < 0) {
    showToast("Please enter a valid price", "error");
    return;
  }

  const editId = DOM.editId ? DOM.editId.value : "";
  let result;

  if (editId) {
    result = await updatePriceItem(editId, data);
  } else {
    result = await createPriceItem(data);
  }

  if (result) {
    showToast(
      editId ? "Price item updated!" : "Price item created!",
      "success",
    );
    closeModal();
    await loadPriceItems();
  }
}

// -------- History Modal --------
async function openHistoryModal(itemId) {
  const history = await fetchPriceHistory(itemId);
  if (!history) return;

  const item = state.items.find((i) => i.id === itemId);
  if (DOM.historyItemName)
    DOM.historyItemName.textContent = item ? item.name : "Item";

  // Summary
  if (DOM.totalChanges) DOM.totalChanges.textContent = history.length || 0;
  if (DOM.currentPrice)
    DOM.currentPrice.textContent =
      history.length > 0
        ? formatCurrency(history[history.length - 1]?.new_price)
        : "-";
  if (DOM.firstPrice)
    DOM.firstPrice.textContent =
      history.length > 0 ? formatCurrency(history[0]?.new_price) : "-";

  // Calculate average change
  let totalChange = 0;
  history.forEach((h) => {
    const change = (h.new_price || 0) - (h.old_price || 0);
    totalChange += change;
  });
  const avgChange = history.length > 0 ? totalChange / history.length : 0;
  if (DOM.avgChange) DOM.avgChange.textContent = formatCurrency(avgChange);

  // Render history rows
  if (!history || history.length === 0) {
    if (DOM.historyBody) {
      DOM.historyBody.innerHTML =
        '<tr><td colspan="6" class="no-data">No price history available</td></tr>';
    }
  } else {
    if (DOM.historyBody) {
      DOM.historyBody.innerHTML = history
        .map((h) => {
          const oldPrice = h.old_price || 0;
          const newPrice = h.new_price || 0;
          const change = newPrice - oldPrice;
          const changePercent =
            oldPrice > 0 ? ((change / oldPrice) * 100).toFixed(1) : 0;

          return `
                    <tr>
                        <td>${formatDateTime(h.changed_at || h.created_at)}</td>
                        <td>${formatCurrency(oldPrice)}</td>
                        <td><strong>${formatCurrency(newPrice)}</strong></td>
                        <td style="color:${change >= 0 ? "var(--success, #10b981)" : "var(--danger, #ef4444)"};">
                            ${change >= 0 ? "+" : ""}${formatCurrency(change)} (${change >= 0 ? "+" : ""}${changePercent}%)
                        </td>
                        <td>${escapeHtml(h.changed_by || "system")}</td>
                        <td style="max-width:150px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                            ${escapeHtml(h.reason || "-")}
                        </td>
                    </tr>
                `;
        })
        .join("");
    }
  }

  if (DOM.historyModal) DOM.historyModal.classList.add("active");
}

function closeHistoryModal() {
  if (DOM.historyModal) DOM.historyModal.classList.remove("active");
}

// -------- Bulk Update Modal --------
function openBulkModal() {
  if (DOM.bulkForm) DOM.bulkForm.reset();
  if (DOM.bulkPreview) DOM.bulkPreview.style.display = "none";
  if (DOM.bulkModal) DOM.bulkModal.classList.add("active");
}

function closeBulkModal() {
  if (DOM.bulkModal) DOM.bulkModal.classList.remove("active");
}

async function handleBulkSubmit(e) {
  e.preventDefault();

  const category = DOM.bulkCategory ? DOM.bulkCategory.value : "";
  const percentage = DOM.bulkPercentage
    ? parseFloat(DOM.bulkPercentage.value)
    : 0;
  const vehicleBrand = DOM.bulkVehicleBrand
    ? DOM.bulkVehicleBrand.value || null
    : null;

  if (!category) {
    showToast("Please select a category", "error");
    return;
  }
  if (!percentage || isNaN(percentage)) {
    showToast("Please enter a valid percentage", "error");
    return;
  }

  // Count items that will be affected
  const affectedItems = state.items.filter(
    (item) =>
      item.category === category &&
      item.is_active !== false &&
      (!vehicleBrand || item.vehicle_brand === vehicleBrand),
  );

  if (affectedItems.length === 0) {
    showToast("No active items found matching the criteria", "warning");
    return;
  }

  if (
    !confirm(`Update ${affectedItems.length} items with ${percentage}% change?`)
  )
    return;

  const result = await bulkUpdatePrices({
    category,
    percentage,
    vehicle_brand: vehicleBrand,
  });

  if (result) {
    showToast(`Successfully updated ${affectedItems.length} items!`, "success");
    closeBulkModal();
    await loadPriceItems();
  }
}

// Show preview when bulk form changes
if (DOM.bulkCategory) {
  DOM.bulkCategory.addEventListener("change", updateBulkPreview);
}
if (DOM.bulkVehicleBrand) {
  DOM.bulkVehicleBrand.addEventListener("change", updateBulkPreview);
}

function updateBulkPreview() {
  const category = DOM.bulkCategory ? DOM.bulkCategory.value : "";
  const vehicleBrand = DOM.bulkVehicleBrand
    ? DOM.bulkVehicleBrand.value || null
    : null;

  if (!category) {
    if (DOM.bulkPreview) DOM.bulkPreview.style.display = "none";
    return;
  }

  const count = state.items.filter(
    (item) =>
      item.category === category &&
      item.is_active !== false &&
      (!vehicleBrand || item.vehicle_brand === vehicleBrand),
  ).length;

  if (DOM.bulkPreviewText) {
    DOM.bulkPreviewText.textContent = `${count} items will be updated (${count > 0 ? "active" : "no active"} items)`;
  }
  if (DOM.bulkPreview) {
    DOM.bulkPreview.style.display = "block";
    DOM.bulkPreview.style.borderColor =
      count > 0 ? "var(--success)" : "var(--danger)";
  }
}

// ============================================================
// ACTION HANDLERS
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

  const result = await deletePriceItem(itemId);
  if (result) {
    showToast("Price item deleted!", "success");
    await loadPriceItems();
  }
}

async function handleToggleStatus(itemId) {
  const result = await togglePriceItem(itemId);
  if (result) {
    showToast("Status toggled!", "success");
    await loadPriceItems();
  }
}

// ============================================================
// EXPORT FUNCTION
// ============================================================

function exportPriceItems() {
  const data = state.items.map((item) => ({
    category: getCategoryLabel(item.category),
    sub_category: item.sub_category || "",
    name: item.name,
    description: item.description || "",
    price: item.price || 0,
    cost_price: item.cost_price || 0,
    unit: item.unit || "",
    sku: item.sku || "",
    vehicle_brand: item.vehicle_brand || "",
    vehicle_model: item.vehicle_model || "",
    status: item.is_active ? "Active" : "Inactive",
    effective_date: formatDate(item.effective_date),
    expiry_date: formatDate(item.expiry_date),
  }));

  const csv = [
    [
      "Category",
      "Sub Category",
      "Name",
      "Description",
      "Price",
      "Cost Price",
      "Unit",
      "SKU",
      "Vehicle Brand",
      "Vehicle Model",
      "Status",
      "Effective Date",
      "Expiry Date",
    ],
    ...data.map((d) => [
      d.category,
      d.sub_category,
      d.name,
      d.description,
      d.price,
      d.cost_price,
      d.unit,
      d.sku,
      d.vehicle_brand,
      d.vehicle_model,
      d.status,
      d.effective_date,
      d.expiry_date,
    ]),
  ]
    .map((row) => row.join(","))
    .join("\n");

  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `price_list_export_${new Date().toISOString().split("T")[0]}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);

  showToast("Export completed!", "success");
}

// ============================================================
// MAIN LOAD FUNCTION
// ============================================================

async function loadPriceItems() {
  console.log("🔄 Loading price items...");
  console.log("📊 Current state:", {
    page: state.currentPage,
    filters: state.filters,
  });

  const data = await fetchPriceItems(state.currentPage, state.filters);

  if (!data) {
    console.error("❌ No data received from API");
    if (DOM.priceTableBody) {
      DOM.priceTableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="no-data">
                        <i class="fas fa-exclamation-triangle" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                        Failed to load price items. Please try again.
                        <br><br>
                        <button class="btn-primary" onclick="loadPriceItems()">
                            <i class="fas fa-rotate"></i> Retry
                        </button>
                    </td>
                </tr>
            `;
    }
    // Reset pagination
    updatePagination(1, 1, 0);
    return;
  }

  // Handle different response structures
  let items = [];
  let totalPages = 1;
  let totalItems = 0;

  // Check if data has nested structure
  if (data.data) {
    // Response from API with nested data
    items = Array.isArray(data.data) ? data.data : [data.data];
    totalItems =
      data.total || data.total_items || data.totalItems || items.length;
    totalPages =
      data.total_pages ||
      data.totalPages ||
      data.pages ||
      Math.ceil(totalItems / ITEMS_PER_PAGE);
  } else if (Array.isArray(data)) {
    // Response is direct array
    items = data;
    totalItems = items.length;
    totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
  } else if (data.items) {
    // Response has items property
    items = Array.isArray(data.items) ? data.items : [data.items];
    totalItems =
      data.total || data.total_items || data.totalItems || items.length;
    totalPages =
      data.total_pages ||
      data.totalPages ||
      Math.ceil(totalItems / ITEMS_PER_PAGE);
  } else {
    // Try to use data as is
    items = Array.isArray(data) ? data : [];
    totalItems = items.length;
    totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
  }

  console.log("📊 Processing data:", {
    itemsCount: items.length,
    totalPages,
    totalItems,
  });

  state.items = items || [];
  state.totalPages = Math.max(1, totalPages);
  state.totalItems = totalItems;

  // Render items
  renderItems(state.items);

  // Update pagination
  updatePagination(state.currentPage, state.totalPages, state.totalItems);

  // Load statistics
  const stats = await fetchStatistics();
  updateDashboard(stats);

  // Load categories for filter
  const categories = await fetchCategories();
  if (categories) {
    updateCategoryFilter(categories);
  }

  console.log("✅ Price items loaded successfully");
}

// ============================================================
// EVENT HANDLERS
// ============================================================

// Pagination
if (DOM.prevPageBtn) {
  DOM.prevPageBtn.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage--;
      loadPriceItems();
    }
  });
}

if (DOM.nextPageBtn) {
  DOM.nextPageBtn.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      state.currentPage++;
      loadPriceItems();
    }
  });
}

// Search & Filters
let searchTimeout;
if (DOM.searchPrice) {
  DOM.searchPrice.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.currentPage = 1;
      loadPriceItems();
    }, 300);
  });
}

if (DOM.categoryFilter) {
  DOM.categoryFilter.addEventListener("change", (e) => {
    state.filters.category = e.target.value;
    state.currentPage = 1;
    loadPriceItems();
  });
}

if (DOM.statusFilter) {
  DOM.statusFilter.addEventListener("change", (e) => {
    const value = e.target.value;
    state.filters.status = value;
    state.filters.active_only = value === "" ? true : value === "active";
    state.currentPage = 1;
    loadPriceItems();
  });
}

if (DOM.vehicleFilter) {
  DOM.vehicleFilter.addEventListener("change", (e) => {
    state.filters.vehicle_brand = e.target.value;
    state.currentPage = 1;
    loadPriceItems();
  });
}

// Buttons
if (DOM.addPriceBtn) {
  DOM.addPriceBtn.addEventListener("click", openCreateModal);
}
if (DOM.exportPriceBtn) {
  DOM.exportPriceBtn.addEventListener("click", exportPriceItems);
}

// Close modal
if (DOM.closeModalBtn) {
  DOM.closeModalBtn.addEventListener("click", closeModal);
}
if (DOM.cancelModalBtn) {
  DOM.cancelModalBtn.addEventListener("click", closeModal);
}
if (DOM.priceModal) {
  DOM.priceModal.addEventListener("click", (e) => {
    if (e.target === DOM.priceModal) closeModal();
  });
}

// Close history modal
if (DOM.closeHistoryModal) {
  DOM.closeHistoryModal.addEventListener("click", closeHistoryModal);
}
if (DOM.closeHistoryModalBtn) {
  DOM.closeHistoryModalBtn.addEventListener("click", closeHistoryModal);
}
if (DOM.historyModal) {
  DOM.historyModal.addEventListener("click", (e) => {
    if (e.target === DOM.historyModal) closeHistoryModal();
  });
}

// Close bulk modal
if (DOM.closeBulkModal) {
  DOM.closeBulkModal.addEventListener("click", closeBulkModal);
}
if (DOM.cancelBulkBtn) {
  DOM.cancelBulkBtn.addEventListener("click", closeBulkModal);
}
if (DOM.bulkModal) {
  DOM.bulkModal.addEventListener("click", (e) => {
    if (e.target === DOM.bulkModal) closeBulkModal();
  });
}

// Form submissions
if (DOM.priceForm) {
  DOM.priceForm.addEventListener("submit", handleFormSubmit);
}
if (DOM.bulkForm) {
  DOM.bulkForm.addEventListener("submit", handleBulkSubmit);
}

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================
document.addEventListener("keydown", (e) => {
  // Escape to close modals
  if (e.key === "Escape") {
    if (DOM.priceModal && DOM.priceModal.classList.contains("active")) {
      closeModal();
    }
    if (DOM.historyModal && DOM.historyModal.classList.contains("active")) {
      closeHistoryModal();
    }
    if (DOM.bulkModal && DOM.bulkModal.classList.contains("active")) {
      closeBulkModal();
    }
  }

  // Ctrl+N to create new item
  if (e.ctrlKey && e.key === "n") {
    e.preventDefault();
    openCreateModal();
  }

  // Ctrl+F to focus search
  if (e.ctrlKey && e.key === "f") {
    e.preventDefault();
    if (DOM.searchPrice) DOM.searchPrice.focus();
  }

  // Ctrl+E to export
  if (e.ctrlKey && e.key === "e") {
    e.preventDefault();
    exportPriceItems();
  }

  // Ctrl+B for bulk update
  if (e.ctrlKey && e.key === "b") {
    e.preventDefault();
    openBulkModal();
  }
});

// ============================================================
// ADDITIONAL CSS FOR TOASTS & STYLES
// ============================================================
const style = document.createElement("style");
style.textContent = `
    /* Toast Styles */
    #toastContainer {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 99999;
        display: flex;
        flex-direction: column;
        gap: 10px;
        max-width: 400px;
    }

    .toast {
        padding: 14px 20px;
        border-radius: var(--radius-md);
        background: var(--bg-card);
        border: 1px solid var(--border);
        box-shadow: var(--shadow-lg);
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        animation: slideInRight 0.3s ease;
        min-width: 280px;
        font-size: 0.9rem;
        color: var(--text-primary);
        transition: opacity 0.3s ease, transform 0.3s ease;
    }

    .toast-success {
        border-left: 4px solid var(--success, #10b981);
    }
    .toast-error {
        border-left: 4px solid var(--danger, #ef4444);
    }
    .toast-info {
        border-left: 4px solid var(--primary, #3b82f6);
    }
    .toast-warning {
        border-left: 4px solid var(--warning, #f59e0b);
    }

    .toast .toast-close {
        background: none;
        border: none;
        color: var(--text-muted);
        font-size: 1.3rem;
        cursor: pointer;
        padding: 0 4px;
        line-height: 1;
    }

    .toast .toast-close:hover {
        color: var(--text-primary);
    }

    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @media (max-width: 480px) {
        #toastContainer {
            right: 10px;
            left: 10px;
            max-width: none;
        }
        .toast {
            min-width: unset;
            font-size: 0.85rem;
            padding: 12px 16px;
        }
    }

    /* Additional table styles */
    .table-wrapper .table-container .no-data {
        text-align: center;
        padding: 2rem 0;
        color: var(--text-muted);
    }
    .table-wrapper .table-container .loading-placeholder {
        text-align: center;
        padding: 2rem 0;
        color: var(--text-muted);
    }
    .table-wrapper .table-container .loading-placeholder i {
        font-size: 1.5rem;
        display: block;
        margin-bottom: 0.5rem;
    }
    .fade-in {
        animation: fadeIn 0.3s ease;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Pagination Styles */
    .pagination-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 20px;
        border-top: 1px solid var(--border, #e5e7eb);
        background: var(--bg-card, #fff);
        border-radius: 0 0 var(--radius-md) var(--radius-md);
        flex-wrap: wrap;
        gap: 12px;
    }

    .pagination-info {
        color: var(--text-muted, #6b7280);
        font-size: 0.875rem;
    }

    .pagination-buttons {
        display: flex;
        gap: 8px;
    }

    .pagination-btn {
        padding: 8px 16px;
        background: var(--bg-secondary, #f3f4f6);
        border: 1px solid var(--border, #e5e7eb);
        border-radius: var(--radius-sm);
        color: var(--text-primary, #111827);
        cursor: pointer;
        font-size: 0.875rem;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .pagination-btn:hover:not(:disabled) {
        background: var(--primary, #3b82f6);
        color: white;
        border-color: var(--primary, #3b82f6);
    }

    .pagination-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    @media (max-width: 600px) {
        .pagination-container {
            flex-direction: column;
            align-items: stretch;
            text-align: center;
        }
        
        .pagination-buttons {
            justify-content: center;
        }
    }
`;
document.head.appendChild(style);

// ============================================================
// INITIALIZATION - FIXED
// ============================================================

// ✅ Menggunakan IIFE dengan async/await
(async function init() {
  console.log("🚀 Initializing Price List page...");
  try {
    await loadPriceItems();
    console.log("📋 Price List page initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize Price List page:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
})();

// ============================================================
// EXPOSE FUNCTIONS TO GLOBAL SCOPE
// ============================================================

window.openCreateModal = openCreateModal;
window.openEditModal = openEditModal;
window.openHistoryModal = openHistoryModal;
window.openBulkModal = openBulkModal;
window.confirmDelete = confirmDelete;
window.handleToggleStatus = handleToggleStatus;
window.loadPriceItems = loadPriceItems;
window.closeModal = closeModal;
window.closeHistoryModal = closeHistoryModal;
window.closeBulkModal = closeBulkModal;
window.exportPriceItems = exportPriceItems;

console.log("📋 Price List page script loaded");
