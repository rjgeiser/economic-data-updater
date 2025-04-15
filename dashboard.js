
console.log("🚀 dashboard.js loaded");

const DATA_FILES = {
  Eggs: "data/Egg_Prices.json",
  Gas: "data/Gas_Prices.json",
  iPhone: "data/iPhone_Prices.json",
  RAV4: "data/Car_Prices.json",
  "Interest Rate (%)": "data/Interest_Rates.json",
  "S&P 500": "data/Stock_Market.json"
};

const POLICY_EVENTS_FILE = "data/Policy_Events.json";

async function fetchJSON(url) {
  const res = await fetch(url);
  return res.json();
}

async function loadAllData() {
  const allData = {};
  for (const [label, path] of Object.entries(DATA_FILES)) {
    const rows = await fetchJSON(path);
    rows.forEach(row => {
      const date = row.Date;
      const rawVal = row["Price (USD)"] || row["Price (USD per gallon)"] || row["Rate (%)"] || row["Close"];
      const value = parseFloat(rawVal || "0");
      if (!allData[date]) allData[date] = { date };
      allData[date][label] = value;
    });
  }

  const policyEvents = await fetchJSON(POLICY_EVENTS_FILE);
  const policyMarkers = policyEvents.map(event => ({
    date: event.Date,
    label: event.Title || event.Type
  }));

  const merged = Object.values(allData).sort((a, b) => new Date(a.date) - new Date(b.date));
  renderChart(merged, policyMarkers);
}

function renderChart(data, policyEvents) {
  const container = document.getElementById("root");
  container.innerHTML = `
    <div class="p-4">
      <h1 class="text-2xl font-semibold mb-4">📊 Economic Data Overview</h1>
      <canvas id="chartCanvas" height="400"></canvas>
    </div>
  `;

  const ctx = document.getElementById("chartCanvas").getContext("2d");

  const labels = data.map((d) => d.date);
  const seriesKeys = Object.keys(data[0]).filter(k => k !== "date");
  const datasets = seriesKeys.map((key, i) => ({
    label: key,
    data: data.map((d) => d[key] || null),
    borderColor: ["#f87171", "#60a5fa", "#34d399", "#fbbf24", "#6366f1", "#10b981"][i % 6],
    fill: false,
    tension: 0.3
  }));

  const annotations = policyEvents.map(e => ({
    type: "line",
    xMin: e.date,
    xMax: e.date,
    borderColor: "#e11d48",
    borderWidth: 1,
    label: {
      content: e.label,
      enabled: true,
      position: "start",
      rotation: 90,
      backgroundColor: "rgba(225,29,72,0.8)",
      color: "white",
      font: { size: 10 }
    }
  }));

  new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets
    },
    options: {
      responsive: true,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: { position: "top" },
        title: {
          display: true,
          text: "Prices, Markets, and Policy Over Time"
        },
        annotation: { annotations }
      },
      scales: {
        x: { title: { display: true, text: "Date" } },
        y: { title: { display: true, text: "Value" } }
      }
    },
    plugins: [Chart.registry.getPlugin("annotation")]
  });
}

const annotationScript = document.createElement("script");
annotationScript.src = "https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@1.4.0";
annotationScript.onload = loadAllData;
document.head.appendChild(annotationScript);
