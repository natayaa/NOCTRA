// EXPENSE CHART

const expenseCtx = document
    .getElementById("expenseChart");

new Chart(expenseCtx, {

    type: "line",

    data: {

        labels: [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun"
        ],

        datasets: [{

            label: "Expenses",

            data: [
                3,
                4,
                5,
                7,
                6,
                8
            ],

            borderColor: "#00d5ff",

            backgroundColor: "rgba(0,213,255,.12)",

            fill: true,

            tension: .4

        }]

    },

    options: {

        responsive: true,

        plugins: {
            legend: {
                labels: {
                    color: "#fff"
                }
            }
        },

        scales: {

            x: {
                ticks: {
                    color: "#8d98b3"
                },

                grid: {
                    color: "rgba(255,255,255,.04)"
                }
            },

            y: {
                ticks: {
                    color: "#8d98b3"
                },

                grid: {
                    color: "rgba(255,255,255,.04)"
                }
            }

        }

    }

});


// BUDGET DISTRIBUTION

const budgetCtx = document
    .getElementById("budgetChart");

new Chart(budgetCtx, {

    type: "doughnut",

    data: {

        labels: [
            "Operational",
            "Paint",
            "Detailing",
            "Tools"
        ],

        datasets: [{

            data: [
                40,
                30,
                20,
                10
            ],

            backgroundColor: [
                "#00d5ff",
                "#9747ff",
                "#00ff88",
                "#ffb020"
            ],

            borderWidth: 0

        }]

    },

    options: {

        plugins: {
            legend: {
                labels: {
                    color: "#fff"
                }
            }
        }

    }

});

// MODAL

const modal = document.getElementById("expenseModal");

const openBtn = document.getElementById("openModal");

const closeBtn = document.getElementById("closeModal");


openBtn.addEventListener("click", () => {
    modal.classList.add("active");
});


closeBtn.addEventListener("click", () => {
    modal.classList.remove("active");
});


modal.addEventListener("click", (e) => {

    if (e.target === modal) {
        modal.classList.remove("active");
    }

});