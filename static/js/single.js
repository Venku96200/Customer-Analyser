const resultBox = document.getElementById("result");
const singleErrorBox = document.getElementById("single-error");
const historyBody = document.getElementById("history-body");
const clearHistoryButton = document.getElementById("clear-history");
const resultSummary = document.getElementById("result-summary");
const insightList = document.getElementById("insight-list");

async function loadHistory() {
  const response = await fetchWithAuth("/predictions");
  if (!response.ok) {
    historyBody.innerHTML = '<tr><td colspan="4">Unable to load history.</td></tr>';
    clearHistoryButton.disabled = true;
    return;
  }

  const records = await response.json();
  if (!records.length) {
    historyBody.innerHTML = '<tr><td colspan="4">No predictions yet.</td></tr>';
    clearHistoryButton.disabled = true;
    return;
  }

  clearHistoryButton.disabled = false;
  historyBody.innerHTML = records
    .map(
      (record) =>
        `<tr><td>${new Date(record.created_at).toLocaleString()}</td><td>${record.prediction}</td><td>${record.risk_level}</td><td>${(record.churn_probability * 100).toFixed(1)}%</td></tr>`,
    )
    .join("");
}

loadHistory();

document.getElementById("home").addEventListener("click", () => {
  location.href = "/app/menu";
});

document.getElementById("predict-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  singleErrorBox.style.display = "none";
  resultBox.style.display = "none";

  const formData = new FormData(event.currentTarget);
  const payload = {};
  for (const [key, value] of formData.entries()) {
    if (["tenure", "SeniorCitizen"].includes(key)) {
      payload[key] = parseInt(value, 10);
    } else if (["MonthlyCharges", "TotalCharges"].includes(key)) {
      payload[key] = parseFloat(value);
    } else {
      payload[key] = value;
    }
  }

  try {
    const response = await fetchWithAuth("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Prediction failed.");
    }

    const data = await response.json();
    resultBox.className = data.risk_level.toLowerCase();
    resultBox.style.display = "block";
    document.getElementById("result-label").textContent = `${data.prediction} - ${data.risk_level} risk`;
    document.getElementById("result-prob").textContent = `${(data.churn_probability * 100).toFixed(1)}% probability`;
    resultSummary.textContent = data.explanation.summary;
    insightList.innerHTML = data.explanation.drivers.length
      ? data.explanation.drivers
          .map(
            (driver) => `
          <article class="insight-card">
            <div class="insight-topline">
              <strong>${driver.feature_label}</strong>
              <span class="insight-share">${driver.contribution_percent.toFixed(1)}% impact</span>
            </div>
            <p class="insight-value">Current value: ${driver.current_value}</p>
            <p>${driver.reason}</p>
            <p><strong>Recommended improvement:</strong> ${driver.recommendation}${driver.estimated_probability_reduction > 0 ? ` Estimated reduction: about ${driver.estimated_probability_reduction.toFixed(1)} points.` : ""}</p>
          </article>
        `,
          )
          .join("")
      : `<article class="insight-card"><p>${data.explanation.headline}: no major actionable driver stands out for this prediction.</p></article>`;

    loadHistory();
  } catch (error) {
    singleErrorBox.textContent = error.message;
    singleErrorBox.style.display = "block";
  }
});

clearHistoryButton.addEventListener("click", async () => {
  if (clearHistoryButton.disabled) {
    return;
  }
  if (!confirm("Clear your prediction history?")) {
    return;
  }

  clearHistoryButton.disabled = true;
  singleErrorBox.style.display = "none";

  try {
    const response = await fetchWithAuth("/predictions", { method: "DELETE" });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Unable to clear history.");
    }

    resultBox.style.display = "none";
    await loadHistory();
  } catch (error) {
    singleErrorBox.textContent = error.message;
    singleErrorBox.style.display = "block";
    await loadHistory();
  }
});
