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
  rs_vs_benchmark: "RS vs index", rs_vs_sector: "RS vs sector", rsi: "RSI", adx: "ADX", earnings_in: "Earnings in (d)",
  wait_for: "Wait for", reason: "Reason", entry_date: "Entry date", entry_price: "Entry price", exit_date: "Exit date",
  exit_price: "Exit price", exit_reason: "Exit", r_multiple: "R", holding_days: "Days held", pnl: "P&L",
  initial_stop: "Initial stop", drawdown_pct: "Drawdown %", positions_open: "Open positions",
  "cagr %": "CAGR %", "excess cagr %": "Excess CAGR %", "max dd %": "Max DD %", market: "Market", strategy: "Strategy", run: "Run",
  last: "Last", "chg %": "Chg %", source: "Source", "to entry %": "To entry %", note: "Note", added: "Added", "target R": "Target R",
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
 *         actions: [{key, title, icon, fn(row)}], rowClass(row)} */
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
        let cls = typeof v === "number" ? "num" : "";
        if (typeof v === "number" && SIGNED_COL.test(columns[i])) cls += v < 0 ? " neg" : v > 0 ? " pos" : "";
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

/** Remember the list a symbol was opened from, so the chart can step through it. */
function openChartFromList(market, symbol, symbols, labelText, back) {
  const uniq = [...new Set(symbols)];
  store.set("chartList", { market, symbols: uniq, label: labelText, back });
  go(`#/chart/${market}/${encodeURIComponent(symbol)}`);
}

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
  const prefs = { panel: true, ...store.get("chartPrefs", {}) };
  market = market || store.get("lastMarket", "us");
  symbol = symbol || store.get("lastSymbol:" + market, market === "us" ? "AAPL" : "RELIANCE.NS");
  tf = tf || store.get("lastTf", "D");
  store.set("lastMarket", market); store.set("lastSymbol:" + market, symbol); store.set("lastTf", tf);
  document.title = `${symbol} · Trading`;
  const list = store.get("chartList", null);
  const pos = list && list.market === market ? list.symbols.indexOf(symbol) : -1;
  const href = (s, t = tf) => `#/chart/${market}/${encodeURIComponent(s)}/${t}`;

  $view.innerHTML = `
    <div class="chart-top">
      ${segmented([["us", "US"], ["india", "India"]], market, "mk")}
      <div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg>
        <input id="sym" value="${esc(symbol)}" autocomplete="off" spellcheck="false" title="Search symbols — or just start typing"><ul hidden></ul></div>
      ${segmented([["D", "1D"], ["W", "1W"], ["M", "1M"]], tf, "tfs")}
      <button class="ghost" id="ind" title="Add indicators"><svg viewBox="0 0 20 20"><path d="M3 15l4-5 3 3 7-8"/><path d="M13 5h4v4"/></svg>Indicators</button>
      <label class="field" id="trades-field" title="Mark the buys and exits a backtest run made in this symbol"><span>Backtest trades</span>
        <select id="trades"><option value="">None</option></select></label>
      <button class="ghost icon" id="fit" title="Show full history"><svg viewBox="0 0 20 20"><path d="M3 8V3h5M17 8V3h-5M3 12v5h5M17 12v5h-5"/></svg></button>
      <span class="spacer"></span>
      ${pos >= 0 ? `<div class="stepper" title="Step through the list (↑ / ↓)"><button class="ghost icon" id="prev">‹</button><span>${pos + 1} / ${list.symbols.length}</span><button class="ghost icon" id="next">›</button></div>` : ""}
      <button class="ghost" id="panel" title="Show / hide the side panel"></button>
    </div>
    <div class="quote" id="quote"><b class="q-sym">${esc(symbol)}</b><span class="muted" id="q-sector"></span></div>
    <div class="chart-layout ${prefs.panel ? "" : "collapsed"}"><div class="tools" id="tools"></div>
      <div id="chart">${LOADING}</div><aside class="side" id="side"></aside></div>`;
  const $ = (s) => $view.querySelector(s);
  $view.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(`#/chart/${b.dataset.v}`));
  $view.querySelectorAll(".tfs button").forEach((b) => b.onclick = () => go(href(symbol, b.dataset.v)));
  const syncPanel = () => { $("#panel").textContent = prefs.panel ? "Hide panel" : "Show panel"; $(".chart-layout").classList.toggle("collapsed", !prefs.panel); };
  syncPanel();
  $("#panel").onclick = () => { prefs.panel = !prefs.panel; store.set("chartPrefs", prefs); syncPanel(); };
  const step = (d) => { if (pos >= 0) go(href(list.symbols[(pos + d + list.symbols.length) % list.symbols.length])); };
  if (pos >= 0) { $("#prev").onclick = () => step(-1); $("#next").onclick = () => step(1); }

  const viewKey = `${market}:${symbol}:${tf}`;
  let chart = null;
  // rebuild the chart (for an indicator change) without losing the user's zoom / scroll
  const rerender = () => { try { if (chart) keepView = { key: viewKey, range: chart.timeScale().getVisibleLogicalRange() }; } catch {} route(); };
  $("#ind").onclick = () => Studies.openPicker({ onChange: rerender });

  const search = $("#sym");
  symbolSearch(search, $(".search ul"), market, (s) => go(href(s)));
  // TradingView habit: start typing anywhere to change symbol; arrows step through the list
  const onKey = (e) => {
    if (e.target.closest?.("input, select, textarea") || e.metaKey || e.ctrlKey || e.altKey) return;
    if (/^[a-z0-9]$/i.test(e.key)) { search.focus(); search.value = e.key.toUpperCase(); search.dispatchEvent(new Event("input")); e.preventDefault(); }
    else if (e.key === "ArrowDown" && pos >= 0) { step(1); e.preventDefault(); }
    else if (e.key === "ArrowUp" && pos >= 0) { step(-1); e.preventDefault(); }
  };
  document.addEventListener("keydown", onKey);
  cleanup = () => { document.removeEventListener("keydown", onKey); };

  const bench = BENCH[market];
  const [px, ctx, tradeRuns, bpx, wlItems] = await Promise.all([
    api(`/api/prices?market=${market}&symbol=${encodeURIComponent(symbol)}&tf=${tf}&bars=${ALL_BARS}`).catch((e) => ({ error: e.message })),
    api(`/api/symbol-context?market=${market}&symbol=${encodeURIComponent(symbol)}`).catch(() => ({ latest: [], history: [] })),
    api(`/api/trade-runs?market=${market}&symbol=${encodeURIComponent(symbol)}`).catch(() => []),
    Studies.needsBench() ? api(`/api/prices?market=${market}&symbol=${bench}&tf=${tf}&bars=${ALL_BARS}`).catch(() => null) : null,
    WL.list(market).catch(() => []),
  ]);
  let wl = wlItems;
  if (!alive()) return;
  const chartEl = $("#chart");
  renderSide(ctx);
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
  $("#quote").innerHTML = `<b class="q-sym">${esc(symbol)}</b><button class="star" id="star"></button>${sector ? `<span class="muted">${esc(sector)}</span>` : ""}
    <span class="q-px">${fmt(lastClose)}</span><span class="${chg >= 0 ? "pos" : "neg"}">${signed(chg)}%</span>
    <span class="muted">${tf === "D" ? "1 day" : tf === "W" ? "1 week" : "1 month"} · ${prettyDate(last.time)}</span>
    ${rows[0].time > "2011-01-01" ? `<span class="hist-note" title="The database holds this symbol from ${prettyDate(rows[0].time)} only — a recent listing, or history that was never backfilled. To fetch up to 16 years, run from scripts/:\npython3 -m swing_screener.marketdata.backfill --market ${market} --years 16 --only-short">history from ${prettyDate(rows[0].time)} ⓘ</span>` : ""}
    <span class="q-range" title="52-week range"><span class="muted">52w</span> ${fmt(lo52)}
      <span class="bar52"><i style="left:${rangePos.toFixed(1)}%"></i></span>${fmt(hi52)}
      <span class="${fromHi >= -0.5 ? "pos" : "muted"}">${fromHi >= -0.5 ? "at high" : signed(fromHi, 1) + "% from high"}</span></span>`;

  // watchlist star: on/off for this symbol (TradingView's "add to watchlist")
  const syncStar = () => {
    const e = wl.find((x) => x.symbol === symbol), b = $("#star");
    b.classList.toggle("starred", !!e);
    b.innerHTML = e ? "★" : "☆";
    b.title = e ? `On your watchlist (${sourceText(e)}) — click to remove` : "Add to watchlist";
  };
  syncStar();
  $("#star").onclick = async () => {
    const on = wl.some((x) => x.symbol === symbol);
    try {
      if (on) { await WL.remove(market, symbol); toast(`${symbol} removed from the watchlist`, "ok"); }
      else { await WL.add(market, symbol); toast(`${symbol} added to the watchlist`, "ok"); }
      wl = await WL.list(market); syncStar(); renderSide(ctx);
    } catch (err) { toast(err.message, "err"); }
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
  // legend controls: hide / settings / remove (hover buttons, like TradingView)
  chartEl.addEventListener("click", (ev) => {
    const row = ev.target.closest(".srow"); if (!row) return;
    const id = row.dataset.id, a = ev.target.closest("button[data-a]")?.dataset.a;
    if (a === "eye") {
      const s = Studies.toggleHidden(id), e = studies.find((x) => x.s.id === id);
      if (s && e) { e.s.hidden = s.hidden; if (e.setVisible) e.setVisible(!s.hidden); else (e.series || []).forEach((ser) => ser.applyOptions({ visible: !s.hidden })); }
      row.classList.toggle("off", !!s?.hidden);
      setLegend(times[lastI]);
    } else if (a === "gear") Studies.openSettings(id, rerender);
    else if (a === "x") removeStudy(id);
    else selectStudy(selStudy === id ? null : id);
  });
  chartEl.addEventListener("dblclick", (ev) => { const r = ev.target.closest(".srow"); if (r) Studies.openSettings(r.dataset.id, rerender); });
  // clicking an indicator's line selects it (nearest line within a few pixels, in the pane clicked)
  chart.subscribeClick((p) => {
    if (!p.point || !dr || !Drawings.TOOLS[dr.tool]?.cursor || dr.tool === "eraser") return;
    let best = null, bd = 7;
    for (const e of studies) {
      if (e.pane !== (p.paneIndex ?? 0) || !e.series || e.s.hidden) continue;
      e.series.forEach((ser) => {
        const d = p.seriesData.get(ser), v = d?.value;
        const y = v == null ? null : ser.priceToCoordinate(v);
        if (y != null && Math.abs(y - p.point.y) < bd) { bd = Math.abs(y - p.point.y); best = e; }
      });
    }
    selectStudy(best ? best.s.id : null);
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

  function renderSide(ctx) {
    const side = $("#side");
    const listHtml = pos >= 0 && list.label !== "Watchlist" ? `<section><h3>${esc(list.label)} <a class="muted" href="${esc(list.back || "#/screening")}">back</a></h3>
      <div class="wl">${list.symbols.map((s, i) => `<a href="${href(s)}" class="${i === pos ? "cur" : ""}">${esc(s)}</a>`).join("")}</div></section>` : "";
    const wlHtml = `<section><h3>Watchlist · ${market.toUpperCase()} <a class="muted" href="#/watchlist/${market}">open</a></h3>
      ${wl.length ? `<div class="wlp">${wl.map((e) => `<a data-s="${esc(e.symbol)}" class="${e.symbol === symbol ? "cur" : ""}" title="${esc(sourceText(e))}${e.note ? " — " + esc(e.note) : ""}">
        <span class="wsym">${e.manual ? '<i class="dot man"></i>' : '<i class="dot scr"></i>'}${esc(e.symbol)}</span>
        <span class="wlast">${e.last != null ? fmt(e.last) : ""}</span>
        <span class="${(e.change_pct ?? 0) >= 0 ? "pos" : "neg"}">${e.change_pct != null ? signed(e.change_pct) + "%" : ""}</span></a>`).join("")}</div>`
        : '<div class="muted small">Empty — use ☆ next to the symbol to add it.</div>'}</section>`;
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
    side.innerHTML = `${wlHtml}${listHtml}<section><h3>Screener — latest</h3>${plans || '<div class="muted small">Not in any screening run.</div>'}</section>
      <section><h3>Decision history</h3>${hist || '<div class="muted small">None.</div>'}</section>`;
    side.querySelectorAll(".wl .cur, .wlp .cur").forEach((c) => c.scrollIntoView({ block: "nearest" }));
    side.querySelectorAll(".wlp a").forEach((a) => a.onclick = () =>
      openChartFromList(market, a.dataset.s, wl.map((e) => e.symbol), "Watchlist", `#/watchlist/${market}`));
  }
}

function symbolSearch(input, list, market, onPick) {
  let timer, items = [], cur = -1;
  const show = () => {
    list.hidden = !items.length || document.activeElement !== input;
    list.innerHTML = items.map((r, i) => `<li data-i="${i}" class="${i === cur ? "sel" : ""}"><b>${esc(r.symbol)}</b><span class="muted">${esc(r.type === "index" ? "Index" : r.sector || "")}</span></li>`).join("");
    const s = list.querySelector(".sel"); if (s) s.scrollIntoView({ block: "nearest" });
  };
  const query = async () => { items = await api(`/api/symbols?market=${market}&q=${encodeURIComponent(input.value)}`).catch(() => []); cur = items.length ? 0 : -1; show(); };
  input.onfocus = () => { input.select(); query(); };
  input.oninput = () => { clearTimeout(timer); timer = setTimeout(query, 100); };
  input.onkeydown = (e) => {
    if (e.key === "ArrowDown") { cur = Math.min(cur + 1, items.length - 1); show(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { cur = Math.max(cur - 1, 0); show(); e.preventDefault(); }
    else if (e.key === "Enter") { e.preventDefault(); const exact = items.find((i) => i.symbol === input.value.trim().toUpperCase()); onPick(exact ? exact.symbol : cur >= 0 ? items[cur].symbol : input.value.trim().toUpperCase()); }
    else if (e.key === "Escape") { list.hidden = true; input.blur(); }
  };
  list.onmousedown = (e) => { const li = e.target.closest("li"); if (li) onPick(items[+li.dataset.i].symbol); };
  input.onblur = () => setTimeout(() => (list.hidden = true), 150);
}

// -------------------------------------------------------------- watchlist

const jsonReq = (method, body) => ({ method, headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
const WL = {
  list: (market) => api(`/api/watchlist${market ? `?market=${market}` : ""}`),
  add: (market, symbol, note) => api("/api/watchlist", jsonReq("POST", { market, symbol, note: note || null })),
  remove: (market, symbol) => api(`/api/watchlist?market=${market}&symbol=${encodeURIComponent(symbol)}`, { method: "DELETE" }),
  note: (market, symbol, note) => api("/api/watchlist/note", jsonReq("PUT", { market, symbol, note: note || null })),
};
const DEC_RANK = (d) => (/^TRADE - HIGH/i.test(d) ? 0 : /^TRADE/i.test(d) ? 1 : /^WATCH/i.test(d) ? 2 : 3);
/** the most actionable plan across the strategies that flagged a name */
const bestPlan = (e) => [...e.strategies].sort((a, b) => DEC_RANK(a.decision) - DEC_RANK(b.decision))[0] || {};
const sourceText = (e) => [...(e.manual ? ["Manual"] : []), ...e.strategies.map((s) => s.strategy)].join(" · ");

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

async function watchlistPage(alive, mkt) {
  mkt = mkt || store.get("wlMarket", "all");
  store.set("wlMarket", mkt);
  document.title = "Watchlist · Trading";
  $view.innerHTML = LOADING;
  const items = await WL.list(mkt === "all" ? null : mkt);
  if (!alive()) return;
  let src = store.get("wlSrc", "all");
  $view.innerHTML = `<div class="page-head"><h1>Watchlist</h1>${segmented([["all", "All"], ["us", "US"], ["india", "India"]], mkt, "mk")}
      <span class="spacer"></span>
      <form class="wl-add" autocomplete="off">
        ${mkt === "all" ? `<select id="wlm" title="Market"><option value="us">US</option><option value="india">India</option></select>` : ""}
        <div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input id="wls" placeholder="Add symbol" spellcheck="false"><ul hidden></ul></div>
        <input id="wln" placeholder="Note (optional)"><button class="primary" type="submit">Add</button>
      </form></div>
    <div class="chips" id="wlsrc"></div><div id="wlt"></div>
    <p class="muted small">Screener names come from the latest full run of each strategy (tradeable or watchlist candidate) and refresh every run.
      Removing one hides it until it drops off the screen and is flagged again. Manual names stay until you remove them.</p>`;
  $view.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(`#/watchlist/${b.dataset.v}`));

  // add form
  const mSel = $view.querySelector("#wlm"), sIn = $view.querySelector("#wls"), nIn = $view.querySelector("#wln");
  const addMarket = () => (mSel ? mSel.value : mkt);
  if (mSel) mSel.value = store.get("lastMarket", "us");
  const wireSearch = () => symbolSearch(sIn, $view.querySelector(".wl-add ul"), addMarket(), (s) => { sIn.value = s; nIn.focus(); });
  wireSearch();
  if (mSel) mSel.onchange = wireSearch;
  $view.querySelector(".wl-add").onsubmit = async (e) => {
    e.preventDefault();
    const sym = sIn.value.trim().toUpperCase(); if (!sym) { sIn.focus(); return; }
    try { const r = await WL.add(addMarket(), sym, nIn.value.trim()); toast(`${r.symbol} added to the watchlist`, "ok"); route(); }
    catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
  };

  const counts = { all: items.length, screener: items.filter((e) => e.strategies.length).length, manual: items.filter((e) => e.manual).length };
  const draw = () => {
    $view.querySelector("#wlsrc").innerHTML = [["all", "All"], ["screener", "From screener"], ["manual", "Added by me"]]
      .map(([v, t]) => `<button class="chip ${v === src ? "on" : ""}" data-s="${v}">${t}<span>${counts[v]}</span></button>`).join("");
    const shown = items.filter((e) => src === "all" || (src === "manual" ? e.manual : e.strategies.length));
    const host = $view.querySelector("#wlt");
    if (!shown.length) {
      host.innerHTML = `<div class="empty"><b>${items.length ? "Nothing in this view" : "Your watchlist is empty"}</b>
        <div class="muted">Add a symbol above, use ☆ on the chart, or run the screener.</div></div>`;
      return;
    }
    const cols = ["symbol", "market", "sector", "last", "chg %", "source", "decision", "entry", "to entry %", "stop", "target R", "note", "added"];
    const rows = shown.map((e) => {
      const p = bestPlan(e);
      return [e.symbol, e.market.toUpperCase(), e.sector || "", e.last, e.change_pct, sourceText(e), p.decision || "", p.entry ?? null,
        p.entry && e.last ? (p.entry / e.last - 1) * 100 : null, p.stop ?? null, p.target_r ?? null, e.note || "", e.added_at];
    });
    dataTable(host, cols, rows, {
      name: `watchlist_${mkt}`, sort: ["added", -1], format: { added: prettyDate },
      rowClick: (row, visible) => {
        const m = row[1].toLowerCase();
        openChartFromList(m, row[0], visible.filter((r) => r[1] === row[1]).map((r) => r[0]), "Watchlist", location.hash);
      },
      actions: [
        { key: "note", title: "Edit note", icon: ICON_NOTE, fn: async (row) => {
          const e = shown.find((x) => x.symbol === row[0] && x.market === row[1].toLowerCase());
          const v = await askText(`Note — ${row[0]}`, e.note || "", "e.g. wait for earnings, breakout above 120");
          if (v === null) return;
          await WL.note(e.market, e.symbol, v.trim()); toast("Note saved", "ok"); route();
        } },
        { key: "rm", title: "Remove from watchlist", icon: ICON_X, fn: async (row) => {
          await WL.remove(row[1].toLowerCase(), row[0]); toast(`${row[0]} removed`, "ok"); route();
        } },
      ],
    });
  };
  $view.querySelector("#wlsrc").onclick = (e) => { const b = e.target.closest("[data-s]"); if (b) { src = b.dataset.s; store.set("wlSrc", src); draw(); } };
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
  const groups = [["screener", "Screening strategies"], ["benchmark", "Benchmark"]].map(([k, t]) => {
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
  const toc = [["overview", "Overview"], ["rules", d.gates.length ? "Rules" : ""], ["entry", d.entry_rules.length ? "Entry & exit" : ""], ["params", "Parameters"],
    ["decisions", d.decisions.length ? "Decisions" : ""], ["results", "Results"], ["commands", "Commands"], ["caveats", "Caveats"]].filter((t) => t[1]);

  $view.innerHTML = `<div class="rep-layout"><aside class="rep-nav strat-nav">${groups}</aside><section class="sdoc">
    <div class="crumbs"><a href="#/strategies">Strategies</a> / ${esc(d.kind === "benchmark" ? "Benchmark" : "Screening strategy")}</div>
    <div class="page-head"><h1>${esc(d.name)}</h1><code>${esc(d.key)}</code>
      ${d.kind === "screener" ? `<span class="spacer"></span><a class="btn" href="#/screening/us/${key}">Latest screening →</a>` : ""}</div>
    ${d.status ? `<div class="sd-status ${statusClass(d.status)}"><b>Status</b> ${mdInline(d.status)}</div>` : ""}
    <p class="sd-lead">${mdInline(d.description)}</p>
    <nav class="sd-toc">${toc.map(([id, t]) => `<a data-sec="sd-${id}">${t}</a>`).join("")}</nav>
    ${sec("overview", "Overview", `${d.thesis ? `<p><b>Thesis.</b> ${mdInline(d.thesis)}</p>` : ""}<h3>How it works</h3>${ol(d.how_it_works)}`)}
    ${d.gates.length || d.watch.length || d.setups.length ? `<section class="sd-sec" id="sd-rules"><h2>Rules</h2>
      ${d.gates.length ? `<h3>Hard gates <span class="muted small">— all must pass, or the stock is AVOID</span></h3>${codeTable(d.gates, "Gate")}` : ""}
      ${d.watch.length ? `<h3>Watch flags <span class="muted small">— don't disqualify, but cap or downgrade the decision</span></h3>${codeTable(d.watch, "Flag")}` : ""}
      ${d.setups.length ? `<h3>Setups <span class="muted small">— the patterns that make a stock entry-eligible</span></h3>${codeTable(d.setups, "Setup")}` : ""}
      <p class="muted small">These codes are the <code>gate_*</code>, <code>watch_*</code> and <code>setup_*</code> columns on the Screening page.</p></section>` : ""}
    ${sec("entry", "Entry & exit", `${d.entry_rules.length ? `<h3>Entry, stop and target</h3>${ol(d.entry_rules)}` : ""}${d.exit_rules.length ? `<h3>Exit</h3>${ol(d.exit_rules)}` : ""}`)}
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

const SCREEN_COLS = ["symbol", "sector", "decision", "price", "entry", "stop", "risk_pct", "target_r", "setup_quality",
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
async function route() {
  cleanup(); cleanup = () => {};
  // a new page opens at the top; re-rendering the same page (indicator change, refresh) keeps the scroll
  if (location.hash !== lastRoute) { window.scrollTo(0, 0); lastRoute = location.hash; }
  const seq = ++navSeq, alive = () => seq === navSeq;
  const parts = location.hash.replace(/^#\//, "").split("/").map(decodeURIComponent);
  const page = parts[0] || "chart";
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("active", a.dataset.nav === page));
  document.body.dataset.page = page;
  try {
    if (page === "chart") await chartPage(alive, parts[1], parts[2], parts[3]);
    else if (page === "screening") await screeningPage(alive, parts[1], parts[2], parts[3]);
    else if (page === "watchlist") await watchlistPage(alive, parts[1]);
    else if (page === "strategies") await strategiesPage(alive, parts[1]);
    else if (page === "reports") await (parts[1] ? reportPage(alive, parts[1], parts[2]) : reportsPage(alive));
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
  <dt>⌘ / Ctrl + Z</dt><dd>Undo the last drawing change</dd><dt>?</dt><dd>Show this help</dd></dl>
  <button class="ghost">Close</button></div></div>`);
document.body.append(HELP);
HELP.onclick = (e) => { if (e.target === HELP || e.target.tagName === "BUTTON") HELP.hidden = true; };
document.addEventListener("keydown", (e) => {
  if ((e.key === "?" || (e.key === "/" && e.shiftKey)) && !e.target.closest?.("input, select, textarea")) { HELP.hidden = !HELP.hidden; e.preventDefault(); e.stopImmediatePropagation(); }
  else if (e.key === "Escape") HELP.hidden = true;
}, true);
document.getElementById("help").onclick = () => (HELP.hidden = false);
route();
