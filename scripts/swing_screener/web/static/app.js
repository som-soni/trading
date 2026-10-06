"use strict";
const $view = document.getElementById("view");
const LC = LightweightCharts;
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};
const api = async (url, init) => {
  const r = await fetch(url, init);
  if (!r.ok) throw new Error(`${r.status} ${(await r.json().catch(() => ({}))).detail || r.statusText}`);
  return r.json();
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const el = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; };
const LOADING = `<div class="loading"><span class="spin"></span>Loading…</div>`;
let cleanup = () => {};
let navSeq = 0;  // bumps on every route change so a slow page load can't paint over a newer page

// ------------------------------------------------------------- formatting

function fmt(v) {
  if (v === null || v === undefined || v === "") return "";
  if (v === true) return "✓";
  if (v === false) return "–";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return v.toLocaleString();
    return Math.abs(v) < 0.01 && v !== 0 ? v.toPrecision(3) : v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(v);
}
const signed = (v, d = 2) => (v > 0 ? "+" : "") + v.toFixed(d);
const decisionClass = (d) => /^TRADE/i.test(d) ? "trade" : /^WATCH/i.test(d) ? "watch" : /^AVOID/i.test(d) ? "avoid" : "";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** "2026-10-03_171703" / "2026-10-03" / ISO timestamp -> "3 Oct 2026 · 17:17" */
function prettyDate(s) {
  const m = String(s ?? "").match(/^(\d{4})-(\d{2})-(\d{2})(?:[_T ](\d{2}):?(\d{2}))?/);
  if (!m) return String(s ?? "");
  return `${+m[3]} ${MONTHS[+m[2] - 1]} ${m[1]}${m[4] ? ` · ${m[4]}:${m[5]}` : ""}`;
}
const LABELS = {
  symbol: "Symbol", sector: "Sector", decision: "Decision", price: "Price", entry: "Entry", stop: "Stop",
  risk_pct: "Risk %", target_r: "Target R", setup_quality: "Quality", strategy_setup: "Setup", pattern: "Pattern",
  rs_vs_benchmark: "RS vs index", rank: "#", rs: "RS", rs_vs_sector: "RS vs sector", rsi: "RSI", adx: "ADX", earnings_in: "Earnings in (d)",
  wait_for: "Wait for", reason: "Reason", entry_date: "Entry date", entry_price: "Entry price", exit_date: "Exit date",
  exit_price: "Exit price", exit_reason: "Exit", r_multiple: "R", holding_days: "Days held", pnl: "P&L",
  initial_stop: "Initial stop", drawdown_pct: "Drawdown %", positions_open: "Open positions",
  "cagr %": "CAGR %", "excess cagr %": "Excess CAGR %", "max dd %": "Max DD %", market: "Market", strategy: "Strategy", run: "Run",
  last: "Last", "chg %": "Chg %", quality: "Quality", f: "F", "roic / roe": "ROIC / ROE", "rev growth": "Rev growth", "eps growth": "EPS growth",
  "op margin": "Op margin", "fcf conv": "FCF conv", "net debt/ebitda": "Net debt/EBITDA", "p/e": "P/E", "p/e vs own": "P/E vs own", "fcf yield": "FCF yield",
  peg: "PEG", "off 52w high": "Off 52w high", "vs 200d": "vs 200D", value: "Value", zone: "Zone", "buy below": "Buy below", signals: "Signals", name: "Company", source: "Source", "to entry %": "To entry %", note: "Note", added: "Added", "target R": "Target R",
};
const label = (c) => LABELS[c] ?? String(c).replace(/_/g, " ").replace(/^\w/, (x) => x.toUpperCase());
// columns where the sign is the story: colour them green / red
const SIGNED_COL = /pnl|return|r_multiple|^r$|cagr|excess|sharpe|xirr|change|^chg|^rs_|pct_vs/i;

function toast(msg, kind = "", action = null) {
  const t = el(`<div class="toast ${kind}"><span>${esc(msg)}</span>${action ? `<button class="ghost">${esc(action.label)}</button>` : ""}</div>`);
  if (action) t.querySelector("button").onclick = () => { t.remove(); action.fn(); };
  document.getElementById("toasts").append(t);
  const life = action ? 6000 : 2600;  // leave time to hit Undo
  setTimeout(() => t.classList.add("out"), life);
  setTimeout(() => t.remove(), life + 400);
}

// ---------------------------------------------------------------- tables

/** Sortable, filterable, exportable table.
 *  opts: {rowClick(row, visibleRows), limit, name, sort: [col, dir], hidden: [cols], format: {col: fn},
 *         actions: [{key, title, icon, fn(row)}], rowClass(row), tags: {col: value -> css class}, signed: [cols]} */
function dataTable(host, columns, rows, opts = {}) {
  const decCol = columns.indexOf("decision");
  const hidden = new Set((opts.hidden || []).map((c) => columns.indexOf(c)));
  let sortCol = opts.sort ? columns.indexOf(opts.sort[0]) : -1, sortDir = opts.sort ? opts.sort[1] : 1;
  let filter = "", limit = opts.limit || 300, visible = [];
  host.innerHTML = `<div class="tbar"><label class="filter"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg>
      <input placeholder="Filter rows" spellcheck="false"></label><span class="muted count"></span><span class="spacer"></span>
      <button class="ghost csv" title="Download the rows shown as CSV">Export CSV</button></div>
    <div class="tablewrap"><table class="data"><thead></thead><tbody></tbody></table></div>
    <div class="tfoot"><button class="more" hidden>Show more</button></div>`;
  const thead = host.querySelector("thead"), tbody = host.querySelector("tbody");
  const more = host.querySelector(".more"), count = host.querySelector(".count");
  const cols = columns.map((c, i) => i).filter((i) => !hidden.has(i));
  const numeric = columns.map((_, i) => rows.some((r) => typeof r[i] === "number"));
  const fmtFor = columns.map((c) => (opts.format && opts.format[c]) || fmt);
  const header = () => {
    thead.innerHTML = "<tr>" + cols.map((i) => `<th data-i="${i}" class="${numeric[i] ? "num" : ""}" title="${esc(columns[i])}">${esc(label(columns[i]))}` +
      `<span class="arrow">${i === sortCol ? (sortDir > 0 ? "▲" : "▼") : ""}</span></th>`).join("") + (opts.actions ? "<th></th>" : "") + "</tr>";
  };
  function draw() {
    const f = filter.toLowerCase();
    visible = f ? rows.filter((row) => row.some((v) => String(v ?? "").toLowerCase().includes(f))) : rows.slice();
    if (sortCol >= 0) visible.sort((a, b) => {
      const x = a[sortCol], y = b[sortCol];
      if (x == null || x === "") return 1; if (y == null || y === "") return -1;
      return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * sortDir;
    });
    count.textContent = visible.length === rows.length ? `${rows.length.toLocaleString()} rows` : `${visible.length.toLocaleString()} of ${rows.length.toLocaleString()} rows`;
    if (!visible.length) { tbody.innerHTML = `<tr><td colspan="${cols.length + (opts.actions ? 1 : 0)}" class="none">${rows.length ? "No rows match the filter." : "No rows."}</td></tr>`; more.hidden = true; return; }
    tbody.innerHTML = visible.slice(0, limit).map((row, ri) => `<tr class="${opts.rowClick ? "click" : ""} ${opts.rowClass ? opts.rowClass(row) : ""}" data-r="${ri}">` +
      cols.map((i) => {
        const v = row[i];
        if (i === decCol && v) return `<td><span class="tag ${decisionClass(v)}">${esc(v)}</span></td>`;
        if (opts.tags && opts.tags[columns[i]] && v) return `<td><span class="tag ${opts.tags[columns[i]](v)}">${esc(v)}</span></td>`;
        let cls = typeof v === "number" ? "num" : "";
        if (typeof v === "number" && (opts.inverse || []).includes(columns[i])) cls += v < 0 ? " pos" : v > 0 ? " neg" : "";  // lower is better
        else if (typeof v === "number" && (SIGNED_COL.test(columns[i]) || (opts.signed || []).includes(columns[i]))) cls += v < 0 ? " neg" : v > 0 ? " pos" : "";
        if (typeof v === "boolean") cls += v ? " yes" : " no";
        return `<td class="${cls}"${typeof v === "string" && v.length > 40 ? ` title="${esc(v)}"` : ""}>${esc(fmtFor[i](v))}</td>`;
      }).join("") + (opts.actions ? `<td class="acts">${opts.actions.map((a) => `<button class="ghost icon" data-act="${a.key}" title="${esc(a.title)}">${a.icon}</button>`).join("")}</td>` : "") + "</tr>").join("");
    more.hidden = visible.length <= limit;
    more.textContent = `Show ${Math.min(500, visible.length - limit).toLocaleString()} more`;
  }
  thead.onclick = (e) => {
    const th = e.target.closest("th"); if (!th) return;
    const i = +th.dataset.i;
    sortDir = sortCol === i ? -sortDir : numeric[i] ? -1 : 1; sortCol = i;  // numbers sort high-first on first click
    header(); draw();
  };
  tbody.onclick = (e) => {
    const tr = e.target.closest("tr[data-r]"); if (!tr) return;
    const act = e.target.closest("[data-act]");
    if (act) { opts.actions.find((a) => a.key === act.dataset.act).fn(visible[+tr.dataset.r]); return; }
    if (opts.rowClick) opts.rowClick(visible[+tr.dataset.r], visible);
  };
  host.querySelector("input").oninput = (e) => { filter = e.target.value; draw(); };
  more.onclick = () => { limit += 500; draw(); };
  host.querySelector(".csv").onclick = () => {
    const q = (v) => (v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
    const csv = [columns.map(q).join(","), ...visible.map((r) => r.map(q).join(","))].join("\n");
    const a = el(`<a download="${esc(opts.name || "table")}.csv"></a>`);
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); a.click(); URL.revokeObjectURL(a.href);
  };
  header(); draw();
}

/** Remember the list a symbol was opened from, so the chart can step through it (↑ / ↓).
 *  `symbols` is a list of symbols in `market`, or of {market, symbol} for a list that mixes markets. */
function openChartFromList(market, symbol, symbols, labelText, back) {
  const seen = new Set(), items = [];
  for (const x of symbols) {
    const it = typeof x === "string" ? { m: market, s: x } : { m: x.market, s: x.symbol };
    const k = it.m + ":" + it.s;
    if (!seen.has(k)) { seen.add(k); items.push(it); }
  }
  store.set("chartList", { items, label: labelText, back });
  go(`#/chart/${market}/${encodeURIComponent(symbol)}`);
}
const MKT_BADGE = { us: "US", india: "NSE" };
const WL_COLS = [["symbol", "Symbol"], ["last", "Last"], ["chg", "Chg"], ["change_pct", "Chg%"]];
/** absolute day change of a watchlist row (the API gives last close and % change) */
const chgOf = (e) => (e.last != null && e.change_pct != null ? e.last - e.last / (1 + e.change_pct / 100) : null);

function segmented(options, current, cls = "") {
  return `<div class="seg ${cls}">${options.map(([v, t]) => `<button data-v="${esc(v)}" class="${v === current ? "on" : ""}">${t}</button>`).join("")}</div>`;
}

// ------------------------------------------------------------ chart page

const CHART_THEME = {
  layout: { background: { color: "#161a25" }, textColor: "#b2b5be", fontSize: 11, panes: { separatorColor: "#2a2e39", separatorHoverColor: "#363c4e" } },
  grid: { vertLines: { color: "#1f2330" }, horzLines: { color: "#1f2330" } },
  rightPriceScale: { borderColor: "#2a2e39" }, timeScale: { borderColor: "#2a2e39", rightOffset: 6, minBarSpacing: 0.05 },
};
let keepView = null;
const ALL_BARS = 100000;  // i.e. everything in the database: the chart shows the full stored history
// strategy keys for the "Screener levels" indicator's setting (fetched once; the page still works without it)
api("/api/strategies").then((xs) => Studies.setStrategies(xs.filter((x) => x.kind === "screener").map((x) => x.key))).catch(() => {});  // visible range to restore when the chart is rebuilt for an indicator change
const BENCH = { us: "SPY", india: "NIFTY50" };

