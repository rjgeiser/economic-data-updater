console.log("🚀 dashboard.js loaded");

const dataSources = {
  Eggs: "https://docs.google.com/spreadsheets/d/e/2PACX-1vST6GB3NYi4TQFCB-tF46TXuqHoX5KTd1jjgcO4i2o8CMlu-M9fUC9ZqvvsxynK2eOl0ZJ8cD8pLBt_/pub?gid=0&single=true&output=csv",
  Gas: "https://docs.google.com/spreadsheets/d/e/2PACX-1vST6GB3NYi4TQFCB-tF46TXuqHoX5KTd1jjgcO4i2o8CMlu-M9fUC9ZqvvsxynK2eOl0ZJ8cD8pLBt_/pub?gid=1376176610&single=true&output=csv",
  iPhone: "https://docs.google.com/spreadsheets/d/e/2PACX-1vST6GB3NYi4TQFCB-tF46TXuqHoX5KTd1jjgcO4i2o8CMlu-M9fUC9ZqvvsxynK2eOl0ZJ8cD8pLBt_/pub?gid=372313849&single=true&output=csv",
  RAV4: "https://docs.google.com/spreadsheets/d/e/2PACX-1vST6GB3NYi4TQFCB-tF46TXuqHoX5KTd1jjgcO4i2o8CMlu-M9fUC9ZqvvsxynK2eOl0ZJ8cD8pLBt_/pub?gid=509103836&single=true&output=csv",
  Rates: "https://docs.google.com/spreadsheets/d/e/2PACX-1vST6GB3NYi4TQFCB-tF46TXuqHoX5KTd1jjgcO4i2o8CMlu-M9fUC9ZqvvsxynK2eOl0ZJ8cD8pLBt_/pub?gid=388261679&single=true&output=csv",
  Market: "https://docs.google.com/spreadsheets/d/e/2PACX-1vST6GB3NYi4TQFCB-tF46TXuqHoX5KTd1jjgcO4i2o8CMlu-M9fUC9ZqvvsxynK2eOl0ZJ8cD8pLBt_/pub?gid=482309404&single=true&output=csv",
  Events: "https://docs.google.com/spreadsheets/d/e/2PACX-1vST6GB3NYi4TQFCB-tF46TXuqHoX5KTd1jjgcO4i2o8CMlu-M9fUC9ZqvvsxynK2eOl0ZJ8cD8pLBt_/pub?gid=1572154206&single=true&output=csv"
};

function parseCSV(text) {
  const [header, ...lines] = text.trim().split("\n");
  const headers = header.split(",").map(h => h.trim().replace(/\r/g, ""));
  return lines.map(line => {
    const row = {};
    line.split(",").forEach((cell, i) => {
      row[headers[i]] = cell.trim();
    });
    return row;
  });
}

function parseValue(val) {
  return isNaN(parseFloat(val)) ? null : parseFloat(val);
}

async function fetchData() {
  const merged = {};
  const annotations = [];

  for (const [label, url] of Object.entries(dataSources)) {
    const res = await fetch(url);
    const text = await res.text();
    const rows = parseCSV(text);

    if (label === "Events") {
      rows.forEach(event => {
        if (event.Date && event.Title) {
          annotations.push({
            type: "line",
            mode: "vertical",
            scaleID: "x",
            value: event.Date,
            borderColor: "gray",
            borderWidth: 1,
            label: {
              content: event.Title,
              enabled: true,
              rotation: 90
            }
          });
        }
      });
    } else {
      rows.forEach(row => {
        const date = row.Date;
        const value = parseValue(
          row["Price (USD)"] || row["Price (USD per gallon)"] || row["Rate (%)"] || row["Close"]
        );
        if (!merged[date]) merged[date] = { date };
        merged[date][label] = value;
      });
    }
  }

  const data = Object.values(merged).sort((a, b) => new Date(a.date) - new Date(b.date));
  renderChart(data, annotations);
}

function renderChart(data, annotations) {
  const container = document.getElementById("root");
  container.innerHTML = `
    <div class="p-4">
      <h1 class="text-2xl font-semibold mb-4">📊 Economic Dashboard with Policy Events</h1>
      <canvas id="chartCanvas" height="400"></canvas>
    </div>
  `;

  const ctx = document.getElementById("chartCanvas").getContext("2d");
  const labels = data.map(d => d.date);
  const keys = ["Eggs", "Gas", "iPhone", "RAV4", "Rates", "Market"];
  const colors = ["#f87171", "#60a5fa", "#34d399", "#fbbf24", "#a78bfa", "#f472b6"];

  const datasets = keys.map((key, i) => ({
    label: key,
    data: data.map(d => d[key] ?? null),
    borderColor: colors[i],
    fill: false,
    tension: 0.3
  }));

  new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top" },
        title: {
          display: true,
          text: "Price, Market, and Rate Trends with Policy Events"
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

fetchData();
