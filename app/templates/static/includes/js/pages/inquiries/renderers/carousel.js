// inquiries/renderers/carousel.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { state } from "../config.js";

const DEFAULT_IMAGE = "/static/images/placeholder.jpg";

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
    track.innerHTML = `
      <div class="carousel-empty" style="display:flex;align-items:center;justify-content:center;height:150px;color:var(--text-muted);font-size:0.85rem;">
        <i class="ph ph-image" style="font-size:2rem;display:block;margin-right:0.5rem;"></i>
        No ${type} photos
      </div>
    `;
    state.carousels[type].images = [];
    state.carousels[type].index = 0;
    updateCarouselButtons(type, container);
    return;
  }

  track.innerHTML = photos
    .map((photo, index) => {
      const src =
        photo.file_path || photo.url || photo.thumbnail_url || DEFAULT_IMAGE;
      const alt = `${type} photo ${index + 1}`;
      return `
      <div class="carousel-slide" style="flex:0 0 100%;min-width:100%;">
        <img src="${src}" 
             alt="${alt}" 
             loading="lazy"
             style="width:100%;height:150px;object-fit:cover;border-radius:var(--radius-sm);cursor:pointer;"
             onclick="window.openLightbox('${type}', ${index})" />
      </div>
    `;
    })
    .join("");

  state.carousels[type].images = photos;
  state.carousels[type].index = 0;

  if (container) {
    const prevBtn = container.querySelector(".carousel-btn.prev");
    const nextBtn = container.querySelector(".carousel-btn.next");
    if (prevBtn) {
      prevBtn.onclick = (e) => {
        e.stopPropagation();
        navigateCarousel(type, -1);
      };
    }
    if (nextBtn) {
      nextBtn.onclick = (e) => {
        e.stopPropagation();
        navigateCarousel(type, 1);
      };
    }
    updateCarouselButtons(type, container);
    updateCarouselPosition(type);
  }
}

function navigateCarousel(type, direction) {
  const carousel = state.carousels[type];
  if (!carousel.images || carousel.images.length === 0) return;

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
  track.style.transform = `translateX(-${carousel.index * 100}%)`;
  track.style.transition = "transform 0.3s ease";
}

function updateCarouselButtons(type, container) {
  if (!container) {
    const track = type === "before" ? DOM.beforeTrack() : DOM.afterTrack();
    if (!track) return;
    container = track.closest(".carousel-container");
  }
  if (!container) return;

  const prevBtn = container.querySelector(".carousel-btn.prev");
  const nextBtn = container.querySelector(".carousel-btn.next");
  const carousel = state.carousels[type];
  const total = carousel.images?.length || 0;

  if (prevBtn) {
    prevBtn.disabled = carousel.index === 0 || total === 0;
    prevBtn.style.opacity = prevBtn.disabled ? "0.3" : "1";
    prevBtn.style.cursor = prevBtn.disabled ? "not-allowed" : "pointer";
  }
  if (nextBtn) {
    nextBtn.disabled = carousel.index >= total - 1 || total === 0;
    nextBtn.style.opacity = nextBtn.disabled ? "0.3" : "1";
    nextBtn.style.cursor = nextBtn.disabled ? "not-allowed" : "pointer";
  }

  // ✅ Update indicator dots
  const dotsContainer = container.querySelector(".carousel-dots");
  if (dotsContainer && total > 0) {
    dotsContainer.innerHTML = Array.from(
      { length: total },
      (_, i) => `
      <span class="carousel-dot ${i === carousel.index ? "active" : ""}" 
            style="display:inline-block;width:8px;height:8px;border-radius:50%;
                   background:${i === carousel.index ? "var(--primary)" : "var(--border)"};
                   margin:0 4px;cursor:pointer;transition:all 0.2s ease;"
            onclick="window.goToCarouselSlide('${type}', ${i})"></span>
    `,
    ).join("");
  }
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
  state.lightbox.currentType = type;

  updateLightboxImage();

  const overlay = DOM.lightboxOverlay();
  if (overlay) {
    overlay.style.display = "flex";
    overlay.style.animation = "fadeIn 0.3s ease";
  }
  document.body.style.overflow = "hidden";

  // ✅ Keyboard navigation
  document.addEventListener("keydown", lightboxKeyHandler);
}

export function closeLightbox() {
  state.lightbox.isOpen = false;
  const overlay = DOM.lightboxOverlay();
  if (overlay) overlay.style.display = "none";
  document.body.style.overflow = "";
  document.removeEventListener("keydown", lightboxKeyHandler);
}

function lightboxKeyHandler(e) {
  if (!state.lightbox.isOpen) return;
  if (e.key === "Escape") {
    closeLightbox();
  } else if (e.key === "ArrowLeft") {
    navigateLightbox(-1);
  } else if (e.key === "ArrowRight") {
    navigateLightbox(1);
  }
}

function updateLightboxImage() {
  const image = state.lightbox.images[state.lightbox.currentIndex];
  const imgEl = DOM.lightboxImage();
  if (imgEl) {
    imgEl.src =
      image?.file_path || image?.url || image?.thumbnail_url || DEFAULT_IMAGE;
    imgEl.alt = `Photo ${state.lightbox.currentIndex + 1} of ${state.lightbox.images.length}`;
    imgEl.style.maxWidth = "90vw";
    imgEl.style.maxHeight = "85vh";
    imgEl.style.objectFit = "contain";
    imgEl.style.borderRadius = "var(--radius-md)";
  }

  // ✅ Update counter
  const counterEl = document.getElementById("lightboxCounter");
  if (counterEl) {
    counterEl.textContent = `${state.lightbox.currentIndex + 1} / ${state.lightbox.images.length}`;
  }
}

export function navigateLightbox(direction) {
  const newIndex = state.lightbox.currentIndex + direction;
  if (newIndex < 0 || newIndex >= state.lightbox.images.length) return;
  state.lightbox.currentIndex = newIndex;
  updateLightboxImage();
}

// ✅ Go to specific slide
export function goToCarouselSlide(type, index) {
  const carousel = state.carousels[type];
  if (!carousel.images || index < 0 || index >= carousel.images.length) return;
  carousel.index = index;
  updateCarouselPosition(type);
  updateCarouselButtons(type);
}

// ✅ Add to window for inline onclick
window.goToCarouselSlide = goToCarouselSlide;
