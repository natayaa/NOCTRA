// ============================================================
// inventories/renderers/detail.js - Detail Panel Rendering
// ============================================================

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../formatters.js";
import { state } from "../config.js";

export function renderDetailPanel(item) {
  const content = DOM.itemDetailContent();
  if (!content) return;

  if (!item) {
    content.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-box-open"></i>
                <h4>No Item Selected</h4>
                <p>Select an inventory item from the table to view detailed information.</p>
            </div>
        `;
    hideDetailActions();
    return;
  }

  const stock = Number(item.current_stock) || 0;
  const threshold = Number(item.min_stock_threshold) || 5;
  const stockStatus = Formatter.stockStatus(stock, threshold);
  const costPrice = Number(item.cost_price) || 0;
  const sellingPrice = Number(item.selling_price) || 0;
  const totalValue = stock * costPrice;
  const profitMargin =
    sellingPrice > 0 ? ((sellingPrice - costPrice) / sellingPrice) * 100 : 0;
  const status = item.status || "active";

  content.innerHTML = `
        <div style="margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);">
            <h3 style="margin:0; font-size:1.1rem; color:var(--text-primary);">${escapeHtml(item.name)}</h3>
            ${item.sku ? `<span style="font-size:0.8rem; color:var(--text-muted);">SKU: ${escapeHtml(item.sku)}</span>` : ""}
        </div>
        
        <div class="detail-info-grid">
            ${createDetailRow(
              "Category",
              `
                <span class="category-badge" style="background:rgba(var(--primary-rgb),0.08);color:var(--primary);padding:0.15rem 0.6rem;border-radius:var(--radius-full);font-size:0.65rem;font-weight:600;text-transform:uppercase;">
                    ${escapeHtml(item.category || "-")}
                </span>
                ${item.sub_category ? `→ ${escapeHtml(item.sub_category)}` : ""}
            `,
            )}
            ${createDetailRow("Unit", escapeHtml(item.unit || "-"))}
            ${createDetailRow(
              "Current Stock",
              `
                <span class="stock-level">
                    <span class="dot ${stockStatus.dot}" style="display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;
                        ${
                          stockStatus.dot === "normal"
                            ? "background:#00d578;"
                            : stockStatus.dot === "low"
                              ? "background:#f59e0b;"
                              : stockStatus.dot === "critical"
                                ? "background:#ef4444;"
                                : "background:var(--text-muted);"
                        }"></span>
                    ${stockStatus.label}
                </span>
                <br><span style="font-size:0.85rem;">${stock} ${escapeHtml(item.unit || "")}</span>
            `,
            )}
            ${createDetailRow("Min Stock Threshold", `${threshold} ${escapeHtml(item.unit || "")}`)}
            ${createDetailRow("Cost Price", `<strong>${Formatter.currency(costPrice)}</strong>`)}
            ${createDetailRow("Selling Price", `<strong>${Formatter.currency(sellingPrice)}</strong>`)}
            ${createDetailRow("Total Inventory Value", `<strong style="color:var(--primary);">${Formatter.currency(totalValue)}</strong>`)}
            ${createDetailRow(
              "Profit Margin",
              `
                <span style="color:${profitMargin > 0 ? "#00d578" : "#ef4444"};">
                    ${profitMargin > 0 ? "+" : ""}${profitMargin.toFixed(1)}%
                </span>
            `,
            )}
            ${createDetailRow("Location", escapeHtml(item.location || "-"))}
            ${createDetailRow("Supplier", escapeHtml(item.supplier_name || item.supplier_id || "-"))}
            ${createDetailRow(
              "Status",
              `
                <span class="status-badge ${Formatter.statusBadge(status)}" 
                    style="display:inline-block;padding:0.15rem 0.7rem;border-radius:var(--radius-full);font-size:0.7rem;font-weight:600;
                    ${
                      status === "active"
                        ? "background:rgba(0,213,120,0.12);color:#00d578;"
                        : status === "out_of_stock"
                          ? "background:rgba(239,68,68,0.12);color:#ef4444;"
                          : "background:rgba(255,255,255,0.06);color:var(--text-muted);"
                    }">
                    ${Formatter.statusLabel(status)}
                </span>
                ${item.is_low_stock ? ' <span style="color:#f59e0b;font-size:0.8rem;">⚠️ Low Stock</span>' : ""}
                ${item.is_out_of_stock ? ' <span style="color:#ef4444;font-size:0.8rem;">🚫 Out of Stock</span>' : ""}
            `,
              "span-2",
            )}
            ${createDetailRow("Description", escapeHtml(item.description || "No description provided."), "span-2")}
            ${createDetailRow("Last Updated", Formatter.dateTime(item.updated_at || item.created_at), "span-2")}
        </div>
    `;

  showDetailActions();
  state.selectedItemData = item;
  state.selectedItemId = item.id;
}

function createDetailRow(label, value, span = "") {
  return `
        <div class="detail-info-item" style="${span === "span-2" ? "grid-column: span 2;" : ""}display:flex;flex-direction:column;gap:0.1rem;">
            <label style="font-size:0.65rem; text-transform:uppercase; letter-spacing:0.04em; color:var(--text-muted);">${label}</label>
            <p style="margin:0; font-size:0.9rem; color:var(--text-primary);">${value}</p>
        </div>
    `;
}

function showDetailActions() {
  const editBtn = DOM.editItemBtn();
  const deleteBtn = DOM.deleteItemBtn();
  const actions = DOM.detailActionsBottom();

  if (editBtn) {
    editBtn.style.display = "inline-flex";
    editBtn.title = "Edit Item";
  }
  if (deleteBtn) {
    deleteBtn.style.display = "inline-flex";
    deleteBtn.title = "Delete Item";
  }
  if (actions) {
    actions.style.display = "flex";
    actions.querySelectorAll(".btn").forEach((btn, i) => {
      btn.style.animationDelay = `${i * 0.1}s`;
    });
  }
}

function hideDetailActions() {
  const editBtn = DOM.editItemBtn();
  const deleteBtn = DOM.deleteItemBtn();
  const actions = DOM.detailActionsBottom();

  if (editBtn) editBtn.style.display = "none";
  if (deleteBtn) deleteBtn.style.display = "none";
  if (actions) actions.style.display = "none";
}
