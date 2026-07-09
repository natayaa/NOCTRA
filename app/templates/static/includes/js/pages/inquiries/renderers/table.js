// ============================================================
// inquiries/renderers/table.js - Table Rendering
// ============================================================

import { DOM } from "../dom.js";
import { Formatter, escapeHtml } from "../formatters.js";
import { state } from "../config.js";

export function showLoadingState() {
  const body = DOM.inquiriesBody();
  if (!body) return;
  body.innerHTML = `
    <tr>
      <td colspan="7" style="text-align:center; padding:2rem;">
        <div class="spinner"></div>
        <p style="color:var(--text-muted);margin-top:0.5rem;">Loading inquiries...</p>
      </td>
    </tr>
  `;
}

export function renderInquiries(inquiries) {
  const body = DOM.inquiriesBody();
  if (!body) return;

  if (!inquiries || inquiries.length === 0) {
    body.innerHTML = `
            <tr>
                <td colspan="7" style="text-align:center; padding:2rem; color: var(--text-muted);">
                    <i class="ph ph-file-text" style="font-size:2rem; display:block; margin-bottom:0.5rem;"></i>
                    No inquiries found
                </td>
            </tr>
        `;
    return;
  }

  body.innerHTML = inquiries
    .map(
      (inquiry) => `
        <tr class="fade-in">
            <td>
                <strong>${escapeHtml(inquiry.customer_name)}</strong><br>
                <span style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(inquiry.customer_phone_number || "")}</span>
            </td>
            <td>
                <span style="font-weight:500;">${escapeHtml(inquiry.vehicle_brand)}</span>
                <span style="color:var(--text-muted);">${escapeHtml(inquiry.vehicle_model)}</span>
            </td>
            <td><span style="color:var(--text-secondary);">${escapeHtml(inquiry.project_type)}</span></td>
            <td>
                <span class="status-badge ${Formatter.statusBadge(inquiry.status)}">
                    ${Formatter.statusLabel(inquiry.status)}
                </span>
            </td>
            <td>
                ${
                  inquiry.project
                    ? `
                    <span class="project-status-badge ${Formatter.projectStatusBadge(inquiry.project.status)}">
                        ${inquiry.project.status || "Active"}
                    </span>
                `
                    : `
                    <span class="project-status-badge no-project">No Project</span>
                `
                }
            </td>
            <td style="font-size:0.8rem; color:var(--text-muted);">
                ${Formatter.date(inquiry.created_at)}
            </td>
            <td style="text-align:center;">
                <div class="actions">
                    <button class="action-btn view" onclick="window.openInquiryDrawer('${inquiry.id}')" title="View Details">
                        <i class="ph ph-eye"></i>
                    </button>
                    ${
                      ["new", "under_review"].includes(inquiry.status)
                        ? `
                        <button class="action-btn quote" onclick="window.openQuoteModal('${inquiry.id}')" title="Send Quote">
                            <i class="ph ph-file-text"></i>
                        </button>
                        <button class="action-btn approve" onclick="window.handleApprove('${inquiry.id}')" title="Approve">
                            <i class="ph ph-check-circle"></i>
                        </button>
                        <button class="action-btn reject" onclick="window.openRejectModal('${inquiry.id}')" title="Reject">
                            <i class="ph ph-x-circle"></i>
                        </button>
                    `
                        : ""
                    }
                    ${
                      ["approved", "quoted"].includes(inquiry.status)
                        ? `
                        <button class="action-btn convert" onclick="window.openConvertModal('${inquiry.id}')" title="Convert to Project">
                            <i class="ph ph-arrow-right"></i>
                        </button>
                    `
                        : ""
                    }
                    ${
                      inquiry.project
                        ? `
                        <button class="action-btn view" onclick="window.location.href='/projects/${inquiry.project.id}'" title="View Project">
                            <i class="ph ph-briefcase"></i>
                        </button>
                    `
                        : ""
                    }
                </div>
            </td>
        </tr>
    `,
    )
    .join("");
}

export function updatePagination(page, totalPages, totalItems) {
  const info = DOM.pageInfo();
  const prev = DOM.prevPage();
  const next = DOM.nextPage();

  if (info)
    info.textContent = `Page ${page} of ${totalPages || 1} (${totalItems} items)`;
  if (prev) prev.disabled = page <= 1;
  if (next) next.disabled = page >= totalPages;
}

export function updateDashboard(stats) {
  if (!stats) return;
  const totalCount = DOM.totalCount();
  const newCount = DOM.newCount();
  const quotedCount = DOM.quotedCount();
  const convertedCount = DOM.convertedCount();

  if (totalCount)
    totalCount.textContent = stats.total || stats.total_count || 0;
  if (newCount)
    newCount.textContent = stats.by_status?.new || stats.new_count || 0;
  if (quotedCount)
    quotedCount.textContent =
      stats.by_status?.quoted || stats.quoted_count || 0;
  if (convertedCount)
    convertedCount.textContent =
      stats.by_status?.converted || stats.converted_count || 0;
}
