// ============================================================
// projects/dom.js - DOM References
// ============================================================

export const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

export const $$ = (selector) => document.querySelectorAll(selector);

// ✅ CREATE drawerBackdrop dan EXPORT
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
  drawerBackdrop: () => $("drawerBackdrop"), // ✅ Tambahkan getter untuk drawerBackdrop
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
