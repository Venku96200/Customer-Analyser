const batchErrorBox = document.getElementById("batch-error");
const batchBody = document.getElementById("batch-body");
const openDashboardButton = document.getElementById("open-dashboard");
const batchDashboard = document.getElementById("batch-dashboard");
const dashboardMetrics = document.getElementById("dashboard-metrics");

let lastBatchPredictions = [];
let dashboardCharts = [];

function destroyDashboardCharts() {
  dashboardCharts.forEach((chart) => chart.destroy());
  dashboardCharts = [];
}

function countBy(items, selector) {
  return items.reduce((accumulator, item) => {
    const key = selector(item);
    accumulator[key] = (accumulator[key] || 0) + 1;
    return accumulator;
  }, {});
}

function renderBatchDashboard(predictions) {
  if (!predictions.length) {
    return;
  }

  const totalCustomers = predictions.length;
  const churnCount = predictions.filter((item) => item.prediction === "Churn").length;
  const noChurnCount = totalCustomers - churnCount;
  const highRiskCount = predictions.filter((item) => item.risk_level === "High").length;
  const averageProbability = predictions.reduce((sum, item) => sum + item.churn_probability, 0) / totalCustomers;
  const churnRate = (churnCount / totalCustomers) * 100;

  dashboardMetrics.innerHTML = `
    <article class="metric-card">
      <span class="metric-label">Total customers</span>
      <span class="metric-value">${totalCustomers}</span>
    </article>
    <article class="metric-card">
      <span class="metric-label">Predicted churn</span>
      <span class="metric-value">${churnRate.toFixed(1)}%</span>
    </article>
    <article class="metric-card">
      <span class="metric-label">Average churn probability</span>
      <span class="metric-value">${(averageProbability * 100).toFixed(1)}%</span>
    </article>
    <article class="metric-card">
      <span class="metric-label">High-risk customers</span>
      <span class="metric-value">${highRiskCount}</span>
    </article>
  `;

  destroyDashboardCharts();

  Chart.defaults.color = "#5f7e99";
  Chart.defaults.font.family = '"Segoe UI", Arial, sans-serif';
  Chart.defaults.borderColor = "rgba(95, 126, 153, 0.14)";

  dashboardCharts.push(
    new Chart(document.getElementById("churn-split-chart"), {
      type: "doughnut",
      data: {
        labels: ["Churn", "No Churn"],
        datasets: [
          {
            data: [churnCount, noChurnCount],
            backgroundColor: ["#e05566", "#4b9dff"],
            borderWidth: 0,
          },
        ],
      },
      options: {
        plugins: {
          legend: { position: "bottom" },
        },
      },
    }),
  );

  const riskCounts = countBy(predictions, (item) => item.risk_level);
  dashboardCharts.push(
    new Chart(document.getElementById("risk-distribution-chart"), {
      type: "bar",
      data: {
        labels: ["Low", "Medium", "High"],
        datasets: [
          {
            label: "Customers",
            data: ["Low", "Medium", "High"].map((risk) => riskCounts[risk] || 0),
            backgroundColor: ["#89d9b0", "#ffd27f", "#ff9fac"],
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0 },
          },
        },
      },
    }),
  );

  const contractStats = predictions.reduce((accumulator, item) => {
    const contract = item.customer_input.Contract;
    const bucket = accumulator[contract] || { total: 0, churn: 0 };
    bucket.total += 1;
    if (item.prediction === "Churn") {
      bucket.churn += 1;
    }
    accumulator[contract] = bucket;
    return accumulator;
  }, {});
  const contractLabels = Object.keys(contractStats);
  const contractRates = contractLabels.map((contract) => {
    const bucket = contractStats[contract];
    return bucket.total ? (bucket.churn / bucket.total) * 100 : 0;
  });

  dashboardCharts.push(
    new Chart(document.getElementById("contract-churn-chart"), {
      type: "bar",
      data: {
        labels: contractLabels,
        datasets: [
          {
            label: "Predicted churn rate %",
            data: contractRates,
            backgroundColor: "#7cc0ff",
            borderRadius: 8,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            beginAtZero: true,
            max: 100,
          },
        },
      },
    }),
  );

  batchDashboard.classList.remove("hidden");
  openDashboardButton.classList.remove("is-hidden");
  batchDashboard.scrollIntoView({ behavior: "smooth", block: "start" });
}

document.getElementById("home").addEventListener("click", () => {
  location.href = "/app/menu";
});

document.getElementById("batch-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  batchErrorBox.style.display = "none";
  document.getElementById("batch-result").style.display = "none";

  const formData = new FormData(event.currentTarget);

  try {
    const response = await fetchWithAuth("/predict/batch", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Batch prediction failed.");
    }

    const data = await response.json();
    lastBatchPredictions = data.predictions;
    batchBody.innerHTML = data.predictions
      .map(
        (prediction) =>
          `<tr><td>${prediction.row_number}</td><td>${prediction.prediction}</td><td>${prediction.risk_level}</td><td>${(prediction.churn_probability * 100).toFixed(1)}%</td></tr>`,
      )
      .join("");
    document.getElementById("batch-result").style.display = "block";
    batchDashboard.classList.add("hidden");
    openDashboardButton.classList.remove("is-hidden");
  } catch (error) {
    batchErrorBox.textContent = error.message;
    batchErrorBox.style.display = "block";
  }
});

openDashboardButton.addEventListener("click", () => {
  if (lastBatchPredictions.length) {
    renderBatchDashboard(lastBatchPredictions);
  }
});
