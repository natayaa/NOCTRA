document.addEventListener("DOMContentLoaded", () => {
  initializeModal();
  initializeDrawer();
  initializeKanban();
  initializeSearch();
  initializeProgressSlider();
  initializeProjectForm();
});

/* =========================================================
   MODAL
========================================================= */

function initializeModal() {
  const modal = document.getElementById("projectModal");
  const openBtn = document.getElementById("newProjectBtn");
  const closeBtn = document.getElementById("closeModal");

  if (!modal || !openBtn || !closeBtn) return;

  openBtn.addEventListener("click", () => {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  });

  closeBtn.addEventListener("click", closeModal);

  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      closeModal();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeModal();
    }
  });

  function closeModal() {
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

/* =========================================================
   DRAWER
========================================================= */

function initializeDrawer() {
  const drawer = document.getElementById("projectDrawer");
  const closeBtn = document.getElementById("closeDrawer");

  if (!drawer) return;

  document.addEventListener("click", (e) => {
    const card = e.target.closest(".project-card");

    if (!card) return;

    openDrawer(card);
  });

  closeBtn?.addEventListener("click", () => {
    drawer.classList.remove("active");
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      drawer.classList.remove("active");
    }
  });

  function openDrawer(card) {
    const title =
      card.querySelector("h4")?.textContent || "Project Details";

    const customer =
      card.querySelector(".project-top small")?.textContent || "-";

    const vehicle =
      card.querySelector(".project-meta p")?.textContent || "-";

    document.getElementById("drawerTitle").textContent = title;
    document.getElementById("drawerCustomer").textContent = customer;
    document.getElementById("drawerMotorbike").textContent = vehicle;

    drawer.classList.add("active");
  }
}

/* =========================================================
   DRAG & DROP KANBAN
========================================================= */

function initializeKanban() {
  const cards = document.querySelectorAll(".project-card");
  const columns = document.querySelectorAll(".column-body");

  let draggedCard = null;

  cards.forEach((card) => {
    card.addEventListener("dragstart", () => {
      draggedCard = card;

      card.classList.add("dragging");

      setTimeout(() => {
        card.style.opacity = "0.4";
      }, 0);
    });

    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");

      card.style.opacity = "1";

      draggedCard = null;

      updateColumnCounts();
    });
  });

  columns.forEach((column) => {
    column.addEventListener("dragover", (e) => {
      e.preventDefault();

      column.classList.add("drag-over");
    });

    column.addEventListener("dragleave", () => {
      column.classList.remove("drag-over");
    });

    column.addEventListener("drop", (e) => {
      e.preventDefault();

      column.classList.remove("drag-over");

      if (!draggedCard) return;

      column.appendChild(draggedCard);

      updateColumnCounts();
    });
  });

  updateColumnCounts();
}

/* =========================================================
   SEARCH
========================================================= */

function initializeSearch() {
  const searchInput = document.getElementById("projectSearch");

  if (!searchInput) return;

  searchInput.addEventListener("input", () => {
    const keyword = searchInput.value.trim().toLowerCase();

    document.querySelectorAll(".project-card").forEach((card) => {
      const text = card.textContent.toLowerCase();

      card.style.display = text.includes(keyword) ? "" : "none";
    });

    updateColumnCounts();
  });
}

/* =========================================================
   PROGRESS SLIDER
========================================================= */

function initializeProgressSlider() {
  const slider = document.getElementById("progressSlider");

  if (!slider) return;

  slider.addEventListener("input", () => {
    const value = slider.value;

    slider.style.background = `linear-gradient(
      90deg,
      var(--accent) ${value}%,
      rgba(255,255,255,0.08) ${value}%
    )`;
  });

  slider.dispatchEvent(new Event("input"));
}

/* =========================================================
   PROJECT FORM
========================================================= */

function initializeProjectForm() {
  const form = document.getElementById("projectForm");
  const modal = document.getElementById("projectModal");

  if (!form) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();

    const customer =
      document.getElementById("customerName")?.value.trim();

    const vehicle =
      document.getElementById("motorbike")?.value.trim();

    const price =
      document.getElementById("price")?.value.trim();

    if (!customer || !vehicle) {
      showToast("Please complete required fields");
      return;
    }

    createProjectCard({
      customer,
      vehicle,
      price,
    });

    form.reset();

    modal?.classList.remove("active");

    document.body.style.overflow = "";

    showToast("Project created successfully");
  });
}