async function chartPage(alive, market, symbol, tf) {
  const prefs = { panel: true, tab: "wl", w: 320, ...store.get("chartPrefs", {}) };
  if (!prefs.panel) prefs.tab = null;  // older prefs: a hidden panel
  market = market || store.get("lastMarket", "us");
  symbol = symbol || store.get("lastSymbol:" + market, market === "us" ? "AAPL" : "RELIANCE.NS");
  tf = tf || store.get("lastTf", "D");
  store.set("lastMarket", market); store.set("lastSymbol:" + market, symbol); store.set("lastTf", tf);
  document.title = `${symbol} · Trading`;
  const list = store.get("chartList", null);
  const pos = list?.items ? list.items.findIndex((i) => i.m === market && i.s === symbol) : -1;
  const hrefFor = (m, s, t = tf) => `#/chart/${m}/${encodeURIComponent(s)}/${t}`;
  const href = (s, t = tf) => hrefFor(market, s, t);

  $view.innerHTML = `
    <div class="chart-top">
      <div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg>
        <input id="sym" value="${esc(symbol)}" autocomplete="off" spellcheck="false" title="Search symbols — or just start typing"><ul hidden></ul></div>
      ${segmented([["D", "1D"], ["W", "1W"], ["M", "1M"]], tf, "tfs")}
      <button class="ghost" id="ind" title="Add indicators"><svg viewBox="0 0 20 20"><path d="M3 15l4-5 3 3 7-8"/><path d="M13 5h4v4"/></svg>Indicators</button>
      <label class="field" id="trades-field" title="Mark the buys and exits a backtest run made in this symbol"><span>Backtest trades</span>
        <select id="trades"><option value="">None</option></select></label>
      <button class="ghost icon" id="fit" title="Show full history"><svg viewBox="0 0 20 20"><path d="M3 8V3h5M17 8V3h-5M3 12v5h5M17 12v5h-5"/></svg></button>
      <span class="spacer"></span>
      ${pos >= 0 ? `<div class="stepper" title="Step through the list (↑ / ↓)"><button class="ghost icon" id="prev">‹</button><span>${pos + 1} / ${list.items.length}</span><button class="ghost icon" id="next">›</button></div>` : ""}
    </div>
    <div class="quote" id="quote"><b class="q-sym">${esc(symbol)}</b><span class="mkt">${MKT_BADGE[market] || market}</span></div>
    <div class="chart-layout"><div class="tools" id="tools"></div>
      <div id="chart">${LOADING}</div>
      <aside class="side" id="side"><div class="side-grip" title="Drag to resize"></div><div class="side-body"></div></aside>
      <nav class="rbar" id="rbar">
        <button data-tab="wl" title="Watchlist"><svg viewBox="0 0 20 20"><path d="M7 5h10M7 10h10M7 15h10"/><circle cx="3.5" cy="5" r=".6"/><circle cx="3.5" cy="10" r=".6"/><circle cx="3.5" cy="15" r=".6"/></svg></button>
        <button data-tab="info" title="Symbol details — fundamentals, screener plan, decision history"><svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="7"/><path d="M10 9v5M10 6.2v.1"/></svg></button>
        ${pos >= 0 && !String(list.label).startsWith("Watchlist") ? `<button data-tab="list" title="${esc(list.label)}"><svg viewBox="0 0 20 20"><path d="M4 4h12v12H4z"/><path d="M7 8h6M7 12h6"/></svg></button>` : ""}
      </nav></div>`;
  const $ = (s) => $view.querySelector(s);
  $view.querySelectorAll(".tfs button").forEach((b) => b.onclick = () => go(href(symbol, b.dataset.v)));
  // right sidebar (TradingView): an icon bar; clicking an icon opens its panel, clicking the open one closes it
  if (prefs.tab === "list" && !$('#rbar [data-tab="list"]')) prefs.tab = "wl";
  const layout = $(".chart-layout");
  const syncPanel = () => {
    layout.classList.toggle("collapsed", !prefs.tab);
    layout.style.setProperty("--side-w", Math.max(240, Math.min(640, prefs.w)) + "px");
    $view.querySelectorAll("#rbar [data-tab]").forEach((b) => b.classList.toggle("on", b.dataset.tab === prefs.tab));
  };
  syncPanel();
  $("#rbar").onclick = (e) => {
    const b = e.target.closest("[data-tab]"); if (!b) return;
    prefs.tab = prefs.tab === b.dataset.tab ? null : b.dataset.tab;
    prefs.panel = !!prefs.tab; store.set("chartPrefs", prefs); syncPanel(); renderSide();
  };
  $(".side-grip").onmousedown = (e) => {  // drag the panel's left edge to resize it
    e.preventDefault();
    const x0 = e.clientX, w0 = $("#side").offsetWidth;
    const move = (ev) => { prefs.w = w0 + (x0 - ev.clientX); syncPanel(); };
    const up = () => { removeEventListener("mousemove", move); removeEventListener("mouseup", up); prefs.w = $("#side").offsetWidth; store.set("chartPrefs", prefs); };
    addEventListener("mousemove", move); addEventListener("mouseup", up);
  };
  const step = (d) => {  // re-read the list: re-sorting the watchlist panel reorders it
    const l = store.get("chartList", null), p = l?.items ? l.items.findIndex((i) => i.m === market && i.s === symbol) : -1;
    if (p >= 0) { const it = l.items[(p + d + l.items.length) % l.items.length]; go(hrefFor(it.m, it.s)); }
  };
  if (pos >= 0) { $("#prev").onclick = () => step(-1); $("#next").onclick = () => step(1); }

  let sideReady = false;  // the panel renders once the symbol's context has loaded
  const viewKey = `${market}:${symbol}:${tf}`;
  let chart = null;
  // rebuild the chart (for an indicator change) without losing the user's zoom / scroll
  const rerender = () => { try { if (chart) keepView = { key: viewKey, range: chart.timeScale().getVisibleLogicalRange() }; } catch {} route(); };
  $("#ind").onclick = () => Studies.openPicker({ onChange: rerender });

  const search = $("#sym");
  symbolSearch(search, $(".search ul"), null, (s, m) => go(hrefFor(m, s)));
  // TradingView habit: start typing anywhere to change symbol; arrows step through the list
  const onKey = (e) => {
    if (e.target.closest?.("input, select, textarea") || e.metaKey || e.ctrlKey || e.altKey) return;
    if (/^[a-z0-9]$/i.test(e.key)) { search.focus(); search.value = e.key.toUpperCase(); search.dispatchEvent(new Event("input")); e.preventDefault(); }
    else if (e.key === "ArrowDown") { step(1); e.preventDefault(); }
    else if (e.key === "ArrowUp") { step(-1); e.preventDefault(); }
  };
  document.addEventListener("keydown", onKey);
  cleanup = () => { document.removeEventListener("keydown", onKey); };

  const bench = BENCH[market];
  const [px, ctx, tradeRuns, bpx, wlLists, wlMember, qrows] = await Promise.all([
    api(`/api/prices?market=${market}&symbol=${encodeURIComponent(symbol)}&tf=${tf}&bars=${ALL_BARS}`).catch((e) => ({ error: e.message })),
    api(`/api/symbol-context?market=${market}&symbol=${encodeURIComponent(symbol)}`).catch(() => ({ latest: [], history: [] })),
    api(`/api/trade-runs?market=${market}&symbol=${encodeURIComponent(symbol)}`).catch(() => []),
    Studies.needsBench() ? api(`/api/prices?market=${market}&symbol=${bench}&tf=${tf}&bars=${ALL_BARS}`).catch(() => null) : null,
    WL.lists().catch(() => []),
    WL.membership(market, symbol).catch(() => ({ lists: [] })),
    api(`/api/quality?market=${market}&symbol=${encodeURIComponent(symbol)}`).catch(() => []),
  ]);
  const qrow = qrows[0];
  // watchlists: the active one is shown in the side panel; ☆ toggles this symbol in it
  let wlAll = wlLists, wlCur = WL.active(wlAll), wl = [], member = new Set(wlMember.lists.map(String));
  const loadWl = async () => {
    wlAll = await WL.lists().catch(() => wlAll);
    wlCur = WL.active(wlAll);
    wl = wlCur ? await WL.items(wlCur.id).catch(() => []) : [];
    member = new Set((await WL.membership(market, symbol).catch(() => ({ lists: [] }))).lists.map(String));
    if (wl.some((e) => e.market === market && e.symbol === symbol) && wlCur?.builtin) member.add("screener");
  };
  await loadWl();
  if (!alive()) return;
  // opened by search but on the shown watchlist: ↑ / ↓ step through that list, as in TradingView
  if (pos < 0 && wlCur && wl.some((e) => e.market === market && e.symbol === symbol))
    store.set("chartList", { items: sortedWl().map((e) => ({ m: e.market, s: e.symbol })), label: `Watchlist · ${wlCur.name}`, back: `#/watchlist/${wlCur.id}` });
  const chartEl = $("#chart");
  sideReady = true;
  renderSide();
  if (px.error) {
    chartEl.innerHTML = `<div class="empty"><b>No price data for ${esc(symbol)}</b><div class="muted">${esc(px.error)}</div>
      <div class="muted">Check the symbol and market — India symbols end in <code>.NS</code>.</div></div>`;
    return;
  }
  chartEl.innerHTML = `<div class="legend"></div>`;
  const sector = (ctx.latest.find((l) => l.sector) || {}).sector;

  const sel = $("#trades");
  tradeRuns.forEach((r) => sel.insertAdjacentHTML("beforeend", `<option value="${r.id}">${esc(r.strategy)} · ${esc(r.run)} — ${r.trades} trade${r.trades > 1 ? "s" : ""}</option>`));
  $("#trades-field").hidden = !tradeRuns.length;
  // a remembered run may no longer exist (or not trade this symbol): fall back to no overlay
  const want = store.get("tradeRun:" + market, "") + "";
  sel.value = [...sel.options].some((o) => o.value === want) ? want : "";
  sel.onchange = () => { store.set("tradeRun:" + market, sel.value); route(); };

  // drag-panning of the plot is done by our own handler below (both axes, TradingView style), so the
  // library's horizontal-only drag is off; wheel zoom, touch and the axis drag-to-scale stay native
  chart = LC.createChart(chartEl, { autoSize: true, ...CHART_THEME, crosshair: { mode: LC.CrosshairMode.Normal },
    handleScroll: { mouseWheel: true, pressedMouseMove: false, horzTouchDrag: true, vertTouchDrag: false } });
  const prevCleanup = cleanup;
  let dr;
  cleanup = () => { prevCleanup(); dr && dr.destroy(); chart.remove(); };
  let main, times;
  const rows = px.ohlc ? px.candles : px.line;
  if (px.ohlc) {
    main = chart.addSeries(LC.CandlestickSeries, { upColor: "#26a69a", downColor: "#ef5350", borderVisible: false, wickUpColor: "#26a69a", wickDownColor: "#ef5350" }, 0);
    main.setData(px.candles);
  } else {
    main = chart.addSeries(LC.AreaSeries, { lineColor: "#2962ff", topColor: "rgba(41,98,255,.25)", bottomColor: "rgba(41,98,255,0)", lineWidth: 2 }, 0);
    main.setData(px.line);
  }
  times = rows.map((c) => c.time);

  // indicators
  const B = { O: [], H: [], L: [], C: [], V: [] };
  rows.forEach((d, i) => {
    if (px.ohlc) { B.O.push(d.open); B.H.push(d.high); B.L.push(d.low); B.C.push(d.close); B.V.push(px.volume[i].value); }
    else { B.O.push(d.value); B.H.push(d.value); B.L.push(d.value); B.C.push(d.value); B.V.push(0); }
  });
  const benchMap = bpx ? new Map((bpx.line || bpx.candles).map((d) => [d.time, d.value ?? d.close])) : null;
  const studies = Studies.render({ chart, times, bars: B, ctx: { bench: benchMap, main, tf, plans: px.ohlc ? ctx.latest : [] } });
  const nPanes = Math.max(0, ...studies.map((e) => e.pane || 0));

  // (the screener's entry / stop / target lines are now an opt-in indicator: Indicators -> Screener)

  // backtest trades from the chosen run
  if (sel.value && px.ohlc) {
    const t = await api(`/api/reports/${sel.value}/tables/trades?symbol=${encodeURIComponent(symbol)}`).catch(() => null);
    if (!alive()) return;
    if (t) {
      const c = (n) => t.columns.indexOf(n), snap = (d) => times.find((x) => x >= d);
      const marks = [];
      t.rows.forEach((r) => {
        const a = snap(r[c("entry_date")]), b = snap(r[c("exit_date")]), pnl = r[c("pnl")], rm = r[c("r_multiple")];
        if (a) marks.push({ time: a, position: "belowBar", shape: "arrowUp", color: "#2196f3", text: "Buy" });
        if (b) marks.push({ time: b, position: "aboveBar", shape: "arrowDown", color: pnl >= 0 ? "#26a69a" : "#ef5350", text: `${r[c("exit_reason")]} ${rm > 0 ? "+" : ""}${rm}R` });
      });
      marks.sort((x, y) => (x.time < y.time ? -1 : x.time > y.time ? 1 : 0));
      LC.createSeriesMarkers(main, marks);
    }
  }

  const bars = tf === "D" ? 130 : tf === "W" ? 104 : 60;  // open zoomed in on recent history
  requestAnimationFrame(() => {  // after autoSize has laid out the panes
    // each indicator pane ~20% of the height, but the price pane always keeps at least half
    const per = Math.round(chartEl.clientHeight * Math.min(0.2, 0.5 / Math.max(nPanes, 1)));
    for (let i = 1; i <= nPanes; i++) try { chart.panes()[i].setHeight(per); } catch {}
    if (keepView && keepView.key === viewKey && keepView.range) chart.timeScale().setVisibleLogicalRange(keepView.range);
    else if (times.length > bars) chart.timeScale().setVisibleLogicalRange({ from: times.length - bars, to: times.length + 4 });
    else chart.timeScale().fitContent();
    keepView = null;
    setLegend();
  });
  $("#fit").onclick = () => chart.timeScale().fitContent();

  // ---- panning, TradingView style: press on the plot and drag to move the chart left/right and
  // up/down at once. Moving the price range by hand switches that pane's auto-scale off (as in
  // TradingView); the "auto" toggle, a double-click on the price axis, or Alt+R restores it.
  const scaleOf = (i) => chart.priceScale("right", i);
  const autoBtn = el(`<button class="autoscale" title="Auto-scale the price axis (fit the visible bars)">auto</button>`);
  chartEl.append(autoBtn);
  const syncAuto = () => autoBtn.classList.toggle("on", scaleOf(0).options().autoScale !== false);
  autoBtn.onclick = () => {
    const on = !autoBtn.classList.contains("on");
    chart.panes().forEach((_, i) => scaleOf(i).applyOptions({ autoScale: on }));
    syncAuto();
  };
  const paneAt = (y) => {
    let top = 0;
    const ps = chart.panes();
    for (let i = 0; i < ps.length; i++) {
      const h = ps[i].getHeight();
      if (y < top + h) return { i, h };
      top += h + 1;  // 1px separator
    }
    return null;  // the time axis
  };
  let drag = null;
  chartEl.addEventListener("mousedown", (ev) => {
    // drawings and legend controls stop the event before it gets here; the axes keep their own drag-to-scale
    if (ev.button !== 0 || ev.target.closest(".legend, .pane-legend, .dtb, .dtext, .autoscale")) return;
    if (dr && !Drawings.TOOLS[dr.tool]?.cursor) return;  // a drawing tool is placing points
    const r = chartEl.getBoundingClientRect(), x = ev.clientX - r.left, p = paneAt(ev.clientY - r.top);
    if (!p || x > chart.timeScale().width()) return;
    const tr = chart.timeScale().getVisibleLogicalRange();
    if (!tr) return;
    drag = { x0: ev.clientX, y0: ev.clientY, pane: p, tr, bar: chart.timeScale().width() / (tr.to - tr.from), pr: null, moved: false };
  });
  const onPanMove = (ev) => {
    if (!drag) return;
    if (!(ev.buttons & 1)) { drag = null; chartEl.classList.remove("panning"); return; }
    const dx = ev.clientX - drag.x0, dy = ev.clientY - drag.y0;
    if (!drag.moved && Math.hypot(dx, dy) < 3) return;  // a click, not a drag
    drag.moved = true;
    chartEl.classList.add("panning");
    // horizontal: drag right -> earlier bars come into view
    const db = dx / drag.bar;
    chart.timeScale().setVisibleLogicalRange({ from: drag.tr.from - db, to: drag.tr.to - db });
    // vertical: engages after a deliberate 6px, so a sideways drag keeps auto-scale on
    if (!drag.pr && Math.abs(dy) >= 6) drag.pr = scaleOf(drag.pane.i).getVisibleRange();
    if (drag.pr) {
      const shift = dy * (drag.pr.to - drag.pr.from) / drag.pane.h;  // drag down -> candles move down
      scaleOf(drag.pane.i).setVisibleRange({ from: drag.pr.from + shift, to: drag.pr.to + shift });
      syncAuto();
    }
  };
  const onPanUp = () => { drag = null; chartEl.classList.remove("panning"); };
  const onResetKey = (ev) => {
    if (ev.altKey && ev.code === "KeyR" && !ev.target.closest?.("input, select, textarea")) {
      ev.preventDefault();
      chart.panes().forEach((_, i) => scaleOf(i).applyOptions({ autoScale: true }));
      const n = times.length, b = tf === "D" ? 130 : tf === "W" ? 104 : 60;
      if (n > b) chart.timeScale().setVisibleLogicalRange({ from: n - b, to: n + 4 }); else chart.timeScale().fitContent();
      syncAuto();
    }
  };
  window.addEventListener("mousemove", onPanMove);
  window.addEventListener("mouseup", onPanUp);
  document.addEventListener("keydown", onResetKey);
  chartEl.addEventListener("dblclick", () => setTimeout(syncAuto, 0));  // axis double-click re-enables auto
  syncAuto();
  { const prev = cleanup; cleanup = () => { window.removeEventListener("mousemove", onPanMove); window.removeEventListener("mouseup", onPanUp);
    document.removeEventListener("keydown", onResetKey); prev(); }; }

  // quote strip: last price, change, 52-week range
  const last = rows.at(-1), lastClose = px.ohlc ? last.close : last.value;
  const prevClose = rows.length > 1 ? (px.ohlc ? rows.at(-2).close : rows.at(-2).value) : lastClose;
  const yearAgo = new Date(Date.parse(last.time) - 365 * 864e5).toISOString().slice(0, 10);
  const yr = rows.filter((r) => r.time >= yearAgo);
  const hi52 = Math.max(...yr.map((r) => (px.ohlc ? r.high : r.value))), lo52 = Math.min(...yr.map((r) => (px.ohlc ? r.low : r.value)));
  const chg = (lastClose / prevClose - 1) * 100, fromHi = (lastClose / hi52 - 1) * 100;
  const rangePos = hi52 > lo52 ? ((lastClose - lo52) / (hi52 - lo52)) * 100 : 50;
  $("#quote").innerHTML = `<b class="q-sym">${esc(symbol)}</b>${ctx.name ? `<span class="q-name" title="${esc(ctx.name)}">${esc(ctx.name)}</span>` : ""}<span class="mkt">${MKT_BADGE[market] || market}</span><button class="star" id="star"></button>${sector ? `<span class="muted">${esc(sector)}</span>` : ""}
    <span class="q-px">${fmt(lastClose)}</span><span class="${chg >= 0 ? "pos" : "neg"}">${signed(chg)}%</span>
    <span class="muted">${tf === "D" ? "1 day" : tf === "W" ? "1 week" : "1 month"} · ${prettyDate(last.time)}</span>
    ${rows[0].time > "2011-01-01" ? `<span class="hist-note" title="The database holds this symbol from ${prettyDate(rows[0].time)} only — a recent listing, or history that was never backfilled. To fetch up to 16 years, run from scripts/:\npython3 -m swing_screener.marketdata.backfill --market ${market} --years 16 --only-short">history from ${prettyDate(rows[0].time)} ⓘ</span>` : ""}
    <span class="q-range" title="52-week range"><span class="muted">52w</span> ${fmt(lo52)}
      <span class="bar52"><i style="left:${rangePos.toFixed(1)}%"></i></span>${fmt(hi52)}
      <span class="${fromHi >= -0.5 ? "pos" : "muted"}">${fromHi >= -0.5 ? "at high" : signed(fromHi, 1) + "% from high"}</span></span>`;

  // watchlist star (TradingView): toggles this symbol in the active list; right-click to pick any list
  const starTarget = () => (wlCur && !wlCur.builtin ? wlCur : wlAll.find((l) => !l.builtin));
  const syncStar = () => {
    const t = starTarget(), on = t && member.has(String(t.id)), b = $("#star");
    b.classList.toggle("starred", !!on);
    b.innerHTML = on ? "★" : "☆";
    const others = wlAll.filter((l) => !l.builtin && member.has(String(l.id)) && l !== t).map((l) => l.name);
    b.title = (on ? `In “${t.name}” — click to remove` : `Add to “${t ? t.name : "a new watchlist"}”`)
      + (others.length ? `\nAlso in: ${others.join(", ")}` : "") + "\nRight-click: choose a list";
  };
  const toggleIn = async (l, on) => {
    try {
      if (on) { await WL.remove(l.id, market, symbol); toast(`${symbol} removed from “${l.name}”`, "ok"); }
      else { await WL.add(l.id, symbol, market); toast(`${symbol} added to “${l.name}”`, "ok"); }
      await loadWl(); syncStar(); renderSide();
    } catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
  };
  syncStar();
  $("#star").onclick = async () => {
    let t = starTarget();
    if (!t) { const id = await wlNew(); if (id == null) return; await loadWl(); t = wlAll.find((l) => String(l.id) === String(id)); }
    toggleIn(t, member.has(String(t.id)));
  };
  $("#star").oncontextmenu = (ev) => {
    ev.preventDefault();
    contextMenu(ev.clientX, ev.clientY, "Add to watchlist", [
      ...wlAll.filter((l) => !l.builtin).map((l) => ({ label: `${member.has(String(l.id)) ? "✓ " : "\u2003"}${l.name}`, fn: () => toggleIn(l, member.has(String(l.id))) })),
      { sep: true },
      { label: "Create new list…", fn: async () => { const id = await wlNew(); if (id == null) return; await WL.add(id, symbol, market); WL.setActive(id); await loadWl(); syncStar(); renderSide(); } },
    ]);
  };

  // legends: OHLC + overlay indicators in the price pane, one legend per indicator pane (TradingView style)
  const legend = chartEl.querySelector(".legend");
  const paneLegends = [];
  for (let p = 1; p <= nPanes; p++) { const d = el(`<div class="pane-legend"></div>`); chartEl.append(d); paneLegends[p] = d; }
  const byTime = new Map(rows.map((d, i) => [d.time, i]));
  let lastI = rows.length - 1, selStudy = null;
  // rows are built once; setLegend only rewrites text inside them (see Studies.legendRow)
  legend.innerHTML = `<div class="ohlc"></div>` + studies.filter((e) => e.pane === 0).map((e) => Studies.legendRow(e)).join("");
  for (let p = 1; p <= nPanes; p++) paneLegends[p].innerHTML = studies.filter((e) => e.pane === p).map((e) => Studies.legendRow(e)).join("");
  const rowEls = studies.map((e) => ({ e, vals: chartEl.querySelector(`.srow[data-id="${e.s.id}"] .svals`) }));
  const ohlcEl = legend.querySelector(".ohlc");
  const setLegend = (t) => {
    const i = t != null && byTime.has(t) ? byTime.get(t) : rows.length - 1, d = rows[i];
    lastI = i;
    if (px.ohlc) {
      const p = rows[i - 1], c = p ? (d.close / p.close - 1) * 100 : 0, cls = d.close >= d.open ? "pos" : "neg";
      ohlcEl.innerHTML = `<span class="muted">${prettyDate(d.time)}</span> O <span class="${cls}">${fmt(d.open)}</span> H <span class="${cls}">${fmt(d.high)}</span>
        L <span class="${cls}">${fmt(d.low)}</span> C <span class="${cls}">${fmt(d.close)}</span> <span class="${c >= 0 ? "pos" : "neg"}">${signed(c)}%</span>`;
    } else ohlcEl.innerHTML = `<span class="muted">${prettyDate(d.time)}</span> ${fmt(d.value)}`;
    rowEls.forEach(({ e, vals }) => { if (vals) vals.innerHTML = Studies.legendValues(e, i); });
    let top = 0;
    for (let p = 1; p <= nPanes; p++) {
      top += chart.panes()[p - 1].getHeight() + 1;
      paneLegends[p].style.top = top + 4 + "px";
    }
  };
  // ---- indicator selection & removal (TradingView: click the line or its name, then Delete)
  const selectStudy = (id) => {
    selStudy = id;
    chartEl.querySelectorAll(".srow").forEach((r) => r.classList.toggle("sel", r.dataset.id === selStudy));
    studies.forEach((e) => (e.series || []).forEach((ser, j) => {  // thicken the selected lines
      const pl = e.def.plots[j]; if (!pl || e.def.custom || pl.s === "hist" || pl.s === "dots") return;
      const w = pl.w || (e.def.overlay ? 1 : 1.5);
      ser.applyOptions({ lineWidth: e.s.id === id ? w + 1.5 : w });
    }));
  };
  /** remove, rebuild the chart, and offer Undo */
  const removeStudies = (ids, what) => {
    const before = Studies.load();
    Studies.restore(before.filter((s) => !ids.includes(s.id)));
    rerender();
    toast(`Removed ${what}`, "ok", { label: "Undo", fn: () => { Studies.restore(before); rerender(); } });
  };
  const removeStudy = (id) => { const e = studies.find((x) => x.s.id === id); removeStudies([id], e ? Studies.label(e.s) : "indicator"); };
  const toggleStudy = (id) => {
    const s = Studies.toggleHidden(id), e = studies.find((x) => x.s.id === id);
    if (s && e) { e.s.hidden = s.hidden; if (e.setVisible) e.setVisible(!s.hidden); else (e.series || []).forEach((ser) => ser.applyOptions({ visible: !s.hidden })); }
    chartEl.querySelector(`.srow[data-id="${id}"]`)?.classList.toggle("off", !!s?.hidden);
    setLegend(times[lastI]);
  };
  // legend controls: hide / settings / remove (hover buttons, like TradingView)
  chartEl.addEventListener("click", (ev) => {
    const row = ev.target.closest(".srow"); if (!row) return;
    const id = row.dataset.id, a = ev.target.closest("button[data-a]")?.dataset.a;
    if (a === "eye") toggleStudy(id);
    else if (a === "gear") Studies.openSettings(id, rerender);
    else if (a === "x") removeStudy(id);
    else selectStudy(selStudy === id ? null : id);
  });
  chartEl.addEventListener("dblclick", (ev) => { const r = ev.target.closest(".srow"); if (r) Studies.openSettings(r.dataset.id, rerender); });
  /** the indicator whose line is within a few pixels of a chart point (in the pane it is in) */
  const studyNear = (p) => {
    if (!p?.point || !p.seriesData) return null;
    let best = null, bd = 7;
    for (const e of studies) {
      if (e.pane !== (p.paneIndex ?? 0) || !e.series || e.s.hidden) continue;
      e.series.forEach((ser) => {
        const d = p.seriesData.get(ser), v = d?.value;
        const y = v == null ? null : ser.priceToCoordinate(v);
        if (y != null && Math.abs(y - p.point.y) < bd) { bd = Math.abs(y - p.point.y); best = e; }
      });
    }
    return best;
  };
  // clicking an indicator's line selects it
  chart.subscribeClick((p) => {
    if (!p.point || !dr || !Drawings.TOOLS[dr.tool]?.cursor || dr.tool === "eraser") return;
    selectStudy(studyNear(p)?.s.id ?? null);
  });
  // right-click an indicator (its legend row or its line): Settings / Hide / Remove, as in TradingView
  let lastHover = null;
  chart.subscribeCrosshairMove((p) => { lastHover = p; });
  chartEl.addEventListener("contextmenu", (ev) => {
    const row = ev.target.closest(".srow");
    let e = row ? studies.find((x) => x.s.id === row.dataset.id) : null;
    if (!e && !ev.target.closest(".legend, .pane-legend")) {
      // lastHover.point is relative to the pane; only trust it if the pointer is where the crosshair last was
      e = studyNear(lastHover);
    }
    if (!e) return;
    ev.preventDefault();
    selectStudy(e.s.id);
    const id = e.s.id;
    contextMenu(ev.clientX, ev.clientY, Studies.label(e.s), [
      { label: "Settings…", fn: () => Studies.openSettings(id, rerender) },
      { label: e.s.hidden ? "Show" : "Hide", fn: () => toggleStudy(id) },
      { sep: true },
      { label: "Remove indicator", danger: true, key: "Del", fn: () => removeStudy(id) },
      ...(studies.length > 1 ? [{ label: `Remove all ${studies.length} indicators`, danger: true,
        fn: () => removeStudies(studies.map((x) => x.s.id), `${studies.length} indicators`) }] : []),
    ]);
  });
  const onStudyKey = (ev) => {
    if (!selStudy || ev.target.closest?.("input, select, textarea")) return;
    if (ev.key === "Delete" || ev.key === "Backspace") { ev.preventDefault(); ev.stopImmediatePropagation(); removeStudy(selStudy); }
    else if (ev.key === "Escape") selectStudy(null);
  };
  document.addEventListener("keydown", onStudyKey, true);
  { const prev = cleanup; cleanup = () => { document.removeEventListener("keydown", onStudyKey, true); prev(); }; }
  setLegend();
  chart.subscribeCrosshairMove((p) => setLegend(p.time));
  const ro = new ResizeObserver(() => setLegend());
  ro.observe(chartEl);
  const prevCleanup1 = cleanup;
  cleanup = () => { ro.disconnect(); prevCleanup1(); };

  // drawing tools (TradingView-style left toolbar)
  const ohlcBars = px.ohlc ? px.candles : px.line.map((d) => ({ open: d.value, high: d.value, low: d.value, close: d.value }));
  dr = Drawings.create({ chart, series: main, chartEl, times, bars: ohlcBars, key: `${market}:${symbol}` });
  const unmountTools = Drawings.mountToolbar($("#tools"), dr, {
    count: () => studies.length,
    removeAll: () => removeStudies(studies.map((e) => e.s.id), `${studies.length} indicator${studies.length === 1 ? "" : "s"}`),
  });
  const prevCleanup2 = cleanup;
  cleanup = () => { unmountTools(); prevCleanup2(); };

  // ---- right panel: Watchlist (TradingView layout) / symbol details / the list this chart was opened from
  function pxQuote() {  // last close, day change and 52-week range of the open symbol (from the loaded bars)
    if (px.error) return null;
    const bars = px.ohlc ? px.candles : px.line, n = bars.length; if (!n) return null;
    const c = (r) => (px.ohlc ? r.close : r.value), lastB = bars[n - 1], prevB = bars[n - 2] || lastB;
    const yearAgo = new Date(Date.parse(lastB.time) - 365 * 864e5).toISOString().slice(0, 10);
    const yr = bars.filter((r) => r.time >= yearAgo);
    return { last: c(lastB), chg: c(lastB) - c(prevB), pct: (c(lastB) / c(prevB) - 1) * 100, date: lastB.time,
      hi: Math.max(...yr.map((r) => (px.ohlc ? r.high : r.value))), lo: Math.min(...yr.map((r) => (px.ohlc ? r.low : r.value))) };
  }
  function sortedWl() {
    const srt = store.get("wlSort", null);
    if (!srt) return wl;
    const v = (e) => (srt.k === "chg" ? chgOf(e) : srt.k === "symbol" ? e.symbol : e[srt.k]);
    return [...wl].sort((x, y) => {
      const a = v(x), b = v(y);
      if (a == null) return 1; if (b == null) return -1;
      return (typeof a === "string" ? a.localeCompare(b) : a - b) * srt.d;
    });
  }
  function infoHtml() {
    const plans = ctx.latest.map((l) => {
      const risk = l.entry > 0 && l.stop > 0 ? ((l.entry - l.stop) / l.entry) * 100 : null;
      return `<div class="plan"><div class="row"><b>${esc(l.strategy)}</b><span class="tag ${decisionClass(l.decision)}">${esc(l.decision)}</span></div>
        ${l.strategy_setup ? `<div class="muted small">${esc(l.strategy_setup)}</div>` : ""}
        ${l.entry > 0 ? `<div class="kv"><span>Entry <b>${fmt(l.entry)}</b></span><span>Stop <b class="neg">${fmt(l.stop)}</b></span>
          ${risk != null ? `<span>Risk <b>${risk.toFixed(1)}%</b></span>` : ""}${l.target_r ? `<span>Target <b class="pos">${fmt(+l.target_r)}R</b></span>` : ""}</div>` : ""}
        <div class="muted small">${prettyDate(String(l.run_id).replace(/^screener\//, ""))}</div></div>`;
    }).join("");
    const hist = ctx.history.slice(0, 20).map((h) => `<div class="hist"><span class="muted">${prettyDate(h.run_id)}</span><span>${esc(h.strategy)}</span>
      <span class="tag ${decisionClass(h.decision)}">${esc(h.decision)}</span></div>`).join("");
    const pc = (v) => (v == null ? "—" : `${(v * 100).toFixed(0)}%`);
    const qHtml = qrow && qrow.quality != null ? `<section><h3>Fundamentals <a class="muted" href="#/quality/${market}">quality page</a></h3>
      <div class="plan"><div class="row"><b>Quality ${qrow.quality}/100 <span class="muted small">F ${qrow.f_score ?? "—"}</span></b>
        <span class="tag ${zoneClass(qrow.at_your_price ? "AT YOUR PRICE" : qrow.zone)}">${esc(qrow.at_your_price ? "AT YOUR PRICE" : qrow.zone || "")}</span></div>
        <div class="kv"><span>${qrow.financial ? "ROE" : "ROIC"} <b>${pc(qrow.financial ? qrow.roe_avg : qrow.roic_avg)}</b></span><span>Rev <b>${pc(qrow.rev_cagr)}</b>/yr</span>
          <span>P/E <b>${qrow.pe ? qrow.pe.toFixed(1) : "—"}</b></span><span>Value <b class="${qrow.value === "Attractive" ? "pos" : qrow.value === "Expensive" ? "neg" : ""}">${esc(qrow.value || "—")}</b></span></div>
        ${(qrow.flags || []).length ? `<div class="muted small">${esc(qrow.flags.join(" · "))}</div>` : ""}</div></section>` : "";
    return `${qHtml}<section><h3>Screener — latest</h3>${plans || '<div class="muted small">Not in any screening run.</div>'}</section>
      <section><h3>Decision history</h3>${hist || '<div class="muted small">None.</div>'}</section>`;
  }
  /** TradingView's details block under the watchlist: the open symbol's price, day change, 52-week range and verdicts */
  function detailsHtml() {
    const q = pxQuote(), sector = ctx.latest[0]?.sector || qrow?.sector || "";
    const best = [...ctx.latest].sort((a, b) => DEC_RANK(a.decision) - DEC_RANK(b.decision))[0];
    const pos52 = q && q.hi > q.lo ? ((q.last - q.lo) / (q.hi - q.lo)) * 100 : 50;
    return `<div class="wld-head"><b>${esc(symbol)}</b><span class="mkt">${MKT_BADGE[market] || market}</span>${sector ? `<span class="muted small">${esc(sector)}</span>` : ""}</div>
      ${ctx.name ? `<div class="wld-name">${esc(ctx.name)}</div>` : ""}
      ${q ? `<div class="wld-px"><span class="big">${fmt(q.last)}</span><span class="${q.chg >= 0 ? "pos" : "neg"}">${q.chg >= 0 ? "+" : ""}${fmt(q.chg)} (${signed(q.pct)}%)</span></div>
        <div class="muted small">Close · ${prettyDate(q.date)}</div>
        <div class="wld-52"><span class="muted small">52-week range</span><div class="bar52 wide"><i style="left:${pos52.toFixed(1)}%"></i></div>
          <div class="wld-52v small"><span>${fmt(q.lo)}</span><span>${fmt(q.hi)}</span></div></div>` : ""}
      <div class="wld-kv">
        ${best ? `<span class="muted">Screener</span><span><span class="tag ${decisionClass(best.decision)}">${esc(best.decision)}</span></span>` : ""}
        ${qrow?.quality != null ? `<span class="muted">Quality</span><span><b>${qrow.quality}</b>/100 · ${esc(qrow.at_your_price ? "AT YOUR PRICE" : qrow.zone || "")}</span>` : ""}
        ${qrow?.pe ? `<span class="muted">P/E</span><span>${qrow.pe.toFixed(1)}</span>` : ""}
      </div>`;
  }
  function wlPanelHtml() {
    const srt = store.get("wlSort", null);
    const wlTitle = (e) => [e.name || "", e.strategies ? e.strategies.map((x) => `${x.strategy}: ${x.decision}`).join("\n") : "", e.note || ""].filter(Boolean).join("\n");
    const rowsHtml = sortedWl().map((e) => {
      const i = wl.indexOf(e), ch = chgOf(e), cls = (e.change_pct ?? 0) >= 0 ? "pos" : "neg";
      return `<div class="wlr ${e.market === market && e.symbol === symbol ? "cur" : ""}" data-i="${i}" title="${esc(wlTitle(e))}">
        <span class="wsym"><span class="dotm ${e.market}"></span>${esc(e.symbol.replace(/\.NS$/, ""))}${e.note ? '<i class="wnote">✎</i>' : ""}</span>
        <span>${e.last != null ? fmt(e.last) : ""}</span><span class="${cls}">${ch != null ? (ch >= 0 ? "+" : "") + fmt(ch) : ""}</span>
        <span class="${cls}">${e.change_pct != null ? signed(e.change_pct) + "%" : ""}</span>
        <button class="wx" title="Remove from list">×</button></div>`;
    }).join("");
    return `<div class="wlpanel">
      <div class="wl-head"><button class="wl-name" id="wlname" title="Switch watchlist">${esc(wlCur ? wlCur.name : "Watchlist")}<svg viewBox="0 0 20 20"><path d="M6 8l4 4 4-4"/></svg></button>
        <span class="spacer"></span>
        ${wlCur && !wlCur.builtin ? '<button class="ibtn" id="wladd" title="Add symbol">+</button>' : ""}
        <button class="ibtn" id="wlmenu" title="More">⋯</button></div>
      <div class="search wl-search" hidden><input placeholder="Add symbol — any market" spellcheck="false"><ul hidden></ul></div>
      <div class="wlcols">${WL_COLS.map(([k, t]) => `<button data-k="${k}" class="${srt?.k === k ? "on" : ""}">${t}${srt?.k === k ? (srt.d > 0 ? " ↑" : " ↓") : ""}</button>`).join("")}</div>
      <div class="wlrows">${rowsHtml || `<div class="muted small wl-empty">${wlCur?.builtin ? "No screener picks." : "Empty — click + or ☆ next to a symbol to add it."}</div>`}</div>
      <div class="wl-details">${detailsHtml()}</div></div>`;
  }
  function listPanelHtml() {
    return `<section><h3>${esc(list.label)} <a class="muted" href="${esc(list.back || "#/screening")}">back</a></h3></section>
      <div class="wlrows">${list.items.map((it, i) => `<a class="wlr nolast ${i === pos ? "cur" : ""}" href="${hrefFor(it.m, it.s)}">
        <span class="wsym"><span class="dotm ${it.m}"></span>${esc(it.s.replace(/\.NS$/, ""))}</span></a>`).join("")}</div>`;
  }
  function renderSide() {
    if (!sideReady || !prefs.tab) return;
    const body = $("#side .side-body");
    body.innerHTML = prefs.tab === "wl" ? wlPanelHtml() : prefs.tab === "list" ? `<div class="wlpanel">${listPanelHtml()}</div>` : infoHtml();
    body.querySelectorAll(".wlr.cur").forEach((c) => c.scrollIntoView({ block: "nearest" }));
    if (prefs.tab !== "wl") return;
    const redraw = async () => { await loadWl(); syncStar(); renderSide(); };
    body.querySelector("#wlname").onclick = (e) => {
      const r = e.currentTarget.getBoundingClientRect();
      contextMenu(r.left, r.bottom + 4, null, [
        ...wlAll.map((l) => ({ label: `${l === wlCur ? "✓ " : " "}${l.name}${l.count != null ? `  ·  ${l.count}` : ""}`, fn: () => { WL.setActive(l.id); redraw(); } })),
        { sep: true },
        { label: "Create new list…", fn: async () => { const id = await wlNew(); if (id != null) { WL.setActive(id); redraw(); } } },
      ]);
    };
    body.querySelector("#wlmenu").onclick = (e) => {
      const r = e.currentTarget.getBoundingClientRect();
      contextMenu(r.right - 200, r.bottom + 4, null, [
        ...wlMenuItems(wlCur, redraw),
        ...(store.get("wlSort", null) ? [{ sep: true }, { label: "Clear sorting", fn: () => { store.set("wlSort", null); renderSide(); } }] : []),
        { sep: true },
        { label: "Open in Watchlist page", fn: () => go(`#/watchlist/${wlCur ? wlCur.id : ""}`) },
      ]);
    };
    body.querySelector(".wlcols").onclick = (e) => {  // TradingView: click a column to sort, again to reverse, a third time to clear
      const k = e.target.closest("[data-k]")?.dataset.k; if (!k) return;
      const srt = store.get("wlSort", null);
      store.set("wlSort", !srt || srt.k !== k ? { k, d: k === "symbol" ? 1 : -1 } : srt.d === (k === "symbol" ? 1 : -1) ? { k, d: -srt.d } : null);
      const l = store.get("chartList", null);
      if (l && l.label === `Watchlist · ${wlCur.name}`) store.set("chartList", { ...l, items: sortedWl().map((e) => ({ m: e.market, s: e.symbol })) });
      renderSide();
    };
    const box = body.querySelector(".wl-search");
    body.querySelector("#wladd")?.addEventListener("click", () => { box.hidden = !box.hidden; if (!box.hidden) box.querySelector("input").focus(); });
    symbolSearch(box.querySelector("input"), box.querySelector("ul"), null, async (s, m) => {
      try { const r = await WL.add(wlCur.id, s, m); toast(`${r.symbol} added to “${wlCur.name}”`, "ok"); await redraw(); }
      catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
    });
    const removeRow = async (e) => {
      try { await WL.remove(wlCur.id, e.market, e.symbol); toast(`${e.symbol} removed from “${wlCur.name}”`, "ok"); await redraw(); }
      catch (err) { toast(err.message, "err"); }
    };
    const open = (e) => openChartFromList(e.market, e.symbol, sortedWl(), `Watchlist · ${wlCur.name}`, `#/watchlist/${wlCur.id}`);
    body.querySelectorAll(".wlr").forEach((r) => {
      const e = wl[+r.dataset.i];
      r.onclick = (ev) => { if (ev.target.closest(".wx")) { ev.stopPropagation(); removeRow(e); } else open(e); };
      r.oncontextmenu = (ev) => {
        ev.preventDefault();
        const others = wlAll.filter((l) => !l.builtin && l !== wlCur);
        contextMenu(ev.clientX, ev.clientY, e.symbol, [
          { label: "Open chart", fn: () => open(e) },
          ...others.map((l) => ({ label: `Add to “${l.name}”`, fn: async () => {
            try { await WL.add(l.id, e.symbol, e.market); toast(`${e.symbol} added to “${l.name}”`, "ok"); await redraw(); } catch (err) { toast(err.message, "err"); }
          } })),
          ...(!wlCur.builtin ? [{ label: "Edit note…", fn: async () => {
            const v = await askText(`Note — ${e.symbol}`, e.note || "", "e.g. wait for earnings, breakout above 120");
            if (v !== null) { await WL.note(wlCur.id, e.market, e.symbol, v.trim()); redraw(); }
          } }] : []),
          { sep: true },
          { label: wlCur.builtin ? "Hide from Screener picks" : `Remove from “${wlCur.name}”`, danger: true, fn: () => removeRow(e) },
        ]);
      };
    });
  }
}

