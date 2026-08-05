// ============================================================
// inventories/api.js - API Services
// ============================================================

import { CONFIG, state } from "./config.js";
import { showToast } from "./toast.js";
import { getItemName } from "./utils.js";

// ============================================================
// Base API Helper
// ============================================================
export async function apiFetch(endpoint, options = {}) {
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
// Inventory API Services
// ============================================================
export const InventoryAPI = {
  fetchItems: async (page = 1, filters = {}) => {
    state.isLoading = true;
    const params = new URLSearchParams({
      page: page,
      limit: CONFIG.ITEMS_PER_PAGE,
    });

    if (filters.search) params.set("search", filters.search);
    if (filters.category) params.set("category", filters.category);
    if (filters.status) params.set("status", filters.status);
    if (filters.low_stock_only) params.set("low_stock_only", "true");

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

  fetchItemDetail: async (itemId) => {
    try {
      const response = await apiFetch(`/inventory/items/${itemId}`);
      return response.data;
    } catch (error) {
      showToast("Failed to load item details: " + error.message, "error");
      return null;
    }
  },

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

  fetchAlerts: async () => {
    try {
      const response = await apiFetch("/inventory/alerts");
      return response.data;
    } catch (error) {
      console.error("Failed to load alerts:", error);
      return null;
    }
  },

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

  fetchStatistics: async () => {
    try {
      const response = await apiFetch("/inventory/statistics");
      return response.data;
    } catch (error) {
      console.error("Failed to load statistics:", error);
      return null;
    }
  },

  fetchCategories: async () => {
    try {
      const response = await apiFetch("/inventory/categories");
      return response.data;
    } catch (error) {
      console.error("Failed to load categories:", error);
      return null;
    }
  },

  fetchSuppliers: async () => {
    try {
      const response = await apiFetch("/inventory/suppliers?active_only=true");
      return response.data;
    } catch (error) {
      console.error("Failed to load suppliers:", error);
      return null;
    }
  },

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
