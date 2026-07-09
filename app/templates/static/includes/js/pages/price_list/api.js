// ============================================================
// price_list/api.js - API Services
// ============================================================

import { CONFIG, state } from "./config.js";
import { showToast } from "./toast.js";

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
// Price List API Services
// ============================================================
export const PriceAPI = {
  fetchItems: async (page = 1, filters = {}) => {
    state.isLoading = true;
    const params = new URLSearchParams({
      page: page,
      limit: CONFIG.ITEMS_PER_PAGE,
    });

    if (filters.search) params.set("search", filters.search);
    if (filters.category) params.set("category", filters.category);
    if (filters.vehicle_brand)
      params.set("vehicle_brand", filters.vehicle_brand);
    if (filters.vehicle_model)
      params.set("vehicle_model", filters.vehicle_model);

    // Handle status filter
    if (filters.status) {
      if (filters.status === "active") {
        params.set("active_only", "true");
      } else if (filters.status === "inactive") {
        params.set("active_only", "false");
      }
      if (filters.status === "") {
        params.delete("active_only");
      }
    }

    try {
      const response = await apiFetch(
        `/price-list/items/?${params.toString()}`,
      );
      return response;
    } catch (error) {
      showToast("Failed to load price items: " + error.message, "error");
      return null;
    } finally {
      state.isLoading = false;
    }
  },

  fetchItemDetail: async (itemId) => {
    try {
      const response = await apiFetch(`/price-list/items/${itemId}`);
      return response.data;
    } catch (error) {
      showToast("Failed to load item details: " + error.message, "error");
      return null;
    }
  },

  createItem: async (data) => {
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
  },

  updateItem: async (itemId, data) => {
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
  },

  deleteItem: async (itemId) => {
    try {
      const response = await apiFetch(`/price-list/items/${itemId}`, {
        method: "DELETE",
      });
      return response.data;
    } catch (error) {
      showToast("Failed to delete price item: " + error.message, "error");
      return null;
    }
  },

  toggleItem: async (itemId) => {
    try {
      const response = await apiFetch(`/price-list/items/${itemId}/toggle`, {
        method: "POST",
      });
      return response.data;
    } catch (error) {
      showToast("Failed to toggle item status: " + error.message, "error");
      return null;
    }
  },

  fetchHistory: async (itemId, limit = 50) => {
    try {
      const response = await apiFetch(
        `/price-list/items/${itemId}/price-history?limit=${limit}`,
      );
      console.log("📦 Price history response:", response);

      // ✅ Return the data directly, let the caller handle array conversion
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load price history:", error);
      showToast("Failed to load price history: " + error.message, "error");
      return [];
    }
  },

  changePrice: async (itemId, newPrice, reason = "") => {
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
  },

  fetchStatistics: async () => {
    try {
      const response = await apiFetch("/price-list/stats");
      return response.data;
    } catch (error) {
      console.error("Failed to load statistics:", error);
      return null;
    }
  },

  fetchCategories: async () => {
    try {
      const response = await apiFetch("/price-list/categories/with-counts");
      return response.data;
    } catch (error) {
      console.error("Failed to load categories:", error);
      return null;
    }
  },

  bulkUpdate: async (data) => {
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
  },
};
