
console.log("🚧 dashboard.js loaded");

const SHEET_BASE = "https://docs.google.com/spreadsheets/d/12_lLnv3t7Om8XHRwFA7spCJ8at282WE7hisxu23gITo/gviz/tq?tqx=out:csv&sheet=";

const tabs = {
  Eggs: "Egg_Prices",
  Gas: "Gas_Prices",
  iPhone: "iPhone_Prices",
  RAV4: "Car_Prices"
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
