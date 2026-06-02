document.addEventListener(
    "DOMContentLoaded",
    () => {

        initializeChart();

    }
);

function initializeChart(){

    const canvas =
    document.getElementById(
        "profitChart"
    );

    if(!canvas){
        return;
    }

    const ctx =
    canvas.getContext("2d");

    new Chart(ctx, {

        type:"line",

        data:{

            labels:[
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun"
            ],

            datasets:[

                {

                    label:"Revenue",

                    data:[
                        12,
                        19,
                        15,
                        25,
                        30,
                        48
                    ],

                    borderColor:
                    "#00d5ff",

                    tension:0.4
                },

                {

                    label:"Profit",

                    data:[
                        4,
                        8,
                        6,
                        10,
                        12,
                        17
                    ],

                    borderColor:
                    "#00ff88",

                    tension:0.4
                }

            ]

        },

        options:{

            responsive:true,

            maintainAspectRatio:false,

            plugins:{

                legend:{
                    labels:{
                        color:"#fff"
                    }
                }

            },

            scales:{

                x:{
                    ticks:{
                        color:"#8d98b3"
                    },
                    grid:{
                        color:
                        "rgba(255,255,255,.04)"
                    }
                },

                y:{
                    ticks:{
                        color:"#8d98b3"
                    },
                    grid:{
                        color:
                        "rgba(255,255,255,.04)"
                    }
                }

            }

        }

    });

}