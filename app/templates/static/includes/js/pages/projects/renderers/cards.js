// projects/renderers/cards.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import {
  Formatter,
  escapeHtml,
  getStatusBadgeClass,
  getPriorityBadgeClass,
  getStatusLabel,
  getPriorityLabel,
} from "../formatters.js";
import { state } from "../config.js";

export function showLoadingState() {
  const grid = DOM.projectCardGrid();
  if (!grid) return;
  grid.innerHTML = `
    <div class="loading-placeholder" style="grid-column:1/-1; text-align:center; padding:3rem 0;">
      <i class="ph ph-spinner" style="font-size:2rem; animation: spin 1s linear infinite;"></i>
      <p style="margin-top:0.5rem; color:var(--text-muted);">Loading projects...</p>
    </div>
  `;
}

export function renderProjects(projects) {
  const grid = DOM.projectCardGrid();
  if (!grid) return;

  if (!projects || projects.length === 0) {
    grid.innerHTML = `
      <div style="grid-column:1/-1; text-align:center; padding:3rem 0; color: var(--text-muted);">
        <i class="ph ph-folder-open" style="font-size:3rem; display:block; margin-bottom:1rem;"></i>
        <p>No projects found</p>
        <button class="btn-primary" onclick="window.openCreateProjectModal()">
          <i class="ph ph-plus"></i> Create your first project
        </button>
      </div>
    `;
    return;
  }

  grid.innerHTML = projects
    .map((project) => {
      const progress = project.progress || 0;
      const statusClass = getStatusBadgeClass(project.status);
      const priorityClass = getPriorityBadgeClass(project.priority);
      const statusLabel = getStatusLabel(project.status);
      const priorityLabel = getPriorityLabel(project.priority);
      const createdDate = project.created_at
        ? Formatter.date(project.created_at)
        : "-";
      const customerName = project.customer_name || "Unknown";
      const vehicleInfo =
        [project.vehicle_brand, project.vehicle_model]
          .filter(Boolean)
          .join(" ") || "-";

      return `
      <div class="project-card fade-in" data-id="${project.id}">
        <div class="card-header">
          <h3 class="project-name" onclick="window.openProjectDrawer('${project.id}')" style="cursor:pointer;" title="${escapeHtml(project.name)}">
            ${escapeHtml(project.name)}
          </h3>
          <div class="card-actions">
            <button onclick="event.stopPropagation(); window.openEditProjectModal('${project.id}')" title="Edit Project" class="card-action-btn">
              <i class="ph ph-pencil-simple"></i>
            </button>
            <button onclick="event.stopPropagation(); window.confirmDeleteProject('${project.id}')" title="Delete Project" class="card-action-btn">
              <i class="ph ph-trash"></i>
            </button>
          </div>
        </div>
        <div class="card-body" onclick="window.openProjectDrawer('${project.id}')" style="cursor:pointer;">
          <div class="customer-info">
            <i class="ph ph-user"></i>
            <span>${escapeHtml(customerName)}</span>
          </div>
          <div class="vehicle-info">
            <i class="ph ph-car"></i>
            <span>${escapeHtml(vehicleInfo)}</span>
          </div>
          <div class="progress-container">
            <div class="progress-bar-wrapper">
              <div class="progress-bar">
                <div class="progress-fill" style="width:${progress}%;"></div>
              </div>
              <span class="progress-text">${progress}%</span>
            </div>
            <button onclick="event.stopPropagation(); window.openProgressPopup('${project.id}')" class="btn-update-progress" title="Update Progress">
              <i class="ph ph-gauge"></i> Update
            </button>
          </div>
          <div class="card-meta">
            <span class="badges-wrapper">
              <span class="status-badge ${statusClass}">${statusLabel}</span>
              <span class="priority-badge ${priorityClass}">${priorityLabel}</span>
            </span>
            <span class="project-date">
              <i class="ph ph-calendar"></i> ${createdDate}
            </span>
          </div>
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

  const displayTotalPages = Math.max(1, totalPages);
  if (info)
    info.textContent = `Page ${page} of ${displayTotalPages} (${totalItems} items)`;

  // ✅ Pakai class, bukan inline style
  if (prev) {
    prev.classList.toggle("disabled", page <= 1);
    prev.disabled = page <= 1;
  }
  if (next) {
    next.classList.toggle("disabled", page >= totalPages || totalPages === 0);
    next.disabled = page >= totalPages || totalPages === 0;
  }
}

export function highlightProjectCard(projectId) {
  const cards = document.querySelectorAll(".project-card");
  cards.forEach((card) => {
    card.classList.remove("selected");
    if (card.dataset.id === projectId) {
      card.classList.add("selected");
    }
  });
}

export function getProjectCard(projectId) {
  return document.querySelector(`.project-card[data-id="${projectId}"]`);
}
