/* eslint-disable no-undef */
dayjs.extend(window.dayjs_plugin_utc);
dayjs.extend(window.dayjs_plugin_timezone);

// ---------- Config ----------
const PATH_PREFIX = "docs/data/"; // change to "data/" if serving data directory next to this page
const SERIES = {
  "Eggs": { file: "Egg_Prices.json", valueKeys: ["Price (USD per dozen)"] },
  "Gas": { file: "Gas_Prices.json", valueKeys: ["Price (USD per gallon)"] },
  "iPhone": { file: "iPhone_Prices.json", valueKeys: ["Price (USD)"] },
  "RAV4": { file: "Car_Prices.json", valueKeys: ["Price (USD)"] },
  "10Y Treasury (%)": { file: "Interest_Rates.json", valueKeys: ["10-Year Treasury Rate (%)", "Rate (%)"] },
  "S&P 500": { file: "Stock_Market.json", valueKeys: ["S&P 500 Index", "Close"] }
};
const POLICY_FILE = "Policy_Events.json";

// state
let rawSeries = {};       // { seriesName: [{date, value}] }
let mergedDates = [];     // sorted dates across all series
let policyEvents = [];    // [{date, title, type, agency, url}]
let selected = new Set(Object.keys(SERIES));
let percentMode = false;
let zscoreMode = false;
let smoothMode = false;
let smoothN = 7;
let anchor = "S&P 500";
let currentLag = 0;
let dateRange = { start: null, end: null };
let typeFilter = new Set();
let agencyFilterText = "";

// utility
const toNum = (x) => (x === null || x === undefined || x === "" ? null : Number(x));
function uniq(arr) { return Array.from(new Set(arr)); }

function rollingAverage(values, n) {
  const out = Array(values.length).fill(null);
  let sum = 0, cnt = 0;
  for (let i = 0; i < values.length; i++) {
    if (values[i] != null) { sum += values[i]; cnt++; }
    if (i >= n) {
      if (values[i-n] != null) { sum -= values[i-n]; cnt--; }
    }
    out[i] = cnt > 0 ? sum / cnt : null;
  }
  return out;
}

function zscore(values) {
  const present = values.filter(v => v != null);
  const mean = present.reduce((a,b)=>a+b,0)/ (present.length || 1);
  const sd = Math.sqrt(present.reduce((a,b)=>a + (b-mean)*(b-mean),0) / (Math.max(1, present.length - 1)));
  return values.map(v => v == null ? null : (sd === 0 ? 0 : (v - mean) / sd));
}

function pctFromFirst(values) {
  const base = values.find(v => v != null);
  return values.map(v => v == null ? null : (base ? (v / base) * 100 : null));
}

function shift(values, days) {
  const out = Array(values.length).fill(null);
  const k = Math.trunc(days);
  if (k === 0) return values.slice();
  for (let i = 0; i < values.length; i++) {
    const j = i + k;
    if (j >= 0 && j < values.length) out[j] = values[i];
  }
  return out;
}

function pearson(x, y) {
  const pairs = [];
  for (let i = 0; i < x.length; i++) {
    if (x[i] != null && y[i] != null) pairs.push([x[i], y[i]]);
  }
  const n = pairs.length;
  if (n < 3) return { r: NaN, n: n };
  const sx = pairs.reduce((a,p)=>a+p[0],0);
  const sy = pairs.reduce((a,p)=>a+p[1],0);
  const sxx = pairs.reduce((a,p)=>a+p[0]*p[0],0);
  const syy = pairs.reduce((a,p)=>a+p[1]*p[1],0);
  const sxy = pairs.reduce((a,p)=>a+p[0]*p[1],0);
  const num = n*sxy - sx*sy;
  const den = Math.sqrt((n*sxx - sx*sx)*(n*syy - sy*sy));
  const r = den === 0 ? NaN : num/den;
  return { r, n };
}

async function fetchJSON(rel) {
  const url = `${PATH_PREFIX}${rel}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status}`);
  return res.json();
}

