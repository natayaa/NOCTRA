// projects/handlers/dropdowns.js

import { DOM } from "../dom.js";
import { ProjectAPI } from "../api.js";
import { Formatter, escapeHtml } from "../formatters.js";
import { getDefaultLaborOptions, getDefaultMaterialOptions } from "../utils.js";

// ============================================================
// MATERIAL DROPDOWN - LOAD PAINT & MATERIAL CATEGORIES
// ============================================================

export async function loadMaterialItems() {
  const select = DOM.materialSelect();
  if (!select) return;

  try {
    // ✅ Ambil dari 2 kategori: paint dan material
    const categories = ["paint", "material"];
    let allItems = [];

    for (const cat of categories) {
      const items = await ProjectAPI.fetchInventoryItems(100, cat);
      if (items && items.length > 0) {
        // Tambahkan category info ke setiap item
        const itemsWithCategory = items.map((item) => ({
          ...item,
          _category: cat,
        }));
        allItems = [...allItems, ...itemsWithCategory];
      }
    }

    console.log(
      `📦 Loaded ${allItems.length} inventory items (paint + material)`,
    );

    if (!allItems || allItems.length === 0) {
      select.innerHTML = `
        <option value="">No paint or material items available</option>
      `;
      return;
    }

    // ✅ Filter hanya item yang aktif
    const activeItems = allItems.filter(
      (item) =>
        item.is_active !== false &&
        item.status !== "inactive" &&
        item.status !== "discontinued",
    );

    if (activeItems.length === 0) {
      select.innerHTML = `
        <option value="">No active materials available</option>
      `;
      return;
    }

    // ✅ Urutkan berdasarkan nama
    const sortedItems = [...activeItems].sort((a, b) =>
      (a.name || "").localeCompare(b.name || ""),
    );

    // ✅ Group by category untuk optgroup
    const grouped = {};
    sortedItems.forEach((item) => {
      const cat = item._category || item.category || "Other";
      // Capitalize category name
      const displayCat = cat.charAt(0).toUpperCase() + cat.slice(1);
      if (!grouped[displayCat]) grouped[displayCat] = [];
      grouped[displayCat].push(item);
    });

    // ✅ Build options dengan optgroup
    let optionsHTML = `<option value="">Select Material</option>`;

    // Tentukan urutan kategori: Paint dulu, baru Material
    const categoryOrder = ["Paint", "Material"];
    const sortedCategories = Object.keys(grouped).sort((a, b) => {
      const indexA = categoryOrder.indexOf(a);
      const indexB = categoryOrder.indexOf(b);
      if (indexA === -1 && indexB === -1) return a.localeCompare(b);
      if (indexA === -1) return 1;
      if (indexB === -1) return -1;
      return indexA - indexB;
    });

    for (const cat of sortedCategories) {
      const items = grouped[cat];
      optionsHTML += `<optgroup label="${escapeHtml(cat)}">`;

      items.forEach((item) => {
        const id = item.id;
        const name = item.name || "Unknown";
        const unit = item.unit || "pcs";
        const price =
          parseFloat(item.selling_price) || parseFloat(item.price) || 0;
        const costPrice = parseFloat(item.cost_price) || 0;
        const stock = parseFloat(item.current_stock) || 0;
        const displayPrice = price > 0 ? price : costPrice;
        const isOutOfStock = stock <= 0;
        const subCategory = item.sub_category || "";

        optionsHTML += `
          <option 
            value="${id}" 
            data-unit="${unit}" 
            data-price="${displayPrice}"
            data-stock="${stock}"
            data-category="${escapeHtml(cat)}"
            data-sub-category="${escapeHtml(subCategory)}"
            ${isOutOfStock ? 'disabled style="opacity:0.5;"' : ""}
          >
            ${escapeHtml(name)} 
            (${unit}) 
            ${displayPrice > 0 ? `- ${Formatter.currency(displayPrice)}` : ""} 
            ${isOutOfStock ? "⚠️ OUT OF STOCK" : `| Stock: ${stock}`}
            ${subCategory ? `| ${escapeHtml(subCategory)}` : ""}
          </option>
        `;
      });

      optionsHTML += `</optgroup>`;
    }

    select.innerHTML = optionsHTML;

    // ✅ Event listener
    select.removeEventListener("change", updateMaterialHint);
    select.addEventListener("change", updateMaterialHint);

    // ✅ Trigger hint jika ada value
    if (select.value) updateMaterialHint();
  } catch (error) {
    console.error("Failed to load materials:", error);
    select.innerHTML = `
      <option value="">Error loading materials</option>
    `;
  }
}

// ============================================================
// UPDATE MATERIAL HINT
// ============================================================

