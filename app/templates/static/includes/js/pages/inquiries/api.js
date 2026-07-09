// ============================================================
// inquiries/api.js - API Services (FIXED)
// ============================================================

import { CONFIG, state } from "./config.js";
import { showToast } from "./toast.js";
import { getItemUnit, getItemCost } from "./utils.js";

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

    // ✅ Clone response untuk debugging
    const clone = response.clone();
    let data;
    try {
      data = await response.json();
    } catch (e) {
      const text = await clone.text();
      console.error("Raw response:", text);
      throw new Error(`Invalid JSON response: ${text.substring(0, 100)}`);
    }

    if (!response.ok) {
      // ✅ Format error dengan detail
      const errorMsg = data.message || data.detail || `HTTP ${response.status}`;
      const error = new Error(errorMsg);
      error.status = response.status;
      error.response = { status: response.status, data };
      throw error;
    }
    return data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

// ============================================================
// Inquiry API Services
// ============================================================
export const InquiryAPI = {
  // ✅ GET /api/api/inquiries/
  fetchInquiries: async (page = 1, filters = {}) => {
    state.isLoading = true;
    const params = new URLSearchParams({
      page: page,
      limit: CONFIG.INQUIRIES_PER_PAGE,
    });
    if (filters.search) params.set("search", filters.search);
    if (filters.status) params.set("status", filters.status);

    try {
      const response = await apiFetch(`/inquiries/?${params.toString()}`);
      return response.data || response;
    } catch (error) {
      showToast("Failed to load inquiries: " + error.message, "error");
      return null;
    } finally {
      state.isLoading = false;
    }
  },

  // ✅ GET /api/api/inquiries/statistics
  fetchStatistics: async () => {
    try {
      const response = await apiFetch("/inquiries/statistics");
      return response.data || response;
    } catch (error) {
      console.error("Failed to load statistics:", error);
      return null;
    }
  },

  // ✅ GET /api/api/inquiries/{inquiry_id}
  fetchDetail: async (inquiryId) => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}`);
      return response.data || response;
    } catch (error) {
      showToast("Failed to load inquiry details: " + error.message, "error");
      return null;
    }
  },

  // ✅ PATCH /api/api/inquiries/{inquiry_id}/status
  updateStatus: async (inquiryId, status, note = "") => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status, note }),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to update status: " + error.message, "error");
      return null;
    }
  },

  // ✅ POST /api/api/inquiries/{inquiry_id}/quote
  sendQuotation: async (inquiryId, estimatedCost, notes = "") => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}/quote`, {
        method: "POST",
        body: JSON.stringify({ estimated_cost: estimatedCost, notes }),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to send quotation: " + error.message, "error");
      return null;
    }
  },

  // ✅ POST /api/api/inquiries/{inquiry_id}/reject
  reject: async (inquiryId, reason = "") => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to reject inquiry: " + error.message, "error");
      return null;
    }
  },

  // ✅ POST /api/api/inquiries/{inquiry_id}/convert-to-project
  convertToProject: async (
    inquiryId,
    startDate = null,
    targetDelivery = null,
    estimatedCost = null,
  ) => {
    try {
      const response = await apiFetch(
        `/inquiries/${inquiryId}/convert-to-project`,
        {
          method: "POST",
          body: JSON.stringify({
            project_start_date: startDate,
            project_target_delivery: targetDelivery,
            estimated_cost: estimatedCost,
          }),
        },
      );
      return response.data || response;
    } catch (error) {
      showToast("Failed to convert to project: " + error.message, "error");
      return null;
    }
  },

  // ✅ GET /api/api/inquiries/{inquiry_id}/activities
  fetchActivities: async (inquiryId, limit = CONFIG.MAX_ACTIVITIES) => {
    try {
      const response = await apiFetch(
        `/inquiries/${inquiryId}/activities?limit=${limit}`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load activities:", error);
      return [];
    }
  },

  // ✅ GET /api/api/inquiries/{inquiry_id}/notes
  fetchNotes: async (inquiryId, includePrivate = false) => {
    try {
      const response = await apiFetch(
        `/inquiries/${inquiryId}/notes?include_private=${includePrivate}`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load notes:", error);
      return [];
    }
  },

  // ✅ POST /api/api/inquiries/{inquiry_id}/notes
  addNote: async (
    inquiryId,
    note,
    noteType = "internal",
    isPrivate = false,
  ) => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}/notes`, {
        method: "POST",
        body: JSON.stringify({
          note,
          note_type: noteType,
          is_private: isPrivate,
        }),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to add note: " + error.message, "error");
      return null;
    }
  },

  // ✅ GET /api/api/inquiries/{inquiry_id}/photos
  fetchPhotos: async (inquiryId) => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}/photos`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load photos:", error);
      return [];
    }
  },

  // ✅ GET /api/api/inventory/items (for inventory items)
  fetchInventoryItems: async () => {
    try {
      const response = await apiFetch("/inventory/items?page=1&limit=100");
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load inventory items:", error);
      return [];
    }
  },

  // ✅ GET /api/api/projects/{project_id}/labor
  fetchProjectLabor: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/labor`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load labor:", error);
      return [];
    }
  },

  // ✅ GET /api/api/inventory/usage/project/{project_id}
  fetchProjectMaterialUsage: async (projectId) => {
    try {
      const response = await apiFetch(`/inventory/usage/project/${projectId}`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load material usage:", error);
      return [];
    }
  },
};
