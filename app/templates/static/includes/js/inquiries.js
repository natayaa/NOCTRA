/**
 * NOCTRA Inquiries Dashboard
 * Full CRUD + Drawer, integrated with backend APIs
 *
 * Refactored to be modular, maintainable, and performant.
 * All logic is encapsulated in a single class.
 */
(function () {
  "use strict";

  // ─── Constants ──────────────────────────────────────────────
  const STATUS_MAP = {
    new: "New",
    quoted: "Quoted",
    approved: "Approved",
    rejected: "Rejected",
    converted: "Converted",
    completed: "Completed",
  };

  const PROJECT_STATUS_MAP = {
    new: "New",
    quoted: "Quoted",
    approved: "Approved",
    preparation: "Preparation",
    painting: "Painting",
    assembly: "Assembly",
    completed: "Completed",
  };

  const API_BASE = "/api/customer/inquiry";
  const API_PROJECTS = "/api/projects";

  // ─── Main Class ──────────────────────────────────────────────
  class InquiryManager {
    // ─── Private fields ──────────────────────────────────────
    #state = {
      inquiries: [],
      currentFilter: "",
      currentSearch: "",
      currentInquiryId: null,
    };

    #dom = {};
    #modals = {
      quote: null,
      reject: null,
      drawer: null,
      convert: null,
    };
    #timeouts = {
      notes: null,
      search: null,
    };
    #isLoading = false;
    #notifiedProjects = new Set();

    // ─── Constructor ──────────────────────────────────────────
    constructor() {
      this.#cacheDomRefs();
      this.#initializeModals();
      this.#bindEvents();
      this.#loadInquiries();
    }

    // ─── DOM Caching ──────────────────────────────────────────
    #cacheDomRefs() {
      const ids = [
        "inquiriesBody",
        "searchInquiry",
        "statusFilter",
        "totalCount",
        "newCount",
        "quotedCount",
        "convertedCount",
        "inquiryDrawer",
        "closeDrawer",
        "drawerCustomerName",
        "drawerStatusBadge",
        "drawerName",
        "drawerPhone",
        "drawerEmail",
        "drawerBrand",
        "drawerModel",
        "drawerPlate",
        "drawerCondition",
        "drawerType",
        "drawerBudget",
        "drawerTarget",
        "drawerDescription",
        "drawerReference",
        "drawerPhotosSection",
        "drawerPhotos",
        "drawerTimeline",
        "drawerNotes",
        "noteCounter",
        "drawerApproveBtn",
        "drawerQuoteBtn",
        "drawerRejectBtn",
        "drawerConvertBtn",
        "drawerWhatsappBtn",
        "drawerViewProjectBtn",
        "drawerFinancialSection",
        "drawerEstCost",
        "drawerActualCost",
        "drawerEstRevenue",
        "drawerActualRevenue",
        "drawerProfit",
        "drawerMargin",
        "drawerProjectStatus",
        "quoteModal",
        "quoteForm",
        "quoteCost",
        "quoteRevenue",
        "closeQuoteModal",
        "cancelQuoteBtn",
        "rejectModal",
        "rejectForm",
        "rejectReason",
        "closeRejectModal",
        "cancelRejectBtn",
        "exportInquiriesBtn",
        "convertModal",
        "convertForm",
        "convertStartDate",
        "convertTargetDelivery",
        "closeConvertModal",
        "cancelConvertBtn",
        // Before After
        "drawerBeforeAfterSection",
        "beforeTrack",
        "afterTrack",
      ];
      const refs = {};
      ids.forEach((id) => {
        refs[id] = document.getElementById(id);
      });
      this.#dom = refs;
    }

    // ─── Modal Initialization ────────────────────────────────
    #initializeModals() {
      const { inquiryDrawer, closeDrawer } = this.#dom;
      if (inquiryDrawer) {
        this.#modals.drawer = inquiryDrawer;
        closeDrawer?.addEventListener("click", () => this.#closeDrawer());
        document.addEventListener("keydown", (e) => {
          if (
            e.key === "Escape" &&
            inquiryDrawer.classList.contains("active")
          ) {
            this.#closeDrawer();
          }
        });

        // Convert Modal
        const convertModal = this.#dom.convertModal;
        if (convertModal) {
          this.#modals.convert = convertModal;
          const close = () => this.#closeConvertModal();
          this.#dom.closeConvertModal?.addEventListener("click", close);
          this.#dom.cancelConvertBtn?.addEventListener("click", close);
          convertModal.addEventListener("click", (e) => {
            if (e.target === convertModal) close();
          });
          this.#dom.convertForm?.addEventListener("submit", (e) =>
            this.#handleConvertSubmit(e),
          );
        }

        // Quote Modal
        const quoteModal = this.#dom.quoteModal;
        if (quoteModal) {
          this.#modals.quote = quoteModal;
          const closeBtn = this.#dom.closeQuoteModal;
          const cancelBtn = this.#dom.cancelQuoteBtn;
          const close = () => this.#closeQuoteModal();
          closeBtn?.addEventListener("click", close);
          cancelBtn?.addEventListener("click", close);
          quoteModal.addEventListener("click", (e) => {
            if (e.target === quoteModal) close();
          });
          this.#dom.quoteForm?.addEventListener("submit", (e) =>
            this.#handleQuoteSubmit(e),
          );
        }

        // Reject Modal
        const rejectModal = this.#dom.rejectModal;
        if (rejectModal) {
          this.#modals.reject = rejectModal;
          const closeBtn = this.#dom.closeRejectModal;
          const cancelBtn = this.#dom.cancelRejectBtn;
          const close = () => this.#closeRejectModal();
          closeBtn?.addEventListener("click", close);
          cancelBtn?.addEventListener("click", close);
          rejectModal.addEventListener("click", (e) => {
            if (e.target === rejectModal) close();
          });
          this.#dom.rejectForm?.addEventListener("submit", (e) =>
            this.#handleRejectSubmit(e),
          );
        }
      }
    }

    // ─── Convert Modal Methods ────────────────────────────────
    #openConvertModal(id) {
      this.#state.currentInquiryId = id;
      const modal = this.#modals.convert;
      if (modal) {
        modal.classList.add("active");
        document.body.style.overflow = "hidden";
        if (this.#dom.convertStartDate) this.#dom.convertStartDate.value = "";
        if (this.#dom.convertTargetDelivery)
          this.#dom.convertTargetDelivery.value = "";
      }
    }

    #closeConvertModal() {
      const modal = this.#modals.convert;
      if (modal) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
      }
      this.#state.currentInquiryId = null;
    }

    // ─── Event Bindings ──────────────────────────────────────
    #bindEvents() {
      const { searchInquiry, statusFilter, exportInquiriesBtn } = this.#dom;

      // Search with debounce
      searchInquiry?.addEventListener("input", (e) => {
        clearTimeout(this.#timeouts.search);
        this.#timeouts.search = setTimeout(() => {
          this.#state.currentSearch = e.target.value;
          this.#renderTable();
        }, 300);
      });

      // Status filter
      statusFilter?.addEventListener("change", (e) => {
        this.#state.currentFilter = e.target.value;
        this.#renderTable();
      });

      // Export button
      exportInquiriesBtn?.addEventListener("click", () => {
        this.#showToast("Export feature coming soon");
      });

      // Drawer action buttons
      const drawerActions = [
        "drawerApproveBtn",
        "drawerQuoteBtn",
        "drawerRejectBtn",
        "drawerConvertBtn",
        "drawerWhatsappBtn",
      ];
      drawerActions.forEach((btnId) => {
        const btn = this.#dom[btnId];
        if (btn) {
          btn.addEventListener("click", () => {
            const id = this.#state.currentInquiryId;
            if (!id) return;
            switch (btnId) {
              case "drawerApproveBtn":
                this.#approveInquiry(id);
                break;
              case "drawerQuoteBtn":
                this.#openQuoteModal(id);
                break;
              case "drawerRejectBtn":
                this.#openRejectModal(id);
                break;
              case "drawerConvertBtn":
                this.#convertInquiry(id);
                break;
              case "drawerWhatsappBtn":
                this.#openWhatsApp(id);
                break;
            }
          });
        }
      });

      // Notes auto-save
      const notes = this.#dom.drawerNotes;
      if (notes) {
        notes.addEventListener("input", () => {
          const counter = this.#dom.noteCounter;
          if (counter) counter.textContent = notes.value.length;
          clearTimeout(this.#timeouts.notes);
          this.#timeouts.notes = setTimeout(() => {
            this.#saveNotes(notes.value);
          }, 800);
        });
      }
    }

    // ─── Data Loading ─────────────────────────────────────────
    async #loadInquiries() {
      if (this.#isLoading) return;
      this.#isLoading = true;
      const tbody = this.#dom.inquiriesBody;
      if (tbody)
        tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">Loading inquiries...</td></tr>`;

      try {
        const data = await this.#fetchJSON(`${API_BASE}/`);
        this.#state.inquiries = data.data || [];
        this.#renderTable();
        this.#updateStats();
        this.#checkCompletedProjects();
      } catch (err) {
        console.error("Inquiries load error:", err);
        this.#showToast("Failed to load inquiries", true);
        if (tbody)
          tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">Error loading inquiries</td></tr>`;
      } finally {
        this.#isLoading = false;
      }
    }

    #checkCompletedProjects() {
      this.#state.inquiries.forEach((inq) => {
        if (
          inq.project &&
          inq.project.status === "completed" &&
          !this.#notifiedProjects.has(inq.project.id)
        ) {
          this.#showToast(
            `🎉 Project for ${inq.customer_name} has been completed!`,
          );
          this.#notifiedProjects.add(inq.project.id);
        }
      });
    }

    // ─── Fetch Helper ─────────────────────────────────────────
    async #fetchJSON(url, options = {}) {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
      });
      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || response.statusText);
      }
      return response.json();
    }

    // ─── Rendering ────────────────────────────────────────────
    #renderTable() {
      const tbody = this.#dom.inquiriesBody;
      if (!tbody) return;

      const search = this.#state.currentSearch.toLowerCase().trim();
      const status = this.#state.currentFilter;

      const filtered = this.#state.inquiries.filter((inq) => {
        const matchSearch =
          !search ||
          inq.customer_name?.toLowerCase().includes(search) ||
          inq.customer_phone_number?.includes(search) ||
          inq.vehicle_brand?.toLowerCase().includes(search) ||
          inq.vehicle_model?.toLowerCase().includes(search);
        const matchStatus = !status || inq.status?.toLowerCase() === status;
        let extraMatch = true;
        if (status === "has_project") extraMatch = !!inq.project;
        else if (status === "no_project") extraMatch = !inq.project;
        else if (status === "project_completed")
          extraMatch = inq.project && inq.project.status === "completed";
        return matchSearch && matchStatus && extraMatch;
      });

      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">No inquiries found</td></tr>`;
        return;
      }

      tbody.innerHTML = filtered
        .map((inq) => {
          const statusLow = (inq.status || "").toLowerCase();
          const canConvert = !["converted", "rejected", "completed"].includes(
            statusLow,
          );
          const projectStatus = inq.project
            ? this.#getProjectStatusLabel(inq.project.status)
            : "—";
          return `
            <tr data-id="${inq.id}">
              <td data-label="Customer">
                <strong>${this.#escapeHtml(inq.customer_name)}</strong><br>
                <small>${this.#escapeHtml(inq.customer_phone_number)}</small>
              </td>
              <td data-label="Vehicle">${this.#escapeHtml(inq.vehicle_brand)} ${this.#escapeHtml(inq.vehicle_model)}</td>
              <td data-label="Project Type">${this.#escapeHtml(inq.project_type || "—")}</td>
              <td data-label="Status"><span class="status-badge ${this.#getStatusBadgeClass(inq.status)}">${this.#getStatusLabel(inq.status)}</span></td>
              <td data-label="Project Status">
                ${inq.project ? `<span class="project-status-badge ${inq.project.status}">${projectStatus}</span>` : "—"}
              </td>
              <td data-label="Created">${new Date(inq.created_at).toLocaleDateString()}</td>
              <td data-label="Actions" style="text-align:center;">
                <div class="actions">
                  <button class="action-btn view" data-action="view" title="View Details"><i class="ph ph-eye"></i></button>
                  <button class="action-btn quote" data-action="quote" title="Send Quote"><i class="ph ph-file-text"></i></button>
                  <button class="action-btn approve" data-action="approve" title="Approve"><i class="ph ph-check"></i></button>
                  <button class="action-btn reject" data-action="reject" title="Reject"><i class="ph ph-x"></i></button>
                  ${canConvert ? `<button class="action-btn convert" data-action="convert" title="Convert to Project"><i class="ph ph-arrow-right"></i></button>` : ""}
                </div>
              </td>
            </tr>
          `;
        })
        .join("");

      tbody.querySelectorAll(".action-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const tr = btn.closest("tr");
          const id = tr?.dataset.id;
          if (!id) return;
          const action = btn.dataset.action;
          switch (action) {
            case "view":
              this.#openDrawer(id);
              break;
            case "quote":
              this.#openQuoteModal(id);
              break;
            case "approve":
              this.#approveInquiry(id);
              break;
            case "reject":
              this.#openRejectModal(id);
              break;
            case "convert":
              this.#convertInquiry(id);
              break;
          }
        });
      });

      tbody.querySelectorAll("tr").forEach((tr) => {
        tr.addEventListener("click", () => {
          const id = tr.dataset.id;
          if (id) this.#openDrawer(id);
        });
      });
    }

    #updateStats() {
      const total = this.#state.inquiries.length;
      const newCount = this.#state.inquiries.filter(
        (i) => i.status?.toLowerCase() === "new",
      ).length;
      const quoted = this.#state.inquiries.filter(
        (i) => i.status?.toLowerCase() === "quoted",
      ).length;
      const converted = this.#state.inquiries.filter(
        (i) => i.status?.toLowerCase() === "converted",
      ).length;

      this.#setText("totalCount", total);
      this.#setText("newCount", newCount);
      this.#setText("quotedCount", quoted);
      this.#setText("convertedCount", converted);
    }

    // ─── Drawer ──────────────────────────────────────────────
    async #openDrawer(id) {
      const drawer = this.#modals.drawer;
      if (!drawer) return;
      this.#state.currentInquiryId = id;
      drawer.classList.add("active");

      this.#resetDrawerFields();

      try {
        const data = await this.#fetchJSON(`${API_BASE}/${id}`);
        const inq = data.data;
        await this.#populateDrawer(inq);
      } catch (err) {
        console.error("Drawer load error:", err);
        this.#showToast("Could not load inquiry details", true);
        this.#closeDrawer();
      }
    }

    #closeDrawer() {
      const drawer = this.#modals.drawer;
      if (drawer) drawer.classList.remove("active");
      this.#state.currentInquiryId = null;
    }

    #resetDrawerFields() {
      const placeholders = [
        "drawerCustomerName",
        "drawerStatusBadge",
        "drawerName",
        "drawerPhone",
        "drawerEmail",
        "drawerBrand",
        "drawerModel",
        "drawerPlate",
        "drawerCondition",
        "drawerType",
        "drawerBudget",
        "drawerTarget",
        "drawerDescription",
        "drawerReference",
        "drawerProjectStatus",
        "drawerEstCost",
        "drawerActualCost",
        "drawerEstRevenue",
        "drawerActualRevenue",
        "drawerProfit",
        "drawerMargin",
      ];
      placeholders.forEach((id) => {
        const el = this.#dom[id];
        if (el) el.textContent = "—";
      });
      if (this.#dom.drawerReference)
        this.#dom.drawerReference.style.display = "none";
      if (this.#dom.drawerPhotosSection)
        this.#dom.drawerPhotosSection.style.display = "none";
      if (this.#dom.drawerFinancialSection)
        this.#dom.drawerFinancialSection.style.display = "none";
      if (this.#dom.drawerTimeline)
        this.#dom.drawerTimeline.innerHTML =
          '<div class="timeline-item"><span>—</span><p>Loading...</p></div>';
      if (this.#dom.drawerNotes) this.#dom.drawerNotes.value = "";
      if (this.#dom.noteCounter) this.#dom.noteCounter.textContent = "0";
      // Before After
      if (this.#dom.drawerBeforeAfterSection)
        this.#dom.drawerBeforeAfterSection.style.display = "none";
    }

    async #populateDrawer(inq) {
      // Basic info
      this.#setText("drawerCustomerName", inq.customer_name || "—");
      const statusBadge = this.#dom.drawerStatusBadge;
      if (statusBadge) {
        statusBadge.textContent = this.#getStatusLabel(inq.status);
        statusBadge.className = `status-badge ${this.#getStatusBadgeClass(inq.status)}`;
      }
      this.#setText("drawerName", inq.customer_name || "—");
      this.#setText("drawerPhone", inq.customer_phone_number || "—");
      this.#setText("drawerEmail", inq.customer_email || "—");
      this.#setText("drawerBrand", inq.vehicle_brand || "—");
      this.#setText("drawerModel", inq.vehicle_model || "—");
      this.#setText("drawerPlate", inq.vehicle_license_plate || "—");
      this.#setText("drawerCondition", inq.vehicle_condition || "—");
      this.#setText("drawerType", inq.project_type || "—");
      this.#setText("drawerBudget", this.#formatCurrency(inq.estimated_budget));
      this.#setText("drawerTarget", inq.project_target || "—");
      this.#setText(
        "drawerDescription",
        inq.project_description || "No description provided.",
      );

      // Project Status
      const projectInfo = this.#getProjectStatusInfo(inq);
      const projectStatusEl = this.#dom.drawerProjectStatus;
      if (projectStatusEl) {
        projectStatusEl.textContent = projectInfo.label;
        projectStatusEl.className = `project-status-badge ${projectInfo.class}`;
      }

      // Disable actions if project completed
      if (projectInfo.class === "completed") {
        [
          "drawerApproveBtn",
          "drawerQuoteBtn",
          "drawerRejectBtn",
          "drawerConvertBtn",
        ].forEach((id) => {
          const btn = this.#dom[id];
          if (btn) btn.disabled = true;
        });
      }

      // Reference link
      const refLink = this.#dom.drawerReference;
      if (inq.reference_link) {
        refLink.href = inq.reference_link;
        refLink.style.display = "inline";
      } else {
        refLink.style.display = "none";
      }

      // Photos
      const photoSection = this.#dom.drawerPhotosSection;
      const photoGrid = this.#dom.drawerPhotos;
      const allPhotos = inq.photos || [];
      console.log("Photos loaded:", allPhotos); // tambahkan log
      const beforePhotos = allPhotos.filter((_, i) => i % 2 === 0);
      const afterPhotos = allPhotos.filter((_, i) => i % 2 === 1);
      this.#renderCarousel("beforeTrack", beforePhotos);
      this.#renderCarousel("afterTrack", afterPhotos);
      if (inq.photos && inq.photos.length > 0) {
        photoSection.style.display = "block";
        photoGrid.innerHTML = inq.photos
          .map(
            (p) =>
              `<img src="${this.#escapeHtml(p.file_path)}" alt="Photo" loading="lazy" />`,
          )
          .join("");
      } else {
        photoSection.style.display = "none";
      }

      // Before & After Carousel
      const beforeAfterSection = this.#dom.drawerBeforeAfterSection;
      if (beforeAfterSection) {
        beforeAfterSection.style.display = "block";
        const beforePhotos = inq.photos?.filter((_, i) => i % 2 === 0) || [];
        const afterPhotos = inq.photos?.filter((_, i) => i % 2 === 1) || [];
        this.#renderCarousel("beforeTrack", beforePhotos);
        this.#renderCarousel("afterTrack", afterPhotos);
      } else {
        this.#renderCarousel("beforeTrack", []);
        this.#renderCarousel("afterTrack", []);
        beforeAfterSection.style.display = "block";
      }

      // Financial Summary & Project Details
      const financialSection = this.#dom.drawerFinancialSection;
      if (inq.project && inq.project.id) {
        try {
          const projectData = await this.#fetchJSON(
            `/api/projects/${inq.project.id}`,
          );
          const p = projectData.data;
          const estCost = p.estimated_cost || 0;
          const actualCost = p.actual_cost || 0;
          const estRevenue = p.estimated_revenue || 0;
          const actualRevenue = p.actual_revenue || 0;
          const profit = actualRevenue - actualCost;
          const margin =
            actualRevenue > 0 ? ((profit / actualRevenue) * 100).toFixed(0) : 0;

          this.#setText("drawerEstCost", this.#formatCurrency(estCost));
          this.#setText("drawerActualCost", this.#formatCurrency(actualCost));
          this.#setText("drawerEstRevenue", this.#formatCurrency(estRevenue));
          this.#setText(
            "drawerActualRevenue",
            this.#formatCurrency(actualRevenue),
          );
          this.#setText("drawerProfit", this.#formatCurrency(profit));
          this.#setText("drawerMargin", margin + "%");
          financialSection.style.display = "block";

          if (p.target_delivery) {
            const targetDate = new Date(p.target_delivery);
            if (!isNaN(targetDate)) {
              this.#setText("drawerTarget", targetDate.toLocaleDateString());
            }
          }
        } catch (err) {
          console.warn("Failed to load project financials", err);
          financialSection.style.display = "none";
        }
      } else {
        financialSection.style.display = "none";
      }

      // Timeline
      const timeline = this.#dom.drawerTimeline;
      if (inq.activities && inq.activities.length > 0) {
        timeline.innerHTML = inq.activities
          .map(
            (act) => `
              <div class="timeline-item">
                <span>${new Date(act.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                <p>${this.#escapeHtml(act.activity)}</p>
              </div>
            `,
          )
          .join("");
      } else {
        timeline.innerHTML = `<div class="timeline-item"><span>—</span><p>No activity yet</p></div>`;
      }

      // Notes
      const notes = this.#dom.drawerNotes;
      if (notes) {
        notes.value = inq.note || "";
        if (this.#dom.noteCounter)
          this.#dom.noteCounter.textContent = notes.value.length;
      }

      // Action buttons state
      const statusLow = (inq.status || "").toLowerCase();
      const isConverted = statusLow === "converted";
      const isRejected = statusLow === "rejected";
      const isCompleted = statusLow === "completed";

      const approveBtn = this.#dom.drawerApproveBtn;
      const quoteBtn = this.#dom.drawerQuoteBtn;
      const rejectBtn = this.#dom.drawerRejectBtn;
      const convertBtn = this.#dom.drawerConvertBtn;
      const viewProjectBtn = this.#dom.drawerViewProjectBtn;

      if (approveBtn)
        approveBtn.disabled = !(statusLow === "new" || statusLow === "quoted");
      if (quoteBtn)
        quoteBtn.disabled = !(statusLow === "new" || statusLow === "quoted");
      if (rejectBtn)
        rejectBtn.disabled = isRejected || isConverted || isCompleted;
      if (convertBtn)
        convertBtn.disabled = isConverted || isRejected || isCompleted;

      if (viewProjectBtn) {
        if (inq.project && inq.project.id) {
          viewProjectBtn.href = `/management/projects?open=${inq.project.id}`;
          viewProjectBtn.style.display = "inline-flex";
        } else {
          viewProjectBtn.style.display = "none";
        }
      }
    }

    // ─── Carousel ─────────────────────────────────────────────
    #renderCarousel(trackId, photos) {
      const track = this.#dom[trackId];
      if (!track) return;
      const container = track.closest(".carousel-container");
      if (!container) return;

      if (!photos || photos.length === 0) {
        track.innerHTML = `<div class="carousel-empty">No photos</div>`;
        container.querySelectorAll(".carousel-btn").forEach((b) => {
          b.style.display = "none";
        });
        return;
      }
      container.querySelectorAll(".carousel-btn").forEach((b) => {
        b.style.display = "block";
      });

      track.innerHTML = "";

      if (!photos || photos.length === 0) {
        track.innerHTML = `<div class="carousel-empty">No photos</div>`;
        container
          .querySelectorAll(".carousel-btn")
          .forEach((b) => (b.style.display = "none"));
        return;
      }

      container
        .querySelectorAll(".carousel-btn")
        .forEach((b) => (b.style.display = "block"));

      photos.forEach((p) => {
        const img = document.createElement("img");
        // ✅ Gunakan prefix /uploads/
        img.src = `/uploads/${this.#escapeHtml(p.file_path)}`;
        img.alt = "Photo";
        img.loading = "lazy";
        track.appendChild(img);
      });

      let currentIndex = 0;
      const total = photos.length;
      const prevBtn = container.querySelector(".prev");
      const nextBtn = container.querySelector(".next");

      const updateCarousel = () => {
        const width = container.clientWidth;
        track.style.transform = `translateX(-${currentIndex * width}px)`;
        if (prevBtn) prevBtn.disabled = currentIndex === 0;
        if (nextBtn) nextBtn.disabled = currentIndex === total - 1;
      };

      // Clone & replace to remove old listeners
      const newPrev = prevBtn?.cloneNode(true);
      const newNext = nextBtn?.cloneNode(true);
      if (prevBtn) prevBtn.replaceWith(newPrev);
      if (nextBtn) nextBtn.replaceWith(newNext);

      if (newPrev) {
        newPrev.addEventListener("click", () => {
          if (currentIndex > 0) {
            currentIndex--;
            updateCarousel();
          }
        });
      }
      if (newNext) {
        newNext.addEventListener("click", () => {
          if (currentIndex < total - 1) {
            currentIndex++;
            updateCarousel();
          }
        });
      }

      const resizeHandler = () => updateCarousel();
      window.addEventListener("resize", resizeHandler);
      requestAnimationFrame(updateCarousel);
    }

    // ─── Helper untuk Project Status ──────────────────────────
    #getProjectStatusInfo(inquiry) {
      if (!inquiry.project) return { label: "No Project", class: "no-project" };
      const status = inquiry.project.status;
      if (status === "completed") {
        return { label: "✅ Project Completed", class: "completed" };
      }
      return { label: this.#getProjectStatusLabel(status), class: status };
    }

    // ─── CRUD Actions ─────────────────────────────────────────
    async #approveInquiry(id) {
      try {
        await this.#fetchJSON(`${API_BASE}/${id}/status`, {
          method: "PATCH",
          body: JSON.stringify({ status: "approved" }),
        });
        this.#showToast("Inquiry approved");
        await this.#refreshAfterAction(id);
      } catch (err) {
        this.#showToast("Failed to approve: " + err.message, true);
      }
    }

    async #handleQuoteSubmit(e) {
      e.preventDefault();
      const cost = parseFloat(this.#dom.quoteCost?.value);
      const revenue = parseFloat(this.#dom.quoteRevenue?.value);
      if (isNaN(cost) || isNaN(revenue) || cost < 0 || revenue < 0) {
        this.#showToast("Please enter valid numbers", true);
        return;
      }
      const id = this.#state.currentInquiryId;
      try {
        await this.#fetchJSON(`${API_BASE}/${id}/quote`, {
          method: "POST",
          body: JSON.stringify({
            estimated_cost: cost,
            estimated_revenue: revenue,
          }),
        });
        this.#showToast("Quotation sent");
        this.#closeQuoteModal();
        await this.#refreshAfterAction(id);
      } catch (err) {
        this.#showToast("Failed to send quote: " + err.message, true);
      }
    }

    async #handleRejectSubmit(e) {
      e.preventDefault();
      const reason = this.#dom.rejectReason?.value.trim();
      const id = this.#state.currentInquiryId;
      try {
        await this.#fetchJSON(`${API_BASE}/${id}/reject`, {
          method: "POST",
          body: JSON.stringify({ reason }),
        });
        this.#showToast("Inquiry rejected");
        this.#closeRejectModal();
        await this.#refreshAfterAction(id);
      } catch (err) {
        this.#showToast("Failed to reject: " + err.message, true);
      }
    }

    async #convertInquiry(id) {
      const inquiry = this.#state.inquiries.find((i) => i.id === id);
      if (inquiry) {
        const status = (inquiry.status || "").toLowerCase();
        if (["converted", "rejected", "completed"].includes(status)) {
          this.#showToast("Inquiry cannot be converted", true);
          return;
        }
      }
      this.#openConvertModal(id);
    }

    async #handleConvertSubmit(e) {
      e.preventDefault();
      const id = this.#state.currentInquiryId;
      if (!id) return;
      const startDate = this.#dom.convertStartDate.value;
      const targetDelivery = this.#dom.convertTargetDelivery.value;

      const submitBtn = e.target.querySelector('button[type="submit"]');
      const originalText = submitBtn?.textContent || "Convert";
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Converting...";
      }

      try {
        const response = await this.#fetchJSON(`${API_BASE}/${id}/convert`, {
          method: "POST",
          body: JSON.stringify({
            start_date: startDate || null,
            target_delivery: targetDelivery || null,
          }),
        });
        if (response && response.data && response.data.project_id) {
          this.#showToast(
            `✅ Inquiry converted to project! ID: ${response.data.project_id.slice(
              0,
              8,
            )}`,
          );
          this.#closeConvertModal();
          await this.#refreshAfterAction(id);
        } else {
          throw new Error("Invalid response from server");
        }
      } catch (err) {
        console.error("Conversion error:", err);
        this.#showToast(`❌ ${err.message || "Conversion failed"}`, true);
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    }

    #openWhatsApp(id) {
      const inquiry = this.#state.inquiries.find((i) => i.id === id);
      if (inquiry && inquiry.customer_phone_number) {
        let phone = inquiry.customer_phone_number.replace(/\D/g, "");
        if (!phone.startsWith("62") && phone.startsWith("0"))
          phone = "62" + phone.slice(1);
        if (!phone.startsWith("62")) phone = "62" + phone;
        window.open(`https://wa.me/${phone}`, "_blank");
      } else {
        this.#showToast("No phone number available", true);
      }
    }

    async #saveNotes(value) {
      const id = this.#state.currentInquiryId;
      if (!id) return;
      try {
        await this.#fetchJSON(`${API_BASE}/${id}/notes`, {
          method: "PATCH",
          body: JSON.stringify({ note: value }),
        });
      } catch (err) {
        console.warn("Failed to save notes:", err);
      }
    }

    // ─── Modal Controls ──────────────────────────────────────
    #openQuoteModal(id) {
      this.#state.currentInquiryId = id;
      const modal = this.#modals.quote;
      if (modal) {
        modal.classList.add("active");
        document.body.style.overflow = "hidden";
        if (this.#dom.quoteCost) this.#dom.quoteCost.value = "";
        if (this.#dom.quoteRevenue) this.#dom.quoteRevenue.value = "";
      }
    }

    #closeQuoteModal() {
      const modal = this.#modals.quote;
      if (modal) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
      }
      this.#state.currentInquiryId = null;
    }

    #openRejectModal(id) {
      this.#state.currentInquiryId = id;
      const modal = this.#modals.reject;
      if (modal) {
        modal.classList.add("active");
        document.body.style.overflow = "hidden";
        if (this.#dom.rejectReason) this.#dom.rejectReason.value = "";
      }
    }

    #closeRejectModal() {
      const modal = this.#modals.reject;
      if (modal) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
      }
      this.#state.currentInquiryId = null;
    }

    // ─── Helpers ──────────────────────────────────────────────
    #formatCurrency(amount) {
      if (!amount && amount !== 0) return "—";
      return "Rp " + Number(amount).toLocaleString("id-ID");
    }

    #escapeHtml(str = "") {
      if (!str) return "";
      return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    #getStatusLabel(status) {
      return STATUS_MAP[status?.toLowerCase()] || status || "—";
    }

    #getProjectStatusLabel(status) {
      return PROJECT_STATUS_MAP[status?.toLowerCase()] || status || "—";
    }

    #getStatusBadgeClass(status) {
      const s = status?.toLowerCase() || "new";
      return s === "completed" ? "completed" : s;
    }

    #setText(elementId, value) {
      const el = this.#dom[elementId];
      if (el) el.textContent = value;
    }

    #showToast(message, isError = false) {
      if (typeof window.showToast === "function") {
        window.showToast(message, isError ? "error" : "success");
        return;
      }
      const toast =
        document.querySelector(".app-toast") ||
        (() => {
          const el = document.createElement("div");
          el.className = "app-toast";
          document.body.appendChild(el);
          return el;
        })();
      toast.textContent = message;
      toast.className = "app-toast" + (isError ? " error" : "");
      clearTimeout(toast._timeout);
      requestAnimationFrame(() => toast.classList.add("show"));
      toast._timeout = setTimeout(() => toast.classList.remove("show"), 3000);
    }

    async #refreshAfterAction(id) {
      await this.#loadInquiries();
      if (
        this.#modals.drawer?.classList.contains("active") &&
        this.#state.currentInquiryId === id
      ) {
        await this.#openDrawer(id);
      }
    }
  }

  // ─── Instantiate ─────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    new InquiryManager();
  });
})();
