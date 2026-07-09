// ============================================================
// inquiries.js - NOCTRA Inquiries Page
// Version: 3.0 - FULLY FIXED
// ============================================================

// ============================================================
// 1. CONFIGURATION
// ============================================================
const CONFIG = {
  API_BASE_URL: "/api/api",
  INQUIRIES_PER_PAGE: 10,
  TOAST_DURATION: 4000,
  MAX_ACTIVITIES: 50,
};

// ============================================================
// 2. STATE
// ============================================================
const state = {
  inquiries: [],
  currentPage: 1,
  totalPages: 1,
  totalItems: 0,
  currentInquiryId: null,
  _currentInquiry: null,
  _convertInquiryId: null,
  _quoteInquiryId: null,
  _rejectInquiryId: null,
  inventoryItems: [],
  activities: [],
  notes: [],
  filters: {
    search: "",
    status: "",
  },
  carousels: {
    before: { index: 0, images: [] },
    after: { index: 0, images: [] },
  },
  lightbox: {
    images: [],
    currentIndex: 0,
    isOpen: false,
  },
  isLoading: false,
};

// ============================================================
// 3. DOM UTILITIES
// ============================================================
const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

const $$ = (selector) => document.querySelectorAll(selector);

// ============================================================
// 4. DOM REFERENCES
// ============================================================
const DOM = {
  // Dashboard
  totalCount: () => $("totalCount"),
  newCount: () => $("newCount"),
  quotedCount: () => $("quotedCount"),
  convertedCount: () => $("convertedCount"),

  // Toolbar
  searchInquiry: () => $("searchInquiry"),
  statusFilter: () => $("statusFilter"),
  exportInquiriesBtn: () => $("exportInquiriesBtn"),

  // Table
  inquiriesBody: () => $("inquiriesBody"),
  prevPage: () => $("prevPage"),
  nextPage: () => $("nextPage"),
  pageInfo: () => $("pageInfo"),

  // Drawer
  drawer: () => $("inquiryDrawer"),
  drawerCustomerName: () => $("drawerCustomerName"),
  drawerStatusBadge: () => $("drawerStatusBadge"),
  closeDrawer: () => $("closeDrawer"),
  drawerBackdrop: () => $("drawerBackdrop"),

  // Drawer - Customer
  drawerName: () => $("drawerName"),
  drawerPhone: () => $("drawerPhone"),
  drawerEmail: () => $("drawerEmail"),
  drawerProvince: () => $("drawerProvince"),
  drawerCity: () => $("drawerCity"),

  // Drawer - Vehicle & Project
  drawerBrand: () => $("drawerBrand"),
  drawerModel: () => $("drawerModel"),
  drawerYear: () => $("drawerYear"),
  drawerPlate: () => $("drawerPlate"),
  drawerPrevRepaint: () => $("drawerPrevRepaint"),
  drawerBikeModified: () => $("drawerBikeModified"),
  drawerCondition: () => $("drawerCondition"),
  drawerType: () => $("drawerType"),
  drawerServices: () => $("drawerServices"),
  drawerFinish: () => $("drawerFinish"),
  drawerColor: () => $("drawerColor"),
  drawerBudget: () => $("drawerBudget"),
  drawerDeadline: () => $("drawerDeadline"),
  drawerPriority: () => $("drawerPriority"),
  drawerDescription: () => $("drawerDescription"),
  drawerReference: () => $("drawerReference"),

  // Drawer - Financial
  drawerEstCost: () => $("drawerEstCost"),
  drawerActualCost: () => $("drawerActualCost"),
  drawerEstRevenue: () => $("drawerEstRevenue"),
  drawerActualRevenue: () => $("drawerActualRevenue"),
  drawerDeposit: () => $("drawerDeposit"),
  drawerDepositStatus: () => $("drawerDepositStatus"),
  drawerProfit: () => $("drawerProfit"),
  drawerMargin: () => $("drawerMargin"),
  drawerMaterialCost: () => $("drawerMaterialCost"),
  drawerLaborCost: () => $("drawerLaborCost"),
  drawerOtherExpenses: () => $("drawerOtherExpenses"),
  drawerTotalCost: () => $("drawerTotalCost"),
  budgetPercentage: () => $("budgetPercentage"),
  budgetProgressFill: () => $("budgetProgressFill"),

  // Drawer - Labor
  drawerLaborItems: () => $("drawerLaborItems"),

  // Drawer - Material
  drawerMaterialUsages: () => $("drawerMaterialUsages"),

  // Drawer - Payment
  drawerTotalDeposit: () => $("drawerTotalDeposit"),
  drawerTotalPaid: () => $("drawerTotalPaid"),
  drawerTotalPending: () => $("drawerTotalPending"),
  drawerRemaining: () => $("drawerRemaining"),
  drawerPaymentHistory: () => $("drawerPaymentHistory"),
  addDepositBtn: () => $("addDepositBtn"),
  addPaymentBtn: () => $("addPaymentBtn"),
  viewInvoicesBtn: () => $("viewInvoicesBtn"),

  // Drawer - Timeline
  drawerTimeline: () => $("drawerTimeline"),

  // Drawer - Notes
  drawerNotes: () => $("drawerNotes"),
  noteCounter: () => $("noteCounter"),

  // Drawer - Before/After
  beforeTrack: () => $("beforeTrack"),
  afterTrack: () => $("afterTrack"),

  // Drawer - Actions
  drawerApproveBtn: () => $("drawerApproveBtn"),
  drawerQuoteBtn: () => $("drawerQuoteBtn"),
  drawerRejectBtn: () => $("drawerRejectBtn"),
  drawerWhatsappBtn: () => $("drawerWhatsappBtn"),
  drawerConvertBtn: () => $("drawerConvertBtn"),
  drawerViewProjectBtn: () => $("drawerViewProjectBtn"),

  // Convert Modal
  convertModal: () => $("convertModal"),
  convertForm: () => $("convertForm"),
  convertStartDate: () => $("convertStartDate"),
  convertTargetDelivery: () => $("convertTargetDelivery"),
  closeConvertModal: () => $("closeConvertModal"),
  cancelConvertBtn: () => $("cancelConvertBtn"),

  // Quote Modal
  quoteModal: () => $("quoteModal"),
  quoteForm: () => $("quoteForm"),
  quoteCost: () => $("quoteCost"),
  quoteNotes: () => $("quoteNotes"),
  closeQuoteModal: () => $("closeQuoteModal"),
  cancelQuoteBtn: () => $("cancelQuoteBtn"),

  // Reject Modal
  rejectModal: () => $("rejectModal"),
  rejectForm: () => $("rejectForm"),
  rejectReason: () => $("rejectReason"),
  closeRejectModal: () => $("closeRejectModal"),
  cancelRejectBtn: () => $("cancelRejectBtn"),

  // Lightbox
  lightboxOverlay: () => $("lightboxOverlay"),
  lightboxImage: () => $("lightboxImage"),
  lightboxClose: () => $("lightboxClose"),
  lightboxPrev: () => $("lightboxPrev"),
  lightboxNext: () => $("lightboxNext"),

  // Toast
  toastContainer: () => $("toastContainer"),
};

// ============================================================
// 5. CREATE DRAWER BACKDROP
// ============================================================
const drawerBackdrop = document.createElement("div");
drawerBackdrop.className = "drawer-backdrop";
drawerBackdrop.id = "drawerBackdrop";
document.body.appendChild(drawerBackdrop);

