/**
 * NOCTRA Project Management
 * Card view with Tabbed Drawer, Progress Popup, Material & Labor management.
 *
 * Refactored as modular class with clear separation of concerns.
 * Designed for easy extension and maintenance.
 */
(function () {
  "use strict";

  // ─── Constants ──────────────────────────────────────────────
  const API_BASE = "/api/projects";
  const STATUS_LABELS = {
    new: "New",
    quoted: "Quoted",
    approved: "Approved",
    preparation: "Preparation",
    painting: "Painting",
    assembly: "Assembly",
    completed: "Completed",
  };

  const MILESTONE_STAGES = [
    { key: "disassembly", label: "Disassembly", threshold: 20 },
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
      currentSearch: "",
      currentProjectId: null,
      isSubmitting: false,
      isLoading: false,
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
        "drawerStatus",
        "drawerProgressFill",
        "drawerProgressText",
        "drawerBrand",
        "drawerModel",
        "drawerPlate",
        "drawerStartDate",
        "drawerDelivery",
        "drawerDuration",
        "drawerTimelineStatus",
        "drawerNotes",
        "drawerMaterialsList",
        "laborList",
        "materialSelect",
        "materialQty",
        "consumeMaterialBtn",
        "laborTypeSelect",
        "laborHours",
        "addLaborBtn",
        "timelineMilestones",
        "timelineNote",
        "exportBtn",
      ];
      const refs = {};
      ids.forEach((id) => {
        refs[id] = document.getElementById(id);
      });
      // Tabs
      refs.tabButtons = document.querySelectorAll(".tab-btn");
      refs.tabPanels = {
        overview: document.getElementById("tab-overview"),
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
                .status-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; }
                .status-badge.new { background: rgba(59,130,246,0.15); color: #3b82f6; }
                .status-badge.quoted { background: rgba(245,158,11,0.15); color: #f59e0b; }
                .status-badge.approved { background: rgba(16,185,129,0.15); color: #10b981; }
                .status-badge.preparation { background: rgba(139,92,246,0.15); color: #8b5cf6; }
                .status-badge.painting { background: rgba(236,72,153,0.15); color: #ec4899; }
                .status-badge.assembly { background: rgba(14,165,233,0.15); color: #0ea5e9; }
                .status-badge.completed { background: rgba(34,197,94,0.15); color: #22c55e; }
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

      // Search with debounce
      projectSearch?.addEventListener("input", () => {
        clearTimeout(this.#timers.search);
        this.#timers.search = setTimeout(() => {
          this.#state.currentSearch = projectSearch.value;
          this.#renderCards();
        }, 300);
      });

      // Status filter
      statusFilter?.addEventListener("change", () => {
        this.#state.currentFilter = statusFilter.value;
        this.#renderCards();
      });

      // New project button
      newProjectBtn?.addEventListener("click", () => this.#openModal());

      // Drawer close
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

      // Modal close
      closeModal?.addEventListener("click", () => this.#closeModal());
      cancelModalBtn?.addEventListener("click", () => this.#closeModal());
      projectModal?.addEventListener("click", (e) => {
        if (e.target === projectModal) this.#closeModal();
      });

      // Modal form submit
      projectForm?.addEventListener("submit", (e) => this.#handleFormSubmit(e));

      // Progress popup close
      closeProgressPopup?.addEventListener("click", () =>
        this.#closeProgressPopup(),
      );
      cancelProgressBtn?.addEventListener("click", () =>
        this.#closeProgressPopup(),
      );
      progressPopup?.addEventListener("click", (e) => {
        if (e.target === progressPopup) this.#closeProgressPopup();
      });

      // Progress popup slider
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

      // Save progress
      saveProgressBtn?.addEventListener("click", () =>
        this.#saveProgressPopup(),
      );

      // Consume material
      consumeMaterialBtn?.addEventListener("click", (e) =>
        this.#consumeMaterial(e),
      );

      // Add labor
      addLaborBtn?.addEventListener("click", (e) => this.#addLabor(e));

      // Export
      exportBtn?.addEventListener("click", () =>
        this.#showToast("Export feature coming soon"),
      );

      // Delete items via event delegation
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

      // Progress slider in modal
      const sliderForm = document.getElementById("progressSliderForm");
      const display = document.getElementById("progressDisplay");
      if (sliderForm && display) {
        sliderForm.addEventListener("input", () => {
          display.textContent = sliderForm.value;
          sliderForm.style.background = `linear-gradient(90deg, var(--accent, #ff7b2c) ${sliderForm.value}%, rgba(255,255,255,0.08) ${sliderForm.value}%)`;
        });
        sliderForm.dispatchEvent(new Event("input"));
      }
    }

    // ─── Initialization ──────────────────────────────────────
    async #init() {
      await this.#loadProjects();
      await this.#loadLaborOptions(); // load labor options once
      // Check URL param 'open'
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
        const data = await this.#fetchJSON(`${API_BASE}/`);
        this.#state.projects = data.data || [];
        this.#renderCards();
        this.#updateDashboard();
      } catch (err) {
        console.error(err);
        this.#showToast("Failed to load projects", "error");
        if (grid)
          grid.innerHTML = `<div class="loading-placeholder">Error loading projects</div>`;
      } finally {
        this.#state.isLoading = false;
      }
    }

    // ─── Render Cards ─────────────────────────────────────────
    #renderCards() {
      const grid = this.#dom.projectCardGrid;
      if (!grid) return;

      const search = this.#state.currentSearch.toLowerCase().trim();
      const status = this.#state.currentFilter;

      const filtered = this.#state.projects.filter((proj) => {
        const matchSearch =
          !search ||
          proj.name.toLowerCase().includes(search) ||
          proj.customer_name.toLowerCase().includes(search) ||
          proj.vehicle_brand.toLowerCase().includes(search) ||
          proj.vehicle_model.toLowerCase().includes(search);
        const matchStatus = !status || proj.status === status;
        return matchSearch && matchStatus;
      });

      if (filtered.length === 0) {
        grid.innerHTML = `<div class="loading-placeholder">No projects found</div>`;
        return;
      }

      grid.innerHTML = filtered
        .map((proj) => {
          const progress = proj.progress || 0;
          const isComplete = proj.status === "completed";
          return `
                    <div class="project-card-item" data-id="${proj.id}">
                        <div class="card-header">
                            <h4>${this.#escapeHtml(proj.name)}</h4>
                            <span class="status-badge ${proj.status}">${this.#statusLabel(proj.status)}</span>
                        </div>
                        <div class="card-body">
                            <div class="customer">👤 ${this.#escapeHtml(proj.customer_name)}</div>
                            <div class="vehicle">🏍️ ${this.#escapeHtml(proj.vehicle_brand)} ${this.#escapeHtml(proj.vehicle_model)}</div>
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

      // Attach events on dynamic buttons
      grid
        .querySelectorAll('[data-action="update-progress"]')
        .forEach((btn) => {
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            this.#openProgressPopup(btn.dataset.id);
          });
        });
      grid.querySelectorAll('[data-action="view-details"]').forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.#openDrawer(btn.dataset.id);
        });
      });
      grid.querySelectorAll('[data-action="complete"]').forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.#completeProject(btn.dataset.id);
        });
      });
      // Click card -> open progress popup
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
      const projects = this.#state.projects;
      const active = projects.filter((p) => p.status !== "completed").length;
      const inProd = projects.filter((p) =>
        ["preparation", "painting", "assembly"].includes(p.status),
      ).length;
      const completed = projects.filter((p) => p.status === "completed").length;
      const revenue = projects.reduce(
        (sum, p) => sum + (p.estimated_revenue || 0),
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

      // Reset placeholders
      this.#resetDrawerFields();

      try {
        const data = await this.#fetchJSON(`${API_BASE}/${id}`);
        const project = data.data;
        this.#populateDrawer(project);
        // Load material & labor lists
        await this.#loadMaterialUsageList(id);
        await this.#loadLaborList(id);
        // Load material dropdown and labor options (refresh)
        await this.#loadMaterialsDropdown();
        await this.#loadLaborOptions(); // refresh options
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
        "drawerStatus",
        "drawerProgressFill",
        "drawerProgressText",
        "drawerBrand",
        "drawerModel",
        "drawerPlate",
        "drawerStartDate",
        "drawerDelivery",
        "drawerDuration",
        "drawerTimelineStatus",
        "drawerNotes",
      ];
      fields.forEach((id) => {
        const el = this.#dom[id];
        if (el) {
          if (id === "drawerStatus")
            el.innerHTML = '<span class="status-badge">-</span>';
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
    }

    #populateDrawer(project) {
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
      setText("drawerPhone", project.phone_number);
      setHTML(
        "drawerStatus",
        `<span class="status-badge ${project.status || ""}">${this.#statusLabel(project.status)}</span>`,
      );

      const progress = project.progress || 0;
      const fill = this.#dom.drawerProgressFill;
      if (fill) fill.style.width = progress + "%";
      setText("drawerProgressText", progress + "%");
      setText("drawerBrand", project.vehicle_brand);
      setText("drawerModel", project.vehicle_model);
      setText("drawerPlate", project.license_plate);

      // Timeline
      const startDate = project.start_date
        ? new Date(project.start_date)
        : null;
      const targetDate = project.target_delivery
        ? new Date(project.target_delivery)
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
        if (now > targetDate)
          timelineStatusText = `⚠️ Overdue by ${Math.abs(daysRemaining)} days`;
        else if (daysRemaining <= 0) timelineStatusText = "🎯 Due today!";
        else if (daysRemaining <= 3)
          timelineStatusText = `⏰ ${daysRemaining} days remaining (urgent)`;
        else timelineStatusText = `✅ ${daysRemaining} days remaining`;
      } else if (startDate && !targetDate) {
        const daysPassed = Math.ceil((now - startDate) / (1000 * 60 * 60 * 24));
        durationText = "No target set";
        timelineStatusText = `Started ${daysPassed} days ago`;
      } else {
        durationText = "Dates not set";
      }
      setText("drawerDuration", durationText);
      setText("drawerTimelineStatus", timelineStatusText);

      // Notes
      setText("drawerNotes", project.notes);
      if (this.#dom.timelineNote)
        this.#dom.timelineNote.textContent = project.notes || "-";

      // Milestones
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

    // ─── Material Usage ──────────────────────────────────────
    async #loadMaterialsDropdown() {
      try {
        const data = await this.#fetchJSON("/api/inventory/");
        const select = this.#dom.materialSelect;
        if (!select) return;
        select.innerHTML = '<option value="">Select Material</option>';
        if (data.data) {
          data.data.forEach((item) => {
            const opt = document.createElement("option");
            opt.value = item.id;
            opt.textContent = `${item.name} (${item.current_stock} ${item.unit})`;
            select.appendChild(opt);
          });
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
          `/api/inventory/usage/project/${projectId}`,
        );
        const items = data.data || [];
        if (items.length === 0) {
          container.innerHTML =
            '<p style="color:var(--text-muted);">No materials consumed yet.</p>';
          return;
        }
        container.innerHTML = items
          .map(
            (item) => `
                    <div>
                        <span>${this.#escapeHtml(item.item_name || "Unknown")}</span>
                        <span>${item.quantity} ${this.#escapeHtml(item.unit || "")}</span>
                        <span>${this.#formatCurrency(item.total_cost || item.quantity * item.cost_price)}</span>
                        <button class="btn-delete-item" data-type="material" data-id="${item.id}" data-project="${projectId}" title="Hapus pemakaian material ini">×</button>
                    </div>
                `,
          )
          .join("");
      } catch (err) {
        container.innerHTML =
          '<p style="color:var(--text-muted);">No materials consumed yet.</p>';
      }
    }

    async #consumeMaterial(e) {
      e.preventDefault();
      const projectId = this.#state.currentProjectId;
      if (!projectId) return this.#showToast("No project selected", "error");
      const select = this.#dom.materialSelect;
      const qtyInput = this.#dom.materialQty;
      if (!select || !qtyInput)
        return this.#showToast("Material form not ready", "error");

      const itemId = select.value;
      const qty = parseInt(qtyInput.value, 10);
      if (!itemId) return this.#showToast("Select a material", "error");
      if (!qty || qty < 1)
        return this.#showToast("Enter valid quantity", "error");

      try {
        await this.#fetchJSON("/api/inventory/usage", {
          method: "POST",
          body: JSON.stringify({
            project_id: projectId,
            item_id: itemId,
            quantity: qty,
          }),
        });
        this.#showToast("Material consumed");
        this.#openDrawer(projectId);
      } catch (err) {
        this.#showToast(err.message || "Failed to consume material", "error");
      }
    }

    async #deleteMaterial(usageId, projectId) {
      if (!confirm("Hapus pemakaian material ini?")) return;
      try {
        await this.#fetchJSON(`/api/inventory/usage/${usageId}`, {
          method: "DELETE",
        });
        this.#showToast("Material usage deleted");
        this.#openDrawer(projectId);
      } catch (err) {
        this.#showToast(err.message || "Gagal hapus material", "error");
      }
    }

    // ─── Labor ────────────────────────────────────────────────
    // ─── Labor ────────────────────────────────────────────────
    async #loadLaborOptions() {
      try {
        const select = this.#dom.laborTypeSelect;
        if (!select) {
          console.warn("laborTypeSelect not found");
          return;
        }

        // Coba ambil dari API dengan filter category=labor
        let url = "/api/price-list/?category=labor&active_only=true";
        let res = await fetch(url);
        let data = await res.json();

        // Jika tidak ada data, fallback ke semua price list
        if (!data.data || data.data.length === 0) {
          res = await fetch("/api/price-list/?active_only=true");
          data = await res.json();
        }

        select.innerHTML = '<option value="">Pilih Labor</option>';

        if (data.data && data.data.length > 0) {
          // Filter manual: cari yang category-nya 'labor' atau nama mengandung 'labor'
          const laborItems = data.data.filter(
            (item) =>
              item.category?.toLowerCase() === "labor" ||
              item.name?.toLowerCase().includes("labor"),
          );

          // Gunakan hasil filter, atau semua item jika tidak ada yang cocok
          const items = laborItems.length > 0 ? laborItems : data.data;

          items.forEach((item) => {
            const opt = document.createElement("option");
            opt.value = item.name || item.id;
            const price = parseFloat(item.price) || 0;
            const unit = item.unit || "jam";
            opt.textContent = `${item.name} (${this.#formatCurrency(price)} / ${unit})`;
            select.appendChild(opt);
          });

          // Jika items kosong, beri tahu user
          if (items.length === 0) {
            select.innerHTML = '<option value="">Tidak ada data labor</option>';
          }
        } else {
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
        const data = await this.#fetchJSON(`/api/projects/${projectId}/labor`);
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
      const laborType = select?.value;
      const hours = parseFloat(hoursInput?.value);
      if (!laborType) return this.#showToast("Pilih jenis labor", "error");
      if (!hours || hours < 0.5)
        return this.#showToast(
          "Masukkan jam kerja yang valid (min 0.5)",
          "error",
        );

      try {
        await this.#fetchJSON(`/api/projects/${projectId}/labor`, {
          method: "POST",
          body: JSON.stringify({ labor_type: laborType, hours }),
        });
        this.#showToast("Labor added");
        this.#openDrawer(projectId);
      } catch (err) {
        this.#showToast(err.message || "Gagal menambah labor", "error");
      }
    }

    async #deleteLabor(laborId, projectId) {
      if (!confirm("Hapus data labor ini?")) return;
      try {
        await this.#fetchJSON(`/api/projects/${projectId}/labor/${laborId}`, {
          method: "DELETE",
        });
        this.#showToast("Labor deleted");
        this.#openDrawer(projectId);
      } catch (err) {
        this.#showToast(err.message || "Gagal hapus labor", "error");
      }
    }

    // ─── Progress Popup ──────────────────────────────────────
    #openProgressPopup(id) {
      const popup = this.#dom.progressPopup;
      if (!popup) return;
      const proj = this.#state.projects.find((p) => p.id === id);
      if (!proj) return;

      // Set title
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
      if (slider) slider.value = progress;
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
      this.#updateMilestoneHighlights(progress);

      // Mark complete checkbox
      const isCompleted = proj.status === "completed";
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

      // Store current project id for save
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
        new: ["inquiry"],
        quoted: ["inquiry"],
        approved: ["inquiry"],
        preparation: ["inquiry", "parts"],
        painting: ["inquiry", "parts", "disassembly", "paint_prep"],
        assembly: ["inquiry", "parts", "disassembly", "paint_prep", "painting"],
        completed: allStages.map((s) => s.key),
      };
      const completedKeys = statusMap[status] || ["inquiry"];
      return allStages.map((stage, idx) => {
        const isDone = completedKeys.includes(stage.key);
        const isActive = !isDone && completedKeys.length === idx;
        return {
          label: stage.label,
          status: isDone ? "done" : isActive ? "active" : "pending",
        };
      });
    }

    async #saveProgressPopup() {
      const projectId = this.#state.currentProjectId;
      if (!projectId) return;
      const progress = parseInt(this.#dom.progressPopupSlider?.value || 0, 10);
      const note = this.#dom.progressPopupNote?.value.trim() || "";
      const markComplete = this.#dom.markCompleteCheckbox?.checked || false;

      const payload = { progress };
      if (note) payload.notes = note;
      if (markComplete && progress === 100) payload.status = "completed";

      try {
        await this.#fetchJSON(`${API_BASE}/${projectId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
        this.#showToast("Progress updated successfully");
        this.#closeProgressPopup();
        this.#loadProjects();
        if (
          this.#dom.projectDrawer?.classList.contains("active") &&
          this.#state.currentProjectId === projectId
        ) {
          this.#openDrawer(projectId);
        }
      } catch (err) {
        this.#showToast("Failed to update progress", "error");
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
        this.#loadProjects();
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
        // Populate fields
        const fieldMap = {
          projectName: "name",
          customerName: "customer_name",
          phoneNumber: "phone_number",
          projectStatus: "status",
          progressSliderForm: "progress",
          vehicleBrand: "vehicle_brand",
          vehicleModel: "vehicle_model",
          licensePlate: "license_plate",
          estimatedCost: "estimated_cost",
          estimatedRevenue: "estimated_revenue",
          actualCost: "actual_cost",
          actualRevenue: "actual_revenue",
          startDate: "start_date",
          targetDelivery: "target_delivery",
          projectNotes: "notes",
        };
        Object.keys(fieldMap).forEach((elId) => {
          const el = document.getElementById(elId);
          const key = fieldMap[elId];
          if (el && editData[key] !== undefined) {
            el.value = editData[key];
          }
        });
        // Trigger progress display
        const slider = document.getElementById("progressSliderForm");
        const display = document.getElementById("progressDisplay");
        if (slider && display) {
          display.textContent = slider.value;
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
        if (slider) slider.value = 0;
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
        phone_number: getVal("phoneNumber").trim(),
        status: getVal("projectStatus"),
        progress: parseInt(getVal("progressSliderForm"), 10) || 0,
        vehicle_brand: getVal("vehicleBrand").trim(),
        vehicle_model: getVal("vehicleModel").trim(),
        license_plate: getVal("licensePlate").trim(),
        estimated_cost: parseFloat(getVal("estimatedCost")) || 0,
        estimated_revenue: parseFloat(getVal("estimatedRevenue")) || 0,
        actual_cost: parseFloat(getVal("actualCost")) || 0,
        actual_revenue: parseFloat(getVal("actualRevenue")) || 0,
        start_date: getVal("startDate") || null,
        target_delivery: getVal("targetDelivery") || null,
        notes: getVal("projectNotes").trim(),
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
        this.#loadProjects();
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
      return STATUS_LABELS[status] || status;
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
