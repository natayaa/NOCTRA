/**
 * NOCTRA Inventory Management
 * Full CRUD with dashboard stats, alerts, and movement history.
 *
 * Refactored to be modular, maintainable, and performant.
 * All logic is encapsulated in a single class.
 */
(function () {
  "use strict";

  // ─── Constants ──────────────────────────────────────────────
  const API_BASE = "/api/inventory";
  const REFRESH_INTERVAL = 60000; // 60 seconds

  // ─── Main Class ──────────────────────────────────────────────
  class InventoryManager {
    // ─── Private fields ──────────────────────────────────────
    #state = {
      items: [],
      selectedId: null,
      isSubmitting: false,
    };

    #dom = {};
    #timers = {
      refresh: null,
    };

    // ─── Constructor ──────────────────────────────────────────
    constructor() {
      this.#cacheDomRefs();
      this.#injectStyles();
      this.#ensureToastContainer();
      this.#bindEvents();
      this.#init();
    }

    // ─── DOM Caching ──────────────────────────────────────────
    #cacheDomRefs() {
      const ids = [
        "inventoryItemsList",
        "searchInventory",
        "categoryFilter",
        "stockFilter",
        "totalValue",
        "totalItems",
        "lowStockCount",
        "inventoryModal",
        "modalTitle",
        "editId",
        "itemName",
        "itemCategory",
        "itemStock",
        "itemUnit",
        "itemCost",
        "reorderLevel",
        "itemSupplier",
        "inventoryForm",
        "closeInventoryModal",
        "cancelModalBtn",
        "addItemBtn",
        "itemDetailContent",
        "editItemBtn",
        "deleteItemBtn",
        "detailActionsBottom",
        "reorderBtn",
        "historyBtn",
      ];
      const refs = {};
      ids.forEach((id) => {
        refs[id] = document.getElementById(id);
      });
      // Additional dynamic elements
      refs.monthlyUsage = document.querySelector(".overview-card.usage h2");
      refs.alertList = document.querySelector(".alert-list");
      refs.movementList = document.querySelector(".movement-list");
      refs.categoryChips = document.querySelectorAll(".category-chip");

      this.#dom = refs;
    }

    // ─── Style Injection ──────────────────────────────────────
    #injectStyles() {
      if (document.getElementById("inventory-styles")) return;
      const style = document.createElement("style");
      style.id = "inventory-styles";
      style.textContent = `
                .status-critical {
                    display: inline-block;
                    padding: 2px 10px;
                    border-radius: 12px;
                    font-size: 0.7rem;
                    font-weight: 600;
                    background: rgba(239, 68, 68, 0.15);
                    color: #ef4444;
                }
                .status-low {
                    display: inline-block;
                    padding: 2px 10px;
                    border-radius: 12px;
                    font-size: 0.7rem;
                    font-weight: 600;
                    background: rgba(245, 158, 11, 0.15);
                    color: #f59e0b;
                }
                .status-normal {
                    display: inline-block;
                    padding: 2px 10px;
                    border-radius: 12px;
                    font-size: 0.7rem;
                    font-weight: 600;
                    background: rgba(16, 185, 129, 0.15);
                    color: #10b981;
                }
                .loading-placeholder {
                    text-align: center;
                    color: var(--gray-500, #6b7280);
                    padding: 2rem 0;
                }
                .detail-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 0.75rem;
                }
                .detail-card {
                    background: rgba(255, 255, 255, 0.03);
                    padding: 0.75rem;
                    border-radius: 10px;
                    border: 1px solid var(--gray-200, #e5e7eb);
                }
                .detail-card label {
                    display: block;
                    font-size: 0.7rem;
                    color: var(--gray-500, #6b7280);
                    text-transform: uppercase;
                    margin-bottom: 0.25rem;
                }
                .detail-card strong {
                    color: var(--gray-800, #1f2937);
                }
                .empty-state {
                    text-align: center;
                    padding: 2rem 0;
                    color: var(--gray-500, #6b7280);
                }
                .empty-state i {
                    font-size: 2.5rem;
                    margin-bottom: 0.5rem;
                }
                .empty-state h4 {
                    margin: 0.5rem 0 0.25rem;
                }
                @media (max-width: 768px) {
                    .detail-grid {
                        grid-template-columns: 1fr;
                    }
                }
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
        searchInventory,
        categoryFilter,
        stockFilter,
        addItemBtn,
        closeInventoryModal,
        cancelModalBtn,
        inventoryModal,
        inventoryForm,
        editItemBtn,
        deleteItemBtn,
        reorderBtn,
        historyBtn,
        categoryChips,
      } = this.#dom;

      // Search & filters (debounced search)
      searchInventory?.addEventListener("input", () => this.#applyFilters());
      categoryFilter?.addEventListener("change", () => this.#applyFilters());
      stockFilter?.addEventListener("change", () => this.#applyFilters());

      // Category chips
      categoryChips.forEach((chip) => {
        chip.addEventListener("click", () => {
          categoryChips.forEach((c) => c.classList.remove("active"));
          chip.classList.add("active");
          const category = chip.textContent.trim();
          if (category === "All") {
            categoryFilter.value = "";
          } else {
            categoryFilter.value = category;
          }
          this.#applyFilters();
        });
      });

      // Modal open/close
      addItemBtn?.addEventListener("click", () => this.#openModal());
      closeInventoryModal?.addEventListener("click", () => this.#closeModal());
      cancelModalBtn?.addEventListener("click", () => this.#closeModal());
      inventoryModal?.addEventListener("click", (e) => {
        if (e.target === inventoryModal) this.#closeModal();
      });
      document.addEventListener("keydown", (e) => {
        if (
          e.key === "Escape" &&
          inventoryModal?.classList.contains("active")
        ) {
          this.#closeModal();
        }
      });

      // Form submit
      inventoryForm?.addEventListener("submit", (e) =>
        this.#handleFormSubmit(e),
      );

      // Detail actions
      editItemBtn?.addEventListener("click", () => this.#editSelectedItem());
      deleteItemBtn?.addEventListener("click", () =>
        this.#deleteSelectedItem(),
      );
      reorderBtn?.addEventListener("click", () => this.#handleReorder());
      historyBtn?.addEventListener("click", () => this.#handleHistory());
    }

    // ─── Initialization ──────────────────────────────────────
    async #init() {
      await this.#loadData();
      this.#showEmptyDetail();

      // Auto-refresh
      this.#timers.refresh = setInterval(() => {
        this.#loadData(false);
      }, REFRESH_INTERVAL);
    }

    // ─── Data Loading ─────────────────────────────────────────
    async #loadData(showLoading = true) {
      try {
        const [items, kpis, usage, alerts, movements] = await Promise.all([
          this.#fetchJSON(`${API_BASE}/`),
          this.#fetchJSON(`${API_BASE}/dashboard/kpis`),
          this.#fetchJSON(`${API_BASE}/dashboard/monthly-usage`),
          this.#fetchJSON(`${API_BASE}/alerts`),
          this.#fetchJSON(`${API_BASE}/movement/recent`),
        ]);

        this.#state.items = items.data || [];

        // Render table
        this.#renderTable(this.#state.items);
        this.#applyFilters();

        // Update dashboard stats
        this.#updateStats(kpis.data, usage.data);

        // Render alerts
        this.#renderAlerts(alerts.data);

        // Render recent movements
        this.#renderMovements(movements.data);

        // If selected item still exists, show it
        if (this.#state.selectedId) {
          const stillExists = this.#state.items.some(
            (i) => i.id === this.#state.selectedId,
          );
          if (stillExists) {
            this.#showItemDetails(this.#state.selectedId);
          } else {
            this.#showEmptyDetail();
            this.#state.selectedId = null;
          }
        }
      } catch (err) {
        console.error("Failed to load inventory data:", err);
        this.#showToast("Error loading inventory", "error");
        const tbody = this.#dom.inventoryItemsList;
        if (tbody) {
          tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">Error loading inventory</td></tr>`;
        }
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

    // ─── Rendering: Table ─────────────────────────────────────
    #renderTable(items) {
      const tbody = this.#dom.inventoryItemsList;
      if (!tbody) return;
      if (!items || items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">No inventory items found</td></tr>`;
        return;
      }

      tbody.innerHTML = items
        .map((item) => {
          const status = this.#getStockStatus(item);
          const totalValue = item.current_stock * item.cost_price;
          return `
                    <tr data-id="${item.id}">
                        <td><strong>${this.#escapeHtml(item.name)}</strong></td>
                        <td>${this.#escapeHtml(item.category)}</td>
                        <td>${item.current_stock}</td>
                        <td>${this.#escapeHtml(item.unit)}</td>
                        <td><span class="${status.className}">${status.label}</span></td>
                        <td>${this.#formatCurrency(totalValue)}</td>
                        <td>
                            <button class="table-view-btn" data-id="${item.id}" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `;
        })
        .join("");

      // Attach view button events
      tbody.querySelectorAll(".table-view-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const id = btn.dataset.id;
          this.#showItemDetails(id);
        });
      });

      // Click row to view details
      tbody.querySelectorAll("tr").forEach((row) => {
        row.addEventListener("click", () => {
          const id = row.dataset.id;
          if (id) this.#showItemDetails(id);
        });
      });
    }

    // ─── Rendering: Stats ─────────────────────────────────────
    #updateStats(kpis, usage) {
      const { totalValue, totalItems, lowStockCount, monthlyUsage } = this.#dom;

      if (kpis) {
        if (totalValue) {
          totalValue.textContent = this.#formatCurrency(
            kpis.total_inventory_value || 0,
          );
        }
        if (totalItems) {
          totalItems.textContent = kpis.total_skus || 0;
        }
        if (lowStockCount) {
          lowStockCount.textContent = kpis.low_stock_count || 0;
        }
      } else {
        // Fallback: compute from items
        if (totalValue) {
          const total = this.#state.items.reduce(
            (sum, i) => sum + i.current_stock * i.cost_price,
            0,
          );
          totalValue.textContent = this.#formatCurrency(total);
        }
        if (totalItems) {
          totalItems.textContent = this.#state.items.length;
        }
        if (lowStockCount) {
          const low = this.#state.items.filter((i) => {
            const threshold = i.min_stock_threshold || 0;
            return i.current_stock <= threshold && threshold > 0;
          }).length;
          lowStockCount.textContent = low;
        }
      }

      if (usage && monthlyUsage) {
        monthlyUsage.textContent = this.#formatCurrency(
          usage.monthly_usage || 0,
        );
      } else if (monthlyUsage) {
        // If no usage data, show 0 or a dash
        monthlyUsage.textContent = this.#formatCurrency(0);
      }
    }

    // ─── Rendering: Alerts ────────────────────────────────────
    #renderAlerts(alerts) {
      const container = this.#dom.alertList;
      if (!container) return;
      if (!alerts || alerts.length === 0) {
        container.innerHTML =
          '<div class="alert-item" style="color:var(--gray-500);">✅ All items are well stocked</div>';
        return;
      }
      container.innerHTML = alerts
        .map(
          (alert) => `
                <div class="alert-item ${alert.status === "critical" ? "critical" : "warning"}">
                    <div>
                        <strong>${this.#escapeHtml(alert.name)}</strong>
                        <span>${this.#escapeHtml(alert.category)} • Stock: ${alert.current_stock}</span>
                    </div>
                    <span class="alert-badge">${alert.status === "critical" ? "Critical" : "Low Stock"}</span>
                </div>
            `,
        )
        .join("");
    }

    // ─── Rendering: Movements ─────────────────────────────────
    #renderMovements(movements) {
      const container = this.#dom.movementList;
      if (!container) return;
      if (!movements || movements.length === 0) {
        container.innerHTML =
          '<div style="color:var(--gray-500);font-size:0.85rem;">No recent movements</div>';
        return;
      }
      container.innerHTML = movements
        .slice(0, 5)
        .map((move) => {
          const icon = move.type === "in" ? "fa-arrow-down" : "fa-arrow-up";
          const className = move.type === "in" ? "stock-in" : "stock-out";
          return `
                    <div class="movement-item ${className}">
                        <i class="fas ${icon}"></i>
                        <div>
                            <strong>${move.type === "in" ? "+" : "-"}${move.quantity}</strong>
                            <small>${this.#escapeHtml(move.item_name || "Unknown")}</small>
                        </div>
                    </div>
                `;
        })
        .join("");
    }

    // ─── Filters ──────────────────────────────────────────────
    #applyFilters() {
      const keyword =
        this.#dom.searchInventory?.value.toLowerCase().trim() || "";
      const category = this.#dom.categoryFilter?.value || "";
      const stockStatus = this.#dom.stockFilter?.value || "";

      let filtered = [...this.#state.items];

      if (keyword) {
        filtered = filtered.filter(
          (item) =>
            item.name.toLowerCase().includes(keyword) ||
            item.category.toLowerCase().includes(keyword),
        );
      }
      if (category) {
        filtered = filtered.filter((item) => item.category === category);
      }
      if (stockStatus) {
        filtered = filtered.filter((item) => {
          const threshold = item.min_stock_threshold || 0;
          const criticalLevel = Math.floor(threshold / 2);
          if (stockStatus === "critical")
            return item.current_stock <= criticalLevel && threshold > 0;
          if (stockStatus === "low")
            return (
              item.current_stock <= threshold &&
              item.current_stock > criticalLevel &&
              threshold > 0
            );
          if (stockStatus === "normal")
            return item.current_stock > threshold || threshold === 0;
          return true;
        });
      }
      this.#renderTable(filtered);
    }

    // ─── Item Details ─────────────────────────────────────────
    #showItemDetails(id) {
      const item = this.#state.items.find((x) => x.id === id);
      if (!item) {
        this.#showToast("Item not found", "error");
        return;
      }

      this.#state.selectedId = id;
      const status = this.#getStockStatus(item);
      const totalValue = item.current_stock * item.cost_price;
      const content = this.#dom.itemDetailContent;
      if (!content) return;

      content.innerHTML = `
                <div class="detail-grid">
                    <div class="detail-card">
                        <label>Item Name</label>
                        <strong>${this.#escapeHtml(item.name)}</strong>
                    </div>
                    <div class="detail-card">
                        <label>Category</label>
                        <strong>${this.#escapeHtml(item.category)}</strong>
                    </div>
                    <div class="detail-card">
                        <label>Current Stock</label>
                        <strong>${item.current_stock} ${this.#escapeHtml(item.unit)}</strong>
                    </div>
                    <div class="detail-card">
                        <label>Reorder Level</label>
                        <strong>${item.min_stock_threshold || 0}</strong>
                    </div>
                    <div class="detail-card">
                        <label>Unit Cost</label>
                        <strong>${this.#formatCurrency(item.cost_price)}</strong>
                    </div>
                    <div class="detail-card">
                        <label>Total Value</label>
                        <strong>${this.#formatCurrency(totalValue)}</strong>
                    </div>
                    <div class="detail-card">
                        <label>Status</label>
                        <strong>${status.label}</strong>
                    </div>
                    <div class="detail-card">
                        <label>Condition</label>
                        <strong>${item.status === "active" ? "Active" : "Inactive"}</strong>
                    </div>
                    <div class="detail-card" style="grid-column: span 2;">
                        <label>Supplier</label>
                        <strong>${this.#escapeHtml(item.supplier || "—")}</strong>
                    </div>
                </div>
            `;

      const actions = this.#dom.detailActionsBottom;
      const editBtn = this.#dom.editItemBtn;
      const deleteBtn = this.#dom.deleteItemBtn;
      if (actions) actions.style.display = "flex";
      if (editBtn) editBtn.style.display = "inline-flex";
      if (deleteBtn) deleteBtn.style.display = "inline-flex";
    }

    #showEmptyDetail() {
      const content = this.#dom.itemDetailContent;
      if (!content) return;
      content.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-box-open"></i>
                    <h4>No Item Selected</h4>
                    <p>Select an inventory item to view detailed information.</p>
                </div>
            `;
      const actions = this.#dom.detailActionsBottom;
      const editBtn = this.#dom.editItemBtn;
      const deleteBtn = this.#dom.deleteItemBtn;
      if (actions) actions.style.display = "none";
      if (editBtn) editBtn.style.display = "none";
      if (deleteBtn) deleteBtn.style.display = "none";
    }

    // ─── Modal ────────────────────────────────────────────────
    #openModal(editMode = false, item = null) {
      const modal = this.#dom.inventoryModal;
      if (!modal) return;
      const title = this.#dom.modalTitle;
      const form = this.#dom.inventoryForm;

      if (editMode && item) {
        title.textContent = "Edit Inventory Item";
        this.#dom.editId.value = item.id;
        this.#dom.itemName.value = item.name || "";
        this.#dom.itemCategory.value = item.category || "";
        this.#dom.itemStock.value = item.current_stock || 0;
        this.#dom.itemUnit.value = item.unit || "";
        this.#dom.itemCost.value = item.cost_price || 0;
        this.#dom.reorderLevel.value = item.min_stock_threshold || 0;
        this.#dom.itemSupplier.value = item.supplier || "";
      } else {
        title.textContent = "Add Inventory Item";
        form.reset();
        this.#dom.editId.value = "";
        this.#dom.itemStock.value = 0;
        this.#dom.reorderLevel.value = 5;
      }
      modal.classList.add("active");
      document.body.style.overflow = "hidden";
    }

    #closeModal() {
      const modal = this.#dom.inventoryModal;
      if (modal) modal.classList.remove("active");
      document.body.style.overflow = "";
    }

    // ─── Form Submit ──────────────────────────────────────────
    async #handleFormSubmit(e) {
      e.preventDefault();
      if (this.#state.isSubmitting) return;
      this.#state.isSubmitting = true;

      const id = this.#dom.editId.value;
      const payload = {
        name: this.#dom.itemName.value.trim(),
        category: this.#dom.itemCategory.value,
        unit: this.#dom.itemUnit.value,
        current_stock: parseInt(this.#dom.itemStock.value) || 0,
        cost_price: parseFloat(this.#dom.itemCost.value) || 0,
        min_stock_threshold: parseInt(this.#dom.reorderLevel.value) || 0,
        supplier: this.#dom.itemSupplier.value.trim() || null,
      };

      try {
        let url = `${API_BASE}/`;
        let method = "POST";
        if (id) {
          url = `${API_BASE}/${id}`;
          method = "PUT";
        }
        await this.#fetchJSON(url, { method, body: JSON.stringify(payload) });
        this.#showToast(id ? "Item updated" : "Item added");
        this.#closeModal();
        await this.#loadData(false);
        if (id && this.#state.selectedId === id) {
          this.#showItemDetails(id);
        }
      } catch (err) {
        console.error(err);
        this.#showToast(err.message || "Save failed", "error");
      } finally {
        this.#state.isSubmitting = false;
      }
    }

    // ─── Actions ──────────────────────────────────────────────
    #editSelectedItem() {
      if (!this.#state.selectedId) return;
      const item = this.#state.items.find(
        (x) => x.id === this.#state.selectedId,
      );
      if (item) this.#openModal(true, item);
    }

    async #deleteSelectedItem() {
      if (!this.#state.selectedId) return;
      if (!confirm("Delete this inventory item permanently?")) return;

      try {
        await this.#fetchJSON(`${API_BASE}/${this.#state.selectedId}`, {
          method: "DELETE",
        });
        this.#showToast("Item deleted");
        await this.#loadData(false);
        this.#showEmptyDetail();
        this.#state.selectedId = null;
      } catch (err) {
        console.error(err);
        this.#showToast("Delete failed", "error");
      }
    }

    #handleReorder() {
      if (!this.#state.selectedId) return;
      const item = this.#state.items.find(
        (x) => x.id === this.#state.selectedId,
      );
      if (!item) return;
      const qty = prompt(
        `Enter reorder quantity for "${item.name}":`,
        item.min_stock_threshold * 2 || 10,
      );
      if (qty === null) return;
      const quantity = parseInt(qty);
      if (isNaN(quantity) || quantity < 1) {
        this.#showToast("Invalid quantity", "error");
        return;
      }
      // TODO: Implement reorder logic
      this.#showToast(
        `Reorder for ${item.name}: ${quantity} ${item.unit} (feature coming soon)`,
      );
    }

    #handleHistory() {
      if (!this.#state.selectedId) return;
      const item = this.#state.items.find(
        (x) => x.id === this.#state.selectedId,
      );
      if (!item) return;
      this.#showToast(`History for ${item.name} (feature coming soon)`);
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

    #getStockStatus(item) {
      const threshold = item.min_stock_threshold || 0;
      const criticalLevel = Math.floor(threshold / 2);
      if (item.current_stock <= criticalLevel && threshold > 0) {
        return { label: "Critical", className: "status-critical" };
      }
      if (item.current_stock <= threshold && threshold > 0) {
        return { label: "Low Stock", className: "status-low" };
      }
      return { label: "Normal", className: "status-normal" };
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
    new InventoryManager();
  });
})();
