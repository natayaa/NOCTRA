// ============================================================
// restored-bikes/handlers/restorations.js - Main Operations
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { RestoredBikeAPI } from "../api.js";
import { showToast } from "../../shared/toast.js";
import { renderDetail, clearDetail } from "../renderers/detail.js";
import { renderGallery } from "../renderers/gallery.js";
import { renderDocuments } from "../renderers/documents.js";
import { loadRestoredBikes } from "../index.js";

let isLoading = false;

export async function openDrawer(bikeId) {
  if (isLoading) return;
  if (!bikeId) {
    showToast("No bike selected", "error");
    return;
  }

  // If same bike and drawer already open, skip
  if (
    state.currentBikeId === bikeId &&
    DOM.drawer()?.classList.contains("active")
  ) {
    return;
  }

  isLoading = true;
  state.currentBikeId = bikeId;

  const drawer = DOM.drawer();
  const backdrop = DOM.drawerBackdrop();
  if (drawer) drawer.classList.add("active");
  if (backdrop) backdrop.classList.add("active");
  document.body.style.overflow = "hidden";

  try {
    const bike = await RestoredBikeAPI.get(bikeId);
    if (!bike) {
      showToast("Failed to load bike details", "error");
      closeDrawer();
      return;
    }

    renderDetail(bike);

    // Load gallery
    const photos = await RestoredBikeAPI.getPhotos(bikeId);
    renderGallery(photos);

    // Load documents
    const docs = await RestoredBikeAPI.getDocuments(bikeId);
    renderDocuments(docs);

    // Set active tab
    switchTab("overview");
  } catch (error) {
    console.error("Failed to open drawer:", error);
    showToast("Failed to load bike details", "error");
    closeDrawer();
  } finally {
    isLoading = false;
  }
}

export function closeDrawer() {
  const drawer = DOM.drawer();
  const backdrop = DOM.drawerBackdrop();
  if (drawer) drawer.classList.remove("active");
  if (backdrop) backdrop.classList.remove("active");
  document.body.style.overflow = "";
  state.currentBikeId = null;
  clearDetail();
}

export function switchTab(tabName) {
  const btns = DOM.tabBtns();
  const panels = DOM.tabPanels();

  if (btns) {
    btns.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabName);
    });
  }
  if (panels) {
    panels.forEach((panel) => {
      panel.classList.toggle("active", panel.id === `tab-${tabName}`);
    });
  }
}

export async function refreshDrawer() {
  if (state.currentBikeId && DOM.drawer()?.classList.contains("active")) {
    await openDrawer(state.currentBikeId);
  }
}

export async function deleteRestoredBike(id) {
  if (!id) return;
  if (!confirm("Delete this restored bike? This action cannot be undone."))
    return;

  const result = await RestoredBikeAPI.delete(id);
  if (result) {
    showToast("🗑️ Bike deleted", "success");
    closeDrawer();
    await loadRestoredBikes();
  }
}
