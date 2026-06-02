const calendarModal = document.getElementById("calendarModal");

document.getElementById("addEventBtn").addEventListener("click", () => {
  calendarModal.classList.add("active");
});

document.getElementById("closeCalendarModal").addEventListener("click", () => {
  calendarModal.classList.remove("active");
});

document.getElementById("calendarForm").addEventListener("submit", (e) => {
  e.preventDefault();

  const title = document.getElementById("eventTitle").value;

  const date = document.getElementById("eventDate").value;

  const item = document.createElement("div");

  item.className = "schedule-item";

  item.innerHTML = `
            <strong>${title}</strong>
            <span>${date}</span>
        `;

  document.getElementById("scheduleList").prepend(item);

  calendarModal.classList.remove("active");

  e.target.reset();
});