function symbolSearch(input, list, market, onPick) {
  let timer, items = [], cur = -1;
  const show = () => {
    list.hidden = !items.length || document.activeElement !== input;
    list.innerHTML = items.map((r, i) => `<li data-i="${i}" class="${i === cur ? "sel" : ""}"><b>${esc(r.symbol)}</b><span class="muted" title="${esc(r.sector || "")}">${esc(r.name || (r.type === "index" ? "Index" : r.sector || ""))}</span><span class="mkt">${r.type === "index" ? "INDEX" : MKT_BADGE[r.market] || ""}</span></li>`).join("");
    const s = list.querySelector(".sel"); if (s) s.scrollIntoView({ block: "nearest" });
  };
  const query = async () => { items = await api(`/api/symbols?${market ? `market=${market}&` : ""}q=${encodeURIComponent(input.value)}`).catch(() => []); cur = items.length ? 0 : -1; show(); };
  input.onfocus = () => { input.select(); query(); };
  input.oninput = () => { clearTimeout(timer); timer = setTimeout(query, 100); };
  input.onkeydown = (e) => {
    if (e.key === "ArrowDown") { cur = Math.min(cur + 1, items.length - 1); show(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { cur = Math.max(cur - 1, 0); show(); e.preventDefault(); }
    else if (e.key === "Enter") { e.preventDefault(); const exact = items.find((i) => i.symbol === input.value.trim().toUpperCase()); const it = exact || (cur >= 0 ? items[cur] : null); onPick(it ? it.symbol : input.value.trim().toUpperCase(), it ? it.market : market); }
    else if (e.key === "Escape") { list.hidden = true; input.blur(); }
  };
  list.onmousedown = (e) => { const li = e.target.closest("li"); if (li) { const it = items[+li.dataset.i]; onPick(it.symbol, it.market); } };
  input.onblur = () => setTimeout(() => (list.hidden = true), 150);
}

// -------------------------------------------------------------- watchlist

const jsonReq = (method, body) => ({ method, headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
/** Named watchlists (TradingView style), plus the built-in, read-mostly "Screener picks" list (id "screener"). */
const WL = {
  lists: () => api("/api/watchlists"),
  items: (id) => api(`/api/watchlists/${id}/items`),
  create: (name) => api("/api/watchlists", jsonReq("POST", { name })),
  rename: (id, name) => api(`/api/watchlists/${id}`, jsonReq("PUT", { name })),
  del: (id) => api(`/api/watchlists/${id}`, { method: "DELETE" }),
  add: (id, symbol, market, note) => api(`/api/watchlists/${id}/items`, jsonReq("POST", { symbol, market: market || null, note: note || null })),
  remove: (id, market, symbol) => api(`/api/watchlists/${id}/items?market=${market}&symbol=${encodeURIComponent(symbol)}`, { method: "DELETE" }),
  note: (id, market, symbol, note) => api(`/api/watchlists/${id}/items`, jsonReq("PUT", { market, symbol, note: note || null })),
  membership: (m, s) => api(`/api/watchlists/membership?market=${m}&symbol=${encodeURIComponent(s)}`),
  /** the list the chart panel and the ☆ work with (remembered); falls back to the first list */
  active: (lists) => {
    const id = store.get("wlActive", null);
    return lists.find((l) => String(l.id) === String(id)) || lists.find((l) => !l.builtin) || lists[0];
  },
  setActive: (id) => store.set("wlActive", id),
};

/** watchlist ⋯ menu actions shared by the chart panel and the Watchlist page; resolve to the list to show next */
async function wlNew() {
  const name = await askText("New watchlist", "", "e.g. Breakouts, Long-term, Banks");
  if (!name?.trim()) return null;
  try { const r = await WL.create(name.trim()); toast(`Created “${r.name}”`, "ok"); return r.id; }
  catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); return null; }
}
async function wlRename(l) {
  const name = await askText("Rename watchlist", l.name);
  if (!name?.trim() || name.trim() === l.name) return null;
  try { await WL.rename(l.id, name.trim()); toast("Renamed", "ok"); return l.id; }
  catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); return null; }
}
async function wlDelete(l) {
  if (!confirm(`Delete the watchlist “${l.name}” and its ${l.count} symbol${l.count === 1 ? "" : "s"}?`)) return false;
  await WL.del(l.id); toast(`Deleted “${l.name}”`, "ok"); return true;
}
function wlMenuItems(l, after) {
  return [
    { label: "Create new list…", fn: async () => { const id = await wlNew(); if (id != null) { WL.setActive(id); after(id); } } },
    ...(l && !l.builtin ? [
      { label: "Rename…", fn: async () => { if ((await wlRename(l)) != null) after(l.id); } },
      { sep: true },
      { label: "Delete list", danger: true, fn: async () => { if (await wlDelete(l)) { store.set("wlActive", null); after(null); } } },
    ] : []),
  ];
}

/** a small floating menu (right-click menus, ⋯ menus). items: {label, fn, danger?, key?, disabled?} or {sep:true} */
function contextMenu(x, y, title, items) {
  document.querySelector(".cmenu")?.remove();
  const m = el(`<div class="cmenu">${title ? `<div class="cm-title">${esc(title)}</div>` : ""}${items.map((it, i) => it.sep ? '<div class="cm-sep"></div>'
    : `<button data-i="${i}" class="${it.danger ? "danger" : ""}" ${it.disabled ? "disabled" : ""}><span>${esc(it.label)}</span>${it.key ? `<kbd>${esc(it.key)}</kbd>` : ""}</button>`).join("")}</div>`);
  document.body.append(m);
  const r = m.getBoundingClientRect();
  m.style.left = Math.max(4, Math.min(x, innerWidth - r.width - 4)) + "px";
  m.style.top = Math.max(4, Math.min(y, innerHeight - r.height - 4)) + "px";
  const close = () => { m.remove(); document.removeEventListener("mousedown", out, true); document.removeEventListener("keydown", esc_, true);
    removeEventListener("wheel", close, true); removeEventListener("blur", close); };
  const out = (e) => { if (!m.contains(e.target)) close(); };
  const esc_ = (e) => { if (e.key === "Escape") { e.stopPropagation(); close(); } };
  setTimeout(() => { document.addEventListener("mousedown", out, true); document.addEventListener("keydown", esc_, true);
    addEventListener("wheel", close, true); addEventListener("blur", close); });
  m.onclick = (e) => { const b = e.target.closest("button[data-i]"); if (b) { close(); items[+b.dataset.i].fn(); } };
  m.oncontextmenu = (e) => e.preventDefault();
}
const DEC_RANK = (d) => (/^TRADE - HIGH/i.test(d) ? 0 : /^TRADE/i.test(d) ? 1 : /^WATCH/i.test(d) ? 2 : 3);
/** the most actionable plan across the strategies that flagged a name */
const bestPlan = (e) => [...e.strategies].sort((a, b) => DEC_RANK(a.decision) - DEC_RANK(b.decision))[0] || {};

/** small text prompt in the app's own style (resolves to null on cancel) */
function askText(title, value = "", placeholder = "") {
  return new Promise((resolve) => {
    const m = el(`<div class="smodal"><div class="smodal-card settings"><div class="sm-head"><b>${esc(title)}</b></div>
      <div class="sm-form"><input value="${esc(value)}" placeholder="${esc(placeholder)}"></div>
      <div class="sm-foot"><span class="spacer"></span><button class="ghost" data-a="cancel">Cancel</button><button class="primary" data-a="ok">Save</button></div></div></div>`);
    document.body.append(m);
    const inp = m.querySelector("input"); inp.focus(); inp.select();
    const done = (v) => { m.remove(); resolve(v); };
    m.onclick = (e) => { const a = e.target.closest("button")?.dataset.a; if (a === "ok") done(inp.value); if (a === "cancel" || e.target === m) done(null); };
    inp.onkeydown = (e) => { e.stopPropagation(); if (e.key === "Enter") done(inp.value); if (e.key === "Escape") done(null); };
  });
}

const ICON_X = '<svg viewBox="0 0 20 20"><path d="M5 5l10 10M15 5L5 15"/></svg>';
const ICON_NOTE = '<svg viewBox="0 0 20 20"><path d="M3 17l1.2-4.2L13 4l3 3-8.8 8.8z"/><path d="M11.5 5.5l3 3"/></svg>';

