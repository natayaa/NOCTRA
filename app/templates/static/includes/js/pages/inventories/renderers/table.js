// ============================================================
// inventories/renderers/table.js - Table Rendering
// ============================================================

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../formatters.js";
import { state } from "../config.js";

export function showLoadingState() {
  const list = DOM.inventoryItemsList();
  if (list) {
    list.innerHTML = `
            <tr>
                <td colspan="7" class="loading-placeholder">
                    <i class="fas fa-spinner fa-spin"></i> Loading inventory...
                </td>
            </tr>
        `;
  }
}

export function renderItems(items) {
  const list = DOM.inventoryItemsList();
  if (!list) return;

  if (!items || items.length === 0) {
    list.innerHTML = `
            <tr>
                <td colspan="7" class="no-data">
                    <i class="fas fa-box-open" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                    No inventory items found
                    <br><br>
                    <button class="btn-add-item" onclick="window.openCreateModal()">
                        <i class="fas fa-plus"></i> Add your first item
                    </button>
                </td>
            </tr>
        `;
    return;
  }

  list.innerHTML = items
    .map((item) => {
      const stock = Number(item.current_stock) || 0;
      const threshold = Number(item.min_stock_threshold) || 0;
      const stockStatus = Formatter.stockStatus(stock, threshold);
      const value = stock * (Number(item.cost_price) || 0);
      const status = item.status || "active";

      return `
            <tr class="fade-in ${state.selectedItemId === item.id ? "selected" : ""}" 
                onclick="window.selectItem('${item.id}')" 
                style="cursor:pointer;">
                <td>
                    <strong style="color:var(--text-primary);">${escapeHtml(item.name)}</strong>
                    ${item.sku ? `<br><small style="color:var(--text-muted);font-size:0.7rem;">SKU: ${escapeHtml(item.sku)}</small>` : ""}
                </td>
                <td>
                    <span class="category-badge" style="background:rgba(var(--primary-rgb),0.08);color:var(--primary);padding:0.15rem 0.6rem;border-radius:var(--radius-full);font-size:0.65rem;font-weight:600;text-transform:uppercase;">
                        ${escapeHtml(item.category || "-")}
                    </span>
                    ${item.sub_category ? `<br><small style="color:var(--text-muted);font-size:0.7rem;">${escapeHtml(item.sub_category)}</small>` : ""}
                </td>
                <td>
                    <span class="stock-level">
                        <span class="dot ${stockStatus.dot}"></span>
                        ${stockStatus.label}
                    </span>
                    <br><small style="color:var(--text-muted);font-size:0.75rem;">${stock} ${escapeHtml(item.unit || "")}</small>
                </td>
                <td>${escapeHtml(item.unit || "-")}</td>
                <td>
                    <span class="status-badge ${Formatter.statusBadge(status)}">
                        ${Formatter.statusLabel(status)}
                    </span>
                </td>
                <td style="font-weight:500;color:var(--text-primary);">
                    ${Formatter.currency(value)}
                </td>
                <!--td style="text-align:center; white-space:nowrap;">
                    <button class="btn-action btn-edit" onclick="event.stopPropagation(); window.openEditModal('${item.id}')" title="Edit">
                        <i class="fas fa-pen"></i>
                    </button>
                    <button class="btn-action btn-delete" onclick="event.stopPropagation(); window.confirmDelete('${item.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </td-->
            </tr>
        `;
    })
    .join("");
}

export function updatePagination(page, totalPages, totalItems) {
  const info = DOM.pageInfo();
  if (info) {
    info.textContent = `Page ${page} of ${totalPages || 1} (${totalItems} items)`;
  }
  const prev = DOM.prevPageBtn();
  const next = DOM.nextPageBtn();
  if (prev) prev.disabled = page <= 1;
  if (next) next.disabled = page >= totalPages;
}

export function updateDashboard(stats) {
  if (!stats) return;
  const totalValue = DOM.totalValue();
  const totalItems = DOM.totalItems();
  const lowStockCount = DOM.lowStockCount();
  const monthlyUsage = DOM.monthlyUsage();

  if (totalValue)
    totalValue.textContent = Formatter.currency(stats.total_value || 0);
  if (totalItems) totalItems.textContent = stats.total_items || 0;
  if (lowStockCount) lowStockCount.textContent = stats.low_stock_items || 0;
  if (monthlyUsage)
    monthlyUsage.textContent = Formatter.currency(stats.monthly_usage || 0);
}
