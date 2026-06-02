document.querySelectorAll(".switch input").forEach((toggle) => {
  toggle.addEventListener("change", () => {
    console.log("Notification setting updated");
  });
});
