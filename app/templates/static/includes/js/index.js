const modal = document.getElementById("inquiryModal");
const openBtn = document.getElementById("openInquiry");
const closeBtn = document.getElementById("closeInquiry");

function lockScroll() {
  document.body.style.overflow = "hidden";
  document.documentElement.style.overflow = "hidden";
  document.body.classList.add("modal-open");
}

function unlockScroll() {
  document.body.style.overflow = "";
  document.documentElement.style.overflow = "";
  document.body.classList.remove("modal-open");
}

function isOpen() {
  return modal?.classList.contains("active");
}

function openModal() {
  if (!modal || isOpen()) return;

  modal.classList.add("active");
  lockScroll();
}

function closeModal() {
  if (!modal || !isOpen()) return;

  modal.classList.remove("active");
  unlockScroll();
}

/* OPEN / CLOSE */
openBtn?.addEventListener("click", openModal);
closeBtn?.addEventListener("click", closeModal);

/* BACKDROP CLOSE */
modal?.addEventListener("click", (e) => {
  const isBackdrop =
    e.target === modal ||
    e.target.classList.contains("modal-backdrop");

  if (isBackdrop) closeModal();
});

/* ESC CLOSE (only when active) */
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (!isOpen()) return;

  closeModal();
});

/* SAFETY: restore scroll if DOM state mismatch */
window.addEventListener("load", () => {
  if (!isOpen()) unlockScroll();
});