async function watchlistPage(alive, lid) {
  document.title = "Watchlist · Trading";
  $view.innerHTML = LOADING;
  const lists = await WL.lists();
  if (lid && lists.some((l) => String(l.id) === String(lid))) WL.setActive(lid);
  const cur = WL.active(lists);
  const items = cur ? await WL.items(cur.id) : [];
  if (!alive()) return;
  const screener = !!cur?.builtin;
  $view.innerHTML = `<div class="page-head"><h1>Watchlists</h1><span class="spacer"></span>
      ${cur && !screener ? `<form class="wl-add" autocomplete="off">
        <div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input id="wls" placeholder="Add symbol — any market" spellcheck="false"><ul hidden></ul></div>
        <input id="wln" placeholder="Note (optional)"><button class="primary" type="submit">Add</button></form>` : ""}</div>
    <div class="wl-layout">
      <aside class="wl-lists">${lists.map((l) => `<a href="#/watchlist/${l.id}" class="${l === cur ? "cur" : ""}">
          <span>${l.builtin ? "⚡ " : ""}${esc(l.name)}</span><span class="muted">${l.count ?? ""}</span></a>`).join("")}
        <button class="ghost" id="wlnew">+ New list</button></aside>
      <div class="wl-main">
        ${cur ? `<div class="wl-title"><h2>${esc(cur.name)}</h2>${screener ? "" : '<button class="ibtn" id="wlmenu" title="List menu">⋯</button>'}</div>` : ""}
        <div id="wlt"></div>
        <p class="muted small">${screener
          ? "Screener picks come from the latest full run of each strategy (tradeable or watchlist candidate) and refresh every run. Removing one hides it until it drops off the screen and is flagged again."
          : "Your own list: symbols stay until you remove them. Lists can mix US and India symbols. On the chart, ☆ toggles the symbol in the active list (right-click it to choose a list)."}</p>
      </div></div>`;
  const after = (id) => go(`#/watchlist/${id ?? ""}`);
  $view.querySelector("#wlnew").onclick = async () => { const id = await wlNew(); if (id != null) { WL.setActive(id); after(id); } };
  $view.querySelector("#wlmenu")?.addEventListener("click", (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    contextMenu(r.left, r.bottom + 4, null, wlMenuItems(cur, after));
  });
  $view.querySelectorAll(".wl-lists a").forEach((a) => a.oncontextmenu = (e) => {
    const l = lists.find((x) => `#/watchlist/${x.id}` === a.getAttribute("href"));
    if (!l || l.builtin) return;
    e.preventDefault(); contextMenu(e.clientX, e.clientY, l.name, wlMenuItems(l, after));
  });

  // add form (any market: the server resolves RELIANCE -> RELIANCE.NS)
  const form = $view.querySelector(".wl-add");
  if (form) {
    const sIn = form.querySelector("#wls"), nIn = form.querySelector("#wln");
    let picked = null;
    symbolSearch(sIn, form.querySelector("ul"), null, (s, m) => { sIn.value = s; picked = { s, m }; nIn.focus(); });
    sIn.addEventListener("input", () => (picked = null));
    form.onsubmit = async (e) => {
      e.preventDefault();
      const sym = sIn.value.trim().toUpperCase(); if (!sym) { sIn.focus(); return; }
      try {
        const r = await WL.add(cur.id, sym, picked && picked.s === sym ? picked.m : null, nIn.value.trim());
        toast(`${r.symbol} added to “${cur.name}”`, "ok"); route();
      } catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
    };
  }

  const host = $view.querySelector("#wlt");
  if (!cur) { host.innerHTML = `<div class="empty"><b>No watchlists</b><div class="muted">Create one with “+ New list”.</div></div>`; return; }
  if (!items.length) {
    host.innerHTML = `<div class="empty"><b>${screener ? "No screener picks" : "This list is empty"}</b>
      <div class="muted">${screener ? "Run the daily screening." : "Add a symbol above, or use ☆ on the chart."}</div></div>`;
    return;
  }
  const cols = screener
    ? ["symbol", "name", "market", "sector", "last", "chg %", "strategies", "decision", "entry", "to entry %", "stop", "target R", "added"]
    : ["symbol", "name", "market", "sector", "last", "chg %", "note", "added"];
  const rows = items.map((e) => {
    const base = [e.symbol, e.name || "", MKT_BADGE[e.market] || e.market, e.sector || "", e.last, e.change_pct];
    if (!screener) return [...base, e.note || "", e.added_at];
    const p = bestPlan(e);
    return [...base, e.strategies.map((x) => x.strategy).join(" · "), p.decision || "", p.entry ?? null,
      p.entry && e.last ? (p.entry / e.last - 1) * 100 : null, p.stop ?? null, p.target_r ?? null, e.added_at];
  });
  const find = (row) => items.find((x) => x.symbol === row[0] && (MKT_BADGE[x.market] || x.market) === row[2]);
  dataTable(host, cols, rows, {
    name: screener ? "watchlist_screener" : "watchlist_list", sort: ["added", -1], format: { added: prettyDate },
    rowClick: (row, visible) => {
      const e = find(row);
      openChartFromList(e.market, e.symbol, visible.map(find).filter(Boolean), `Watchlist · ${cur.name}`, location.hash);
    },
    actions: [
      ...(screener ? [] : [{ key: "note", title: "Edit note", icon: ICON_NOTE, fn: async (row) => {
        const e = find(row);
        const v = await askText(`Note — ${e.symbol}`, e.note || "", "e.g. wait for earnings, breakout above 120");
        if (v === null) return;
        await WL.note(cur.id, e.market, e.symbol, v.trim()); toast("Note saved", "ok"); route();
      } }]),
      { key: "rm", title: screener ? "Hide from Screener picks" : "Remove from this list", icon: ICON_X, fn: async (row) => {
        const e = find(row);
        await WL.remove(cur.id, e.market, e.symbol); toast(`${e.symbol} removed`, "ok"); route();
      } },
    ],
  });
}

// ------------------------------------------------------------- movers page

const MOVER_PERIODS = [["1D", "1D"], ["1W", "1W"], ["1M", "1M"], ["3M", "3M"], ["6M", "6M"], ["YTD", "YTD"], ["1Y", "1Y"]];
const MKT_NAME = { us: "US", india: "India" };
/** traded value in the market's own units: $12.3M / $1.2B, ₹45 Cr */
function moneyShort(v, market) {
  if (v == null) return "";
  if (market === "india") { const cr = v / 1e7; return `₹${cr >= 100 ? Math.round(cr).toLocaleString() : cr.toFixed(1)} Cr`; }
  return v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : `$${(v / 1e6).toFixed(v >= 1e8 ? 0 : 1)}M`;
}

async function moversPage(alive, mkt) {
  const prefs = { period: "1D", universe: "liquid", ...store.get("moversPrefs", {}) };
  mkt = ["us", "india", "both"].includes(mkt) ? mkt : store.get("moversMarket", "both");
  store.set("moversMarket", mkt);
  document.title = "Movers · Trading";
  $view.innerHTML = `<div class="page-head"><h1>Top movers</h1>
      ${segmented([["both", "US + India"], ["us", "US"], ["india", "India"]], mkt, "mk")}
      ${segmented(MOVER_PERIODS, prefs.period, "pd")}
      ${segmented([["liquid", "Liquid stocks"], ["all", "All stocks"]], prefs.universe, "un")}</div>
    <div id="mv">${LOADING}</div>`;
  $view.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(`#/movers/${b.dataset.v}`));
  $view.querySelectorAll(".pd button").forEach((b) => b.onclick = () => { store.set("moversPrefs", { ...prefs, period: b.dataset.v }); route(); });
  $view.querySelectorAll(".un button").forEach((b) => b.onclick = () => { store.set("moversPrefs", { ...prefs, universe: b.dataset.v }); route(); });
  const markets = mkt === "both" ? ["us", "india"] : [mkt];
  const data = await Promise.all(markets.map((m) =>
    api(`/api/movers?market=${m}&period=${prefs.period}&universe=${prefs.universe}&limit=25`).catch((e) => ({ market: m, error: e.message }))));
  if (!alive()) return;

  const table = (d, kind) => {
    const rows = d[kind];
    if (!rows.length) return `<div class="muted small mv-none">No ${kind === "gainers" ? "gainers" : "losers"}.</div>`;
    return `<table class="mvt"><thead><tr><th>#</th><th>Symbol</th><th class="num">Last</th><th class="num">Chg%</th>
        <th class="num" title="Volume on the last day ÷ its 50-day average">Rel vol</th><th class="num" title="Traded value on the last day">Value</th></tr></thead>
      <tbody>${rows.map((r, i) => `<tr data-k="${kind}" data-i="${i}">
        <td class="muted">${i + 1}</td>
        <td title="${esc([r.name, r.sector].filter(Boolean).join(" · "))}"><b>${esc(r.symbol.replace(/\.NS$/, ""))}</b><span class="muted small mv-sec">${esc(r.name || r.sector || "")}</span></td>
        <td class="num">${fmt(r.last)}</td>
        <td class="num"><span class="mv-pct ${r.pct >= 0 ? "up" : "dn"}">${signed(r.pct)}%</span></td>
        <td class="num ${r.rel_vol >= 2 ? "strong" : "muted"}">${r.rel_vol != null ? r.rel_vol.toFixed(1) + "×" : ""}</td>
        <td class="num muted">${moneyShort(r.value, d.market)}</td></tr>`).join("")}</tbody></table>`;
  };
  const section = (d) => {
    if (d.error || d.empty) return `<section class="mv-card"><div class="empty"><b>No data for ${MKT_NAME[d.market]}</b><div class="muted">${esc(d.error || "")}</div></div></section>`;
    const tot = d.adv + d.dec + d.unch || 1;
    const span = d.period === "1D" ? `${prettyDate(d.date)} vs ${prettyDate(d.from)}` : `${prettyDate(d.from)} → ${prettyDate(d.date)}`;
    const liq = d.universe === "liquid"
      ? `stocks trading ≥ ${moneyShort(d.liquid.value, d.market)}/day (20-day avg), price ≥ ${d.market === "india" ? "₹" : "$"}${d.liquid.price}` : "every common stock";
    return `<section class="mv-card">
      <div class="mv-head"><h2>${MKT_NAME[d.market]}</h2><span class="muted">${span}</span>
        ${d.bench.pct != null ? `<span class="mv-bench">${esc(d.bench.label)} <b class="${d.bench.pct >= 0 ? "pos" : "neg"}">${signed(d.bench.pct)}%</b></span>` : ""}
        <span class="spacer"></span>
        <span class="mv-ad" title="Advancing / declining stocks over the period">
          <span class="pos">${d.adv.toLocaleString()} up</span>
          <span class="adbar"><i class="up" style="width:${(d.adv / tot * 100).toFixed(1)}%"></i><i class="dn" style="width:${(d.dec / tot * 100).toFixed(1)}%"></i></span>
          <span class="neg">${d.dec.toLocaleString()} down</span></span></div>
      <div class="mv-cols">
        <div><h3>Top gainers</h3>${table(d, "gainers")}</div>
        <div><h3>Top losers</h3>${table(d, "losers")}</div>
      </div>
      <p class="muted small">${d.count.toLocaleString()} ${liq}. Prices are not adjusted for spin-offs, so a demerger can show as a large drop.</p></section>`;
  };
  const host = $view.querySelector("#mv");
  host.innerHTML = data.map(section).join("");
  host.querySelectorAll(".mv-card").forEach((card, ci) => {
    const d = data[ci];
    card.querySelectorAll("tbody tr").forEach((tr) => tr.onclick = () => {
      const rows = d[tr.dataset.k], r = rows[+tr.dataset.i];
      openChartFromList(d.market, r.symbol, rows.map((x) => x.symbol),
        `Top ${tr.dataset.k} · ${MKT_NAME[d.market]} ${d.period}`, location.hash);
    });
  });
}

// ------------------------------------------------------------- sectors page

const QUADS = ["Leading", "Improving", "Weakening", "Lagging"];
const QUAD_CLS = { Leading: "q-lead", Improving: "q-impr", Weakening: "q-weak", Lagging: "q-lag" };
const SEC_H = ["1W", "1M", "3M", "6M", "12M"];
const pct1 = (v, d = 1) => (v == null ? "" : `${v > 0 ? "+" : ""}${(v * 100).toFixed(d)}%`);
const pctCls = (v) => (v == null ? "" : v >= 0 ? "pos" : "neg");
const secHref = (m, level, g) => `#/sectors/${m}/${level}${g ? "/" + encodeURIComponent(g) : ""}`;
const rsBadge = (rs) => (rs == null ? "" : `<span class="rsb ${rs >= 80 ? "hi" : rs >= 50 ? "mid" : "lo"}">${rs}</span>`);

/** a sparkline of a group's RS line (values relative to its first point) */
function sparkSvg(vals, w = 90, h = 22) {
  if (!vals || vals.length < 2) return "";
  const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * w},${h - 2 - ((v - lo) / span) * (h - 4)}`).join(" ");
  const up = vals.at(-1) >= vals[0];
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}"><polyline points="${pts}" fill="none" stroke="${up ? "#26a69a" : "#ef5350"}" stroke-width="1.5"/></svg>`;
}

/** Relative Rotation Graph: RS-Ratio (x) vs RS-Momentum (y), each group's last weeks as a tail */
function rrgSvg(groups, hot) {
  const W = 560, H = 420, P = 34;
  const pts = groups.flatMap((g) => g.rrg || []);
  if (!pts.length) return '<div class="muted small">Not enough history for a rotation graph.</div>';
  const dx = Math.max(1.5, ...pts.map((p) => Math.abs(p.ratio - 100))) * 1.1;
  const dy = Math.max(1.5, ...pts.map((p) => Math.abs(p.mom - 100))) * 1.1;
  const X = (v) => P + ((v - (100 - dx)) / (2 * dx)) * (W - 2 * P), Y = (v) => H - P - ((v - (100 - dy)) / (2 * dy)) * (H - 2 * P);
  const cx = X(100), cy = Y(100);
  const palette = ["#2962ff", "#ff9800", "#26a69a", "#e91e63", "#9c27b0", "#00bcd4", "#8bc34a", "#ffc107", "#795548", "#f44336", "#3f51b5", "#cddc39", "#009688", "#ff5722", "#607d8b", "#673ab7"];
  // label positions: start at each head, then push apart vertically so names don't overprint
  const labs = groups.map((g, i) => ({ i, x: g.rrg?.length ? X(g.rrg.at(-1).ratio) + 7 : 0, y: g.rrg?.length ? Y(g.rrg.at(-1).mom) + 4 : 0, ok: !!g.rrg?.length }))
    .filter((l) => l.ok).sort((a, b) => a.y - b.y);
  for (let k = 1; k < labs.length; k++)
    for (let j = 0; j < k; j++)
      if (Math.abs(labs[k].x - labs[j].x) < 120 && labs[k].y - labs[j].y < 12) labs[k].y = labs[j].y + 12;
  const labY = Object.fromEntries(labs.map((l) => [l.i, Math.min(H - P - 2, l.y)]));
  const series = groups.map((g, i) => {
    const t = g.rrg || []; if (!t.length) return "";
    const c = palette[i % palette.length], head = t.at(-1), on = hot === g.group;
    const line = t.map((p) => `${X(p.ratio).toFixed(1)},${Y(p.mom).toFixed(1)}`).join(" ");
    return `<g class="rrg-g ${on ? "on" : ""}" data-g="${esc(g.group)}"><title>${esc(g.group)} — ${g.quadrant || ""}\nRS-Ratio ${head.ratio.toFixed(1)} · RS-Momentum ${head.mom.toFixed(1)}</title>
      <polyline points="${line}" fill="none" stroke="${c}" stroke-width="${on ? 2.5 : 1.3}" stroke-opacity="${on ? 1 : .75}"/>
      ${t.slice(0, -1).map((p) => `<circle cx="${X(p.ratio).toFixed(1)}" cy="${Y(p.mom).toFixed(1)}" r="1.8" fill="${c}"/>`).join("")}
      <circle cx="${X(head.ratio).toFixed(1)}" cy="${Y(head.mom).toFixed(1)}" r="${on ? 6 : 4.5}" fill="${c}" stroke="#0f121a" stroke-width="1"/>
      <text class="lbl" x="${(X(head.ratio) + 7).toFixed(1)}" y="${labY[i].toFixed(1)}" fill="${c}">${esc(g.group.length > 26 ? g.group.slice(0, 25) + "…" : g.group)}</text></g>`;
  }).join("");
  return `<svg class="rrg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
    <rect x="${cx}" y="${P}" width="${W - P - cx}" height="${cy - P}" class="rq lead"/><rect x="${cx}" y="${cy}" width="${W - P - cx}" height="${H - P - cy}" class="rq weak"/>
    <rect x="${P}" y="${cy}" width="${cx - P}" height="${H - P - cy}" class="rq lag"/><rect x="${P}" y="${P}" width="${cx - P}" height="${cy - P}" class="rq impr"/>
    <text x="${W - P - 6}" y="${P + 14}" class="rql" text-anchor="end">LEADING</text><text x="${W - P - 6}" y="${H - P - 6}" class="rql" text-anchor="end">WEAKENING</text>
    <text x="${P + 6}" y="${H - P - 6}" class="rql">LAGGING</text><text x="${P + 6}" y="${P + 14}" class="rql">IMPROVING</text>
    <line x1="${cx}" y1="${P}" x2="${cx}" y2="${H - P}" class="rqx"/><line x1="${P}" y1="${cy}" x2="${W - P}" y2="${cy}" class="rqx"/>
    <text x="${W / 2}" y="${H - 8}" class="rqa" text-anchor="middle">RS-Ratio → (relative strength trend)</text>
    <text x="12" y="${H / 2}" class="rqa" text-anchor="middle" transform="rotate(-90 12 ${H / 2})">RS-Momentum →</text>
    ${series}</svg>`;
}

