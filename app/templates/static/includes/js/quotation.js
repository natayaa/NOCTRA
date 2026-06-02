let laborTotal = 0;
let materialTotal = 0;

document.getElementById("addServiceBtn").addEventListener("click", () => {
  const price = prompt("Service Price");

  laborTotal += Number(price);

  calculate();
});

document.getElementById("addMaterialBtn").addEventListener("click", () => {
  const price = prompt("Material Cost");

  materialTotal += Number(price);

  calculate();
});

function calculate() {
  const margin = (laborTotal + materialTotal) * 0.4;

  const grand = laborTotal + materialTotal + margin;

  document.getElementById("laborTotal").innerText = formatIDR(laborTotal);

  document.getElementById("materialTotal").innerText = formatIDR(materialTotal);

  document.getElementById("marginTotal").innerText = formatIDR(margin);

  document.getElementById("grandTotal").innerText = formatIDR(grand);
}

function formatIDR(value) {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",

    currency: "IDR",
  }).format(value);
}
