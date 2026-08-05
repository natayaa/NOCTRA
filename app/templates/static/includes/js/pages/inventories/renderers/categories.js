// ============================================================
// inventories/renderers/categories.js - Categories Rendering
// ============================================================

import { DOM } from "../dom.js";
import { escapeHtml } from "../formatters.js";

export function renderCategories(categories) {
  const list = DOM.categoryList();
  if (!list) return;

  if (!categories || categories.length === 0) {
    list.innerHTML = '<div class="loading-placeholder-sm">No categories</div>';
    return;
  }

  list.innerHTML = categories
    .map(
      (cat) => `
        <span class="category-chip" onclick="window.filterByCategory('${cat}')">${escapeHtml(cat)}</span>
    `,
    )
    .join("");
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
            <option value="${cat}">${escapeHtml(cat)}</option>
        `,
          )
          .join("")}
    `;
  filter.value = currentValue || "";
}
