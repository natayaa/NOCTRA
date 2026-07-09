// ============================================================
// inquiries/renderers/carousel.js - Carousel & Lightbox
// ============================================================

import { DOM } from "../dom.js";
import { state } from "../config.js";

export function renderDrawerBeforeAfter(photos) {
  const beforePhotos =
    photos?.filter((p) => p.stage === "before" || p.stage === "initial") || [];
  const afterPhotos =
    photos?.filter((p) => p.stage === "after" || p.stage === "final") || [];
  renderCarousel("before", beforePhotos);
  renderCarousel("after", afterPhotos);
}

function renderCarousel(type, photos) {
  const track = type === "before" ? DOM.beforeTrack() : DOM.afterTrack();
  if (!track) return;
  const container = track.closest(".carousel-container");

  if (!photos || photos.length === 0) {
    track.innerHTML = `<div class="carousel-empty">No ${type} photos</div>`;
    return;
  }

  track.innerHTML = photos
    .map(
      (photo, index) => `
        <img src="${photo.file_path || photo.url || photo.thumbnail_url || "/static/images/placeholder.jpg"}" 
             alt="${type} photo" 
             onclick="window.openLightbox('${type}', ${index})" />
    `,
    )
    .join("");

  state.carousels[type].images = photos;
  state.carousels[type].index = 0;

  if (container) {
    const prevBtn = container.querySelector(".carousel-btn.prev");
    const nextBtn = container.querySelector(".carousel-btn.next");
    if (prevBtn) prevBtn.onclick = () => navigateCarousel(type, -1);
    if (nextBtn) nextBtn.onclick = () => navigateCarousel(type, 1);
    updateCarouselButtons(type);
  }
}

function navigateCarousel(type, direction) {
  const carousel = state.carousels[type];
  const newIndex = carousel.index + direction;
  if (newIndex < 0 || newIndex >= carousel.images.length) return;
  carousel.index = newIndex;
  updateCarouselPosition(type);
  updateCarouselButtons(type);
}

function updateCarouselPosition(type) {
  const track = type === "before" ? DOM.beforeTrack() : DOM.afterTrack();
  if (!track) return;
  const carousel = state.carousels[type];
  track.style.transform = `translateX(${-carousel.index * 100}%)`;
}

function updateCarouselButtons(type) {
  const track = type === "before" ? DOM.beforeTrack() : DOM.afterTrack();
  if (!track) return;
  const container = track.closest(".carousel-container");
  if (!container) return;
  const prevBtn = container.querySelector(".carousel-btn.prev");
  const nextBtn = container.querySelector(".carousel-btn.next");
  const carousel = state.carousels[type];
  if (prevBtn) prevBtn.disabled = carousel.index === 0;
  if (nextBtn) nextBtn.disabled = carousel.index >= carousel.images.length - 1;
}

// Lightbox
export function openLightbox(type, index) {
  const images =
    type === "before"
      ? state.carousels.before.images
      : state.carousels.after.images;
  if (!images || images.length === 0) return;
  state.lightbox.images = images;
  state.lightbox.currentIndex = index;
  state.lightbox.isOpen = true;
  updateLightboxImage();
  if (DOM.lightboxOverlay()) DOM.lightboxOverlay().style.display = "flex";
  document.body.style.overflow = "hidden";
}

export function closeLightbox() {
  state.lightbox.isOpen = false;
  if (DOM.lightboxOverlay()) DOM.lightboxOverlay().style.display = "none";
  document.body.style.overflow = "";
}

function updateLightboxImage() {
  const image = state.lightbox.images[state.lightbox.currentIndex];
  if (DOM.lightboxImage()) {
    DOM.lightboxImage().src =
      image.file_path ||
      image.url ||
      image.thumbnail_url ||
      "/static/images/placeholder.jpg";
    DOM.lightboxImage().alt = `Photo ${state.lightbox.currentIndex + 1} of ${state.lightbox.images.length}`;
  }
}

export function navigateLightbox(direction) {
  const newIndex = state.lightbox.currentIndex + direction;
  if (newIndex < 0 || newIndex >= state.lightbox.images.length) return;
  state.lightbox.currentIndex = newIndex;
  updateLightboxImage();
}