// ============================================================
// 6. TOAST SYSTEM
// ============================================================
function showToast(message, type = "info", duration = CONFIG.TOAST_DURATION) {
  const container = DOM.toastContainer();
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
        <span>${message}</span>
        <button class="toast-close">&times;</button>
    `;

  container.appendChild(toast);

  toast.querySelector(".toast-close").addEventListener("click", () => {
    toast.remove();
  });

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-10px)";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ============================================================
// 7. FORMATTERS
// ============================================================
const Formatter = {
  currency: (amount) => {
    if (!amount && amount !== 0) return "-";
    return new Intl.NumberFormat("id-ID", {
      style: "currency",
      currency: "IDR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(Number(amount));
  },

  date: (dateString) => {
    if (!dateString) return "-";
    try {
      return new Date(dateString).toLocaleDateString("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return "-";
    }
  },

  dateTime: (dateString) => {
    if (!dateString) return "-";
    try {
      return new Date(dateString).toLocaleString("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "-";
    }
  },

  statusBadge: (status) => {
    const map = {
      new: "new",
      under_review: "under_review",
      contacted: "contacted",
      quoted: "quoted",
      approved: "approved",
      converted: "converted",
      rejected: "rejected",
      closed: "closed",
      completed: "completed",
      has_project: "has_project",
      no_project: "no_project",
      project_completed: "project_completed",
    };
    return map[status] || "new";
  },

  statusLabel: (status) => {
    const map = {
      new: "New",
      under_review: "Under Review",
      contacted: "Contacted",
      quoted: "Quoted",
      approved: "Approved",
      converted: "Converted",
      rejected: "Rejected",
      closed: "Closed",
      completed: "Completed",
      has_project: "Has Project",
      no_project: "No Project",
      project_completed: "Project Completed",
    };
    return map[status] || status;
  },

  projectStatusBadge: (status) => {
    const map = {
      preparation: "preparation",
      painting: "painting",
      assembly: "assembly",
      completed: "completed",
      active: "active",
      in_progress: "in_progress",
      draft: "draft",
    };
    return map[status] || "no-project";
  },
};

// ============================================================
// 8. HTML ESCAPE
// ============================================================
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ============================================================
// 9. API HELPERS
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
      throw new Error(data.message || `HTTP ${response.status}`);
    }

    return data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

// ============================================================
// 10. API SERVICES
// ============================================================
const InquiryAPI = {
  // Fetch inquiries with pagination and filters
  fetchInquiries: async (page = 1, filters = {}) => {
    state.isLoading = true;
    showLoadingState();

    const params = new URLSearchParams({
      page: page,
      limit: CONFIG.INQUIRIES_PER_PAGE,
    });

    if (filters.search) params.set("search", filters.search);
    if (filters.status) params.set("status", filters.status);

    try {
      const response = await apiFetch(`/inquiries/?${params.toString()}`);
      return response.data || response;
    } catch (error) {
      showToast("Failed to load inquiries: " + error.message, "error");
      return null;
    } finally {
      state.isLoading = false;
    }
  },

  // Fetch inquiry statistics
  fetchStatistics: async () => {
    try {
      const response = await apiFetch("/inquiries/statistics");
      return response.data || response;
    } catch (error) {
      console.error("Failed to load statistics:", error);
      return null;
    }
  },

  // Fetch inventory items for material lookup
  fetchInventoryItems: async () => {
    try {
      // Try with pagination parameters that are accepted
      const response = await apiFetch("/inventory/items?page=1&limit=100");
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load inventory items:", error);

      // Try without limit parameter
      try {
        const response2 = await apiFetch("/inventory/items?page=1");
        return response2.data || response2 || [];
      } catch (e2) {
        console.error("Alternative inventory fetch failed:", e2);

        // Try with different endpoint
        try {
          const response3 = await apiFetch("/inventory/items/all");
          return response3.data || response3 || [];
        } catch (e3) {
          console.error("All inventory fetch attempts failed");
          return [];
        }
      }
    }
  },

  // Fetch inquiry detail
  fetchDetail: async (inquiryId) => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}`);
      return response.data || response;
    } catch (error) {
      showToast("Failed to load inquiry details: " + error.message, "error");
      return null;
    }
  },

  // Update inquiry status
  updateStatus: async (inquiryId, status, note = "") => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status, note }),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to update status: " + error.message, "error");
      return null;
    }
  },

  // Send quotation
  sendQuotation: async (inquiryId, estimatedCost, notes = "") => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}/quote`, {
        method: "POST",
        body: JSON.stringify({ estimated_cost: estimatedCost, notes }),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to send quotation: " + error.message, "error");
      return null;
    }
  },

  // Reject inquiry
  reject: async (inquiryId, reason = "") => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to reject inquiry: " + error.message, "error");
      return null;
    }
  },

  // Convert to project
  convertToProject: async (
    inquiryId,
    startDate = null,
    targetDelivery = null,
  ) => {
    try {
      const response = await apiFetch(`/projects/from-inquiry/${inquiryId}`, {
        method: "POST",
        body: JSON.stringify({
          start_date: startDate,
          target_delivery: targetDelivery,
        }),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to convert to project: " + error.message, "error");
      return null;
    }
  },

  // Fetch activities
  fetchActivities: async (inquiryId, limit = CONFIG.MAX_ACTIVITIES) => {
    try {
      const response = await apiFetch(
        `/inquiries/${inquiryId}/activities?limit=${limit}`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load activities:", error);
      return [];
    }
  },

  // Fetch notes
  fetchNotes: async (inquiryId, includePrivate = false) => {
    try {
      const response = await apiFetch(
        `/inquiries/${inquiryId}/notes?include_private=${includePrivate}`,
      );
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load notes:", error);
      return [];
    }
  },

  // Add note
  addNote: async (
    inquiryId,
    note,
    noteType = "internal",
    isPrivate = false,
  ) => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}/notes`, {
        method: "POST",
        body: JSON.stringify({
          note,
          note_type: noteType,
          is_private: isPrivate,
        }),
      });
      return response.data || response;
    } catch (error) {
      showToast("Failed to add note: " + error.message, "error");
      return null;
    }
  },

  // Fetch photos
  fetchPhotos: async (inquiryId) => {
    try {
      const response = await apiFetch(`/inquiries/${inquiryId}/photos`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load photos:", error);
      return [];
    }
  },

  // Fetch payments
  // ============================================================
  // REPLACE fetchPayments in InquiryAPI (line ~377-414)
  // ============================================================

  fetchPayments: async (inquiryId) => {
    try {
      console.log("📡 Fetching payments for inquiry:", inquiryId);
      const response = await apiFetch(`/payments/inquiry/${inquiryId}`);
      console.log("📦 Payments response:", response);

      // Handle different response structures
      let payments = [];

      if (response) {
        // Check if response.data exists
        if (response.data) {
          if (Array.isArray(response.data)) {
            payments = response.data;
          } else if (
            response.data.items &&
            Array.isArray(response.data.items)
          ) {
            payments = response.data.items;
          } else if (
            response.data.payments &&
            Array.isArray(response.data.payments)
          ) {
            payments = response.data.payments;
          } else {
            // Try to see if data is an object with payment properties
            payments = [response.data];
          }
        } else if (Array.isArray(response)) {
          payments = response;
        } else if (response.items && Array.isArray(response.items)) {
          payments = response.items;
        } else if (response.payments && Array.isArray(response.payments)) {
          payments = response.payments;
        } else if (typeof response === "object" && response !== null) {
          // Maybe it's a single payment object
          payments = [response];
        }
      }

      // Ensure each payment has required fields
      payments = payments
        .filter((p) => p !== null && typeof p === "object")
        .map((p) => ({
          ...p,
          id:
            p.id ||
            p.payment_id ||
            `pay_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
          amount: Number(p.amount) || Number(p.total) || Number(p.nominal) || 0,
          status: p.status || p.payment_status || "pending",
          type: p.type || p.payment_type || "payment",
          method: p.method || p.payment_method || p.paymentMethod || "",
          reference_number:
            p.reference_number || p.reference || p.invoice_number || "",
          created_at:
            p.created_at ||
            p.paid_at ||
            p.payment_date ||
            p.date ||
            new Date().toISOString(),
        }));

      console.log("📊 Processed payments:", payments);
      console.log("📊 Payments count:", payments.length);
      return payments;
    } catch (error) {
      console.error("Failed to load payments:", error);

      // Try alternative endpoint
      try {
        console.log("🔄 Trying alternative payments endpoint...");
        const response2 = await apiFetch(`/payments/inquiry/${inquiryId}/list`);
        console.log("📦 Alternative payments response:", response2);

        let payments = [];
        if (response2 && response2.data) {
          payments = Array.isArray(response2.data) ? response2.data : [];
        } else if (response2 && Array.isArray(response2)) {
          payments = response2;
        }

        return payments;
      } catch (e2) {
        console.error("Alternative payments load failed:", e2);

        // Try third endpoint
        try {
          console.log("🔄 Trying third payments endpoint...");
          const response3 = await apiFetch(`/inquiries/${inquiryId}/payments`);
          console.log("📦 Third payments response:", response3);

          let payments = [];
          if (response3 && response3.data) {
            payments = Array.isArray(response3.data) ? response3.data : [];
          } else if (response3 && Array.isArray(response3)) {
            payments = response3;
          }

          return payments;
        } catch (e3) {
          console.error("All payment endpoints failed");
          return [];
        }
      }
    }
  },

  // Fetch project labor
  fetchProjectLabor: async (projectId) => {
    try {
      const response = await apiFetch(`/projects/${projectId}/labor`);
      return response.data || response || [];
    } catch (error) {
      console.error("Failed to load labor:", error);
      return [];
    }
  },

  // Fetch project material usage - FIXED with item name enrichment
  fetchProjectMaterialUsage: async (projectId) => {
    try {
      console.log("📡 Fetching material usage for project:", projectId);
      const response = await apiFetch(`/inventory/usage/project/${projectId}`);
      console.log("📦 Material usage response:", response);

      let materialData = response.data || response || [];

      if (!Array.isArray(materialData)) {
        materialData = [];
      }

      // Enrich material data with item names from state inventory
      materialData = materialData.map((item) => {
        const enriched = { ...item };

        if (enriched.item_id) {
          // Try to find item in state inventory
          const foundItem = state.inventoryItems?.find(
            (i) => i.id === enriched.item_id,
          );
          if (foundItem) {
            enriched.item_name = foundItem.name || enriched.item_id;
            enriched.unit = foundItem.unit || enriched.unit || "";
            enriched.cost_price =
              foundItem.cost_price || enriched.cost_price || 0;
          } else {
            // Use item_id as fallback name
            enriched.item_name = enriched.item_name || enriched.item_id;
            // Try to get from helper
            if (!enriched.unit) {
              const unit = getItemUnit(enriched.item_id);
              if (unit) enriched.unit = unit;
            }
            if (!enriched.cost_price || enriched.cost_price === 0) {
              const cost = getItemCost(enriched.item_id);
              if (cost) enriched.cost_price = cost;
            }
          }
        }
        return enriched;
      });

      // Calculate total material cost for debugging
      const totalMaterialCost = materialData.reduce((sum, item) => {
        const qty = Number(item.quantity) || 0;
        const price = Number(item.cost_price) || Number(item.unit_price) || 0;
        return sum + qty * price;
      }, 0);
      console.log("💰 Total material cost:", totalMaterialCost);
      console.log("📦 Enriched material data:", materialData);

      return materialData;
    } catch (error) {
      console.error("Failed to load material usage:", error);
      return [];
    }
  },
};

// ============================================================
// 11. FINANCIAL CALCULATOR
// ============================================================
function calculateFinancialFromData(inquiry, labor, materials, payments) {
  // Calculate total labor cost
  const totalLaborCost = labor.reduce((sum, item) => {
    return sum + (Number(item.hours) || 0) * (Number(item.rate_per_hour) || 0);
  }, 0);

  // Calculate total material cost
  const totalMaterialCost = materials.reduce((sum, item) => {
    const qty = Number(item.quantity) || 0;
    const price = Number(item.cost_price) || Number(item.unit_price) || 0;
    return sum + qty * price;
  }, 0);

  // Calculate total payments
  const totalDeposit = payments
    .filter((p) => p.type === "deposit" || p.payment_type === "deposit")
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalPaid = payments
    .filter(
      (p) =>
        p.status === "completed" ||
        p.status === "confirmed" ||
        p.status === "paid",
    )
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  // Get project financials from inquiry if available
  const project = inquiry?.project || {};
  const estimatedCost = Number(project.estimated_cost) || 0;
  const estimatedRevenue = Number(project.estimated_revenue) || 0;
  const depositAmount = Number(project.deposit_amount) || totalDeposit || 0;
  const depositPaid = project.deposit_paid || depositAmount > 0;

  return {
    estimated_cost: estimatedCost,
    actual_cost: totalLaborCost + totalMaterialCost,
    estimated_revenue: estimatedRevenue,
    actual_revenue: totalPaid || 0,
    deposit_amount: depositAmount,
    deposit_paid: depositPaid,
    material_cost: totalMaterialCost,
    labor_cost: totalLaborCost,
    other_expenses: 0,
    total_paid: totalPaid,
    total_deposit: totalDeposit,
    total_pending: payments
      .filter(
        (p) => p.status === "pending" || p.status === "awaiting_confirmation",
      )
      .reduce((sum, p) => sum + (Number(p.amount) || 0), 0),
  };
}

// ============================================================
// 12. ITEM NAME HELPERS
// ============================================================
function getItemName(itemId) {
  if (!itemId) return "Unknown";

  if (state.inventoryItems && state.inventoryItems.length > 0) {
    const found = state.inventoryItems.find((i) => i.id === itemId);
    if (found) return found.name;
  }
  return `Item ${itemId.substring(0, 8)}`;
}

function getItemUnit(itemId) {
  if (!itemId) return "";

  if (state.inventoryItems && state.inventoryItems.length > 0) {
    const found = state.inventoryItems.find((i) => i.id === itemId);
    if (found) return found.unit || "";
  }
  return "";
}

function getItemCost(itemId) {
  if (!itemId) return 0;

  if (state.inventoryItems && state.inventoryItems.length > 0) {
    const found = state.inventoryItems.find((i) => i.id === itemId);
    if (found) return found.cost_price || 0;
  }
  return 0;
}

// ============================================================
// 13. RENDER FUNCTIONS
// ============================================================

function showLoadingState() {
  const body = DOM.inquiriesBody();
  if (!body) return;

  body.innerHTML = `
        <tr>
            <td colspan="7" style="text-align:center; padding:2rem;">
                <i class="ph ph-spinner" style="font-size:1.5rem; animation: spin 1s linear infinite;"></i>
                <p style="color:var(--text-muted);">Loading inquiries...</p>
            </td>
        </tr>
    `;
}

function renderInquiries(inquiries) {
  const body = DOM.inquiriesBody();
  if (!body) return;

  if (!inquiries || inquiries.length === 0) {
    body.innerHTML = `
            <tr>
                <td colspan="7" style="text-align:center; padding:2rem; color: var(--text-muted);">
                    <i class="ph ph-file-text" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                    No inquiries found
                </td>
            </tr>
        `;
    return;
  }

  body.innerHTML = inquiries
    .map(
      (inquiry) => `
        <tr class="fade-in">
            <td>
                <strong>${escapeHtml(inquiry.customer_name)}</strong><br>
                <span style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(inquiry.customer_phone_number || "")}</span>
            </td>
            <td>
                <span style="font-weight:500;">${escapeHtml(inquiry.vehicle_brand)}</span>
                <span style="color:var(--text-muted);">${escapeHtml(inquiry.vehicle_model)}</span>
            </td>
            <td><span style="color:var(--text-secondary);">${escapeHtml(inquiry.project_type)}</span></td>
            <td>
                <span class="status-badge ${Formatter.statusBadge(inquiry.status)}">
                    ${Formatter.statusLabel(inquiry.status)}
                </span>
            </td>
            <td>
                ${
                  inquiry.project
                    ? `
                    <span class="project-status-badge ${Formatter.projectStatusBadge(inquiry.project.status)}">
                        ${inquiry.project.status || "Active"}
                    </span>
                `
                    : `
                    <span class="project-status-badge no-project">No Project</span>
                `
                }
            </td>
            <td style="font-size:0.8rem; color:var(--text-muted);">
                ${Formatter.date(inquiry.created_at)}
            </td>
            <td style="text-align:center;">
                <div class="actions">
                    <button class="action-btn view" onclick="openInquiryDrawer('${inquiry.id}')" title="View Details">
                        <i class="ph ph-eye"></i>
                    </button>
                    ${
                      ["new", "under_review"].includes(inquiry.status)
                        ? `
                        <button class="action-btn quote" onclick="openQuoteModal('${inquiry.id}')" title="Send Quote">
                            <i class="ph ph-file-text"></i>
                        </button>
                        <button class="action-btn approve" onclick="handleApprove('${inquiry.id}')" title="Approve">
                            <i class="ph ph-check-circle"></i>
                        </button>
                        <button class="action-btn reject" onclick="openRejectModal('${inquiry.id}')" title="Reject">
                            <i class="ph ph-x-circle"></i>
                        </button>
                    `
                        : ""
                    }
                    ${
                      ["approved", "quoted"].includes(inquiry.status)
                        ? `
                        <button class="action-btn convert" onclick="openConvertModal('${inquiry.id}')" title="Convert to Project">
                            <i class="ph ph-arrow-right"></i>
                        </button>
                    `
                        : ""
                    }
                    ${
                      inquiry.project
                        ? `
                        <button class="action-btn view" onclick="window.location.href='/projects/${inquiry.project.id}'" title="View Project">
                            <i class="ph ph-briefcase"></i>
                        </button>
                    `
                        : ""
                    }
                </div>
            </td>
        </tr>
    `,
    )
    .join("");
}

function updatePagination(page, totalPages, totalItems) {
  const info = DOM.pageInfo();
  const prev = DOM.prevPage();
  const next = DOM.nextPage();

  if (info) {
    info.textContent = `Page ${page} of ${totalPages || 1} (${totalItems} items)`;
  }
  if (prev) prev.disabled = page <= 1;
  if (next) next.disabled = page >= totalPages;
}

function updateDashboard(stats) {
  if (!stats) return;

  const totalCount = DOM.totalCount();
  const newCount = DOM.newCount();
  const quotedCount = DOM.quotedCount();
  const convertedCount = DOM.convertedCount();

  if (totalCount)
    totalCount.textContent = stats.total || stats.total_count || 0;
  if (newCount)
    newCount.textContent = stats.by_status?.new || stats.new_count || 0;
  if (quotedCount)
    quotedCount.textContent =
      stats.by_status?.quoted || stats.quoted_count || 0;
  if (convertedCount)
    convertedCount.textContent =
      stats.by_status?.converted || stats.converted_count || 0;
}

// ============================================================
// 14. DRAWER RENDER FUNCTIONS
// ============================================================

function renderDrawerCustomer(inquiry) {
  if (!inquiry) return;

  const name = DOM.drawerCustomerName();
  const badge = DOM.drawerStatusBadge();

  if (name) name.textContent = inquiry.customer_name || "Unknown";
  if (badge) {
    badge.textContent = Formatter.statusLabel(inquiry.status);
    badge.className = `status-badge ${Formatter.statusBadge(inquiry.status)}`;
  }

  const fields = {
    drawerName: inquiry.customer_name,
    drawerPhone: inquiry.customer_phone_number,
    drawerEmail: inquiry.customer_email,
    drawerProvince: inquiry.province,
    drawerCity: inquiry.city,
  };

  Object.keys(fields).forEach((key) => {
    const el = DOM[key]();
    if (el) el.textContent = fields[key] || "-";
  });
}

function renderDrawerVehicle(inquiry) {
  if (!inquiry) return;

  const fields = {
    drawerBrand: inquiry.vehicle_brand,
    drawerModel: inquiry.vehicle_model,
    drawerYear: inquiry.vehicle_year,
    drawerPlate: inquiry.vehicle_license_plate,
    drawerPrevRepaint: inquiry.previous_repaint,
    drawerBikeModified: inquiry.bike_modified,
    drawerCondition: inquiry.vehicle_condition,
    drawerType: inquiry.project_type,
    drawerServices: inquiry.services,
    drawerFinish: inquiry.desired_finish,
    drawerColor: inquiry.desired_color,
    drawerBudget: inquiry.estimated_budget
      ? Formatter.currency(inquiry.estimated_budget)
      : "-",
    drawerDeadline: inquiry.deadline,
    drawerPriority: inquiry.priority,
  };

  Object.keys(fields).forEach((key) => {
    const el = DOM[key]();
    if (el) el.textContent = fields[key] || "-";
  });

  const desc = DOM.drawerDescription();
  if (desc)
    desc.textContent =
      inquiry.project_description || "No description provided.";

  const ref = DOM.drawerReference();
  if (ref) {
    if (inquiry.reference_link) {
      ref.href = inquiry.reference_link;
      ref.style.display = "inline";
      ref.textContent = "🔗 View Reference Link";
    } else {
      ref.style.display = "none";
    }
  }
}

// ============================================================
// 15. FINANCIAL RENDER - FIXED
// ============================================================

function renderDrawerFinancial(financial) {
  const estCostEl = DOM.drawerEstCost();
  const actualCostEl = DOM.drawerActualCost();
  const estRevenueEl = DOM.drawerEstRevenue();
  const actualRevenueEl = DOM.drawerActualRevenue();
  const depositEl = DOM.drawerDeposit();
  const depositStatusEl = DOM.drawerDepositStatus();
  const profitEl = DOM.drawerProfit();
  const marginEl = DOM.drawerMargin();
  const materialCostEl = DOM.drawerMaterialCost();
  const laborCostEl = DOM.drawerLaborCost();
  const otherExpensesEl = DOM.drawerOtherExpenses();
  const totalCostEl = DOM.drawerTotalCost();
  const budgetPercentEl = DOM.budgetPercentage();
  const budgetFillEl = DOM.budgetProgressFill();

  if (!financial) {
    const emptyFields = [
      estCostEl,
      actualCostEl,
      estRevenueEl,
      actualRevenueEl,
      depositEl,
      depositStatusEl,
      profitEl,
      marginEl,
      materialCostEl,
      laborCostEl,
      otherExpensesEl,
      totalCostEl,
    ];
    emptyFields.forEach((el) => {
      if (el) el.textContent = "-";
    });
    if (budgetPercentEl) budgetPercentEl.textContent = "0%";
    if (budgetFillEl) {
      budgetFillEl.style.width = "0%";
      budgetFillEl.className = "budget-progress-fill";
    }
    return;
  }

  // Extract values with fallbacks
  const estCost = Number(financial.estimated_cost) || 0;
  const actualCost = Number(financial.actual_cost) || 0;
  const estRevenue = Number(financial.estimated_revenue) || 0;
  const actualRevenue = Number(financial.actual_revenue) || 0;
  const deposit = Number(financial.deposit_amount) || 0;
  const depositPaid = financial.deposit_paid || false;

  // Get material and labor costs
  const materialCost = Number(financial.material_cost) || 0;
  const laborCost = Number(financial.labor_cost) || 0;
  const otherExpenses = Number(financial.other_expenses) || 0;
  const totalCost = materialCost + laborCost + otherExpenses;

  // Set main financial values
  if (estCostEl) estCostEl.textContent = Formatter.currency(estCost);
  if (actualCostEl) actualCostEl.textContent = Formatter.currency(actualCost);
  if (estRevenueEl) estRevenueEl.textContent = Formatter.currency(estRevenue);
  if (actualRevenueEl)
    actualRevenueEl.textContent = Formatter.currency(actualRevenue);
  if (depositEl) depositEl.textContent = Formatter.currency(deposit);
  if (depositStatusEl) {
    depositStatusEl.textContent = depositPaid ? "✅ Paid" : "❌ Not Paid";
    depositStatusEl.style.color = depositPaid
      ? "var(--success, #10b981)"
      : "var(--danger, #ef4444)";
  }

  // Calculate profit and margin
  const profit = actualRevenue - actualCost;
  const margin = actualRevenue > 0 ? (profit / actualRevenue) * 100 : 0;

  if (profitEl) {
    profitEl.textContent = Formatter.currency(profit);
    profitEl.className = `value ${profit >= 0 ? "positive" : "negative"}`;
  }
  if (marginEl) {
    marginEl.textContent = margin.toFixed(1) + "%";
    marginEl.className = `value ${margin >= 0 ? "positive" : "negative"}`;
  }

  // Set cost breakdown
  if (materialCostEl)
    materialCostEl.textContent = Formatter.currency(materialCost);
  if (laborCostEl) laborCostEl.textContent = Formatter.currency(laborCost);
  if (otherExpensesEl)
    otherExpensesEl.textContent = Formatter.currency(otherExpenses);
  if (totalCostEl)
    totalCostEl.textContent = Formatter.currency(totalCost || actualCost);

  // Budget progress
  const budgetPercent =
    estCost > 0 ? Math.min((actualCost / estCost) * 100, 100) : 0;
  if (budgetPercentEl)
    budgetPercentEl.textContent = budgetPercent.toFixed(0) + "%";
  if (budgetFillEl) {
    budgetFillEl.style.width = `${budgetPercent}%`;
    budgetFillEl.className = "budget-progress-fill";
    if (budgetPercent > 90) budgetFillEl.classList.add("danger");
    else if (budgetPercent > 75) budgetFillEl.classList.add("warning");
  }
}

// ============================================================
// 16. LABOR RENDER - FIXED
// ============================================================

function renderDrawerLabor(laborItems) {
  const container = DOM.drawerLaborItems();
  if (!container) return;

  if (!laborItems || laborItems.length === 0) {
    container.innerHTML = `
            <div style="text-align:center;padding:0.5rem 0;color:var(--text-muted);">
                <i class="ph ph-user" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
                No labor items recorded
            </div>
        `;
    return;
  }

  let totalLaborCost = 0;
  const laborList = laborItems.map((item) => {
    const hours = Number(item.hours) || 0;
    const rate = Number(item.rate_per_hour) || 0;
    const cost = hours * rate;
    totalLaborCost += cost;
    return { ...item, hours, rate, cost };
  });

  container.innerHTML = `
        ${laborList
          .map(
            (item) => `
            <div class="labor-list-item" style="display:flex;justify-content:space-between;align-items:center;
                        padding:0.5rem 0.75rem;background:var(--bg-input);border-radius:var(--radius-sm);
                        margin-bottom:0.25rem;font-size:0.85rem;">
                <div style="display:flex;flex-direction:column;gap:0.1rem;">
                    <span class="name" style="font-weight:500;color:var(--text-primary);">
                        ${escapeHtml(item.labor_type || "Unknown")}
                    </span>
                    <span style="font-size:0.7rem;color:var(--text-muted);">
                        ${item.technician_name ? `By: ${escapeHtml(item.technician_name)}` : ""}
                        ${item.date_performed ? `· ${Formatter.date(item.date_performed)}` : ""}
                    </span>
                </div>
                <div style="text-align:right;">
                    <span class="hours" style="font-weight:600;color:var(--text-secondary);">
                        ${item.hours}h @ ${Formatter.currency(item.rate)}
                    </span>
                    <br>
                    <span style="font-size:0.75rem;font-weight:600;color:var(--text-primary);">
                        ${Formatter.currency(item.cost)}
                    </span>
                </div>
            </div>
        `,
          )
          .join("")}
        ${
          totalLaborCost > 0
            ? `
            <div style="display:flex;justify-content:space-between;padding:0.5rem 0.75rem;margin-top:0.5rem;
                        border-top:2px solid var(--border);font-weight:600;color:var(--text-primary);">
                <span>Total Labor Cost</span>
                <span>${Formatter.currency(totalLaborCost)}</span>
            </div>
        `
            : ""
        }
    `;
}

// ============================================================
// 17. MATERIAL USAGE RENDER - FULLY FIXED
// ============================================================

function renderDrawerMaterialUsages(materials) {
  const container = DOM.drawerMaterialUsages();
  if (!container) return;

  if (!materials || materials.length === 0) {
    container.innerHTML = `
            <div style="text-align:center;padding:0.5rem 0;color:var(--text-muted);">
                <i class="ph ph-box" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
                No material usage recorded
            </div>
        `;
    return;
  }

  // Enrich materials with item names from state
  const enrichedMaterials = materials.map((item) => {
    const enriched = { ...item };

    // If item_name is missing or is an ID, try to find in state
    if (
      !enriched.item_name ||
      enriched.item_name === enriched.item_id ||
      enriched.item_name.startsWith("{")
    ) {
      const foundItem = state.inventoryItems?.find(
        (i) => i.id === enriched.item_id,
      );
      if (foundItem) {
        enriched.item_name = foundItem.name;
        enriched.unit = foundItem.unit || enriched.unit || "";
        enriched.cost_price = foundItem.cost_price || enriched.cost_price || 0;
      } else {
        // Use helper to get name
        enriched.item_name = getItemName(enriched.item_id);
        const unit = getItemUnit(enriched.item_id);
        if (unit) enriched.unit = unit;
        const cost = getItemCost(enriched.item_id);
        if (cost) enriched.cost_price = cost;
      }
    }
    return enriched;
  });

  // Group materials by name
  const grouped = {};
  enrichedMaterials.forEach((item) => {
    const key = item.item_name || item.item_id || "Unknown";
    if (!grouped[key]) {
      grouped[key] = {
        name: key,
        total_qty: 0,
        unit: item.unit || "",
        items: [],
        item_id: item.item_id,
      };
    }
    grouped[key].total_qty += Number(item.quantity) || 0;
    grouped[key].unit = item.unit || grouped[key].unit;
    grouped[key].items.push(item);
  });

  // Calculate total material cost
  let totalMaterialCost = 0;
  const materialList = Object.values(grouped).map((g) => {
    const cost = g.items.reduce((sum, i) => {
      const price =
        Number(i.cost_price) || Number(i.unit_price) || Number(i.price) || 0;
      return sum + price * (Number(i.quantity) || 0);
    }, 0);
    totalMaterialCost += cost;
    return { ...g, cost };
  });

  container.innerHTML = `
        ${materialList
          .map(
            (g) => `
            <div class="material-list-item" style="display:flex;justify-content:space-between;align-items:center;
                        padding:0.5rem 0.75rem;background:var(--bg-input);border-radius:var(--radius-sm);
                        margin-bottom:0.25rem;font-size:0.85rem;">
                <div style="display:flex;flex-direction:column;gap:0.1rem;">
                    <span class="name" style="font-weight:500;color:var(--text-primary);">
                        ${escapeHtml(g.name)}
                    </span>
                    <span style="font-size:0.7rem;color:var(--text-muted);">
                        ${g.items.length} transaction${g.items.length > 1 ? "s" : ""}
                        ${g.cost > 0 ? `· ${Formatter.currency(g.cost)}` : ""}
                    </span>
                </div>
                <span class="qty" style="font-weight:600;color:var(--text-secondary);">
                    ${g.total_qty} ${escapeHtml(g.unit)}
                </span>
            </div>
        `,
          )
          .join("")}
        ${
          totalMaterialCost > 0
            ? `
            <div style="display:flex;justify-content:space-between;padding:0.5rem 0.75rem;margin-top:0.5rem;
                        border-top:2px solid var(--border);font-weight:600;color:var(--text-primary);">
                <span>Total Material Cost</span>
                <span>${Formatter.currency(totalMaterialCost)}</span>
            </div>
        `
            : ""
        }
    `;
}

// ============================================================
// 18. PAYMENTS RENDER - FIXED
// ============================================================

function renderDrawerPayments(payments) {
  const container = DOM.drawerPaymentHistory();
  const totalDepositEl = DOM.drawerTotalDeposit();
  const totalPaidEl = DOM.drawerTotalPaid();
  const totalPendingEl = DOM.drawerTotalPending();
  const remainingEl = DOM.drawerRemaining();

  if (!container) return;

  console.log("🎨 Rendering payments:", payments);

  // Default empty state
  if (!payments || payments.length === 0) {
    container.innerHTML = `
            <div style="text-align:center;padding:1rem 0;color:var(--text-muted);">
                <i class="ph ph-credit-card" style="font-size:1.5rem;display:block;margin-bottom:0.25rem;"></i>
                No payments recorded
            </div>
        `;
    if (totalDepositEl) totalDepositEl.textContent = Formatter.currency(0);
    if (totalPaidEl) totalPaidEl.textContent = Formatter.currency(0);
    if (totalPendingEl) totalPendingEl.textContent = Formatter.currency(0);
    if (remainingEl) remainingEl.textContent = Formatter.currency(0);
    return;
  }

  // Calculate payment summaries
  const totalDeposit = payments
    .filter((p) => {
      const type = (p.type || p.payment_type || "").toLowerCase();
      return type === "deposit";
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalPaid = payments
    .filter((p) => {
      const status = (p.status || "").toLowerCase();
      return (
        status === "completed" ||
        status === "confirmed" ||
        status === "paid" ||
        status === "success"
      );
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const totalPending = payments
    .filter((p) => {
      const status = (p.status || "").toLowerCase();
      return (
        status === "pending" ||
        status === "awaiting_confirmation" ||
        status === "waiting"
      );
    })
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);

  const remaining = totalDeposit - totalPaid;

  // Update summary values
  if (totalDepositEl) {
    totalDepositEl.textContent = Formatter.currency(totalDeposit);
    totalDepositEl.style.color = "var(--text-primary)";
  }
  if (totalPaidEl) {
    totalPaidEl.textContent = Formatter.currency(totalPaid);
    totalPaidEl.style.color = "var(--success, #10b981)";
  }
  if (totalPendingEl) {
    totalPendingEl.textContent = Formatter.currency(totalPending);
    totalPendingEl.style.color = "var(--warning, #f59e0b)";
  }
  if (remainingEl) {
    remainingEl.textContent = Formatter.currency(remaining > 0 ? remaining : 0);
    remainingEl.style.color =
      remaining > 0 ? "var(--warning, #f59e0b)" : "var(--success, #10b981)";
  }

  // Render payment history
  container.innerHTML = payments
    .map((p, index) => {
      const amount = Number(p.amount) || 0;
      const type = p.type || p.payment_type || "Payment";
      const method = p.method || p.payment_method || "";
      const status = p.status || "pending";
      const reference = p.reference_number || p.reference || "";
      const date = p.created_at || p.paid_at || p.payment_date || "";

      const isPending = [
        "pending",
        "awaiting_confirmation",
        "waiting",
      ].includes(status.toLowerCase());
      const isCompleted = [
        "completed",
        "confirmed",
        "paid",
        "success",
      ].includes(status.toLowerCase());
      const isCancelled = ["cancelled", "failed", "voided"].includes(
        status.toLowerCase(),
      );

      let statusIcon = "⏳";
      let statusLabel = "Pending";
      let statusColor = "var(--warning, #f59e0b)";

      if (isCompleted) {
        statusIcon = "✅";
        statusLabel = "Completed";
        statusColor = "var(--success, #10b981)";
      } else if (isCancelled) {
        statusIcon = "❌";
        statusLabel = "Cancelled";
        statusColor = "var(--danger, #ef4444)";
      } else if (isPending) {
        statusIcon = "⏳";
        statusLabel = "Pending";
        statusColor = "var(--warning, #f59e0b)";
      }

      const typeIcon = type.toLowerCase() === "deposit" ? "🏦" : "💳";

      return `
            <div class="payment-history-item ${isPending ? "pending" : isCompleted ? "completed" : "cancelled"}"
                 style="display:flex;justify-content:space-between;align-items:center;
                        padding:0.6rem 0.75rem;border-bottom:1px solid var(--border);
                        ${
                          isPending
                            ? "border-left:3px solid var(--warning, #f59e0b);"
                            : isCompleted
                              ? "border-left:3px solid var(--success, #10b981);"
                              : "border-left:3px solid var(--danger, #ef4444);"
                        }
                        transition:background var(--transition-fast);">
                <div style="display:flex;flex-direction:column;gap:0.1rem;flex:1;">
                    <div style="display:flex;align-items:center;gap:0.5rem;">
                        <span style="font-size:0.9rem;">${typeIcon}</span>
                        <span class="type" style="font-weight:600;color:var(--text-primary);">
                            ${escapeHtml(type)}
                        </span>
                        <span style="font-size:0.65rem;color:${statusColor};font-weight:500;">
                            ${statusIcon} ${statusLabel}
                        </span>
                    </div>
                    <div style="display:flex;flex-wrap:wrap;gap:0.25rem 0.75rem;font-size:0.7rem;color:var(--text-muted);">
                        ${date ? `<span>📅 ${Formatter.dateTime(date)}</span>` : ""}
                        ${method ? `<span>💳 ${escapeHtml(method)}</span>` : ""}
                        ${reference ? `<span>📋 Ref: ${escapeHtml(reference)}</span>` : ""}
                    </div>
                </div>
                <div style="text-align:right;flex-shrink:0;margin-left:0.5rem;">
                    <span class="payment-amount ${isPending ? "pending" : isCompleted ? "completed" : "cancelled"}"
                          style="font-weight:700;font-size:0.95rem;
                                ${
                                  isPending
                                    ? "color:var(--warning, #f59e0b);"
                                    : isCompleted
                                      ? "color:var(--success, #10b981);"
                                      : "color:var(--danger, #ef4444);"
                                }">
                        ${Formatter.currency(amount)}
                    </span>
                </div>
            </div>
        `;
    })
    .join("");

  // Add total summary at bottom
  if (payments.length > 0) {
    container.innerHTML += `
            <div style="display:flex;justify-content:space-between;padding:0.6rem 0.75rem;margin-top:0.5rem;
                        border-top:2px solid var(--border);font-weight:600;color:var(--text-primary);
                        background:var(--bg-input);border-radius:var(--radius-sm);">
                <span>Total Payments</span>
                <span>${Formatter.currency(payments.reduce((sum, p) => sum + (Number(p.amount) || 0), 0))}</span>
            </div>
        `;
  }
}

function renderDrawerTimeline(activities) {
  const container = DOM.drawerTimeline();
  if (!container) return;

  if (!activities || activities.length === 0) {
    container.innerHTML = `
            <div class="timeline-item">
                <span>—</span>
                <p>No activity yet</p>
            </div>
        `;
    return;
  }

  container.innerHTML = activities
    .map(
      (activity) => `
        <div class="timeline-item">
            <span class="time">${Formatter.date(activity.created_at)}</span>
            <p class="content">${escapeHtml(activity.activity || activity.description || activity.action || "Activity")}</p>
        </div>
    `,
    )
    .join("");
}

function renderDrawerNotes(notes) {
  const container = DOM.drawerNotes();
  const counter = DOM.noteCounter();

  if (!container) return;

  if (!notes || notes.length === 0) {
    container.value = "";
    if (counter) counter.textContent = "0";
    return;
  }

  const latestNote = notes[notes.length - 1];
  container.value = latestNote?.note || "";
  if (counter) counter.textContent = container.value.length;
}

function renderDrawerBeforeAfter(photos) {
  const beforePhotos =
    photos?.filter((p) => p.stage === "before" || p.stage === "initial") || [];
  const afterPhotos =
    photos?.filter((p) => p.stage === "after" || p.stage === "final") || [];

  renderCarousel("before", beforePhotos);
  renderCarousel("after", afterPhotos);
}

function renderCarousel(type, photos) {
  const track = type === "before" ? DOM.beforeTrack() : DOM.afterTrack();
  if (!track) return;

  const container = track.closest(".carousel-container");

  if (!photos || photos.length === 0) {
    track.innerHTML = `<div class="carousel-empty">No ${type} photos</div>`;
    return;
  }

  track.innerHTML = photos
    .map(
      (photo, index) => `
        <img src="${photo.file_path || photo.url || photo.thumbnail_url || "/static/images/placeholder.jpg"}" 
             alt="${type} photo" 
             onclick="openLightbox('${type}', ${index})" />
    `,
    )
    .join("");

  state.carousels[type].images = photos;
  state.carousels[type].index = 0;

  if (container) {
    const prevBtn = container.querySelector(".carousel-btn.prev");
    const nextBtn = container.querySelector(".carousel-btn.next");

    if (prevBtn) prevBtn.onclick = () => navigateCarousel(type, -1);
    if (nextBtn) nextBtn.onclick = () => navigateCarousel(type, 1);

    updateCarouselButtons(type);
  }
}

function navigateCarousel(type, direction) {
  const carousel = state.carousels[type];
  const newIndex = carousel.index + direction;
  const maxIndex = carousel.images.length - 1;

  if (newIndex < 0 || newIndex > maxIndex) return;

  carousel.index = newIndex;
  updateCarouselPosition(type);
  updateCarouselButtons(type);
}

function updateCarouselPosition(type) {
  const track = type === "before" ? DOM.beforeTrack() : DOM.afterTrack();
  if (!track) return;

  const carousel = state.carousels[type];
  const offset = -carousel.index * 100;
  track.style.transform = `translateX(${offset}%)`;
}

function updateCarouselButtons(type) {
  const track = type === "before" ? DOM.beforeTrack() : DOM.afterTrack();
  if (!track) return;

  const container = track.closest(".carousel-container");
  if (!container) return;

  const prevBtn = container.querySelector(".carousel-btn.prev");
  const nextBtn = container.querySelector(".carousel-btn.next");
  const carousel = state.carousels[type];

  if (prevBtn) prevBtn.disabled = carousel.index === 0;
  if (nextBtn) nextBtn.disabled = carousel.index >= carousel.images.length - 1;
}

// ============================================================
// 19. LIGHTBOX
// ============================================================
function openLightbox(type, index) {
  const images =
    type === "before"
      ? state.carousels.before.images
      : state.carousels.after.images;

  if (!images || images.length === 0) return;

  state.lightbox.images = images;
  state.lightbox.currentIndex = index;
  state.lightbox.isOpen = true;

  updateLightboxImage();
  if (DOM.lightboxOverlay()) DOM.lightboxOverlay().style.display = "flex";
  document.body.style.overflow = "hidden";
}

function closeLightbox() {
  state.lightbox.isOpen = false;
  if (DOM.lightboxOverlay()) DOM.lightboxOverlay().style.display = "none";
  document.body.style.overflow = "";
}

function updateLightboxImage() {
  const image = state.lightbox.images[state.lightbox.currentIndex];
  if (DOM.lightboxImage()) {
    DOM.lightboxImage().src =
      image.file_path ||
      image.url ||
      image.thumbnail_url ||
      "/static/images/placeholder.jpg";
    DOM.lightboxImage().alt = `Photo ${state.lightbox.currentIndex + 1} of ${state.lightbox.images.length}`;
  }
}

function navigateLightbox(direction) {
  const newIndex = state.lightbox.currentIndex + direction;
  if (newIndex < 0 || newIndex >= state.lightbox.images.length) return;
  state.lightbox.currentIndex = newIndex;
  updateLightboxImage();
}

// ============================================================
// 20. INQUIRY DETAIL LOADER - FULLY FIXED
// ============================================================

async function loadInquiryDetail(inquiryId) {
  state.currentInquiryId = inquiryId;

  // Load inquiry detail first
  const inquiry = await InquiryAPI.fetchDetail(inquiryId);
  if (!inquiry) return;

  // Load inventory items for material name lookup
  try {
    state.inventoryItems = await InquiryAPI.fetchInventoryItems();
    console.log(
      "📦 Loaded inventory items for material lookup:",
      state.inventoryItems.length,
    );
  } catch (e) {
    console.warn("Failed to load inventory items:", e);
    state.inventoryItems = [];
  }

  // Load all related data in parallel
  const [payments, activities, notes, photos] = await Promise.all([
    InquiryAPI.fetchPayments(inquiryId),
    InquiryAPI.fetchActivities(inquiryId),
    InquiryAPI.fetchNotes(inquiryId, true),
    InquiryAPI.fetchPhotos(inquiryId),
  ]);

  // Store activities and notes in state
  state.activities = activities;
  state.notes = notes;

  // Load project-related data if project exists
  let labor = [];
  let materials = [];
  let financial = null;

  if (inquiry.project && inquiry.project.id) {
    const projectId = inquiry.project.id;

    // Load labor and materials
    [labor, materials] = await Promise.all([
      InquiryAPI.fetchProjectLabor(projectId),
      InquiryAPI.fetchProjectMaterialUsage(projectId),
    ]);

    // Calculate financial data from all sources
    financial = calculateFinancialFromData(inquiry, labor, materials, payments);
    console.log("📊 Calculated financial data:", financial);
  } else {
    financial = {
      estimated_cost: 0,
      actual_cost: 0,
      estimated_revenue: 0,
      actual_revenue: 0,
      deposit_amount: 0,
      deposit_paid: false,
      material_cost: 0,
      labor_cost: 0,
      other_expenses: 0,
    };
  }

  // Render all sections
  renderDrawerCustomer(inquiry);
  renderDrawerVehicle(inquiry);
  renderDrawerFinancial(financial);
  renderDrawerLabor(labor);
  renderDrawerMaterialUsages(materials);
  renderDrawerPayments(payments);
  renderDrawerTimeline(activities);
  renderDrawerNotes(notes);
  renderDrawerBeforeAfter(photos);

  // Update action buttons based on status
  updateActionButtons(inquiry);

  // Store inquiry data
  state._currentInquiry = inquiry;

  // Open drawer
  if (DOM.drawer()) DOM.drawer().classList.add("active");
  if (DOM.drawerBackdrop()) DOM.drawerBackdrop().classList.add("active");
  document.body.style.overflow = "hidden";
}

function updateActionButtons(inquiry) {
  if (!inquiry) return;

  const status = inquiry.status;

  const approveBtn = DOM.drawerApproveBtn();
  const quoteBtn = DOM.drawerQuoteBtn();
  const rejectBtn = DOM.drawerRejectBtn();
  const convertBtn = DOM.drawerConvertBtn();
  const viewProjectBtn = DOM.drawerViewProjectBtn();

  if (approveBtn) {
    approveBtn.style.display = ["new", "under_review"].includes(status)
      ? "inline-flex"
      : "none";
  }
  if (quoteBtn) {
    quoteBtn.style.display = ["new", "under_review", "contacted"].includes(
      status,
    )
      ? "inline-flex"
      : "none";
  }
  if (rejectBtn) {
    rejectBtn.style.display = !["rejected", "converted", "completed"].includes(
      status,
    )
      ? "inline-flex"
      : "none";
  }
  if (convertBtn) {
    convertBtn.style.display = ["approved", "quoted"].includes(status)
      ? "inline-flex"
      : "none";
    if (status === "converted") {
      convertBtn.disabled = true;
      convertBtn.textContent = "✓ Converted";
    } else {
      convertBtn.disabled = false;
      convertBtn.innerHTML =
        '<i class="ph ph-arrow-right"></i> Convert to Project';
    }
  }

  if (viewProjectBtn) {
    if (inquiry.project) {
      viewProjectBtn.style.display = "inline-flex";
      viewProjectBtn.href = `/projects/${inquiry.project.id}`;
    } else {
      viewProjectBtn.style.display = "none";
    }
  }
}

// ============================================================
// 21. DRAWER FUNCTIONS
// ============================================================

async function openInquiryDrawer(inquiryId) {
  await loadInquiryDetail(inquiryId);
}

function closeDrawer() {
  if (DOM.drawer()) DOM.drawer().classList.remove("active");
  if (DOM.drawerBackdrop()) DOM.drawerBackdrop().classList.remove("active");
  document.body.style.overflow = "";
  state.currentInquiryId = null;
}

// ============================================================
// 22. ACTION HANDLERS
// ============================================================

async function handleApprove(inquiryId) {
  if (!confirm("Approve this inquiry?")) return;

  const result = await InquiryAPI.updateStatus(
    inquiryId,
    "approved",
    "Approved by staff",
  );
  if (result) {
    showToast("Inquiry approved!", "success");
    await loadInquiries();
    if (DOM.drawer() && DOM.drawer().classList.contains("active")) {
      await loadInquiryDetail(inquiryId);
    }
  }
}

async function handleUpdateStatus(inquiryId, status, note = "") {
  const result = await InquiryAPI.updateStatus(inquiryId, status, note);
  if (result) {
    showToast(`Status updated to ${Formatter.statusLabel(status)}`, "success");
    await loadInquiries();
    if (DOM.drawer() && DOM.drawer().classList.contains("active")) {
      await loadInquiryDetail(inquiryId);
    }
  }
}

// ============================================================
// 23. MODAL FUNCTIONS
// ============================================================

// --- Convert Modal ---
function openConvertModal(inquiryId) {
  state._convertInquiryId = inquiryId;
  if (DOM.convertStartDate()) {
    DOM.convertStartDate().value = new Date().toISOString().split("T")[0];
  }
  if (DOM.convertTargetDelivery()) {
    DOM.convertTargetDelivery().value = "";
  }
  if (DOM.convertModal()) DOM.convertModal().classList.add("active");
}

function closeConvertModal() {
  if (DOM.convertModal()) DOM.convertModal().classList.remove("active");
  state._convertInquiryId = null;
}

async function handleConvert(e) {
  if (e) e.preventDefault();

  const inquiryId = state._convertInquiryId;
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  const startDate = DOM.convertStartDate()?.value || null;
  const targetDelivery = DOM.convertTargetDelivery()?.value || null;

  const result = await InquiryAPI.convertToProject(
    inquiryId,
    startDate,
    targetDelivery,
  );
  if (result) {
    showToast("🎉 Project created successfully!", "success");
    closeConvertModal();
    await loadInquiries();
    if (DOM.drawer() && DOM.drawer().classList.contains("active")) {
      await loadInquiryDetail(inquiryId);
    }
  }
}

// --- Quote Modal ---
function openQuoteModal(inquiryId) {
  state._quoteInquiryId = inquiryId;
  if (DOM.quoteCost()) DOM.quoteCost().value = "";
  if (DOM.quoteNotes()) DOM.quoteNotes().value = "";
  if (DOM.quoteModal()) DOM.quoteModal().classList.add("active");
}

function closeQuoteModal() {
  if (DOM.quoteModal()) DOM.quoteModal().classList.remove("active");
  state._quoteInquiryId = null;
}

async function handleSendQuote(e) {
  if (e) e.preventDefault();

  const inquiryId = state._quoteInquiryId;
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  const cost = parseFloat(DOM.quoteCost()?.value);
  if (!cost || cost <= 0) {
    showToast("Please enter a valid estimated cost", "error");
    return;
  }

  const notes = DOM.quoteNotes()?.value?.trim() || "";

  const result = await InquiryAPI.sendQuotation(inquiryId, cost, notes);
  if (result) {
    showToast("Quotation sent!", "success");
    closeQuoteModal();
    await handleUpdateStatus(inquiryId, "quoted", "Quotation sent");
  }
}

// --- Reject Modal ---
function openRejectModal(inquiryId) {
  state._rejectInquiryId = inquiryId;
  if (DOM.rejectReason()) DOM.rejectReason().value = "";
  if (DOM.rejectModal()) DOM.rejectModal().classList.add("active");
}

function closeRejectModal() {
  if (DOM.rejectModal()) DOM.rejectModal().classList.remove("active");
  state._rejectInquiryId = null;
}

async function handleReject(e) {
  if (e) e.preventDefault();

  const inquiryId = state._rejectInquiryId;
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  const reason = DOM.rejectReason()?.value?.trim() || "";

  if (!confirm("Reject this inquiry?")) return;

  const result = await InquiryAPI.reject(inquiryId, reason);
  if (result) {
    showToast("Inquiry rejected", "info");
    closeRejectModal();
    await loadInquiries();
    if (DOM.drawer() && DOM.drawer().classList.contains("active")) {
      await loadInquiryDetail(inquiryId);
    }
  }
}

// ============================================================
// 24. WHATSAPP HANDLER
// ============================================================

function handleWhatsApp(inquiry) {
  const phone = inquiry?.customer_phone_number;
  if (!phone) {
    showToast("No phone number available", "error");
    return;
  }

  const cleanPhone = phone.replace(/[^0-9]/g, "");
  const message = encodeURIComponent(
    `Halo ${inquiry.customer_name},\n\n` +
      `Kami dari NOCTRA ingin menindaklanjuti inquiry Anda mengenai:\n` +
      `• Kendaraan: ${inquiry.vehicle_brand} ${inquiry.vehicle_model}\n` +
      `• Tipe Proyek: ${inquiry.project_type}\n\n` +
      `Ada yang bisa kami bantu? 😊`,
  );

  const url = `https://wa.me/${cleanPhone}?text=${message}`;
  window.open(url, "_blank");
}

// ============================================================
// 25. NOTES HANDLER
// ============================================================

async function handleSaveNote() {
  const inquiryId = state.currentInquiryId;
  if (!inquiryId) {
    showToast("No inquiry selected", "error");
    return;
  }

  const note = DOM.drawerNotes()?.value?.trim();
  if (!note) {
    showToast("Please enter a note", "error");
    return;
  }

  const result = await InquiryAPI.addNote(inquiryId, note, "internal", false);
  if (result) {
    showToast("Note saved!", "success");
    if (DOM.noteCounter()) DOM.noteCounter().textContent = note.length;
  }
}

// Note character counter
if (DOM.drawerNotes()) {
  DOM.drawerNotes().addEventListener("input", () => {
    if (DOM.noteCounter()) {
      DOM.noteCounter().textContent = DOM.drawerNotes().value.length;
    }
  });
}

// ============================================================
// 26. EXPORT FUNCTION
// ============================================================

function exportInquiries() {
  if (!state.inquiries || state.inquiries.length === 0) {
    showToast("No data to export", "warning");
    return;
  }

  const headers = [
    "ID",
    "Customer",
    "Phone",
    "Vehicle",
    "Project Type",
    "Status",
    "Created",
    "Has Project",
  ];
  const rows = state.inquiries.map((inq) => [
    inq.id,
    inq.customer_name,
    inq.customer_phone_number,
    `${inq.vehicle_brand} ${inq.vehicle_model}`,
    inq.project_type,
    Formatter.statusLabel(inq.status),
    Formatter.date(inq.created_at),
    inq.project ? "Yes" : "No",
  ]);

  const csv = [headers.join(","), ...rows.map((row) => row.join(","))].join(
    "\n",
  );
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `inquiries_export_${new Date().toISOString().split("T")[0]}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);

  showToast("Export completed!", "success");
}

// ============================================================
// 27. MAIN LOAD FUNCTION
// ============================================================

async function loadInquiries() {
  const data = await InquiryAPI.fetchInquiries(
    state.currentPage,
    state.filters,
  );
  if (!data) {
    const body = DOM.inquiriesBody();
    if (body) {
      body.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center; padding:2rem; color: var(--text-muted);">
                        <i class="ph ph-warning" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                        Failed to load inquiries. Please try again.
                        <br><br>
                        <button class="btn-primary" onclick="loadInquiries()">
                            <i class="ph ph-arrow-clockwise"></i> Retry
                        </button>
                    </td>
                </tr>
            `;
    }
    return;
  }

  let inquiries = [];
  let totalPages = 1;
  let totalItems = 0;

  if (data.data && Array.isArray(data.data)) {
    inquiries = data.data;
    totalItems = data.total || data.total_items || inquiries.length;
    totalPages =
      data.total_pages ||
      data.totalPages ||
      Math.ceil(totalItems / CONFIG.INQUIRIES_PER_PAGE);
  } else if (Array.isArray(data)) {
    inquiries = data;
    totalItems = inquiries.length;
    totalPages = Math.ceil(totalItems / CONFIG.INQUIRIES_PER_PAGE);
  } else if (data.items && Array.isArray(data.items)) {
    inquiries = data.items;
    totalItems = data.total || data.total_items || inquiries.length;
    totalPages =
      data.total_pages ||
      data.totalPages ||
      Math.ceil(totalItems / CONFIG.INQUIRIES_PER_PAGE);
  }

  state.inquiries = inquiries;
  state.totalPages = Math.max(1, totalPages);
  state.totalItems = totalItems;

  renderInquiries(state.inquiries);
  updatePagination(state.currentPage, state.totalPages, state.totalItems);

  const stats = await InquiryAPI.fetchStatistics();
  updateDashboard(stats);
}

// ============================================================
// 28. EVENT BINDINGS
// ============================================================

function bindEvents() {
  // Pagination
  DOM.prevPage()?.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage--;
      loadInquiries();
    }
  });

  DOM.nextPage()?.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      state.currentPage++;
      loadInquiries();
    }
  });

  // Search with debounce
  let searchTimeout;
  DOM.searchInquiry()?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.currentPage = 1;
      loadInquiries();
    }, 300);
  });

  // Status filter
  DOM.statusFilter()?.addEventListener("change", (e) => {
    state.filters.status = e.target.value;
    state.currentPage = 1;
    loadInquiries();
  });

  // Export
  DOM.exportInquiriesBtn()?.addEventListener("click", exportInquiries);

  // Close drawer
  DOM.closeDrawer()?.addEventListener("click", closeDrawer);
  DOM.drawerBackdrop()?.addEventListener("click", closeDrawer);

  // Close modals
  DOM.closeConvertModal()?.addEventListener("click", closeConvertModal);
  DOM.cancelConvertBtn()?.addEventListener("click", closeConvertModal);
  DOM.convertModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.convertModal()) closeConvertModal();
  });

  DOM.closeQuoteModal()?.addEventListener("click", closeQuoteModal);
  DOM.cancelQuoteBtn()?.addEventListener("click", closeQuoteModal);
  DOM.quoteModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.quoteModal()) closeQuoteModal();
  });

  DOM.closeRejectModal()?.addEventListener("click", closeRejectModal);
  DOM.cancelRejectBtn()?.addEventListener("click", closeRejectModal);
  DOM.rejectModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.rejectModal()) closeRejectModal();
  });

  // Form submissions
  DOM.convertForm()?.addEventListener("submit", handleConvert);
  DOM.quoteForm()?.addEventListener("submit", handleSendQuote);
  DOM.rejectForm()?.addEventListener("submit", handleReject);

  // Drawer action buttons
  DOM.drawerApproveBtn()?.addEventListener("click", () => {
    if (state.currentInquiryId) handleApprove(state.currentInquiryId);
  });

  DOM.drawerQuoteBtn()?.addEventListener("click", () => {
    if (state.currentInquiryId) openQuoteModal(state.currentInquiryId);
  });

  DOM.drawerRejectBtn()?.addEventListener("click", () => {
    if (state.currentInquiryId) openRejectModal(state.currentInquiryId);
  });

  DOM.drawerWhatsappBtn()?.addEventListener("click", () => {
    if (state._currentInquiry) handleWhatsApp(state._currentInquiry);
  });

  DOM.drawerConvertBtn()?.addEventListener("click", () => {
    if (state.currentInquiryId) openConvertModal(state.currentInquiryId);
  });

  // Payment buttons (placeholder)
  DOM.addDepositBtn()?.addEventListener("click", () => {
    showToast("Add deposit feature coming soon", "info");
  });

  DOM.addPaymentBtn()?.addEventListener("click", () => {
    showToast("Add payment feature coming soon", "info");
  });

  DOM.viewInvoicesBtn()?.addEventListener("click", () => {
    showToast("View invoices feature coming soon", "info");
  });

  // Lightbox events
  DOM.lightboxClose()?.addEventListener("click", closeLightbox);
  DOM.lightboxOverlay()?.addEventListener("click", (e) => {
    if (e.target === DOM.lightboxOverlay()) closeLightbox();
  });
  DOM.lightboxPrev()?.addEventListener("click", () => navigateLightbox(-1));
  DOM.lightboxNext()?.addEventListener("click", () => navigateLightbox(1));
}

