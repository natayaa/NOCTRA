// ============================================================
// restored-bikes/renderers/gallery.js - Gallery Rendering
// ============================================================

import { DOM } from "../dom.js";

export function renderGallery(photos) {
  const grid = DOM.galleryGrid();
  if (!grid) return;

  if (!photos || photos.length === 0) {
    grid.innerHTML = `<div class="empty-state">No photos uploaded yet</div>`;
    return;
  }

  grid.innerHTML = photos
    .map((photo) => {
      const url = photo.url || photo.file_path || photo.thumbnail_url || "";
      return `
        <div class="gallery-item" data-id="${photo.id}">
          <img src="${url}" alt="Restoration photo" loading="lazy" />
          <button class="delete-photo" onclick="window.deleteGalleryPhoto('${photo.id}')" title="Delete photo">
            <i class="fas fa-times"></i>
          </button>
          ${photo.is_primary ? `<span style="position:absolute;bottom:4px;left:4px;font-size:0.5rem;background:rgba(255,107,0,0.8);color:#fff;padding:0.05rem 0.4rem;border-radius:var(--radius-full);">Primary</span>` : ""}
        </div>
      `;
    })
    .join("");
}
