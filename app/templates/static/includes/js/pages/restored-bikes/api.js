// ============================================================
// restored-bikes/api.js - API Calls
// ============================================================

import { CONFIG, state } from "./config.js";

// Helper fetch
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
      const errorMsg = data.message || data.detail || `HTTP ${response.status}`;
      throw new Error(errorMsg);
    }

    return data.data || data;
  } catch (error) {
    console.error("Restored Bikes API Error:", error);
    throw error;
  }
}

// ============================================================
// RESTORED BIKES API
// ============================================================

export const RestoredBikeAPI = {
  // List all restored bikes
  list: async (page = 1, filters = {}) => {
    state.isLoading = true;
    const params = new URLSearchParams({
      page: page,
      limit: CONFIG.ITEMS_PER_PAGE,
    });
    if (filters.search) params.set("search", filters.search);
    if (filters.status) params.set("status", filters.status);
    if (filters.brand) params.set("brand", filters.brand);

    try {
      const result = await apiFetch(`/restored-bikes/?${params.toString()}`);
      return result;
    } catch (error) {
      console.error("Failed to load restored bikes:", error);
      return null;
    } finally {
      state.isLoading = false;
    }
  },

  // Get detail
  get: async (id) => {
    try {
      return await apiFetch(`/restored-bikes/${id}`);
    } catch (error) {
      console.error("Failed to load bike detail:", error);
      return null;
    }
  },

  // Create
  create: async (data) => {
    try {
      return await apiFetch("/restored-bikes/", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch (error) {
      console.error("Failed to create restored bike:", error);
      throw error;
    }
  },

  // Update
  update: async (id, data) => {
    try {
      return await apiFetch(`/restored-bikes/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    } catch (error) {
      console.error("Failed to update restored bike:", error);
      throw error;
    }
  },

  // Delete
  delete: async (id) => {
    try {
      return await apiFetch(`/restored-bikes/${id}`, {
        method: "DELETE",
      });
    } catch (error) {
      console.error("Failed to delete restored bike:", error);
      throw error;
    }
  },

  // Get statistics
  stats: async () => {
    try {
      return await apiFetch("/restored-bikes/statistics");
    } catch (error) {
      console.error("Failed to load stats:", error);
      return null;
    }
  },

  // ===== GALLERY =====

  // Upload photos
  uploadPhotos: async (bikeId, files) => {
    const formData = new FormData();
    files.forEach((file) => formData.append("photos", file));

    const url = `${CONFIG.API_BASE_URL}/restored-bikes/${bikeId}/photos`;
    try {
      const response = await fetch(url, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(
          data.message || data.detail || `HTTP ${response.status}`,
        );
      }
      return data.data || data;
    } catch (error) {
      console.error("Failed to upload photos:", error);
      throw error;
    }
  },

  // Get photos
  getPhotos: async (bikeId) => {
    try {
      return await apiFetch(`/restored-bikes/${bikeId}/photos`);
    } catch (error) {
      console.error("Failed to load photos:", error);
      return [];
    }
  },

  // Delete photo
  deletePhoto: async (photoId) => {
    try {
      return await apiFetch(`/restored-bikes/photos/${photoId}`, {
        method: "DELETE",
      });
    } catch (error) {
      console.error("Failed to delete photo:", error);
      throw error;
    }
  },

  // ===== DOCUMENTS =====

  // Upload document
  uploadDocument: async (bikeId, file) => {
    const formData = new FormData();
    formData.append("document", file);

    const url = `${CONFIG.API_BASE_URL}/restored-bikes/${bikeId}/documents`;
    try {
      const response = await fetch(url, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(
          data.message || data.detail || `HTTP ${response.status}`,
        );
      }
      return data.data || data;
    } catch (error) {
      console.error("Failed to upload document:", error);
      throw error;
    }
  },

  // Get documents
  getDocuments: async (bikeId) => {
    try {
      return await apiFetch(`/restored-bikes/${bikeId}/documents`);
    } catch (error) {
      console.error("Failed to load documents:", error);
      return [];
    }
  },

  // Delete document
  deleteDocument: async (docId) => {
    try {
      return await apiFetch(`/restored-bikes/documents/${docId}`, {
        method: "DELETE",
      });
    } catch (error) {
      console.error("Failed to delete document:", error);
      throw error;
    }
  },

  // Download document
  downloadDocument: async (docId) => {
    try {
      const url = `${CONFIG.API_BASE_URL}/restored-bikes/documents/${docId}/download`;
      window.open(url, "_blank");
      return true;
    } catch (error) {
      console.error("Failed to download document:", error);
      return false;
    }
  },
};