async function loadAll() {
  for (const [name, cfg] of Object.entries(SERIES)) {
    const arr = await fetchJSON(cfg.file);
    const points = [];
    for (const row of arr) {
      const date = row.Date;
      let val = null;
      for (const key of cfg.valueKeys) {
        if (row[key] !== undefined) { val = toNum(row[key]); break; }
      }
      if (date) points.push({ date, value: val });
    }
    points.sort((a,b)=> new Date(a.date) - new Date(b.date));
    rawSeries[name] = points;
  }

  mergedDates = uniq(
    Object.values(rawSeries).flatMap(s => s.map(p => p.date))
  ).sort((a,b)=> new Date(a) - new Date(b));

  const events = await fetchJSON(POLICY_FILE);
  policyEvents = events.map(e => ({
    date: e.Date,
    title: e.Title || e.Type,
    type: e.Type || "",
    agency: e.Agency || "",
    url: e["Source URL"] || e.Source || ""
  })).filter(e => e.date);

  initUI();
  renderAll();
}

function initUI() {
  const chips = document.getElementById("seriesChips");
  chips.innerHTML = "";
  Object.keys(SERIES).forEach(name => {
    const div = document.createElement("button");
    div.className = "chip " + (selected.has(name) ? "chip-active" : "");
    div.textContent = name;
    div.onclick = () => {
      if (selected.has(name)) selected.delete(name); else selected.add(name);
      renderAll();
    };
    chips.appendChild(div);
  });

  const percentToggle = document.getElementById("percentToggle");
  const zToggle = document.getElementById("zscoreToggle");
  const sToggle = document.getElementById("smoothToggle");
  const sWin = document.getElementById("smoothWindow");
  percentToggle.onchange = () => { percentMode = percentToggle.checked; renderAll(); };
  zToggle.onchange = () => { zscoreMode = zToggle.checked; renderAll(); };
  sToggle.onchange = () => { smoothMode = sToggle.checked; renderAll(); };
  sWin.onchange = () => { smoothN = Math.max(2, Number(sWin.value||7)); renderAll(); };

  const sd = document.getElementById("startDate");
  const ed = document.getElementById("endDate");
  if (mergedDates.length) {
    sd.value = mergedDates[0];
    ed.value = mergedDates[mergedDates.length - 1];
    dateRange.start = sd.value; dateRange.end = ed.value;
  }
  document.getElementById("applyRange").onclick = () => {
    dateRange.start = sd.value || null;
    dateRange.end = ed.value || null;
    renderAll();
  };

  const typeSel = document.getElementById("typeFilter");
  const types = uniq(policyEvents.map(e=>e.type)).sort();
  typeSel.innerHTML = types.map(t => `<option value="${t}">${t}</option>`).join("");
  document.getElementById("applyEventFilters").onclick = () => {
    typeFilter = new Set(Array.from(typeSel.selectedOptions).map(o=>o.value));
    agencyFilterText = (document.getElementById("agencyFilter").value || "").toLowerCase();
    renderAll();
  };

  const wrap = document.getElementById("anchorSelectWrap");
  wrap.innerHTML = "";
  const sel = document.createElement("select");
  sel.className = "border rounded px-2 py-1 text-sm";
  for (const k of Object.keys(SERIES)) {
    const opt = document.createElement("option");
    opt.value = k; opt.textContent = k; if (k === anchor) opt.selected = true;
    sel.appendChild(opt);
  }
  sel.onchange = () => { anchor = sel.value; renderAll(); };
  wrap.appendChild(sel);

  document.getElementById("updateLag").onclick = () => {
    currentLag = Number(document.getElementById("lagDays").value || 0);
    renderAll();
  };
}

function buildFrame() {
  const dates = mergedDates.filter(d => {
    if (dateRange.start && d < dateRange.start) return false;
    if (dateRange.end && d > dateRange.end) return false;
    return true;
  });
  const frame = { dates, series: {} };
  for (const name of Object.keys(SERIES)) {
    const map = new Map(rawSeries[name].map(p => [p.date, p.value]));
    frame.series[name] = dates.map(d => (map.has(d) ? map.get(d) : null));
    if (smoothMode) frame.series[name] = rollingAverage(frame.series[name], smoothN);
  }
  if (percentMode) {
    for (const name of Object.keys(frame.series)) frame.series[name] = pctFromFirst(frame.series[name]);
  }
  if (zscoreMode) {
    for (const name of Object.keys(frame.series)) frame.series[name] = zscore(frame.series[name]);
  }
  return frame;
}

