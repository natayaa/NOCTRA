const inventoryModal = document.getElementById("inventoryModal");

document.getElementById("addItemBtn").addEventListener("click", () => {
  inventoryModal.classList.add("active");
});

document.getElementById("closeInventoryModal").addEventListener("click", () => {
  inventoryModal.classList.remove("active");
});

document.getElementById("inventoryForm").addEventListener("submit", (e) => {
  e.preventDefault();

  const item = document.getElementById("itemName").value;

  const category = document.getElementById("itemCategory").value;

  const stock = document.getElementById("itemStock").value;

  const unit = document.getElementById("itemUnit").value;

  const cost = document.getElementById("itemCost").value;

  const status = Number(stock) <= 3 ? "LOW" : "OK";

  const row = document.createElement("tr");

  row.innerHTML = `
        <td>${item}</td>
        <td>${category}</td>
        <td>${stock}</td>
        <td>${unit}</td>
        <td>Rp ${Number(cost).toLocaleString("id-ID")}</td>
        <td>
            <span class="${status === "LOW" ? "status-low" : "status-ok"}">
                ${status}
            </span>
        </td>
    `;

  document.getElementById("inventoryTable").appendChild(row);

  e.target.reset();

  inventoryModal.classList.remove("active");
});

document.getElementById("searchInventory").addEventListener("keyup", (e) => {
  const keyword = e.target.value.toLowerCase();

  document.querySelectorAll("#inventoryTable tr").forEach((row) => {
    row.style.display = row.innerText.toLowerCase().includes(keyword)
      ? ""
      : "none";
  });
});
