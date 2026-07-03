/**
 * NOCTRA Inquiries Management
 * Full CRUD + Drawer, integrated with backend APIs
 * Based on CustomerInquiry schema
 */
(function () {
  "use strict";

  // ─── Constants ──────────────────────────────────────────────
  const API_BASE = "/api/customer/inquiry";
  const PROJECT_API = "/api/projects";

  const STATUS_MAP = {
    new: "New",
    under_review: "Under Review",
    contacted: "Contacted",
    quoted: "Quoted",
    approved: "Approved", // <-- TAMBAHKAN INI
    converted: "Converted",
    rejected: "Rejected",
    closed: "Closed",
    completed: "Completed",
  };

  const PROJECT_STATUS_MAP = {
    draft: "Draft",
    active: "Active",
    in_progress: "In Progress",
    on_hold: "On Hold",
    completed: "Completed",
    cancelled: "Cancelled",
    preparation: "Preparation",
    painting: "Painting",
    assembly: "Assembly",
  };

  // ─── Main Class ──────────────────────────────────────────────
  class InquiryManager {
    // ─── Private fields ──────────────────────────────────────
    #state = {
      inquiries: [],
      filterStatus: "",
      searchQuery: "",
      currentInquiryId: null,
    };

    #dom = {};
    #modals = {};
    #timers = { search: null, notes: null };
    #isLoading = false;
    #completedProjectsNotified = new Set();
    #carouselResizeHandlers = new Map();
    #lightbox = {
      overlay: null,
      image: null,
      prevBtn: null,
      nextBtn: null,
      photos: [],
      currentIndex: 0,
      isOpen: false,
    };

    // ─── Constructor ──────────────────────────────────────────
    constructor() {
      this.#cacheDom();
      this.#initModals();
      this.#bindEvents();
      this.#initLightbox();
      this.#bindTableEvents();
      this.#loadInquiries();
    }

    // ─── DOM Caching ──────────────────────────────────────────
    #cacheDom() {
      const ids = [
        "inquiriesBody",
        "searchInquiry",
        "statusFilter",
        "totalCount",
        "newCount",
        "underReviewCount",
        "quotedCount",
        "convertedCount",
        "inquiryDrawer",
        "closeDrawer",
        "drawerCustomerName",
        "drawerStatusBadge",
        "drawerName",
        "drawerPhone",
        "drawerEmail",
        "drawerProvince",
        "drawerCity",
        "drawerBrand",
        "drawerModel",
        "drawerYear",
        "drawerPlate",
        "drawerPrevRepaint",
        "drawerBikeModified",
        "drawerCondition",
        "drawerType",
        "drawerServices",
        "drawerFinish",
        "drawerColor",
        "drawerBudget",
        "drawerDeadline",
        "drawerPriority",
        "drawerDescription",
        "drawerReference",
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
        "drawerProjectStartDate",
        "drawerProjectTargetDelivery",
        "quoteModal",
        "quoteForm",
        "quoteCost",
        "quoteNotes",
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
        "drawerBeforeAfterSection",
        "beforeTrack",
        "afterTrack",
        "projectStartDateDisplay",
        "projectTargetDeliveryDisplay",
        "drawerLaborItems",
        "drawerMaterialUsages",
      ];

      const refs = {};
      ids.forEach((id) => {
        refs[id] = document.getElementById(id);
      });
      this.#dom = refs;
    }

    // ─── Toast Notification ──────────────────────────────────
    #showToast(message, isError = false) {
      if (typeof window.showToast === "function") {
        window.showToast(message, isError ? "error" : "success");
        return;
      }

      let toast = document.querySelector(".app-toast");
      if (!toast) {
        toast = document.createElement("div");
        toast.className = "app-toast";
        document.body.appendChild(toast);
      }

      toast.textContent = message;
      toast.className = "app-toast" + (isError ? " error" : "");
      clearTimeout(toast._timeout);
      requestAnimationFrame(() => toast.classList.add("show"));
      toast._timeout = setTimeout(() => toast.classList.remove("show"), 3000);
    }

    // ─── Modal Initialization ────────────────────────────────
    #initModals() {
      const { inquiryDrawer, closeDrawer } = this.#dom;

      if (!inquiryDrawer) return;

      this.#modals.drawer = inquiryDrawer;

      // Close drawer
      closeDrawer?.addEventListener("click", () => this.#closeDrawer());
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && inquiryDrawer.classList.contains("active")) {
          this.#closeDrawer();
        }
      });

      // Convert modal
      const convertModal = this.#dom.convertModal;
      if (convertModal) {
        this.#modals.convert = convertModal;
        const closeConvert = () => this.#closeConvertModal();
        this.#dom.closeConvertModal?.addEventListener("click", closeConvert);
        this.#dom.cancelConvertBtn?.addEventListener("click", closeConvert);
        convertModal.addEventListener("click", (e) => {
          if (e.target === convertModal) closeConvert();
        });
        this.#dom.convertForm?.addEventListener("submit", (e) =>
          this.#handleConvertSubmit(e),
        );
      }

      // Quote modal
      const quoteModal = this.#dom.quoteModal;
      if (quoteModal) {
        this.#modals.quote = quoteModal;
        const closeQuote = () => this.#closeQuoteModal();
        this.#dom.closeQuoteModal?.addEventListener("click", closeQuote);
        this.#dom.cancelQuoteBtn?.addEventListener("click", closeQuote);
        quoteModal.addEventListener("click", (e) => {
          if (e.target === quoteModal) closeQuote();
        });
        this.#dom.quoteForm?.addEventListener("submit", (e) =>
          this.#handleQuoteSubmit(e),
        );
      }

      // Reject modal
      const rejectModal = this.#dom.rejectModal;
      if (rejectModal) {
        this.#modals.reject = rejectModal;
        const closeReject = () => this.#closeRejectModal();
        this.#dom.closeRejectModal?.addEventListener("click", closeReject);
        this.#dom.cancelRejectBtn?.addEventListener("click", closeReject);
        rejectModal.addEventListener("click", (e) => {
          if (e.target === rejectModal) closeReject();
        });
        this.#dom.rejectForm?.addEventListener("submit", (e) =>
          this.#handleRejectSubmit(e),
        );
      }
    }

    // ─── Event Bindings ──────────────────────────────────────
    #bindEvents() {
      const { searchInquiry, statusFilter, exportInquiriesBtn } = this.#dom;

      // Search with debounce
      searchInquiry?.addEventListener("input", (e) => {
        clearTimeout(this.#timers.search);
        this.#timers.search = setTimeout(() => {
          this.#state.searchQuery = e.target.value.trim();
          this.#renderTable();
        }, 300);
      });

      // Status filter
      statusFilter?.addEventListener("change", (e) => {
        this.#state.filterStatus = e.target.value;
        this.#renderTable();
      });

      // Export (placeholder)
      exportInquiriesBtn?.addEventListener("click", () => {
        this.#showToast("Export feature coming soon");
      });

      // Quote form submit
      this.#dom.quoteForm?.addEventListener("submit", (e) =>
        this.#handleQuoteSubmit(e),
      );

      // Drawer action buttons
      const drawerActions = [
        { btn: "drawerApproveBtn", action: "approve" },
        { btn: "drawerQuoteBtn", action: "quote" },
        { btn: "drawerRejectBtn", action: "reject" },
        { btn: "drawerConvertBtn", action: "convert" },
        { btn: "drawerWhatsappBtn", action: "whatsapp" },
      ];

      // 🔥 DEBUG: Cek drawer action buttons
      // console.log("🔍 Checking drawer action buttons:");
      const drawerBtnIds = [
        "drawerApproveBtn",
        "drawerQuoteBtn",
        "drawerRejectBtn",
        "drawerConvertBtn",
        "drawerWhatsappBtn",
      ];
      drawerBtnIds.forEach((id) => {
        const el = document.getElementById(id);
        /// console.log(`  ${id}:`, el ? "✅ Found" : "❌ Not found");
      });

      drawerActions.forEach(({ btn, action }) => {
        const btnEl = document.getElementById(btn); // 🔥 Gunakan getElementById langsung
        // if (!btnEl) {
        //  console.warn(`⚠️ Button ${btn} not found in DOM`);
        //  return;
        // }
        // console.log(
        //  `✅ Attaching event listener to ${btn} for action: ${action}`,
        // );
        btnEl.addEventListener("click", (e) => {
          console.log(`🖱️ ${btn} clicked!`);
          e.preventDefault();
          e.stopPropagation();
          const id = this.#state.currentInquiryId;
          console.log(`📌 Current inquiry ID:`, id);
          if (!id) {
            this.#showToast("No inquiry selected", true);
            return;
          }

          switch (action) {
            case "approve":
              console.log("🟢 Approving inquiry:", id);
              this.#approveInquiry(id);
              break;
            case "quote":
              this.#openQuoteModal(id);
              break;
            case "reject":
              this.#openRejectModal(id);
              break;
            case "convert":
              this.#openConvertModal(id);
              break;
            case "whatsapp":
              this.#openWhatsApp(id);
              break;
          }
        });
      });

      // Notes auto-save
      const notes = this.#dom.drawerNotes;
      if (notes) {
        notes.addEventListener("input", () => {
          const counter = this.#dom.noteCounter;
          if (counter) counter.textContent = notes.value.length;
          clearTimeout(this.#timers.notes);
          this.#timers.notes = setTimeout(() => {
            this.#saveNotes(notes.value);
          }, 800);
        });
      }
    }

    // ─── Table Event Delegation ──────────────────────────────
    #bindTableEvents() {
      const tbody = this.#dom.inquiriesBody;
      if (!tbody) return;

      tbody.addEventListener("click", (e) => {
        const target = e.target.closest("button, tr");
        if (!target) return;

        const tr = target.closest("tr");
        if (!tr) return;
        const id = tr.dataset.id;
        if (!id) return;

        // If button clicked
        if (target.tagName === "BUTTON") {
          const action = target.dataset.action;
          if (action) {
            e.stopPropagation();
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
                this.#openConvertModal(id);
                break;
            }
            return;
          }
        }

        // Click on row (not button)
        this.#openDrawer(id);
      });
    }

    // ─── Lightbox ─────────────────────────────────────────────
    #initLightbox() {
      const overlay = document.getElementById("lightboxOverlay");
      if (!overlay) {
        console.warn("Lightbox overlay not found – lightbox disabled");
        return;
      }
      this.#lightbox.overlay = overlay;
      this.#lightbox.image = document.getElementById("lightboxImage");
      this.#lightbox.prevBtn = document.getElementById("lightboxPrev");
      this.#lightbox.nextBtn = document.getElementById("lightboxNext");
      const closeBtn = document.getElementById("lightboxClose");

      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) this.#closeLightbox();
      });

      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && this.#lightbox.isOpen) this.#closeLightbox();
        if (e.key === "ArrowLeft" && this.#lightbox.isOpen)
          this.#prevLightbox();
        if (e.key === "ArrowRight" && this.#lightbox.isOpen)
          this.#nextLightbox();
      });

      closeBtn?.addEventListener("click", () => this.#closeLightbox());
      this.#lightbox.prevBtn?.addEventListener("click", () =>
        this.#prevLightbox(),
      );
      this.#lightbox.nextBtn?.addEventListener("click", () =>
        this.#nextLightbox(),
      );
    }

    #openLightbox(imageUrls, initialIndex = 0) {
      if (!imageUrls || imageUrls.length === 0) return;
      if (!this.#lightbox.overlay) {
        console.warn("Lightbox overlay not found");
        return;
      }

      this.#lightbox.photos = imageUrls;
      this.#lightbox.currentIndex = Math.min(
        initialIndex,
        imageUrls.length - 1,
      );
      this.#lightbox.isOpen = true;

      this.#updateLightboxImage();
      this.#lightbox.overlay.style.display = "flex";
      document.body.style.overflow = "hidden";

      const hasPrev = this.#lightbox.currentIndex > 0;
      const hasNext =
        this.#lightbox.currentIndex < this.#lightbox.photos.length - 1;
      if (this.#lightbox.prevBtn)
        this.#lightbox.prevBtn.style.display = hasPrev ? "flex" : "none";
      if (this.#lightbox.nextBtn)
        this.#lightbox.nextBtn.style.display = hasNext ? "flex" : "none";

      let counter = this.#lightbox.overlay.querySelector(".lightbox-counter");
      if (!counter) {
        counter = document.createElement("div");
        counter.className = "lightbox-counter";
        this.#lightbox.overlay.appendChild(counter);
      }
      counter.textContent = `${this.#lightbox.currentIndex + 1} / ${this.#lightbox.photos.length}`;
    }

    #closeLightbox() {
      this.#lightbox.isOpen = false;
      if (this.#lightbox.overlay) {
        this.#lightbox.overlay.style.display = "none";
      }
      document.body.style.overflow = "";
    }

    #updateLightboxImage() {
      const img = this.#lightbox.image;
      const urls = this.#lightbox.photos;
      const idx = this.#lightbox.currentIndex;
      if (img && urls && urls.length > 0) {
        img.src = urls[idx];
        const counter =
          this.#lightbox.overlay?.querySelector(".lightbox-counter");
        if (counter) counter.textContent = `${idx + 1} / ${urls.length}`;
      }
      const hasPrev = idx > 0;
      const hasNext = idx < urls.length - 1;
      if (this.#lightbox.prevBtn)
        this.#lightbox.prevBtn.style.display = hasPrev ? "flex" : "none";
      if (this.#lightbox.nextBtn)
        this.#lightbox.nextBtn.style.display = hasNext ? "flex" : "none";
    }

    #prevLightbox() {
      if (this.#lightbox.currentIndex > 0) {
        this.#lightbox.currentIndex--;
        this.#updateLightboxImage();
      }
    }

    #nextLightbox() {
      if (this.#lightbox.currentIndex < this.#lightbox.photos.length - 1) {
        this.#lightbox.currentIndex++;
        this.#updateLightboxImage();
      }
    }

    // ─── Data Loading ─────────────────────────────────────────
    async #loadInquiries() {
      if (this.#isLoading) return;
      this.#isLoading = true;

      const tbody = this.#dom.inquiriesBody;
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">Loading inquiries...</td></tr>`;
      }

      try {
        const data = await this.#fetchJSON(`${API_BASE}/`);
        // 🔥 FIX: Response dari API adalah { success, message, data: [...] }
        const inquiries = Array.isArray(data.data) ? data.data : [];
        this.#state.inquiries = inquiries;
        this.#renderTable();
        this.#updateStats();
        this.#notifyCompletedProjects();
      } catch (err) {
        console.error("Inquiries load error:", err);
        this.#showToast("Failed to load inquiries", true);
        if (tbody) {
          tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">Error loading inquiries</td></tr>`;
        }
      } finally {
        this.#isLoading = false;
      }
    }

    #notifyCompletedProjects() {
      this.#state.inquiries.forEach((inq) => {
        if (
          inq.project &&
          inq.project.status === "completed" &&
          !this.#completedProjectsNotified.has(inq.project.id)
        ) {
          this.#showToast(
            `🎉 Project for ${inq.customer_name} has been completed!`,
          );
          this.#completedProjectsNotified.add(inq.project.id);
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

      const { searchQuery, filterStatus, inquiries } = this.#state;
      const search = searchQuery.toLowerCase();

      const filtered = inquiries.filter((inq) => {
        const matchSearch =
          !search ||
          (inq.customer_name || "").toLowerCase().includes(search) ||
          (inq.customer_phone_number || "").includes(search) ||
          (inq.vehicle_brand || "").toLowerCase().includes(search) ||
          (inq.vehicle_model || "").toLowerCase().includes(search);

        let matchStatus = true;
        const statusLower = (inq.status || "").toLowerCase();
        if (filterStatus === "has_project") {
          matchStatus = !!inq.project;
        } else if (filterStatus === "no_project") {
          matchStatus = !inq.project;
        } else if (filterStatus === "project_completed") {
          matchStatus = !!(inq.project && inq.project.status === "completed");
        } else {
          matchStatus =
            !filterStatus || statusLower === filterStatus.toLowerCase();
        }

        return matchSearch && matchStatus;
      });

      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">No inquiries found</td></tr>`;
        return;
      }

      const fragment = document.createDocumentFragment();
      filtered.forEach((inq) => {
        const row = this.#createRow(inq);
        fragment.appendChild(row);
      });

      tbody.innerHTML = "";
      tbody.appendChild(fragment);
    }

    #createRow(inq) {
      const tr = document.createElement("tr");
      tr.dataset.id = inq.id;

      const statusLow = (inq.status || "").toLowerCase();
      const canConvert = ![
        "converted",
        "rejected",
        "closed",
        "completed",
      ].includes(statusLow);
      const projectStatus = inq.project
        ? this.#getProjectStatusLabel(inq.project.status)
        : "—";

      tr.innerHTML = `
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
      `;

      return tr;
    }

    #updateStats() {
      const total = this.#state.inquiries.length;
      const newCount = this.#state.inquiries.filter(
        (i) => (i.status || "").toLowerCase() === "new",
      ).length;
      const underReviewCount = this.#state.inquiries.filter(
        (i) => (i.status || "").toLowerCase() === "under_review",
      ).length;
      const quotedCount = this.#state.inquiries.filter(
        (i) => (i.status || "").toLowerCase() === "quoted",
      ).length;
      const convertedCount = this.#state.inquiries.filter(
        (i) => (i.status || "").toLowerCase() === "converted",
      ).length;

      this.#setText("totalCount", total);
      this.#setText("newCount", newCount);
      this.#setText("underReviewCount", underReviewCount);
      this.#setText("quotedCount", quotedCount);
      this.#setText("convertedCount", convertedCount);
    }

    // ─── Drawer ──────────────────────────────────────────────
    async #openDrawer(id) {
      const drawer = this.#modals.drawer;
      if (!drawer) return;

      this.#state.currentInquiryId = id;
      drawer.classList.add("active");
      this.#resetDrawer();

      try {
        const data = await this.#fetchJSON(`${API_BASE}/${id}`);
        const inquiry = data.data;
        await this.#populateDrawer(inquiry);
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

      for (const [trackId, handler] of this.#carouselResizeHandlers) {
        window.removeEventListener("resize", handler);
      }
      this.#carouselResizeHandlers.clear();
    }

    #resetDrawer() {
      const fields = [
        "drawerCustomerName",
        "drawerStatusBadge",
        "drawerName",
        "drawerPhone",
        "drawerEmail",
        "drawerProvince",
        "drawerCity",
        "drawerBrand",
        "drawerModel",
        "drawerYear",
        "drawerPlate",
        "drawerPrevRepaint",
        "drawerBikeModified",
        "drawerCondition",
        "drawerType",
        "drawerServices",
        "drawerFinish",
        "drawerColor",
        "drawerBudget",
        "drawerDeadline",
        "drawerPriority",
        "drawerDescription",
        "drawerReference",
        "drawerProjectStatus",
        "drawerEstCost",
        "drawerActualCost",
        "drawerEstRevenue",
        "drawerActualRevenue",
        "drawerProfit",
        "drawerMargin",
        "projectStartDateDisplay",
        "projectTargetDeliveryDisplay",
      ];
      fields.forEach((id) => {
        const el = this.#dom[id];
        if (el) el.textContent = "—";
      });

      const refLink = this.#dom.drawerReference;
      if (refLink) refLink.style.display = "none";

      const financialSection = this.#dom.drawerFinancialSection;
      if (financialSection) financialSection.style.display = "none";

      const timeline = this.#dom.drawerTimeline;
      if (timeline) {
        timeline.innerHTML =
          '<div class="timeline-item"><span>—</span><p>Loading...</p></div>';
      }

      const notes = this.#dom.drawerNotes;
      if (notes) notes.value = "";
      const counter = this.#dom.noteCounter;
      if (counter) counter.textContent = "0";

      const beforeAfter = this.#dom.drawerBeforeAfterSection;
      if (beforeAfter) beforeAfter.style.display = "none";

      const laborContainer = this.#dom.drawerLaborItems;
      if (laborContainer)
        laborContainer.innerHTML = '<p class="no-data">No labor items</p>';

      const materialContainer = this.#dom.drawerMaterialUsages;
      if (materialContainer)
        materialContainer.innerHTML =
          '<p class="no-data">No material usage</p>';
    }

    async #populateDrawer(inquiry) {
      // Basic info
      this.#setText("drawerCustomerName", inquiry.customer_name || "—");
      const statusBadge = this.#dom.drawerStatusBadge;
      if (statusBadge) {
        statusBadge.textContent = this.#getStatusLabel(inquiry.status);
        statusBadge.className = `status-badge ${this.#getStatusBadgeClass(inquiry.status)}`;
      }
      this.#setText("drawerName", inquiry.customer_name || "—");
      this.#setText("drawerPhone", inquiry.customer_phone_number || "—");
      this.#setText("drawerEmail", inquiry.customer_email || "—");
      this.#setText("drawerProvince", inquiry.province || "—");
      this.#setText("drawerCity", inquiry.city || "—");
      this.#setText("drawerBrand", inquiry.vehicle_brand || "—");
      this.#setText("drawerModel", inquiry.vehicle_model || "—");
      this.#setText("drawerYear", inquiry.vehicle_year || "—");
      this.#setText("drawerPlate", inquiry.vehicle_license_plate || "—");
      this.#setText("drawerPrevRepaint", inquiry.previous_repaint || "—");
      this.#setText("drawerBikeModified", inquiry.bike_modified || "—");
      this.#setText("drawerCondition", inquiry.vehicle_condition || "—");
      this.#setText("drawerType", inquiry.project_type || "—");
      this.#setText("drawerServices", inquiry.services || "—");
      this.#setText("drawerFinish", inquiry.desired_finish || "—");
      this.#setText("drawerColor", inquiry.desired_color || "—");
      this.#setText(
        "drawerBudget",
        this.#formatCurrency(inquiry.estimated_budget),
      );
      this.#setText("drawerDeadline", inquiry.deadline || "—");
      this.#setText("drawerPriority", inquiry.priority || "—");
      this.#setText(
        "drawerDescription",
        inquiry.project_description || "No description provided.",
      );

      // Project status
      const projectInfo = this.#getProjectStatusInfo(inquiry);
      const statusEl = this.#dom.drawerProjectStatus;
      if (statusEl) {
        statusEl.textContent = projectInfo.label;
        statusEl.className = `project-status-badge ${projectInfo.class}`;
      }

      // Disable actions if project completed
      const isCompleted = projectInfo.class === "completed";
      [
        "drawerApproveBtn",
        "drawerQuoteBtn",
        "drawerRejectBtn",
        "drawerConvertBtn",
      ].forEach((id) => {
        const btn = this.#dom[id];
        if (btn) btn.disabled = isCompleted;
      });

      // Reference link
      const refLink = this.#dom.drawerReference;
      if (inquiry.reference_link) {
        refLink.href = inquiry.reference_link;
        refLink.style.display = "inline";
      } else {
        refLink.style.display = "none";
      }

      // Before / After photos
      this.#renderInquiryPhotos(inquiry.photos || []);

      const beforeAfterSection = this.#dom.drawerBeforeAfterSection;
      if (beforeAfterSection) beforeAfterSection.style.display = "block";

      // Financials and project details
      await this.#loadProjectFinancials(inquiry);

      // Timeline
      this.#renderTimeline(inquiry.activities);

      // Notes
      const notes = this.#dom.drawerNotes;
      if (notes) {
        notes.value = inquiry.note || "";
        const counter = this.#dom.noteCounter;
        if (counter) counter.textContent = notes.value.length;
      }

      // Action buttons state
      const statusLow = (inquiry.status || "").toLowerCase();
      const isConverted = statusLow === "converted";
      const isRejected = statusLow === "rejected";
      const isFinal =
        isConverted ||
        isRejected ||
        statusLow === "closed" ||
        statusLow === "completed";

      const approveBtn = this.#dom.drawerApproveBtn;
      const quoteBtn = this.#dom.drawerQuoteBtn;
      const rejectBtn = this.#dom.drawerRejectBtn;
      const convertBtn = this.#dom.drawerConvertBtn;

      if (approveBtn)
        approveBtn.disabled = !(
          statusLow === "new" ||
          statusLow === "under_review" ||
          statusLow === "quoted"
        );
      if (quoteBtn)
        quoteBtn.disabled = !(
          statusLow === "new" ||
          statusLow === "under_review" ||
          statusLow === "quoted"
        );
      if (rejectBtn) rejectBtn.disabled = isFinal;
      if (convertBtn) convertBtn.disabled = isFinal;

      // View project button
      const viewProjectBtn = this.#dom.drawerViewProjectBtn;
      if (viewProjectBtn) {
        if (inquiry.project && inquiry.project.id) {
          viewProjectBtn.href = `/management/projects?open=${inquiry.project.id}`;
          viewProjectBtn.style.display = "inline-flex";
        } else {
          viewProjectBtn.style.display = "none";
        }
      }
    }

    // ─── Financial Methods ──────────────────────────────────
    async #loadProjectFinancials(inquiry) {
      const financialSection = this.#dom.drawerFinancialSection;
      if (!financialSection) return;

      if (!inquiry.project || !inquiry.project.id) {
        financialSection.style.display = "none";
        return;
      }

      try {
        const response = await this.#fetchJSON(
          `/api/projects/${inquiry.project.id}`,
        );
        const data = response.data;
        const project = data.project;
        const laborItems = data.labor_items || [];
        const materialUsages = data.material_usages || [];

        const summary = this.#calculateFinancialSummary(
          project,
          laborItems,
          materialUsages,
        );

        this.#setText(
          "drawerEstCost",
          this.#formatCurrency(project.estimated_cost || 0),
        );
        this.#setText(
          "drawerActualCost",
          this.#formatCurrency(summary.actual_cost),
        );
        this.#setText(
          "drawerEstRevenue",
          this.#formatCurrency(project.estimated_revenue || 0),
        );
        this.#setText(
          "drawerActualRevenue",
          this.#formatCurrency(summary.actual_revenue),
        );
        this.#setText("drawerProfit", this.#formatCurrency(summary.profit));
        this.#setText("drawerMargin", summary.margin + "%");

        this.#renderFinancialDetails(laborItems, materialUsages);

        if (project.project_start_date) {
          const startDate = new Date(project.project_start_date);
          if (!isNaN(startDate)) {
            this.#setText(
              "projectStartDateDisplay",
              startDate.toLocaleDateString("id-ID"),
            );
          }
        }

        if (project.project_target_delivery) {
          const targetDate = new Date(project.project_target_delivery);
          if (!isNaN(targetDate)) {
            this.#setText(
              "projectTargetDeliveryDisplay",
              targetDate.toLocaleDateString("id-ID"),
            );
          }
        }

        financialSection.style.display = "block";
      } catch (err) {
        console.warn("Failed to load project financials", err);
        financialSection.style.display = "none";
      }
    }

    #calculateFinancialSummary(project, laborItems, materialUsages) {
      const totalLaborCost = laborItems.reduce((sum, item) => {
        let total = 0;
        if (item.total !== undefined && item.total !== null) {
          total = parseFloat(item.total) || 0;
        } else {
          const hours = parseFloat(item.hours) || 0;
          const rate = parseFloat(item.rate) || 0;
          total = hours * rate;
        }
        return sum + total;
      }, 0);

      const totalMaterialCost = materialUsages.reduce((sum, item) => {
        let total = 0;
        if (item.total !== undefined && item.total !== null) {
          total = parseFloat(item.total) || 0;
        } else {
          const quantity = parseFloat(item.quantity) || 0;
          const unitPrice = parseFloat(item.unit_price) || 0;
          total = quantity * unitPrice;
        }
        return sum + total;
      }, 0);

      const actualCost = totalLaborCost + totalMaterialCost;

      let actualRevenue = parseFloat(project.actual_revenue) || 0;
      if (actualRevenue === 0 && project.estimated_cost) {
        const estCost = parseFloat(project.estimated_cost) || 0;
        actualRevenue = estCost * 1.3;
      }

      const profit = actualRevenue - actualCost;

      let margin = 0;
      if (actualRevenue > 0) {
        margin = (profit / actualRevenue) * 100;
      } else if (actualCost > 0) {
        margin = (profit / actualCost) * 100;
      }
      margin = parseFloat(margin.toFixed(2));

      return {
        material_cost: parseFloat(totalMaterialCost.toFixed(2)),
        labor_cost: parseFloat(totalLaborCost.toFixed(2)),
        actual_cost: parseFloat(actualCost.toFixed(2)),
        actual_revenue: parseFloat(actualRevenue.toFixed(2)),
        profit: parseFloat(profit.toFixed(2)),
        margin: margin,
      };
    }

    #renderFinancialDetails(laborItems, materialUsages) {
      const laborContainer = this.#dom.drawerLaborItems;
      if (laborContainer) {
        if (laborItems.length > 0) {
          laborContainer.innerHTML = `
            <table class="financial-detail-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Hours</th>
                  <th>Rate</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                ${laborItems
                  .map(
                    (item) => `
                  <tr>
                    <td>${item.type || "-"}</td>
                    <td>${(parseFloat(item.hours) || 0).toFixed(1)}h</td>
                    <td>${this.#formatCurrency(item.rate || 0)}</td>
                    <td>${this.#formatCurrency(item.total || item.hours * item.rate)}</td>
                  </tr>
                `,
                  )
                  .join("")}
              </tbody>
            </table>
          `;
        } else {
          laborContainer.innerHTML = '<p class="no-data">No labor items</p>';
        }
      }

      const materialContainer = this.#dom.drawerMaterialUsages;
      if (materialContainer) {
        if (materialUsages.length > 0) {
          materialContainer.innerHTML = `
            <table class="financial-detail-table">
              <thead>
                <tr>
                  <th>Material</th>
                  <th>Qty</th>
                  <th>Unit</th>
                  <th>Unit Price</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                ${materialUsages
                  .map(
                    (item) => `
                  <tr>
                    <td>${item.material_name || item.name || "-"}</td>
                    <td>${(parseFloat(item.quantity) || 0).toFixed(2)}</td>
                    <td>${item.unit || "pcs"}</td>
                    <td>${this.#formatCurrency(item.unit_price || 0)}</td>
                    <td>${this.#formatCurrency(item.total || item.quantity * item.unit_price)}</td>
                  </tr>
                `,
                  )
                  .join("")}
              </tbody>
            </table>
          `;
        } else {
          materialContainer.innerHTML =
            '<p class="no-data">No material usage</p>';
        }
      }
    }

    // ─── Photo Rendering ─────────────────────────────────────
    #renderInquiryPhotos(photos) {
      const groups = { before: [], after: [] };
      photos.forEach((p) => {
        const stage = p.stage || "before";
        if (groups[stage]) {
          groups[stage].push(p);
        } else {
          groups.before.push(p);
        }
      });

      this.#renderCarousel("beforeTrack", groups.before);
      this.#renderCarousel("afterTrack", groups.after);
    }

    #renderCarousel(trackId, photos) {
      const track = this.#dom[trackId];
      if (!track) return;
      const container = track.closest(".carousel-container");
      if (!container) return;

      const oldHandler = this.#carouselResizeHandlers.get(trackId);
      if (oldHandler) {
        window.removeEventListener("resize", oldHandler);
        this.#carouselResizeHandlers.delete(trackId);
      }

      track.innerHTML = "";

      const buttons = container.querySelectorAll(".carousel-btn");
      if (!photos || photos.length === 0) {
        track.innerHTML = `<div class="carousel-empty">No photos</div>`;
        buttons.forEach((btn) => (btn.style.display = "none"));
        return;
      }
      buttons.forEach((btn) => (btn.style.display = "block"));

      photos.forEach((photo) => {
        const img = document.createElement("img");
        img.src = `/uploads/customer_inquiries/${this.#escapeHtml(photo.file_path)}`;
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

      const newPrev = prevBtn?.cloneNode(true);
      const newNext = nextBtn?.cloneNode(true);
      prevBtn?.replaceWith(newPrev);
      nextBtn?.replaceWith(newNext);

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
      this.#carouselResizeHandlers.set(trackId, resizeHandler);

      requestAnimationFrame(updateCarousel);

      track.addEventListener("click", (e) => {
        const img = e.target.closest("img");
        if (!img) return;
        const allImages = Array.from(track.querySelectorAll("img"));
        const urls = allImages.map((el) => el.src);
        const index = allImages.indexOf(img);
        if (index !== -1) {
          this.#openLightbox(urls, index);
        }
      });
    }

    // ─── Timeline ─────────────────────────────────────────────
    #renderTimeline(activities) {
      const timeline = this.#dom.drawerTimeline;
      if (!timeline) return;

      if (activities && activities.length > 0) {
        timeline.innerHTML = activities
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
    }

    // ─── Project Status Helpers ──────────────────────────────
    #getProjectStatusInfo(inquiry) {
      if (!inquiry.project) {
        return { label: "No Project", class: "no-project" };
      }
      const status = inquiry.project.status;
      if (status === "completed") {
        return { label: "✅ Project Completed", class: "completed" };
      }
      return { label: this.#getProjectStatusLabel(status), class: status };
    }

    // ─── CRUD Actions ──────────────────────────────────────────
    // inquiries.js - #approveInquiry

    async #approveInquiry(id) {
      console.log("🟢 approveInquiry called with id:", id);

      if (!id) {
        console.error("❌ No ID provided");
        this.#showToast("No inquiry selected", true);
        return;
      }

      const inquiry = this.#state.inquiries.find((i) => i.id === id);
      if (!inquiry) {
        console.error("❌ Inquiry not found in state");
        this.#showToast("Inquiry not found", true);
        return;
      }

      const currentStatus = (inquiry.status || "").toLowerCase();
      console.log("📌 Current status:", currentStatus);

      // Status yang bisa di-approve: new, under_review, quoted
      const validStatuses = ["new", "under_review", "quoted"];
      if (!validStatuses.includes(currentStatus)) {
        console.warn("⚠️ Invalid status for approval:", currentStatus);
        this.#showToast(
          `Cannot approve inquiry with status: ${inquiry.status}`,
          true,
        );
        return;
      }

      if (!confirm(`Approve inquiry from ${inquiry.customer_name}?`)) {
        console.log("❌ User cancelled approval");
        return;
      }

      const submitBtn =
        this.#dom.drawerApproveBtn ||
        document.getElementById("drawerApproveBtn");
      const originalText = submitBtn?.textContent || "Approve";
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Approving...";
      }

      try {
        // 🔥 FIX: Gunakan status "contacted" atau "quoted" yang sudah ada di enum
        // Atau gunakan "approved" jika sudah ditambahkan ke enum
        const newStatus = "approved"; // atau "contacted" / "quoted"

        console.log("📤 Sending approve request with status:", newStatus);
        const response = await this.#fetchJSON(`${API_BASE}/${id}/status`, {
          method: "PATCH",
          body: JSON.stringify({
            status: newStatus,
            note: "Approved by system",
          }),
        });
        console.log("📥 Response:", response);

        if (response?.success !== false) {
          this.#showToast(`✅ Inquiry from ${inquiry.customer_name} approved!`);
          await this.#refreshAfterAction(id);
        } else {
          throw new Error(response?.message || "Failed to approve inquiry");
        }
      } catch (err) {
        console.error("❌ Approve error:", err);
        this.#showToast(`❌ ${err.message || "Failed to approve"}`, true);
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    }

    async #handleQuoteSubmit(e) {
      e.preventDefault();

      const costInput = this.#dom.quoteCost;
      const notesInput = this.#dom.quoteNotes;

      const cost = parseFloat(costInput?.value);
      const notes = notesInput?.value.trim() || "";

      if (isNaN(cost) || cost < 0) {
        this.#showToast("Masukkan estimasi biaya yang valid", true);
        return;
      }

      const id = this.#state.currentInquiryId;
      if (!id) {
        this.#showToast("No inquiry selected", true);
        return;
      }

      const submitBtn = e.target.querySelector('button[type="submit"]');
      const originalText = submitBtn?.textContent || "Send Quote";
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Sending...";
      }

      try {
        // 🔥 Kirim estimated_cost DAN notes sesuai schema InquirySendQuotation
        const payload = {
          estimated_cost: cost,
          notes: notes || undefined, // jika kosong, kirim undefined
        };

        const response = await this.#fetchJSON(`${API_BASE}/${id}/quote`, {
          method: "POST",
          body: JSON.stringify(payload),
        });

        if (response?.success !== false) {
          this.#showToast(
            `✅ Quotation sent: Rp ${cost.toLocaleString("id-ID")}`,
          );
          this.#closeQuoteModal();
          await this.#refreshAfterAction(id);
        } else {
          throw new Error(response?.message || "Failed to send quotation");
        }
      } catch (err) {
        console.error("Quote error:", err);
        this.#showToast(
          `❌ ${err.message || "Failed to send quotation"}`,
          true,
        );
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    }

    async #handleRejectSubmit(e) {
      e.preventDefault();
      const reason = this.#dom.rejectReason?.value.trim();
      const id = this.#state.currentInquiryId;
      try {
        await this.#fetchJSON(`${API_BASE}/${id}/reject`, {
          method: "POST",
          body: JSON.stringify({ reason: reason || "No reason provided" }),
        });
        this.#showToast("Inquiry rejected");
        this.#closeRejectModal();
        await this.#refreshAfterAction(id);
      } catch (err) {
        this.#showToast("Failed to reject: " + err.message, true);
      }
    }

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

    async #handleConvertSubmit(e) {
      e.preventDefault();
      const id = this.#state.currentInquiryId;
      if (!id) return;

      const startDate = this.#dom.convertStartDate?.value || null;
      const targetDelivery = this.#dom.convertTargetDelivery?.value || null;

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
            project_start_date: startDate,
            project_target_delivery: targetDelivery,
          }),
        });
        if (response?.data?.project_id) {
          this.#showToast(
            `✅ Inquiry converted to project! ID: ${response.data.project_id.slice(0, 8)}`,
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

    #openQuoteModal(id) {
      this.#state.currentInquiryId = id;
      const modal = this.#modals.quote;
      if (modal) {
        modal.classList.add("active");
        document.body.style.overflow = "hidden";
        // Reset form
        if (this.#dom.quoteCost) this.#dom.quoteCost.value = "";
        if (this.#dom.quoteNotes) this.#dom.quoteNotes.value = "";
        // Focus pada cost input
        setTimeout(() => this.#dom.quoteCost?.focus(), 100);
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

    #closeConvertModal() {
      const modal = this.#modals.convert;
      if (modal) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
      }
      this.#state.currentInquiryId = null;
    }

    #openWhatsApp(id) {
      const inquiry = this.#state.inquiries.find((i) => i.id === id);
      if (!inquiry?.customer_phone_number) {
        this.#showToast("No phone number available", true);
        return;
      }

      let phone = inquiry.customer_phone_number.replace(/\D/g, "");
      if (!phone.startsWith("62") && phone.startsWith("0")) {
        phone = "62" + phone.slice(1);
      } else if (!phone.startsWith("62")) {
        phone = "62" + phone;
      }
      window.open(`https://wa.me/${phone}`, "_blank");
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

    // inquiries.js - #getStatusBadgeClass

    #getStatusBadgeClass(status) {
      const s = status?.toLowerCase() || "new";
      // Tambahkan mapping untuk status yang valid
      const validStatuses = [
        "new",
        "under_review",
        "contacted",
        "quoted",
        "approved",
        "converted",
        "rejected",
        "closed",
        "completed",
      ];
      if (!validStatuses.includes(s)) {
        return "new"; // fallback
      }
      return s === "completed" ? "completed" : s;
    }

    #setText(elementId, value) {
      const el = this.#dom[elementId];
      if (el) el.textContent = value;
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
