// projects/renderers/dashboard.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { Formatter } from "../formatters.js";

export function updateDashboard(stats) {
  if (!stats) return;

  // ✅ Try different possible data structures
  const byStatus = stats.by_status || {};
  const financial = stats.financial || {};

  const active =
    byStatus.active || stats.active_count || stats.active_projects || 0;
  const inProgress =
    byStatus.in_progress ||
    stats.in_production_count ||
    stats.in_progress_count ||
    0;
  const completed =
    byStatus.completed ||
    stats.completed_this_month ||
    stats.completed_count ||
    0;
  const revenue =
    financial.estimated_revenue ||
    stats.estimated_revenue ||
    stats.total_revenue ||
    0;

  const activeEl = DOM.activeCount();
  const prodEl = DOM.prodCount();
  const completedEl = DOM.completedCount();
  const revenueEl = DOM.revenueTotal();

  if (activeEl) {
    activeEl.textContent = typeof active === "number" ? active : 0;
    // Add animation
    animateNumber(activeEl, 0, typeof active === "number" ? active : 0);
  }
  if (prodEl) {
    prodEl.textContent = typeof inProgress === "number" ? inProgress : 0;
    animateNumber(prodEl, 0, typeof inProgress === "number" ? inProgress : 0);
  }
  if (completedEl) {
    completedEl.textContent = typeof completed === "number" ? completed : 0;
    animateNumber(
      completedEl,
      0,
      typeof completed === "number" ? completed : 0,
    );
  }
  if (revenueEl) {
    revenueEl.textContent = Formatter.currency(revenue);
  }

  // ✅ Update additional stats if available
  const totalProjectsEl = document.getElementById("totalProjects");
  if (totalProjectsEl && stats.total) {
    totalProjectsEl.textContent = stats.total;
  }

  const totalValueEl = document.getElementById("totalValue");
  if (totalValueEl && financial.total_value) {
    totalValueEl.textContent = Formatter.currency(financial.total_value);
  }

  console.log("📊 Dashboard updated:", {
    active,
    inProgress,
    completed,
    revenue,
  });
}

function animateNumber(el, start, end) {
  if (!el || start === end) return;
  const duration = 500;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const current = Math.round(start + (end - start) * easeOutQuad(progress));
    el.textContent = current;
    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      el.textContent = end;
    }
  }

  requestAnimationFrame(update);
}

function easeOutQuad(t) {
  return t * (2 - t);
}

export function updateProjectCounts(counts) {
  if (!counts) return;

  const totalEl = document.getElementById("projectTotalCount");
  const activeEl = DOM.activeCount();
  const completedEl = DOM.completedCount();

  if (totalEl) totalEl.textContent = counts.total || 0;
  if (activeEl) activeEl.textContent = counts.active || 0;
  if (completedEl) completedEl.textContent = counts.completed || 0;
}

export function updateRevenueDisplay(amount) {
  const el = DOM.revenueTotal();
  if (el) {
    el.textContent = Formatter.currency(amount);
    // Add pulse animation
    el.style.animation = "pulse 0.3s ease";
    setTimeout(() => {
      el.style.animation = "";
    }, 300);
  }
}

// ✅ Add pulse animation to document
const style = document.createElement("style");
style.textContent = `
  @keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
  }
`;
if (!document.querySelector("#dashboard-styles")) {
  style.id = "dashboard-styles";
  document.head.appendChild(style);
}
