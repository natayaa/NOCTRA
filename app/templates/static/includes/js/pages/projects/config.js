// ============================================================
// projects/config.js - Configuration & State
// ============================================================

export const CONFIG = {
  API_BASE_URL: "/api/api",
  PROJECTS_PER_PAGE: 10,
  TOAST_DURATION: 4000,
};

export const state = {
  projects: [],
  currentPage: 1,
  totalPages: 1,
  totalItems: 0,
  currentProjectId: null,
  editingProjectId: null,
  filters: {
    search: "",
    status: "",
    priority: "",
  },
  materials: [],
  laborTypes: [],
  isLoading: false,
  _currentProject: null,
  _currentProjectData: null,
  _progressProjectId: null,
};
