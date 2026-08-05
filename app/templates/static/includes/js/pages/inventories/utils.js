// ============================================================
// inventories/utils.js - Utility Functions
// ============================================================

import { state } from "./config.js";

export function getItemById(itemId) {
  return state.items.find((i) => i.id === itemId);
}

export function getItemName(itemId) {
  if (!itemId) return "Unknown";
  const item = getItemById(itemId);
  return item ? item.name : `Item ${itemId.substring(0, 8)}`;
}

export function getItemUnit(itemId) {
  if (!itemId) return "";
  const item = getItemById(itemId);
  return item ? item.unit || "" : "";
}

export function ensureArray(data) {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") {
    if (data.data && Array.isArray(data.data)) return data.data;
    if (data.items && Array.isArray(data.items)) return data.items;
    if (data.movements && Array.isArray(data.movements)) return data.movements;
    if (data.history && Array.isArray(data.history)) return data.history;
    return [data];
  }
  return [];
}
