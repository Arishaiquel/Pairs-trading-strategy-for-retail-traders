const el = (id) => document.getElementById(id);

const ids = [
  "ticker_a", "ticker_b", "start_date", "end_date", "lookback", "entry_z", "exit_z", "stop_z",
  "cost_bps", "slippage_bps", "capital", "use_rolling_beta"
];

const charts = {};

function setStatus(text, isError = false) {
  const status = el("status");
  status.textContent = text;
  status.style.color = isError ? "#be123c" : "#5f6966";
}

function num(v, pct = false) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-";
  return pct ? `${(v * 100).toFixed(2)}%` : Number(v).toFixed(4);
}

function collectPayload() {
  return {
    ticker_a: el("ticker_a").value.trim().toUpperCase(),
    ticker_b: el("ticker_b").value.trim().toUpperCase(),
    start_date: el("start_date").value,
    end_date: el("end_date").value,
    lookback: Number(el("lookback").value),
    entry_z: Number(el("entry_z").value),
    exit_z: Number(el("exit_z").value),
    stop_z: Number(el("stop_z").value),
    cost_bps: Number(el("cost_bps").value),
    slippage_bps: Number(el("slippage_bps").value),
    capital: Number(el("capital").value),
    use_rolling_beta: el("use_rolling_beta").checked,
  };
}

function renderMetrics(metrics, pairStats) {
  const entries = [
    ["Correlation", num(pairStats.correlation)],
    ["Cointegration p-val", num(pairStats.cointegration_pvalue)],
    ["ADF p-val", num(pairStats.spread_adf_pvalue)],
    ["Half-life (days)", num(pairStats.half_life_days)],
    ["Total Return", num(metrics.total_return, true)],
    ["Annual Return", num(metrics.annual_return, true)],
    ["Annual Volatility", num(metrics.annual_volatility, true)],
    ["Sharpe", num(metrics.sharpe_ratio)],
    ["Max Drawdown", num(metrics.max_drawdown, true)],
    ["Win Rate", num(metrics.win_rate, true)],
    ["Trades", num(metrics.num_trades)],
    ["Cost Drag", num(metrics.cost_drag, true)],
  ];

  el("metrics").innerHTML = entries.map(([k, v]) => `
    <article class="metric">
      <div class="k">${k}</div>
      <div class="v">${v}</div>
    </article>
  `).join("");
}

function createOrUpdateChart(key, canvasId, config) {
  if (charts[key]) {
    charts[key].destroy();
  }
  const ctx = el(canvasId).getContext("2d");
  charts[key] = new Chart(ctx, config);
}

function renderCharts(ts, payload) {
  const labels = ts.dates;
  createOrUpdateChart("price", "priceChart", {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: payload.ticker_a, data: ts.price_a, borderColor: "#0f766e", pointRadius: 0 },
        { label: payload.ticker_b, data: ts.price_b, borderColor: "#be123c", pointRadius: 0 },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });

  createOrUpdateChart("spread", "spreadChart", {
    type: "line",
    data: {
      labels,
      datasets: [{ label: "Spread", data: ts.spread, borderColor: "#1f2524", pointRadius: 0 }],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });

  createOrUpdateChart("z", "zChart", {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Z-Score", data: ts.zscore, borderColor: "#0ea5e9", pointRadius: 0 },
        { label: "+Entry", data: labels.map(() => payload.entry_z), borderColor: "#9ca3af", borderDash: [6, 4], pointRadius: 0 },
        { label: "-Entry", data: labels.map(() => -payload.entry_z), borderColor: "#9ca3af", borderDash: [6, 4], pointRadius: 0 },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });

  createOrUpdateChart("equity", "equityChart", {
    type: "line",
    data: {
      labels,
      datasets: [{ label: "Equity", data: ts.equity, borderColor: "#7c3aed", pointRadius: 0 }],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });
}

function renderTrades(trades) {
  const body = el("tradeBody");
  if (!trades.length) {
    body.innerHTML = `<tr><td colspan="7">No closed trades</td></tr>`;
    return;
  }
  body.innerHTML = trades.map((t) => `
    <tr>
      <td>${t.side}</td>
      <td>${t.entry_date}</td>
      <td>${num(t.entry_z)}</td>
      <td>${t.exit_date}</td>
      <td>${num(t.exit_z)}</td>
      <td>${t.exit_reason}</td>
      <td>${num(t.trade_return, true)}</td>
    </tr>
  `).join("");
}

async function loadDefaults() {
  const resp = await fetch("/api/defaults");
  const data = await resp.json();
  const pairsSelect = el("examplePairs");
  pairsSelect.innerHTML = data.example_pairs.map(([a, b]) => `<option value="${a},${b}">${a} / ${b}</option>`).join("");

  pairsSelect.addEventListener("change", () => {
    const [a, b] = pairsSelect.value.split(",");
    el("ticker_a").value = a;
    el("ticker_b").value = b;
  });
}

async function runBacktest() {
  const payload = collectPayload();
  setStatus("Running backtest...");

  try {
    const resp = await fetch("/api/backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "Backtest request failed");
    }

    renderMetrics(data.metrics, data.pair_stats);
    renderCharts(data.timeseries, payload);
    renderTrades(data.trades);
    setStatus(`Done. ${payload.ticker_a}/${payload.ticker_b} backtest completed.`);
  } catch (err) {
    setStatus(err.message, true);
  }
}

function renderScan(rows) {
  const body = el("scanBody");
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="7">No scan results</td></tr>`;
    return;
  }
  body.innerHTML = rows.map((r) => `
    <tr>
      <td>${r.pair}</td>
      <td>${num(r.correlation)}</td>
      <td>${num(r.cointegration_pvalue)}</td>
      <td>${num(r.half_life_days)}</td>
      <td>${num(r.annual_return, true)}</td>
      <td>${num(r.sharpe_ratio)}</td>
      <td>${num(r.max_drawdown, true)}</td>
    </tr>
  `).join("");
}

async function scanPairs() {
  const payload = collectPayload();
  setStatus("Scanning default pairs...");
  try {
    const resp = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "Scan failed");
    }
    renderScan(data.results);
    setStatus(`Scan done. Ranked ${data.results.length} pairs.`);
  } catch (err) {
    setStatus(err.message, true);
  }
}

el("runBtn").addEventListener("click", runBacktest);
el("scanBtn").addEventListener("click", scanPairs);
loadDefaults();
