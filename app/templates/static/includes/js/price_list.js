/**
 * NOCTRA Price List Management
 * Full CRUD with pagination, search, filter, and modal.
 *
 * Refactored to be modular, maintainable, and performant.
 * All logic is encapsulated in a single class.
 */
(function () {
  "use strict";

  // ─── Constants ──────────────────────────────────────────────
  const API_BASE = "/api/price-list";
  const DEFAULT_PAGE_SIZE = 10;
  const DEBOUNCE_DELAY = 300;

  // ─── Main Class ──────────────────────────────────────────────
  class PriceListManager {
    // ─── Private fields ──────────────────────────────────────
    #state = {
      items: [],
      currentPage: 1,
      totalPages: 1,
      totalItems: 0,
      isSubmitting: false,
      isLoading: false,
    };

    #dom = {};
    #timers = { search: null };

    // ─── Constructor ──────────────────────────────────────────
    constructor() {
      this.#cacheDomRefs();
      this.#ensureToastContainer();
      this.#injectStyles();
      this.#bindEvents();
      this.#loadData(1);
    }

    // ─── DOM Caching ──────────────────────────────────────────
    #cacheDomRefs() {
      const ids = [
        "priceTableBody",
        "searchPrice",
        "categoryFilter",
        "addPriceBtn",
        "priceModal",
        "modalTitle",
        "closeModalBtn",
        "cancelModalBtn",
        "priceForm",
        "editId",
        "category",
        "name",
        "description",
        "price",
        "unit",
        "vehicleBrand",
        "vehicleModel",
        "effectiveDate",
        "isActive",
        "submitBtn",
        "prevPageBtn",
        "nextPageBtn",
        "pageInfo",
      ];
      const refs = {};
      ids.forEach((id) => (refs[id] = document.getElementById(id)));
      this.#dom = refs;
    }

    // ─── Style Injection ──────────────────────────────────────
    #injectStyles() {
      if (document.getElementById("price-list-styles")) return;
      const style = document.createElement("style");
      style.id = "price-list-styles";
      style.textContent = `
                .badge {
                    display: inline-block;
                    padding: 2px 10px;
                    border-radius: 12px;
                    font-size: 0.7rem;
                    font-weight: 600;
                }
                .badge.category-paint { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
                .badge.category-material { background: rgba(16, 185, 129, 0.15); color: #10b981; }
                .badge.category-service { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
                .badge.category-other { background: rgba(139, 92, 246, 0.15); color: #8b5cf6; }
                .status-badge.active { color: #10b981; background: rgba(16,185,129,0.15); }
                .status-badge.inactive { color: #ef4444; background: rgba(239,68,68,0.15); }
                .loading-placeholder {
                    text-align: center;
                    color: var(--gray-500, #6b7280);
                    padding: 2rem 0;
                }
                .action-btn {
                    background: none;
                    border: none;
                    cursor: pointer;
                    padding: 4px 8px;
                    border-radius: 6px;
                    transition: background 0.2s;
                }
                .action-btn:hover { background: rgba(255,255,255,0.05); }
                .action-btn.edit-btn { color: #3b82f6; }
                .action-btn.delete-btn { color: #ef4444; }
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

    // ─── Event Binding ────────────────────────────────────────
    #bindEvents() {
      const {
        searchPrice,
        categoryFilter,
        addPriceBtn,
        closeModalBtn,
        cancelModalBtn,
        priceModal,
        priceForm,
        prevPageBtn,
        nextPageBtn,
      } = this.#dom;

      // Search with debounce
      searchPrice?.addEventListener("input", () => {
        clearTimeout(this.#timers.search);
        this.#timers.search = setTimeout(
          () => this.#applyFilters(),
          DEBOUNCE_DELAY,
        );
      });

      // Category filter
      categoryFilter?.addEventListener("change", () => this.#applyFilters());

      // Add button
      addPriceBtn?.addEventListener("click", () => this.#openModal());

      // Modal close
      closeModalBtn?.addEventListener("click", () => this.#closeModal());
      cancelModalBtn?.addEventListener("click", () => this.#closeModal());
      priceModal?.addEventListener("click", (e) => {
        if (e.target === priceModal) this.#closeModal();
      });
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && priceModal?.classList.contains("active")) {
          this.#closeModal();
        }
      });

      // Form submit
      priceForm?.addEventListener("submit", (e) => this.#handleFormSubmit(e));

      // Pagination
      prevPageBtn?.addEventListener("click", () => {
        if (this.#state.currentPage > 1) {
          this.#loadData(this.#state.currentPage - 1);
        }
      });
      nextPageBtn?.addEventListener("click", () => {
        if (this.#state.currentPage < this.#state.totalPages) {
          this.#loadData(this.#state.currentPage + 1);
        }
      });
    }

    // ─── Data Loading ─────────────────────────────────────────
    async #loadData(page = 1) {
      if (this.#state.isLoading) return;
      this.#state.isLoading = true;
      this.#state.currentPage = page;

      const tbody = this.#dom.priceTableBody;
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="8" class="loading-placeholder">Loading...</td></tr>`;
      }

      try {
        const search = this.#dom.searchPrice?.value.trim() || "";
        const category = this.#dom.categoryFilter?.value || "";
        const params = new URLSearchParams({
          page,
          limit: DEFAULT_PAGE_SIZE,
          active_only: "true",
        });
        if (category) params.append("category", category);
        if (search) params.append("search", search);

        const url = `${API_BASE}/?${params.toString()}`;
        const data = await this.#fetchJSON(url);

        this.#state.items = data.data || [];
        this.#state.totalItems = data.total || 0;
        this.#state.totalPages =
          Math.ceil(this.#state.totalItems / DEFAULT_PAGE_SIZE) || 1;

        this.#renderTable(this.#state.items);
        this.#updatePagination();
      } catch (err) {
        console.error("Load error:", err);
        this.#showToast("Failed to load price list", "error");
        if (tbody) {
          tbody.innerHTML = `<tr><td colspan="8" class="loading-placeholder">Error loading</td></tr>`;
        }
      } finally {
        this.#state.isLoading = false;
      }
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
    #renderTable(items) {
      const tbody = this.#dom.priceTableBody;
      if (!tbody) return;

      if (!items || items.length === 0) {
        tbody.innerHTML =
          '<tr><td colspan="8" class="loading-placeholder">No price items found</td></tr>';
        return;
      }

      tbody.innerHTML = items
        .map(
          (item) => `
                <tr>
                    <td><span class="badge category-${this.#escapeHtml(item.category || "other")}">${this.#escapeHtml(item.category || "—")}</span></td>
                    <td><strong>${this.#escapeHtml(item.name)}</strong></td>
                    <td>${this.#escapeHtml(item.description || "-")}</td>
                    <td>${this.#formatCurrency(item.price)}</td>
                    <td>${this.#escapeHtml(item.unit || "-")}</td>
                    <td>${item.vehicle_brand ? this.#escapeHtml(item.vehicle_brand) + " " + this.#escapeHtml(item.vehicle_model || "") : "-"}</td>
                    <td><span class="status-badge ${item.is_active ? "active" : "inactive"}">${item.is_active ? "Active" : "Inactive"}</span></td>
                    <td>
                        <button class="action-btn edit-btn" data-id="${item.id}"><i class="ph ph-pencil"></i></button>
                        <button class="action-btn delete-btn" data-id="${item.id}"><i class="ph ph-trash"></i></button>
                    </td>
                </tr>
            `,
        )
        .join("");

      // Attach events
      tbody.querySelectorAll(".edit-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const id = btn.dataset.id;
          this.#openEditModal(id);
        });
      });
      tbody.querySelectorAll(".delete-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const id = btn.dataset.id;
          this.#deleteItem(id);
        });
      });

      // Click row to edit (optional enhancement)
      tbody.querySelectorAll("tr").forEach((row) => {
        row.addEventListener("click", () => {
          const id = row.querySelector(".edit-btn")?.dataset.id;
          if (id) this.#openEditModal(id);
        });
      });
    }

    #updatePagination() {
      const { pageInfo, prevPageBtn, nextPageBtn } = this.#dom;
      const { currentPage, totalPages } = this.#state;
      if (pageInfo) {
        pageInfo.textContent = `Page ${currentPage} of ${totalPages || 1}`;
      }
      if (prevPageBtn) prevPageBtn.disabled = currentPage <= 1;
      if (nextPageBtn) nextPageBtn.disabled = currentPage >= totalPages;
    }

    // ─── Filters ──────────────────────────────────────────────
    #applyFilters() {
      this.#loadData(1); // reset to first page on filter change
    }

    // ─── Modal ────────────────────────────────────────────────
    #openModal(editMode = false, item = null) {
      const modal = this.#dom.priceModal;
      if (!modal) return;

      if (editMode && item) {
        this.#dom.modalTitle.textContent = "Edit Price Item";
        this.#dom.editId.value = item.id;
        this.#dom.category.value = item.category || "";
        this.#dom.name.value = item.name || "";
        this.#dom.description.value = item.description || "";
        this.#dom.price.value = item.price || "";
        this.#dom.unit.value = item.unit || "";
        this.#dom.vehicleBrand.value = item.vehicle_brand || "";
        this.#dom.vehicleModel.value = item.vehicle_model || "";
        this.#dom.effectiveDate.value = item.effective_date || "";
        this.#dom.isActive.checked =
          item.is_active !== undefined ? item.is_active : true;
        this.#dom.submitBtn.textContent = "Update";
      } else {
        this.#dom.modalTitle.textContent = "Add Price Item";
        this.#dom.editId.value = "";
        this.#dom.priceForm.reset();
        this.#dom.isActive.checked = true;
        this.#dom.effectiveDate.value = new Date().toISOString().split("T")[0];
        this.#dom.submitBtn.textContent = "Save";
      }
      modal.classList.add("active");
      document.body.style.overflow = "hidden";
    }

    #closeModal() {
      const modal = this.#dom.priceModal;
      if (modal) modal.classList.remove("active");
      document.body.style.overflow = "";
    }

    // ─── Edit & Delete ────────────────────────────────────────
    async #openEditModal(id) {
      try {
        const data = await this.#fetchJSON(`${API_BASE}/${id}`);
        this.#openModal(true, data.data);
      } catch (err) {
        this.#showToast("Failed to load price item", "error");
      }
    }

    async #deleteItem(id) {
      if (!confirm("Delete this price item permanently?")) return;
      try {
        await this.#fetchJSON(`${API_BASE}/${id}`, { method: "DELETE" });
        this.#showToast("Item deleted");
        this.#loadData(this.#state.currentPage);
      } catch (err) {
        this.#showToast("Delete failed: " + err.message, "error");
      }
    }

    // ─── Form Submit ──────────────────────────────────────────
    async #handleFormSubmit(e) {
      e.preventDefault();
      if (this.#state.isSubmitting) return;
      this.#state.isSubmitting = true;

      const id = this.#dom.editId.value;
      const payload = {
        category: this.#dom.category.value,
        name: this.#dom.name.value.trim(),
        description: this.#dom.description.value.trim(),
        price: parseFloat(this.#dom.price.value) || 0,
        unit: this.#dom.unit.value.trim(),
        vehicle_brand: this.#dom.vehicleBrand.value.trim(),
        vehicle_model: this.#dom.vehicleModel.value.trim(),
        effective_date:
          this.#dom.effectiveDate.value ||
          new Date().toISOString().split("T")[0],
        is_active: this.#dom.isActive.checked,
      };

      try {
        let url = API_BASE + "/";
        let method = "POST";
        if (id) {
          url = `${API_BASE}/${id}`;
          method = "PUT";
        }
        await this.#fetchJSON(url, { method, body: JSON.stringify(payload) });
        this.#showToast(id ? "Item updated" : "Item created");
        this.#closeModal();
        this.#loadData(this.#state.currentPage);
      } catch (err) {
        console.error(err);
        this.#showToast(err.message || "Save failed", "error");
      } finally {
        this.#state.isSubmitting = false;
      }
    }

    // ─── Helpers ──────────────────────────────────────────────
    #formatCurrency(value) {
      return new Intl.NumberFormat("id-ID", {
        style: "currency",
        currency: "IDR",
        maximumFractionDigits: 0,
      }).format(value || 0);
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

    // ─── Toast ────────────────────────────────────────────────
    #showToast(message, type = "success") {
      if (typeof window.showToast === "function") {
        window.showToast(message, type);
        return;
      }
      // Fallback
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
    new PriceListManager();
  });
})();