let chartInstance = null;

function drawEventsOverlay(ctx, xScale, chartArea, filteredEvents) {
  ctx.save();
  ctx.strokeStyle = "rgba(0,0,0,0.25)";
  filteredEvents.forEach(ev => {
    const x = xScale.getPixelForValue(ev.date);
    if (x >= chartArea.left && x <= chartArea.right) {
      ctx.beginPath();
      ctx.moveTo(x, chartArea.top);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();
    }
  });
  ctx.restore();
}

function renderChart(frame, filteredEvents) {
  const ctx = document.getElementById("chart").getContext("2d");
  const labels = frame.dates;
  const visibleSeries = Array.from(selected);

  const palette = [
    "#0ea5e9","#ef4444","#10b981","#f59e0b","#8b5cf6","#14b8a6","#f97316","#22c55e"
  ];

  const datasets = visibleSeries.map((name, i) => ({
    label: name,
    data: (name === anchor ? shift(frame.series[name], currentLag) : frame.series[name]),
    borderColor: palette[i % palette.length],
    backgroundColor: "transparent",
    borderWidth: 2,
    pointRadius: 0,
    spanGaps: true,
    tension: 0.15
  }));

  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" },
        tooltip: {
          mode: "index",
          intersect: false,
          callbacks: {
            title: (items) => items[0].label,
          }
        }
      },
      scales: {
        x: { ticks: { maxRotation: 0, autoSkip: true } },
        y: { beginAtZero: false }
      },
      interaction: { mode: "index", intersect: false },
      events: ["mousemove","click","mouseout","touchstart","touchmove","touchend"]
    },
    plugins: [{
      id: "events-overlay",
      afterDatasetsDraw(chart) {
        const { ctx, chartArea, scales } = chart;
        drawEventsOverlay(ctx, scales.x, chartArea, filteredEvents);
      }
    }]
  });
}

function renderEventsList(filteredEvents) {
  const list = document.getElementById("eventsList");
  list.innerHTML = "";
  filteredEvents.slice(0, 250).forEach(ev => {
    const a = document.createElement("a");
    a.href = ev.url || "#";
    a.target = "_blank";
    a.className = "block py-1 border-b border-slate-100 hover:bg-slate-50";
    a.innerHTML = `<span class="text-xs text-slate-500 mr-2">${ev.date}</span> <span class="font-medium">${ev.title}</span> <span class="text-xs text-slate-500 ml-2">${ev.type}</span>`;
    list.appendChild(a);
  });
  if (filteredEvents.length > 250) {
    const more = document.createElement("div");
    more.className = "text-xs text-slate-500 mt-1";
    more.textContent = `(+${filteredEvents.length - 250} more hidden)`;
    list.appendChild(more);
  }
}

function renderCorrelation(frame) {
  const tbody = document.querySelector("#corrTable tbody");
  tbody.innerHTML = "";
  const vis = Array.from(selected);
  if (!vis.includes(anchor)) vis.unshift(anchor);

  const anchorVals = shift(frame.series[anchor], currentLag);
  for (const name of vis) {
    if (name === anchor) continue;
    const { r, n } = pearson(anchorVals, frame.series[name]);
    const tr = document.createElement("tr");
    tr.innerHTML = `<td class="py-1 pr-2">${name}</td><td class="py-1 pr-2 font-mono">${isNaN(r) ? "—" : r.toFixed(3)}</td><td class="py-1">${n}</td>`;
    tbody.appendChild(tr);
  }
}

function filterEvents() {
  return policyEvents.filter(ev => {
    if (dateRange.start && ev.date < dateRange.start) return false;
    if (dateRange.end && ev.date > dateRange.end) return false;
    if (typeFilter.size && !typeFilter.has(ev.type)) return false;
    if (agencyFilterText && !ev.agency.toLowerCase().includes(agencyFilterText)) return false;
    return true;
  });
}

function renderAll() {
  const frame = buildFrame();
  const evs = filterEvents();
  renderChart(frame, evs);
  renderEventsList(evs);
  renderCorrelation(frame);
}

// kick off
loadAll().catch(err => {
  console.error(err);
  alert("Failed to load data. Check console for details.");
});
