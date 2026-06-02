const inquiryCards = document.querySelectorAll(".inquiry-card");

const customerName = document.getElementById("customerName");

const motorbikeName = document.getElementById("motorbikeName");

const serviceName = document.getElementById("serviceName");

const budget = document.getElementById("budget");

const phone = document.getElementById("phone");

let selectedPhone = "";

inquiryCards.forEach((card) => {
  card.addEventListener("click", () => {
    document.querySelectorAll(".inquiry-card").forEach((c) => {
      c.classList.remove("active");
    });

    card.classList.add("active");

    customerName.textContent = card.dataset.customer;

    motorbikeName.textContent = card.dataset.motorbike;

    serviceName.textContent = card.dataset.service;

    budget.textContent =
      "Rp " + Number(card.dataset.budget).toLocaleString("id-ID");

    phone.textContent = card.dataset.phone;

    selectedPhone = card.dataset.phone;
  });
});

document.getElementById("searchInquiry").addEventListener("keyup", (e) => {
  const keyword = e.target.value.toLowerCase();

  document.querySelectorAll(".inquiry-card").forEach((card) => {
    card.style.display = card.innerText.toLowerCase().includes(keyword)
      ? ""
      : "none";
  });
});

document.getElementById("whatsappBtn").addEventListener("click", () => {
  if (!selectedPhone) {
    return;
  }

  window.open(`https://wa.me/${selectedPhone}`, "_blank");
});

document.getElementById("approveBtn").addEventListener("click", () => {
  alert("Inquiry Approved");
});

document.getElementById("rejectBtn").addEventListener("click", () => {
  alert("Inquiry Rejected");
});

document.getElementById("quoteBtn").addEventListener("click", () => {
  alert("Quotation Sent");
});

document.getElementById("createProjectBtn").addEventListener("click", () => {
  alert("Move to Projects");
});
