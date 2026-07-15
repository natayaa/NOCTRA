// ============================================================
// restored-bikes/renderers/list.js - Grid Rendering
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";

const formatter = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export function renderList() {
  const grid = DOM.restoredGrid();
  if (!grid) return;

  const bikes = state.bikes;

  if (!bikes || bikes.length === 0) {
    grid.innerHTML = `
      <div class="loading-placeholder" style="grid-column:1/-1;">
        <i class="fas fa-motorcycle" style="font-size:2rem;opacity:0.3;display:block;margin-bottom:0.5rem;"></i>
        <p>No restored bikes found</p>
        <button class="btn-primary" onclick="window.openAddRestoredModal()" style="margin-top:0.5rem;">
          <i class="fas fa-plus"></i> Add your first bike
        </button>
      </div>
    `;
    return;
  }

  grid.innerHTML = bikes
    .map((bike) => {
      const status = bike.status || "completed";
      const statusLabel =
        status === "in_progress"
          ? "In Progress"
          : status.charAt(0).toUpperCase() + status.slice(1);
      const hasImage = bike.cover_image || bike.photos?.length > 0;
      const imageUrl =
        bike.cover_image || (bike.photos && bike.photos[0]?.url) || "";

      return `
        <div class="restored-card" data-id="${bike.id}" onclick="window.openRestoredDrawer('${bike.id}')">
          <div class="card-image">
            ${
              imageUrl
                ? `<img src="${imageUrl}" alt="${bike.brand} ${bike.model}" loading="lazy" />`
                : `
              <div class="placeholder">
                <i class="fas fa-motorcycle"></i>
              </div>
            `
            }
            <span class="status-badge ${status}">${statusLabel}</span>
          </div>
          <div class="card-body">
            <h3>${bike.brand || "Unknown"} ${bike.model || ""}</h3>
            <div class="card-meta">
              ${bike.year ? `<span><i class="fas fa-calendar"></i> ${bike.year}</span>` : ""}
              ${bike.license_plate ? `<span><i class="fas fa-id-card"></i> ${bike.license_plate}</span>` : ""}
              ${bike.restoration_cost ? `<span><i class="fas fa-coins"></i> ${formatter.format(bike.restoration_cost)}</span>` : ""}
            </div>
            ${bike.customer_name ? `<div class="card-customer"><i class="fas fa-user"></i> ${bike.customer_name}</div>` : ""}
          </div>
        </div>
      `;
    })
    .join("");
}

export function updatePagination(page, totalPages, totalItems) {
  const info = DOM.pageInfo();
  const prev = DOM.prevPageBtn();
  const next = DOM.nextPageBtn();

  if (info) {
    info.textContent = `Page ${page} of ${Math.max(1, totalPages)} (${totalItems} items)`;
  }
  if (prev) {
    prev.disabled = page <= 1;
    prev.style.opacity = page <= 1 ? "0.4" : "1";
  }
  if (next) {
    const isLast = page >= totalPages || totalPages === 0;
    next.disabled = isLast;
    next.style.opacity = isLast ? "0.4" : "1";
  }
}

export function updateStats(stats) {
  const total = DOM.totalRestored();
  const completed = DOM.completedRestored();
  const inProgress = DOM.inProgressRestored();
  const featured = DOM.featuredRestored();

  if (total) total.textContent = stats?.total || 0;
  if (completed) completed.textContent = stats?.completed || 0;
  if (inProgress) inProgress.textContent = stats?.in_progress || 0;
  if (featured) featured.textContent = stats?.featured || 0;
}
