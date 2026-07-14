// static/js/pages/settings/api.js

import { CONFIG, state } from "./config.js";
import { showToast } from "../../pages/shared/toast.js";

// ============================================================
// Base API Helper
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
// Settings API Services
// ============================================================

export const SettingsAPI = {
  // ==================== WORKSHOP ====================

  getWorkshop: async () => {
    try {
      const response = await apiFetch("/settings/workshop");
      return response.data;
    } catch (error) {
      console.error("Failed to load workshop settings:", error);
      return null;
    }
  },

  updateWorkshop: async (data) => {
    try {
      const response = await apiFetch("/settings/workshop", {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      return response.data;
    } catch (error) {
      showToast(
        "Failed to update workshop settings: " + error.message,
        "error",
      );
      return null;
    }
  },

  // ==================== PRICING ====================

  getPricing: async () => {
    try {
      const response = await apiFetch("/settings/pricing");
      return response.data;
    } catch (error) {
      console.error("Failed to load pricing settings:", error);
      return null;
    }
  },

  updatePricing: async (data) => {
    try {
      const response = await apiFetch("/settings/pricing", {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      return response.data;
    } catch (error) {
      showToast("Failed to update pricing settings: " + error.message, "error");
      return null;
    }
  },

  // ==================== SECURITY ====================

  getSecurity: async () => {
    try {
      const response = await apiFetch("/settings/security");
      return response.data;
    } catch (error) {
      console.error("Failed to load security settings:", error);
      return null;
    }
  },

  updateSecurity: async (data) => {
    try {
      const response = await apiFetch("/settings/security", {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      return response.data;
    } catch (error) {
      showToast(
        "Failed to update security settings: " + error.message,
        "error",
      );
      return null;
    }
  },

  // ==================== WHATSAPP TEMPLATES ====================

  getWhatsAppTemplates: async () => {
    try {
      const response = await apiFetch("/settings/whatsapp-templates");
      return response.data || [];
    } catch (error) {
      console.error("Failed to load WhatsApp templates:", error);
      return [];
    }
  },

  getDefaultWhatsAppTemplate: async () => {
    try {
      const response = await apiFetch("/settings/whatsapp-templates/default");
      return response.data;
    } catch (error) {
      console.error("Failed to load default template:", error);
      return null;
    }
  },

  createWhatsAppTemplate: async (data) => {
    try {
      const response = await apiFetch("/settings/whatsapp-templates", {
        method: "POST",
        body: JSON.stringify(data),
      });
      showToast("WhatsApp template created!", "success");
      return response.data;
    } catch (error) {
      showToast("Failed to create template: " + error.message, "error");
      return null;
    }
  },

  updateWhatsAppTemplate: async (id, data) => {
    try {
      const response = await apiFetch(`/settings/whatsapp-templates/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      showToast("WhatsApp template updated!", "success");
      return response.data;
    } catch (error) {
      showToast("Failed to update template: " + error.message, "error");
      return null;
    }
  },

  deleteWhatsAppTemplate: async (id) => {
    try {
      await apiFetch(`/settings/whatsapp-templates/${id}`, {
        method: "DELETE",
      });
      showToast("Template deleted", "info");
      return true;
    } catch (error) {
      showToast("Failed to delete template: " + error.message, "error");
      return false;
    }
  },

  setDefaultTemplate: async (id) => {
    try {
      await apiFetch(`/settings/whatsapp-templates/${id}/set-default`, {
        method: "POST",
      });
      showToast("Default template updated!", "success");
      return true;
    } catch (error) {
      showToast("Failed to set default template: " + error.message, "error");
      return false;
    }
  },

  // ==================== PROJECT TYPES ====================

  getProjectTypes: async (includeInactive = false) => {
    try {
      const response = await apiFetch(
        `/settings/project-types?include_inactive=${includeInactive}`,
      );
      return response.data || [];
    } catch (error) {
      console.error("Failed to load project types:", error);
      return [];
    }
  },

  createProjectType: async (data) => {
    try {
      const response = await apiFetch("/settings/project-types", {
        method: "POST",
        body: JSON.stringify(data),
      });
      showToast("Project type created!", "success");
      return response.data;
    } catch (error) {
      showToast("Failed to create project type: " + error.message, "error");
      return null;
    }
  },

  updateProjectType: async (id, data) => {
    try {
      const response = await apiFetch(`/settings/project-types/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      showToast("Project type updated!", "success");
      return response.data;
    } catch (error) {
      showToast("Failed to update project type: " + error.message, "error");
      return null;
    }
  },

  deleteProjectType: async (id) => {
    try {
      await apiFetch(`/settings/project-types/${id}`, {
        method: "DELETE",
      });
      showToast("Project type deleted", "info");
      return true;
    } catch (error) {
      showToast("Failed to delete project type: " + error.message, "error");
      return false;
    }
  },

  // ==================== PAYMENT METHODS ====================

  getPaymentMethods: async (includeInactive = false) => {
    try {
      const response = await apiFetch(
        `/settings/payment-methods?include_inactive=${includeInactive}`,
      );
      return response.data || [];
    } catch (error) {
      console.error("Failed to load payment methods:", error);
      return [];
    }
  },

  createPaymentMethod: async (data) => {
    try {
      const response = await apiFetch("/settings/payment-methods", {
        method: "POST",
        body: JSON.stringify(data),
      });
      showToast("Payment method created!", "success");
      return response.data;
    } catch (error) {
      showToast("Failed to create payment method: " + error.message, "error");
      return null;
    }
  },

  updatePaymentMethod: async (id, data) => {
    try {
      const response = await apiFetch(`/settings/payment-methods/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      showToast("Payment method updated!", "success");
      return response.data;
    } catch (error) {
      showToast("Failed to update payment method: " + error.message, "error");
      return null;
    }
  },

  deletePaymentMethod: async (id) => {
    try {
      await apiFetch(`/settings/payment-methods/${id}`, {
        method: "DELETE",
      });
      showToast("Payment method deleted", "info");
      return true;
    } catch (error) {
      showToast("Failed to delete payment method: " + error.message, "error");
      return false;
    }
  },

  // ==================== STATUS WORKFLOW ====================

  getStatusWorkflows: async (includeInactive = false) => {
    try {
      const response = await apiFetch(
        `/settings/status-workflows?include_inactive=${includeInactive}`,
      );
      return response.data || [];
    } catch (error) {
      console.error("Failed to load status workflows:", error);
      return [];
    }
  },

  getStatusWorkflowMap: async () => {
    try {
      const response = await apiFetch("/settings/status-workflows/map");
      return response.data || {};
    } catch (error) {
      console.error("Failed to load status workflow map:", error);
      return {};
    }
  },

  // ==================== ALL SETTINGS ====================

  getAllSettings: async () => {
    try {
      const response = await apiFetch("/settings/all");
      return response.data;
    } catch (error) {
      showToast("Failed to load settings: " + error.message, "error");
      return null;
    }
  },
};

// ============================================================
// User API (if not available elsewhere)
// ============================================================

export const UserAPI = {
  getUsers: async () => {
    try {
      const response = await apiFetch("/users");
      return response.data || [];
    } catch (error) {
      console.error("Failed to load users:", error);
      return [];
    }
  },

  createUser: async (data) => {
    try {
      const response = await apiFetch("/users", {
        method: "POST",
        body: JSON.stringify(data),
      });
      showToast("User created!", "success");
      return response.data;
    } catch (error) {
      showToast("Failed to create user: " + error.message, "error");
      return null;
    }
  },

  updateUser: async (id, data) => {
    try {
      const response = await apiFetch(`/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      showToast("User updated!", "success");
      return response.data;
    } catch (error) {
      showToast("Failed to update user: " + error.message, "error");
      return null;
    }
  },

  deleteUser: async (id) => {
    try {
      await apiFetch(`/users/${id}`, {
        method: "DELETE",
      });
      showToast("User deleted", "info");
      return true;
    } catch (error) {
      showToast("Failed to delete user: " + error.message, "error");
      return false;
    }
  },
};