// ============================================================
// 29. KEYBOARD SHORTCUTS
// ============================================================

document.addEventListener("keydown", (e) => {
  // Escape
  if (e.key === "Escape") {
    if (
      DOM.lightboxOverlay() &&
      DOM.lightboxOverlay().style.display === "flex"
    ) {
      closeLightbox();
    }
    if (DOM.drawer() && DOM.drawer().classList.contains("active")) {
      closeDrawer();
    }
    if (DOM.convertModal() && DOM.convertModal().classList.contains("active")) {
      closeConvertModal();
    }
    if (DOM.quoteModal() && DOM.quoteModal().classList.contains("active")) {
      closeQuoteModal();
    }
    if (DOM.rejectModal() && DOM.rejectModal().classList.contains("active")) {
      closeRejectModal();
    }
  }

  // Arrow keys for lightbox
  if (e.key === "ArrowLeft" && state.lightbox.isOpen) {
    navigateLightbox(-1);
  }
  if (e.key === "ArrowRight" && state.lightbox.isOpen) {
    navigateLightbox(1);
  }

  // Ctrl+F to focus search
  if (e.ctrlKey && e.key === "f") {
    e.preventDefault();
    DOM.searchInquiry()?.focus();
  }

  // Ctrl+E to export
  if (e.ctrlKey && e.key === "e") {
    e.preventDefault();
    exportInquiries();
  }
});

