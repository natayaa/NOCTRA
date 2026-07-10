// projects/utils.js - Utility Functions (FIXED & IMPROVED)

import { state } from "./config.js";

export function getProjectById(projectId) {
  if (!projectId) return null;
  return state.projects.find((p) => p.id === projectId) || null;
}

export function getProjectByIndex(index) {
  return state.projects[index] || null;
}

export function getCurrentProject() {
  if (!state.currentProjectId) return null;
  return getProjectById(state.currentProjectId);
}

export function getDefaultLaborOptions() {
  return `
    <option value="">Select Labor Type</option>
    <option value="Sanding" data-rate="50000">Sanding (Rp 50,000/hour)</option>
    <option value="Priming" data-rate="60000">Priming (Rp 60,000/hour)</option>
    <option value="Painting" data-rate="75000">Painting (Rp 75,000/hour)</option>
    <option value="Clear Coat" data-rate="70000">Clear Coat (Rp 70,000/hour)</option>
    <option value="Polishing" data-rate="55000">Polishing (Rp 55,000/hour)</option>
    <option value="Fabrication" data-rate="80000">Fabrication (Rp 80,000/hour)</option>
    <option value="Assembly" data-rate="65000">Assembly (Rp 65,000/hour)</option>
    <option value="Restoration" data-rate="90000">Restoration (Rp 90,000/hour)</option>
    <option value="Body Work" data-rate="70000">Body Work (Rp 70,000/hour)</option>
    <option value="Quality Control" data-rate="90000">Quality Control (Rp 90,000/hour)</option>
    <option value="Technician - Junior" data-rate="80000">Technician - Junior (Rp 80,000/hour)</option>
    <option value="Technician - Senior" data-rate="120000">Technician - Senior (Rp 120,000/hour)</option>
    <option value="Other" data-rate="50000">Other (Rp 50,000/hour)</option>
  `;
}

export function getDefaultMaterialOptions() {
  return `
    <option value="">Select Material</option>
    <option value="mat-1" data-unit="liter" data-price="58000">Epoxy Primer Putih (liter) - Rp 58,000</option>
    <option value="mat-2" data-unit="liter" data-price="75000">Base Coat (liter) - Rp 75,000</option>
    <option value="mat-3" data-unit="liter" data-price="85000">Clear Coat (liter) - Rp 85,000</option>
    <option value="mat-4" data-unit="roll" data-price="50000">Masking Paper (roll) - Rp 50,000</option>
    <option value="mat-5" data-unit="liter" data-price="100000">Degreaser (liter) - Rp 100,000</option>
  `;
}

export function ensureArray(data) {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") {
    if (data.data && Array.isArray(data.data)) return data.data;
    if (data.items && Array.isArray(data.items)) return data.items;
    if (data.projects && Array.isArray(data.projects)) return data.projects;
    if (data.results && Array.isArray(data.results)) return data.results;
    return [data];
  }
  return [];
}

export function formatDate(dateString) {
  if (!dateString) return "-";
  try {
    return new Date(dateString).toLocaleDateString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "-";
  }
}

export function formatDateTime(dateString) {
  if (!dateString) return "-";
  try {
    return new Date(dateString).toLocaleString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "-";
  }
}

export function getStatusColor(status) {
  const map = {
    draft: "#94a3b8",
    active: "#3b82f6",
    in_progress: "#f59e0b",
    on_hold: "#94a3b8",
    completed: "#10b981",
    cancelled: "#ef4444",
  };
  return map[status] || "#94a3b8";
}

export function getStatusLabel(status) {
  const map = {
    draft: "Draft",
    active: "Active",
    in_progress: "In Progress",
    on_hold: "On Hold",
    completed: "Completed",
    cancelled: "Cancelled",
  };
  return map[status] || status;
}

export function getPriorityColor(priority) {
  const map = {
    low: "#94a3b8",
    medium: "#3b82f6",
    high: "#f59e0b",
    urgent: "#ef4444",
  };
  return map[priority] || "#94a3b8";
}

export function getPriorityLabel(priority) {
  const map = {
    low: "Low",
    medium: "Medium",
    high: "High",
    urgent: "Urgent",
  };
  return map[priority] || priority;
}

export function getProgressColor(progress) {
  if (progress >= 100) return "#10b981";
  if (progress >= 75) return "#3b82f6";
  if (progress >= 50) return "#f59e0b";
  if (progress >= 25) return "#f97316";
  return "#94a3b8";
}

export function calculateProgress(completed, total) {
  if (!total || total === 0) return 0;
  return Math.round((completed / total) * 100);
}

export function debounce(func, wait = 300) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

export function truncateText(text, maxLength = 50) {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + "...";
}

export function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
}
