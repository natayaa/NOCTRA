// ============================================================
// restored-bikes/dom.js - DOM References
// ============================================================

export const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

export const $$ = (selector) => document.querySelectorAll(selector);

export const DOM = {
  // Stats
  totalRestored: () => $("totalRestored"),
  completedRestored: () => $("completedRestored"),
  inProgressRestored: () => $("inProgressRestored"),
  featuredRestored: () => $("featuredRestored"),

  // Toolbar
  searchRestored: () => $("searchRestored"),
  statusFilter: () => $("statusFilter"),
  brandFilter: () => $("brandFilter"),
  addRestoredBtn: () => $("addRestoredBtn"),

  // Grid
  restoredGrid: () => $("restoredGrid"),

  // Pagination
  prevPageBtn: () => $("prevPageBtn"),
  nextPageBtn: () => $("nextPageBtn"),
  pageInfo: () => $("pageInfo"),

  // Modal
  restoredModal: () => $("restoredModal"),
  modalTitle: () => $("modalTitle"),
  modalSubtitle: () => $("modalSubtitle"),
  restoredForm: () => $("restoredForm"),
  editId: () => $("editId"),
  bikeBrand: () => $("bikeBrand"),
  bikeModel: () => $("bikeModel"),
  bikeYear: () => $("bikeYear"),
  licensePlate: () => $("licensePlate"),
  customerName: () => $("customerName"),
  purchasePrice: () => $("purchasePrice"),
  purchaseSource: () => $("purchaseSource"),
  initialCondition: () => $("initialCondition"),
  restorationCost: () => $("restorationCost"),
  restorationDuration: () => $("restorationDuration"),
  technicianName: () => $("technicianName"),
  restorationStatus: () => $("restorationStatus"),
  restorationNotes: () => $("restorationNotes"),
  submitBtn: () => $("submitBtn"),
  cancelModalBtn: () => $("cancelModalBtn"),
  closeModal: () => $("closeModal"),

  // Drawer
  drawer: () => $("restoredDrawer"),
  drawerTitle: () => $("drawerTitle"),
  drawerSubtitle: () => $("drawerSubtitle"),
  closeDrawer: () => $("closeDrawer"),
  drawerBackdrop: () => document.getElementById("drawerBackdrop"),

  // Drawer - Detail
  detailBrand: () => $("detailBrand"),
  detailModel: () => $("detailModel"),
  detailYear: () => $("detailYear"),
  detailPlate: () => $("detailPlate"),
  detailCustomer: () => $("detailCustomer"),
  detailPurchasePrice: () => $("detailPurchasePrice"),
  detailPurchaseSource: () => $("detailPurchaseSource"),
  detailInitialCondition: () => $("detailInitialCondition"),
  detailRestorationCost: () => $("detailRestorationCost"),
  detailRestorationDuration: () => $("detailRestorationDuration"),
  detailTechnician: () => $("detailTechnician"),
  detailStatus: () => $("detailStatus"),
  detailNotes: () => $("detailNotes"),

  // Drawer - Actions
  editRestoredBtn: () => $("editRestoredBtn"),
  deleteRestoredBtn: () => $("deleteRestoredBtn"),

  // Drawer - Gallery
  galleryGrid: () => $("galleryGrid"),
  galleryPhotos: () => $("galleryPhotos"),
  galleryUploadZone: () => $("galleryUploadZone"),

  // Drawer - Documents
  documentList: () => $("documentList"),
  documentFiles: () => $("documentFiles"),
  documentUploadZone: () => $("documentUploadZone"),

  // Tabs
  tabBtns: () => document.querySelectorAll(".drawer-tabs .tab-btn"),
  tabPanels: () => document.querySelectorAll(".drawer-content .tab-panel"),

  // Toast
  toastContainer: () => $("toastContainer"),
};
