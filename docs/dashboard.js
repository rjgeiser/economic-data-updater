
console.log("🚀 dashboard.js loaded");

const BASE_URL = "https://docs.google.com/spreadsheets/d/12_lLnv3t7Om8XHRwFA7spCJ8at282WE7hisxu23gITo/gviz/tq?tqx=out:csv&sheet=";

const DATA_SOURCES = {
  Eggs: BASE_URL + "Egg_Prices",
  Gas: BASE_URL + "Gas_Prices",
  iPhone: BASE_URL + "iPhone_Prices",
  RAV4: BASE_URL + "Car_Prices",
  "Interest Rate (%)": BASE_URL + "Interest_Rates",
  "S&P 500": BASE_URL + "Stock_Market"
};

const POLICY_EVENTS_CSV = BASE_URL + "Policy_Events";

function parseCSV(text) {
  const [headerLine, ...lines] = text.trim().split("\n");
  const headers = headerLine.split(",").map(h => h.trim());
  return lines.map(line => {
    const cells = line.split(",");
    const row = {};
    headers.forEach((h, i) => {
      row[h] = cells[i] ? cells[i].trim() : "";
    });
    return row;
  });
}

async function fetchAndBuildChart() {
  const allData = {};

  for (const [label, url] of Object.entries(DATA_SOURCES)) {
    const res = await fetch(url);
    const text = await res.text();
    const parsed = parseCSV(text);

    parsed.forEach(row => {
      const date = row.Date;
      const rawVal = row["Price (USD)"] || row["Price (USD per gallon)"] || row["Rate (%)"] || row["Close"];
      const value = parseFloat(rawVal || "0");
      if (!allData[date]) allData[date] = { date };
      allData[date][label] = value;
    });
  }

  const policyRes = await fetch(POLICY_EVENTS_CSV);
  const policyText = await policyRes.text();
  const policyRows = parseCSV(policyText);
  const policyEvents = policyRows.map(row => ({
    date: row.Date,
    label: row.Title || row.Type
  }));

  const merged = Object.values(allData).sort((a, b) => new Date(a.date) - new Date(b.date));
  renderChart(merged, policyEvents);
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

  const annotations = policyEvents.map((e, i) => ({
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
        legend: {
          position: "top"
        },
        title: {
          display: true,
          text: "Prices, Markets, and Policy Over Time"
        },
        annotation: {
          annotations
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: "Date"
          }
        },
        y: {
          title: {
            display: true,
            text: "Value"
          }
        }
      }
    },
    plugins: [Chart.registry.getPlugin("annotation")]
  });
}

// Load Chart.js annotation plugin and then build chart
const annotationScript = document.createElement("script");
annotationScript.src = "https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@1.4.0";
annotationScript.onload = fetchAndBuildChart;
document.head.appendChild(annotationScript);