// ============================================================
// 30. INITIALIZATION
// ============================================================

async function init() {
  console.log("🚀 Initializing Inquiries page...");
  try {
    bindEvents();
    await loadInquiries();
    console.log("📋 Inquiries page initialized successfully");
  } catch (error) {
    console.error("❌ Failed to initialize inquiries page:", error);
    showToast("Failed to initialize page: " + error.message, "error");
  }
}

// Run initialization
init();

// ============================================================
// 31. EXPOSE TO GLOBAL
// ============================================================

window.openInquiryDrawer = openInquiryDrawer;
window.openConvertModal = openConvertModal;
window.openQuoteModal = openQuoteModal;
window.openRejectModal = openRejectModal;
window.handleApprove = handleApprove;
window.handleUpdateStatus = handleUpdateStatus;
window.loadInquiries = loadInquiries;
window.openLightbox = openLightbox;
window.closeLightbox = closeLightbox;
window.navigateLightbox = navigateLightbox;
window.exportInquiries = exportInquiries;
window.handleWhatsApp = handleWhatsApp;
window.closeDrawer = closeDrawer;
window.closeConvertModal = closeConvertModal;
window.closeQuoteModal = closeQuoteModal;
window.closeRejectModal = closeRejectModal;
window.handleSaveNote = handleSaveNote;

console.log("📋 Inquiries page fully loaded");