async function sectorsPage(alive, mkt, level, group) {
  mkt = mkt === "us" || mkt === "india" ? mkt : store.get("secMarket", "us");
  level = level === "industry" || level === "sector" ? level : store.get("secLevel", "industry");
  store.set("secMarket", mkt); store.set("secLevel", level);
  if (group) return sectorGroupPage(alive, mkt, level, group);
  document.title = "Sectors · Trading";
  const prefs = { sort: "rs", dir: -1, rel: false, quad: "all", sector: "", rrgN: 10, ...store.get("secPrefs", {}) };
  const save = () => store.set("secPrefs", prefs);
  $view.innerHTML = `<div class="page-head"><h1>Sectors</h1>
      ${segmented([["us", "US"], ["india", "India"]], mkt, "mk")}
      ${segmented([["industry", "Industry groups"], ["sector", "Sectors"]], level, "lv")}</div><div id="sec">${LOADING}</div>`;
  $view.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(secHref(b.dataset.v, level)));
  $view.querySelectorAll(".lv button").forEach((b) => b.onclick = () => go(secHref(mkt, b.dataset.v)));
  const d = await api(`/api/sectors?market=${mkt}&level=${level}`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  const host = $view.querySelector("#sec");
  if (d.error || d.empty) {
    host.innerHTML = `<div class="empty"><b>${d.empty ? "No industry classification yet" : "Could not load sectors"}</b>
      <div class="muted">${d.empty ? "Fetch it once (a few minutes), from scripts/ with PYTHONPATH=.:" : esc(d.error)}</div>${d.command ? `<code>${esc(d.command)}</code>` : ""}</div>`;
    return;
  }
  const sectorsList = [...new Set(d.groups.map((g) => g.sector))].sort();
  const mret = d.market_ret, bench = d.bench;
  host.innerHTML = `
    <div class="sec-sub muted">${prettyDate(d.date)} · ${d.stocks.toLocaleString()} liquid stocks in ${d.groups.length} ${level === "industry" ? "industry groups" : "sectors"}
      · typical stock ${SEC_H.map((h) => `${h} <b class="${pctCls(mret[h])}">${pct1(mret[h])}</b>`).join(" ")}
      ${bench ? ` · ${esc(bench.label)} 3M <b class="${pctCls(bench["3M"])}">${pct1(bench["3M"])}</b> 12M <b class="${pctCls(bench["12M"])}">${pct1(bench["12M"])}</b>` : ""}
      ${d.updating ? ' <span class="tag watch">updating…</span>' : ""}</div>
    <div class="sec-top">
      <section class="sec-card"><div class="sec-card-h"><h3>Rotation</h3><span class="muted small" id="rrg-note"></span><span class="spacer"></span>
        ${level === "industry" ? `<label class="small muted">show <select id="rrgn">${[6, 10, 15, 20].map((n) => `<option ${n === prefs.rrgN ? "selected" : ""}>${n}</option>`).join("")}</select></label>` : ""}</div>
        <div id="rrg"></div></section>
      <section class="sec-card sec-doc"><h3>How to read this page</h3>
        ${["rs", "returns", "relative", "breadth", "rrg", "universe", "caveats"].map((k) => `<p>${esc(d.doc[k])}</p>`).join("")}
        <p><a href="#/playbook">Read the sector-analysis playbook →</a></p></section>
    </div>
    <div class="sec-filters">
      <label class="filter"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input id="sf" placeholder="Filter groups" spellcheck="false"></label>
      ${level === "industry" ? `<select id="ssec"><option value="">All sectors</option>${sectorsList.map((x) => `<option ${x === prefs.sector ? "selected" : ""}>${esc(x)}</option>`).join("")}</select>` : ""}
      <div class="chips" id="squad">${["all", ...QUADS].map((q) => `<button class="chip ${q === prefs.quad ? "on" : ""}" data-q="${q}">${q === "all" ? "All" : q}<span>${q === "all" ? d.groups.length : d.groups.filter((g) => g.quadrant === q).length}</span></button>`).join("")}</div>
      <span class="spacer"></span>
      <label class="check"><input type="checkbox" id="srel" ${prefs.rel ? "checked" : ""}> Returns vs the typical stock</label>
    </div>
    <div id="stbl"></div>`;
  let text = "", hot = null;
  const shown = () => {
    let gs = d.groups.filter((g) => (prefs.quad === "all" || g.quadrant === prefs.quad) && (!prefs.sector || level !== "industry" || g.sector === prefs.sector)
      && (!text || g.group.toLowerCase().includes(text) || g.sector.toLowerCase().includes(text) || g.leaders.some((l) => l.symbol.toLowerCase().includes(text))));
    const v = (g) => prefs.sort === "rs" ? g.rs : prefs.sort === "drs" ? (g.rs ?? 0) - (g.rs_prev ?? g.rs ?? 0) : prefs.sort === "group" ? g.group
      : prefs.sort === "n" ? g.n : prefs.sort === "above50" ? g.above50 : prefs.sort === "above200" ? g.above200 : prefs.sort === "hl" ? g.highs - g.lows
      : (prefs.rel ? g.rel : g.ew)[prefs.sort];
    return gs.sort((a, b) => { const x = v(a), y = v(b); if (x == null) return 1; if (y == null) return -1; return (typeof x === "string" ? x.localeCompare(y) : x - y) * prefs.dir; });
  };
  const drawRrg = () => {
    const gs = shown(), n = level === "sector" ? gs.length : Math.min(prefs.rrgN, gs.length);
    $view.querySelector("#rrg").innerHTML = rrgSvg(gs.slice(0, n), hot);
    $view.querySelector("#rrg-note").textContent = level === "sector" ? "weekly, last 8 weeks" : `first ${n} rows of the table below · weekly, last 8 weeks`;
    $view.querySelectorAll(".rrg-g").forEach((g) => { g.onclick = () => go(secHref(mkt, level, g.dataset.g)); });
  };
  const bar = (v) => v == null ? "" : `<span class="pbar"><i style="width:${(v * 100).toFixed(0)}%" class="${v >= 0.6 ? "hi" : v >= 0.4 ? "mid" : "lo"}"></i></span><span class="pnum">${(v * 100).toFixed(0)}%</span>`;
  const drawTable = () => {
    const gs = shown();
    const th = (k, t, cls = "num", title = "") => `<th class="${cls} ${prefs.sort === k ? "on" : ""}" data-k="${k}" title="${esc(title)}">${t}${prefs.sort === k ? (prefs.dir > 0 ? " ↑" : " ↓") : ""}</th>`;
    $view.querySelector("#stbl").innerHTML = `<div class="sect-wrap"><table class="sect"><thead><tr>
        ${th("rs", "RS", "num", "RS rating 1–99 across groups")}${th("drs", "Δ 1M", "num", "Change in RS rating over the last month")}
        ${th("group", level === "industry" ? "Industry group" : "Sector", "")}${th("n", "Stocks")}
        ${SEC_H.map((h) => th(h, h, "num", prefs.rel ? "Equal-weight return minus the typical stock's" : "Equal-weight return")).join("")}
        ${th("above50", "> 50D", "", "% of members above their 50-day average")}${th("above200", "> 200D", "", "% of members above their 200-day average")}
        ${th("hl", "Highs / lows", "num", "Members at a new 52-week closing high / low")}<th>Rotation</th><th>RS line 6M</th><th>Leaders</th></tr></thead>
      <tbody>${gs.map((g) => {
        const dr = g.rs != null && g.rs_prev != null ? g.rs - g.rs_prev : null, r = prefs.rel ? g.rel : g.ew;
        return `<tr data-g="${esc(g.group)}"><td class="num">${rsBadge(g.rs)}</td>
          <td class="num ${dr == null ? "" : dr >= 10 ? "pos" : dr <= -10 ? "neg" : "muted"}">${dr == null ? "" : (dr > 0 ? "▲" : dr < 0 ? "▼" : "") + Math.abs(dr)}</td>
          <td class="gname"><b>${esc(g.group)}</b>${level === "industry" ? `<span class="muted sec-of">${esc(g.sector)}</span>` : ""}</td>
          <td class="num muted">${g.n}</td>
          ${SEC_H.map((h) => `<td class="num ${pctCls(r[h])}">${pct1(r[h])}</td>`).join("")}
          <td class="pc">${bar(g.above50)}</td><td class="pc">${bar(g.above200)}</td>
          <td class="num"><span class="pos">${g.highs}</span> / <span class="neg">${g.lows}</span></td>
          <td>${g.quadrant ? `<span class="qtag ${QUAD_CLS[g.quadrant]}">${g.quadrant}</span>` : ""}</td>
          <td>${sparkSvg(g.spark)}</td>
          <td class="ldr">${g.leaders.map((l) => `<a data-s="${esc(l.symbol)}" title="${esc(l.name || "")}">${esc(l.symbol.replace(/\.NS$/, ""))}</a>`).join("")}</td></tr>`;
      }).join("")}</tbody></table></div>
      ${gs.length ? "" : '<div class="empty"><b>No groups match</b></div>'}`;
    $view.querySelectorAll(".sect th[data-k]").forEach((t) => t.onclick = () => {
      const k = t.dataset.k;
      if (prefs.sort === k) prefs.dir = -prefs.dir; else { prefs.sort = k; prefs.dir = k === "group" ? 1 : -1; }
      save(); drawTable(); drawRrg();
    });
    $view.querySelectorAll(".sect tbody tr").forEach((tr) => {
      tr.onclick = (e) => {
        const a = e.target.closest(".ldr a");
        if (a) { const g = d.groups.find((x) => x.group === tr.dataset.g); openChartFromList(mkt, a.dataset.s, g.leaders.map((l) => l.symbol), `${g.group} leaders`, location.hash); return; }
        go(secHref(mkt, level, tr.dataset.g));
      };
      tr.onmouseenter = () => { hot = tr.dataset.g; $view.querySelectorAll(".rrg-g").forEach((g) => g.classList.toggle("on", g.dataset.g === hot)); };
    });
  };
  const redraw = () => { drawTable(); drawRrg(); };
  $view.querySelector("#sf").oninput = (e) => { text = e.target.value.trim().toLowerCase(); redraw(); };
  $view.querySelector("#ssec")?.addEventListener("change", (e) => { prefs.sector = e.target.value; save(); redraw(); });
  $view.querySelector("#squad").onclick = (e) => { const b = e.target.closest("[data-q]"); if (!b) return; prefs.quad = b.dataset.q; save();
    $view.querySelectorAll("#squad .chip").forEach((c) => c.classList.toggle("on", c === b)); redraw(); };
  $view.querySelector("#srel").onchange = (e) => { prefs.rel = e.target.checked; save(); drawTable(); };
  $view.querySelector("#rrgn")?.addEventListener("change", (e) => { prefs.rrgN = +e.target.value; save(); drawRrg(); });
  redraw();
}

