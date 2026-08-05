// projects/config.js (FIXED)

export const CONFIG = {
  API_BASE_URL: "/api/api", // ✅ FIXED: removed duplicate /api
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

export function resetState() {
  state.projects = [];
  state.currentPage = 1;
  state.totalPages = 1;
  state.totalItems = 0;
  state.currentProjectId = null;
  state.editingProjectId = null;
  state.filters.search = "";
  state.filters.status = "";
  state.filters.priority = "";
  state.isLoading = false;
  state._currentProject = null;
  state._currentProjectData = null;
  state._progressProjectId = null;
}

export function getCurrentProject() {
  return state._currentProject || null;
}

export function getCurrentProjectData() {
  return state._currentProjectData || null;
}
