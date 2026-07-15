// ============================================================
// dashboard/handlers/events.js - Event Binding
// ============================================================

import { DOM } from "../dom.js";
import { loadDashboardData } from "../index.js";
import { showToast } from "../../shared/toast.js";

let refreshInterval = null;

export function bindEvents() {
  // Refresh button
  const refreshBtn = DOM.refreshBtn();
  if (refreshBtn) {
    refreshBtn.addEventListener("click", handleRefresh);
  }

  // Auto-refresh every 60 seconds (optional)
  // startAutoRefresh(60000);

  // Keyboard shortcut: Ctrl+R untuk refresh
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey && e.key === "r" && !e.shiftKey) {
      e.preventDefault();
      handleRefresh();
    }
  });

  console.log("✅ Dashboard events bound");
}

async function handleRefresh() {
  const refreshBtn = DOM.refreshBtn();
  if (refreshBtn) {
    const icon = refreshBtn.querySelector("i");
    if (icon) {
      icon.style.animation = "spin 0.6s linear";
      setTimeout(() => {
        icon.style.animation = "";
      }, 600);
    }
  }

  showToast("🔄 Refreshing dashboard...", "info", 1500);
  await loadDashboardData();
  showToast("✅ Dashboard updated", "success", 1500);
}

export function startAutoRefresh(intervalMs = 60000) {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  refreshInterval = setInterval(() => {
    console.log("🔄 Auto-refreshing dashboard...");
    loadDashboardData();
  }, intervalMs);
}

export function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}