async function sectorGroupPage(alive, mkt, level, group) {
  document.title = `${group} · Sectors · Trading`;
  $view.innerHTML = LOADING;
  const d = await api(`/api/sectors/group?market=${mkt}&level=${level}&group=${encodeURIComponent(group)}`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  if (d.error) { $view.innerHTML = `<div class="empty"><b>${esc(group)}</b><div class="muted">${esc(d.error)}</div><a href="${secHref(mkt, level)}">Back to sectors</a></div>`; return; }
  const g = d.group, dr = g.rs != null && g.rs_prev != null ? g.rs - g.rs_prev : null;
  const ret = (o, h) => `<td class="num ${pctCls(o[h])}">${pct1(o[h])}</td>`;
  $view.innerHTML = `<div class="page-head"><a class="muted" href="${secHref(mkt, level)}">← Sectors</a>
      <h1>${esc(g.group)}</h1>${level === "industry" ? `<a class="muted" href="${secHref(mkt, "sector", g.sector)}">${esc(g.sector)}</a>` : ""}
      <span class="mkt">${MKT_BADGE[mkt]}</span>${rsBadge(g.rs)}${dr != null ? `<span class="${dr >= 10 ? "pos" : dr <= -10 ? "neg" : "muted"}">${dr > 0 ? "▲" : dr < 0 ? "▼" : ""}${Math.abs(dr)} in a month</span>` : ""}
      ${g.quadrant ? `<span class="qtag ${QUAD_CLS[g.quadrant]}">${g.quadrant}</span>` : ""}<span class="spacer"></span>
      <button class="ghost" id="towl">Add top 10 to a watchlist…</button></div>
    <div class="sec-top">
      <section class="sec-card"><div class="sec-card-h"><h3>Group vs the typical stock</h3><span class="muted small">equal-weight, rebased to 100 a year ago · lower pane: RS line</span></div><div id="gchart" class="gchart"></div></section>
      <section class="sec-card">
        <h3>Returns</h3>
        <table class="sect mini"><thead><tr><th></th>${SEC_H.map((h) => `<th class="num">${h}</th>`).join("")}</tr></thead><tbody>
          <tr><td>Equal-weight (typical member)</td>${SEC_H.map((h) => ret(g.ew, h)).join("")}</tr>
          <tr><td>Cap-weight (big names)</td>${SEC_H.map((h) => ret(g.cw, h)).join("")}</tr>
          <tr><td class="muted">Typical stock (market)</td>${SEC_H.map((h) => ret(d.market_ret, h)).join("")}</tr>
          <tr><td>Group vs market</td>${SEC_H.map((h) => ret(g.rel, h)).join("")}</tr></tbody></table>
        <h3>Breadth</h3>
        <div class="kvs"><span>Members</span><b>${g.n}</b><span>Above 50-day average</span><b>${g.above50 != null ? (g.above50 * 100).toFixed(0) + "%" : "—"}</b>
          <span>Above 200-day average</span><b>${g.above200 != null ? (g.above200 * 100).toFixed(0) + "%" : "—"}</b>
          <span>Up over 3 months</span><b>${(g.up3m * 100).toFixed(0)}%</b>
          <span>New 52-week highs / lows</span><b><span class="pos">${g.highs}</span> / <span class="neg">${g.lows}</span></b></div>
        <p class="muted small">${esc(d.doc.returns)}</p>
      </section></div>
    ${d.industries.length ? `<section class="sec-card"><h3>Industry groups in ${esc(g.group)}</h3><table class="sect mini"><thead><tr><th class="num">RS</th><th>Industry</th><th class="num">Stocks</th>${SEC_H.map((h) => `<th class="num">${h}</th>`).join("")}<th>Rotation</th></tr></thead>
      <tbody>${d.industries.map((x) => `<tr data-g="${esc(x.group)}"><td class="num">${rsBadge(x.rs)}</td><td><b>${esc(x.group)}</b></td><td class="num muted">${x.n}</td>${SEC_H.map((h) => ret(x.ew, h)).join("")}
        <td>${x.quadrant ? `<span class="qtag ${QUAD_CLS[x.quadrant]}">${x.quadrant}</span>` : ""}</td></tr>`).join("")}</tbody></table></section>` : ""}
    <section class="sec-card"><div class="sec-card-h"><h3>Members, strongest first</h3><span class="muted small">ranked by the RS composite across all ${d.members.length ? "" : ""}stocks · click a row for its chart</span></div><div id="gmem"></div></section>`;
  $view.querySelectorAll(".sect.mini tr[data-g]").forEach((tr) => tr.onclick = () => go(secHref(mkt, "industry", tr.dataset.g)));

  // chart: group vs market (rebased) and the RS line
  const el_ = $view.querySelector("#gchart");
  const chart = LC.createChart(el_, { autoSize: true, ...CHART_THEME, handleScroll: false, handleScale: false, crosshair: { mode: LC.CrosshairMode.Normal } });
  const s0 = g.series[0];
  chart.addSeries(LC.LineSeries, { color: "#2962ff", lineWidth: 2, priceLineVisible: false, title: g.group.slice(0, 24) })
    .setData(g.series.map((p) => ({ time: p.time, value: (100 * p.group) / s0.group })));
  chart.addSeries(LC.LineSeries, { color: "#787b86", lineWidth: 1.5, priceLineVisible: false, title: "Typical stock" })
    .setData(g.series.map((p) => ({ time: p.time, value: (100 * p.market) / s0.market })));
  chart.addSeries(LC.LineSeries, { color: "#ff9800", lineWidth: 1.5, priceLineVisible: false, title: "RS line" }, 1)
    .setData(g.series.map((p) => ({ time: p.time, value: (100 * p.group / p.market) / (s0.group / s0.market) })));
  chart.panes()[1]?.setHeight(110);
  chart.timeScale().fitContent();
  { const prev = cleanup; cleanup = () => { chart.remove(); prev(); }; }

  // members
  const cols = ["rank", "symbol", "name", "rs", "1M %", "3M %", "6M %", "12M %", "off 52w high", "> 50D", "> 200D", "quality", "last"];
  const p100 = (v) => (v == null ? null : +(v * 100).toFixed(1));
  const rows = d.members.map((m, i) => [i + 1, m.symbol, m.name || "", m.rs, p100(m["1M"]), p100(m["3M"]), p100(m["6M"]), p100(m["12M"]),
    p100(m.from_high), m.above50, m.above200, m.quality != null ? Math.round(m.quality) : null, m.last]);
  dataTable($view.querySelector("#gmem"), cols, rows, {
    name: "sector_members", sort: ["rank", 1],
    rowClick: (row, visible) => openChartFromList(mkt, row[1], visible.map((r) => r[1]), `${g.group} · members`, location.hash),
  });

  $view.querySelector("#towl").onclick = async () => {
    const name = await askText("Add the top 10 members to a watchlist", `${g.group} (${MKT_BADGE[mkt]})`, "Watchlist name");
    if (!name?.trim()) return;
    try {
      const lists = await WL.lists();
      let l = lists.find((x) => !x.builtin && x.name.toLowerCase() === name.trim().toLowerCase());
      const id = l ? l.id : (await WL.create(name.trim())).id;
      for (const m of d.members.slice(0, 10)) await WL.add(id, m.symbol, mkt);
      toast(`Added ${Math.min(10, d.members.length)} stocks to “${name.trim()}”`, "ok", { label: "Open", fn: () => go(`#/watchlist/${id}`) });
    } catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
  };
}

// ------------------------------------------------------------ breadth page

// which direction is "strong" for each breadth column (for shading and gauges)
const BR_GOOD_HIGH = new Set(["adv", "up4", "highs", "pct5", "pct50", "up25m", "up50m"]);

async function breadthPage(alive, mkt) {
  mkt = mkt === "us" || mkt === "india" ? mkt : store.get("brMarket", "india");
  store.set("brMarket", mkt);
  document.title = "Breadth · Trading";
  $view.innerHTML = LOADING;
  const b = await api(`/api/breadth?market=${mkt}`);
  if (!alive()) return;
  const head = `<div class="page-head"><h1>Market breadth</h1>${segmented([["india", "India"], ["us", "US"]], mkt, "mk")}
    ${b.date ? `<span class="muted">${prettyDate(b.date)} · the ${b.breadth_n?.toLocaleString()} most-traded stocks</span>` : ""}
    ${b.updating ? `<span class="tag watch" title="Newer prices exist; today's figures are being computed in the background">updating…</span>` : ""}</div>`;
  if (b.empty) {
    $view.innerHTML = head + `<div class="empty"><b>No breadth history yet for ${mkt.toUpperCase()}</b>
      <div class="muted">${b.updating ? "It is being computed now — reload in a few minutes, or run it yourself:" : "Compute it once (a few minutes), from scripts/ with PYTHONPATH=.:"}</div><code>${esc(b.command)}</code></div>`;
    $view.querySelectorAll(".mk button").forEach((x) => x.onclick = () => go(`#/breadth/${x.dataset.v}`));
    return;
  }
  const pc = (v, d = 1) => (v == null ? "" : `${v > 0 ? "+" : ""}${(v * 100).toFixed(d)}%`);
  const idxLine = b.index_keys.map((k) => { const x = b.indexes[k]; return `${esc(x.label)} <b class="${x.day >= 0 ? "pos" : "neg"}">${pc(x.day, 2)}</b>`; }).join(" · ");
  const gauge = (p) => (p == null ? "" : `<div class="gauge"><i style="left:${Math.max(0, Math.min(100, p)).toFixed(1)}%"></i></div><div class="gauge-l"><span>low</span><span>high</span></div>`);
  const card = (c) => `<div class="bcard"><div class="bq">${esc(c.title)}</div><div class="bv">${esc(c.value)}</div>${c.sub ? `<div class="muted small">${esc(c.sub)}</div>` : ""}
    ${gauge(c.pct)}<p class="bt">${esc(c.text)}</p>
    <table class="btab"><thead><tr><th></th>${c.compare.cols.map((x) => `<th>${esc(x)}</th>`).join("")}</tr></thead>
    <tbody>${c.compare.rows.map((r) => `<tr>${r.map((v, i) => (i ? `<td>${esc(String(v))}</td>` : `<td class="muted">${esc(v)}</td>`)).join("")}</tr>`).join("")}</tbody></table></div>`;
  const shade = (col, v) => {
    const band = b.bands[col]; if (v == null || !band) return "";
    const hi = v >= band[1], lo = v <= band[0];
    if (!hi && !lo) return "";
    return (hi === BR_GOOD_HIGH.has(col)) ? "s-good" : "s-bad";
  };
  const idxCols = b.index_keys.map((k) => b.indexes[k].label);
  const t30 = `<div class="tablewrap"><table class="data b30"><thead><tr><th>Date</th><th class="num">Rising</th><th class="num">Falling</th><th class="num">Up 4%+</th><th class="num">Down 4%+</th>
      <th class="num">52w highs</th><th class="num">52w lows</th><th class="num">> 5 DMA</th><th class="num">> 50 DMA</th><th class="num">Month +25%</th><th class="num">Month −25%</th>
      ${idxCols.map((l) => `<th class="num">${esc(l)}</th><th class="num">Month</th>`).join("")}<th class="num">Expected</th><th class="num">Actual</th><th class="num">Exp ÷ act</th></tr></thead>
    <tbody>${b.last30.map((r) => `<tr><td>${prettyDate(r.date)}</td>
      ${["adv", "dec", "up4", "dn4", "highs", "lows"].map((c) => `<td class="num ${shade(c, r[c])}">${r[c] ?? ""}</td>`).join("")}
      ${["pct5", "pct50"].map((c) => `<td class="num ${shade(c, r[c])}">${r[c] == null ? "" : r[c].toFixed(0) + "%"}</td>`).join("")}
      ${["up25m", "dn25m"].map((c) => `<td class="num ${shade(c, r[c])}">${r[c] ?? ""}</td>`).join("")}
      ${b.index_keys.map((k) => { const x = r[k]; return x ? `<td class="num">${fmt(+x.close.toFixed(0))} <span class="${x.day >= 0 ? "pos" : "neg"}">${pc(x.day, 2)}</span></td><td class="num ${x.month >= 0 ? "pos" : "neg"}">${pc(x.month)}</td>` : "<td></td><td></td>"; }).join("")}
      ${r.vol ? `<td class="num">${r.vol.exp.toFixed(1)}</td><td class="num">${r.vol.act.toFixed(1)}</td><td class="num">${r.vol.ratio.toFixed(2)}</td>` : "<td></td><td></td><td></td>"}</tr>`).join("")}</tbody></table></div>`;
  const sx = b.sectors;
  const secRows = (sx.sectors || []).map((x, i) => `<tr class="sec" data-i="${i}"><td>▸ ${esc(x.sector)}</td><td class="num">${x.stocks}</td>
      <td class="num ${x.r3m_vs >= 0 ? "pos" : "neg"}">${pc(x.r3m_vs)}</td><td class="num ${x.r1m_vs >= 0 ? "pos" : "neg"}">${pc(x.r1m_vs)}</td>
      <td class="num ${x.above50 >= 0.5 ? "s-good" : x.above50 < 0.2 ? "s-bad" : ""}">${(x.above50 * 100).toFixed(0)}%</td><td class="num">${x.highs}</td><td class="num">${x.lows}</td></tr>
    <tr class="members" data-for="${i}" hidden><td colspan="7"><div class="wl">${x.members.map((m) => `<a href="#/chart/${mkt}/${encodeURIComponent(m.symbol)}" title="3M ${pc(m.r3m)} · 1M ${pc(m.r1m)}">${esc(m.symbol)} <span class="${m.r3m >= 0 ? "pos" : "neg"}">${pc(m.r3m, 0)}</span></a>`).join("")}</div></td></tr>`).join("");

  $view.innerHTML = head + `<div class="bsub">Today · ${idxLine}</div>
    <div class="bcards">${b.cards.map(card).join("")}</div>
    <p class="muted small">Each reading is ranked against every trading day since 2015 and compared with a week, a month and three months ago. Slow changes matter most: markets rarely turn in a day.</p>
    ${b.events.length ? `<h2>What changed in the last 5 sessions</h2><div class="bevents">${b.events.map((e) => `<div><span class="muted">${prettyDate(e.date)}</span> ${esc(e.text)}</div>`).join("")}</div>` : ""}
    <h2>Charts <span class="seg brange">${["6M", "1Y", "3Y", "All"].map((r) => `<button data-r="${r}" class="${r === store.get("brRange", "1Y") ? "on" : ""}">${r}</button>`).join("")}</span></h2>
    <div class="bcharts">
      <div class="bchart"><div class="bct">${esc(idxCols.slice(0, 2).join(" and "))}</div><div class="bc" id="bc-idx"></div></div>
      <div class="bchart"><div class="bct">Stocks at one-year highs minus lows <span class="muted">· day, and 10-day average</span></div><div class="bc" id="bc-hl"></div></div>
      <div class="bchart"><div class="bct">Stocks above their 50-day average <span class="muted">· 30% washout, 70% strong</span></div><div class="bc" id="bc-50"></div></div>
      <div class="bchart"><div class="bct">Rising minus falling stocks <span class="muted">· 10-day average</span></div><div class="bc" id="bc-ad"></div></div>
    </div>
    <h2>Sectors: where the strength is?</h2>
    ${sx.sectors?.length ? `<div class="tablewrap"><table class="data bsec"><thead><tr><th>Sector</th><th class="num">Stocks</th><th class="num">3M vs avg stock</th><th class="num">1M vs avg stock</th>
      <th class="num">Above 50 DMA</th><th class="num">52w highs, 2 wks</th><th class="num">52w lows, 2 wks</th></tr></thead><tbody>${secRows}</tbody></table></div>
      <p class="muted small">Click a sector for its stocks, strongest over 3 months first. Sector known for ${sx.covered} of the ${sx.total} stocks.</p>` : `<p class="muted">Sector data not available yet.</p>`}
    <h2>The last 30 days</h2>${t30}
    <p class="muted small">Shading marks an unusual day for that reading: green for its strongest fifth since 2015, red for its weakest fifth.</p>
    <details class="qhow"><summary>How this page works</summary><div class="md qmd">
      <p>How the ${b.breadth_n.toLocaleString()} most-traded stocks (by 20-day average turnover, common stocks only — ETFs and funds are excluded) are doing as a group.
      It helps judge how risky the market is, <b>not</b> which way it will go.</p>
      <ul class="sd-list"><li><b>52-week highs / lows</b>: today's high (low) is the highest (lowest) of the last 252 sessions, for stocks with roughly a year of history.</li>
      <li><b>Above the 5 / 50 DMA</b>: the close is above its 5- / 50-day simple average. Below 30% on the 50-day is a washout; above 70% is broad strength.</li>
      <li><b>Rising / falling</b>: the close is above / below the previous close; <b>up / down 4%+</b> are the day's big movers.</li>
      <li><b>Sectors</b>: median 3- and 1-month change of the sector's stocks minus the median of all of them; "in an uptrend" = most of its stocks above the 50-day average.</li>
      <li><b>Options, expected vs actual</b>: ${esc(b.vol_label)} (the market's expected annualised move) against the index's realised volatility over the last 20 sessions. A ratio well above 1 means options are dear.</li>
      <li><b>Ranks</b>: "only N in 100 days since 2015" compares today with every trading day since 2015 (two-week readings with every two-week stretch).</li></ul>
      <p class="muted small">Computed from your own daily prices by <code>python3 -m jobs run breadth --market ${mkt}</code>; the page tops it up automatically when newer prices arrive. No intraday updates and no event calendar.</p>
    </div></details>`;
  $view.querySelectorAll(".mk button").forEach((x) => x.onclick = () => go(`#/breadth/${x.dataset.v}`));
  $view.querySelector(".bsec")?.addEventListener("click", (e) => {
    const tr = e.target.closest("tr.sec"); if (!tr) return;
    const m = $view.querySelector(`tr.members[data-for="${tr.dataset.i}"]`); m.hidden = !m.hidden;
    tr.firstElementChild.textContent = (m.hidden ? "▸ " : "▾ ") + tr.firstElementChild.textContent.slice(2);
  });

  // charts
  const charts = [];
  const mk = (id) => { const c = LC.createChart($view.querySelector(id), { autoSize: true, ...CHART_THEME, handleScroll: false, handleScale: false,
    crosshair: { mode: LC.CrosshairMode.Normal }, rightPriceScale: { borderColor: "#2a2e39" }, leftPriceScale: { visible: false, borderColor: "#2a2e39" } }); charts.push(c); return c; };
  const k0 = b.index_keys[0], k1 = b.index_keys[b.index_keys.length - 1];
  const ci = mk("#bc-idx");
  ci.addSeries(LC.LineSeries, { color: "#2962ff", lineWidth: 2, priceLineVisible: false, title: b.indexes[k0].label }).setData(b.charts[k0]);
  if (k1 !== k0) { ci.applyOptions({ leftPriceScale: { visible: true } }); ci.addSeries(LC.LineSeries, { color: "#ff9800", lineWidth: 1, priceLineVisible: false, priceScaleId: "left", title: b.indexes[k1].label }).setData(b.charts[k1]); }
  const ch = mk("#bc-hl");
  ch.addSeries(LC.HistogramSeries, { priceLineVisible: false, lastValueVisible: false }).setData(b.charts.hl.map((p) => ({ ...p, color: p.value >= 0 ? "rgba(38,166,154,.45)" : "rgba(239,83,80,.45)" })));
  ch.addSeries(LC.LineSeries, { color: "#e0e0e0", lineWidth: 1.5, priceLineVisible: false, title: "10d" }).setData(b.charts.hl10);
  const c5 = mk("#bc-50");
  const s5 = c5.addSeries(LC.AreaSeries, { lineColor: "#26a69a", topColor: "rgba(38,166,154,.25)", bottomColor: "rgba(38,166,154,0)", lineWidth: 1.5, priceLineVisible: false });
  s5.setData(b.charts.pct50);
  [[30, "#ef5350"], [70, "#26a69a"]].forEach(([v, c]) => s5.createPriceLine({ price: v, color: c, lineStyle: 2, lineWidth: 1, axisLabelVisible: true }));
  const ca = mk("#bc-ad");
  const sa = ca.addSeries(LC.BaselineSeries, { baseValue: { type: "price", price: 0 }, topLineColor: "#26a69a", bottomLineColor: "#ef5350",
    topFillColor1: "rgba(38,166,154,.25)", topFillColor2: "rgba(38,166,154,0)", bottomFillColor1: "rgba(239,83,80,0)", bottomFillColor2: "rgba(239,83,80,.25)", lineWidth: 1.5, priceLineVisible: false });
  sa.setData(b.charts.ad10);
  const setRange = (r) => {
    const end = b.date, start = r === "All" ? null : new Date(Date.parse(end) - { "6M": 182, "1Y": 365, "3Y": 1095 }[r] * 864e5).toISOString().slice(0, 10);
    charts.forEach((c) => { if (start) c.timeScale().setVisibleRange({ from: start, to: end }); else c.timeScale().fitContent(); });
  };
  const rangeBar = $view.querySelector(".brange");
  rangeBar.onclick = (e) => { const x = e.target.closest("[data-r]"); if (!x) return; store.set("brRange", x.dataset.r);
    rangeBar.querySelectorAll("button").forEach((y) => y.classList.toggle("on", y === x)); setRange(x.dataset.r); };
  requestAnimationFrame(() => setRange(store.get("brRange", "1Y")));
  cleanup = () => charts.forEach((c) => c.remove());
}

// ------------------------------------------------------------ quality page

/** small multi-field form in the app's style (resolves to null on cancel) */
function askFields(title, fields) {
  return new Promise((resolve) => {
    const m = el(`<div class="smodal"><div class="smodal-card settings"><div class="sm-head"><b>${esc(title)}</b></div>
      <div class="sm-form">${fields.map((f) => `<label><span>${esc(f.label)}</span><input data-k="${f.key}" type="${f.type || "text"}" step="any"
        value="${esc(f.value ?? "")}" placeholder="${esc(f.placeholder || "")}"></label>`).join("")}</div>
      <div class="sm-foot"><span class="spacer"></span><button class="ghost" data-a="cancel">Cancel</button><button class="primary" data-a="ok">Save</button></div></div></div>`);
    document.body.append(m);
    const inputs = [...m.querySelectorAll("input")]; inputs[0].focus();
    const done = (ok) => { const v = ok ? Object.fromEntries(inputs.map((i) => [i.dataset.k, i.value])) : null; m.remove(); resolve(v); };
    m.onclick = (e) => { const a = e.target.closest("button")?.dataset.a; if (a === "ok") done(true); if (a === "cancel" || e.target === m) done(false); };
    m.onkeydown = (e) => { e.stopPropagation(); if (e.key === "Enter") done(true); if (e.key === "Escape") done(false); };
  });
}
const zoneClass = (z) => (z === "BUY ZONE" ? "trade" : z === "ACCUMULATE" ? "watch" : z === "AT YOUR PRICE" ? "trade" : "");
const valueClass = (v) => (v === "Attractive" ? "trade" : v === "Fair" ? "watch" : v === "Expensive" ? "avoid" : "");
const ICON_STAR = '<svg viewBox="0 0 20 20"><path d="M10 2.5l2.3 4.8 5.2.6-3.9 3.6 1 5.2-4.6-2.6-4.6 2.6 1-5.2L2.5 7.9l5.2-.6z"/></svg>';
const QCMD = (m, syms) => `python3 -m fundamentals.quality ${syms ? `--market ${m} --symbols ${syms}` : "--tracked"}`;

async function qualityPage(alive, mkt) {
  mkt = mkt || store.get("qMarket", "all");
  store.set("qMarket", mkt);
  document.title = "Quality · Trading";
  $view.innerHTML = LOADING;
  const [rows, crit] = await Promise.all([api(`/api/quality${mkt === "all" ? "" : `?market=${mkt}`}`), api("/api/quality/criteria")]);
  if (!alive()) return;
  let view = store.get("qView", "tracked");
  if (view === "tracked" && !rows.some((r) => r.tracked)) view = "all";
  $view.innerHTML = `<div class="page-head"><h1>Quality companies</h1>${segmented([["all", "All"], ["us", "US"], ["india", "India"]], mkt, "mk")}
      <span class="spacer"></span>
      <form class="wl-add" autocomplete="off">
        ${mkt === "all" ? `<select id="qm" title="Market"><option value="us">US</option><option value="india">India</option></select>` : ""}
        <div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input id="qs" placeholder="Track a company" spellcheck="false"><ul hidden></ul></div>
        <input id="qt" type="number" step="any" placeholder="Buy below (optional)" title="Your own buy-below price: the row is flagged AT YOUR PRICE once the close reaches it">
        <input id="qn" placeholder="Note (optional)"><button class="primary" type="submit">Track</button>
      </form></div>
    <div class="chips" id="qchips"></div><div id="qpending"></div><div id="qt-host"></div>
    <details class="qhow"><summary>How the signals work</summary><div class="md qmd">
      <p><b>${esc(crit.thesis)}</b></p>
      <h3>1 · Is it a great business? <span class="muted small">Quality score out of 100 — ${crit.high_quality_score}+ with no red flag counts as high quality</span></h3>
      <table class="dtab"><tbody>${crit.quality_tests.map((t) => `<tr><td class="num">${t.points} pts</td><td>${esc(t.text)}</td></tr>`).join("")}</tbody></table>
      <p class="muted small">F = Piotroski F-score (0–9): nine year-on-year health checks, shown alongside.</p>
      <h3>2 · Is the price right? <span class="muted small">recomputed from every new close</span></h3>
      <ul class="sd-list">${crit.price_rules.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>
      <h3>Caveats</h3><ul class="sd-list">${crit.caveats.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>
      <p class="muted small">Refresh the fundamentals offline (from <code>scripts/</code>, with <code>PYTHONPATH=.</code>): <code>python3 -m fundamentals.quality --market us --top 500</code> · <code>--market india --top 300</code> · <code>--tracked</code>. Statements older than 30 days are re-fetched.</p>
    </div></details>`;
  $view.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(`#/quality/${b.dataset.v}`));

  // track form
  const mSel = $view.querySelector("#qm"), sIn = $view.querySelector("#qs"), tIn = $view.querySelector("#qt"), nIn = $view.querySelector("#qn");
  const addMarket = () => (mSel ? mSel.value : mkt);
  if (mSel) mSel.value = store.get("lastMarket", "us");
  const wire = () => symbolSearch(sIn, $view.querySelector(".wl-add ul"), addMarket(), (s) => { sIn.value = s; tIn.focus(); });
  wire(); if (mSel) mSel.onchange = wire;
  $view.querySelector(".wl-add").onsubmit = async (e) => {
    e.preventDefault();
    const sym = sIn.value.trim().toUpperCase(); if (!sym) { sIn.focus(); return; }
    try {
      const r = await api("/api/quality/watch", jsonReq("POST", { market: addMarket(), symbol: sym, note: nIn.value.trim() || null, target: tIn.value ? +tIn.value : null }));
      toast(`Tracking ${r.symbol}`, "ok"); store.set("qView", "tracked"); route();
    } catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
  };

  const high = (r) => !!r.high_quality;  // score threshold AND no red flag (decided server-side)
  const views = [
    ["tracked", "Tracked", rows.filter((r) => r.tracked)],
    ["buy", "Buy zone", rows.filter((r) => r.zone === "BUY ZONE")],
    ["yourprice", "At your price", rows.filter((r) => r.at_your_price)],
    ["accumulate", "Accumulate", rows.filter((r) => r.zone === "ACCUMULATE")],
    ["high", "High quality", rows.filter(high)],
    ["all", "All scored", rows.filter((r) => r.quality != null)],
  ];
  const pct = (v) => (v == null ? "" : `${(v * 100).toFixed(Math.abs(v) < 0.1 ? 1 : 0)}%`);
  const num = (v) => (v == null ? "" : fmt(+v.toFixed(2)));
  const draw = () => {
    $view.querySelector("#qchips").innerHTML = views.map(([k, t, xs]) => `<button class="chip ${k === view ? "on" : ""} ${k === "buy" || k === "yourprice" ? "trade" : k === "accumulate" ? "watch" : ""}" data-v="${k}">${t}<span>${xs.length}</span></button>`).join("");
    const shown = views.find((v) => v[0] === view)[2];
    const pending = shown.filter((r) => r.tracked && r.quality == null);
    $view.querySelector("#qpending").innerHTML = pending.length ? `<div class="qpend"><b>${pending.length} tracked compan${pending.length > 1 ? "ies have" : "y has"} no fundamentals yet</b> —
      price signals are shown; to score ${pending.length > 1 ? "them" : "it"}, run from <code>scripts/</code>: <code>${esc(QCMD())}</code>
      <button class="ghost copy" data-c="PYTHONPATH=. ${esc(QCMD())}">Copy</button></div>` : "";
    const host = $view.querySelector("#qt-host");
    if (!shown.length) {
      host.innerHTML = `<div class="empty"><b>${view === "tracked" ? "You're not tracking any companies yet" : "No companies in this view"}</b>
        <div class="muted">${view === "tracked" ? "Add one with “Track a company” above, or ★ any row under High quality / All scored." : rows.some((r) => r.quality != null) ? "Try another view." : "Run the fundamentals script to score companies (see “How the signals work”)."}</div></div>`;
      return;
    }
    const cols = ["symbol", "name", "market", "sector", "quality", "f", "roic / roe", "rev growth", "eps growth", "op margin", "fcf conv", "net debt/ebitda",
      "last", "p/e", "p/e vs own", "fcf yield", "peg", "off 52w high", "vs 200d", "rsi", "value", "zone", "buy below", "signals", "note"];
    const data = shown.map((r) => [r.symbol, r.name || "", r.market.toUpperCase(), r.sector || "", r.quality, r.f_score ?? null,
      r.financial ? r.roe_avg : r.roic_avg, r.rev_cagr, r.eps_cagr, r.financial ? null : r.op_margin, r.financial ? null : r.fcf_conversion,
      r.net_cash ? -0.0001 : r.net_debt_ebitda, r.close, r.pe, r.pe_vs_own, r.fcf_yield, r.peg, r.drawdown, r.vs_200dma, r.rsi,
      r.value || (r.quality == null ? "pending" : ""), r.at_your_price ? "AT YOUR PRICE" : r.zone || "", r.target,
      [...(r.timing || []), ...(r.flags || [])].join(" · "), r.note || ""]);
    const P = (c) => [c, pct];
    dataTable(host, cols, data, {
      name: `quality_${mkt}_${view}`, sort: ["quality", -1],
      format: Object.fromEntries([...["roic / roe", "rev growth", "eps growth", "op margin", "fcf conv", "p/e vs own", "fcf yield", "off 52w high", "vs 200d"].map(P),
        ["net debt/ebitda", (v) => (v === -0.0001 ? "net cash" : num(v))], ["p/e", num], ["peg", num], ["rsi", (v) => (v == null ? "" : v.toFixed(0))],
        ["quality", (v) => (v == null ? "pending" : String(v))]]),
      signed: ["rev growth", "eps growth"], inverse: ["p/e vs own"],
      tags: { value: valueClass, zone: zoneClass },
      rowClass: (row) => (shown.find((x) => x.symbol === row[0] && x.market === row[2].toLowerCase())?.high_quality ? "hq" : ""),
      rowClick: (row, visible) => openChartFromList(row[2].toLowerCase(), row[0], visible.filter((x) => x[2] === row[2]).map((x) => x[0]), "Quality", location.hash),
      actions: [
        { key: "track", title: "Track / stop tracking", icon: ICON_STAR, fn: async (row) => {
          const r = shown.find((x) => x.symbol === row[0] && x.market === row[2].toLowerCase());
          if (r.tracked) { await api(`/api/quality/watch?market=${r.market}&symbol=${encodeURIComponent(r.symbol)}`, { method: "DELETE" }); toast(`Stopped tracking ${r.symbol}`, "ok"); }
          else { await api("/api/quality/watch", jsonReq("POST", { market: r.market, symbol: r.symbol })); toast(`Tracking ${r.symbol}`, "ok"); }
          route();
        } },
        { key: "edit", title: "Set your buy-below price and note", icon: ICON_NOTE, fn: async (row) => {
          const r = shown.find((x) => x.symbol === row[0] && x.market === row[2].toLowerCase());
          const v = await askFields(`${r.symbol} — your price`, [
            { key: "target", label: "Buy below", type: "number", value: r.target ?? "", placeholder: r.close ? `last ${fmt(r.close)}` : "" },
            { key: "note", label: "Note", value: r.note ?? "", placeholder: "why you like it" }]);
          if (!v) return;
          if (!r.tracked) await api("/api/quality/watch", jsonReq("POST", { market: r.market, symbol: r.symbol }));
          await api("/api/quality/watch", jsonReq("PUT", { market: r.market, symbol: r.symbol, note: v.note.trim() || null, target: v.target ? +v.target : null }));
          toast("Saved", "ok"); route();
        } },
      ],
    });
    // the star shows filled for tracked rows
    host.querySelectorAll("tbody tr[data-r]").forEach((tr, i) => {
      const row = data.find((d) => d[0] === tr.firstElementChild.textContent);
      const r = row && shown.find((x) => x.symbol === row[0] && x.market === row[2].toLowerCase());
      if (r?.tracked) tr.querySelector('[data-act="track"]')?.classList.add("starred");
    });
  };
  $view.querySelector("#qchips").onclick = (e) => { const b = e.target.closest("[data-v]"); if (b) { view = b.dataset.v; store.set("qView", view); draw(); } };
  $view.querySelector("#qpending").onclick = (e) => { const b = e.target.closest(".copy"); if (b) navigator.clipboard.writeText(b.dataset.c).then(() => toast("Command copied", "ok"), () => {}); };
  draw();
}

// ------------------------------------------------------------ strategies

// the strategy prose uses light markdown (**bold**, `code`, *italic*); escape first, then format
const mdInline = (t) => esc(t).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/(^|[^*])\*([^*\s][^*]*?)\*/g, "$1<i>$2</i>");
const statusClass = (t) => (/no demonstrated edge|not validated|no edge|untested|does not beat|did not beat|losing|negative/i.test(t) ? "watch" : /beats|edge confirmed/i.test(t) ? "trade" : "");

