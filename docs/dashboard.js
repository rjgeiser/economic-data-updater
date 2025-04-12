
console.log("🚧 dashboard.js loaded");

const SHEET_BASE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vST6GB3NYi4TQFCB-tF46TXuqHoX5KTd1jjgcO4i2o8CMlu-M9fUC9ZqvvsxynK2eOl0ZJ8cD8pLBt_/pub?output=csv&gid=";

const tabs = {
  Eggs: "0",
  Gas: "1376176610",
  iPhone: "372313849",
  RAV4: "509103836"
};

function parseCSV(text) {
  const [headerLine, ...lines] = text.trim().split("\n");
  const headers = headerLine.split(",").map(h => h.trim().replace(/\r/, ""));
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

  for (const [label, gid] of Object.entries(tabs)) {
    const res = await fetch(SHEET_BASE + gid);
    const text = await res.text();
    const parsed = parseCSV(text);

    parsed.forEach(row => {
      const date = row.Date;
      const price = parseFloat(row["Price (USD)"] || row["Price (USD per gallon)"] || "0");
      if (!allData[date]) allData[date] = { date };
      allData[date][label] = price;
    });
  }

  const merged = Object.values(allData).sort((a, b) => new Date(a.date) - new Date(b.date));
  renderChart(merged);
}

function renderChart(data) {
  const container = document.getElementById("root");
  container.innerHTML = `
    <div class="p-4">
      <h1 class="text-2xl font-semibold mb-4">📊 Economic Data Overview</h1>
      <canvas id="chartCanvas" height="400"></canvas>
    </div>
  `;

  const ctx = document.getElementById("chartCanvas").getContext("2d");

  const labels = data.map((d) => d.date);
  const datasets = ["Eggs", "Gas", "iPhone", "RAV4"].map((key, i) => ({
    label: key,
    data: data.map((d) => d[key] || null),
    borderColor: ["#f87171", "#60a5fa", "#34d399", "#fbbf24"][i],
    fill: false,
    tension: 0.3
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
          text: "Prices and Economic Data Over Time"
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
            text: "Value (USD)"
          }
        }
      }
    }
  });
}

fetchAndBuildChart();
