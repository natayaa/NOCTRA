// projects/dom.js (FIXED & IMPROVED)

export const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

export const $$ = (selector) => document.querySelectorAll(selector);

export const $exists = (id) => !!document.getElementById(id);

export const $safe = (id, fallback = null) => {
  const el = document.getElementById(id);
  return el || fallback;
};

// ✅ Drawer backdrop
export const drawerBackdrop = document.createElement("div");
drawerBackdrop.className = "drawer-backdrop";
drawerBackdrop.id = "drawerBackdrop";
document.body.appendChild(drawerBackdrop);

export const DOM = {
  // Dashboard
  activeCount: () => $("activeCount"),
  prodCount: () => $("prodCount"),
  completedCount: () => $("completedCount"),
  revenueTotal: () => $("revenueTotal"),

  // Toolbar
  projectSearch: () => $("projectSearch"),
  statusFilter: () => $("statusFilter"),
  priorityFilter: () => $("priorityFilter"),
  createProjectBtn: () => $("createProjectBtn"),

  // Grid
  projectCardGrid: () => $("projectCardGrid"),

  // Pagination
  prevPageBtn: () => $("prevPageBtn"),
  nextPageBtn: () => $("nextPageBtn"),
  pageInfo: () => $("pageInfo"),

  // Project Modal
  projectModal: () => $("projectModal"),
  modalTitle: () => $("modalTitle"),
  modalSubtitle: () => $("modalSubtitle"),
  editProjectId: () => $("editProjectId"),
  projectForm: () => $("projectForm"),
  projectName: () => $("projectName"),
  customerName: () => $("customerName"),
  customerPhone: () => $("customerPhone"),
  customerEmail: () => $("customerEmail"),
  projectStatus: () => $("projectStatus"),
  projectPriority: () => $("projectPriority"),
  vehicleBrand: () => $("vehicleBrand"),
  vehicleModel: () => $("vehicleModel"),
  vehicleYear: () => $("vehicleYear"),
  licensePlate: () => $("licensePlate"),
  estimatedCost: () => $("estimatedCost"),
  estimatedRevenue: () => $("estimatedRevenue"),
  startDate: () => $("startDate"),
  targetDelivery: () => $("targetDelivery"),
  projectNotes: () => $("projectNotes"),
  submitProjectBtn: () => $("submitProjectBtn"),
  cancelModalBtn: () => $("cancelModalBtn"),
  closeModal: () => $("closeModal"),

  // Drawer
  drawer: () => $("projectDrawer"),
  drawerTitle: () => $("drawerTitle"),
  drawerSubtitle: () => $("drawerSubtitle"),
  closeDrawer: () => $("closeDrawer"),
  drawerBackdrop: () => $("drawerBackdrop"),
  drawerCustomer: () => $("drawerCustomer"),
  drawerPhone: () => $("drawerPhone"),
  drawerEmail: () => $("drawerEmail"),
  drawerBrand: () => $("drawerBrand"),
  drawerModel: () => $("drawerModel"),
  drawerYear: () => $("drawerYear"),
  drawerPlate: () => $("drawerPlate"),
  drawerStatus: () => $("drawerStatus"),
  drawerPriority: () => $("drawerPriority"),
  drawerProgressFill: () => $("drawerProgressFill"),
  drawerProgressText: () => $("drawerProgressText"),
  drawerNotes: () => $("drawerNotes"),
  budgetPercentage: () => $("budgetPercentage"),
  budgetProgressFillFinancial: () => $("budgetProgressFillFinancial"),

  // Material
  materialSelect: () => $("materialSelect"),
  materialQty: () => $("materialQty"),
  materialUnit: () => $("materialUnit"),
  materialHint: () => $("materialHint"),
  consumeMaterialBtn: () => $("consumeMaterialBtn"),
  drawerMaterialsList: () => $("drawerMaterialsList"),

  // Labor
  laborTypeSelect: () => $("laborTypeSelect"),
  laborHours: () => $("laborHours"),
  laborRate: () => $("laborRate"),
  addLaborBtn: () => $("addLaborBtn"),
  laborList: () => $("laborList"),

  // Timeline
  drawerStartDate: () => $("drawerStartDate"),
  drawerDelivery: () => $("drawerDelivery"),
  drawerActualDelivery: () => $("drawerActualDelivery"),
  drawerCompletedAt: () => $("drawerCompletedAt"),
  drawerMilestones: () => $("drawerMilestones"),
  drawerActivities: () => $("drawerActivities"),

  // Tasks
  drawerTasks: () => $("drawerTasks"),
  addTaskBtn: () => $("addTaskBtn"),

  // Progress Popup
  progressPopup: () => $("progressPopup"),
  progressPopupSlider: () => $("progressPopupSlider"),
  progressPopupValue: () => $("progressPopupValue"),
  progressPopupNote: () => $("progressPopupNote"),
  markCompleteCheckbox: () => $("markCompleteCheckbox"),
  progressPopupMilestones: () => $("progressPopupMilestones"),
  saveProgressBtn: () => $("saveProgressBtn"),
  cancelProgressBtn: () => $("cancelProgressBtn"),
  closeProgressPopup: () => $("closeProgressPopup"),

  // Task Modal
  taskModal: () => $("taskModal"),
  taskForm: () => $("taskForm"),
  taskProjectId: () => $("taskProjectId"),
  taskTitle: () => $("taskTitle"),
  taskDescription: () => $("taskDescription"),
  taskAssignee: () => $("taskAssignee"),
  taskPriority: () => $("taskPriority"),
  taskDueDate: () => $("taskDueDate"),
  cancelTaskBtn: () => $("cancelTaskBtn"),
  closeTaskModal: () => $("closeTaskModal"),

  // Toast
  toastContainer: () => $("toastContainer"),

  // Tabs
  tabBtns: () => document.querySelectorAll(".drawer-tabs .tab-btn"),
  tabPanels: {
    overview: () => $("tab-overview"),
    material: () => $("tab-material"),
    labor: () => $("tab-labor"),
    timeline: () => $("tab-timeline"),
    tasks: () => $("tab-tasks"),
  },
};

// ✅ Helper functions
export function toggleElement(id, show) {
  const el = $safe(id);
  if (!el) return;
  el.style.display = show ? "" : "none";
}

export function showElement(id) {
  toggleElement(id, true);
}
export function hideElement(id) {
  toggleElement(id, false);
}

export function getValue(id, fallback = "") {
  const el = $safe(id);
  if (!el) return fallback;
  return el.value || fallback;
}

export function setValue(id, value) {
  const el = $safe(id);
  if (!el) return;
  el.value = value;
}

export function getText(id, fallback = "") {
  const el = $safe(id);
  if (!el) return fallback;
  return el.textContent || fallback;
}

export function setText(id, text) {
  const el = $safe(id);
  if (!el) return;
  el.textContent = text;
}

export function addClass(id, className) {
  const el = $safe(id);
  if (!el) return;
  el.classList.add(className);
}

export function removeClass(id, className) {
  const el = $safe(id);
  if (!el) return;
  el.classList.remove(className);
}

export function toggleClass(id, className) {
  const el = $safe(id);
  if (!el) return;
  el.classList.toggle(className);
}

export function hasClass(id, className) {
  const el = $safe(id);
  if (!el) return false;
  return el.classList.contains(className);
}
