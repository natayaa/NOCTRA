// ============================================================
// projects/utils.js - Utility Functions
// ============================================================

import { state } from "./config.js";

export function getProjectById(projectId) {
  return state.projects.find((p) => p.id === projectId);
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
    return [data];
  }
  return [];
}
