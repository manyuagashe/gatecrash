const API = "http://localhost:8000";
const CHAPEL_HILL = [35.9097, -79.0506];
const BENCHMARK_MAX = 5 ;  // mirrors backend/api.py

const state = {
  depot: null,
  stops: [],
  classicalLayer: null,
  quantumLayer: null,
  view: "both",
};

const map = L.map("map", { zoomControl: true, attributionControl: false })
  .setView(CHAPEL_HILL, 14);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(map);

const pinIcon = (isDepot) => L.divIcon({
  className: "",
  html: `<div class="pin ${isDepot ? "depot" : ""}"></div>`,
  iconSize: isDepot ? [18, 18] : [14, 14],
  iconAnchor: isDepot ? [9, 9] : [7, 7],
});

function placeDepot(coord, name = "depot") {
  const m = L.marker(coord, { icon: pinIcon(true), draggable: true }).addTo(map).bindTooltip(name);
  m.on("dragend", (e) => (state.depot.coord = [e.target.getLatLng().lat, e.target.getLatLng().lng]));
  state.depot = { coord, marker: m };
}

function addStop(coord, name) {
  const m = L.marker(coord, { icon: pinIcon(false), draggable: true })
    .addTo(map).bindTooltip(name || `stop ${state.stops.length + 1}`);
  const entry = { coord, marker: m };
  m.on("dragend", (e) => (entry.coord = [e.target.getLatLng().lat, e.target.getLatLng().lng]));
  m.on("click", (e) => { if (e.originalEvent.shiftKey) removeStop(entry); });
  state.stops.push(entry);
  updateCounters();
}

function removeStop(entry) {
  map.removeLayer(entry.marker);
  state.stops = state.stops.filter((s) => s !== entry);
  updateCounters();
  clearRoutes();
}

map.on("click", (e) => {
  if (e.originalEvent.shiftKey) return;
  addStop([e.latlng.lat, e.latlng.lng]);
});

// live counters: "stops" = user pins. "benchmark n" = what will actually run.
function updateCounters() {
  document.getElementById("stop-count").textContent = state.stops.length;
  // benchmark n = min(1 + stops, BENCHMARK_MAX) — depot + as many stops as we'll fit
  const nPreview = Math.min(1 + state.stops.length, BENCHMARK_MAX);
  document.getElementById("bench-n").textContent = state.stops.length === 0 ? "—" : nPreview;
  document.getElementById("qubit-count").textContent = state.stops.length === 0 ? "—" : (nPreview - 1) ** 2;
}

const logEl = document.getElementById("log");
function logLine(text, cls = "") {
  const ts = new Date().toLocaleTimeString([], { hour12: false });
  const line = document.createElement("div");
  line.className = cls;
  line.innerHTML = `<span class="dim">[${ts}]</span>  ${text}`;
  logEl.appendChild(line);
  logEl.scrollTop = logEl.scrollHeight;
}
function logClear() { logEl.innerHTML = ""; }

function setStatus(text, active = false) {
  const el = document.getElementById("status");
  el.textContent = text;
  el.classList.toggle("is-active", active);
}
function setLoading(on) {
  const b = document.getElementById("run-btn");
  b.classList.toggle("is-loading", on);
  b.disabled = on;
}

function clearRoutes() {
  if (state.classicalLayer) map.removeLayer(state.classicalLayer);
  if (state.quantumLayer) map.removeLayer(state.quantumLayer);
  state.classicalLayer = null;
  state.quantumLayer = null;
  document.getElementById("trim-note").classList.add("hidden");
  ["c-dist","c-co2","c-ms","q-dist","q-co2","q-ms","d-dist","d-co2"].forEach(id => {
    document.getElementById(id).textContent = "—";
  });
}

function animateNum(el, to, decimals = 3, ms = 800) {
  const from = parseFloat(el.textContent) || 0;
  const t0 = performance.now();
  (function tick(now) {
    const k = Math.min(1, (now - t0) / ms);
    const eased = 1 - Math.pow(1 - k, 3);
    el.textContent = (from + (to - from) * eased).toFixed(decimals);
    if (k < 1) requestAnimationFrame(tick);
  })(performance.now());
}

