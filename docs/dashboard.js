
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
let usePercentView = false;
let selectedSeries = new Set(Object.keys(DATA_FILES));

async function fetchJSON(url) {
  const res = await fetch(url);
  return res.json();
}

function buildControls() {
  const controls = document.createElement("div");
  controls.className = "flex justify-between items-center mb-4";

  // Checkbox group
  const checkboxGroup = document.createElement("div");
  checkboxGroup.className = "flex flex-wrap gap-4";
  Object.keys(DATA_FILES).forEach((key) => {
    const label = document.createElement("label");
    label.className = "text-sm";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        selectedSeries.add(key);
      } else {
        selectedSeries.delete(key);
      }
      renderChart(window.chartData, window.policyEvents);
    });
    label.appendChild(checkbox);
    label.append(" " + key);
    checkboxGroup.appendChild(label);
  });

  // Toggle
  const toggle = document.createElement("label");
  toggle.className = "flex items-center gap-2 text-sm";
  const toggleInput = document.createElement("input");
  toggleInput.type = "checkbox";
  toggleInput.addEventListener("change", () => {
    usePercentView = toggleInput.checked;
    renderChart(window.chartData, window.policyEvents);
  });
  toggle.appendChild(toggleInput);
  toggle.append(" % Change View");

  controls.appendChild(checkboxGroup);
  controls.appendChild(toggle);

  return controls;
}

function normalizeSeries(data, keys) {
  const baselines = {};
  keys.forEach((key) => {
    const first = data.find((d) => d[key] !== undefined);
    baselines[key] = first ? first[key] : 1;
  });

  return data.map((d) => {
    const out = { date: d.date };
    keys.forEach((key) => {
      if (d[key] !== undefined) {
        out[key] = (d[key] / baselines[key]) * 100;
      }
    });
    return out;
  });
}

async function loadAllData() {
  const allData = {};
  for (const [label, path] of Object.entries(DATA_FILES)) {
    const rows = await fetchJSON(path);
    rows.forEach((row) => {
      const date = row.Date;
      const rawVal = row["Price (USD)"] || row["Price (USD per gallon)"] || row["Rate (%)"] || row["Close"];
      const value = parseFloat(rawVal || "0");
      if (!allData[date]) allData[date] = { date };
      allData[date][label] = value;
    });
  }

  const policyEvents = await fetchJSON(POLICY_EVENTS_FILE);
  const policyMarkers = policyEvents.map((event) => ({
    date: event.Date,
    label: event.Title || event.Type
  }));

  const merged = Object.values(allData).sort((a, b) => new Date(a.date) - new Date(b.date));
  window.chartData = merged;
  window.policyEvents = policyMarkers;
  renderChart(merged, policyMarkers);
}

function renderChart(data, policyEvents) {
  const container = document.getElementById("root");
  container.innerHTML = "";

  container.appendChild(buildControls());
  container.innerHTML += `<canvas id="chartCanvas" height="400"></canvas>`;

  const ctx = document.getElementById("chartCanvas").getContext("2d");

  const filteredKeys = Array.from(selectedSeries);
  const normalized = usePercentView ? normalizeSeries(data, filteredKeys) : data;

  const labels = normalized.map((d) => d.date);
  const datasets = filteredKeys.map((key, i) => ({
    label: key,
    data: normalized.map((d) => d[key] ?? null),
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
    data: { labels, datasets },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top" },
        title: { display: true, text: "Prices, Markets, and Policy Over Time" },
        annotation: { annotations }
      },
      scales: {
        x: { title: { display: true, text: "Date" } },
        y: { title: { display: true, text: usePercentView ? "% of Baseline" : "Value" } }
      }
    },
    plugins: [Chart.registry.getPlugin("annotation")]
  });
}

const annotationScript = document.createElement("script");
annotationScript.src = "https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@1.4.0";
annotationScript.onload = loadAllData;
document.head.appendChild(annotationScript);
