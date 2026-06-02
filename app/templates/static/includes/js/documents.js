const documentModal = document.getElementById("documentModal");

document.getElementById("uploadDocumentBtn").addEventListener("click", () => {
  documentModal.classList.add("active");
});

document.getElementById("closeDocumentModal").addEventListener("click", () => {
  documentModal.classList.remove("active");
});

document.getElementById("documentForm").addEventListener("submit", (e) => {
  e.preventDefault();

  const name = document.getElementById("documentName").value;

  const type = document.getElementById("documentType").value;

  const customer = document.getElementById("customerName").value;

  const row = document.createElement("tr");

  row.innerHTML = `
            <td>${name}</td>
            <td>${type}</td>
            <td>${customer}</td>
            <td>${new Date().toLocaleDateString()}</td>
            <td>
                <button>View</button>
                <button>Download</button>
            </td>
        `;

  document.getElementById("documentTable").prepend(row);

  documentModal.classList.remove("active");

  e.target.reset();
});

document.getElementById("documentSearch").addEventListener("keyup", (e) => {
  const keyword = e.target.value.toLowerCase();

  document.querySelectorAll("#documentTable tr").forEach((row) => {
    row.style.display = row.innerText.toLowerCase().includes(keyword)
      ? ""
      : "none";
  });
});
