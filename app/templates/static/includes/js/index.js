AOS.init({
    duration: 1000,
    once: true
});

/* ======================
   NAVBAR SCROLL EFFECT
====================== */
const navbar = document.querySelector("nav");

window.addEventListener("scroll", () => {
    if (!navbar) return;

    navbar.style.background =
        window.scrollY > 30
            ? "rgba(4,8,22,.92)"
            : "rgba(4,8,22,.6)";
});

/* ======================
   MODAL
====================== */
const modal = document.getElementById("inquiryModal");
const openBtn = document.getElementById("openInquiry");
const closeBtn = document.getElementById("closeInquiry");

/* ======================
   SCROLL LOCK SYSTEM (SINGLE SOURCE OF TRUTH)
====================== */
function lockScroll() {
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
}

function unlockScroll() {
    document.body.style.overflow = "";
    document.documentElement.style.overflow = "";
}

/* ======================
   MODAL CONTROL
====================== */
function openModal() {
    if (!modal) return;

    modal.classList.add("active");
    lockScroll();
}

function closeModal() {
    if (!modal) return;

    modal.classList.remove("active");
    unlockScroll();
}

/* ======================
   EVENTS
====================== */
openBtn?.addEventListener("click", openModal);

closeBtn?.addEventListener("click", closeModal);

modal?.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal-backdrop")) {
        closeModal();
    }
});