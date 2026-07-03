/**
 * NOCTRA Project Management
 * Card view with Tabbed Drawer, Progress Popup, Material & Labor management.
 */
(function () {
  "use strict";

  // ─── Constants ──────────────────────────────────────────────
  const API_BASE = "/api/projects";
  const INVENTORY_API = "/api/inventory";
  const PRICE_LIST_API = "/api/price-list";

  const STATUS_LABELS = {
    draft: "Draft",
    active: "Active",
    in_progress: "In Progress",
    on_hold: "On Hold",
    completed: "Completed",
    cancelled: "Cancelled",
    preparation: "Preparation",
    painting: "Painting",
    assembly: "Assembly",
    new: "New",
    quoted: "Quoted",
    approved: "Approved",
  };

  const PRIORITY_LABELS = {
    low: "Low",
    medium: "Medium",
    high: "High",
    urgent: "Urgent",
  };

  const MILESTONE_STAGES = [
    { key: "inquiry", label: "Inquiry Approved", threshold: 10 },
    { key: "disassembly", label: "Disassembly", threshold: 25 },
    { key: "paint_prep", label: "Paint Prep", threshold: 40 },
    { key: "painting", label: "Painting", threshold: 60 },
    { key: "assembly", label: "Assembly", threshold: 80 },
    { key: "qc", label: "Quality Check", threshold: 95 },
    { key: "delivery", label: "Ready for Delivery", threshold: 100 },
  ];

  // ─── Main Class ──────────────────────────────────────────────
  class ProjectManager {
    // ─── Private fields ──────────────────────────────────────
    #state = {
      projects: [],
      currentFilter: "",
      currentPriority: "",
      currentSearch: "",
      currentProjectId: null,
      isSubmitting: false,
      isLoading: false,
      laborOptions: [],
      materialOptions: [],
    };

    #dom = {};
    #timers = { search: null };
    #popup = null;

    // ─── Constructor ──────────────────────────────────────────
    constructor() {
      this.#cacheDomRefs();
      this.#ensureToastContainer();
      this.#injectStyles();
      this.#initTabs();
      this.#initProgressPopup();
      this.#bindEvents();
      this.#init();
    }

    // ─── DOM Caching ──────────────────────────────────────────
    #cacheDomRefs() {
      const ids = [
        "projectCardGrid",
        "projectSearch",
        "statusFilter",
        "priorityFilter",
        "activeCount",
        "prodCount",
        "completedCount",
        "revenueTotal",
        "projectDrawer",
        "closeDrawer",
        "projectModal",
        "modalTitle",
        "modalSubtitle",
        "projectForm",
        "submitProjectBtn",
        "closeModal",
        "cancelModalBtn",
        "newProjectBtn",
        "editProjectId",
        "progressPopup",
        "progressPopupSlider",
        "progressPopupValue",
        "progressPopupNote",
        "progressPopupMilestones",
        "markCompleteCheckbox",
        "closeProgressPopup",
        "cancelProgressBtn",
        "saveProgressBtn",
        "progressPopupTitle",
        "progressPopupSubtitle",
        "drawerTitle",
        "drawerCustomer",
        "drawerPhone",
        "drawerEmail",
        "drawerStatus",
        "drawerPriority",
        "drawerProgressFill",
        "drawerProgressText",
        "drawerBrand",
        "drawerModel",
        "drawerYear",
        "drawerPlate",
        "drawerStartDate",
        "drawerDelivery",
        "drawerActualDelivery",
        "drawerCompletedAt",
        "drawerDuration",
        "drawerTimelineStatus",
        "drawerNotes",
        "drawerMaterialsList",
        "laborList",
        "materialSelect",
        "materialQty",
        "materialUnit",
        "consumeMaterialBtn",
        "laborTypeSelect",
        "laborHours",
        "laborRate",
        "addLaborBtn",
        "timelineMilestones",
        "timelineNote",
        "drawerActivities",
        "exportBtn",
        "drawerEstCost",
        "drawerActualCost",
        "drawerEstRevenue",
        "drawerActualRevenue",
        "drawerDeposit",
        "drawerDepositPaid",
        "drawerProfit",
        "drawerMargin",
        "progressDisplay",
        "progressSliderForm",
      ];
      const refs = {};
      ids.forEach((id) => {
        refs[id] = document.getElementById(id);
      });
      // Tabs
      refs.tabButtons = document.querySelectorAll(".tab-btn");
      refs.tabPanels = {
        overview: document.getElementById("tab-overview"),
        financial: document.getElementById("tab-financial"),
        material: document.getElementById("tab-material"),
        labor: document.getElementById("tab-labor"),
        timeline: document.getElementById("tab-timeline"),
      };
      this.#dom = refs;
    }

    // ─── Style Injection ──────────────────────────────────────
    #injectStyles() {
      if (document.getElementById("project-styles")) return;
      const style = document.createElement("style");
      style.id = "project-styles";
      style.textContent = `
                .loading-placeholder { text-align: center; color: var(--gray-500, #6b7280); padding: 2rem 0; }
                .project-card-item { background: var(--card-bg, #1a1a2e); border-radius: 12px; padding: 1rem; border: 1px solid var(--border-color, #2d2d44); cursor: pointer; transition: all 0.2s; }
                .project-card-item:hover { transform: translateY(-2px); border-color: var(--accent, #ff7b2c); }
                .card-header { display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem; }
                .card-header h4 { margin: 0; font-size: 1rem; }
                .card-body { font-size: 0.85rem; color: var(--text-muted, #94a3b8); }
                .card-body .customer, .card-body .vehicle { margin: 0.2rem 0; }
                .card-progress { margin-top: 0.75rem; }
                .progress-bar { background: rgba(255,255,255,0.05); border-radius: 8px; height: 6px; overflow: hidden; }
                .progress-bar .fill { height: 100%; background: var(--accent, #ff7b2c); transition: width 0.3s; }
                .progress-label { display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-muted, #94a3b8); margin-top: 0.2rem; }
                .card-actions { display: flex; gap: 0.5rem; margin-top: 0.75rem; flex-wrap: wrap; }
                .card-actions button { flex: 1; min-width: 60px; padding: 4px 8px; font-size: 0.75rem; border-radius: 6px; border: none; cursor: pointer; transition: background 0.2s; background: rgba(255,255,255,0.05); color: var(--text-primary, #f1f5f9); }
                .card-actions button:hover { background: rgba(255,255,255,0.1); }
                .btn-complete { background: #10b981 !important; color: #fff !important; }
                .badge-completed { background: #10b981; color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; }
                .priority-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.65rem; font-weight: 600; }
                .priority-badge.low { background: rgba(107,114,128,0.15); color: #6b7280; }
                .priority-badge.medium { background: rgba(59,130,246,0.15); color: #3b82f6; }
                .priority-badge.high { background: rgba(245,158,11,0.15); color: #f59e0b; }
                .priority-badge.urgent { background: rgba(239,68,68,0.15); color: #ef4444; }
                .status-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; }
                .status-badge.draft { background: rgba(107,114,128,0.15); color: #6b7280; }
                .status-badge.active { background: rgba(59,130,246,0.15); color: #3b82f6; }
                .status-badge.in_progress { background: rgba(245,158,11,0.15); color: #f59e0b; }
                .status-badge.on_hold { background: rgba(139,92,246,0.15); color: #8b5cf6; }
                .status-badge.completed { background: rgba(34,197,94,0.15); color: #22c55e; }
                .status-badge.cancelled { background: rgba(239,68,68,0.15); color: #ef4444; }
                .status-badge.preparation { background: rgba(139,92,246,0.15); color: #8b5cf6; }
                .status-badge.painting { background: rgba(236,72,153,0.15); color: #ec4899; }
                .status-badge.assembly { background: rgba(14,165,233,0.15); color: #0ea5e9; }
                .status-badge.new { background: rgba(59,130,246,0.15); color: #3b82f6; }
                .status-badge.quoted { background: rgba(245,158,11,0.15); color: #f59e0b; }
                .status-badge.approved { background: rgba(16,185,129,0.15); color: #10b981; }
                .milestone-item { padding: 4px 0; font-size: 0.85rem; }
                .milestone-item.done { color: #10b981; }
                .milestone-item.active { color: #f59e0b; font-weight: 600; }
                .milestone-item.pending { color: var(--text-muted, #94a3b8); }
                .btn-delete-item { background: none; border: none; color: #ef4444; cursor: pointer; padding: 0 4px; font-size: 1rem; }
                .btn-delete-item:hover { transform: scale(1.2); }
                #drawerMaterialsList > div, #laborList > div { display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0; border-bottom: 1px solid var(--border-color, #2d2d44); }
                .project-status-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 500; }
                .project-status-badge.completed { background: rgba(16,185,129,0.15); color: #10b981; }
                .project-status-badge.no-project { background: rgba(107,114,128,0.15); color: #6b7280; }
                .financial-detail-table { width: 100%; font-size: 0.85rem; border-collapse: collapse; }
                .financial-detail-table th, .financial-detail-table td { padding: 6px 8px; text-align: left; border-bottom: 1px solid var(--border-color, #2d2d44); }
                .financial-detail-table th { color: var(--text-muted, #94a3b8); font-weight: 500; }
                .no-data { color: var(--text-muted, #94a3b8); font-style: italic; }
                .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; }
                .detail-item { display: flex; flex-direction: column; }
                .detail-item label { font-size: 0.7rem; color: var(--text-muted, #94a3b8); text-transform: uppercase; letter-spacing: 0.05em; }
                .detail-item p { margin: 0; font-weight: 500; }
                .detail-item.full { grid-column: span 2; }
            `;
      document.head.appendChild(style);
    }

    // ─── Toast Container ──────────────────────────────────────
    #ensureToastContainer() {
      if (!document.getElementById("toastContainer")) {
        const container = document.createElement("div");
        container.id = "toastContainer";
        container.style.cssText = `
                    position: fixed;
                    bottom: 24px;
                    right: 24px;
                    z-index: 99999;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    max-width: 400px;
                `;
        document.body.appendChild(container);
      }
    }

    // ─── Tabs ──────────────────────────────────────────────────
    #initTabs() {
      const { tabButtons, tabPanels } = this.#dom;
      if (!tabButtons || tabButtons.length === 0) return;
      tabButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          tabButtons.forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          const tab = btn.dataset.tab;
          Object.keys(tabPanels).forEach((key) => {
            const panel = tabPanels[key];
            if (panel) panel.classList.toggle("active", key === tab);
          });
        });
      });
    }

    // ─── Progress Popup ──────────────────────────────────────
    #initProgressPopup() {
      this.#popup = {
        slider: this.#dom.progressPopupSlider,
        value: this.#dom.progressPopupValue,
        note: this.#dom.progressPopupNote,
        milestones: this.#dom.progressPopupMilestones,
        markComplete: this.#dom.markCompleteCheckbox,
      };
    }

    // ─── Event Binding ────────────────────────────────────────
    #bindEvents() {
      const {
        projectSearch,
        statusFilter,
        priorityFilter,
        newProjectBtn,
        closeDrawer,
        projectModal,
        closeModal,
        cancelModalBtn,
        projectForm,
        submitProjectBtn,
        progressPopup,
        closeProgressPopup,
        cancelProgressBtn,
        saveProgressBtn,
        consumeMaterialBtn,
        addLaborBtn,
        exportBtn,
        progressPopupSlider,
        markCompleteCheckbox,
      } = this.#dom;

      projectSearch?.addEventListener("input", () => {
        clearTimeout(this.#timers.search);
        this.#timers.search = setTimeout(() => {
          this.#state.currentSearch = projectSearch.value;
          this.#renderCards();
        }, 300);
      });

      statusFilter?.addEventListener("change", () => {
        this.#state.currentFilter = statusFilter.value;
        this.#renderCards();
      });

      priorityFilter?.addEventListener("change", () => {
        this.#state.currentPriority = priorityFilter.value;
        this.#renderCards();
      });

      newProjectBtn?.addEventListener("click", () => this.#openModal());

      closeDrawer?.addEventListener("click", () => this.#closeDrawer());
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          if (this.#dom.projectDrawer?.classList.contains("active"))
            this.#closeDrawer();
          if (this.#dom.projectModal?.classList.contains("active"))
            this.#closeModal();
          if (this.#dom.progressPopup?.classList.contains("active"))
            this.#closeProgressPopup();
        }
      });

      closeModal?.addEventListener("click", () => this.#closeModal());
      cancelModalBtn?.addEventListener("click", () => this.#closeModal());
      projectModal?.addEventListener("click", (e) => {
        if (e.target === projectModal) this.#closeModal();
      });

      projectForm?.addEventListener("submit", (e) => this.#handleFormSubmit(e));

      closeProgressPopup?.addEventListener("click", () =>
        this.#closeProgressPopup(),
      );
      cancelProgressBtn?.addEventListener("click", () =>
        this.#closeProgressPopup(),
      );
      progressPopup?.addEventListener("click", (e) => {
        if (e.target === progressPopup) this.#closeProgressPopup();
      });

      progressPopupSlider?.addEventListener("input", (e) => {
        const val = parseInt(e.target.value, 10);
        if (this.#dom.progressPopupValue)
          this.#dom.progressPopupValue.textContent = val;
        this.#updateMilestoneHighlights(val);
        if (val === 100 && markCompleteCheckbox) {
          markCompleteCheckbox.style.display = "flex";
          markCompleteCheckbox.checked = true;
        } else if (markCompleteCheckbox) {
          markCompleteCheckbox.style.display = "none";
          markCompleteCheckbox.checked = false;
        }
      });

      saveProgressBtn?.addEventListener("click", () =>
        this.#saveProgressPopup(),
      );

      consumeMaterialBtn?.addEventListener("click", (e) =>
        this.#consumeMaterial(e),
      );

      addLaborBtn?.addEventListener("click", (e) => this.#addLabor(e));

      exportBtn?.addEventListener("click", () =>
        this.#showToast("Export feature coming soon"),
      );

      document.addEventListener("click", (e) => {
        const deleteBtn = e.target.closest(".btn-delete-item");
        if (deleteBtn) {
          const type = deleteBtn.dataset.type;
          const id = deleteBtn.dataset.id;
          const projectId =
            deleteBtn.dataset.project || this.#state.currentProjectId;
          if (!projectId)
            return this.#showToast("Project ID not found", "error");
          if (type === "labor") this.#deleteLabor(id, projectId);
          else if (type === "material") this.#deleteMaterial(id, projectId);
        }
      });

      // Progress slider in modal - FIXED
      const sliderForm = this.#dom.progressSliderForm;
      const display = this.#dom.progressDisplay;
      if (sliderForm && display) {
        sliderForm.addEventListener("input", () => {
          display.textContent = sliderForm.value;
          // Update background gradient for visual feedback
          const percentage = parseInt(sliderForm.value, 10);
          sliderForm.style.background = `linear-gradient(90deg, var(--accent, #ff7b2c) ${percentage}%, rgba(255,255,255,0.08) ${percentage}%)`;
        });
        // Trigger initial display
        sliderForm.dispatchEvent(new Event("input"));
      }
    }

    // ─── Initialization ──────────────────────────────────────
    async #init() {
      await this.#loadProjects();
      const params = new URLSearchParams(window.location.search);
      const openId = params.get("open");
      if (openId) {
        setTimeout(() => this.#openDrawer(openId), 500);
        const url = new URL(window.location);
        url.searchParams.delete("open");
        window.history.replaceState({}, "", url);
      }
    }

    // ─── API Helpers ──────────────────────────────────────────
    async #fetchJSON(url, options = {}) {
      const res = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
      });
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || res.statusText);
      }
      return res.json();
    }

    // ─── Load Projects ────────────────────────────────────────
    async #loadProjects() {
      if (this.#state.isLoading) return;
      this.#state.isLoading = true;
      const grid = this.#dom.projectCardGrid;
      if (grid)
        grid.innerHTML = `<div class="loading-placeholder">Loading projects...</div>`;

      try {
        const response = await this.#fetchJSON(`${API_BASE}/`);
        const items = response?.data?.items;
        this.#state.projects = Array.isArray(items) ? items : [];
        this.#renderCards();
        this.#updateDashboard();
      } catch (err) {
        console.error("Load projects error:", err);
        this.#showToast("Failed to load projects", "error");
        if (grid)
          grid.innerHTML = `<div class="loading-placeholder">Error loading projects</div>`;
        this.#state.projects = [];
      } finally {
        this.#state.isLoading = false;
      }
    }

    // ─── Render Cards ─────────────────────────────────────────
    #renderCards() {
      const grid = this.#dom.projectCardGrid;
      if (!grid) return;

      const projects = Array.isArray(this.#state.projects)
        ? this.#state.projects
        : [];

      const search = (this.#state.currentSearch || "").toLowerCase().trim();
      const status = (this.#state.currentFilter || "").toLowerCase();
      const priority = (this.#state.currentPriority || "").toLowerCase();

      const filtered = projects.filter((proj) => {
        const matchSearch =
          !search ||
          (proj.name || "").toLowerCase().includes(search) ||
          (proj.customer_name || "").toLowerCase().includes(search) ||
          (proj.vehicle_brand || "").toLowerCase().includes(search) ||
          (proj.vehicle_model || "").toLowerCase().includes(search);
        const matchStatus =
          !status || (proj.status || "").toLowerCase() === status;
        const matchPriority =
          !priority || (proj.priority || "").toLowerCase() === priority;
        return matchSearch && matchStatus && matchPriority;
      });

      if (filtered.length === 0) {
        grid.innerHTML = `<div class="loading-placeholder">No projects found</div>`;
        return;
      }

      grid.innerHTML = filtered
        .map((proj) => {
          const progress = proj.progress || 0;
          const isComplete = (proj.status || "").toLowerCase() === "completed";
          const statusKey = (proj.status || "").toLowerCase();
          const priorityKey = (proj.priority || "medium").toLowerCase();
          return `
                    <div class="project-card-item" data-id="${proj.id}">
                        <div class="card-header">
                            <h4>${this.#escapeHtml(proj.name)}</h4>
                            <span class="status-badge ${statusKey}">${this.#statusLabel(proj.status)}</span>
                        </div>
                        <div class="card-body">
                            <div class="customer">👤 ${this.#escapeHtml(proj.customer_name)}</div>
                            <div class="vehicle">🏍️ ${this.#escapeHtml(proj.vehicle_brand)} ${this.#escapeHtml(proj.vehicle_model)}</div>
                            <div class="priority">🔹 ${this.#priorityLabel(proj.priority)}</div>
                        </div>
                        <div class="card-progress">
                            <div class="progress-bar"><div class="fill" style="width:${progress}%;"></div></div>
                            <div class="progress-label"><span>Progress</span><span>${progress}%</span></div>
                        </div>
                        <div class="card-actions">
                            <button class="btn-progress" data-action="update-progress" data-id="${proj.id}">
                                <i class="ph ph-sliders-horizontal"></i> Progress
                            </button>
                            <button class="btn-details" data-action="view-details" data-id="${proj.id}">
                                <i class="ph ph-eye"></i> Detail
                            </button>
                            ${
                              progress === 100 && !isComplete
                                ? `
                                <button class="btn-complete" data-action="complete" data-id="${proj.id}">
                                    <i class="ph ph-check-circle"></i> Complete
                                </button>
                            `
                                : ""
                            }
                            ${isComplete ? `<span class="badge-completed">✅ Selesai</span>` : ""}
                        </div>
                    </div>
                `;
        })
        .join("");

      // Attach events - FIXED untuk semua action
      grid
        .querySelectorAll('[data-action="update-progress"]')
        .forEach((btn) => {
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            if (id) {
              console.log("🔄 Opening progress popup for project:", id);
              this.#openProgressPopup(id);
            }
          });
        });

      grid.querySelectorAll('[data-action="view-details"]').forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const id = btn.dataset.id;
          if (id) {
            console.log("📋 Opening drawer for project:", id);
            this.#openDrawer(id);
          }
        });
      });

      grid.querySelectorAll('[data-action="complete"]').forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const id = btn.dataset.id;
          if (id) {
            this.#completeProject(id);
          }
        });
      });

      grid.querySelectorAll(".project-card-item").forEach((card) => {
        card.addEventListener("click", (e) => {
          if (e.target.closest(".card-actions")) return;
          const id = card.dataset.id;
          if (id) this.#openProgressPopup(id);
        });
      });
    }

    // ─── Dashboard ────────────────────────────────────────────
    #updateDashboard() {
      const projects = Array.isArray(this.#state.projects)
        ? this.#state.projects
        : [];
      const active = projects.filter(
        (p) => (p.status || "").toLowerCase() !== "completed",
      ).length;
      const inProd = projects.filter((p) =>
        ["active", "in_progress"].includes((p.status || "").toLowerCase()),
      ).length;
      const completed = projects.filter(
        (p) => (p.status || "").toLowerCase() === "completed",
      ).length;
      const revenue = projects.reduce(
        (sum, p) => sum + (parseFloat(p.estimated_revenue) || 0),
        0,
      );

      this.#setText("activeCount", active);
      this.#setText("prodCount", inProd);
      this.#setText("completedCount", completed);
      this.#setText("revenueTotal", this.#formatCurrency(revenue));
    }

    // ─── Drawer ───────────────────────────────────────────────
    async #openDrawer(id) {
      const drawer = this.#dom.projectDrawer;
      if (!drawer) return;
      this.#state.currentProjectId = id;
      drawer.classList.add("active");

      this.#resetDrawerFields();

      try {
        const data = await this.#fetchJSON(`${API_BASE}/${id}`);
        const project = data.data?.project || data.data;
        this.#populateDrawer(project, data.data);

        await Promise.all([
          this.#loadMaterialUsageList(id),
          this.#loadLaborList(id),
          this.#loadMaterialsDropdown(),
          this.#loadLaborOptions(),
          this.#loadActivities(id),
        ]);
      } catch (err) {
        console.error(err);
        this.#showToast("Could not load project details", "error");
        this.#closeDrawer();
      }
    }

    #closeDrawer() {
      const drawer = this.#dom.projectDrawer;
      if (drawer) drawer.classList.remove("active");
      this.#state.currentProjectId = null;
    }

    #resetDrawerFields() {
      const fields = [
        "drawerTitle",
        "drawerCustomer",
        "drawerPhone",
        "drawerEmail",
        "drawerStatus",
        "drawerPriority",
        "drawerProgressFill",
        "drawerProgressText",
        "drawerBrand",
        "drawerModel",
        "drawerYear",
        "drawerPlate",
        "drawerStartDate",
        "drawerDelivery",
        "drawerActualDelivery",
        "drawerCompletedAt",
        "drawerDuration",
        "drawerTimelineStatus",
        "drawerNotes",
        "drawerEstCost",
        "drawerActualCost",
        "drawerEstRevenue",
        "drawerActualRevenue",
        "drawerDeposit",
        "drawerDepositPaid",
        "drawerProfit",
        "drawerMargin",
      ];
      fields.forEach((id) => {
        const el = this.#dom[id];
        if (el) {
          if (id === "drawerStatus")
            el.innerHTML = '<span class="status-badge">-</span>';
          else if (id === "drawerPriority")
            el.innerHTML = '<span class="priority-badge">-</span>';
          else if (id === "drawerProgressFill") el.style.width = "0%";
          else if (id === "drawerProgressText") el.textContent = "0%";
          else if (id === "drawerTitle") el.textContent = "Loading...";
          else el.textContent = "-";
        }
      });
      if (this.#dom.drawerMaterialsList)
        this.#dom.drawerMaterialsList.innerHTML =
          '<p style="color:var(--text-muted);">Loading...</p>';
      if (this.#dom.laborList)
        this.#dom.laborList.innerHTML =
          '<p style="color:var(--text-muted);">Loading...</p>';
      if (this.#dom.timelineMilestones)
        this.#dom.timelineMilestones.innerHTML = "";
      if (this.#dom.drawerActivities)
        this.#dom.drawerActivities.innerHTML =
          '<p style="color:var(--text-muted);">Loading...</p>';
    }

    #populateDrawer(project, fullData) {
      const setText = (id, val) => {
        const el = this.#dom[id];
        if (el) el.textContent = val ?? "-";
      };
      const setHTML = (id, html) => {
        const el = this.#dom[id];
        if (el) el.innerHTML = html ?? "-";
      };

      setText("drawerTitle", project.name);
      setText("drawerCustomer", project.customer_name);
      setText("drawerPhone", project.customer_phone || "-");
      setText("drawerEmail", project.customer_email || "-");
      const statusKey = (project.status || "").toLowerCase();
      setHTML(
        "drawerStatus",
        `<span class="status-badge ${statusKey}">${this.#statusLabel(project.status)}</span>`,
      );
      const priorityKey = (project.priority || "medium").toLowerCase();
      setHTML(
        "drawerPriority",
        `<span class="priority-badge ${priorityKey}">${this.#priorityLabel(project.priority)}</span>`,
      );

      const progress = project.progress || 0;
      const fill = this.#dom.drawerProgressFill;
      if (fill) fill.style.width = progress + "%";
      setText("drawerProgressText", progress + "%");
      setText("drawerBrand", project.vehicle_brand || "-");
      setText("drawerModel", project.vehicle_model || "-");
      setText("drawerYear", project.vehicle_year || "-");
      setText("drawerPlate", project.vehicle_license_plate || "-");

      const financial = fullData?.financial_summary || {};
      setText(
        "drawerEstCost",
        this.#formatCurrency(project.estimated_cost || 0),
      );
      setText(
        "drawerActualCost",
        this.#formatCurrency(financial.actual_cost || project.actual_cost || 0),
      );
      setText(
        "drawerEstRevenue",
        this.#formatCurrency(project.estimated_revenue || 0),
      );
      setText(
        "drawerActualRevenue",
        this.#formatCurrency(
          financial.actual_revenue || project.actual_revenue || 0,
        ),
      );
      setText(
        "drawerDeposit",
        this.#formatCurrency(project.deposit_amount || 0),
      );
      setText(
        "drawerDepositPaid",
        project.deposit_paid ? "✅ Paid" : "❌ Not Paid",
      );
      setText("drawerProfit", this.#formatCurrency(financial.profit || 0));
      setText("drawerMargin", (financial.margin || 0) + "%");

      const startDate = project.project_start_date
        ? new Date(project.project_start_date)
        : null;
      const targetDate = project.project_target_delivery
        ? new Date(project.project_target_delivery)
        : null;
      const actualDate = project.actual_delivery_date
        ? new Date(project.actual_delivery_date)
        : null;
      const completedDate = project.completed_at
        ? new Date(project.completed_at)
        : null;
      const now = new Date();

      setText(
        "drawerStartDate",
        startDate ? startDate.toLocaleDateString() : "-",
      );
      setText(
        "drawerDelivery",
        targetDate ? targetDate.toLocaleDateString() : "-",
      );
      setText(
        "drawerActualDelivery",
        actualDate ? actualDate.toLocaleDateString() : "-",
      );
      setText(
        "drawerCompletedAt",
        completedDate ? completedDate.toLocaleDateString() : "-",
      );

      let durationText = "-";
      let timelineStatusText = "-";
      if (startDate && targetDate) {
        const days = Math.ceil(
          (targetDate - startDate) / (1000 * 60 * 60 * 24),
        );
        durationText = `${days} days`;
        const daysRemaining = Math.ceil(
          (targetDate - now) / (1000 * 60 * 60 * 24),
        );
        if ((project.status || "").toLowerCase() === "completed") {
          timelineStatusText = "✅ Completed";
        } else if (now > targetDate) {
          timelineStatusText = `⚠️ Overdue by ${Math.abs(daysRemaining)} days`;
        } else if (daysRemaining <= 0) {
          timelineStatusText = "🎯 Due today!";
        } else if (daysRemaining <= 3) {
          timelineStatusText = `⏰ ${daysRemaining} days remaining (urgent)`;
        } else {
          timelineStatusText = `✅ ${daysRemaining} days remaining`;
        }
      } else if (startDate && !targetDate) {
        const daysPassed = Math.ceil((now - startDate) / (1000 * 60 * 60 * 24));
        durationText = "No target set";
        timelineStatusText = `Started ${daysPassed} days ago`;
      } else {
        durationText = "Dates not set";
      }
      setText("drawerDuration", durationText);
      setText("drawerTimelineStatus", timelineStatusText);

      setText("drawerNotes", project.notes || "-");
      if (this.#dom.timelineNote)
        this.#dom.timelineNote.textContent = project.notes || "-";

      this.#updateTimelineMilestones(progress);
    }

    #updateTimelineMilestones(progress) {
      const container = this.#dom.timelineMilestones;
      if (!container) return;
      let html = "";
      MILESTONE_STAGES.forEach((stage, index) => {
        let status = "pending";
        if (progress >= stage.threshold) status = "done";
        else if (
          index === 0 ||
          progress >= (MILESTONE_STAGES[index - 1]?.threshold || 0)
        )
          status = "active";
        const icon =
          status === "done" ? "✅" : status === "active" ? "⏳" : "⬜";
        html += `<div class="milestone-item ${status}">${icon} ${stage.label}</div>`;
      });
      container.innerHTML = html;
    }

    // ─── Activities ───────────────────────────────────────────
    async #loadActivities(projectId) {
      const container = this.#dom.drawerActivities;
      if (!container) return;
      try {
        const data = await this.#fetchJSON(
          `${API_BASE}/${projectId}/activities`,
        );
        const items = data.data || [];
        if (items.length === 0) {
          container.innerHTML =
            '<p style="color:var(--text-muted);">No activities recorded.</p>';
          return;
        }
        container.innerHTML = items
          .map(
            (act) => `
                    <div style="padding: 6px 0; border-bottom: 1px solid var(--border-color, #2d2d44);">
                        <div style="font-weight: 500;">${this.#escapeHtml(act.activity)}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted, #94a3b8);">
                            ${act.performed_by || "system"} • ${new Date(act.created_at).toLocaleString()}
                            ${act.activity_type ? `<span style="background: rgba(255,255,255,0.05); padding: 0 6px; border-radius: 4px;">${act.activity_type}</span>` : ""}
                        </div>
                    </div>
                `,
          )
          .join("");
      } catch (err) {
        container.innerHTML =
          '<p style="color:var(--text-muted);">No activities recorded.</p>';
      }
    }

    // ─── Load Materials ──────────────────────────────────────
    async #loadMaterialsDropdown() {
      try {
        const data = await this.#fetchJSON(`${INVENTORY_API}/`);
        const select = this.#dom.materialSelect;
        const unitSelect = this.#dom.materialUnit; // 🔥 Sekarang tidak undefined

        if (!select) {
          console.warn("materialSelect not found");
          return;
        }

        const items = data.data?.items || data.data || [];
        this.#state.materialOptions = items;
        select.innerHTML = '<option value="">Select Material</option>';

        items.forEach((item) => {
          const opt = document.createElement("option");
          opt.value = item.id;

          const stock = parseFloat(item.current_stock) || 0;
          const unitDisplay = item.unit || "pcs";

          let stockDisplay;
          if (unitDisplay === "ml" || unitDisplay === "liter") {
            stockDisplay = stock.toFixed(2);
          } else if (unitDisplay === "gram" || unitDisplay === "kg") {
            stockDisplay = stock.toFixed(2);
          } else {
            stockDisplay = Math.floor(stock);
          }

          opt.textContent = `${item.name} (${stockDisplay} ${unitDisplay})`;
          opt.dataset.unit = unitDisplay;
          opt.dataset.baseUnit = item.base_unit || unitDisplay;
          opt.dataset.conversionFactor = item.conversion_factor || 1;
          opt.dataset.stock = stock;
          opt.disabled = stock <= 0;
          select.appendChild(opt);
        });

        // 🔥 Set default unit berdasarkan material yang dipilih
        if (unitSelect) {
          const firstOption = select.options[1];
          if (firstOption) {
            const unit = firstOption.dataset?.unit || "pcs";
            if (unit === "liter" || unit === "kg") {
              unitSelect.value = unit === "liter" ? "ml" : "gram";
            } else {
              unitSelect.value = unit;
            }
          }

          // Event listener untuk change material
          select.addEventListener("change", () => {
            const selected = select.options[select.selectedIndex];
            const unit = selected?.dataset?.unit || "pcs";
            if (unitSelect) {
              if (unit === "liter") {
                unitSelect.value = "ml";
              } else if (unit === "kg") {
                unitSelect.value = "gram";
              } else {
                unitSelect.value = unit;
              }
            }
            // Update placeholder
            const qtyInput = this.#dom.materialQty;
            if (qtyInput) {
              const displayUnit = unitSelect?.value || unit;
              qtyInput.placeholder = `Qty (${displayUnit})`;
              qtyInput.step =
                displayUnit === "ml" || displayUnit === "gram" ? "1" : "0.1";
              qtyInput.min =
                displayUnit === "ml" || displayUnit === "gram" ? "1" : "0.01";
            }
          });

          // Trigger initial change
          if (select.options.length > 1) {
            select.dispatchEvent(new Event("change"));
          }
        }
      } catch (err) {
        console.warn("Failed to load materials dropdown:", err);
      }
    }

    async #loadMaterialUsageList(projectId) {
      const container = this.#dom.drawerMaterialsList;
      if (!container) return;
      try {
        const data = await this.#fetchJSON(
          `${INVENTORY_API}/usage/project/${projectId}`,
        );
        const items = data.data || [];
        if (items.length === 0) {
          container.innerHTML =
            '<p style="color:var(--text-muted);">No materials consumed yet.</p>';
          return;
        }
        container.innerHTML = items
          .map((item) => {
            // 🔥 FIX: Parse quantity ke number
            const qty = parseFloat(item.quantity) || 0;
            const unit = item.unit || "pcs";

            // 🔥 FIX: Format quantity dengan presisi yang sesuai
            let displayQty;
            if (unit === "ml" || unit === "liter") {
              displayQty = qty.toFixed(2);
            } else if (unit === "gram" || unit === "kg") {
              displayQty = qty.toFixed(2);
            } else {
              displayQty = qty % 1 === 0 ? Math.floor(qty) : qty.toFixed(2);
            }

            return `
          <div>
            <span>${this.#escapeHtml(item.item_name || "Unknown")}</span>
            <span>${displayQty} ${unit}</span>
            <span>${this.#formatCurrency(item.total_cost || 0)}</span>
            <button class="btn-delete-item" data-type="material" data-id="${item.usage_id || item.id}" data-project="${projectId}" title="Hapus pemakaian material ini">×</button>
          </div>
        `;
          })
          .join("");
      } catch (err) {
        container.innerHTML =
          '<p style="color:var(--text-muted);">No materials consumed yet.</p>';
      }
    }

    // ─── Consume Material ──────────────────────────────────────
    async #consumeMaterial(e) {
      e.preventDefault();
      const projectId = this.#state.currentProjectId;
      if (!projectId) return this.#showToast("No project selected", "error");

      const select = this.#dom.materialSelect;
      const qtyInput = this.#dom.materialQty;
      const unitSelect = this.#dom.materialUnit; // 🔥 Sekarang tidak undefined

      if (!select || !qtyInput) {
        return this.#showToast("Material form not ready", "error");
      }

      const itemId = select.value;
      const selectedOption = select.options[select.selectedIndex];
      const itemUnit = selectedOption?.dataset?.unit || "pcs";

      // 🔥 Ambil unit yang dipilih user, fallback ke 'ml'
      const selectedUnit = unitSelect?.value || "ml";
      const qty = parseFloat(qtyInput.value);

      if (!itemId) return this.#showToast("Select a material", "error");
      if (!qty || qty <= 0) {
        return this.#showToast("Enter valid quantity", "error");
      }

      // 🔥 DEBUG: Log untuk debugging
      console.log("🔍 Consuming material:", {
        itemId,
        qty,
        selectedUnit,
        itemUnit,
        unitSelectValue: unitSelect?.value,
      });

      // 🔥 Validasi untuk unit ml
      if (selectedUnit === "ml" && qty > 1000) {
        if (
          !confirm(
            `Anda memasukkan ${qty} ml (${(qty / 1000).toFixed(2)} liter). Apakah Anda yakin?`,
          )
        ) {
          return;
        }
      }

      const selectedItem = this.#state.materialOptions.find(
        (i) => i.id === itemId,
      );

      // 🔥 Konversi ke unit item
      let qtyInItemUnit = qty;
      let conversionNote = "";

      if (selectedUnit === "ml" && itemUnit === "liter") {
        qtyInItemUnit = qty / 1000;
        conversionNote = ` (${qty} ml = ${qtyInItemUnit.toFixed(3)} liter)`;
      } else if (selectedUnit === "liter" && itemUnit === "ml") {
        qtyInItemUnit = qty * 1000;
        conversionNote = ` (${qty} liter = ${qtyInItemUnit} ml)`;
      } else if (selectedUnit === "gram" && itemUnit === "kg") {
        qtyInItemUnit = qty / 1000;
        conversionNote = ` (${qty} gram = ${qtyInItemUnit.toFixed(3)} kg)`;
      } else if (selectedUnit === "kg" && itemUnit === "gram") {
        qtyInItemUnit = qty * 1000;
        conversionNote = ` (${qty} kg = ${qtyInItemUnit} gram)`;
      } else if (selectedUnit !== itemUnit) {
        this.#showToast(
          `Unit '${selectedUnit}' tidak kompatibel dengan item unit '${itemUnit}'`,
          "error",
        );
        return;
      }

      console.log(
        `🔍 Converted: ${qty} ${selectedUnit} -> ${qtyInItemUnit} ${itemUnit}${conversionNote}`,
      );

      // 🔥 Cek stock
      const currentStock = parseFloat(selectedItem?.current_stock) || 0;

      if (selectedItem && currentStock < qtyInItemUnit) {
        const stockDisplay =
          currentStock < 1 ? currentStock.toFixed(3) : Math.floor(currentStock);
        return this.#showToast(
          `Stok tidak mencukupi. Tersedia: ${stockDisplay} ${itemUnit}${conversionNote}`,
          "error",
        );
      }

      try {
        const payload = {
          project_id: projectId,
          item_id: itemId,
          quantity: qty,
          unit: selectedUnit,
          note: conversionNote ? `Konversi: ${conversionNote}` : undefined,
        };

        console.log("📤 Sending payload:", payload);

        await this.#fetchJSON(`${INVENTORY_API}/usage`, {
          method: "POST",
          body: JSON.stringify(payload),
        });

        const qtyDisplay = qty < 1 ? qty.toFixed(2) : Math.floor(qty);
        this.#showToast(
          `Material consumed ✅ (${qtyDisplay} ${selectedUnit})${conversionNote}`,
        );

        await this.#loadMaterialsDropdown();
        await this.#loadMaterialUsageList(projectId);
        qtyInput.value = "";
      } catch (err) {
        console.error("❌ Consume material error:", err);
        this.#showToast(err.message || "Failed to consume material", "error");
      }
    }

    async #deleteMaterial(usageId, projectId) {
      if (!confirm("Hapus pemakaian material ini?")) return;
      try {
        await this.#fetchJSON(`${INVENTORY_API}/usage/${usageId}`, {
          method: "DELETE",
        });
        this.#showToast("Material usage deleted");
        await this.#loadMaterialUsageList(projectId);
        await this.#loadMaterialsDropdown();
      } catch (err) {
        this.#showToast(err.message || "Gagal hapus material", "error");
      }
    }

    // ─── Labor ────────────────────────────────────────────────
    async #loadLaborOptions() {
      try {
        const select = this.#dom.laborTypeSelect;
        if (!select) return;

        let url = `${PRICE_LIST_API}/?category=labor&active_only=true&limit=100`;
        let res = await fetch(url);
        let data = await res.json();

        if (!data.data || data.data.length === 0) {
          res = await fetch(`${PRICE_LIST_API}/?active_only=true&limit=100`);
          data = await res.json();
        }

        const items = data.data || [];
        this.#state.laborOptions = items;

        select.innerHTML = '<option value="">Pilih Labor</option>';

        const laborItems = items.filter(
          (item) =>
            item.category?.toLowerCase() === "labor" ||
            item.name?.toLowerCase().includes("labor"),
        );

        const displayItems = laborItems.length > 0 ? laborItems : items;

        displayItems.forEach((item) => {
          const opt = document.createElement("option");
          opt.value = item.name || item.id;
          const price = parseFloat(item.price) || 0;
          const unit = item.unit || "jam";
          opt.textContent = `${item.name} (${this.#formatCurrency(price)} / ${unit})`;
          select.appendChild(opt);
        });

        if (displayItems.length === 0) {
          select.innerHTML = '<option value="">Tidak ada data labor</option>';
        }
      } catch (err) {
        console.warn("Gagal load labor options:", err);
        const select = this.#dom.laborTypeSelect;
        if (select) {
          select.innerHTML = '<option value="">Gagal load data</option>';
        }
      }
    }

    async #loadLaborList(projectId) {
      const container = this.#dom.laborList;
      if (!container) return;
      try {
        const data = await this.#fetchJSON(`${API_BASE}/${projectId}/labor`);
        const items = data.data || [];
        if (items.length === 0) {
          container.innerHTML =
            '<p style="color:var(--text-muted);">No labor recorded.</p>';
          return;
        }
        container.innerHTML = items
          .map(
            (item) => `
                    <div>
                        <span>${this.#escapeHtml(item.labor_type)}</span>
                        <span>${item.hours} jam @ ${this.#formatCurrency(item.rate_per_hour)}</span>
                        <span>${this.#formatCurrency(item.total_cost)}</span>
                        <button class="btn-delete-item" data-type="labor" data-id="${item.id}" data-project="${projectId}" title="Hapus data labor ini">×</button>
                    </div>
                `,
          )
          .join("");
      } catch (err) {
        container.innerHTML =
          '<p style="color:var(--text-muted);">No labor recorded.</p>';
      }
    }

    async #addLabor(e) {
      e.preventDefault();
      const projectId = this.#state.currentProjectId;
      if (!projectId) return this.#showToast("No project selected", "error");
      const select = this.#dom.laborTypeSelect;
      const hoursInput = this.#dom.laborHours;
      const rateInput = this.#dom.laborRate;

      const laborType = select?.value;
      const hours = parseFloat(hoursInput?.value);
      const rate = rateInput?.value ? parseFloat(rateInput.value) : null;

      if (!laborType) return this.#showToast("Pilih jenis labor", "error");
      if (!hours || hours < 0.5)
        return this.#showToast(
          "Masukkan jam kerja yang valid (min 0.5)",
          "error",
        );

      const payload = { labor_type: laborType, hours };
      if (rate && rate > 0) payload.rate_per_hour = rate;

      try {
        await this.#fetchJSON(`${API_BASE}/${projectId}/labor`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
        this.#showToast("Labor added ✅");
        await this.#loadLaborList(projectId);
        hoursInput.value = "";
        if (rateInput) rateInput.value = "";
      } catch (err) {
        this.#showToast(err.message || "Gagal menambah labor", "error");
      }
    }

    async #deleteLabor(laborId, projectId) {
      if (!confirm("Hapus data labor ini?")) return;
      try {
        await this.#fetchJSON(`${API_BASE}/${projectId}/labor/${laborId}`, {
          method: "DELETE",
        });
        this.#showToast("Labor deleted");
        await this.#loadLaborList(projectId);
      } catch (err) {
        this.#showToast(err.message || "Gagal hapus labor", "error");
      }
    }

    // ─── Progress Popup ──────────────────────────────────────
    #openProgressPopup(id) {
      const popup = this.#dom.progressPopup;
      if (!popup) return;

      const projects = Array.isArray(this.#state.projects)
        ? this.#state.projects
        : [];
      const proj = projects.find((p) => p.id === id);
      if (!proj) {
        this.#showToast("Project not found", "error");
        return;
      }

      console.log("📊 Opening progress popup for:", proj.name);

      if (this.#dom.progressPopupTitle)
        this.#dom.progressPopupTitle.textContent = `Update Progress: ${proj.name}`;
      if (this.#dom.progressPopupSubtitle) {
        this.#dom.progressPopupSubtitle.textContent = `${proj.customer_name} • ${proj.vehicle_brand} ${proj.vehicle_model}`;
      }

      const slider = this.#dom.progressPopupSlider;
      const valueDisplay = this.#dom.progressPopupValue;
      const note = this.#dom.progressPopupNote;
      const milestones = this.#dom.progressPopupMilestones;
      const markComplete = this.#dom.markCompleteCheckbox;

      const progress = proj.progress || 0;
      if (slider) {
        slider.value = progress;
        // Update background gradient
        slider.style.background = `linear-gradient(90deg, var(--accent, #ff7b2c) ${progress}%, rgba(255,255,255,0.08) ${progress}%)`;
      }
      if (valueDisplay) valueDisplay.textContent = progress;
      if (note) note.value = proj.notes || "";

      // Milestones
      const milestoneItems = this.#getMilestones(proj.status, progress);
      if (milestones) {
        milestones.innerHTML = milestoneItems
          .map(
            (m) =>
              `<div class="milestone-item ${m.status}">${m.status === "done" ? "✅" : m.status === "active" ? "⏳" : "⬜"} ${this.#escapeHtml(m.label)}</div>`,
          )
          .join("");
      }

      const isCompleted = (proj.status || "").toLowerCase() === "completed";
      if (markComplete) {
        if (isCompleted) {
          markComplete.style.display = "flex";
          markComplete.checked = true;
          markComplete.disabled = true;
        } else if (progress === 100) {
          markComplete.style.display = "flex";
          markComplete.checked = true;
          markComplete.disabled = false;
        } else {
          markComplete.style.display = "none";
          markComplete.checked = false;
          markComplete.disabled = false;
        }
      }

      this.#state.currentProjectId = id;
      popup.classList.add("active");
      document.body.style.overflow = "hidden";
    }

    #closeProgressPopup() {
      const popup = this.#dom.progressPopup;
      if (popup) popup.classList.remove("active");
      document.body.style.overflow = "";
      this.#state.currentProjectId = null;
    }

    #updateMilestoneHighlights(progress) {
      const container = this.#dom.progressPopupMilestones;
      if (!container) return;
      const items = container.querySelectorAll(".milestone-item");
      const total = items.length;
      const doneCount = Math.floor((progress / 100) * total);
      items.forEach((item, index) => {
        const label = item.textContent.replace(/[✅⏳⬜]\s*/, "");
        if (index < doneCount) {
          item.className = "milestone-item done";
          item.innerHTML = "✅ " + label;
        } else if (index === doneCount) {
          item.className = "milestone-item active";
          item.innerHTML = "⏳ " + label;
        } else {
          item.className = "milestone-item pending";
          item.innerHTML = "⬜ " + label;
        }
      });
    }

    #getMilestones(status, progress) {
      const allStages = [
        { key: "inquiry", label: "Inquiry Approved" },
        { key: "parts", label: "Parts Ordered" },
        { key: "disassembly", label: "Disassembly" },
        { key: "paint_prep", label: "Paint Preparation" },
        { key: "painting", label: "Painting" },
        { key: "assembly", label: "Assembly" },
        { key: "qc", label: "Quality Check" },
        { key: "delivery", label: "Ready for Delivery" },
      ];
      const statusMap = {
        draft: ["inquiry"],
        active: ["inquiry"],
        in_progress: ["inquiry", "parts"],
        on_hold: ["inquiry", "parts"],
        completed: allStages.map((s) => s.key),
        cancelled: [],
        preparation: ["inquiry", "parts"],
        painting: ["inquiry", "parts", "disassembly", "paint_prep"],
        assembly: ["inquiry", "parts", "disassembly", "paint_prep", "painting"],
        new: ["inquiry"],
        quoted: ["inquiry"],
        approved: ["inquiry"],
      };
      const statusLower = (status || "").toLowerCase();
      const completedKeys = statusMap[statusLower] || ["inquiry"];
      return allStages.map((stage, idx) => {
        const isDone = completedKeys.includes(stage.key);
        const isActive = !isDone && completedKeys.length === idx;
        return {
          label: stage.label,
          status: isDone ? "done" : isActive ? "active" : "pending",
        };
      });
    }

    // ─── Save Progress ──────────────────────────────────────
    async #saveProgressPopup() {
      const projectId = this.#state.currentProjectId;
      if (!projectId) {
        this.#showToast("No project selected", "error");
        return;
      }

      const progress = parseInt(this.#dom.progressPopupSlider?.value || 0, 10);
      const note = this.#dom.progressPopupNote?.value.trim() || "";
      const markComplete = this.#dom.markCompleteCheckbox?.checked || false;

      console.log("💾 Saving progress:", {
        projectId,
        progress,
        note,
        markComplete,
      });

      const payload = { progress };
      if (note) payload.notes = note;
      if (markComplete && progress === 100) {
        payload.status = "completed";
        payload.completed_at = new Date().toISOString();
      }

      const submitBtn = this.#dom.saveProgressBtn;
      const originalText = submitBtn?.textContent || "Save";
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Saving...";
      }

      try {
        const response = await this.#fetchJSON(`${API_BASE}/${projectId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });

        if (response?.success !== false) {
          this.#showToast("✅ Progress updated successfully!");
          this.#closeProgressPopup();
          await this.#loadProjects();

          // Refresh drawer if open
          if (
            this.#dom.projectDrawer?.classList.contains("active") &&
            this.#state.currentProjectId === projectId
          ) {
            await this.#openDrawer(projectId);
          }
        } else {
          throw new Error(response?.message || "Failed to update progress");
        }
      } catch (err) {
        console.error("Save progress error:", err);
        this.#showToast(
          `❌ ${err.message || "Failed to update progress"}`,
          "error",
        );
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    }

    // ─── Complete Project ─────────────────────────────────────
    async #completeProject(id) {
      if (
        !confirm(
          "✅ Tandai project ini sebagai selesai?\n\nProject akan diarsipkan dan tidak bisa diubah lagi.",
        )
      )
        return;
      try {
        await this.#fetchJSON(`${API_BASE}/${id}/complete`, { method: "POST" });
        this.#showToast("🎉 Project completed successfully!");
        await this.#loadProjects();
      } catch (err) {
        this.#showToast(err.message || "Failed to complete project", "error");
      }
    }

    // ─── Modal (Create / Edit) ──────────────────────────────
    #openModal(editData = null) {
      const modal = this.#dom.projectModal;
      if (!modal) return;
      const isEdit = !!editData;
      if (isEdit) {
        this.#dom.modalTitle.textContent = "Edit Project";
        this.#dom.modalSubtitle.textContent = "Update project details";
        this.#dom.submitProjectBtn.textContent = "Update Project";
        this.#dom.editProjectId.value = editData.id;
        const fieldMap = {
          projectName: "name",
          customerName: "customer_name",
          customerPhone: "customer_phone",
          customerEmail: "customer_email",
          projectStatus: "status",
          projectPriority: "priority",
          progressSliderForm: "progress",
          vehicleBrand: "vehicle_brand",
          vehicleModel: "vehicle_model",
          vehicleYear: "vehicle_year",
          licensePlate: "vehicle_license_plate",
          estimatedCost: "estimated_cost",
          estimatedRevenue: "estimated_revenue",
          startDate: "project_start_date",
          targetDelivery: "project_target_delivery",
          projectNotes: "notes",
        };
        Object.keys(fieldMap).forEach((elId) => {
          const el = document.getElementById(elId);
          const key = fieldMap[elId];
          if (el && editData[key] !== undefined) {
            el.value = editData[key];
          }
        });
        const slider = document.getElementById("progressSliderForm");
        const display = document.getElementById("progressDisplay");
        if (slider && display) {
          display.textContent = slider.value;
          slider.style.background = `linear-gradient(90deg, var(--accent, #ff7b2c) ${slider.value}%, rgba(255,255,255,0.08) ${slider.value}%)`;
        }
      } else {
        this.#dom.modalTitle.textContent = "Create New Project";
        this.#dom.modalSubtitle.textContent =
          "Register workshop project and production schedule";
        this.#dom.submitProjectBtn.textContent = "Create Project";
        this.#dom.projectForm.reset();
        this.#dom.editProjectId.value = "";
        const display = document.getElementById("progressDisplay");
        const slider = document.getElementById("progressSliderForm");
        if (slider) {
          slider.value = 0;
          slider.style.background = `linear-gradient(90deg, var(--accent, #ff7b2c) 0%, rgba(255,255,255,0.08) 0%)`;
        }
        if (display) display.textContent = "0";
      }
      modal.classList.add("active");
      document.body.style.overflow = "hidden";
    }

    #closeModal() {
      const modal = this.#dom.projectModal;
      if (modal) modal.classList.remove("active");
      document.body.style.overflow = "";
    }

    async #handleFormSubmit(e) {
      e.preventDefault();
      if (this.#state.isSubmitting) return;
      this.#state.isSubmitting = true;

      const getVal = (id) => document.getElementById(id)?.value || "";
      const editId = this.#dom.editProjectId.value;
      const payload = {
        name: getVal("projectName").trim(),
        customer_name: getVal("customerName").trim(),
        customer_phone: getVal("customerPhone").trim() || null,
        customer_email: getVal("customerEmail").trim() || null,
        status: getVal("projectStatus"),
        priority: getVal("projectPriority") || "medium",
        progress: parseInt(getVal("progressSliderForm"), 10) || 0,
        vehicle_brand: getVal("vehicleBrand").trim(),
        vehicle_model: getVal("vehicleModel").trim(),
        vehicle_year: parseInt(getVal("vehicleYear")) || null,
        vehicle_license_plate: getVal("licensePlate").trim() || null,
        estimated_cost: parseFloat(getVal("estimatedCost")) || 0,
        estimated_revenue: parseFloat(getVal("estimatedRevenue")) || 0,
        project_start_date: getVal("startDate") || null,
        project_target_delivery: getVal("targetDelivery") || null,
        notes: getVal("projectNotes").trim() || null,
      };

      try {
        let url = `${API_BASE}/`;
        let method = "POST";
        if (editId) {
          url = `${API_BASE}/${editId}`;
          method = "PATCH";
        }
        await this.#fetchJSON(url, { method, body: JSON.stringify(payload) });
        this.#showToast(editId ? "Project updated" : "Project created");
        this.#closeModal();
        await this.#loadProjects();
      } catch (err) {
        this.#showToast(
          err.message || (editId ? "Update failed" : "Create failed"),
          "error",
        );
      } finally {
        this.#state.isSubmitting = false;
      }
    }

    // ─── Helpers ──────────────────────────────────────────────
    #formatCurrency(amount) {
      if (amount === undefined || amount === null) return "Rp 0";
      return new Intl.NumberFormat("id-ID", {
        style: "currency",
        currency: "IDR",
        maximumFractionDigits: 0,
      }).format(amount || 0);
    }

    #escapeHtml(str) {
      if (!str) return "";
      return String(str).replace(/[&<>]/g, (m) => {
        if (m === "&") return "&amp;";
        if (m === "<") return "&lt;";
        if (m === ">") return "&gt;";
        return m;
      });
    }

    #statusLabel(status) {
      const key = (status || "").toLowerCase();
      return STATUS_LABELS[key] || status || "-";
    }

    #priorityLabel(priority) {
      const key = (priority || "").toLowerCase();
      return PRIORITY_LABELS[key] || priority || "Medium";
    }

    #setText(id, value) {
      const el = this.#dom[id];
      if (el) el.textContent = value;
    }

    #showToast(message, type = "success") {
      if (typeof window.showToast === "function") {
        window.showToast(message, type);
        return;
      }
      const container = document.getElementById("toastContainer");
      if (!container) return;
      const toast = document.createElement("div");
      toast.className = `toast ${type}`;
      toast.style.cssText = `
                padding: 12px 18px;
                border-radius: 12px;
                background: ${type === "error" ? "#7f1d1d" : "#111827"};
                color: #fff;
                border: 1px solid rgba(255,255,255,0.08);
                box-shadow: 0 15px 40px rgba(0,0,0,0.3);
                transform: translateX(100%);
                opacity: 0;
                transition: all 0.3s ease;
            `;
      toast.textContent = message;
      container.appendChild(toast);
      requestAnimationFrame(() => {
        toast.style.transform = "translateX(0)";
        toast.style.opacity = "1";
      });
      setTimeout(() => {
        toast.style.transform = "translateX(100%)";
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
      }, 3000);
    }
  }

  // ─── Instantiate ─────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    new ProjectManager();
  });
})();
