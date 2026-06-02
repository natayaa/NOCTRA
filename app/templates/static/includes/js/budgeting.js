const expenseModal = document.getElementById("expenseModal");

document.getElementById("addExpenseBtn").addEventListener("click", () => {
  expenseModal.classList.add("active");
});

document.getElementById("closeExpenseModal").addEventListener("click", () => {
  expenseModal.classList.remove("active");
});

document.getElementById("expenseForm").addEventListener("submit", (e) => {
  e.preventDefault();

  const date = document.getElementById("expenseDate").value;

  const category = document.getElementById("expenseCategory").value;

  const description = document.getElementById("expenseDescription").value;

  const amount = document.getElementById("expenseAmount").value;

  const row = document.createElement("tr");

  row.innerHTML = `
            <td>${date}</td>
            <td>${category}</td>
            <td>${description}</td>
            <td>Rp ${Number(amount).toLocaleString("id-ID")}</td>
        `;

  document.getElementById("expenseTable").appendChild(row);

  expenseModal.classList.remove("active");

  e.target.reset();
});

// Expense Trend

new Chart(document.getElementById("expenseChart"), {
  type: "line",

  data: {
    labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],

    datasets: [
      {
        label: "Expenses",

        data: [2, 3, 2.5, 4, 3.8, 5],

        borderColor: "#00d5ff",

        tension: 0.4,
      },
    ],
  },
});

// Expense Breakdown

new Chart(document.getElementById("expensePieChart"), {
  type: "doughnut",

  data: {
    labels: ["Material", "Labor", "Operational", "Equipment"],

    datasets: [
      {
        data: [40, 30, 20, 10],
      },
    ],
  },
});
