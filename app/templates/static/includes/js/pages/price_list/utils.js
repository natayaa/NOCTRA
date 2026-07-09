// ============================================================
// price_list/utils.js - Utility Functions
// ============================================================

import { state } from "./config.js";

export function getAffectedItemsCount(category, vehicleBrand = null) {
  return state.items.filter(
    (item) =>
      item.category === category &&
      item.is_active !== false &&
      (!vehicleBrand || item.vehicle_brand === vehicleBrand),
  ).length;
}

export function getItemById(itemId) {
  return state.items.find((i) => i.id === itemId);
}
