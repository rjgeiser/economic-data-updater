
const SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vST6GB3NYi4TQFCB-tF46TXuqHoX5KTd1jjgcO4i2o8CMlu-M9fUC9ZqvvsxynK2eOl0ZJ8cD8pLBt_/pub?output=tsv";

const script = document.createElement("script");
script.src = "https://cdn.jsdelivr.net/npm/tabletop@1.6.0/tabletop.min.js";
document.head.appendChild(script);

script.onload = () => {
  Tabletop.init({
    key: SHEET_URL,
    simpleSheet: false,
    callback: (data) => {
      const parseSheet = (name) =>
        data[name].elements.map((row) => ({
          date: row.Date,
          value: parseFloat(row["Price (USD)"] || row["Price (USD per gallon)"] || "0")
        }));

      const sheets = {
        Eggs: parseSheet("Egg_Prices"),
        Gas: parseSheet("Gas_Prices"),
        iPhone: parseSheet("iPhone_Prices"),
        RAV4: parseSheet("Car_Prices")
      };

      const merged = {};

      Object.entries(sheets).forEach(([label, rows]) => {
        rows.forEach(({ date, value }) => {
          if (!merged[date]) merged[date] = { date };
          merged[date][label] = value;
        });
      });

      const finalData = Object.values(merged).sort((a, b) =>
        new Date(a.date) - new Date(b.date)
      );

      renderChart(finalData);
    }
  });
};

function renderChart(data) {
  const container = document.getElementById("root");
  container.innerHTML = "";

  const el = document.createElement("div");
  el.className = "p-4";
  el.innerHTML = \``
    <div class="p-4">
      <h1 class="text-2xl font-semibold mb-4">📊 Economic Data Overview</h1>
      <canvas id="chartCanvas" height="400"></canvas>
    </div>
  \``;
  container.appendChild(el);

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
