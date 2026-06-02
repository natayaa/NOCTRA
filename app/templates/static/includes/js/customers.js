// CUSTOMER SELECT

document.querySelectorAll(".customer-card").forEach((card) => {
  card.addEventListener("click", () => {
    document.querySelectorAll(".customer-card").forEach((c) => {
      c.classList.remove("active");
    });

    card.classList.add("active");

    document.getElementById("customerName").textContent = card.dataset.customer;
  });
});

// TABS

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => {
      t.classList.remove("active");
    });

    document.querySelectorAll(".tab-content").forEach((content) => {
      content.classList.remove("active");
    });

    tab.classList.add("active");

    document.getElementById(tab.dataset.tab).classList.add("active");
  });
});

// SEARCH

document.getElementById("customerSearch").addEventListener("keyup", (e) => {
  const keyword = e.target.value.toLowerCase();

  document.querySelectorAll(".customer-card").forEach((card) => {
    card.style.display = card.innerText.toLowerCase().includes(keyword)
      ? ""
      : "none";
  });
});
