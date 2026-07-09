// ============================================================
// projects/renderers/cards.js - Project Cards Rendering
// ============================================================

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
    .map(
      (project) => `
        <div class="project-card fade-in" data-id="${project.id}">
            <div class="card-header">
                <h3 class="project-name" onclick="window.openProjectDrawer('${project.id}')" style="cursor:pointer;">${escapeHtml(project.name)}</h3>
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
                    <span>${escapeHtml(project.customer_name || "Unknown")}</span>
                </div>
                <div class="vehicle-info">
                    <i class="ph ph-car"></i>
                    <span>${escapeHtml(project.vehicle_brand || "")} ${escapeHtml(project.vehicle_model || "")}</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar-wrapper">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width:${project.progress || 0}%;"></div>
                        </div>
                        <span class="progress-text">${project.progress || 0}%</span>
                    </div>
                    <button onclick="event.stopPropagation(); window.openProgressPopup('${project.id}')" class="btn-update-progress" title="Update Progress">
                        <i class="ph ph-gauge"></i> Update
                    </button>
                </div>
                <div class="card-meta">
                    <span class="badges-wrapper">
                        <span class="status-badge ${getStatusBadgeClass(project.status)}">${getStatusLabel(project.status)}</span>
                        <span class="priority-badge ${getPriorityBadgeClass(project.priority)}">${getPriorityLabel(project.priority)}</span>
                    </span>
                    <span class="project-date">
                        <i class="ph ph-calendar"></i> ${Formatter.date(project.created_at)}
                    </span>
                </div>
            </div>
        </div>
    `,
    )
    .join("");
}

export function updatePagination(page, totalPages, totalItems) {
  const info = DOM.pageInfo();
  const prev = DOM.prevPageBtn();
  const next = DOM.nextPageBtn();

  if (info)
    info.textContent = `Page ${page} of ${Math.max(1, totalPages)} (${totalItems} items)`;
  if (prev) {
    prev.disabled = page <= 1;
    prev.style.opacity = page <= 1 ? "0.5" : "1";
    prev.style.cursor = page <= 1 ? "not-allowed" : "pointer";
  }
  if (next) {
    const isLastPage = page >= totalPages || totalPages === 0;
    next.disabled = isLastPage;
    next.style.opacity = isLastPage ? "0.5" : "1";
    next.style.cursor = isLastPage ? "not-allowed" : "pointer";
  }
}
