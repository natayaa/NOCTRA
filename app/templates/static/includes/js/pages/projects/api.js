// projects/api.js (FIXED)

import { CONFIG, state } from "./config.js";
import { showToast } from "./toast.js";
import { ensureArray } from "./utils.js";

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
      const errorMsg = data.detail || data.message || `HTTP ${response.status}`;
      throw new Error(errorMsg);
    }
    return data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

// ============================================================
// Projects API Services
// ============================================================
export const ProjectAPI = {
  fetchProjects: async (page = 1, filters = {}) => {
    state.isLoading = true;
    const params = new URLSearchParams({
      page: page,
      limit: CONFIG.PROJECTS_PER_PAGE,
    });
    if (filters.search) params.set("search", filters.search);
    if (filters.status) params.set("status", filters.status);
    if (filters.priority) params.set("priority", filters.priority);

    try {
      const response = await apiFetch(`/projects/?${params.toString()}`);
      return response.data || response;
    } catch (error) {
      showToast("Failed to load projects: " + error.message, "error");
      return null;
    } finally {
      state.isLoading = false;
    }
  },

  fetchStatistics: async () => {
    try {
      const response = await apiFetch("/projects/statistics");
      return response.data || response;
    } catch (error) {
      console.error("Failed to load statistics:", error);
      return null;
    }
  },

  fetchFinancialSummary: async () => {
    try {
      const response = await apiFetch("/projects/financial-summary");
      return response.data || response;
    } catch (error) {
      console.error("Failed to load financial summary:", error);
      return null;
    }
  },

  fetchDetail: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}`);
      return response.data || response;
    } catch (error) {
      showToast("Failed to load project details: " + error.message, "error");
      return null;
    }
  },

  create: async (data) => {
    try {
      const response = await apiFetch("/projects/", {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to create project: " + error.message, "error");
      return null;
    }
  },

  update: async (projectId, data) => {
    try {
      const response = await apiFetch(`/projects/${projectId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to update project: " + error.message, "error");
      return null;
    }
  },

  delete: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}`, {
        method: "DELETE",
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to delete project: " + error.message, "error");
      return null;
    }
  },

  updateProgress: async (projectId, progress, note = "") => {
    try {
      const response = await apiFetch(`/projects/${projectId}/progress`, {
        method: "PATCH",
        body: JSON.stringify({ progress }),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to update progress: " + error.message, "error");
      return null;
    }
  },

  complete: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/complete`, {
        method: "POST",
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to complete project: " + error.message, "error");
      return null;
    }
  },

  updateStatus: async (projectId, status, note = "") => {
    try {
      const response = await apiFetch(`/projects/${projectId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status, note }),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to update status: " + error.message, "error");
      return null;
    }
  },

  archive: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/archive`, {
        method: "POST",
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to archive project: " + error.message, "error");
      return null;
    }
  },

  unarchive: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/unarchive`, {
        method: "POST",
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to unarchive project: " + error.message, "error");
      return null;
    }
  },

  // --- Tasks ---
  fetchTasks: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/tasks`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load tasks:", error);
      return [];
    }
  },

  addTask: async (projectId, data) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/tasks`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to add task: " + error.message, "error");
      return null;
    }
  },

  completeTask: async (taskId) => {
    try {
      const response = await apiFetch(`/projects/tasks/${taskId}/complete`, {
        method: "POST",
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to complete task: " + error.message, "error");
      return null;
    }
  },

  // --- Labor ---
  fetchLabor: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/labor`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load labor:", error);
      return [];
    }
  },

  addLabor: async (projectId, data) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/labor`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to add labor: " + error.message, "error");
      return null;
    }
  },

  deleteLabor: async (laborId) => {
    try {
      const response = await apiFetch(`/projects/labor/${laborId}`, {
        method: "DELETE",
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to delete labor: " + error.message, "error");
      return null;
    }
  },

  // --- Expenses ---
  fetchExpenses: async (projectId, category = null) => {
    try {
      const params = category ? `?category=${category}` : "";
      const response = await apiFetch(
        `/projects/${projectId}/expenses${params}`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load expenses:", error);
      return [];
    }
  },

  addExpense: async (projectId, data) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/expenses`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to add expense: " + error.message, "error");
      return null;
    }
  },

  // --- Material Usage ---
  consumeMaterial: async (data) => {
    try {
      const response = await apiFetch("/inventory/usage", {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to consume material: " + error.message, "error");
      return null;
    }
  },

  deleteMaterialUsage: async (usageId) => {
    try {
      const response = await apiFetch(`/inventory/usage/${usageId}`, {
        method: "DELETE",
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to delete material: " + error.message, "error");
      return null;
    }
  },

  // --- Inventory & Price List ---
  fetchInventoryItems: async (limit = 100, category = null) => {
    try {
      let url = `/inventory/items?limit=${limit}`;
      if (category) url += `&category=${encodeURIComponent(category)}`;
      const response = await apiFetch(url);
      const result = response.data || response;
      return result.items || result || [];
    } catch (error) {
      console.error("Failed to load inventory items:", error);
      return [];
    }
  },

  fetchPriceListItems: async (page = 1, limit = 100, category = null) => {
    try {
      let url = `/price-list/items?page=${page}&limit=${limit}`;
      if (category) url += `&category=${encodeURIComponent(category)}`;
      const response = await apiFetch(url);
      const result = response.data || response;
      return result.items || result || [];
    } catch (error) {
      console.warn("⚠️ Failed to load price list:", error.message);
      return [];
    }
  },

  checkInventoryItem: async (itemId) => {
    try {
      const response = await apiFetch(`/inventory/items/${itemId}`);
      return response.data || response;
    } catch (error) {
      console.warn("Item not found in inventory:", error.message);
      return null;
    }
  },

  // --- Price List Items (for project) ---
  addPriceListItem: async (
    projectId,
    priceListItemId,
    quantity = 1,
    notes = "",
  ) => {
    try {
      const response = await apiFetch(
        `/projects/${projectId}/price-list-items`,
        {
          method: "POST",
          body: JSON.stringify({
            price_list_item_id: priceListItemId,
            quantity: quantity,
            notes: notes,
          }),
        },
      );
      return response.data || response;
    } catch (error) {
      showToast("Failed to add price list item: " + error.message, "error");
      return null;
    }
  },

  fetchPriceListItemsForProject: async (projectId) => {
    try {
      const response = await apiFetch(
        `/projects/${projectId}/price-list-items`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load project price list items:", error);
      return [];
    }
  },

  // --- Stages ---
  fetchStages: async (activeOnly = true) => {
    try {
      const response = await apiFetch(
        `/projects/stages?active_only=${activeOnly}`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load stages:", error);
      return [];
    }
  },

  createStage: async (data) => {
    try {
      const response = await apiFetch("/projects/stages", {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to create stage: " + error.message, "error");
      return null;
    }
  },

  // --- Timeline ---
  fetchTimelines: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/timeline`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load timelines:", error);
      return [];
    }
  },

  addTimeline: async (projectId, data) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/timeline`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to add timeline: " + error.message, "error");
      return null;
    }
  },

  updateTimeline: async (timelineId, data) => {
    try {
      const response = await apiFetch(`/projects/timeline/${timelineId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to update timeline: " + error.message, "error");
      return null;
    }
  },

  deleteTimeline: async (timelineId) => {
    try {
      const response = await apiFetch(`/projects/timeline/${timelineId}`, {
        method: "DELETE",
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to delete timeline: " + error.message, "error");
      return null;
    }
  },

  // --- Documents ---
  uploadDocument: async (projectId, formData) => {
    try {
      const response = await fetch(
        `${CONFIG.API_BASE_URL}/projects/${projectId}/documents`,
        {
          method: "POST",
          body: formData,
        },
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(
          data.detail || data.message || `HTTP ${response.status}`,
        );
      }
      return data.data || data;
    } catch (error) {
      showToast("Failed to upload document: " + error.message, "error");
      return null;
    }
  },

  fetchDocuments: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/documents`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load documents:", error);
      return [];
    }
  },

  deleteDocument: async (documentId) => {
    try {
      const response = await apiFetch(`/projects/documents/${documentId}`, {
        method: "DELETE",
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to delete document: " + error.message, "error");
      return null;
    }
  },

  // --- Team ---
  fetchTeamMembers: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/team`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load team members:", error);
      return [];
    }
  },

  addTeamMember: async (projectId, data) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/team`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to add team member: " + error.message, "error");
      return null;
    }
  },

  removeTeamMember: async (teamMemberId) => {
    try {
      const response = await apiFetch(`/projects/team/${teamMemberId}`, {
        method: "DELETE",
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to remove team member: " + error.message, "error");
      return null;
    }
  },

  // --- Helper ---
  getProjectById: (projectId) => {
    return state.projects.find((p) => p.id === projectId) || null;
  },
};