export function updateMaterialHint() {
  const select = DOM.materialSelect();
  if (!select) return;

  const selectedOption = select.options[select.selectedIndex];
  const hintEl = DOM.materialHint();
  const unitEl = DOM.materialUnit();

  if (!hintEl) return;

  if (!selectedOption || !selectedOption.value) {
    hintEl.textContent = "💡 Select a material first";
    if (unitEl) unitEl.value = "pcs";
    return;
  }

  const name = selectedOption.text?.split("(")[0]?.trim() || "Material";
  const unit = selectedOption.dataset?.unit || "pcs";
  const price = parseFloat(selectedOption.dataset?.price) || 0;
  const stock = parseFloat(selectedOption.dataset?.stock) || 0;
  const category = selectedOption.dataset?.category || "";
  const subCategory = selectedOption.dataset?.subCategory || "";

  // ✅ Update unit
  if (unitEl) unitEl.value = unit;

  // ✅ Build hint dengan informasi lengkap
  let hint = `📦 ${name}`;
  if (category) hint += ` (${category})`;
  if (subCategory) hint += ` - ${subCategory}`;
  if (price > 0) hint += ` | Price: ${Formatter.currency(price)}`;
  if (stock > 0) {
    hint += ` | Stock: ${stock} ${unit}`;
  } else {
    hint += ` | ⚠️ OUT OF STOCK`;
  }

  hintEl.textContent = hint;

  // ✅ Color hint based on stock
  if (stock <= 0) {
    hintEl.style.color = "var(--danger, #ef4444)";
  } else if (stock < 10) {
    hintEl.style.color = "var(--warning, #f59e0b)";
  } else {
    hintEl.style.color = "";
  }
}

// ============================================================
// LABOR DROPDOWN
// ============================================================

export async function loadLaborTypes(category = "labor") {
  const select = DOM.laborTypeSelect();
  if (!select) return;

  try {
    const items = await ProjectAPI.fetchPriceListItems(1, 100, category);

    console.log(`👷 Loaded ${items.length} labor items`);

    if (!items || items.length === 0) {
      select.innerHTML = getDefaultLaborOptions();
      select.removeEventListener("change", autoFillLaborRate);
      select.addEventListener("change", autoFillLaborRate);
      if (select.value) autoFillLaborRate();
      return;
    }

    // Filter labor items
    const laborItems = items.filter(
      (item) =>
        item.category?.toLowerCase() === "labor" ||
        item.category?.toLowerCase() === "service" ||
        item.sub_category?.toLowerCase() === "labor" ||
        item.is_active !== false,
    );

    if (laborItems.length === 0) {
      select.innerHTML = getDefaultLaborOptions();
      select.removeEventListener("change", autoFillLaborRate);
      select.addEventListener("change", autoFillLaborRate);
      if (select.value) autoFillLaborRate();
      return;
    }

    const sortedItems = [...laborItems].sort((a, b) =>
      (a.name || "").localeCompare(b.name || ""),
    );

    select.innerHTML = `
      <option value="">Select Labor Type</option>
      ${sortedItems
        .map((item) => {
          const name = item.name || "Unknown";
          const price =
            parseFloat(item.price) || parseFloat(item.cost_price) || 0;
          const unit = item.unit || "hour";
          const id = item.id;
          const subCategory = item.sub_category || "";
          const description = item.description || "";

          return `
            <option 
              value="${escapeHtml(name)}" 
              data-rate="${price}" 
              data-id="${id}"
              data-unit="${unit}"
              data-sub-category="${escapeHtml(subCategory)}"
              data-description="${escapeHtml(description)}"
            >
              ${escapeHtml(name)} 
              ${price > 0 ? `(${Formatter.currency(price)}/${unit})` : ""}
              ${subCategory ? `- ${escapeHtml(subCategory)}` : ""}
            </option>
          `;
        })
        .join("")}
    `;

    select.removeEventListener("change", autoFillLaborRate);
    select.addEventListener("change", autoFillLaborRate);
    if (select.value) autoFillLaborRate();
  } catch (error) {
    console.error("Failed to load labor types:", error);
    select.innerHTML = getDefaultLaborOptions();
    select.removeEventListener("change", autoFillLaborRate);
    select.addEventListener("change", autoFillLaborRate);
    if (select.value) autoFillLaborRate();
  }
}

// ============================================================
// AUTO-FILL LABOR RATE
// ============================================================

export function autoFillLaborRate() {
  const select = DOM.laborTypeSelect();
  if (!select) return;

  const selectedOption = select.options[select.selectedIndex];
  const rateEl = DOM.laborRate();
  const hint = document.getElementById("laborRateHint");

  if (!selectedOption || !selectedOption.value) {
    if (rateEl) {
      rateEl.value = "";
      rateEl.placeholder = "Auto-filled";
      rateEl.readOnly = false;
      rateEl.style.borderColor = "";
      rateEl.style.backgroundColor = "";
    }
    if (hint) {
      hint.className = "";
      hint.innerHTML = `<span class="hint-icon">💡</span> Rate will be auto-filled from selected labor type`;
    }
    return;
  }

  const rate = selectedOption.dataset?.rate;

  if (rateEl) {
    if (rate && parseFloat(rate) > 0) {
      const rateValue = parseFloat(rate);
      rateEl.value = rateValue;
      rateEl.placeholder = `${Formatter.currency(rateValue)}/hour`;
      rateEl.readOnly = true;
      rateEl.style.borderColor = "var(--success, #10b981)";
      rateEl.style.backgroundColor = "rgba(16, 185, 129, 0.06)";

      if (hint) {
        hint.className = "success";
        hint.innerHTML = `
          <span class="hint-icon">✅</span> 
          Rate auto-filled: <strong>${Formatter.currency(rateValue)}</strong>/hour
        `;
      }
    } else {
      rateEl.value = "";
      rateEl.placeholder = "Enter rate manually";
      rateEl.readOnly = false;
      rateEl.style.borderColor = "";
      rateEl.style.backgroundColor = "";

      if (hint) {
        hint.className = "";
        hint.innerHTML = `<span class="hint-icon">⚠️</span> No rate found for this labor type. Please enter manually.`;
      }
    }
  }
}
