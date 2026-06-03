// ======================================
// UTILITIES
// ======================================

const formatCurrency = (amount) => {
  return `Rp ${Number(amount).toLocaleString("id-ID")}`;
};

const expenseModal = document.getElementById("expenseModal");
const expenseForm = document.getElementById("expenseForm");
const expenseTable = document.getElementById("expenseTable");

// ======================================
// MODAL
// ======================================

document.getElementById("addExpenseBtn")?.addEventListener("click", () => {
  expenseModal.classList.add("active");
});

document
  .getElementById("closeExpenseModal")
  ?.addEventListener("click", () => {
    expenseModal.classList.remove("active");
  });

expenseModal?.addEventListener("click", (e) => {
  if (e.target === expenseModal) {
    expenseModal.classList.remove("active");
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    expenseModal.classList.remove("active");
  }
});

// ======================================
// EXPENSE FORM
// ======================================

expenseForm?.addEventListener("submit", (e) => {
  e.preventDefault();

  const date = document.getElementById("expenseDate").value;
  const project = document.getElementById("expenseProject").value;
  const category = document.getElementById("expenseCategory").value;
  const description = document
    .getElementById("expenseDescription")
    .value.trim();
  const amount = document.getElementById("expenseAmount").value;

  const row = document.createElement("tr");

  row.innerHTML = `
    <td>${date}</td>
    <td>${project}</td>
    <td>${category}</td>
    <td>${description}</td>
    <td>${formatCurrency(amount)}</td>
  `;

  expenseTable.prepend(row);

  expenseForm.reset();
  expenseModal.classList.remove("active");

  updateExpenseSummary();
});

// ======================================
// SEARCH
// ======================================

const expenseSearch = document.getElementById("expenseSearch");

expenseSearch?.addEventListener("input", (e) => {
  const searchTerm = e.target.value.toLowerCase();

  [...expenseTable.querySelectorAll("tr")].forEach((row) => {
    const text = row.textContent.toLowerCase();

    row.style.display = text.includes(searchTerm) ? "" : "none";
  });
});

// ======================================
// CATEGORY FILTER
// ======================================

const expenseFilter = document.getElementById("expenseFilter");

expenseFilter?.addEventListener("change", (e) => {
  const selected = e.target.value.toLowerCase();

  [...expenseTable.querySelectorAll("tr")].forEach((row) => {
    const category =
      row.children[2]?.textContent.toLowerCase() ?? "";

    if (
      selected === "all categories" ||
      category === selected
    ) {
      row.style.display = "";
    } else {
      row.style.display = "none";
    }
  });
});

// ======================================
// KPI UPDATE
// ======================================

function updateExpenseSummary() {
  let totalExpenses = 0;

  [...expenseTable.querySelectorAll("tr")].forEach((row) => {
    const amountCell = row.children[4];

    if (!amountCell) return;

    const value = amountCell.textContent
      .replace(/[^\d]/g, "");

    totalExpenses += Number(value);
  });

  const expenseCard = document.querySelector(
    ".stat-card.expense h2"
  );

  if (expenseCard) {
    expenseCard.textContent = formatCurrency(totalExpenses);
  }
}

// ======================================
// CHART DEFAULT CONFIG
// ======================================

Chart.defaults.color = "#9ca3af";
Chart.defaults.borderColor = "rgba(255,255,255,0.08)";
Chart.defaults.font.family =
  "Inter, system-ui, sans-serif";

// ======================================
// MONTHLY EXPENSES
// ======================================

new Chart(
  document.getElementById("expenseChart"),
  {
    type: "line",

    data: {
      labels: [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
      ],

      datasets: [
        {
          label: "Expenses",

          data: [
            2000000,
            3000000,
            2500000,
            4000000,
            3800000,
            5000000,
          ],

          borderColor: "#00d5ff",

          backgroundColor:
            "rgba(0,213,255,.12)",

          borderWidth: 3,

          fill: true,

          tension: 0.4,

          pointRadius: 4,
        },
      ],
    },

    options: {
      responsive: true,

      maintainAspectRatio: false,

      plugins: {
        legend: {
          display: false,
        },
      },

      scales: {
        y: {
          ticks: {
            callback: (value) =>
              `Rp ${(value / 1000000).toFixed(0)}M`,
          },
        },
      },
    },
  }
);

// ======================================
// EXPENSE BREAKDOWN
// ======================================

new Chart(
  document.getElementById("expensePieChart"),
  {
    type: "doughnut",

    data: {
      labels: [
        "Material",
        "Labor",
        "Operational",
        "Equipment",
      ],

      datasets: [
        {
          data: [45, 25, 20, 10],

          backgroundColor: [
            "#06b6d4",
            "#8b5cf6",
            "#f59e0b",
            "#ef4444",
          ],

          borderWidth: 0,
        },
      ],
    },

    options: {
      responsive: true,

      maintainAspectRatio: false,

      cutout: "70%",

      plugins: {
        legend: {
          position: "bottom",
        },
      },
    },
  }
);

// ======================================
// REVENUE VS EXPENSES
// ======================================

new Chart(
  document.getElementById("cashflowChart"),
  {
    type: "bar",

    data: {
      labels: [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
      ],

      datasets: [
        {
          label: "Revenue",

          data: [
            6000000,
            8500000,
            7000000,
            9500000,
            8200000,
            11000000,
          ],

          backgroundColor: "#22c55e",
        },

        {
          label: "Expenses",

          data: [
            2000000,
            3000000,
            2500000,
            4000000,
            3800000,
            5000000,
          ],

          backgroundColor: "#ef4444",
        },
      ],
    },

    options: {
      responsive: true,

      maintainAspectRatio: false,

      borderRadius: 8,

      plugins: {
        legend: {
          position: "top",
        },
      },

      scales: {
        y: {
          ticks: {
            callback: (value) =>
              `Rp ${(value / 1000000).toFixed(0)}M`,
          },
        },
      },
    },
  }
);

// ======================================
// PERIOD FILTER (PLACEHOLDER)
// ======================================

document
  .getElementById("periodFilter")
  ?.addEventListener("change", (e) => {
    console.log(
      `Selected period: ${e.target.value}`
    );

    // TODO:
    // fetch(`/api/budgeting?period=${e.target.value}`)
  });

// ======================================
// INIT
// ======================================

updateExpenseSummary();