document.addEventListener("DOMContentLoaded", () => {
  initializeCharts();
});

function initializeCharts() {
  createRevenueProfitChart();

  createConversionChart();

  createServiceChart();

  createMaterialChart();
}

function createRevenueProfitChart() {
  new Chart(
    document.getElementById("revenueProfitChart"),

    {
      type: "line",

      data: {
        labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],

        datasets: [
          {
            label: "Revenue",

            data: [12, 15, 20, 18, 25, 48],

            borderColor: "#00d5ff",

            tension: 0.4,
          },

          {
            label: "Profit",

            data: [5, 7, 9, 8, 12, 31],

            borderColor: "#00ff88",

            tension: 0.4,
          },
        ],
      },
    },
  );
}

function createConversionChart() {
  new Chart(
    document.getElementById("conversionChart"),

    {
      type: "doughnut",

      data: {
        labels: ["Converted", "Lost"],

        datasets: [
          {
            data: [78, 22],
          },
        ],
      },
    },
  );
}

function createServiceChart() {
  new Chart(
    document.getElementById("serviceChart"),

    {
      type: "bar",

      data: {
        labels: ["Restoration", "Paint", "Detailing", "CVT"],

        datasets: [
          {
            label: "Projects",

            data: [24, 41, 18, 12],
          },
        ],
      },
    },
  );
}

function createMaterialChart() {
  new Chart(
    document.getElementById("materialChart"),

    {
      type: "polarArea",

      data: {
        labels: ["Primer", "Basecoat", "Clear Coat", "Compound"],

        datasets: [
          {
            data: [25, 35, 30, 10],
          },
        ],
      },
    },
  );
}
