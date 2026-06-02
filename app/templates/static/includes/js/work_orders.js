const drawer = document.getElementById("woDrawer");

document.querySelectorAll(".wo-card").forEach((card) => {
  card.addEventListener("click", () => {
    drawer.classList.add("active");
  });
});

document.getElementById("closeDrawer").addEventListener("click", () => {
  drawer.classList.remove("active");
});