async function strategiesPage(alive, key) {
  document.title = "Strategies · Trading";
  $view.innerHTML = LOADING;
  const list = await api("/api/strategies");
  if (!alive()) return;
  if (!list.some((x) => x.key === key)) key = list.some((x) => x.key === store.get("stratKey")) ? store.get("stratKey") : list[0].key;
  store.set("stratKey", key);
  const d = await api(`/api/strategies/${encodeURIComponent(key)}`);
  if (!alive()) return;
  document.title = `${d.name} · Strategies · Trading`;

  const navItem = (x) => `<a class="nav-item ${x.key === key ? "active" : ""}" href="#/strategies/${x.key}" title="${esc(x.status)}">
      <span><b class="sn">${esc(x.name)}</b><span class="muted small sk">${esc(x.key)}</span></span>${x.backtests ? `<span class="n" title="backtest reports">${x.backtests}</span>` : ""}</a>`;
  const groups = [["screener", "Screening strategies"], ["long-term", "Long-term investing"], ["benchmark", "Benchmark"]].map(([k, t]) => {
    const xs = list.filter((x) => x.kind === k);
    return xs.length ? `<div class="nav-h">${t}</div>${xs.map(navItem).join("")}` : "";
  }).join("");

  const sec = (id, title, body) => (body ? `<section class="sd-sec" id="sd-${id}"><h2>${title}</h2>${body}</section>` : "");
  const codeTable = (rows, head) => rows.length ? `<table class="dtab"><thead><tr><th>${head}</th><th>Rule</th></tr></thead><tbody>${rows.map((r) =>
    `<tr><td><code>${esc(r.code)}</code></td><td>${mdInline(r.text) || '<span class="neg">Not documented</span>'}</td></tr>`).join("")}</tbody></table>` : "";
  const ol = (xs) => (xs.length ? `<ol class="sd-list">${xs.map((x) => `<li>${mdInline(x)}</li>`).join("")}</ol>` : "");
  const ul = (xs) => (xs.length ? `<ul class="sd-list">${xs.map((x) => `<li>${mdInline(x)}</li>`).join("")}</ul>` : "");

  const sameAcross = d.params.every((p) => p.values.us === p.values.india);
  const params = d.params.length ? `<table class="dtab"><thead><tr><th>Parameter</th>${sameAcross ? "<th class='num'>Value</th>" : "<th class='num'>US</th><th class='num'>India</th>"}<th>Meaning</th></tr></thead><tbody>${
    d.params.map((p) => `<tr><td>${esc(p.label)}<div class="muted small"><code>${esc(p.source)}</code></div></td>${
      sameAcross ? `<td class="num">${esc(p.values.us)}</td>` : `<td class="num">${esc(p.values.us)}</td><td class="num">${esc(p.values.india)}</td>`}<td>${mdInline(p.meaning)}</td></tr>`).join("")}</tbody></table>
    <p class="muted small">Values are read live from the code and the market configs.</p>` : "";

  const pv = (x) => (x == null ? "" : x);
  const bts = d.backtests.length ? `<table class="dtab click"><thead><tr><th>Market</th><th>Run</th><th class="num">CAGR</th><th class="num">Excess CAGR</th><th class="num">Max DD</th><th class="num">Sharpe</th><th>Generated</th></tr></thead><tbody>${
    d.backtests.map((b) => { const s = b.summary || {};
      return `<tr data-href="#/reports/${b.id}"><td>${b.market.toUpperCase()}</td><td>${esc(b.run)}</td><td class="num">${esc(pv(s.cagr))}</td>
        <td class="num ${/^-/.test(s.excess_cagr || "") ? "neg" : s.excess_cagr ? "pos" : ""}">${esc(pv(s.excess_cagr))}</td><td class="num">${esc(pv(s.max_drawdown))}</td>
        <td class="num">${esc(pv(s.sharpe))}</td><td class="muted">${prettyDate(b.generated_at)}</td></tr>`; }).join("")}</tbody></table>`
    : `<p class="muted">No backtest reports loaded for this strategy yet.</p>`;
  const screens = d.kind === "screener" ? (d.screens.length ? `<div class="tiles">${d.screens.map((x) => `<a class="tile link" href="#/screening/${x.market}/${key}">
      <span>${x.market.toUpperCase()} · ${prettyDate(x.run)}</span><b>${x.tradeable} tradeable</b><span class="muted small">${x.watch} on watch · ${x.rows} screened</span></a>`).join("")}</div>`
    : `<p class="muted">No recorded screening run yet.</p>`) : "";

  const cmds = Object.entries(d.commands).map(([k, c]) => `<div class="cmd"><div class="muted small">${esc(k)}</div><pre><code>${esc(c)}</code></pre><button class="ghost copy" data-c="${esc(c)}">Copy</button></div>`).join("");
  const toc = [["overview", "Overview"], ["rules", d.gates.length ? "Rules" : ""], ["entry", d.entry_rules.length ? (d.kind === "long-term" ? "Price" : "Entry & exit") : ""], ["params", "Parameters"],
    ["decisions", d.decisions.length ? "Decisions" : ""], ["results", "Results"], ["commands", "Commands"], ["caveats", "Caveats"]].filter((t) => t[1]);

  $view.innerHTML = `<div class="rep-layout"><aside class="rep-nav strat-nav">${groups}</aside><section class="sdoc">
    <div class="crumbs"><a href="#/strategies">Strategies</a> / ${esc(d.kind === "benchmark" ? "Benchmark" : d.kind === "long-term" ? "Long-term investing" : "Screening strategy")}</div>
    <div class="page-head"><h1>${esc(d.name)}</h1><code>${esc(d.key)}</code>
      ${d.kind === "screener" ? `<span class="spacer"></span><a class="btn" href="#/screening/us/${key}">Latest screening →</a>` : ""}
      ${d.kind === "long-term" ? `<span class="spacer"></span><a class="btn" href="#/quality">Open the Quality page →</a>` : ""}</div>
    ${d.status ? `<div class="sd-status ${statusClass(d.status)}"><b>Status</b> ${mdInline(d.status)}</div>` : ""}
    <p class="sd-lead">${mdInline(d.description)}</p>
    <nav class="sd-toc">${toc.map(([id, t]) => `<a data-sec="sd-${id}">${t}</a>`).join("")}</nav>
    ${sec("overview", "Overview", `${d.thesis ? `<p><b>Thesis.</b> ${mdInline(d.thesis)}</p>` : ""}<h3>How it works</h3>${ol(d.how_it_works)}`)}
    ${d.gates.length || d.watch.length || d.setups.length ? `<section class="sd-sec" id="sd-rules"><h2>Rules</h2>
      ${d.gates.length ? (d.kind === "long-term" ? `<h3>Quality tests <span class="muted small">— points out of 100</span></h3>${codeTable(d.gates, "Worth")}`
        : `<h3>Hard gates <span class="muted small">— all must pass, or the stock is AVOID</span></h3>${codeTable(d.gates, "Gate")}`) : ""}
      ${d.watch.length ? `<h3>Watch flags <span class="muted small">— don't disqualify, but cap or downgrade the decision</span></h3>${codeTable(d.watch, "Flag")}` : ""}
      ${d.setups.length ? `<h3>Setups <span class="muted small">— the patterns that make a stock entry-eligible</span></h3>${codeTable(d.setups, "Setup")}` : ""}
      <p class="muted small">These codes are the <code>gate_*</code>, <code>watch_*</code> and <code>setup_*</code> columns on the Screening page.</p></section>` : ""}
    ${sec("entry", d.kind === "long-term" ? "Is the price right?" : "Entry & exit", `${d.entry_rules.length ? (d.kind === "long-term" ? ul(d.entry_rules) : `<h3>Entry, stop and target</h3>${ol(d.entry_rules)}`) : ""}${d.exit_rules.length ? `<h3>Exit</h3>${ol(d.exit_rules)}` : ""}`)}
    ${sec("params", "Parameters", params)}
    ${sec("decisions", "Decisions", d.decisions.length ? `<table class="dtab"><tbody>${d.decisions.map((x) => `<tr><td><span class="tag ${decisionClass(x.label)}">${esc(x.label)}</span></td><td>${esc(x.text)}</td></tr>`).join("")}</tbody></table>
      <p class="muted small">${esc(d.regime_note)}</p>` : "")}
    ${sec("results", "Results", `${screens ? `<h3>Latest screening</h3>${screens}` : ""}<h3>Backtests</h3>${bts}`)}
    ${sec("commands", "Commands", `${cmds}<p class="muted small">Run from <code>scripts/</code> with <code>PYTHONPATH=.</code>. Change <code>--market</code> to <code>india</code> as needed.</p>`)}
    ${sec("caveats", "Known caveats", ul(d.caveats))}
    <p class="muted small sd-src">Generated from <code>${esc(d.source.file)}</code> · code last changed ${prettyDate(d.source.modified)}.
      This page is built from the strategy's own code, so it always describes what the screener and backtester actually run.</p>
  </section></div>`;

  $view.querySelectorAll(".sd-toc a").forEach((a) => a.onclick = () => document.getElementById(a.dataset.sec)?.scrollIntoView({ behavior: "smooth", block: "start" }));
  $view.querySelectorAll("tr[data-href]").forEach((tr) => tr.onclick = () => go(tr.dataset.href));
  $view.querySelectorAll(".copy").forEach((b) => b.onclick = async () => {
    try { await navigator.clipboard.writeText(b.dataset.c); toast("Command copied", "ok"); } catch { toast("Copy failed — select the text instead", "err"); }
  });
}

// --------------------------------------------------------- screening page

const SCREEN_COLS = ["symbol", "name", "sector", "decision", "price", "entry", "stop", "risk_pct", "target_r", "setup_quality",
  "strategy_setup", "pattern", "rs_vs_benchmark", "rsi", "earnings_in", "wait_for", "reason"];

async function screeningPage(alive, mkt, strat, runKey) {
  mkt = mkt || store.get("scrMarket", "us");
  store.set("scrMarket", mkt);
  document.title = "Screening · Trading";
  $view.innerHTML = LOADING;
  const all = await api(`/api/screening/runs?market=${mkt}`);
  if (!alive()) return;
  // a report-source run duplicates a history run from the same day: keep the history one
  const hist = all.filter((r) => r.source === "history");
  const runs = all.filter((r) => r.source === "history" || !hist.some((h) => h.strategy === r.strategy && String(h.run).startsWith(r.run)));
  const strategies = [...new Set(runs.map((r) => r.strategy))].sort();
  strat = strategies.includes(strat) ? strat : strategies.includes(store.get("scrStrat")) ? store.get("scrStrat") : strategies[0];
  const mine = runs.filter((r) => r.strategy === strat);
  const run = mine.find((r) => r.run === runKey) || mine[0];
  $view.innerHTML = `<div class="page-head"><h1>Screening</h1>
      ${segmented([["us", "US"], ["india", "India"]], mkt, "mk")}
      <label class="field"><span>Strategy</span><select id="strat">${strategies.map((s) => `<option ${s === strat ? "selected" : ""}>${esc(s)}</option>`).join("")}</select></label>
      <a class="small" href="#/strategies/${encodeURIComponent(strat)}" title="What this strategy looks for, gate by gate">About this strategy →</a>
      <label class="field"><span>Run</span><select id="run">${mine.map((r, i) => `<option value="${esc(r.run)}" ${r === run ? "selected" : ""}>${prettyDate(r.run)}${i === 0 ? " (latest)" : ""}${r.tradeable != null ? ` — ${r.tradeable} tradeable of ${r.rows}` : ""}</option>`).join("")}</select></label>
    </div>
    <div class="chips" id="dec"></div><div id="tbl">${LOADING}</div>`;
  $view.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(`#/screening/${b.dataset.v}`));
  const nav = (s, r) => go(`#/screening/${mkt}/${encodeURIComponent(s)}${r ? "/" + encodeURIComponent(r) : ""}`);
  $view.querySelector("#strat").onchange = (e) => { store.set("scrStrat", e.target.value); nav(e.target.value); };
  $view.querySelector("#run").onchange = (e) => nav(strat, e.target.value);
  if (!run) { $view.querySelector("#tbl").innerHTML = `<div class="empty"><b>No screening runs for ${mkt.toUpperCase()}</b><div class="muted">Run the screener pipeline, then refresh.</div></div>`; return; }

  const q = new URLSearchParams({ source: run.source, market: mkt, strategy: strat, run: run.run });
  if (run.id) q.set("id", run.id);
  const t = await api(`/api/screening/table?${q}`);
  if (!alive()) return;
  const di = t.columns.indexOf("decision"), ti = t.columns.indexOf("tradeable"), si = t.columns.indexOf("symbol");
  const counts = {};
  t.rows.forEach((r) => { counts[r[di]] = (counts[r[di]] || 0) + 1; });
  const decisions = Object.keys(counts).filter((d) => d && d !== "null").sort();
  const nTrade = t.rows.filter((r) => r[ti] === true).length;
  let activeDec = store.get("scrDec", "tradeable");
  if (activeDec !== "all" && activeDec !== "tradeable" && !counts[activeDec]) activeDec = "tradeable";
  let allCols = store.get("scrAllCols", false);
  const dec = $view.querySelector("#dec");
  const drawChips = () => {
    dec.innerHTML = [["tradeable", "Tradeable", nTrade, "trade"], ["all", "All", t.rows.length, ""], ...decisions.map((d) => [d, d, counts[d], decisionClass(d)])]
      .map(([v, txt, n, cls]) => `<button class="chip ${cls} ${v === activeDec ? "on" : ""}" data-d="${esc(v)}">${esc(txt)}<span>${n}</span></button>`).join("") +
      `<span class="spacer"></span><label class="check"><input type="checkbox" id="allcols" ${allCols ? "checked" : ""}> Show all ${t.columns.length} columns</label>`;
  };
  const draw = () => {
    drawChips();
    const keep = allCols ? [si, ...t.columns.map((_, i) => i).filter((i) => i !== si)] : SCREEN_COLS.map((c) => t.columns.indexOf(c)).filter((i) => i >= 0);
    const rows = t.rows.filter((r) => activeDec === "all" || (activeDec === "tradeable" ? r[ti] === true : r[di] === activeDec));
    const host = $view.querySelector("#tbl");
    if (!rows.length) { host.innerHTML = `<div class="empty"><b>Nothing ${activeDec === "tradeable" ? "tradeable" : "here"} in this run</b><div class="muted">Try “All” to see every screened name.</div></div>`; return; }
    dataTable(host, keep.map((i) => t.columns[i]), rows.map((r) => keep.map((i) => r[i])), {
      name: `${mkt}_${strat}_${run.run}`,
      rowClick: (row, visible) => openChartFromList(mkt, row[keep.indexOf(si)], visible.map((r) => r[keep.indexOf(si)]),
        `${strat} · ${activeDec === "all" ? "all" : activeDec.toLowerCase()}`, location.hash),
    });
  };
  dec.onclick = (e) => { const b = e.target.closest("button[data-d]"); if (b) { activeDec = b.dataset.d; store.set("scrDec", activeDec); draw(); } };
  dec.onchange = (e) => { if (e.target.id === "allcols") { allCols = e.target.checked; store.set("scrAllCols", allCols); draw(); } };
  draw();
}

// ------------------------------------------------------------ reports page

const KIND_LABEL = { backtest: "Backtests", screener: "Screener reports", index: "Index investing", daily: "Daily review", research: "Research notes" };
const KIND_ICON = {
  backtest: '<path d="M3 15l4-5 3 3 6-8"/>', screener: '<path d="M3 4h14l-5 7v5l-4-2v-3z"/>', index: '<path d="M4 16V9M10 16V4M16 16v-5"/>',
  daily: '<rect x="3" y="4" width="14" height="13" rx="1"/><path d="M3 8h14M7 2v4M13 2v4"/>', research: '<path d="M5 3h7l3 3v11H5z"/><path d="M8 9h5M8 12h5"/>',
};
const pct = (x) => (x == null ? null : parseFloat(String(x).replace(/[^0-9.\-]/g, "")));

async function reportsPage(alive) {
  document.title = "Reports · Trading";
  $view.innerHTML = LOADING;
  const list = await api("/api/reports");
  if (!alive()) return;
  const st = store.get("repState", { market: "all", kind: "backtest", strategy: "all" });
  const inMarket = (r) => st.market === "all" || r.market === st.market || r.market === "all";
  $view.innerHTML = `<div class="rep-layout"><aside class="rep-nav"></aside><section class="rep-main"></section></div>`;
  const nav = $view.querySelector(".rep-nav"), main = $view.querySelector(".rep-main");
  const save = () => { store.set("repState", st); draw(); };
  if (!list.length) { main.innerHTML = `<div class="empty"><b>No reports loaded yet</b><div class="muted">Press <b>Refresh reports</b> (top right) after a backtest or screening run.</div></div>`; return; }

  function draw() {
    const mk = list.filter(inMarket);
    const kinds = Object.keys(KIND_LABEL).filter((k) => mk.some((r) => r.kind === k));
    if (!kinds.includes(st.kind)) { st.kind = kinds[0]; st.strategy = "all"; }
    const ofKind = mk.filter((r) => r.kind === st.kind);
    const strategies = [...new Set(ofKind.map((r) => r.strategy))].sort();
    if (st.strategy !== "all" && !strategies.includes(st.strategy)) st.strategy = "all";

    nav.innerHTML = segmented([["all", "All"], ["us", "US"], ["india", "India"]], st.market, "mk") +
      kinds.map((k) => {
        const n = mk.filter((r) => r.kind === k).length;
        return `<div class="nav-item ${k === st.kind ? "active" : ""}" data-k="${k}"><svg viewBox="0 0 20 20">${KIND_ICON[k]}</svg><span>${KIND_LABEL[k]}</span><span class="n">${n}</span></div>` +
          (k === st.kind && strategies.length > 1 ? `<div class="nav-sub"><div class="nav-item ${st.strategy === "all" ? "active" : ""}" data-s="all"><span>All strategies</span><span class="n">${ofKind.length}</span></div>` +
            strategies.map((s) => `<div class="nav-item ${st.strategy === s ? "active" : ""}" data-s="${esc(s)}"><span>${esc(s)}</span><span class="n">${ofKind.filter((r) => r.strategy === s).length}</span></div>`).join("") + "</div>" : "");
      }).join("");
    nav.querySelectorAll(".mk button").forEach((b) => b.onclick = () => { st.market = b.dataset.v; save(); });
    nav.querySelectorAll("[data-k]").forEach((b) => b.onclick = () => { st.kind = b.dataset.k; st.strategy = "all"; save(); });
    nav.querySelectorAll("[data-s]").forEach((b) => b.onclick = () => { st.strategy = b.dataset.s; save(); });

    const rows = ofKind.filter((r) => st.strategy === "all" || r.strategy === st.strategy);
    const isBt = st.kind === "backtest";
    const cols = ["id", "market", "strategy", "run", ...(isBt ? ["cagr %", "excess cagr %", "max dd %", "sharpe"] : ["title"]), "generated"];
    const data = rows.map((r) => {
      const s = r.summary || {};
      return [r.id, r.market === "all" ? "—" : r.market.toUpperCase(), r.strategy, r.run,
        ...(isBt ? [pct(s.cagr), pct(s.excess_cagr), pct(s.max_drawdown), pct(s.sharpe)] : [r.title]), r.generated_at || ""];
    });
    const best = isBt ? rows.reduce((b, r) => (pct(r.summary?.excess_cagr) > pct(b?.summary?.excess_cagr ?? "-1e9") ? r : b), null) : null;
    main.innerHTML = `<div class="page-head"><h1>${KIND_LABEL[st.kind]}</h1><span class="muted">${st.market === "all" ? "Both markets" : st.market.toUpperCase()}${st.strategy === "all" ? "" : " · " + esc(st.strategy)} · ${rows.length} report${rows.length === 1 ? "" : "s"}</span>
      ${best ? `<span class="spacer"></span><span class="muted small">Best excess CAGR: <a href="#/reports/${best.id}">${esc(best.strategy)} · ${esc(best.run)}</a> <b class="${pct(best.summary.excess_cagr) >= 0 ? "pos" : "neg"}">${esc(best.summary.excess_cagr)}</b></span>` : ""}</div><div id="rt"></div>`;
    dataTable(main.querySelector("#rt"), cols, data, {
      hidden: ["id"], name: `reports_${st.kind}`, sort: ["generated", -1],
      format: { generated: prettyDate },  // sorting still uses the raw ISO value
      rowClick: (row) => go(`#/reports/${row[0]}`),
    });
  }
  draw();
}

