export const CONFIG = {
  API_BASE_URL: "/api/api",
  TOAST_DURATION: 4000,
};

export const state = {
  // Settings
  workshop: null,
  pricing: null,
  security: null,
  whatsappTemplates: [],
  projectTypes: [],
  paymentMethods: [],
  statusWorkflows: [],

  // Users (from auth module)
  users: [],

  // UI State
  isLoading: false,
  isSaving: false,
  activeSection: "workshop",
};