/* =========================================================
   CREATE CARD
========================================================= */

function createProjectCard(data) {
  const targetColumn = document.querySelector(
    '[data-column="new"]'
  );

  if (!targetColumn) return;

  const card = document.createElement("article");

  card.className = "project-card priority-medium";
  card.draggable = true;

  card.innerHTML = `
    <div class="card-priority">
      <span>New Project</span>
    </div>

    <div class="project-top">
      <div>
        <h4>${escapeHtml(data.vehicle)}</h4>
        <small>${escapeHtml(data.customer)}</small>
      </div>

      <span class="status-badge active">
        Active
      </span>
    </div>

    <div class="project-tags">
      <span>Workshop</span>
    </div>

    <div class="project-meta">
      <div>
        <label>Vehicle</label>
        <p>${escapeHtml(data.vehicle)}</p>
      </div>

      <div>
        <label>Value</label>
        <p>Rp ${Number(data.price || 0).toLocaleString("id-ID")}</p>
      </div>
    </div>

    <div class="progress-section">
      <div class="progress-header">
        <span>Progress</span>
        <span>0%</span>
      </div>

      <div class="progress-bar">
        <div class="progress-fill" style="width:0%;"></div>
      </div>
    </div>

    <div class="project-footer">
      <div class="footer-users">
        <div class="avatar">
          ${data.customer.charAt(0).toUpperCase()}
        </div>
      </div>

      <span>New</span>
    </div>
  `;

  attachDragEvents(card);

  targetColumn.prepend(card);

  updateColumnCounts();
}

/* =========================================================
   ATTACH DRAG EVENTS
========================================================= */

function attachDragEvents(card) {
  card.addEventListener("dragstart", () => {
    card.classList.add("dragging");

    setTimeout(() => {
      card.style.opacity = "0.4";
    }, 0);

    window.__draggedCard = card;
  });

  card.addEventListener("dragend", () => {
    card.classList.remove("dragging");

    card.style.opacity = "1";

    updateColumnCounts();
  });

  document.querySelectorAll(".column-body").forEach((column) => {
    if (column.dataset.dragInitialized) return;

    column.dataset.dragInitialized = "true";

    column.addEventListener("dragover", (e) => {
      e.preventDefault();
    });

    column.addEventListener("drop", (e) => {
      e.preventDefault();

      if (window.__draggedCard) {
        column.appendChild(window.__draggedCard);

        updateColumnCounts();
      }
    });
  });
}

/* =========================================================
   COLUMN COUNTER
========================================================= */

function updateColumnCounts() {
  document.querySelectorAll(".kanban-column").forEach((column) => {
    const countElement = column.querySelector(
      ".column-header strong"
    );

    const count = column.querySelectorAll(
      '.project-card:not([style*="display: none"])'
    ).length;

    if (countElement) {
      countElement.textContent = count;
    }
  });
}

/* =========================================================
   TOAST
========================================================= */

function showToast(message) {
  let toast = document.querySelector(".app-toast");

  if (!toast) {
    toast = document.createElement("div");

    toast.className = "app-toast";

    document.body.appendChild(toast);

    Object.assign(toast.style, {
      position: "fixed",
      right: "24px",
      bottom: "24px",
      zIndex: "99999",
      padding: "14px 18px",
      borderRadius: "14px",
      background: "#111827",
      color: "#fff",
      border: "1px solid rgba(255,255,255,.08)",
      boxShadow: "0 15px 40px rgba(0,0,0,.3)",
      transform: "translateY(20px)",
      opacity: "0",
      transition: ".25s ease",
    });
  }

  toast.textContent = message;

  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
  });

  clearTimeout(toast._timeout);

  toast._timeout = setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(20px)";
  }, 3000);
}

/* =========================================================
   HELPERS
========================================================= */

function escapeHtml(str = "") {
  return str
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}