const reportModal = document.getElementById("reportModal");

let selectedReport = "";

document.querySelectorAll("[data-report]").forEach((btn) => {
  btn.addEventListener("click", () => {
    selectedReport = btn.dataset.report;

    reportModal.classList.add("active");
  });
});

document.getElementById("closeReportModal").addEventListener("click", () => {
  reportModal.classList.remove("active");
});

document.getElementById("reportForm").addEventListener("submit", (e) => {
  e.preventDefault();

  const from = document.getElementById("fromDate").value;

  const to = document.getElementById("toDate").value;

  const filename = `${selectedReport}-${from}-${to}.pdf`;

  const row = document.createElement("tr");

  row.innerHTML = `
            <td>${filename}</td>
            <td>${selectedReport}</td>
            <td>${new Date().toLocaleDateString()}</td>
            <td>
                <button class="download-btn">
                    Download
                </button>
            </td>
        `;

  document.getElementById("reportTable").prepend(row);

  reportModal.classList.remove("active");

  e.target.reset();
});
