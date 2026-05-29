const ctx = document
    .getElementById("profitChart")
    .getContext("2d");

new Chart(ctx, {
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
            label: "Profit",

            data: [
                4200000,
                6800000,
                7200000,
                9100000,
                11800000,
                12100000
            ],

            borderColor: "#00d5ff",

            backgroundColor: "rgba(0,213,255,.15)",

            tension: 0.4,

            fill: true
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
                    color: "#8f99b3"
                },

                grid: {
                    color: "rgba(255,255,255,.05)"
                }
            },

            y: {
                ticks: {
                    color: "#8f99b3"
                },

                grid: {
                    color: "rgba(255,255,255,.05)"
                }
            }

        }

    }
});