function drawRoute(edges, coords, color, dashed) {
  const group = L.layerGroup().addTo(map);
  edges.forEach(([i, j], k) => {
    setTimeout(() => {
      L.polyline([coords[i], coords[j]], {
        color, weight: 4, opacity: 0.92,
        dashArray: dashed ? "6 6" : null,
        lineCap: "round", lineJoin: "round",
      }).addTo(group);
    }, k * 200);
  });
  return group;
}

async function runBenchmark() {
  if (state.stops.length < 2) {
    setStatus("add at least 2 stops");
    return;
  }
  clearRoutes();
  logClear();
  setLoading(true);

  const stages = [
    "building distance matrix",
    "formulating QUBO",
    "submitting QAOA circuit",
    "optimizing γ, β with COBYLA",
    "decoding bitstring",
  ];
  let stageIdx = 0;
  const startTime = Date.now();

  logLine(stages[0] + "…", "orange");
  setStatus(stages[0] + "…", true);

  // advance the status/log one step at a time; stop advancing at the last stage,
  // then just tick elapsed-time so the UI shows we're still alive.
  const timer = setInterval(() => {
    const elapsed = Math.round((Date.now() - startTime) / 1000);
    const next = Math.min(stageIdx + 1, stages.length - 1);
    if (next !== stageIdx) {
      stageIdx = next;
      logLine(stages[stageIdx] + "…", stageIdx === stages.length - 1 ? "" : "");
      setStatus(stages[stageIdx] + "…", true);
    } else {
      setStatus(`${stages[stageIdx]}… ${elapsed}s elapsed`, true);
    }
  }, 900);

  const coords = [state.depot.coord, ...state.stops.map((x) => x.coord)];

  try {
    const res = await fetch(`${API}/optimize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ coords, num_vehicles: 1, qaoa_reps: 1 }),
    });
    const data = await res.json();
    clearInterval(timer);
    renderResults(data, coords);
  } catch (err) {
    clearInterval(timer);
    setStatus(`error: ${err.message}`);
    logLine(`ERROR: ${err.message}`, "orange");
  } finally {
    setLoading(false);
  }
}

function renderResults(data, fullCoords) {
  const p = data.problem;
  document.getElementById("stop-count").textContent = state.stops.length;
  document.getElementById("bench-n").textContent = p.n;
  document.getElementById("qubit-count").textContent = p.qubits;

  if (p.trimmed_from) {
    document.getElementById("trim-from").textContent = p.trimmed_from;
    document.getElementById("trim-to").textContent = p.n;
    document.getElementById("trim-note").classList.remove("hidden");
    logLine(`trim ${p.trimmed_from} → ${p.n} coords (benchmark parity)`, "orange");
  }

  logLine(`n = ${p.n} · qubits = ${p.qubits}`);
  (data.run_log || []).forEach(l => logLine(l, "dim"));
  logLine(`classical edges: ${JSON.stringify(data.classical.edges)}`, "dim");
  logLine(`quantum edges:   ${JSON.stringify(data.quantum.edges)}`, "dim");
  logLine(`DONE · classical ${data.classical.compute_ms}ms · quantum ${Math.round(data.quantum.compute_ms)}ms`, "orange");

  animateNum(document.getElementById("c-dist"), data.classical.distance_km, 3);
  animateNum(document.getElementById("q-dist"), data.quantum.distance_km, 3);
  document.getElementById("c-co2").textContent = data.classical.co2_kg.toFixed(3);
  document.getElementById("q-co2").textContent = data.quantum.co2_kg.toFixed(3);
  document.getElementById("c-ms").textContent = Math.round(data.classical.compute_ms);
  document.getElementById("q-ms").textContent = Math.round(data.quantum.compute_ms);

  const sv = data.savings;
  const dDist = document.getElementById("d-dist");
  const dCo2  = document.getElementById("d-co2");
  const sign  = sv.distance_saved_km >= 0 ? "−" : "+";
  dDist.textContent = `${sign}${Math.abs(sv.distance_saved_km).toFixed(3)}`;
  dCo2.textContent  = `${sign}${Math.abs(sv.co2_saved_kg).toFixed(3)}`;
  dDist.style.color = sv.distance_saved_km > 0 ? "var(--success)" : "var(--ink-soft)";
  dCo2.style.color  = dDist.style.color;

  // both solvers ran on the same coord subset
  const benchCoords = p.coord_indices.map(i => fullCoords[i]);
  state.classicalLayer = drawRoute(data.classical.edges, benchCoords, cssVar("--classical"), true);
  state.quantumLayer   = drawRoute(data.quantum.edges,   benchCoords, cssVar("--orange"), false);
  applyView();

  setStatus(`done · ${p.qubits} qubits · parity ✓`, false);
}

function cssVar(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }

function applyView() {
  if (!state.classicalLayer || !state.quantumLayer) return;
  const v = state.view;
  const showC = v === "both" || v === "classical";
  const showQ = v === "both" || v === "quantum";
  showC ? state.classicalLayer.addTo(map) : map.removeLayer(state.classicalLayer);
  showQ ? state.quantumLayer.addTo(map)   : map.removeLayer(state.quantumLayer);
}

document.querySelectorAll(".tab").forEach(t =>
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(x => x.classList.remove("is-active"));
    t.classList.add("is-active");
    state.view = t.dataset.view;
    applyView();
  })
);

document.getElementById("run-btn").addEventListener("click", runBenchmark);

async function loadDemo() {
  try {
    const res = await fetch(`${API}/demo`);
    const d = await res.json();
    placeDepot(d.depot.coord, d.depot.name);
    d.stops.forEach((s) => addStop(s.coord, s.name));
    map.setView(d.depot.coord, 14);
  } catch {
    placeDepot(CHAPEL_HILL, "depot");
  }
  logLine("gatecrash instrument ready", "orange");
  logLine(`benchmark cap: n=${BENCHMARK_MAX} · ${(BENCHMARK_MAX - 1) ** 2} qubits`, "dim");
}
loadDemo();

// ---------- scaling chart — honest formulas, log scale ----------
// |routes| = (n-1)!/2   — Hamiltonian cycles on K_n
// qubits   = n(n-1)     — exact QUBO variable count from backend/vrp.py

function fact(n) { let r = 1; for (let i = 2; i <= n; i++) r *= i; return r; }

const nVals = [4, 5, 6, 8, 10, 12, 14, 16, 18, 20];
const solutionSpace = nVals.map(n => fact(n - 1) / 2);
const quboQubits    = nVals.map(n => (n - 1) ** 2);

const ctx = document.getElementById("scaling-chart").getContext("2d");
const classicalCol = cssVar("--classical");
const orangeCol = cssVar("--orange");
const inkSoft = cssVar("--ink-soft");
const ruleCol = cssVar("--rule");

new Chart(ctx, {
  type: "line",
  data: {
    labels: nVals,
    datasets: [
      {
        label: "|routes|  =  (n−1)! / 2",
        data: solutionSpace,
        borderColor: classicalCol, backgroundColor: "transparent",
        borderWidth: 2, borderDash: [6, 6], tension: 0.2, pointRadius: 3,
      },
      {
        label: "qubits  =  (n−1)²",
        data: quboQubits,
        borderColor: orangeCol, backgroundColor: "transparent",
        borderWidth: 2.5, tension: 0.2, pointRadius: 3,
      },
    ],
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { labels: { font: { family: "IBM Plex Mono", size: 12 }, color: inkSoft } },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const v = ctx.parsed.y;
            const f = v >= 1e6 ? v.toExponential(2) : v.toLocaleString();
            return `${ctx.dataset.label}:  ${f}`;
          },
        },
      },
    },
    scales: {
      x: {
        title: { display: true, text: "n (stops + depot)", color: inkSoft, font: { family: "IBM Plex Mono" } },
        grid: { color: ruleCol },
        ticks: { color: inkSoft, font: { family: "IBM Plex Mono" } },
      },
      y: {
        type: "logarithmic",
        title: { display: true, text: "count (log scale)", color: inkSoft, font: { family: "IBM Plex Mono" } },
        grid: { color: ruleCol },
        ticks: {
          color: inkSoft,
          font: { family: "IBM Plex Mono" },
          callback: (v) => {
            if (v === 1) return "1";
            const e = Math.log10(v);
            if (Math.abs(e - Math.round(e)) > 0.01) return "";
            return `10^${Math.round(e)}`;
          },
        },
      },
    },
  },
});
