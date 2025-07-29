document.addEventListener("DOMContentLoaded", async () => {
    const res = await fetch("/pr_data");
    const data = await res.json();

    const select = document.getElementById("exerciseSelect");
    Object.keys(data).forEach(ex => {
        const opt = document.createElement("option");
        opt.value = ex;
        opt.innerText = ex;
        select.appendChild(opt);
    });

    const ctx = document.getElementById("prChart").getContext("2d");
    let chart;

    function updateChart(exercise) {
        const exData = data[exercise];
        const labels = exData.map(e => e.date);
        const weights = exData.map(e => e.weight);

        if (chart) chart.destroy();
        chart = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    label: "PR Weight",
                    data: weights,
                    borderColor: "blue",
                    fill: false
                }]
            }
        });
    }

    select.addEventListener("change", e => updateChart(e.target.value));

    if (Object.keys(data).length > 0) {
        select.value = Object.keys(data)[0];
        updateChart(select.value);
    }
});
