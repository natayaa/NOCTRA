// ============================================================
// price_list/renderers/table.js - Table Rendering
// ============================================================

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../formatters.js";

export function showLoadingState() {
  const body = DOM.priceTableBody();
  if (!body) return;
  body.innerHTML = `
        <tr>
            <td colspan="8" class="loading-placeholder">
                <i class="fas fa-spinner fa-spin"></i> Loading prices...
            </td>
        </tr>
    `;
}

export function renderItems(items) {
  const body = DOM.priceTableBody();
  if (!body) return;

  if (!items || items.length === 0) {
    body.innerHTML = `
            <tr>
                <td colspan="8" class="no-data">
                    <i class="fas fa-box-open" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                    No price items found
                    <br><br>
                    <button class="btn-primary" onclick="window.openCreateModal()">
                        <i class="fas fa-plus"></i> Add your first price item
                    </button>
                </td>
            </tr>
        `;
    return;
  }

  body.innerHTML = items
    .map(
      (item) => `
        <tr class="fade-in">
            <td>
                <span class="category-badge ${Formatter.categoryBadgeClass(item.category)}">
                    ${Formatter.categoryLabel(item.category)}
                </span>
                ${item.sub_category ? `<br><small style="color:var(--text-muted);font-size:0.7rem;">${escapeHtml(item.sub_category)}</small>` : ""}
            </td>
            <td>
                <strong style="color:var(--text-primary);">${escapeHtml(item.name)}</strong>
                ${item.sku ? `<br><small style="color:var(--text-muted);font-size:0.7rem;">SKU: ${escapeHtml(item.sku)}</small>` : ""}
            </td>
            <td style="max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                ${escapeHtml(item.description || "-")}
            </td>
            <td style="font-weight:600; color:var(--text-primary);">
                ${Formatter.currency(item.price)}
                ${item.cost_price ? `<br><small style="color:var(--text-muted);font-weight:400;font-size:0.7rem;">Cost: ${Formatter.currency(item.cost_price)}</small>` : ""}
            </td>
            <td>${escapeHtml(item.unit || "-")}</td>
            <td>
                ${item.vehicle_brand ? escapeHtml(item.vehicle_brand) : "-"}
                ${item.vehicle_model ? `<br><small style="color:var(--text-muted);font-size:0.7rem;">${escapeHtml(item.vehicle_model)}</small>` : ""}
            </td>
            <td>
                <span class="status-badge ${item.is_active ? "active" : "inactive"}">
                    ${item.is_active ? "Active" : "Inactive"}
                </span>
                ${item.is_expired ? '<br><small style="color:#ef4444;font-size:0.65rem;">Expired</small>' : ""}
            </td>
            <td style="text-align:center; white-space:nowrap;">
                <button class="action-btn history-btn" onclick="window.openHistoryModal('${item.id}')" title="Price History">
                    <i class="fas fa-history"></i>
                </button>
                <button class="action-btn edit-btn" onclick="window.openEditModal('${item.id}')" title="Edit">
                    <i class="fas fa-pen"></i>
                </button>
                <button class="action-btn delete-btn" onclick="window.confirmDelete('${item.id}')" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `,
    )
    .join("");
}

export function updatePagination(page, totalPages, totalItems) {
  const info = DOM.pageInfo();
  const prev = DOM.prevPageBtn();
  const next = DOM.nextPageBtn();

  if (info)
    info.textContent = `Page ${page} of ${totalPages || 1} (${totalItems} items)`;
  if (prev) {
    prev.disabled = page <= 1;
    prev.style.opacity = page <= 1 ? "0.5" : "1";
    prev.style.cursor = page <= 1 ? "not-allowed" : "pointer";
  }
  if (next) {
    next.disabled = page >= totalPages || totalPages === 0;
    next.style.opacity = page >= totalPages || totalPages === 0 ? "0.5" : "1";
    next.style.cursor =
      page >= totalPages || totalPages === 0 ? "not-allowed" : "pointer";
  }
}

export function updateDashboard(stats) {
  if (!stats) return;
  const totalItems = DOM.totalItems();
  const activeItems = DOM.activeItems();
  const expiringItems = DOM.expiringItems();
  const categoryCount = DOM.categoryCount();

  if (totalItems) totalItems.textContent = stats.total_items || 0;
  if (activeItems) activeItems.textContent = stats.active_items || 0;
  if (expiringItems) expiringItems.textContent = stats.expiring_soon || 0;
  if (categoryCount) categoryCount.textContent = stats.total_categories || 0;
}

export function updateCategoryFilter(categories) {
  if (!categories || categories.length === 0) return;
  const filter = DOM.categoryFilter();
  if (!filter) return;

  const currentValue = filter.value;
  filter.innerHTML = `
        <option value="">All Categories</option>
        ${categories
          .map(
            (cat) => `
            <option value="${cat.name}">${cat.display_name || cat.name} (${cat.item_count || 0})</option>
        `,
          )
          .join("")}
    `;
  filter.value = currentValue || "";
}