async function reportPage(alive, id, tab) {
  $view.innerHTML = LOADING;
  const r = await api(`/api/reports/${id}`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  if (r.error) {
    $view.innerHTML = `<div class="empty"><b>Report not found</b><div class="muted">It may have been deleted on disk or re-generated. <a href="#/reports">Back to reports</a></div></div>`;
    return;
  }
  document.title = `${r.strategy} · ${r.run} · Trading`;
  const has = (n) => r.tables.some((t) => t.name === n);
  const tabs = [["report", "Report"], ...(has("equity") ? [["equity", "Equity curve"]] : []), ...(has("trades") ? [["trades", `Trades (${r.tables.find((t) => t.name === "trades").rows})`]] : []),
    ...(r.tables.length ? [["tables", `Data (${r.tables.length})`]] : [])];
  tab = tabs.some((t) => t[0] === tab) ? tab : "report";
  const s = r.summary || {};
  const tiles = [["CAGR", s.cagr], ["Excess CAGR", s.excess_cagr], ["Max drawdown", s.max_drawdown], ["Sharpe", s.sharpe], ["Total return", s.total_return]]
    .filter(([, v]) => v).map(([k, v]) => `<div class="tile"><span>${k}</span><b class="${/^-/.test(v) ? "neg" : k === "Max drawdown" ? "" : "pos"}">${esc(v)}</b></div>`).join("");
  $view.innerHTML = `<div class="crumbs"><a href="#/reports">Reports</a> / <span>${KIND_LABEL[r.kind] || r.kind}</span> / <span>${esc(r.market === "all" ? "" : r.market.toUpperCase() + " · ")}<a href="#/strategies/${encodeURIComponent(r.strategy)}" title="About this strategy">${esc(r.strategy)}</a></span></div>
    <div class="page-head"><h1>${esc(r.run)}</h1>${tiles ? `<div class="tiles">${tiles}</div>` : ""}</div>
    <div class="tabs">${tabs.map((t) => `<a href="#/reports/${id}/${t[0]}" class="${t[0] === tab ? "on" : ""}">${t[1]}</a>`).join("")}</div><div id="body"></div>`;
  const body = $view.querySelector("#body");
  const tableOpts = (t, name) => {
    const si = t.columns.indexOf("symbol");
    return {
      name: `${r.strategy}_${r.run}_${name}`.replace(/\W+/g, "_"),
      ...(si >= 0 && r.market !== "all" ? {
        rowClick: (row, visible) => {
          if (name === "trades") store.set("tradeRun:" + r.market, String(id));
          openChartFromList(r.market, row[si], visible.map((x) => x[si]), `${r.strategy} trades`, location.hash);
        },
      } : {}),
    };
  };
  if (tab === "report") {
    body.innerHTML = `<article class="md">${marked.parse(r.markdown)}</article>`;
    body.querySelectorAll(".md table").forEach((t) => t.outerHTML = `<div class="md-table">${t.outerHTML}</div>`);
  } else if (tab === "equity") {
    body.innerHTML = `<div id="eqchart"></div><div id="eqt"></div>`;
    const t = await api(`/api/reports/${id}/tables/equity`);
    if (!alive()) return;
    const chart = LC.createChart(body.querySelector("#eqchart"), { autoSize: true, ...CHART_THEME });
    const ci = (n) => t.columns.indexOf(n), ei = ci("equity") >= 0 ? ci("equity") : 1, di = ci("drawdown_pct");
    const series = (idx) => t.rows.filter((x) => x[idx] != null).map((x) => ({ time: String(x[0]).slice(0, 10), value: x[idx] }));
    chart.addSeries(LC.AreaSeries, { lineColor: "#2962ff", topColor: "rgba(41,98,255,.25)", bottomColor: "rgba(41,98,255,0)", lineWidth: 2, title: "Equity" }, 0).setData(series(ei));
    if (di >= 0) {
      chart.addSeries(LC.AreaSeries, { lineColor: "#ef5350", topColor: "rgba(239,83,80,.05)", bottomColor: "rgba(239,83,80,.35)", lineWidth: 1, title: "Drawdown %" }, 1).setData(series(di));
      try { chart.panes()[1].setHeight(130); } catch {}
    }
    requestAnimationFrame(() => chart.timeScale().fitContent());
    cleanup = () => chart.remove();
    dataTable(body.querySelector("#eqt"), t.columns, t.rows, tableOpts(t, "equity"));
  } else if (tab === "trades") {
    const t = await api(`/api/reports/${id}/tables/trades`);
    if (!alive()) return;
    const wins = t.rows.filter((x) => x[t.columns.indexOf("pnl")] > 0).length;
    const rIdx = t.columns.indexOf("r_multiple"), avgR = rIdx >= 0 && t.rows.length ? t.rows.reduce((a, x) => a + (x[rIdx] || 0), 0) / t.rows.length : null;
    body.innerHTML = `<div class="tiles small"><div class="tile"><span>Trades</span><b>${t.rows.length}</b></div>
      <div class="tile"><span>Win rate</span><b>${t.rows.length ? ((wins / t.rows.length) * 100).toFixed(1) : 0}%</b></div>
      ${avgR != null ? `<div class="tile"><span>Avg R</span><b class="${avgR >= 0 ? "pos" : "neg"}">${signed(avgR)}</b></div>` : ""}
      <div class="tile hint"><span>Tip</span><b class="muted">Click a trade to see it on the chart</b></div></div><div id="tt"></div>`;
    dataTable(body.querySelector("#tt"), t.columns, t.rows, tableOpts(t, "trades"));
  } else {
    const first = store.get("dataTab:" + id, r.tables[0].name);
    body.innerHTML = `<div class="split"><nav class="tlist">${r.tables.map((t) => `<a data-n="${esc(t.name)}" class="${t.name === first ? "on" : ""}" title="${esc(t.name)}">${esc(t.name)}<span class="n">${t.rows}</span></a>`).join("")}</nav><div id="tt"></div></div>`;
    const show = async (n) => {
      store.set("dataTab:" + id, n);
      body.querySelectorAll(".tlist a").forEach((a) => a.classList.toggle("on", a.dataset.n === n));
      const t = await api(`/api/reports/${id}/tables/${encodeURIComponent(n)}`);
      if (alive()) dataTable(body.querySelector("#tt"), t.columns, t.rows, tableOpts(t, n));
    };
    body.querySelector(".tlist").onclick = (e) => { const a = e.target.closest("a"); if (a) show(a.dataset.n); };
    show(r.tables.some((t) => t.name === first) ? first : r.tables[0].name);
  }
}

// ----------------------------------------------------------------- router

function go(hash) { if (location.hash === hash) route(); else location.hash = hash; }

let lastRoute = null;
// ------------------------------------------------------------- data status page

const ST_ICON = { ok: "✓", partial: "!", failed: "✕", running: "", pending: "", skipped: "–", interrupted: "✕", warn: "!", stale: "✕", missing: "?" };
const ST_TEXT = { ok: "OK", partial: "Partly failed", failed: "Failed", running: "Running", pending: "Pending", skipped: "Skipped", interrupted: "Interrupted",
  warn: "Behind", stale: "Stale", missing: "Missing" };
const stBadge = (st) => `<span class="stb st-${st}">${st === "running" ? '<i class="spin"></i>' : ST_ICON[st] || ""}${ST_TEXT[st] || st}</span>`;
function dur(sec) {
  if (sec == null) return "";
  if (sec < 60) return `${Math.round(sec)}s`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${Math.round(sec % 60)}s`;
  return `${Math.floor(sec / 3600)}h ${Math.round((sec % 3600) / 60)}m`;
}
const clock = (iso) => (iso ? new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "");
const ago = (iso) => {
  if (!iso) return "";
  const m = (Date.now() - new Date(iso)) / 60000;
  return m < 1 ? "just now" : m < 60 ? `${Math.round(m)} min ago` : m < 48 * 60 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`;
};

/** header dot: worst of prices / breadth / screening across markets, or "updating" while a job runs */
async function refreshStatusDot() {
  const a = document.getElementById("dstatus");
  try {
    const s = await api("/api/status");
    const st = s.running.length ? "running" : s.overall;
    a.className = `dstatus st-${st}`;
    a.querySelector("span").textContent = s.running.length ? "Updating…" : "Data";
    const line = (m) => { const f = s.freshness[m]; const p = f.items.find((i) => i.key === "prices"); return `${f.name}: prices ${p.date ? prettyDate(p.date) : "none"} (${ST_TEXT[p.status]})`; };
    a.title = `Data status — ${line("us")} · ${line("india")}${s.latest_daily ? ` · last daily run ${clock(s.latest_daily.started_at)}: ${ST_TEXT[s.latest_daily.status]}` : ""}`;
    return s;
  } catch { a.className = "dstatus"; return null; }
}
refreshStatusDot();
setInterval(refreshStatusDot, 120000);

async function statusPage(alive, runId) {
  document.title = "Data status · Trading";
  $view.innerHTML = LOADING;
  const s = await refreshStatusDot() || await api("/api/status");
  const run = runId ? await api(`/api/status/run/${runId}`).catch(() => null) : s.latest_daily;
  if (!alive()) return;
  const live = (run && run.status === "running") || s.running.length;
  const steps = run?.steps || [];
  const done = steps.filter((x) => ["ok", "failed", "skipped", "interrupted"].includes(x.status)).length;
  const fresh = (m) => {
    const f = s.freshness[m];
    return `<section class="sec-card"><div class="sec-card-h"><h3>${f.name}</h3><span class="muted small">expected trading day: ${prettyDate(f.expected)}</span></div>
      <table class="stt">${f.items.map((i) => `<tr><td>${stBadge(i.status)}</td><td><b>${esc(i.label)}</b></td>
        <td class="num">${i.kind === "session" ? (i.date ? prettyDate(i.date) : "—") : (i.date ? clock(i.date) : "—")}</td><td class="muted">${esc(i.text)}</td></tr>`).join("")}</table></section>`;
  };
  const stepRows = steps.map((x, i) => `<tr class="srow-${x.status}" data-i="${i}">
      <td>${stBadge(x.status)}</td><td><b>${esc(x.label || x.step)}</b>${x.market ? ` <span class="mkt">${MKT_BADGE[x.market] || x.market}</span>` : ""}</td>
      <td class="num muted">${x.started_at ? new Date(x.started_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : ""}</td>
      <td class="num">${x.status === "running" ? dur((Date.now() - new Date(x.started_at)) / 1000) : dur(x.duration_s)}</td>
      <td class="sdetail">${esc(x.detail || "")}${x.error ? `<details><summary class="neg">${esc(x.error.split("\n")[0])}</summary><pre>${esc(x.error)}</pre></details>` : ""}</td></tr>`).join("");
  $view.innerHTML = `<div class="page-head"><h1>Data status</h1>${stBadge(s.running.length ? "running" : s.overall)}
      <span class="muted small">checked ${clock(s.now)}${live ? " · refreshing every 5 s while a job runs" : ""}</span><span class="spacer"></span>
      <button class="ghost" id="strefresh">Refresh</button></div>
    <div class="pipes">${s.pipelines.map((p) => `<a class="pipe ${run && p.last && p.last.id === run.id ? "cur" : ""}" ${p.last ? `href="#/status/${p.last.id}"` : ""} title="${esc(p.jobs.join(" → "))}">
        <div class="pipe-h"><b>${p.name}</b>${p.market ? ` <span class="mkt">${MKT_BADGE[p.market]}</span>` : ""}<span class="spacer"></span>${p.last ? stBadge(p.last.status) : '<span class="muted small">never run</span>'}</div>
        <div class="muted small">${p.last ? `${clock(p.last.started_at)} · ${ago(p.last.started_at)}${p.last.duration_s != null ? " · " + dur(p.last.duration_s) : ""}` : esc(p.summary)}</div></a>`).join("")}</div>
    <section class="sec-card">
      ${run ? `<div class="sec-card-h"><h3>${runId ? `Run #${run.id}` : run.status === "running" ? "Running now" : "Latest run"}</h3>${stBadge(run.status)}
          <span class="muted small">${esc(run.job)} · started ${clock(run.started_at)} (${ago(run.started_at)})
          ${run.finished_at ? ` · finished ${clock(run.finished_at)} · took ${dur(run.duration_s)}` : run.status === "running" ? ` · running for ${dur((Date.now() - new Date(run.started_at)) / 1000)}` : ""}</span>
          <span class="spacer"></span>${runId ? `<a href="#/status">latest run</a>` : ""}</div>
        <div class="stprog"><i style="width:${steps.length ? (done / steps.length) * 100 : 0}%"></i></div>
        <div class="muted small" style="margin:4px 0 8px">${done} of ${steps.length} steps done${run.summary ? ` · ${esc(run.summary)}` : ""}${run.args?.strategies ? ` · strategies: ${esc(run.args.strategies.join(", "))}` : ""}</div>
        <table class="stt steps"><thead><tr><th></th><th>Step</th><th class="num">Started</th><th class="num">Took</th><th>Result</th></tr></thead><tbody>${stepRows}</tbody></table>
        ${run.log_tail ? `<details class="stlog"><summary>Log — last ${run.log_tail.length} lines of ${esc(run.log_path.split("/").slice(-1)[0])}</summary><pre>${esc(run.log_tail.join("\n"))}</pre></details>` : ""}`
      : `<div class="empty"><b>No run recorded yet</b><div class="muted">Run the daily pipeline from a terminal:</div><code>${esc(s.command)}</code>
          <div class="muted small">Suggested schedule (cron lines, one per market close): <code>${esc(s.schedule_command)}</code></div></div>`}
    </section>
    <section class="sec-card"><div class="sec-card-h"><h3>Jobs</h3><span class="muted small">each job's latest run · <code>python -m jobs list</code> · run one with <code>python -m jobs run &lt;job&gt; --market us</code></span></div>
      <table class="stt jobs"><thead><tr><th>Job</th><th>Layer</th><th>Cadence</th><th>US</th><th>India</th><th>What it does</th></tr></thead><tbody>
      ${s.jobs.map((j) => { const c = (x) => x ? `<span title="${esc(x.detail || "")}">${stBadge(x.status)} <span class="muted small">${clock(x.at)}</span></span>` : '<span class="muted small">never</span>';
        return `<tr><td><b>${esc(j.name)}</b></td><td><span class="layer l-${j.layer}">${j.layer}</span></td><td class="muted">${j.cadence}${j.network ? "" : " · offline"}</td>
          ${j.per_market ? `<td>${c(j.last.us)}</td><td>${c(j.last.india)}</td>` : `<td colspan="2">${c(j.last.all)}</td>`}<td class="muted small">${esc(j.summary.split(": ").slice(1).join(": ") || j.summary)}</td></tr>`; }).join("")}
      </tbody></table></section>
    <div class="sec-top">${fresh("us")}${fresh("india")}</div>
    <section class="sec-card"><div class="sec-card-h"><h3>Run history</h3><span class="muted small">daily runs and standalone commands · click one for its steps and log</span></div>
      ${s.runs.length ? `<table class="stt hist"><thead><tr><th></th><th>Started</th><th>Job</th><th class="num">Took</th><th>Steps</th><th>Notes</th></tr></thead><tbody>
        ${s.runs.map((r) => `<tr data-id="${r.id}" class="${run && r.id === run.id ? "cur" : ""}"><td>${stBadge(r.status)}</td><td>${clock(r.started_at)} <span class="muted small">${ago(r.started_at)}</span></td>
          <td><b>${esc(r.job)}</b>${r.args?.market ? ` <span class="mkt">${MKT_BADGE[r.args.market] || r.args.market}</span>` : ""}${r.args?.markets ? ` <span class="muted small">${esc(r.args.markets.map((m) => MKT_BADGE[m]).join(" + "))}</span>` : ""}</td>
          <td class="num">${dur(r.duration_s)}</td>
          <td class="small">${r.steps ? `<span class="pos">${r.steps.ok} ok</span>${r.steps.failed ? ` · <span class="neg">${r.steps.failed} failed</span>` : ""}${r.steps.skipped ? ` · <span class="muted">${r.steps.skipped} skipped</span>` : ""}` : ""}</td>
          <td class="muted small">${esc(r.summary || "")}</td></tr>`).join("")}</tbody></table>`
        : '<div class="muted small">Nothing recorded yet.</div>'}
      <p class="muted small">Web viewer: ${s.freshness.viewer.reports} reports loaded, last at ${clock(s.freshness.viewer.reports_loaded_at)}. Daily update: <code>${esc(s.command)}</code></p></section>`;
  $view.querySelector("#strefresh").onclick = () => route();
  $view.querySelectorAll(".stt.hist tbody tr").forEach((tr) => tr.onclick = () => go(`#/status/${tr.dataset.id}`));
  if (live) {
    const t = setTimeout(() => { if (alive()) route(); }, 5000);
    const prev = cleanup; cleanup = () => { clearTimeout(t); prev(); };
  }
}

// ------------------------------------------------------------- navigation

/** Top-level sections in the order of a review — market, ideas, the stock, what I track, does it work —
 *  each with its pages (shown inline in the header, next to the open section, when there is more than one). */
const SECTIONS = [
  { key: "markets", label: "Markets", pages: [["breadth", "Breadth"], ["sectors", "Sectors"], ["movers", "Movers"]] },
  { key: "ideas", label: "Ideas", pages: [["screening", "Screening"], ["quality", "Quality"]] },
  { key: "chart", label: "Chart", pages: [["chart", "Chart"]] },
  { key: "watchlists", label: "Watchlists", pages: [["watchlist", "Watchlists"]] },
  { key: "research", label: "Research", pages: [["reports", "Reports"], ["strategies", "Strategies"], ["playbook", "Playbook"]] },
];
const PAGE_SECTION = Object.fromEntries(SECTIONS.flatMap((s) => s.pages.map(([p]) => [p, s])));
const $nav = document.getElementById("nav");

/** highlight the section and tab; each section and tab reopens the exact page you were last on */
function renderNav(page) {
  const sec = PAGE_SECTION[page] || null;  // pages outside the sections (Data status) highlight none
  if (sec) { store.set(`navLast:${sec.key}`, location.hash); store.set(`navPage:${page}`, location.hash); }
  $nav.innerHTML = SECTIONS.map((s, i) => {
    const link = `<a href="${esc(store.get(`navLast:${s.key}`, `#/${s.pages[0][0]}`))}" data-sec="${s.key}"
      class="sec ${s === sec ? "active" : ""}" title="${esc(s.pages.map((p) => p[1]).join(" · "))} (Alt+${i + 1})">${s.label}</a>`;
    if (s !== sec || s.pages.length < 2) return link;
    // the open section's pages, inline next to it
    return `<span class="sec-group">${link}<span class="sec-tabs">${s.pages.map(([p, t]) =>
      `<a href="${esc(p === page ? location.hash : store.get(`navPage:${p}`, `#/${p}`))}" class="tab ${p === page ? "active" : ""}">${t}</a>`).join("")}</span></span>`;
  }).join("");
}
// Alt+1…5: jump to a section; Alt+[ / Alt+]: previous / next tab in the section
document.addEventListener("keydown", (e) => {
  if (!e.altKey || e.metaKey || e.ctrlKey || e.target.closest?.("input, select, textarea")) return;
  const n = /^Digit([1-9])$/.exec(e.code)?.[1];
  if (n && SECTIONS[n - 1]) { e.preventDefault(); go($nav.querySelector(`[data-sec="${SECTIONS[n - 1].key}"]`).getAttribute("href")); return; }
  if (e.code === "BracketLeft" || e.code === "BracketRight") {
    const page = location.hash.replace(/^#\//, "").split("/")[0] || "chart", sec = PAGE_SECTION[page];
    if (!sec || sec.pages.length < 2) return;
    const i = sec.pages.findIndex(([p]) => p === page), j = (i + (e.code === "BracketRight" ? 1 : -1) + sec.pages.length) % sec.pages.length;
    e.preventDefault(); go(store.get(`navPage:${sec.pages[j][0]}`, `#/${sec.pages[j][0]}`));
  }
});

/** the sector-analysis playbook (research/sector-analysis-playbook.md), shown as its ingested report */
async function playbookPage(alive) {
  $view.innerHTML = LOADING;
  const runs = await api("/api/reports?kind=research").catch(() => []);
  if (!alive()) return;
  const r = runs.find((x) => x.run === "sector-analysis-playbook");
  if (!r) {
    $view.innerHTML = `<div class="empty"><b>Playbook not loaded</b><div class="muted">Click <b>Refresh reports</b> to load research/sector-analysis-playbook.md.</div></div>`;
    return;
  }
  return reportPage(alive, r.id);
}

async function route() {
  cleanup(); cleanup = () => {};
  // a new page opens at the top; re-rendering the same page (indicator change, refresh) keeps the scroll
  if (location.hash !== lastRoute) { window.scrollTo(0, 0); lastRoute = location.hash; }
  const seq = ++navSeq, alive = () => seq === navSeq;
  const parts = location.hash.replace(/^#\//, "").split("/").map(decodeURIComponent);
  const page = parts[0] || "chart";
  renderNav(page);
  document.body.dataset.page = page;
  try {
    if (page === "chart") await chartPage(alive, parts[1], parts[2], parts[3]);
    else if (page === "screening") await screeningPage(alive, parts[1], parts[2], parts[3]);
    else if (page === "watchlist") await watchlistPage(alive, parts[1]);
    else if (page === "strategies") await strategiesPage(alive, parts[1]);
    else if (page === "quality") await qualityPage(alive, parts[1]);
    else if (page === "breadth") await breadthPage(alive, parts[1]);
    else if (page === "movers") await moversPage(alive, parts[1]);
    else if (page === "sectors") await sectorsPage(alive, parts[1], parts[2], parts[3]);
    else if (page === "reports") await (parts[1] ? reportPage(alive, parts[1], parts[2]) : reportsPage(alive));
    else if (page === "playbook") await playbookPage(alive);
    else if (page === "status") await statusPage(alive, parts[1]);
    else go("#/chart");
  } catch (e) {
    if (alive()) $view.innerHTML = `<div class="empty"><b>Something went wrong</b><div class="muted">${esc(e.message)}</div></div>`;
  }
}
window.addEventListener("hashchange", route);

document.getElementById("refresh").onclick = async (e) => {
  const b = e.currentTarget;
  b.disabled = true; b.classList.add("busy");
  try {
    const before = (await api("/api/reports")).length;
    const r = await api("/api/ingest", { method: "POST" });
    const d = r.runs - before;
    toast(d > 0 ? `${d} new report${d > 1 ? "s" : ""} loaded` : d < 0 ? `${-d} removed — ${r.runs} reports` : `Up to date — ${r.runs} reports`, "ok");
    route();
  } catch (err) { toast("Refresh failed: " + err.message, "err"); }
  b.disabled = false; b.classList.remove("busy");
};

// keyboard help
const HELP = el(`<div class="help" hidden><div class="help-card"><h3>Keyboard shortcuts</h3>
  <dl><dt>Type a letter</dt><dd>Search symbols (on the chart)</dd><dt>↑ / ↓</dt><dd>Previous / next symbol in the list you opened it from</dd>
  <dt>Alt + T / H / J / V / C / F</dt><dd>Trend line / horizontal line / horizontal ray / vertical line / cross line / Fib retracement</dd>
  <dt>Drag the chart</dt><dd>Pan left/right and up/down (up/down turns auto-scale off; click “auto” to restore)</dd>
  <dt>Drag the price axis</dt><dd>Stretch / squeeze the price scale</dd><dt>Alt + R</dt><dd>Reset the chart view</dd>
  <dt>Shift + drag</dt><dd>Measure</dd><dt>Esc</dt><dd>Cancel drawing / deselect</dd><dt>Del</dt><dd>Delete the selected drawing</dd>
  <dt>⌘ / Ctrl + Z</dt><dd>Undo the last drawing change</dd>
  <dt>Alt + 1 … 5</dt><dd>Markets / Ideas / Chart / Watchlists / Research</dd><dt>Alt + [ / ]</dt><dd>Previous / next tab in the section</dd>
  <dt>?</dt><dd>Show this help</dd></dl>
  <button class="ghost">Close</button></div></div>`);
document.body.append(HELP);
HELP.onclick = (e) => { if (e.target === HELP || e.target.tagName === "BUTTON") HELP.hidden = true; };
document.addEventListener("keydown", (e) => {
  if ((e.key === "?" || (e.key === "/" && e.shiftKey)) && !e.target.closest?.("input, select, textarea")) { HELP.hidden = !HELP.hidden; e.preventDefault(); e.stopImmediatePropagation(); }
  else if (e.key === "Escape") HELP.hidden = true;
}, true);
document.getElementById("help").onclick = () => (HELP.hidden = false);
route();
