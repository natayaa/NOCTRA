const modal = document.getElementById("projectModal");

document.getElementById("newProjectBtn").addEventListener("click", () => {
  modal.classList.add("active");
});

document.getElementById("closeModal").addEventListener("click", () => {
  modal.classList.remove("active");
});

document.getElementById("projectForm").addEventListener("submit", (e) => {
  e.preventDefault();

  const customer = document.getElementById("customerName").value;

  const motorbike = document.getElementById("motorbike").value;

  const price = document.getElementById("price").value;

  const card = document.createElement("div");

  card.classList.add("project-card");

  card.draggable = true;

  card.innerHTML = `
        <h4>${motorbike}</h4>
        <p>${customer}</p>
        <span class="price">
            Rp ${Number(price).toLocaleString("id-ID")}
        </span>
    `;

  document.querySelector('[data-column="new"]').appendChild(card);

  initializeDrag(card);

  modal.classList.remove("active");

  e.target.reset();
});

// DRAG & DROP

function initializeDrag(card) {
  card.addEventListener("dragstart", () => {
    card.classList.add("dragging");
  });

  card.addEventListener("dragend", () => {
    card.classList.remove("dragging");
  });
}

document.querySelectorAll(".column-body").forEach((column) => {
  column.addEventListener("dragover", (e) => {
    e.preventDefault();

    const draggable = document.querySelector(".dragging");

    if (draggable) {
      column.appendChild(draggable);
    }
  });
});

document.querySelectorAll(".project-card").forEach(initializeDrag);

const drawer = document.getElementById("projectDrawer");

const drawerTitle = document.getElementById("drawerTitle");

const drawerCustomer = document.getElementById("drawerCustomer");

const drawerMotorbike = document.getElementById("drawerMotorbike");

document.addEventListener("click", (e) => {
  const card = e.target.closest(".project-card");

  if (!card) {
    return;
  }

  drawer.classList.add("active");

  drawerTitle.textContent = card.querySelector("h4").textContent;

  drawerCustomer.textContent = card.querySelector("p").textContent;

  drawerMotorbike.textContent = card.querySelector("h4").textContent;
});

document.getElementById("closeDrawer").addEventListener("click", () => {
  drawer.classList.remove("active");
});
