// ============================================================
// restored-bikes/handlers/events.js - Event Binding
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { loadRestoredBikes } from "../index.js";
import {
  openAddModal,
  openEditModal,
  closeModal,
  handleFormSubmit,
} from "./modals.js";
import {
  openDrawer,
  closeDrawer,
  deleteRestoredBike,
  switchTab,
} from "./restorations.js";
import { handleGalleryUpload, handleDocumentUpload } from "./documents.js";

export function bindEvents() {
  // ---- Search & Filters ----
  let searchTimeout;
  DOM.searchRestored()?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.currentPage = 1;
      loadRestoredBikes();
    }, 300);
  });

  DOM.statusFilter()?.addEventListener("change", (e) => {
    state.filters.status = e.target.value;
    state.currentPage = 1;
    loadRestoredBikes();
  });

  DOM.brandFilter()?.addEventListener("change", (e) => {
    state.filters.brand = e.target.value;
    state.currentPage = 1;
    loadRestoredBikes();
  });

  // ---- Add Button ----
  DOM.addRestoredBtn()?.addEventListener("click", openAddModal);

  // ---- Modal ----
  DOM.closeModal()?.addEventListener("click", closeModal);
  DOM.cancelModalBtn()?.addEventListener("click", closeModal);
  DOM.restoredModal()?.addEventListener("click", (e) => {
    if (e.target === DOM.restoredModal()) closeModal();
  });
  DOM.restoredForm()?.addEventListener("submit", handleFormSubmit);

  // ---- Drawer ----
  DOM.closeDrawer()?.addEventListener("click", closeDrawer);
  DOM.drawerBackdrop()?.addEventListener("click", closeDrawer);

  // ---- Drawer Tabs ----
  const tabs = DOM.tabBtns();
  if (tabs) {
    tabs.forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });
  }

  // ---- Drawer Actions ----
  DOM.editRestoredBtn()?.addEventListener("click", () => {
    if (state.currentBikeId) {
      openEditModal(state.currentBikeId);
    }
  });
  DOM.deleteRestoredBtn()?.addEventListener("click", () => {
    if (state.currentBikeId) {
      deleteRestoredBike(state.currentBikeId);
    }
  });

  // ---- Gallery Upload ----
  DOM.galleryPhotos()?.addEventListener("change", handleGalleryUpload);
  const uploadZone = DOM.galleryUploadZone();
  if (uploadZone) {
    uploadZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      uploadZone.classList.add("dragover");
    });
    uploadZone.addEventListener("dragleave", () => {
      uploadZone.classList.remove("dragover");
    });
    uploadZone.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadZone.classList.remove("dragover");
      if (e.dataTransfer.files.length > 0) {
        const input = DOM.galleryPhotos();
        if (input) {
          input.files = e.dataTransfer.files;
          handleGalleryUpload({ target: input });
        }
      }
    });
  }

  // ---- Document Upload ----
  DOM.documentFiles()?.addEventListener("change", handleDocumentUpload);
  const docZone = DOM.documentUploadZone();
  if (docZone) {
    docZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      docZone.classList.add("dragover");
    });
    docZone.addEventListener("dragleave", () => {
      docZone.classList.remove("dragover");
    });
    docZone.addEventListener("drop", (e) => {
      e.preventDefault();
      docZone.classList.remove("dragover");
      if (e.dataTransfer.files.length > 0) {
        const input = DOM.documentFiles();
        if (input) {
          input.files = e.dataTransfer.files;
          handleDocumentUpload({ target: input });
        }
      }
    });
  }

  // ---- Pagination ----
  DOM.prevPageBtn()?.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage--;
      loadRestoredBikes();
    }
  });
  DOM.nextPageBtn()?.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      state.currentPage++;
      loadRestoredBikes();
    }
  });

  // ---- Keyboard ----
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (DOM.restoredModal()?.classList.contains("active")) closeModal();
      if (DOM.drawer()?.classList.contains("active")) closeDrawer();
    }
    if (e.ctrlKey && e.key === "n") {
      e.preventDefault();
      openAddModal();
    }
    if (e.ctrlKey && e.key === "f") {
      e.preventDefault();
      DOM.searchRestored()?.focus();
    }
  });

  // ---- Expose globals ----
  exposeGlobals();

  console.log("✅ Restored Bikes events bound");
}

function exposeGlobals() {
  window.openRestoredDrawer = openDrawer;
  window.openAddRestoredModal = openAddModal;
  window.deleteRestoredBike = deleteRestoredBike;
  window.deleteGalleryPhoto = async (photoId) => {
    const { handleDeletePhoto } = await import("./documents.js");
    handleDeletePhoto(photoId);
  };
  window.deleteDocument = async (docId) => {
    const { handleDeleteDocument } = await import("./documents.js");
    handleDeleteDocument(docId);
  };
  window.downloadDocument = async (docId) => {
    const { handleDownloadDocument } = await import("./documents.js");
    handleDownloadDocument(docId);
  };
}
