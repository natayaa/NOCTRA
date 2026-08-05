// ============================================================
// restored-bikes/handlers/documents.js - Gallery & Documents
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { RestoredBikeAPI } from "../api.js";
import { showToast } from "../../shared/toast.js";
import { renderGallery } from "../renderers/gallery.js";
import { renderDocuments } from "../renderers/documents.js";
import { refreshDrawer } from "./restorations.js";

// ============================================================
// GALLERY
// ============================================================

export async function handleGalleryUpload(event) {
  const input = event.target;
  const files = input.files;
  if (!files || files.length === 0) return;

  const bikeId = state.currentBikeId;
  if (!bikeId) {
    showToast("No bike selected", "error");
    return;
  }

  if (files.length > CONFIG.MAX_PHOTOS) {
    showToast(`Max ${CONFIG.MAX_PHOTOS} photos allowed`, "warning");
    input.value = "";
    return;
  }

  // Validate file size (max 5MB each)
  for (const file of files) {
    if (file.size > 5 * 1024 * 1024) {
      showToast(`File "${file.name}" exceeds 5MB`, "warning");
      input.value = "";
      return;
    }
  }

  state.gallery.uploading = true;

  try {
    const result = await RestoredBikeAPI.uploadPhotos(bikeId, files);
    if (result) {
      showToast(
        `✅ ${files.length} photo${files.length > 1 ? "s" : ""} uploaded!`,
        "success",
      );
      const photos = await RestoredBikeAPI.getPhotos(bikeId);
      renderGallery(photos);
      await refreshDrawer();
    }
  } catch (error) {
    showToast("❌ Failed to upload photos: " + error.message, "error");
  } finally {
    state.gallery.uploading = false;
    input.value = "";
  }
}

export async function handleDeletePhoto(photoId) {
  if (!photoId) return;
  if (!confirm("Delete this photo?")) return;

  try {
    const result = await RestoredBikeAPI.deletePhoto(photoId);
    if (result) {
      showToast("🗑️ Photo deleted", "success");
      const bikeId = state.currentBikeId;
      if (bikeId) {
        const photos = await RestoredBikeAPI.getPhotos(bikeId);
        renderGallery(photos);
        await refreshDrawer();
      }
    }
  } catch (error) {
    showToast("❌ Failed to delete photo: " + error.message, "error");
  }
}

// ============================================================
// DOCUMENTS
// ============================================================

export async function handleDocumentUpload(event) {
  const input = event.target;
  const files = input.files;
  if (!files || files.length === 0) return;

  const bikeId = state.currentBikeId;
  if (!bikeId) {
    showToast("No bike selected", "error");
    return;
  }

  if (files.length > CONFIG.MAX_DOCUMENTS) {
    showToast(`Max ${CONFIG.MAX_DOCUMENTS} documents allowed`, "warning");
    input.value = "";
    return;
  }

  // Validate file size (max 10MB each)
  for (const file of files) {
    if (file.size > 10 * 1024 * 1024) {
      showToast(`File "${file.name}" exceeds 10MB`, "warning");
      input.value = "";
      return;
    }
  }

  try {
    let successCount = 0;
    for (const file of files) {
      const result = await RestoredBikeAPI.uploadDocument(bikeId, file);
      if (result) successCount++;
    }

    if (successCount > 0) {
      showToast(
        `✅ ${successCount} document${successCount > 1 ? "s" : ""} uploaded!`,
        "success",
      );
      const docs = await RestoredBikeAPI.getDocuments(bikeId);
      renderDocuments(docs);
      await refreshDrawer();
    }
  } catch (error) {
    showToast("❌ Failed to upload documents: " + error.message, "error");
  } finally {
    input.value = "";
  }
}

export async function handleDeleteDocument(docId) {
  if (!docId) return;
  if (!confirm("Delete this document?")) return;

  try {
    const result = await RestoredBikeAPI.deleteDocument(docId);
    if (result) {
      showToast("🗑️ Document deleted", "success");
      const bikeId = state.currentBikeId;
      if (bikeId) {
        const docs = await RestoredBikeAPI.getDocuments(bikeId);
        renderDocuments(docs);
        await refreshDrawer();
      }
    }
  } catch (error) {
    showToast("❌ Failed to delete document: " + error.message, "error");
  }
}

export async function handleDownloadDocument(docId) {
  if (!docId) return;
  try {
    await RestoredBikeAPI.downloadDocument(docId);
  } catch (error) {
    showToast("❌ Failed to download document: " + error.message, "error");
  }
}
