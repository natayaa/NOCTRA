// ============================================================
// projects.js - NOCTRA Projects Page (FULL FIXED)
// Complete JavaScript for Projects management with API integration
// ============================================================

// ============================================================
// CONFIGURATION
// ============================================================
const API_BASE_URL = "/api/api";
const PROJECTS_PER_PAGE = 10;

// ============================================================
// STATE
// ============================================================
let state = {
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

// ============================================================
// DOM REFS
// ============================================================
const DOM = {
  activeCount: document.getElementById("activeCount"),
  prodCount: document.getElementById("prodCount"),
  completedCount: document.getElementById("completedCount"),
  revenueTotal: document.getElementById("revenueTotal"),
  projectSearch: document.getElementById("projectSearch"),
  statusFilter: document.getElementById("statusFilter"),
  priorityFilter: document.getElementById("priorityFilter"),
  createProjectBtn: document.getElementById("createProjectBtn"),
  projectCardGrid: document.getElementById("projectCardGrid"),
  prevPageBtn: document.getElementById("prevPageBtn"),
  nextPageBtn: document.getElementById("nextPageBtn"),
  pageInfo: document.getElementById("pageInfo"),
  projectModal: document.getElementById("projectModal"),
  modalTitle: document.getElementById("modalTitle"),
  modalSubtitle: document.getElementById("modalSubtitle"),
  editProjectId: document.getElementById("editProjectId"),
  projectForm: document.getElementById("projectForm"),
  projectName: document.getElementById("projectName"),
  customerName: document.getElementById("customerName"),
  customerPhone: document.getElementById("customerPhone"),
  customerEmail: document.getElementById("customerEmail"),
  projectStatus: document.getElementById("projectStatus"),
  projectPriority: document.getElementById("projectPriority"),
  vehicleBrand: document.getElementById("vehicleBrand"),
  vehicleModel: document.getElementById("vehicleModel"),
  vehicleYear: document.getElementById("vehicleYear"),
  licensePlate: document.getElementById("licensePlate"),
  estimatedCost: document.getElementById("estimatedCost"),
  estimatedRevenue: document.getElementById("estimatedRevenue"),
  startDate: document.getElementById("startDate"),
  targetDelivery: document.getElementById("targetDelivery"),
  projectNotes: document.getElementById("projectNotes"),
  submitProjectBtn: document.getElementById("submitProjectBtn"),
  cancelModalBtn: document.getElementById("cancelModalBtn"),
  closeModal: document.getElementById("closeModal"),
  drawer: document.getElementById("projectDrawer"),
  drawerTitle: document.getElementById("drawerTitle"),
  drawerSubtitle: document.getElementById("drawerSubtitle"),
  closeDrawer: document.getElementById("closeDrawer"),
  drawerBackdrop: null,
  drawerCustomer: document.getElementById("drawerCustomer"),
  drawerPhone: document.getElementById("drawerPhone"),
  drawerEmail: document.getElementById("drawerEmail"),
  drawerBrand: document.getElementById("drawerBrand"),
  drawerModel: document.getElementById("drawerModel"),
  drawerYear: document.getElementById("drawerYear"),
  drawerPlate: document.getElementById("drawerPlate"),
  drawerStatus: document.getElementById("drawerStatus"),
  drawerPriority: document.getElementById("drawerPriority"),
  drawerProgressFill: document.getElementById("drawerProgressFill"),
  drawerProgressText: document.getElementById("drawerProgressText"),
  drawerNotes: document.getElementById("drawerNotes"),
  // drawerEstCost: document.getElementById("drawerEstCost"),
  //drawerActualCost: document.getElementById("drawerActualCost"),
  //drawerEstRevenue: document.getElementById("drawerEstRevenue"),
  //drawerActualRevenue: document.getElementById("drawerActualRevenue"),
  //drawerDeposit: document.getElementById("drawerDeposit"),
  //drawerDepositPaid: document.getElementById("drawerDepositPaid"),
  //drawerProfit: document.getElementById("drawerProfit"),
  //drawerMargin: document.getElementById("drawerMargin"),
  //drawerMaterialCost: document.getElementById("drawerMaterialCost"),
  //drawerLaborCost: document.getElementById("drawerLaborCost"),
  //drawerOtherExpenses: document.getElementById("drawerOtherExpenses"),
  //drawerTotalCost: document.getElementById("drawerTotalCost"),
  budgetPercentage: document.getElementById("budgetPercentage"),
  budgetProgressFillFinancial: document.getElementById(
    "budgetProgressFillFinancial",
  ),
  materialSelect: document.getElementById("materialSelect"),
  materialQty: document.getElementById("materialQty"),
  materialUnit: document.getElementById("materialUnit"),
  materialHint: document.getElementById("materialHint"),
  consumeMaterialBtn: document.getElementById("consumeMaterialBtn"),
  drawerMaterialsList: document.getElementById("drawerMaterialsList"),
  laborTypeSelect: document.getElementById("laborTypeSelect"),
  laborHours: document.getElementById("laborHours"),
  laborRate: document.getElementById("laborRate"),
  addLaborBtn: document.getElementById("addLaborBtn"),
  laborList: document.getElementById("laborList"),
  drawerStartDate: document.getElementById("drawerStartDate"),
  drawerDelivery: document.getElementById("drawerDelivery"),
  drawerActualDelivery: document.getElementById("drawerActualDelivery"),
  drawerCompletedAt: document.getElementById("drawerCompletedAt"),
  drawerMilestones: document.getElementById("drawerMilestones"),
  drawerActivities: document.getElementById("drawerActivities"),
  drawerTasks: document.getElementById("drawerTasks"),
  addTaskBtn: document.getElementById("addTaskBtn"),
  progressPopup: document.getElementById("progressPopup"),
  progressPopupSlider: document.getElementById("progressPopupSlider"),
  progressPopupValue: document.getElementById("progressPopupValue"),
  progressPopupNote: document.getElementById("progressPopupNote"),
  markCompleteCheckbox: document.getElementById("markCompleteCheckbox"),
  progressPopupMilestones: document.getElementById("progressPopupMilestones"),
  saveProgressBtn: document.getElementById("saveProgressBtn"),
  cancelProgressBtn: document.getElementById("cancelProgressBtn"),
  closeProgressPopup: document.getElementById("closeProgressPopup"),
  taskModal: document.getElementById("taskModal"),
  taskForm: document.getElementById("taskForm"),
  taskProjectId: document.getElementById("taskProjectId"),
  taskTitle: document.getElementById("taskTitle"),
  taskDescription: document.getElementById("taskDescription"),
  taskAssignee: document.getElementById("taskAssignee"),
  taskPriority: document.getElementById("taskPriority"),
  taskDueDate: document.getElementById("taskDueDate"),
  cancelTaskBtn: document.getElementById("cancelTaskBtn"),
  closeTaskModal: document.getElementById("closeTaskModal"),
  toastContainer: document.getElementById("toastContainer"),
  tabBtns: document.querySelectorAll(".drawer-tabs .tab-btn"),
  tabPanels: {
    overview: document.getElementById("tab-overview"),
    //financial: document.getElementById("tab-financial"),
    material: document.getElementById("tab-material"),
    labor: document.getElementById("tab-labor"),
    timeline: document.getElementById("tab-timeline"),
    tasks: document.getElementById("tab-tasks"),
  },
};

// Create drawer backdrop
const drawerBackdrop = document.createElement("div");
drawerBackdrop.className = "drawer-backdrop";
drawerBackdrop.id = "drawerBackdrop";
document.body.appendChild(drawerBackdrop);
DOM.drawerBackdrop = drawerBackdrop;

// ============================================================
// TOAST SYSTEM
// ============================================================
function showToast(message, type = "info", duration = 4000) {
  const container = DOM.toastContainer;
  if (!container) {
    console.warn("Toast container not found");
    return;
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${message}</span><button class="toast-close">&times;</button>`;
  container.appendChild(toast);

  const closeBtn = toast.querySelector(".toast-close");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => toast.remove());
  }

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
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "-";
  }
}

function formatDateTime(dateString) {
  if (!dateString) return "-";
  try {
    const date = new Date(dateString);
    return date.toLocaleString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "-";
  }
}

function getStatusBadgeClass(status) {
  const map = {
    draft: "draft",
    active: "active",
    in_progress: "in_progress",
    on_hold: "on_hold",
    completed: "completed",
    cancelled: "cancelled",
  };
  return map[status] || "draft";
}

function getPriorityBadgeClass(priority) {
  const map = { low: "low", medium: "medium", high: "high", urgent: "urgent" };
  return map[priority] || "medium";
}

function getStatusLabel(status) {
  const map = {
    draft: "Draft",
    active: "Active",
    in_progress: "In Progress",
    on_hold: "On Hold",
    completed: "Completed",
    cancelled: "Cancelled",
  };
  return map[status] || status;
}

function getPriorityLabel(priority) {
  const map = { low: "Low", medium: "Medium", high: "High", urgent: "Urgent" };
  return map[priority] || priority;
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
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || data.detail || `HTTP ${response.status}`);
    }
    return data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

// ============================================================
// PROJECTS API CALLS
// ============================================================
async function fetchProjects(page = 1, filters = {}) {
  state.isLoading = true;
  showLoadingState();

  const params = new URLSearchParams({ page, limit: PROJECTS_PER_PAGE });
  if (filters.search) params.append("search", filters.search);
  if (filters.status) params.append("status", filters.status);
  if (filters.priority) params.append("priority", filters.priority);

  try {
    const response = await apiFetch(`/projects/?${params.toString()}`);
    return response;
  } catch (error) {
    showToast("Failed to load projects: " + error.message, "error");
    return null;
  } finally {
    state.isLoading = false;
  }
}

async function fetchProjectStatistics() {
  try {
    const response = await apiFetch("/projects/statistics");
    return response.data || response;
  } catch (error) {
    console.error("Failed to load statistics:", error);
    return null;
  }
}

async function fetchProjectDetail(projectId) {
  try {
    const response = await apiFetch(`/projects/${projectId}`);
    return response.data || response;
  } catch (error) {
    showToast("Failed to load project details: " + error.message, "error");
    return null;
  }
}

async function createProject(data) {
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
}

async function updateProject(projectId, data) {
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
}

async function deleteProject(projectId) {
  try {
    const response = await apiFetch(`/projects/${projectId}`, {
      method: "DELETE",
    });
    return response.data || response;
  } catch (error) {
    showToast("Failed to delete project: " + error.message, "error");
    return null;
  }
}

async function updateProjectProgress(projectId, progress, note = "") {
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
}

async function completeProject(projectId) {
  try {
    const response = await apiFetch(`/projects/${projectId}/complete`, {
      method: "POST",
    });
    return response.data || response;
  } catch (error) {
    showToast("Failed to complete project: " + error.message, "error");
    return null;
  }
}

async function consumeMaterial(data) {
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
}

// ============================================================
// API CALLS - DELETE MATERIAL & LABOR
// ============================================================

async function deleteMaterialUsage(usageId) {
  try {
    const response = await apiFetch(`/inventory/usage/${usageId}`, {
      method: "DELETE",
    });
    return response.data || response;
  } catch (error) {
    showToast("Failed to delete material: " + error.message, "error");
    return null;
  }
}

async function deleteLabor(laborId) {
  try {
    const response = await apiFetch(`/projects/labor/${laborId}`, {
      method: "DELETE",
    });
    return response.data || response;
  } catch (error) {
    showToast("Failed to delete labor: " + error.message, "error");
    return null;
  }
}

async function addLabor(projectId, data) {
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
}

async function fetchTasks(projectId) {
  try {
    const response = await apiFetch(`/projects/${projectId}/tasks`);
    return response.data || response || [];
  } catch (error) {
    console.error("Failed to load tasks:", error);
    return [];
  }
}

async function addTask(projectId, data) {
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
}

async function completeTask(taskId) {
  try {
    const response = await apiFetch(`/projects/tasks/${taskId}/complete`, {
      method: "POST",
    });
    return response.data || response;
  } catch (error) {
    showToast("Failed to complete task: " + error.message, "error");
    return null;
  }
}

// ============================================================
// PRICE LIST API (UNTUK LABOR)
// ============================================================
async function fetchPriceListItems(page = 1, pageSize = 100) {
  try {
    // Perbaiki endpoint: /price-list/items
    const response = await apiFetch(
      `/price-list/items?page=${page}&page_size=${pageSize}`,
    );
    //console.log("📦 Price list response:", response);

    // Response structure: { success, message, total, page, page_size, total_pages, data: [...] }
    if (response.data && Array.isArray(response.data)) {
      return response.data;
    }

    if (Array.isArray(response)) {
      return response;
    }

    return [];
  } catch (error) {
    console.warn("⚠️ Failed to load price list:", error.message);
    return [];
  }
}

// ============================================================
// INVENTORY API (UNTUK MATERIAL)
// ============================================================
async function fetchInventoryItems() {
  try {
    // Endpoint sudah benar: /inventory/items
    const response = await apiFetch("/inventory/items?limit=100");
    //console.log("📦 Inventory response:", response);

    // Response structure: { success, message, total, page, page_size, total_pages, data: [...] }
    if (response.data && Array.isArray(response.data)) {
      return response.data;
    }

    if (Array.isArray(response)) {
      return response;
    }

    return [];
  } catch (error) {
    console.error("Failed to load inventory items:", error);
    return [];
  }
}

async function checkInventoryItem(itemId) {
  try {
    const response = await apiFetch(`/inventory/items/${itemId}`);
    return response.data || response;
  } catch (error) {
    console.warn("Item not found in inventory:", error.message);
    return null;
  }
}

// ============================================================
// RENDER FUNCTIONS
// ============================================================
function showLoadingState() {
  const grid = DOM.projectCardGrid;
  if (!grid) return;
  grid.innerHTML = `
    <div class="loading-placeholder" style="grid-column:1/-1; text-align:center; padding:3rem 0;">
      <i class="ph ph-spinner" style="font-size:2rem; animation: spin 1s linear infinite;"></i>
      <p style="margin-top:0.5rem; color:var(--text-muted);">Loading projects...</p>
    </div>
  `;
}

function renderProjects(projects) {
  const grid = DOM.projectCardGrid;
  if (!grid) return;

  if (!projects || projects.length === 0) {
    grid.innerHTML = `
      <div style="grid-column:1/-1; text-align:center; padding:3rem 0; color: var(--text-muted);">
        <i class="ph ph-folder-open" style="font-size:3rem; display:block; margin-bottom:1rem;"></i>
        <p>No projects found</p>
        <button class="btn-primary" onclick="openCreateProjectModal()">
          <i class="ph ph-plus"></i> Create your first project
        </button>
      </div>
    `;
    return;
  }

  grid.innerHTML = projects
    .map(
      (project) => `
    <div class="project-card fade-in" data-id="${project.id}">
      <div class="card-header">
        <h3 class="project-name" onclick="openProjectDrawer('${project.id}')" style="cursor:pointer;">${escapeHtml(project.name)}</h3>
        <div class="card-actions">
          <button onclick="event.stopPropagation(); openEditProjectModal('${project.id}')" title="Edit Project" class="card-action-btn">
            <i class="ph ph-pencil-simple"></i>
          </button>
          <button onclick="event.stopPropagation(); confirmDeleteProject('${project.id}')" title="Delete Project" class="card-action-btn">
            <i class="ph ph-trash"></i>
          </button>
        </div>
      </div>
      <div class="card-body" onclick="openProjectDrawer('${project.id}')" style="cursor:pointer;">
        <div class="customer-info">
          <i class="ph ph-user"></i>
          <span>${escapeHtml(project.customer_name || "Unknown")}</span>
        </div>
        <div class="vehicle-info">
          <i class="ph ph-car"></i>
          <span>${escapeHtml(project.vehicle_brand || "")} ${escapeHtml(project.vehicle_model || "")}</span>
        </div>
        <div class="progress-container">
          <div class="progress-bar-wrapper">
            <div class="progress-bar">
              <div class="progress-fill" style="width:${project.progress || 0}%;"></div>
            </div>
            <span class="progress-text">${project.progress || 0}%</span>
          </div>
          <button onclick="event.stopPropagation(); openProgressPopup('${project.id}')" class="btn-update-progress" title="Update Progress">
            <i class="ph ph-gauge"></i> Update
          </button>
        </div>
        <div class="card-meta">
          <span class="badges-wrapper">
            <span class="status-badge ${getStatusBadgeClass(project.status)}">${getStatusLabel(project.status)}</span>
            <span class="priority-badge ${getPriorityBadgeClass(project.priority)}">${getPriorityLabel(project.priority)}</span>
          </span>
          <span class="project-date">
            <i class="ph ph-calendar"></i> ${formatDate(project.created_at)}
          </span>
        </div>
      </div>
    </div>
  `,
    )
    .join("");
}

function updatePagination(page, totalPages, totalItems) {
  const info = DOM.pageInfo;
  const prev = DOM.prevPageBtn;
  const next = DOM.nextPageBtn;

  if (info)
    info.textContent = `Page ${page} of ${Math.max(1, totalPages)} (${totalItems} items)`;
  if (prev) {
    prev.disabled = page <= 1;
    prev.style.opacity = page <= 1 ? "0.5" : "1";
  }
  if (next) {
    const isLastPage = page >= totalPages || totalPages === 0;
    next.disabled = isLastPage;
    next.style.opacity = isLastPage ? "0.5" : "1";
  }
}

function updateDashboard(stats) {
  if (!stats) return;
  const active = stats.active_count || stats.by_status?.active || 0;
  const inProgress =
    stats.in_production_count || stats.by_status?.in_progress || 0;
  const completed =
    stats.completed_this_month || stats.by_status?.completed || 0;
  const revenue =
    stats.estimated_revenue || stats.financial?.estimated_revenue || 0;

  if (DOM.activeCount) DOM.activeCount.textContent = active;
  if (DOM.prodCount) DOM.prodCount.textContent = inProgress;
  if (DOM.completedCount) DOM.completedCount.textContent = completed;
  if (DOM.revenueTotal) DOM.revenueTotal.textContent = formatCurrency(revenue);
}

// ============================================================
// DRAWER RENDER FUNCTIONS
// ============================================================
function renderOverview(projectData) {
  const project = projectData?.project || projectData;
  if (!project) return;

  if (DOM.drawerTitle)
    DOM.drawerTitle.textContent = project.name || "Project Details";
  if (DOM.drawerSubtitle)
    DOM.drawerSubtitle.textContent = `ID: ${project.id?.substring(0, 8) || "N/A"}`;

  const fields = {
    drawerCustomer: project.customer_name,
    drawerPhone: project.customer_phone,
    drawerEmail: project.customer_email,
    drawerBrand: project.vehicle_brand,
    drawerModel: project.vehicle_model,
    drawerYear: project.vehicle_year,
    drawerPlate: project.vehicle_license_plate,
  };
  Object.keys(fields).forEach((key) => {
    const el = DOM[key];
    if (el) {
      const value = fields[key];
      el.textContent =
        value !== undefined && value !== null && value !== "" ? value : "-";
    }
  });

  if (DOM.drawerStatus) {
    DOM.drawerStatus.innerHTML = `<span class="status-badge ${getStatusBadgeClass(project.status)}">${getStatusLabel(project.status)}</span>`;
  }
  if (DOM.drawerPriority) {
    DOM.drawerPriority.innerHTML = `<span class="priority-badge ${getPriorityBadgeClass(project.priority)}">${getPriorityLabel(project.priority)}</span>`;
  }

  const progress = project.progress || 0;
  if (DOM.drawerProgressFill)
    DOM.drawerProgressFill.style.width = `${progress}%`;
  if (DOM.drawerProgressText)
    DOM.drawerProgressText.textContent = `${progress}%`;
  if (DOM.drawerNotes) DOM.drawerNotes.textContent = project.notes || "-";
}

function renderMaterials(projectData) {
  const container = DOM.drawerMaterialsList;
  if (!container) return;

  const financial = projectData?.financial_summary || {};
  const materialUsages = financial.material_usages || [];

  // console.log("📦 Rendering materials:", materialUsages);

  if (!materialUsages || materialUsages.length === 0) {
    container.innerHTML =
      '<p style="color:var(--text-muted);">No materials consumed yet.</p>';
    return;
  }

  container.innerHTML = materialUsages
    .map((item) => {
      const name =
        item.item_name ||
        item.material_name ||
        item.name ||
        (item.item_id ? `ID: ${item.item_id.substring(0, 8)}` : "Unknown");
      const id = item.id;

      return `
      <div class="material-list-item" data-id="${id}">
        <span class="name">${escapeHtml(name)}</span>
        <span class="qty">${item.quantity} ${item.unit || item.item_unit || ""} (${formatCurrency(item.total_cost)})</span>
        <button onclick="handleDeleteMaterial('${id}')" class="btn-danger btn-sm" title="Delete material usage">
          <i class="ph ph-trash"></i>
        </button>
      </div>
    `;
    })
    .join("");
}

// ============================================================
// HANDLE DELETE MATERIAL
// ============================================================

async function handleDeleteMaterial(usageId) {
  if (
    !confirm(
      "Are you sure you want to delete this material usage? This action cannot be undone.",
    )
  ) {
    return;
  }

  const result = await deleteMaterialUsage(usageId);
  if (result) {
    showToast("Material usage deleted successfully", "success");

    // Refresh drawer data
    if (state.currentProjectId) {
      const projectData = await fetchProjectDetail(state.currentProjectId);
      if (projectData) {
        state._currentProjectData = projectData;
        renderMaterials(projectData);
      }
    }
    await loadProjects();
  }
}

// ============================================================
// HANDLE DELETE LABOR
// ============================================================

async function handleDeleteLabor(laborId) {
  if (
    !confirm(
      "Are you sure you want to delete this labor entry? This action cannot be undone.",
    )
  ) {
    return;
  }

  const result = await deleteLabor(laborId);
  if (result) {
    showToast("Labor entry deleted successfully", "success");

    // Refresh drawer data
    if (state.currentProjectId) {
      const projectData = await fetchProjectDetail(state.currentProjectId);
      if (projectData) {
        state._currentProjectData = projectData;
        renderLabor(projectData);
      }
    }
    await loadProjects();
  }
}

function renderLabor(projectData) {
  const container = DOM.laborList;
  if (!container) return;

  const financial = projectData?.financial_summary || {};
  const laborItems = financial.labor_items || [];

  // console.log("👷 Rendering labor:", laborItems);

  if (!laborItems || laborItems.length === 0) {
    container.innerHTML =
      '<p style="color:var(--text-muted);">No labor recorded.</p>';
    return;
  }

  container.innerHTML = laborItems
    .map((item) => {
      // Try multiple possible field names for labor type
      let name =
        item.labor_type ||
        item.name ||
        item.type ||
        item.labor?.type ||
        item.labor?.name ||
        item.technician_name ||
        item.description ||
        "Unknown Labor";

      if (name === "Unknown Labor" && item.id) {
        name = `Labor ${item.id.substring(0, 8)}`;
      }

      const hours = item.hours || 0;
      const rate = item.rate_per_hour || item.rate || 0;
      const total = hours * rate;
      const id = item.id;

      let display = `${hours}h`;
      if (rate > 0) display += ` @ ${formatCurrency(rate)}`;
      if (total > 0) display += ` = ${formatCurrency(total)}`;

      return `
      <div class="labor-list-item" data-id="${id}">
        <span class="name">${escapeHtml(name)}</span>
        <span class="hours">${display}</span>
        <button onclick="handleDeleteLabor('${id}')" class="btn-danger btn-sm" title="Delete labor entry">
          <i class="ph ph-trash"></i>
        </button>
      </div>
    `;
    })
    .join("");
}

function renderTimeline(projectData) {
  const project = projectData?.project || projectData;
  if (!project) return;

  if (DOM.drawerStartDate)
    DOM.drawerStartDate.textContent = formatDate(project.project_start_date);
  if (DOM.drawerDelivery)
    DOM.drawerDelivery.textContent = formatDate(
      project.project_target_delivery,
    );
  if (DOM.drawerActualDelivery)
    DOM.drawerActualDelivery.textContent = formatDate(
      project.actual_delivery_date,
    );
  if (DOM.drawerCompletedAt)
    DOM.drawerCompletedAt.textContent = formatDate(project.completed_at);

  const activities = projectData?.activities || [];
  if (DOM.drawerActivities) {
    if (activities.length === 0) {
      DOM.drawerActivities.innerHTML =
        '<p style="color:var(--text-muted);">No activities recorded.</p>';
    } else {
      DOM.drawerActivities.innerHTML = activities
        .map(
          (activity) => `
        <div class="timeline-item">
          <div class="timeline-icon"><i class="ph ph-clock"></i></div>
          <div class="timeline-content">
            <div class="title">${escapeHtml(activity.activity || "Activity")}</div>
            <div class="desc">${escapeHtml(activity.activity_type || "")}</div>
            <div class="time">${formatDateTime(activity.created_at)}</div>
          </div>
        </div>
      `,
        )
        .join("");
    }
  }

  if (DOM.drawerMilestones) {
    const progress = project.progress || 0;
    const milestones = [
      { label: "25% - Initial Phase", done: progress >= 25 },
      { label: "50% - Midway", done: progress >= 50 },
      { label: "75% - Almost Done", done: progress >= 75 },
      { label: "100% - Complete", done: progress >= 100 },
    ];
    if (milestones.some((m) => m.done)) {
      DOM.drawerMilestones.innerHTML = milestones
        .map(
          (m) => `
        <div class="milestone-item">
          <span class="label ${m.done ? "done" : ""}">${m.done ? "✅" : "⬜"} ${m.label}</span>
        </div>
      `,
        )
        .join("");
    } else {
      DOM.drawerMilestones.innerHTML =
        '<p style="color:var(--text-muted);">No milestones reached yet.</p>';
    }
  }
}

function renderTasks(projectData) {
  const container = DOM.drawerTasks;
  if (!container) return;

  const tasks = projectData?.tasks || [];
  if (!tasks || tasks.length === 0) {
    container.innerHTML =
      '<p style="color:var(--text-muted);">No tasks created yet.</p>';
    return;
  }

  container.innerHTML = tasks
    .map(
      (task) => `
    <div class="material-list-item" style="justify-content:space-between;">
      <div>
        <strong>${escapeHtml(task.title)}</strong>
        <span style="font-size:0.8rem;color:var(--text-muted);"> - ${escapeHtml(task.assigned_to || "Unassigned")}</span>
      </div>
      <div style="display:flex;align-items:center;gap:0.5rem;">
        <span class="status-badge ${task.status === "completed" ? "completed" : "in_progress"}">${task.status || "pending"}</span>
        ${
          task.status !== "completed"
            ? `
          <button onclick="handleCompleteTask('${task.id}')" class="btn-primary btn-sm" style="padding:2px 8px;font-size:0.7rem;">
            <i class="ph ph-check"></i>
          </button>
        `
            : ""
        }
      </div>
    </div>
  `,
    )
    .join("");
}

// ============================================================
// LOAD LABOR TYPES FROM PRICE LIST
// ============================================================
async function loadLaborTypes() {
  const select = DOM.laborTypeSelect;
  if (!select) return;

  try {
    const items = await fetchPriceListItems();

    // console.log("👷 All price list items:", items);

    if (!items || items.length === 0) {
      select.innerHTML = getDefaultLaborOptions();
      select.removeEventListener("change", autoFillLaborRate);
      select.addEventListener("change", autoFillLaborRate);
      return;
    }

    // Filter for labor category (category = "labor")
    const laborItems = items.filter(
      (item) =>
        item.category?.toLowerCase() === "labor" && item.is_active !== false,
    );

    // console.log("👷 Filtered labor items:", laborItems);

    if (laborItems.length === 0) {
      select.innerHTML = getDefaultLaborOptions();
      select.removeEventListener("change", autoFillLaborRate);
      select.addEventListener("change", autoFillLaborRate);
      return;
    }

    // Sort and render options
    const sortedItems = [...laborItems].sort((a, b) =>
      (a.name || "").localeCompare(b.name || ""),
    );

    select.innerHTML = `
      <option value="">Select Labor Type</option>
      ${sortedItems
        .map((item) => {
          const name = item.name || "Unknown";
          const price = parseFloat(item.price) || 0;
          const unit = item.unit || "hour";
          const id = item.id;
          const subCategory = item.sub_category || "";
          const description = item.description || "";

          // Use name as value, not ID (for API compatibility)
          const displayName = subCategory ? `${name} (${subCategory})` : name;

          return `
          <option 
            value="${escapeHtml(name)}" 
            data-rate="${price}" 
            data-id="${id}"
            data-unit="${unit}"
            data-sub-category="${subCategory || ""}"
            data-description="${escapeHtml(description)}"
          >
            ${escapeHtml(displayName)} 
            ${price > 0 ? `(${formatCurrency(price)}/${unit})` : ""}
            ${description ? `- ${escapeHtml(description)}` : ""}
          </option>
        `;
        })
        .join("")}
    `;

    select.removeEventListener("change", autoFillLaborRate);
    select.addEventListener("change", autoFillLaborRate);
  } catch (error) {
    console.error("Failed to load labor types:", error);
    select.innerHTML = getDefaultLaborOptions();
    select.removeEventListener("change", autoFillLaborRate);
    select.addEventListener("change", autoFillLaborRate);
  }
}

function autoFillLaborRate() {
  const select = DOM.laborTypeSelect;
  const selected = select?.options[select.selectedIndex];
  const rate = selected?.dataset?.rate;
  const rateEl = DOM.laborRate;
  if (rateEl) {
    if (rate && parseFloat(rate) > 0) {
      rateEl.value = parseFloat(rate);
      rateEl.placeholder = `Auto-filled: ${formatCurrency(parseFloat(rate))}/hour`;
      rateEl.style.borderColor = "var(--success, #10b981)";
    } else {
      rateEl.value = "";
      rateEl.placeholder = "Rate / hour *";
      rateEl.style.borderColor = "";
    }
  }
}

function getDefaultLaborOptions() {
  return `
    <option value="">Select Labor Type</option>
    <option value="Sanding" data-rate="50000">Sanding (Rp 50,000/hour)</option>
    <option value="Priming" data-rate="60000">Priming (Rp 60,000/hour)</option>
    <option value="Painting" data-rate="75000">Painting (Rp 75,000/hour)</option>
    <option value="Clear Coat" data-rate="70000">Clear Coat (Rp 70,000/hour)</option>
    <option value="Polishing" data-rate="55000">Polishing (Rp 55,000/hour)</option>
    <option value="Fabrication" data-rate="80000">Fabrication (Rp 80,000/hour)</option>
    <option value="Assembly" data-rate="65000">Assembly (Rp 65,000/hour)</option>
    <option value="Restoration" data-rate="90000">Restoration (Rp 90,000/hour)</option>
    <option value="Body Work" data-rate="70000">Body Work (Rp 70,000/hour)</option>
    <option value="Quality Control" data-rate="90000">Quality Control (Rp 90,000/hour)</option>
    <option value="Technician - Junior" data-rate="80000">Technician - Junior (Rp 80,000/hour)</option>
    <option value="Technician - Senior" data-rate="120000">Technician - Senior (Rp 120,000/hour)</option>
    <option value="Other" data-rate="50000">Other (Rp 50,000/hour)</option>
  `;
}

// ============================================================
// LOAD MATERIAL ITEMS FROM INVENTORY
// ============================================================
async function loadMaterialItems() {
  const select = DOM.materialSelect;
  if (!select) return;

  try {
    const items = await fetchInventoryItems();

    // console.log("📦 Inventory items for materials:", items);

    if (!items || items.length === 0) {
      select.innerHTML = getDefaultMaterialOptions();
      select.removeEventListener("change", updateMaterialHint);
      select.addEventListener("change", updateMaterialHint);
      return;
    }

    const sortedItems = [...items].sort((a, b) =>
      (a.name || "").localeCompare(b.name || ""),
    );

    select.innerHTML = `
      <option value="">Select Material</option>
      ${sortedItems
        .map((item) => {
          const name = item.name || "Unknown";
          const unit = item.unit || "pcs";
          const id = item.id;
          const price =
            parseFloat(item.selling_price) || parseFloat(item.price) || 0;
          const costPrice = parseFloat(item.cost_price) || 0;
          const stock = parseFloat(item.current_stock) || 0;
          const displayPrice = price > 0 ? price : costPrice;

          // Get status
          const status = item.status || "active";
          const isOutOfStock = stock <= 0 || status === "out_of_stock";

          return `
          <option 
            value="${id}" 
            data-unit="${unit}" 
            data-price="${displayPrice}"
            data-stock="${stock}"
            data-status="${status}"
          >
            ${escapeHtml(name)} 
            (${unit}) 
            ${displayPrice > 0 ? `- ${formatCurrency(displayPrice)}` : ""} 
            ${stock > 0 ? `| Stock: ${stock}` : "| ⚠️ Out of stock"}
          </option>
        `;
        })
        .join("")}
    `;

    select.removeEventListener("change", updateMaterialHint);
    select.addEventListener("change", updateMaterialHint);
  } catch (error) {
    console.error("Failed to load materials:", error);
    select.innerHTML = getDefaultMaterialOptions();
    select.removeEventListener("change", updateMaterialHint);
    select.addEventListener("change", updateMaterialHint);
  }
}

function updateMaterialHint() {
  const select = DOM.materialSelect;
  const selected = select?.options[select.selectedIndex];
  const unit = selected?.dataset?.unit || "";
  const price = selected?.dataset?.price || 0;
  const stock = selected?.dataset?.stock || 0;
  const hintEl = DOM.materialHint;

  if (hintEl) {
    if (selected && selected.value) {
      let hint = `Selected: ${selected.text}`;
      if (price > 0) hint += ` | Price: ${formatCurrency(parseFloat(price))}`;
      if (stock !== undefined && stock !== null) {
        const stockNum = parseFloat(stock);
        if (stockNum > 0) hint += ` | Stock: ${stockNum}`;
        else if (stockNum === 0) hint += ` | ⚠️ OUT OF STOCK`;
      }
      hintEl.textContent = hint;
    } else {
      hintEl.textContent = "Select a material first";
    }
  }

  const unitEl = DOM.materialUnit;
  if (unitEl && unit) unitEl.value = unit;
}

function getDefaultMaterialOptions() {
  return `
    <option value="">Select Material</option>
    <option value="mat-1" data-unit="liter" data-price="58000">Epoxy Primer Putih (liter) - Rp 58,000</option>
    <option value="mat-2" data-unit="liter" data-price="75000">Base Coat (liter) - Rp 75,000</option>
    <option value="mat-3" data-unit="liter" data-price="85000">Clear Coat (liter) - Rp 85,000</option>
    <option value="mat-4" data-unit="roll" data-price="50000">Masking Paper (roll) - Rp 50,000</option>
    <option value="mat-5" data-unit="liter" data-price="100000">Degreaser (liter) - Rp 100,000</option>
  `;
}

// ============================================================
// DRAWER FUNCTIONS
// ============================================================
async function openProjectDrawer(projectId) {
  state.currentProjectId = projectId;
  const projectData = await fetchProjectDetail(projectId);
  if (!projectData) return;

  state._currentProjectData = projectData;
  state._currentProject = projectData.project || projectData;

  switchTab("overview");
  renderOverview(projectData);
  renderTimeline(projectData);
  renderMaterials(projectData);
  renderLabor(projectData);
  renderTasks(projectData);

  await loadMaterialItems();
  await loadLaborTypes();

  if (DOM.drawer) DOM.drawer.classList.add("active");
  if (DOM.drawerBackdrop) DOM.drawerBackdrop.classList.add("active");
  document.body.style.overflow = "hidden";
}

function closeDrawer() {
  if (DOM.drawer) DOM.drawer.classList.remove("active");
  if (DOM.drawerBackdrop) DOM.drawerBackdrop.classList.remove("active");
  document.body.style.overflow = "";
  state.currentProjectId = null;
  state._currentProjectData = null;
}

function switchTab(tabName) {
  if (DOM.tabBtns) {
    DOM.tabBtns.forEach((btn) => {
      const isActive = btn.dataset.tab === tabName;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", isActive);
    });
  }
  if (DOM.tabPanels) {
    Object.keys(DOM.tabPanels).forEach((key) => {
      const panel = DOM.tabPanels[key];
      if (panel) panel.classList.toggle("active", key === tabName);
    });
  }
}

// ============================================================
// MODAL FUNCTIONS
// ============================================================
function closeProjectModal() {
  if (DOM.projectModal) DOM.projectModal.classList.remove("active");
  document.body.style.overflow = "";
}

function openCreateProjectModal() {
  if (DOM.modalTitle) DOM.modalTitle.textContent = "Create New Project";
  if (DOM.modalSubtitle)
    DOM.modalSubtitle.textContent =
      "Register workshop project and production schedule";
  if (DOM.editProjectId) DOM.editProjectId.value = "";
  if (DOM.projectForm) DOM.projectForm.reset();
  if (DOM.submitProjectBtn) DOM.submitProjectBtn.textContent = "Create Project";
  if (DOM.projectModal) {
    DOM.projectModal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

async function openEditProjectModal(projectId) {
  const projectData = await fetchProjectDetail(projectId);
  const project = projectData?.project || projectData;
  if (!project) return;

  if (DOM.modalTitle) DOM.modalTitle.textContent = "Edit Project";
  if (DOM.modalSubtitle)
    DOM.modalSubtitle.textContent = "Update project information";
  if (DOM.editProjectId) DOM.editProjectId.value = projectId;
  if (DOM.submitProjectBtn) DOM.submitProjectBtn.textContent = "Update Project";

  const fields = {
    projectName: project.name,
    customerName: project.customer_name,
    customerPhone: project.customer_phone,
    customerEmail: project.customer_email,
    projectStatus: project.status || "active",
    projectPriority: project.priority || "medium",
    vehicleBrand: project.vehicle_brand,
    vehicleModel: project.vehicle_model,
    vehicleYear: project.vehicle_year,
    licensePlate: project.vehicle_license_plate,
    estimatedCost: project.estimated_cost,
    estimatedRevenue: project.estimated_revenue,
    startDate: project.project_start_date
      ? project.project_start_date.split("T")[0]
      : "",
    targetDelivery: project.project_target_delivery
      ? project.project_target_delivery.split("T")[0]
      : "",
    projectNotes: project.notes,
  };
  Object.keys(fields).forEach((key) => {
    const el = DOM[key];
    if (el) el.value = fields[key] || "";
  });

  if (DOM.projectModal) {
    DOM.projectModal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

function confirmDeleteProject(projectId) {
  if (confirm("Are you sure you want to delete this project?")) {
    handleDeleteProject(projectId);
  }
}

async function handleDeleteProject(projectId) {
  const result = await deleteProject(projectId);
  if (result) {
    showToast("Project deleted successfully", "success");
    await loadProjects();
    if (DOM.drawer && DOM.drawer.classList.contains("active")) closeDrawer();
  }
}

// ============================================================
// PROGRESS POPUP
// ============================================================
function openProgressPopup(projectId) {
  const project = state.projects.find((p) => p.id === projectId);
  if (!project) {
    showToast("Project not found", "error");
    return;
  }

  state._progressProjectId = projectId;
  const progress = project.progress || 0;

  if (DOM.progressPopupSlider) DOM.progressPopupSlider.value = progress;
  if (DOM.progressPopupValue) DOM.progressPopupValue.textContent = progress;
  if (DOM.progressPopupNote) DOM.progressPopupNote.value = "";
  if (DOM.markCompleteCheckbox)
    DOM.markCompleteCheckbox.checked = progress >= 100;

  if (DOM.progressPopupMilestones) {
    DOM.progressPopupMilestones.innerHTML = `
      <div class="milestone-item"><input type="checkbox" class="checkbox" ${progress >= 25 ? "checked" : ""} /><span class="label ${progress >= 25 ? "done" : ""}">25% - Initial Phase</span></div>
      <div class="milestone-item"><input type="checkbox" class="checkbox" ${progress >= 50 ? "checked" : ""} /><span class="label ${progress >= 50 ? "done" : ""}">50% - Midway</span></div>
      <div class="milestone-item"><input type="checkbox" class="checkbox" ${progress >= 75 ? "checked" : ""} /><span class="label ${progress >= 75 ? "done" : ""}">75% - Almost Done</span></div>
      <div class="milestone-item"><input type="checkbox" class="checkbox" ${progress >= 100 ? "checked" : ""} /><span class="label ${progress >= 100 ? "done" : ""}">100% - Complete</span></div>
    `;
  }

  if (DOM.progressPopup) {
    DOM.progressPopup.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

function closeProgressPopup() {
  if (DOM.progressPopup) DOM.progressPopup.classList.remove("active");
  document.body.style.overflow = "";
  state._progressProjectId = null;
}

async function handleSaveProgress() {
  const projectId = state._progressProjectId;
  if (!projectId) {
    showToast("No project selected", "error");
    return;
  }

  const progress = parseInt(
    DOM.progressPopupSlider ? DOM.progressPopupSlider.value : 0,
  );
  const note = DOM.progressPopupNote ? DOM.progressPopupNote.value.trim() : "";

  if (isNaN(progress) || progress < 0 || progress > 100) {
    showToast("Progress must be between 0 and 100", "error");
    return;
  }

  const result = await updateProjectProgress(projectId, progress, note);
  if (result) {
    showToast(`Progress updated to ${progress}%`, "success");
    if (
      progress >= 100 &&
      DOM.markCompleteCheckbox &&
      DOM.markCompleteCheckbox.checked
    ) {
      await completeProject(projectId);
      showToast("Project marked as completed! 🎉", "success");
    }
    closeProgressPopup();
    await loadProjects();
    if (
      DOM.drawer &&
      DOM.drawer.classList.contains("active") &&
      state.currentProjectId === projectId
    ) {
      await openProjectDrawer(projectId);
    }
  }
}

// ============================================================
// TASK FUNCTIONS
// ============================================================
function openTaskModal(projectId) {
  if (DOM.taskProjectId) DOM.taskProjectId.value = projectId;
  if (DOM.taskForm) DOM.taskForm.reset();
  if (DOM.taskModal) {
    DOM.taskModal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

function closeTaskModal() {
  if (DOM.taskModal) DOM.taskModal.classList.remove("active");
  document.body.style.overflow = "";
}

async function handleAddTask(e) {
  e.preventDefault();
  const projectId = DOM.taskProjectId?.value || "";
  if (!projectId) {
    showToast("Project ID missing", "error");
    return;
  }

  const data = {
    title: DOM.taskTitle?.value?.trim() || "",
    description: DOM.taskDescription?.value?.trim() || "",
    assigned_to: DOM.taskAssignee?.value?.trim() || "",
    priority: DOM.taskPriority?.value || "medium",
    due_date: DOM.taskDueDate?.value || null,
  };
  if (!data.title) {
    showToast("Task title is required", "error");
    return;
  }

  const result = await addTask(projectId, data);
  if (result) {
    showToast("Task added successfully", "success");
    closeTaskModal();
    if (state.currentProjectId) {
      const projectData = await fetchProjectDetail(state.currentProjectId);
      if (projectData) {
        state._currentProjectData = projectData;
        renderTasks(projectData);
      }
    }
    await loadProjects();
  }
}

async function handleCompleteTask(taskId) {
  if (confirm("Mark this task as completed?")) {
    const result = await completeTask(taskId);
    if (result) {
      showToast("Task completed! 🎉", "success");
      if (state.currentProjectId) {
        const projectData = await fetchProjectDetail(state.currentProjectId);
        if (projectData) {
          state._currentProjectData = projectData;
          renderTasks(projectData);
        }
        await loadProjects();
      }
    }
  }
}

// ============================================================
// MATERIAL & LABOR HANDLERS
// ============================================================
async function handleConsumeMaterial() {
  const projectId = state.currentProjectId;
  if (!projectId) {
    showToast("No project selected", "error");
    return;
  }

  const itemId = DOM.materialSelect?.value || "";
  const quantity = parseFloat(DOM.materialQty?.value || 0);
  const unit = DOM.materialUnit?.value || "";

  if (!itemId) {
    showToast("Please select a material", "error");
    return;
  }
  if (itemId.startsWith("mat-")) {
    showToast("Please select a valid material from inventory", "error");
    return;
  }
  if (!quantity || quantity <= 0) {
    showToast("Please enter a valid quantity", "error");
    return;
  }

  const selected =
    DOM.materialSelect?.options[DOM.materialSelect.selectedIndex];
  const materialName = selected?.text?.split("(")[0]?.trim() || "Material";
  const stock = parseFloat(selected?.dataset?.stock) || 0;

  if (stock > 0 && quantity > stock) {
    showToast(`Insufficient stock! Available: ${stock} ${unit}`, "error");
    return;
  }

  const inventoryItem = await checkInventoryItem(itemId);
  if (!inventoryItem) {
    showToast(`Material "${materialName}" not found in inventory.`, "error");
    return;
  }

  const result = await consumeMaterial({
    project_id: projectId,
    item_id: itemId,
    quantity: quantity,
    note: `Consumed ${quantity} ${unit} of ${materialName}`,
  });

  if (result) {
    showToast(`✅ Consumed: ${quantity} ${unit} ${materialName}`, "success");
    if (DOM.materialQty) DOM.materialQty.value = "";
    await loadMaterialItems();
    if (state.currentProjectId) {
      const projectData = await fetchProjectDetail(state.currentProjectId);
      if (projectData) {
        state._currentProjectData = projectData;
        renderMaterials(projectData);
      }
    }
    await loadProjects();
  }
}

async function handleAddLabor() {
  const projectId = state.currentProjectId;
  if (!projectId) {
    showToast("No project selected", "error");
    return;
  }

  const typeSelect = DOM.laborTypeSelect;
  const hoursEl = DOM.laborHours;
  const rateEl = DOM.laborRate;

  const laborType = typeSelect ? typeSelect.value : "";
  const hours = parseFloat(hoursEl ? hoursEl.value : 0);
  const rate = parseFloat(rateEl ? rateEl.value : 0);

  if (!laborType) {
    showToast("Please select labor type", "error");
    typeSelect?.focus();
    return;
  }

  if (!hours || hours <= 0) {
    showToast("Please enter valid hours (minimum 0.5)", "error");
    hoursEl?.focus();
    return;
  }

  if (!rate || rate <= 0) {
    showToast("Rate per hour is required", "error");
    rateEl?.focus();
    return;
  }

  // Get additional info from selected option
  const selected = typeSelect?.options[typeSelect.selectedIndex];
  const subCategory = selected?.dataset?.subCategory || "";
  const description = selected?.dataset?.description || "";

  // Show confirmation
  const totalCost = hours * rate;
  if (
    !confirm(
      `Add ${hours}h of "${laborType}" @ ${formatCurrency(rate)}/hour = ${formatCurrency(totalCost)}?`,
    )
  ) {
    return;
  }

  const data = {
    labor_type: laborType,
    hours: hours,
    rate_per_hour: rate,
    technician_name: subCategory || laborType,
    description: description || `Labor: ${laborType} for ${hours} hours`,
  };

  console.log("📤 Adding labor with data:", data);

  const result = await addLabor(projectId, data);
  if (result) {
    showToast(
      `✅ Added: ${hours}h ${laborType} (${formatCurrency(totalCost)})`,
      "success",
    );
    if (hoursEl) hoursEl.value = "";
    // Keep rate for next entry

    // Refresh drawer data
    if (state.currentProjectId) {
      const projectData = await fetchProjectDetail(state.currentProjectId);
      if (projectData) {
        state._currentProjectData = projectData;
        renderLabor(projectData);
      }
    }
    await loadProjects();
  }
}

// ============================================================
// MAIN LOAD FUNCTION
// ============================================================
async function loadProjects() {
  const data = await fetchProjects(state.currentPage, state.filters);
  if (!data) {
    if (DOM.projectCardGrid) {
      DOM.projectCardGrid.innerHTML = `
        <div style="grid-column:1/-1; text-align:center; padding:3rem 0; color: var(--text-muted);">
          <i class="ph ph-warning" style="font-size:2rem; display:block; margin-bottom:1rem;"></i>
          <p>Failed to load projects. Please try again.</p>
          <button class="btn-primary" onclick="loadProjects()"><i class="ph ph-arrow-clockwise"></i> Retry</button>
        </div>
      `;
    }
    return;
  }

  let projects = [],
    totalPages = 1,
    totalItems = 0;
  if (data.data && Array.isArray(data.data)) {
    projects = data.data;
    totalItems = data.total || data.total_items || projects.length;
    totalPages =
      data.total_pages ||
      data.totalPages ||
      Math.ceil(totalItems / PROJECTS_PER_PAGE) ||
      1;
  } else if (Array.isArray(data)) {
    projects = data;
    totalItems = projects.length;
    totalPages = Math.ceil(totalItems / PROJECTS_PER_PAGE) || 1;
  } else if (data.items && Array.isArray(data.items)) {
    projects = data.items;
    totalItems = data.total || data.total_items || projects.length;
    totalPages =
      data.total_pages ||
      data.totalPages ||
      Math.ceil(totalItems / PROJECTS_PER_PAGE) ||
      1;
  }

  state.projects = projects;
  state.totalPages = Math.max(1, totalPages);
  state.totalItems = totalItems;

  renderProjects(state.projects);
  updatePagination(state.currentPage, state.totalPages, state.totalItems);

  const stats = await fetchProjectStatistics();
  if (stats) updateDashboard(stats);
}

// ============================================================
// EVENT HANDLERS
// ============================================================
if (DOM.prevPageBtn) {
  DOM.prevPageBtn.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage--;
      loadProjects();
    }
  });
}
if (DOM.nextPageBtn) {
  DOM.nextPageBtn.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      state.currentPage++;
      loadProjects();
    }
  });
}

if (DOM.projectSearch) {
  let searchTimeout = null;
  DOM.projectSearch.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.currentPage = 1;
      loadProjects();
    }, 300);
  });
}
if (DOM.statusFilter) {
  DOM.statusFilter.addEventListener("change", (e) => {
    state.filters.status = e.target.value;
    state.currentPage = 1;
    loadProjects();
  });
}
if (DOM.priorityFilter) {
  DOM.priorityFilter.addEventListener("change", (e) => {
    state.filters.priority = e.target.value;
    state.currentPage = 1;
    loadProjects();
  });
}

if (DOM.createProjectBtn)
  DOM.createProjectBtn.addEventListener("click", openCreateProjectModal);
if (DOM.closeModal) DOM.closeModal.addEventListener("click", closeProjectModal);
if (DOM.cancelModalBtn)
  DOM.cancelModalBtn.addEventListener("click", closeProjectModal);
if (DOM.projectModal) {
  DOM.projectModal.addEventListener("click", (e) => {
    if (e.target === DOM.projectModal) closeProjectModal();
  });
}

if (DOM.closeDrawer) DOM.closeDrawer.addEventListener("click", closeDrawer);
if (DOM.drawerBackdrop)
  DOM.drawerBackdrop.addEventListener("click", closeDrawer);

if (DOM.closeProgressPopup)
  DOM.closeProgressPopup.addEventListener("click", closeProgressPopup);
if (DOM.cancelProgressBtn)
  DOM.cancelProgressBtn.addEventListener("click", closeProgressPopup);
if (DOM.progressPopup) {
  DOM.progressPopup.addEventListener("click", (e) => {
    if (e.target === DOM.progressPopup) closeProgressPopup();
  });
}

if (DOM.progressPopupSlider) {
  DOM.progressPopupSlider.addEventListener("input", (e) => {
    const val = e.target.value;
    if (DOM.progressPopupValue) DOM.progressPopupValue.textContent = val;
    if (DOM.markCompleteCheckbox)
      DOM.markCompleteCheckbox.checked = parseInt(val) >= 100;
    const milestones = DOM.progressPopupMilestones;
    if (milestones) {
      const items = milestones.querySelectorAll(".milestone-item");
      const progress = parseInt(val);
      const thresholds = [25, 50, 75, 100];
      items.forEach((item, index) => {
        const checkboxEl = item.querySelector(".checkbox");
        const labelEl = item.querySelector(".label");
        const threshold = thresholds[index];
        if (checkboxEl) checkboxEl.checked = progress >= threshold;
        if (labelEl) labelEl.classList.toggle("done", progress >= threshold);
      });
    }
  });
}
if (DOM.saveProgressBtn)
  DOM.saveProgressBtn.addEventListener("click", handleSaveProgress);

if (DOM.addTaskBtn) {
  DOM.addTaskBtn.addEventListener("click", () => {
    if (state.currentProjectId) openTaskModal(state.currentProjectId);
  });
}
if (DOM.closeTaskModal)
  DOM.closeTaskModal.addEventListener("click", closeTaskModal);
if (DOM.cancelTaskBtn)
  DOM.cancelTaskBtn.addEventListener("click", closeTaskModal);
if (DOM.taskModal) {
  DOM.taskModal.addEventListener("click", (e) => {
    if (e.target === DOM.taskModal) closeTaskModal();
  });
}
if (DOM.taskForm) DOM.taskForm.addEventListener("submit", handleAddTask);

if (DOM.consumeMaterialBtn)
  DOM.consumeMaterialBtn.addEventListener("click", handleConsumeMaterial);
if (DOM.addLaborBtn) DOM.addLaborBtn.addEventListener("click", handleAddLabor);

if (DOM.tabBtns && DOM.tabBtns.length) {
  DOM.tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

if (DOM.projectForm) {
  DOM.projectForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const editId = DOM.editProjectId?.value || "";
    const isEdit = !!editId;
    const data = {
      name: DOM.projectName?.value?.trim(),
      customer_name: DOM.customerName?.value?.trim(),
      customer_phone: DOM.customerPhone?.value?.trim(),
      customer_email: DOM.customerEmail?.value?.trim(),
      status: DOM.projectStatus?.value || "active",
      priority: DOM.projectPriority?.value || "medium",
      vehicle_brand: DOM.vehicleBrand?.value?.trim(),
      vehicle_model: DOM.vehicleModel?.value?.trim(),
      vehicle_year: DOM.vehicleYear?.value
        ? parseInt(DOM.vehicleYear.value)
        : null,
      vehicle_license_plate: DOM.licensePlate?.value?.trim(),
      estimated_cost: DOM.estimatedCost?.value
        ? parseFloat(DOM.estimatedCost.value)
        : null,
      estimated_revenue: DOM.estimatedRevenue?.value
        ? parseFloat(DOM.estimatedRevenue.value)
        : null,
      project_start_date: DOM.startDate?.value || null,
      project_target_delivery: DOM.targetDelivery?.value || null,
      notes: DOM.projectNotes?.value?.trim(),
    };
    if (
      !data.name ||
      !data.customer_name ||
      !data.vehicle_brand ||
      !data.vehicle_model
    ) {
      showToast("Please fill in all required fields", "error");
      return;
    }
    const result = isEdit
      ? await updateProject(editId, data)
      : await createProject(data);
    if (result) {
      showToast(isEdit ? "Project updated" : "Project created", "success");
      closeProjectModal();
      await loadProjects();
    }
  });
}

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (DOM.progressPopup?.classList.contains("active")) {
      closeProgressPopup();
      e.preventDefault();
    }
    if (DOM.projectModal?.classList.contains("active")) {
      closeProjectModal();
      e.preventDefault();
    }
    if (DOM.taskModal?.classList.contains("active")) {
      closeTaskModal();
      e.preventDefault();
    }
    if (DOM.drawer?.classList.contains("active")) {
      closeDrawer();
      e.preventDefault();
    }
  }
  if (e.ctrlKey && e.key === "n") {
    e.preventDefault();
    openCreateProjectModal();
  }
  if (e.ctrlKey && e.key === "f") {
    e.preventDefault();
    if (DOM.projectSearch) DOM.projectSearch.focus();
  }
});

// ============================================================
// INITIALIZATION
// ============================================================
async function init() {
  console.log("🚀 Initializing Projects page...");
  try {
    await loadProjects();
    await loadMaterialItems();
    await loadLaborTypes();
    console.log("✅ Projects page initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", init);

const deleteButtonStyles = document.createElement("style");
deleteButtonStyles.textContent = `
  /* Material & Labor list items with delete button */
  .material-list-item,
  .labor-list-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.75rem;
    background: var(--bg-input);
    border-radius: var(--radius-sm);
    margin-bottom: 0.25rem;
    font-size: 0.85rem;
    gap: 0.5rem;
  }

  .material-list-item .name,
  .labor-list-item .name {
    color: var(--text-primary);
    flex: 1;
  }

  .material-list-item .qty,
  .labor-list-item .hours {
    color: var(--text-secondary);
    margin-right: 0.5rem;
  }

  .btn-danger {
    background: var(--danger, #ef4444);
    color: white;
    border: none;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.7rem;
    transition: all 0.2s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    flex-shrink: 0;
  }

  .btn-danger:hover {
    background: var(--danger-dark, #dc2626);
    transform: scale(1.05);
  }

  .btn-danger:active {
    transform: scale(0.95);
  }

  .btn-sm {
    padding: 2px 8px;
    font-size: 0.7rem;
  }

  .material-list-item .btn-danger,
  .labor-list-item .btn-danger {
    opacity: 0.6;
    transition: opacity 0.2s ease;
  }

  .material-list-item:hover .btn-danger,
  .labor-list-item:hover .btn-danger {
    opacity: 1;
  }
`;

document.head.appendChild(deleteButtonStyles);

// ============================================================
// EXPOSE FUNCTIONS TO GLOBAL SCOPE
// ============================================================
window.openCreateProjectModal = openCreateProjectModal;
window.openEditProjectModal = openEditProjectModal;
window.openProjectDrawer = openProjectDrawer;
window.confirmDeleteProject = confirmDeleteProject;
window.openProgressPopup = openProgressPopup;
window.handleCompleteTask = handleCompleteTask;
window.loadProjects = loadProjects;
window.closeDrawer = closeDrawer;
window.closeProjectModal = closeProjectModal;
window.closeProgressPopup = closeProgressPopup;
window.closeTaskModal = closeTaskModal;
window.handleDeleteMaterial = handleDeleteMaterial;
window.handleDeleteLabor = handleDeleteLabor;

console.log("📋 Projects page fully loaded");
