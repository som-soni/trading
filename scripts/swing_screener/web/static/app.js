"use strict";
const $view = document.getElementById("view");
const LC = LightweightCharts;
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};
const _fetchJson = async (url, init) => {
  const r = await fetch(url, init);
  if (!r.ok) throw new Error(`${r.status} ${(await r.json().catch(() => ({}))).detail || r.statusText}`);
  return r.text();
};
/* Page data is kept for a while (stale-while-revalidate): coming back to a tab draws it at once from the
 * last copy, while a fresh copy loads behind it; if that differs, the page redraws in place (same URL, so
 * the scroll is kept) — unless you are typing in a field. Live endpoints (status, queue, the wait poll,
 * notes, schedules, search) are never cached, and any write clears the cache, so an edit is never hidden
 * behind an older copy. */
const API_CACHE = new Map();                 // url -> {t: ms, text}
const API_CACHE_MAX_MS = 10 * 60e3, API_REVALIDATE_AFTER_MS = 15e3;
const CACHEABLE = /^\/api\/(postmarket|breadth|sectors|movers|screens|setups|quality|strategies|company|fundamentals|news|reports|prices|vcp|trade|watchlists)\b/;
const _revalidating = new Set();
const api = async (url, init) => {
  const method = (init?.method || "GET").toUpperCase();
  if (method !== "GET") { const text = await _fetchJson(url, init); API_CACHE.clear(); return JSON.parse(text); }
  if (!CACHEABLE.test(url)) return JSON.parse(await _fetchJson(url, init));
  const hit = API_CACHE.get(url), now = Date.now();
  if (hit && now - hit.t < API_CACHE_MAX_MS) {
    if (now - hit.t > API_REVALIDATE_AFTER_MS && !_revalidating.has(url)) {
      _revalidating.add(url);
      const hash = location.hash;
      _fetchJson(url, init).then((text) => {
        const changed = text !== hit.text;
        API_CACHE.set(url, { t: Date.now(), text });
        const typing = document.activeElement?.closest?.("input, textarea, select, [contenteditable]");
        if (changed && location.hash === hash && !typing) route();
      }).catch(() => {}).finally(() => _revalidating.delete(url));
    }
    return JSON.parse(hit.text);
  }
  const text = await _fetchJson(url, init);
  API_CACHE.set(url, { t: Date.now(), text });
  return JSON.parse(text);
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const el = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; };
/** Loading state: a skeleton shaped like a page (title, cards, table rows) instead of a bare spinner;
 *  a note appears if it takes more than a few seconds, so slow never looks broken. */
const LOADING = `<div class="skel" aria-busy="true" aria-label="Loading"><div class="sk-h"></div>
  <div class="sk-cards"><i></i><i></i><i></i></div><div class="sk-rows">${"<i></i>".repeat(7)}</div>
  <div class="sk-note muted small"><span class="spin"></span>Still working — the first load after new data can take a few seconds.</div></div>`;
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
/** status → badge variant. Five variants only (style.css): positive (trade / ok / leading), warning (watch /
 *  behind / weakening), negative (avoid / failed / lagging), info (running / improving), neutral (the rest). */
const decisionClass = (d) => /^TRADE/i.test(d) ? "trade" : /^WATCH/i.test(d) ? "watch" : /^AVOID/i.test(d) ? "avoid" : "neutral";
/** what each decision state means — shown on hover wherever a decision tag appears */
const DECISION_HELP = [
  [/^TRADE\W*HIGH/i, "TRADE — HIGH CONFIDENCE: every gate passed and the entry signal has already fired. Take the trade at the plan's entry, with its stop."],
  [/^TRADE ON TRIGGER/i, "TRADE ON TRIGGER: the setup is valid but has not fired yet. Place the order at the entry price; it only fills if price gets there."],
  [/^WATCH/i, "WATCH — WAIT: a setup is forming or a watch flag caps it (extended, earnings near, weak volume…). Keep it on the list; do not buy yet."],
  [/^AVOID/i, "AVOID: a hard gate failed (trend, liquidity, risk too wide…). Not a trade for this strategy today."],
  [/^NO SETUP/i, "NO SETUP: the stock passed the screen but shows none of this strategy's setups today."],
];
const decisionHelp = (d) => (DECISION_HELP.find(([re]) => re.test(String(d || ""))) || [null, ""])[1];
const decisionTag = (d) => `<span class="tag ${decisionClass(d)}" title="${esc(decisionHelp(d))}">${esc(d)}</span>`;
/** "TC-01 / A (Plan A (pullback))" -> "TC-01 · Plan A pullback": the setup code, then the plan in plain words
 *  (the stored string keeps the old nested form; the full text stays in the tooltip) */
function setupFmt(s) {
  const m = String(s ?? "").match(/^(\S+) \/ (\S+) \((.*)\)$/);
  if (!m) return String(s ?? "");
  const [, code, plan, reason] = m;
  const why = reason.replace(/\(([^()]*)\)/g, "$1").replace(new RegExp(`^${code.replace(/[-.]/g, "\\$&")}[:\\s]+`), "").trim();
  if (!/^[A-Z]$/.test(plan) || new RegExp(`\\bplan ${plan}\\b`, "i").test(why)) return why ? `${code} · ${why}` : code;
  return `${code} · Plan ${plan}${why ? " — " + why : ""}`;
}
/** header tooltips: what a column means, where its name alone does not say */
const COL_HELP = {
  group_rs: "Group RS: the RS rating (1–99) of the stock's peer group — its sub-industry, else its industry group — against every other group. 80+ leading, under 50 lagging.",
  peer_rs: "Group RS: the RS rating (1–99) of the stock's peer group — its sub-industry, else its industry group — against every other group. 80+ leading, under 50 lagging.",
  peer_rank: "The stock's place among its peer group's tradable stocks by RS rank (1 = strongest).",
  rs_rank: "RS rank: the stock's relative strength (1–99) against every stock in the market — 40% the last quarter, 20% each of the three before.",
  decision: "The strategy's verdict today. Hover a decision for what it means.",
  setup: "The setup code and the entry plan it produced.", strategy_setup: "The setup code and the entry plan it produced.",
};
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
  rs_vs_benchmark: "RS vs index", rank: "#", rs: "RS", sepa: "SEPA", rs_vs_sector: "RS vs sector", rsi: "RSI", adx: "ADX", earnings_in: "Earnings in (d)",
  wait_for: "Wait for", reason: "Reason", entry_date: "Entry date", entry_price: "Entry price", exit_date: "Exit date",
  exit_price: "Exit price", exit_reason: "Exit", r_multiple: "R", holding_days: "Days held", pnl: "P&L",
  initial_stop: "Initial stop", drawdown_pct: "Drawdown %", positions_open: "Open positions",
  "cagr %": "CAGR %", "excess cagr %": "Excess CAGR %", "max dd %": "Max DD %", market: "Market", strategy: "Strategy", run: "Run",
  last: "Last", "chg %": "Chg %", quality: "Quality", f: "F", "roic / roe": "ROIC / ROE", "rev growth": "Rev growth", "eps growth": "EPS growth",
  "op margin": "Op margin", "fcf conv": "FCF conv", "net debt/ebitda": "Net debt/EBITDA", "p/e": "P/E", "p/e vs own": "P/E vs own", "fcf yield": "FCF yield",
  peg: "PEG", "off 52w high": "Off 52w high", "vs 200d": "vs 200D", value: "Value", zone: "Zone", "buy below": "Buy below", signals: "Signals", name: "Company", source: "Source", "to entry %": "To entry %", note: "Note", added: "Added", "target R": "Target R",
  peer_group: "Peer group", group_rs: "Group RS", peer_rs: "Group RS", peer_rank: "Rank in group",
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
  // hidden columns: the page's default, or what you chose with the Columns menu (remembered per table)
  const colKey = opts.name ? `cols:${opts.name.replace(/_(us|india|both|all)$/, "")}` : null;
  const saved = colKey ? store.get(colKey, null) : null;
  const hidden = new Set((saved || opts.hidden || []).map((c) => columns.indexOf(c)).filter((i) => i > 0));
  // the company name sits under the symbol in one cell (one column fewer, no truncated names)
  const stack = !opts.noStack && /^(name|company)$/i.test(columns[1] || "");
  if (stack) hidden.add(1);
  let sortCol = opts.sort ? columns.indexOf(opts.sort[0]) : -1, sortDir = opts.sort ? opts.sort[1] : 1;
  let filter = "", limit = opts.limit || 300, visible = [];
  host.innerHTML = `<div class="tbar"><label class="filter"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg>
      <input placeholder="Filter rows" spellcheck="false"></label><span class="muted count"></span>
      ${opts.rowClick && opts.rowHint !== false ? `<span class="muted small rowhint">${esc(opts.rowHint || "Click a row to open its chart — ↑ / ↓ there step through this list")}</span>` : ""}<span class="spacer"></span>
      <span class="hscroll" hidden><button class="sm" data-dir="-1" title="Scroll to the columns on the left">‹ <span></span></button><button class="sm" data-dir="1" title="Scroll to the columns on the right"><span></span> ›</button></span>
      <span class="menu"><button class="sm colsbtn" title="Choose which columns to show">Columns</button><div class="menu-pop cols-pop" hidden></div></span>
      <button class="sm csv" title="Download the rows shown as CSV">Export CSV</button></div>
    <div class="tablefade"><div class="tablewrap"><table class="data"><thead></thead><tbody></tbody></table></div></div>
    <div class="tfoot"><button class="more" hidden>Show more</button></div>`;
  const thead = host.querySelector("thead"), tbody = host.querySelector("tbody");
  const more = host.querySelector(".more"), count = host.querySelector(".count");
  let cols = columns.map((c, i) => i).filter((i) => !hidden.has(i));
  const wrap = host.querySelector(".tablewrap"), fade = host.querySelector(".tablefade");
  // pin the company name next to the symbol when it is the second column
  const pin2 = () => {
    const nameCol = cols[1] != null && /^(name|company)$/i.test(columns[cols[1]]);
    fade.classList.toggle("pin2", nameCol);
    if (nameCol) { const th = thead.querySelector("th"); if (th) fade.style.setProperty("--c1w", th.getBoundingClientRect().width + "px"); }
  };
  // fade the edge that has more columns behind it, and say how many are off-screen on each side: the native
  // scrollbar sits at the bottom of a long table and (on macOS) only shows while scrolling, so it is no hint
  const hs = host.querySelector(".hscroll"), [hsL, hsR] = hs.querySelectorAll("button");
  const edges = () => {
    const r = wrap.scrollLeft + wrap.clientWidth < wrap.scrollWidth - 2, l = wrap.scrollLeft > 2;
    fade.classList.toggle("more-r", r);
    fade.classList.toggle("more-l", l);
    hs.hidden = !(r || l);
    if (hs.hidden) return;
    const box = wrap.getBoundingClientRect(), ths = [...thead.querySelectorAll("th")];
    const pinned = parseFloat(getComputedStyle(fade).getPropertyValue("--c1w")) || (ths[0]?.getBoundingClientRect().width || 0);
    const offR = ths.filter((th) => th.getBoundingClientRect().right > box.right + 2).length;
    const offL = ths.slice(1).filter((th) => th.getBoundingClientRect().left < box.left + pinned - 2).length;
    hsR.disabled = !r; hsL.disabled = !l;
    hsR.querySelector("span").textContent = offR ? `${offR} more` : "";
    hsL.querySelector("span").textContent = offL ? `${offL}` : "";
  };
  hs.onclick = (e) => { const b = e.target.closest("button[data-dir]"); if (b) wrap.scrollBy({ left: +b.dataset.dir * wrap.clientWidth * 0.7, behavior: "smooth" }); };
  wrap.addEventListener("scroll", edges, { passive: true });
  // the table too: filling or re-filtering it changes its width without resizing the wrap
  const ro = new ResizeObserver(() => { pin2(); edges(); });
  ro.observe(wrap); ro.observe(host.querySelector("table.data"));
  const pop = host.querySelector(".cols-pop");
  host.querySelector(".colsbtn").onclick = (e) => {
    e.stopPropagation();
    if (!pop.hidden) { pop.hidden = true; return; }
    pop.innerHTML = columns.map((c, i) => stack && i === 1 ? "" : `<label><input type="checkbox" data-i="${i}" ${hidden.has(i) ? "" : "checked"} ${i === 0 ? "disabled" : ""}> ${esc(label(c))}</label>`).join("")
      + `<button class="ghost small" data-reset>Reset to default</button>`;
    pop.hidden = false;
    const close = (ev) => { if (!pop.contains(ev.target)) { pop.hidden = true; document.removeEventListener("click", close); } };
    setTimeout(() => document.addEventListener("click", close));
  };
  pop.onchange = (e) => {
    const i = +e.target.dataset.i; e.target.checked ? hidden.delete(i) : hidden.add(i);
    cols = columns.map((c, j) => j).filter((j) => !hidden.has(j));
    if (colKey) store.set(colKey, [...hidden].map((j) => columns[j]));
    header(); draw();
  };
  pop.onclick = (e) => {
    if (!e.target.closest("[data-reset]")) return;
    hidden.clear(); (opts.hidden || []).forEach((c) => { const j = columns.indexOf(c); if (j > 0) hidden.add(j); }); if (stack) hidden.add(1);
    if (colKey) store.set(colKey, null);
    cols = columns.map((c, j) => j).filter((j) => !hidden.has(j)); pop.hidden = true; header(); draw();
  };
  const numeric = columns.map((_, i) => rows.some((r) => typeof r[i] === "number"));
  // symbols show without the data provider's suffix (RELIANCE, not RELIANCE.NS); the market badge says where it trades
  const bareSym = (v) => { const x = String(v ?? ""); const sfx = MKTS.find((m) => m.suffix && x.endsWith(m.suffix)); return sfx ? x.slice(0, -sfx.suffix.length) : x; };
  // peer-group columns, wherever they appear: the short name (sub-industry, else industry group) and a coloured RS badge
  const isPeer = (c) => /^(peer_group|peer group)$/i.test(c), isGrpRs = (c) => /^(group_rs|peer_rs|peer group rs)$/i.test(c);
  const isSetup = (c) => /^(setup|strategy_setup)$/i.test(c);
  const peerFmt = (v) => (v ? String(v).split(" › ").at(-1) : "");
  const fmtFor = columns.map((c) => (opts.format && opts.format[c]) || (c === "symbol" ? bareSym : isPeer(c) ? peerFmt : fmt));
  const autoTags = Object.fromEntries(columns.filter(isGrpRs).map((c) => [c, (v) => (v >= 80 ? "pos" : v >= 50 ? "warn" : "neg")]));
  opts = { ...opts, tags: { ...autoTags, ...(opts.tags || {}) } };
  const header = () => {
    thead.innerHTML = "<tr>" + cols.map((i) => `<th data-i="${i}" class="${numeric[i] ? "num" : ""}" title="${esc(COL_HELP[columns[i]] || label(columns[i]))}">${esc(label(columns[i]))}` +
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
        if (i === decCol && v) return `<td>${decisionTag(v)}</td>`;
        if (isSetup(columns[i]) && v) return `<td title="${esc(v)}">${esc(setupFmt(v))}</td>`;
        if (stack && i === cols[0]) return `<td class="symcell"><div title="${esc(row[1] || "")}"><b>${esc(fmtFor[i](v, row))}</b>${row[1] ? `<span>${esc(row[1])}</span>` : ""}</div></td>`;
        if (opts.tags && opts.tags[columns[i]] && v) return `<td><span class="tag ${opts.tags[columns[i]](v)}"${isGrpRs(columns[i]) ? ` title="Group RS ${esc(v)} — ${esc(RS_WORDS(v))}"` : ""}>${esc(v)}</span></td>`;
        let cls = typeof v === "number" ? "num" : "";
        if (typeof v === "number" && (opts.inverse || []).includes(columns[i])) cls += v < 0 ? " pos" : v > 0 ? " neg" : "";  // lower is better
        else if (typeof v === "number" && (SIGNED_COL.test(columns[i]) || (opts.signed || []).includes(columns[i]))) cls += v < 0 ? " neg" : v > 0 ? " pos" : "";
        if (typeof v === "boolean") cls += v ? " yes" : " no";
        return `<td class="${cls}"${typeof v === "string" && (v.length > 40 || isPeer(columns[i])) ? ` title="${esc(v)}"` : ""}>${esc(fmtFor[i](v, row))}</td>`;
      }).join("") + (opts.actions ? `<td class="acts">${opts.actions.map((a) => `<button class="ghost icon" data-act="${a.key}" title="${esc(a.title)}">${a.icon}</button>`).join("")}</td>` : "") + "</tr>").join("");
    more.hidden = visible.length <= limit;
    more.textContent = `Show ${Math.min(500, visible.length - limit).toLocaleString()} more`;
    requestAnimationFrame(() => { pin2(); edges(); });
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
function openChartFromList(market, symbol, symbols, labelText, back, setup = null, backtest = null) {
  const seen = new Set(), items = [];
  for (const x of symbols) {
    const it = typeof x === "string" ? { m: market, s: x } : { m: x.market, s: x.symbol };
    const k = it.m + ":" + it.s;
    if (!seen.has(k)) { seen.add(k); items.push(it); }
  }
  // setup: {strategy, date, patterns: {symbol: pattern name}} when the list is a strategy run's setups, so the
  // chart can draw each stock's pattern as of that run without the user adding the indicator
  // backtest: {run, strategy} when the list is a backtest's trades — the chart opens in its backtest view
  store.set("chartList", { items, label: labelText, back, fresh: true, setup, backtest: backtest && { ...backtest, arrive: true } });   // fresh: open the list panel on arrival
  go(`#/chart/${market}/${encodeURIComponent(symbol)}`);
}
/** The markets, from config (GET /api/markets) — the selector, badges and currency all come from this list,
 *  so a new country needs no UI change. The two defaults only cover the moment before it loads. */
let MKTS = [{ key: "us", name: "US", exchange: "NYSE · Nasdaq", badge: "US", flag: "🇺🇸", currency: "$", suffix: "" },
  { key: "india", name: "India", exchange: "NSE", badge: "NSE", flag: "🇮🇳", currency: "₹", suffix: ".NS" }];
const MKT_BADGE = Object.fromEntries(MKTS.map((m) => [m.key, m.badge]));
const isMarket = (m) => MKTS.some((x) => x.key === m);
const mktInfo = (m) => MKTS.find((x) => x.key === m) || MKTS[0];
const WL_COLS = [["symbol", "Symbol"], ["last", "Last"], ["chg", "Chg"], ["change_pct", "Chg%"]];
/** absolute day change of a watchlist row (the API gives last close and % change) */
const chgOf = (e) => (e.last != null && e.change_pct != null ? e.last - e.last / (1 + e.change_pct / 100) : null);

/** The market is one remembered setting shared by every market-scoped page: a page opened without one
 *  in its URL shows the market you last chose anywhere, and choosing one on any page sets it everywhere.
 *  There is no global selector — each market-scoped page shows its own switcher (marketSeg), because
 *  plenty of pages (watchlists, reports, status…) cover every market at once and a header control
 *  would claim an authority it does not have there. `extra` are page-specific combined views
 *  ("both", "all") — kept in the URL only, never remembered as the market. */
function pageMarket(m, extra = []) {
  if (isMarket(m)) { if (store.get("market", null) !== m) store.set("market", m); return m; }
  const g = store.get("market", MKTS[0].key);
  return extra.includes(m) ? m : isMarket(g) ? g : MKTS[0].key;
}
/** The market switcher, rendered by each market-scoped page next to its title: every market, plus the
 *  page's own combined views (e.g. [["both", "US + India"]]). Pages wire `.mk button` themselves,
 *  since switching usually means navigating to the market's own URL. */
function marketSeg(m, extra = []) {
  return segmented([...MKTS.map((x) => [x.key, `${x.flag} ${esc(x.name)}`]), ...extra], m, "mk") + freshBadge(m);
}
/** "data through 13 Oct" beside the market toggle — amber when that market's prices are behind — so the
 *  staleness the Status page reports is visible where you act on the data. Filled from the status check
 *  the header already makes (FRESH); repainted in place when that check comes back. */
let FRESH = null;
function freshBadgeInner(m, flag = false) {
  const p = FRESH?.[m]?.items?.find((i) => i.key === "prices");
  if (!p || !p.date) return "";
  const behind = p.status && p.status !== "ok";
  const short = behind ? (String(p.text || "").split(/ — | · /)[0] || "behind") : "";
  return `<span class="freshb ${behind ? "warn" : ""}" title="${esc(`${FRESH[m].name || m}: prices ${prettyDate(p.date)} — ${p.text || ""}. System → Status for details.`)}">${flag ? `${mktInfo(m).flag || ""} ` : ""}data through ${esc(prettyDate(p.date).replace(/ \d{4}$/, ""))}${behind ? ` · ${esc(short)}` : ""}</span>`;
}
const freshBadge = (m, flag = false) => (MKTS.some((x) => x.key === m) ? `<a class="freshwrap" href="#/status" data-fm="${esc(m)}" ${flag ? "data-flag" : ""}>${freshBadgeInner(m, flag)}</a>` : "");
/** every market, with its flag: for pages that mix markets (Watchlists) */
const freshBadges = () => MKTS.map((x) => freshBadge(x.key, true)).join("");
function paintFresh() { document.querySelectorAll(".freshwrap[data-fm]").forEach((a) => { a.innerHTML = freshBadgeInner(a.dataset.fm, a.hasAttribute("data-flag")); }); }
api("/api/markets").then((xs) => { if (xs?.length) { MKTS = xs; Object.assign(MKT_BADGE, Object.fromEntries(xs.map((m) => [m.key, m.badge]))); } }).catch(() => {});
/** ⓘ — an explanation kept out of the way: a small button that opens the text in a popover.
 *  `html` is trusted markup built by the page (escape any data inside it); `label` turns it into a text button. */
const INFO = new Map();
let infoSeq = 0;
function info(html, label = "") {
  const id = `i${++infoSeq}`; INFO.set(id, html);
  if (INFO.size > 400) INFO.delete(INFO.keys().next().value);
  return label ? `<button class="info-link" data-info="${id}">${esc(label)}</button>`
    : `<button class="info" data-info="${id}" aria-label="What is this?" title="What is this?">i</button>`;
}
{
  const pop = el(`<div class="infopop" hidden></div>`); document.body.append(pop);
  let cur = null;
  const close = () => { pop.hidden = true; cur = null; };
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-info]");
    if (!b) { if (!pop.contains(e.target)) close(); return; }
    e.preventDefault(); e.stopPropagation();
    if (cur === b) return close();
    cur = b; pop.innerHTML = INFO.get(b.dataset.info) || ""; pop.hidden = false;
    const r = b.getBoundingClientRect(), w = pop.offsetWidth;
    pop.style.left = `${Math.max(8, Math.min(innerWidth - w - 8, r.left))}px`;
    pop.style.top = `${r.bottom + 6 + window.scrollY}px`;
  }, true);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  addEventListener("hashchange", close);
}
/** The page header band, the same on every page: title, then the page's context controls (date, view),
 *  then — pushed right — its actions. */
function pageHead(title, { context = "", actions = "", extra = "" } = {}) {
  return `<div class="page-head"><h1>${title}</h1>${extra}${context ? `<div class="ph-ctx">${context}</div>` : ""}<span class="spacer"></span>${actions ? `<div class="ph-act">${actions}</div>` : ""}</div>`;
}
/** One date control for every dated page: ‹ older · the date (every date in the list) · newer ›, a Latest
 *  button when you are not on the newest, and how many there are. `dates`: [{value, label}], newest first. */
function datePicker(dates, cur, noun = "sessions") {
  const i = Math.max(0, dates.findIndex((d) => d.value === cur));
  return `<div class="dpick"><button class="ghost icon dp-prev" ${i >= dates.length - 1 ? "disabled" : ""} title="Older">‹</button>
    <select class="dp-sel" aria-label="Date">${dates.map((d, j) => `<option value="${esc(d.value)}" ${j === i ? "selected" : ""}>${esc(d.label)}${j === 0 ? " · latest" : ""}</option>`).join("")}</select>
    <button class="ghost icon dp-next" ${i <= 0 ? "disabled" : ""} title="Newer">›</button>
    ${i > 0 ? `<button class="ghost dp-latest" title="Jump to the newest">Latest</button>` : ""}<span class="muted small dp-n">${i + 1} of ${dates.length} ${noun}</span></div>`;
}
/** wire a datePicker inside `root`: onPick(value, isLatest) */
function wireDatePicker(root, dates, cur, onPick) {
  const dp = root.querySelector(".dpick"); if (!dp) return;
  const i = Math.max(0, dates.findIndex((d) => d.value === cur));
  const pick = (j) => onPick(dates[j].value, j === 0);
  dp.querySelector(".dp-prev").onclick = () => i < dates.length - 1 && pick(i + 1);
  dp.querySelector(".dp-next").onclick = () => i > 0 && pick(i - 1);
  dp.querySelector(".dp-latest")?.addEventListener("click", () => pick(0));
  dp.querySelector(".dp-sel").onchange = (e) => pick(e.target.selectedIndex);
}
/** a remembered page URL, with its market switched to the current one (the market follows you between pages) */
function withMarket(hash) {
  const m = store.get("market", "us");
  if (/^#\/(chart|watchlist|reports|notes)\b/.test(hash)) return hash;   // there the market belongs to a symbol or record, not the view
  return hash.split("/").map((x) => (isMarket(x) ? m : x)).join("/");
}
/** The one back-link style: "← Where you came from" in a row above the page title (extra links after it). */
const backLink = (href, label, extra = "") => `<div class="crumbs back"><a href="${href}">← ${esc(label)}</a>${extra}</div>`;
function segmented(options, current, cls = "") {
  return `<div class="seg ${cls}">${options.map(([v, t]) => `<button data-v="${esc(v)}" class="${v === current ? "on" : ""}">${t}</button>`).join("")}</div>`;
}

// ------------------------------------------------------------ chart page

/** a theme token's current value (style.css :root), so charts follow the theme */
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
/** a #rrggbb colour with an alpha, for chart fills */
const alpha = (hex, a) => { const n = parseInt(hex.replace("#", ""), 16); return `rgba(${n >> 16 & 255},${n >> 8 & 255},${n & 255},${a})`; };
function chartTheme() {
  return {
    layout: { background: { color: cssVar("--panel") }, textColor: cssVar("--chart-text"), fontSize: 11, panes: { separatorColor: cssVar("--line-2"), separatorHoverColor: cssVar("--line-3") } },
    grid: { vertLines: { color: cssVar("--chart-grid") }, horzLines: { color: cssVar("--chart-grid") } },
    rightPriceScale: { borderColor: cssVar("--line-2") }, timeScale: { borderColor: cssVar("--line-2"), rightOffset: 6, minBarSpacing: 0.05 },
  };
}
let keepView = null;
const ALL_BARS = 100000;  // i.e. everything in the database: the chart shows the full stored history
// strategy keys for the "Screener levels" indicator's setting (fetched once; the page still works without it)
// Fetched once and kept as a promise: a setups layer is NAMED for its strategy, and the chart can
// render before this lands — awaiting it is what stops the control flashing the raw key.
const STRATEGIES = api("/api/strategies").then((xs) => {
  Studies.setStrategies(xs.filter((x) => x.kind === "screener").map((x) => x.key));
  Studies.setStrategyNames(Object.fromEntries(xs.map((x) => [x.key, x.name])));
  return xs;
}).catch(() => []);  // visible range to restore when the chart is rebuilt for an indicator change
const BENCH = { us: "SPY", india: "NIFTY50" };

/** Key events on a price chart, the TradingView way: a row of lettered badges along the bottom of the
 *  price pane — E earnings / results, D ex-dividend (only those two, as on TradingView; splits and
 *  bonuses stay in the News & events panel) — each under the bar it falls on
 *  (upcoming ones in the empty space right of the last bar, hollow). Hover shows a card with the
 *  details (a past report with that quarter's EPS and revenue from `quarters`, the stored quarterly
 *  results; the next one with its EPS estimate); click calls onOpen. Returns { set(events), destroy() }. */
function eventStrip({ chart, chartEl, times, tf, market, quarters, onOpen }) {
  const KIND = { earnings: "E", results: "E", dividend: "D" };
  const NAME = { E: "Earnings", D: "Dividend" };
  const today = new Date().toISOString().slice(0, 10), last = times.at(-1);
  const strip = document.createElement("div"); strip.className = "ev-strip";
  const tip = document.createElement("div"); tip.className = "ev-tip"; tip.hidden = true;
  chartEl.append(strip, tip);
  let groups = [];
  const days = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 864e5);
  // bars between the last bar and a future date (weekdays / weeks / months), for an upcoming event
  const barsAhead = (d) => {
    if (tf === "W") return Math.max(1, Math.ceil(days(last, d) / 7));
    if (tf === "M") return Math.max(1, (+d.slice(0, 4) - +last.slice(0, 4)) * 12 + (+d.slice(5, 7) - +last.slice(5, 7)));
    let n = 0; for (let t = Date.parse(last) + 864e5; t <= Date.parse(d); t += 864e5) { const w = new Date(t).getUTCDay(); if (w && w < 6) n++; }
    return Math.max(1, n);
  };
  const pct = (v) => (v == null ? "" : `${v >= 0 ? "+" : "−"}${Math.abs(v * 100).toFixed(0)}% YoY`);
  const num = (v) => (v == null ? "—" : (+v).toFixed(2));
  // the quarter a report covers: the latest quarter that ended in the ~4 months before it
  const quarterOf = (d) => [...quarters].reverse().find((q) => q.end < d && days(q.end, d) <= 120);
  const card = (e) => {
    const L = KIND[e.kind], up = e.date >= today, det = e.detail || {}, rows = [];
    if (L === "E" && up) {
      const lastQ = quarters.at(-1), yago = lastQ && days(lastQ.end, e.date) <= 160 ? quarters.at(-4) : null;
      if (det.eps_estimate != null) rows.push(["EPS estimate", num(det.eps_estimate) + (det.eps_low != null ? ` <span class="muted">(${num(det.eps_low)} – ${num(det.eps_high)})</span>` : "")]);
      if (yago && det.eps_estimate != null && yago.eps > 0) rows.push(["vs year-ago quarter", `${num(yago.eps)} → ${pct(det.eps_estimate / yago.eps - 1)}`]);
    } else if (L === "E") {
      const q = quarterOf(e.date);
      if (q) {
        rows.push(["Quarter", `${esc(q.fiscal || "")} <span class="muted">to ${prettyDate(q.end)}</span>`]);
        rows.push(["EPS", `${num(q.eps)} <span class="${q.eps_g > 0 ? "up" : q.eps_g < 0 ? "dn" : "muted"}">${pct(q.eps_g)}</span>`]);
        if (q.rev != null) rows.push(["Revenue", `${moneyShort(q.rev, market)} <span class="${q.rev_g > 0 ? "up" : q.rev_g < 0 ? "dn" : "muted"}">${pct(q.rev_g)}</span>`]);
      }
    } else if (L === "D") {
      if (det.amount != null) rows.push(["Amount", `${(MKTS.find((m) => m.key === market) || {}).currency || ""}${(+det.amount).toFixed(det.amount < 1 ? 3 : 2)} per share`]);
      if (det.pay_date) rows.push(["Pay date", prettyDate(det.pay_date)]);
      if (det.record_date) rows.push(["Record date", esc(det.record_date)]);
    }
    const when = up ? `${prettyDate(e.date)} · in ${days(today, e.date)} days` : prettyDate(e.date);
    return `<div class="ev-card"><div class="ev-h"><i class="ev-ic ${L}${up ? " soon" : ""}">${L}</i><b>${up ? "Upcoming " + NAME[L].toLowerCase() : NAME[L]}</b><span class="muted">${when}</span></div>
      ${rows.length ? `<table>${rows.map(([k, v]) => `<tr><td class="muted">${k}</td><td>${v}</td></tr>`).join("")}</table>` : ""}
      <div class="ev-t muted">${esc(e.title)}${e.source ? ` · ${esc(e.source)}` : ""}</div></div>`;
  };
  // colour: a past report by EPS growth vs the year-ago quarter (no consensus history is stored, so
  // not beat / miss as on TradingView); upcoming events hollow
  const tone = (e) => {
    if (e.date >= today) return "soon";
    if (KIND[e.kind] !== "E") return "";
    const q = quarterOf(e.date);
    return q?.eps_g > 0 ? "pos" : q?.eps_g < 0 ? "neg" : "";
  };
  const set = (events) => {
    const by = new Map();
    for (const e of events) {
      const L = KIND[e.kind]; if (!L) continue;
      let t, ahead = 0;
      if (e.date > last) { if (e.date < today) continue; ahead = barsAhead(e.date); t = e.date; }   // a past date after the last bar: data gap
      else { t = times.find((x) => x >= e.date); if (!t) continue; }
      const k = (ahead ? "f" + t : t) + L;
      if (!by.has(k)) by.set(k, { L, t, ahead, idx: ahead ? times.length - 1 + ahead : times.indexOf(t), items: [] });
      by.get(k).items.push(e);
    }
    groups = [...by.values()].sort((a, b) => a.idx - b.idx);
    strip.innerHTML = groups.map((g, i) => `<button class="ev-ic ${g.L} ${tone(g.items[0])}" data-i="${i}" aria-label="${NAME[g.L]} ${g.items[0].date}">${g.L}</button>`).join("");
    place();
  };
  let raf = 0;
  const place = () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      const ts = chart.timeScale(), pane = chart.panes()[0];
      if (!pane) return;
      const left = chart.priceScale("left").width(), bottom = pane.getHeight() - 24, width = ts.width();
      const stack = new Map();   // two kinds on one bar stack upward, as on TradingView
      strip.querySelectorAll(".ev-ic").forEach((b) => {
        const g = groups[+b.dataset.i], x = ts.logicalToCoordinate(g.idx);
        if (x == null || x < 0 || x > width) { b.hidden = true; return; }
        const n = stack.get(g.idx) || 0; stack.set(g.idx, n + 1);
        b.hidden = false; b.style.left = `${left + x - 9}px`; b.style.top = `${bottom - n * 21}px`;
      });
    });
  };
  const show = (b) => {
    const g = groups[+b.dataset.i];
    tip.innerHTML = g.items.map(card).join("");
    tip.hidden = false;
    const r = b.getBoundingClientRect(), host = chartEl.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = `${Math.max(6, Math.min(host.width - w - 6, r.left - host.left + 9 - w / 2))}px`;
    tip.style.top = `${Math.max(6, r.top - host.top - h - 8)}px`;
  };
  strip.addEventListener("mouseover", (e) => { const b = e.target.closest(".ev-ic"); if (b) show(b); });
  strip.addEventListener("mouseout", (e) => { if (e.target.closest(".ev-ic") && !e.relatedTarget?.closest?.(".ev-ic")) tip.hidden = true; });
  strip.addEventListener("click", (e) => { if (e.target.closest(".ev-ic")) { tip.hidden = true; onOpen?.(); } });
  strip.addEventListener("mousedown", (e) => e.stopPropagation());   // not a chart drag
  chart.timeScale().subscribeVisibleLogicalRangeChange(place);
  chart.timeScale().subscribeSizeChange(place);
  const ro = new ResizeObserver(place); ro.observe(chartEl);
  return {
    set,
    destroy() { cancelAnimationFrame(raf); ro.disconnect(); try { chart.timeScale().unsubscribeVisibleLogicalRangeChange(place); chart.timeScale().unsubscribeSizeChange(place); } catch {} strip.remove(); tip.remove(); },
  };
}

async function chartPage(alive, market, symbol, tf) {
  const prefs = { panel: true, tab: "wl", w: 320, ...store.get("chartPrefs", {}) };
  if (!prefs.panel) prefs.tab = null;  // older prefs: a hidden panel
  market = isMarket(market) ? market : store.get("market", store.get("lastMarket", "us"));
  pageMarket(market);   // the chart's market is the app's market (the header selector follows it)
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
      <button class="ghost" id="setupbtn" title="Draw one strategy's trade setups over the whole history — what its rules would set up on, run on demand. Not trades: pick a backtest run to see what was actually bought."><svg viewBox="0 0 20 20"><path d="M3 13l4-4 3 2 4-6"/><rect x="11" y="11" width="6" height="5" rx="1"/></svg>Trade setups</button>
      <label class="field" id="trades-field" title="Mark the buys and exits a backtest run made in this symbol"><span>Backtest trades</span>
        <select id="trades"><option value="">None</option></select></label>
      <button class="ghost icon" id="fit" title="Show full history"><svg viewBox="0 0 20 20"><path d="M3 8V3h5M17 8V3h-5M3 12v5h5M17 12v5h-5"/></svg></button>
      <span class="spacer"></span>
      ${pos >= 0 ? `<div class="srcchip" title="You are stepping through this list (↑ / ↓)"><span class="muted">From</span>
        <a href="${esc(list.back || "#/screens")}" title="Back to the list">${esc(list.label)}</a>
        <button class="ghost icon" id="prev" title="Previous (↑)">‹</button><span class="pos-n">${pos + 1} / ${list.items.length}</span><button class="ghost icon" id="next" title="Next (↓)">›</button>
        <button class="ghost icon" id="exitlist" title="Stop stepping through this list">✕</button></div>` : ""}
    </div>
    <div class="quote" id="quote"><b class="q-sym">${esc(symbol)}</b><span class="mkt">${MKT_BADGE[market] || market}</span></div>
    <div class="chart-layout"><div class="tools" id="tools"></div>
      <div id="chart">${LOADING}</div>
      <aside class="side" id="side"><div class="side-grip" title="Drag to resize"></div><div class="side-body"></div></aside>
      <nav class="rbar" id="rbar">
        <button data-tab="wl" title="Watchlist"><svg viewBox="0 0 20 20"><path d="M7 5h10M7 10h10M7 15h10"/><circle cx="3.5" cy="5" r=".6"/><circle cx="3.5" cy="10" r=".6"/><circle cx="3.5" cy="15" r=".6"/></svg></button>
        <button data-tab="info" title="Symbol details — fundamentals, screener plan, decision history"><svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="7"/><path d="M10 9v5M10 6.2v.1"/></svg></button>
        <button data-tab="news" title="News & key events — headlines, filings, exchange announcements, earnings, dividends, splits"><svg viewBox="0 0 20 20"><path d="M4 4h10v12H5a1 1 0 0 1-1-1z"/><path d="M14 7h2v8a1 1 0 0 1-2 0"/><path d="M6.5 7h5M6.5 10h5M6.5 13h3"/></svg></button>
        ${pos >= 0 && !String(list.label).startsWith("Watchlist") ? `<button data-tab="list" title="${esc(list.label)}"><svg viewBox="0 0 20 20"><path d="M4 4h12v12H4z"/><path d="M7 8h6M7 12h6"/></svg></button>` : ""}
      </nav></div>`;
  const $ = (s) => $view.querySelector(s);
  $view.querySelectorAll(".tfs button").forEach((b) => b.onclick = () => go(href(symbol, b.dataset.v)));
  // right sidebar (TradingView): an icon bar; clicking an icon opens its panel, clicking the open one closes it
  if (prefs.tab === "list" && !$('#rbar [data-tab="list"]')) prefs.tab = "wl";
  // arriving from a list (a screen, today's setups, movers…): show it beside the chart, so chart and list are both in view
  if (list?.fresh) { if ($('#rbar [data-tab="list"]')) prefs.tab = "list"; store.set("chartList", { ...list, fresh: false }); }
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
  if (pos >= 0) {
    $("#prev").onclick = () => step(-1); $("#next").onclick = () => step(1);
    $("#exitlist").onclick = () => { store.set("chartList", null); if (prefs.tab === "list") prefs.tab = "wl"; route(); };
  }

  let sideReady = false;  // the panel renders once the symbol's context has loaded
  let symNotes = null;    // promise of this stock's notes, for the details panel
  // this stock's news & key events (marketdata/news.py); the server asks the queue for a fetch when
  // none is stored or it is a day old, and `pending` names that queue item until it lands
  let symNews = null, newsPoll = null;
  const loadNews = (refresh = false) => (symNews = (!refresh && symNews) ||
    api(`/api/news/${market}/${encodeURIComponent(symbol)}${refresh ? "?refresh=1" : ""}`).catch((e) => ({ error: e.message })));
  { const prev = cleanup; cleanup = () => { clearInterval(newsPoll); prev(); }; }
  // trade-debug overlay state — declared before the first renderSide(), which can hit the
  // restored Trades tab before the chart (and its data) exists
  let dr = null, vcpAnnotations = [], anatomy = [], selTrade = -1, runStrategy = null, viewClaimed = false;
  // the active Trade setups layer's list, as it published it (studies.js setupLayer): { list, focus, select }
  let setupFeed = null, setupFilter = store.get("setupFilter", "all");
  // the Chart patterns indicator's history, as it published it (studies.js patterns): { list, focus, select, clear }
  let patternFeed = null, patternFilter = store.get("patternFilter", "all");
  // the Supply & demand zones indicator's zones, as it published them (studies.js sdz): { list, focus, checks, select, clear }
  let zoneFeed = null, zoneFilter = store.get("zoneFilter", "active");
  // three read-only layers share the annotation overlay: VCP near misses, the chosen backtest run's
  // trades, and studies that draw shapes (Indicators -> Chart patterns); each sets its own part
  let tradeItems = (keep) => [], studyItems = () => [];
  // ONE design for a setup, whether it is illustrated or was traded. A study may declare that it
  // supersedes a strategy's run layers (`supersedes`), and then it draws the whole setup -- base,
  // shelf, zones AND the run's own entry levels, read from the run's record -- while /api/vcp's
  // boxes and the trade anatomy's boxes, notes and levels stand down. Both layers describe the same
  // base in the same words (the anatomy's label for AAPL's 2024-12-26 base, "base 33d · 7c 7.03% →
  // 8.69%", is the string the indicator prints too), so running both drew everything twice in two
  // visual languages and let one base carry two different rejection rules.
  //
  // Scoped to the run's own strategy: a donchian run's bases are not drawn by a Minervini indicator,
  // so they must keep drawing themselves. Neither layer is deleted -- /api/vcp and trade-anatomy
  // replay the RUN's detections pinned to its spec_id, the only honest answer once current code
  // detects differently from the code that ran, and hiding the indicator restores them at once.
  let supersededStrategy = () => null;
  const runDrawnByStudy = () => runStrategy != null && supersededStrategy() === runStrategy;
  // the run's trades the study drew as setups (by entry date); the rest keep the run's own drawing
  let claimedTrades = new Set();
  const applyAnnotations = () => {
    if (!dr) return;
    const run = runDrawnByStudy() ? tradeItems((t) => !claimedTrades.has(t.entry_date)) : [...vcpAnnotations, ...tradeItems()];
    dr.annotate([...run, ...studyItems()]);
  };
  let zoomToTrade = () => {};
  const viewKey = `${market}:${symbol}:${tf}`;
  let chart = null;
  // rebuild the chart (for an indicator change) without losing the user's zoom / scroll
  const rerender = () => { try { if (chart) keepView = { key: viewKey, range: chart.timeScale().getVisibleLogicalRange() }; } catch {} route(); };
  $("#ind").onclick = () => Studies.openPicker({ onChange: () => { leaveBtView(); rerender(); } });

  // Trade setups: picked the way indicators are, from its own picker — one strategy at a time.
  // The button carries the chosen strategy, so the chart says what it is drawing without the card open.
  const setupBtn = $("#setupbtn");
  const markSetup = async () => {
    await STRATEGIES;
    const name = Studies.setupName();
    setupBtn.lastChild.textContent = name ? ` ${name}` : " Trade setups";
    setupBtn.classList.toggle("on", !!name);
    setupBtn.hidden = !Studies.setupLayers().length;
  };
  markSetup();
  // await the registry first: a layer is NAMED for its strategy, and opening before /api/strategies
  // lands would list the raw key
  setupBtn.onclick = async () => {
    await STRATEGIES;
    Studies.openSetupPicker({ onChange: () => { leaveBtView(); markSetup(); rerender(); } });
  };
  // leaving the backtest view (below): a pick of your own means you want your layers back
  function leaveBtView() { const l = store.get("chartList", null); if (l?.backtest) store.set("chartList", { ...l, backtest: { ...l.backtest, layers: true } }); }

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
  const [px, ctx, tradeRuns, bpx, wlLists, wlMember, qrows, srows] = await Promise.all([
    api(`/api/prices?market=${market}&symbol=${encodeURIComponent(symbol)}&tf=${tf}&bars=${ALL_BARS}`).catch((e) => ({ error: e.message })),
    api(`/api/symbol-context?market=${market}&symbol=${encodeURIComponent(symbol)}`).catch(() => ({ latest: [], history: [] })),
    api(`/api/trade-runs?market=${market}&symbol=${encodeURIComponent(symbol)}`).catch(() => []),
    Studies.needsBench() ? api(`/api/prices?market=${market}&symbol=${bench}&tf=${tf}&bars=${ALL_BARS}`).catch(() => null) : null,
    WL.lists().catch(() => []),
    WL.membership(market, symbol).catch(() => ({ lists: [] })),
    api(`/api/quality?market=${market}&symbol=${encodeURIComponent(symbol)}`).catch(() => []),
    api(`/api/fundamentals?market=${market}&symbol=${encodeURIComponent(symbol)}`).catch(() => ({ rows: [] })),
  ]);
  const qrow = qrows[0], srow = srows.rows?.[0];
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
  const tabAtFirstRender = prefs.tab;
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
  // The BACKTEST VIEW: arrived from a backtest's Trades table and still on that run. The chart shows
  // that run's trades and nothing else of the viewer's — overlay layers (zones, patterns, other
  // strategies' setups) stand down for this list, unsaved, until "show my layers" or a new pick.
  const btView = pos >= 0 && list.backtest && !list.backtest.layers && String(list.backtest.run) === String(sel.value) ? list.backtest : null;
  const isOverlayLayer = (s, def) => !!def.setupsFor || ["sdz", "patterns", "plan"].includes(s.type);
  if (btView) {
    $(".srcchip")?.insertAdjacentHTML("beforeend", `<span class="muted" title="Opened from a backtest's trades: the chart shows that run's trades only. Your own overlay layers are hidden while you step through this list.">· backtest view</span><a class="small" id="btlayers" title="Show your saved overlay layers too">show my layers</a>`);
    $("#btlayers").onclick = () => { leaveBtView(); route(); };
    if (["setups", "patterns", "zones"].includes(prefs.tab)) prefs.tab = "trades";   // their buttons stand down here
    if (list.backtest.arrive) { prefs.tab = "trades"; store.set("chartList", { ...store.get("chartList", {}), backtest: { ...list.backtest, arrive: false } }); }
  }
  // a backtest run is on: offer its trades as a side panel (click a trade -> its anatomy)
  if (sel.value) {
    $("#rbar").insertAdjacentHTML("beforeend", `<button data-tab="trades" title="Backtest trades — click one to zoom to it and see the structure the strategy traded on">
      <svg viewBox="0 0 20 20"><path d="M3 17V3M3 17h14"/><path d="M5 13l3.5-5 3 3L16 5"/></svg></button>`);
  } else if (prefs.tab === "trades") prefs.tab = "wl";
  // a Trade setups layer is on: offer its setups as a side panel (click one -> the chart goes to it)
  if (Studies.activeSetup() && !btView) {
    $("#rbar").insertAdjacentHTML("beforeend", `<button data-tab="setups" title="Trade setups — every setup of ${esc(Studies.setupName() || "the layer")}; click one to go to it">
      <svg viewBox="0 0 20 20"><rect x="3" y="4" width="14" height="12" rx="1.5"/><path d="M6 12l2.5-3 2 2L14 7"/></svg></button>`);
  } else if (prefs.tab === "setups") prefs.tab = "wl";
  // the Chart patterns indicator is on: offer every pattern its detectors saw as a side panel
  if (Studies.load().some((s) => s.type === "patterns") && !btView) {
    $("#rbar").insertAdjacentHTML("beforeend", `<button data-tab="patterns" title="Chart patterns — every pattern the chart-pattern strategy's detectors saw; click one to draw it">
      <svg viewBox="0 0 20 20"><path d="M2 15l4-8 3 5 3-7 6 10"/><path d="M2 17h16"/></svg></button>`);
  } else if (prefs.tab === "patterns") prefs.tab = "wl";
  // the Supply & demand zones indicator is on: offer its zones, with each one's checklist, as a side panel
  if (Studies.load().some((s) => s.type === "sdz") && !btView) {
    $("#rbar").insertAdjacentHTML("beforeend", `<button data-tab="zones" title="Supply & demand zones — every base a decisive move left from, its checklist and retests; click one to go to it">
      <svg viewBox="0 0 20 20"><rect x="3" y="4" width="14" height="4" rx="1"/><rect x="3" y="12" width="14" height="4" rx="1"/></svg></button>`);
  } else if (prefs.tab === "zones") prefs.tab = "wl";
  syncPanel();
  // the panel first rendered with the remembered tab; if that tab's indicator is not on this chart
  // (zones, patterns, setups…), it was just replaced: render the panel again, or it shows the stale one
  if (prefs.tab !== tabAtFirstRender) renderSide();

  // The time axis must be on screen without scrolling. The rows above the chart (nav, subnav,
  // toolbar, quote) wrap differently per width, so no CSS constant fits every window: measure the
  // chart's real top and give it exactly the viewport space below it (min 440px, as in the CSS).
  const sizeChart = () => {
    const top = chartEl.getBoundingClientRect().top + window.scrollY;
    const vh = Math.max(window.innerHeight, document.documentElement.clientHeight);   // innerHeight can read 0 mid-layout
    chartEl.style.height = Math.max(440, vh - top - 14) + "px";
  };
  sizeChart();
  addEventListener("resize", sizeChart);
  { const prev = cleanup; cleanup = () => { removeEventListener("resize", sizeChart); prev(); }; }
  // drag-panning of the plot is done by our own handler below (both axes, TradingView style), so the
  // library's horizontal-only drag is off; wheel zoom, touch and the axis drag-to-scale stay native
  chart = LC.createChart(chartEl, { autoSize: true, ...chartTheme(), crosshair: { mode: LC.CrosshairMode.Normal },
    handleScroll: { mouseWheel: true, pressedMouseMove: false, horzTouchDrag: true, vertTouchDrag: false } });
  const prevCleanup = cleanup;
  cleanup = () => { prevCleanup(); dr && dr.destroy(); chart.remove(); };
  let main, times;
  const rows = px.ohlc ? px.candles : px.line;
  if (px.ohlc) {
    // the current-price tag in a neutral blue, not the day's red / green: it must not look like a
    // resistance or support tag beside it (the day's change is in the header)
    main = chart.addSeries(LC.CandlestickSeries, { upColor: "#26a69a", downColor: "#ef5350", borderVisible: false, wickUpColor: "#26a69a", wickDownColor: "#ef5350",
      priceLineColor: "#2962ff" }, 0);
    main.setData(px.candles);
  } else {
    main = chart.addSeries(LC.AreaSeries, { lineColor: cssVar("--series"), topColor: alpha(cssVar("--series"), .2), bottomColor: alpha(cssVar("--series"), 0), lineWidth: 2 }, 0);
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
  // Shapes in the Strategy.chart_anatomy schema (strategies/base.py) -> annotation items. Used by the
  // backtest-trade overlay and by studies that draw patterns, so a pattern looks the same in both.
  const ROLE = { base: "#2962ff", pivot: "#26a69a", stop: "#ef5350", target: "#26a69a", support: "#8a8a8a", level: "#ff9800" };
  const barOf = (d) => times.find((x) => x >= d);   // a date onto the nearest charted bar at or after it
  const tsOf = (d) => { const s = barOf(d); return s ? Date.parse(s + "T00:00:00Z") : null; };
  const idxOf = (d) => { const s = barOf(d); return s ? times.indexOf(s) : -1; };
  // s.faint: this one shape drawn as background (thin, unlabelled) — a study dimming all but its focus
  const shapeItems = (shapes, { dim: dimAll = false, withNotes = false, at = null, price = null, roles = {} } = {}) => shapes.map((s) => {
    const dim = dimAll || !!s.faint;
    const col = dimAll ? "#4b5063" : roles[s.role] || ROLE[s.role] || ROLE.level;
    // point markers carry their own dates, so they come before the anchor lookup (which they lack)
    if (s.shape === "dots") return dim ? [] : (s.points || []).map((q) => ({ t: tsOf(q.at), p: q.price, label: q.label }))
      .filter((q) => q.t != null).flatMap((q) => [{ type: "dot", pts: [{ t: q.t, p: q.p }], color: col },
        ...(q.label ? [{ type: "text", pts: [{ t: q.t, p: q.p }], color: col, size: 11, text: q.label }] : [])]);
    const t1 = tsOf(s.to || s.at || at); if (t1 == null) return null;
    const i1 = idxOf(s.to || s.at || at);
    const t0 = s.from ? tsOf(s.from) : s.bars && i1 >= 0 ? Date.parse(times[Math.max(0, i1 - s.bars)] + "T00:00:00Z") : t1;
    if (s.shape === "box") return { type: "rect", pts: [{ t: t0, p: s.top }, { t: t1, p: s.bottom }],
      color: col, width: dim ? 1 : s.frame ? 1.5 : 2, dash: !!s.dash, text: dim ? "" : s.label || "",
      bg: !!s.bg, shade: !!s.shade, frame: !!s.frame, edge: !!s.edge };   // bg: a full-height tint; shade: fill only (edge: + a faint outline); frame: outline + header tab
    // a level may set its own weight and dash ("dot" | true | false) — an annotation's timeframe — and
    // `alpha` (two hex digits) to fade it
    if (s.shape === "level") return { type: "trend", pts: [{ t: t0, p: s.price }, { t: t1, p: s.price }],
      color: s.alpha ? col + s.alpha : col, width: s.width || 1, dash: s.dash === undefined ? true : s.dash, text: dim ? "" : s.label || "" };
    if (s.shape === "line") return { type: "trend", pts: [{ t: t0, p: s.p0 }, { t: t1, p: s.p1 }],
      color: col, width: dim ? 1 : s.arrow ? 2.5 : 2, dash: !!s.dash, arrow: !dim && !!s.arrow, text: dim ? "" : s.label || "" };
    if (s.shape === "text") return dim ? null : { type: "text", pts: [{ t: t1, p: s.price }], color: col, size: 11, text: s.label || "" };
    if (s.shape === "path") {
      // the pattern itself: its swing points joined in order, each point named (dimmed: line only)
      const P = (s.points || []).map((q) => ({ t: tsOf(q.at), p: q.price, label: q.label })).filter((q) => q.t != null);
      return [
        ...P.slice(1).map((q, j) => ({ type: "trend", pts: [{ t: P[j].t, p: P[j].p }, { t: q.t, p: q.p }],
          color: col, width: dim ? 1 : 2.5, dash: false, text: "" })),
        // the named points get a dot and a label; unnamed ones are curve vertices (a rounded cup)
        ...(dim ? [] : P.filter((q) => q.label).flatMap((q) => [
          { type: "dot", pts: [{ t: q.t, p: q.p }], color: col },
          { type: "text", pts: [{ t: q.t, p: q.p }], color: col, size: 11, text: q.label }])),
      ];
    }
    if (s.shape === "note" && withNotes && s.text) {
      // the text box is pinned to the pane's top strip (pts[1].f = fraction of pane height),
      // so the note never covers the bars it explains; the leader still drops to the anchor
      const p = s.price ?? price;
      const bx = Math.min(times.length - 1, (i1 < 0 ? times.length - 1 : i1) + 2);
      return { type: "callout", pts: [{ t: t1, p }, { t: Date.parse(times[bx] + "T00:00:00Z"), f: 0.05 }],
        color: col, width: 1, text: s.text };
    }
    return null;
  }).flat().filter(Boolean);
  // studies that draw shapes hand them over here, keyed by study id; the overlay redraws at once
  const studyShapes = new Map();
  studyItems = () => [...studyShapes.values()].flatMap(({ shapes, roles }) => shapeItems(shapes, { roles }));
  const annotate = (key, shapes, roles) => { studyShapes.set(key, { shapes, roles }); applyAnnotations(); };
  // trades: the selected backtest run's trades on this symbol (trade-anatomy), for a study that should
  // defer to a run's record; onTrades: called when they (re)load
  const tradeHooks = [], focusHooks = [];
  // A backtest run is selected (from its Trades table or the Backtest trades menu): its trades are drawn
  // the way a setup is drawn — the run strategy's setups layer, traded setups only, for this visit —
  // never the older run-anatomy boxes. A saved setups layer of the same strategy already draws them
  // (in full); one of another strategy stands down while the run is shown (the card and lane are single).
  // In the backtest view, the viewer's other overlay layers stand down too.
  const runKey = tradeRuns.find((r) => String(r.id) === String(sel.value))?.strategy || null;
  const runLayerType = runKey && Studies.setupLayers().find((l) => l.strategy === runKey)?.type;
  const btLayer = runLayerType && Studies.activeSetup() !== runLayerType ? runLayerType : null;
  const studies = Studies.render({ chart, times, bars: B,
    skip: (s, def) => (!!btView && isOverlayLayer(s, def)) || (!!btLayer && !!def.setupsFor),
    extra: btLayer ? [Studies.transient(btLayer, { tradedOnly: true })] : [],
    ctx: { bench: benchMap, main, tf, plans: px.ohlc ? ctx.latest : [],
    market, symbol, chartEl, annotate: px.ohlc ? annotate : null,
    trades: () => anatomy, onTrades: (fn) => tradeHooks.push(fn), claimTrades: (set) => { claimedTrades = set; },
    claimView: () => { viewClaimed = true; }, onFocusTrade: (fn) => focusHooks.push(fn),
    // a list pick frames its item: the price axis back on auto-scale (as the "auto" button does)
    fitPrice: () => { try { chart.panes().forEach((_, i) => chart.priceScale("right", i).applyOptions({ autoScale: true })); syncAuto(); } catch {} },   // a study framed something itself: skip the opening view
    // the selected run's start date (its directory name begins with it), so a setups layer scans back that far
    runStart: (/^\d{4}-\d{2}-\d{2}/.exec(tradeRuns.find((r) => String(r.id) === String($("#trades").value))?.run || "") || [null])[0],
    onSetups: (feed) => { setupFeed = feed; if (prefs.tab === "setups") renderSide(); },
    onPatterns: (feed) => { patternFeed = feed; if (prefs.tab === "patterns") renderSide(); },
    onZones: (feed) => { zoneFeed = feed; if (prefs.tab === "zones") renderSide(); } } });
  // read at paint time, not captured: hiding the indicator from the legend restores the stored layer
  supersededStrategy = () => studies.find((e) => e.def?.setupsFor && !e.skipped && !e.s.hidden)?.def.setupsFor ?? null;
  const nPanes = Math.max(0, ...studies.map((e) => e.pane || 0));

  // Opened from a chart-pattern strategy's setups: draw the stock's pattern as of that run (the same
  // detectors and drawing as the Chart patterns indicator, /api/patterns), so a listed setup is visible
  // without adding the indicator. The run's own record — trigger, stop, decision — stays in the table.
  const setup = pos >= 0 && list.setup;
  const setupName = setup?.patterns?.[symbol];
  if (setupName && setup.strategy === "chart_pattern" && tf === "D" && px.ohlc) {
    api(`/api/patterns/${market}/${encodeURIComponent(symbol)}?show=all&topping=0&date=${setup.date}`).then((r) => {
      if (!alive()) return;
      const m = (r.matches || []).find((x) => x.name === setupName);
      const chip = $(".srcchip");
      chip?.insertAdjacentHTML("beforeend", `<span class="muted" title="${m ? `Drawn as detected on ${esc(r.as_of)}, the run's last bar`
        : esc(r.note || `The detector no longer finds this pattern on ${r.as_of} — current code may differ from the code that ran`)}">· ${esc(setupName)}${m ? "" : " (not redrawn)"}</span>`);
      if (m) annotate("setup", m.shapes);
    }).catch(() => {});
  }

  // (the screener's entry / stop / target lines are now an opt-in indicator: Indicators -> Screener)

  // backtest trades from the chosen run
  // (any symbol, candles or a close-only line: a portfolio run's holdings are often index series — GOLD,
  // MIDCAP — and their trades belong on the chart as much as a stock's)
  if (sel.value) {
    const t = await api(`/api/reports/${sel.value}/tables/trades?symbol=${encodeURIComponent(symbol)}`).catch(() => null);
    if (!alive()) return;
    // `snap` maps a date onto the nearest charted bar; the VCP annotation below needs it
    // too, so it is declared here rather than inside the trades block
    const snap = (d) => times.find((x) => x >= d);
    if (t) {
      const c = (n) => t.columns.indexOf(n);
      // a run without stops (a rotation or allocation strategy) has no risk unit: its "r_multiple" is the
      // trade's return, so it is shown as a percentage, never as R
      const noStop = !t.columns.includes("stop") && !t.columns.includes("initial_stop");
      const res = (rm) => (rm == null ? "" : noStop ? `${rm > 0 ? "+" : ""}${(rm * 100).toFixed(1)}%` : `${rm > 0 ? "+" : ""}${rm}R`);
      const marks = [];
      t.rows.forEach((r) => {
        const a = snap(r[c("entry_date")]), b = snap(r[c("exit_date")]), pnl = r[c("pnl")], rm = r[c("r_multiple")];
        const ep = +r[c("entry_price")], xp = +r[c("exit_price")];
        // pinned to the FILL price, not under the bar's low: a marker below the candle reads as a
        // fill below the trigger line when the trade actually bought through it
        if (a) marks.push({ time: a, shape: "arrowUp", color: "#2196f3", text: `Buy ${fmt(ep)}`,
          ...(ep > 0 ? { position: "atPriceBottom", price: ep } : { position: "belowBar" }) });
        if (b) marks.push({ time: b, shape: "arrowDown", color: pnl >= 0 ? "#26a69a" : "#ef5350", text: `${r[c("exit_reason")]} ${res(rm)}`,
          ...(xp > 0 ? { position: "atPriceTop", price: xp } : { position: "aboveBar" }) });
      });
      marks.sort((x, y) => (x.time < y.time ? -1 : x.time > y.time ? 1 : 0));
      LC.createSeriesMarkers(main, marks);
    }

    // Auto-annotate the structure the strategy claimed to see, per executed trade: the base box,
    // the pivot, the contraction story, the trade's own stop/target — straight from the signal
    // record the run wrote (/api/reports/{id}/trade-anatomy), so the chart shows WHY each trade
    // fired, not just where. The old VCP layer stays for the near misses: bases the detector saw
    // that never became one of this run's trades (dashed, labelled with the rejecting rule).
    const { strategy: stratKey, spec_id: runSpec } = tradeRuns.find((r) => String(r.id) === String(sel.value)) || {};
    runStrategy = stratKey || null;
    if (stratKey) {
      const [anat, boxes] = await Promise.all([
        api(`/api/reports/${sel.value}/trade-anatomy?symbol=${encodeURIComponent(symbol)}`).catch(() => []),
        api(`/api/vcp/${market}/${encodeURIComponent(symbol)}?strategy=${encodeURIComponent(stratKey)}${runSpec ? `&spec=${encodeURIComponent(runSpec)}` : ""}`).catch(() => []),
      ]);
      if (!alive()) return;
      anatomy = anat || [];
      tradeHooks.forEach((f) => f());
      const ts = tsOf;
      // near misses only: a base that one of this run's trades was built on is drawn by its trade
      const traded = new Set(anatomy.flatMap((t) => t.shapes.filter((s) => s.shape === "box" && s.from).map((s) => `${s.from}`)));
      const ann = [];
      (boxes || []).filter((b) => !traded.has(`${b.from}`)).forEach((b) => {
        const t0 = ts(b.from), t1 = ts(b.to);
        if (t0 == null || t1 == null) return;
        const done = b.complete;
        ann.push({ type: "rect", pts: [{ t: t0, p: b.high }, { t: t1, p: b.low }],
          color: done ? "#26a69a" : "#8a8a8a", width: done ? 2 : 1, dash: !done,
          text: `VCP ${b.contractions}c${done ? "" : " · " + (b.fail || "incomplete")}` });
        if (b.pivot) ann.push({ type: "trend", pts: [{ t: t0, p: b.pivot }, { t: t1, p: b.pivot }],
          color: "#26a69a", width: 1, dash: true });
      });
      vcpAnnotations = ann;   // applied once Drawings exists, further down
      // anatomy shapes -> overlay items; the selected trade stays vivid, the rest dim to context
      const items = (t, i) => shapeItems(t.shapes, { dim: selTrade >= 0 && selTrade !== i,
        withNotes: selTrade === i || (selTrade < 0 && anatomy.length <= 3), at: t.entry_date, price: t.entry_price });
      tradeItems = (keep = () => true) => anatomy.flatMap((t, i) => (keep(t) ? items(t, i) : []));
      zoomToTrade = (t) => {
        const ids = t.shapes.map((s) => (s.from ? idxOf(s.from) : s.bars ? idxOf(s.to || t.entry_date) - s.bars : -1)).filter((x) => x >= 0);
        const i0 = Math.min(...(ids.length ? ids : [idxOf(t.signal_date || t.entry_date)]).filter((x) => x >= 0), idxOf(t.entry_date));
        const i1 = Math.max(idxOf(t.exit_date || t.entry_date), i0);
        if (i0 >= 0) chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, i0 - 8), to: i1 + 14 });
      };
      if (prefs.tab === "trades") renderSide();   // the panel rendered before the trades arrived
    }
  }

  const bars = tf === "D" ? 130 : tf === "W" ? 104 : 60;  // open zoomed in on recent history (unless a study framed something)
  requestAnimationFrame(() => {  // after autoSize has laid out the panes
    if (!alive()) return;   // left (or re-rendered) before this frame: the chart is already removed
    // each indicator pane ~20% of the height, but the price pane always keeps at least half
    const per = Math.round(chartEl.clientHeight * Math.min(0.2, 0.5 / Math.max(nPanes, 1)));
    for (let i = 1; i <= nPanes; i++) try { chart.panes()[i].setHeight(per); } catch {}
    if (viewClaimed) {}
    else if (keepView && keepView.key === viewKey && keepView.range) chart.timeScale().setVisibleLogicalRange(keepView.range);
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
  // from the server's daily bars when it sent them (px.range52): a weekly or monthly bar straddling the
  // year boundary would otherwise pull in a high or low from before it
  const hi52 = px.range52?.hi ?? Math.max(...yr.map((r) => (px.ohlc ? r.high : r.value))),
    lo52 = px.range52?.lo ?? Math.min(...yr.map((r) => (px.ohlc ? r.low : r.value)));
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
    const panes = chart.panes();   // empty once the chart is removed, which a late event can still reach
    for (let p = 1; p <= nPanes && panes[p - 1]; p++) {
      top += panes[p - 1].getHeight() + 1;
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

  // drawing tools (TradingView-style left toolbar). Drawings live on the server per symbol
  // (chart_drawings table) so they survive browsers; localStorage stays as the offline fallback.
  const ohlcBars = px.ohlc ? px.candles : px.line.map((d) => ({ open: d.value, high: d.value, low: d.value, close: d.value }));
  const drawUrl = `/api/drawings/${market}/${encodeURIComponent(symbol)}`;
  const remote = await api(drawUrl).then((r) => {
    let t = null, pending = null, failed = false;
    const push = async () => {
      const items = pending; pending = null;
      try { await api(drawUrl, jsonReq("PUT", { items })); failed = false; }
      catch { if (!failed) { failed = true; toast("Could not save drawings to the server — kept in this browser", "err"); } }
    };
    return {
      exists: r.exists, items: r.items,
      save(items) { pending = items.map((x) => ({ ...x })); clearTimeout(t); t = setTimeout(push, 600); },
      flush() { if (pending != null) { clearTimeout(t); push(); } },
    };
  }).catch(() => null);
  if (!alive()) return;
  dr = Drawings.create({ chart, series: main, chartEl, times, bars: ohlcBars, key: `${market}:${symbol}`, remote });
  applyAnnotations();   // read-only: never saved, never erasable
  // key events along the bottom of the price pane, TradingView style: E earnings / results and D ex-dividend
  // only; hover for the details, click for the News & events panel. Upcoming events sit
  // in the empty space right of the last bar.
  const evStrip = eventStrip({ chart, chartEl, times, tf, market, quarters: srow?.series || [],
    onOpen: () => { prefs.tab = "news"; prefs.panel = true; store.set("chartPrefs", prefs); syncPanel(); renderSide(); } });
  { const prev = cleanup; cleanup = () => { evStrip.destroy(); prev(); }; }
  const showEventMarkers = (d) => { if (d && d.events && alive()) evStrip.set(d.events); };
  // `function` (hoisted) because the panel's Refresh link calls it before this line has run
  function onNews(d) {
    showEventMarkers(d);
    if (prefs.tab === "news") renderSide();
    if (d && d.pending && !newsPoll) {   // a fetch is queued: check back until it lands
      let tries = 0;
      newsPoll = setInterval(async () => {
        if (!alive() || ++tries > 50) { clearInterval(newsPoll); newsPoll = null; return; }
        const x = await api(`/api/news/${market}/${encodeURIComponent(symbol)}`).catch(() => null);
        if (x && !x.pending) { clearInterval(newsPoll); newsPoll = null; symNews = Promise.resolve(x); onNews(x); }
      }, 6000);
    }
  }
  loadNews().then(onNews);
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
    // the server's 52-week range comes from daily bars, so it reads the same on every timeframe
    return { last: c(lastB), chg: c(lastB) - c(prevB), pct: (c(lastB) / c(prevB) - 1) * 100, date: lastB.time,
      hi: px.range52?.hi ?? Math.max(...yr.map((r) => (px.ohlc ? r.high : r.value))),
      lo: px.range52?.lo ?? Math.min(...yr.map((r) => (px.ohlc ? r.low : r.value))) };
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
      return `<div class="plan"><div class="row"><b>${esc(l.strategy)}</b>${decisionTag(l.decision)}</div>
        ${l.strategy_setup ? `<div class="muted small">${esc(l.strategy_setup)}</div>` : ""}
        ${l.entry > 0 ? `<div class="kv"><span>Entry <b>${fmt(l.entry)}</b></span><span>Stop <b class="neg">${fmt(l.stop)}</b></span>
          ${risk != null ? `<span>Risk <b>${risk.toFixed(1)}%</b></span>` : ""}${l.target_r ? `<span>Target <b class="pos">${fmt(+l.target_r)}R</b></span>` : ""}</div>` : ""}
        <div class="muted small">${prettyDate(String(l.run_id).replace(/^screener\//, ""))}</div></div>`;
    }).join("");
    const hist = ctx.history.slice(0, 20).map((h) => `<div class="dhist"><span class="muted">${prettyDate(h.run_id)}</span><span>${esc(h.strategy)}</span>
      ${decisionTag(h.decision)}</div>`).join("");
    const pc = (v) => (v == null ? "—" : `${(v * 100).toFixed(0)}%`);
    const qHtml = qrow && qrow.quality != null ? `<section><h3>Fundamentals <a class="muted" href="#/quality/${market}">quality page</a></h3>
      <div class="plan"><div class="row"><b>Quality ${qrow.quality}/100 <span class="muted small">F ${qrow.f_score ?? "—"}</span></b>
        <span class="tag ${zoneClass(qrow.at_your_price ? "AT YOUR PRICE" : qrow.zone)}">${esc(qrow.at_your_price ? "AT YOUR PRICE" : qrow.zone || "")}</span></div>
        <div class="kv"><span>${qrow.financial ? "ROE" : "ROIC"} <b>${pc(qrow.financial ? qrow.roe_avg : qrow.roic_avg)}</b></span><span>Rev <b>${pc(qrow.rev_cagr)}</b>/yr</span>
          <span>P/E <b>${qrow.pe ? qrow.pe.toFixed(1) : "—"}</b></span><span>Value <b class="${qrow.value === "Attractive" ? "pos" : qrow.value === "Expensive" ? "neg" : ""}">${esc(qrow.value || "—")}</b></span></div>
        ${(qrow.flags || []).length ? `<div class="muted small">${esc(qrow.flags.join(" · "))}</div>` : ""}</div></section>` : "";
    const sv = srow?.views?.sepa;
    const sHtml = srow ? `<section><h3>Quarterly fundamentals <a class="muted" href="${companyHref(market, symbol)}">financials</a></h3>
      <div class="plan"><div class="kv"><span>EPS <b class="${(srow.eps_g?.[0] ?? 0) >= 0 ? "pos" : "neg"}">${esc(sepaPct(srow.eps_g?.[0]) || "—")}</b>
          <span class="muted small">${(srow.eps_g || []).slice(1, 3).map((v) => esc(sepaPct(v) || "—")).join(" · ")}</span></span>
          <span>Sales <b>${esc(sepaPct(srow.rev_g?.[0]) || "—")}</b></span><span>ROE <b>${srow.roe == null ? "—" : `${(srow.roe * 100).toFixed(0)}%`}</b></span></div>
        ${sv ? `<div class="row"><span class="muted small">Minervini SEPA · ${sv.passed}/${sv.scored} tests</span>
          <span>${sv.code33 ? '<span class="tag trade">CODE 33</span> ' : ""}<span class="tag ${sepaClass(sv.verdict)}">${esc(sv.verdict)}</span></span></div>` : ""}
        <div class="muted small">latest ${esc(srow.latest_fiscal || prettyDate(srow.latest_end))} · <a href="${companyHref(market, symbol)}">full financials →</a></div></div></section>` : "";
    return `${qHtml}${sHtml}<section><h3>Screener — latest</h3>${plans || '<div class="muted small">Not in any screening run.</div>'}</section>
      <section><h3>Decision history</h3>${hist || '<div class="muted small">None.</div>'}</section>`;
  }
  /** TradingView's details block under the watchlist: the open symbol's price, day change, 52-week range and verdicts */
  function detailsHtml() {
    const q = pxQuote(), sector = ctx.latest[0]?.sector || qrow?.sector || "";
    const best = [...ctx.latest].sort((a, b) => DEC_RANK(a.decision) - DEC_RANK(b.decision))[0];
    const pos52 = q && q.hi > q.lo ? ((q.last - q.lo) / (q.hi - q.lo)) * 100 : 50;
    return `<div class="wld-head"><b>${esc(symbol)}</b><span class="mkt">${MKT_BADGE[market] || market}</span>${sector ? `<span class="muted small">${esc(sector)}</span>` : ""}</div>
      ${ctx.name ? `<div class="wld-name">${esc(ctx.name)}</div>` : ""}
      ${ctx.classification ? `<div class="wld-cls small">${[["sector", ctx.classification.sector], ["industry", ctx.classification.industry], ["sub", ctx.classification.sub_key]]
        .filter(([, v]) => v).map(([lv, v]) => `<a href="${secHref(market, lv, v)}" title="Open on the Sectors page">${esc(groupParts(v)[0])}</a>`).join('<span class="muted"> › </span>')}</div>` : ""}
      ${q ? `<div class="wld-px"><span class="big">${fmt(q.last)}</span><span class="${q.chg >= 0 ? "pos" : "neg"}">${q.chg >= 0 ? "+" : ""}${fmt(q.chg)} (${signed(q.pct)}%)</span></div>
        <div class="muted small">Close · ${prettyDate(q.date)}</div>
        <div class="wld-52"><span class="muted small">52-week range</span><div class="bar52 wide"><i style="left:${pos52.toFixed(1)}%"></i></div>
          <div class="wld-52v small"><span>${fmt(q.lo)}</span><span>${fmt(q.hi)}</span></div></div>` : ""}
      <div class="wld-notes" id="wlnotes"></div>
      <div class="wld-kv">
        ${best ? `<span class="muted">Screener</span><span>${decisionTag(best.decision)}</span>` : ""}
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
      <div class="wlrows">${rowsHtml || `<div class="wl-empty">${wlCur?.builtin
        ? '<b>No screener picks today</b><div class="muted small">Stocks a strategy marks tradeable or on watch land here after the daily run. <a href="#/strategies">See today\'s setups →</a></div>'
        : '<b>This list is empty</b><div class="muted small">Track stocks here to see their price and change at a glance.</div><button class="primary wl-empty-add">+ Add a symbol</button><div class="muted small">or press ☆ next to any chart\'s name.</div>'}</div>`}</div>
      <div class="wl-details">${detailsHtml()}</div></div>`;
  }
  function listPanelHtml() {
    return `<section><h3>${esc(list.label)} <a class="muted" href="${esc(list.back || "#/screening")}">back</a></h3></section>
      <div class="wlrows">${list.items.map((it, i) => `<a class="wlr nolast ${i === pos ? "cur" : ""}" href="${hrefFor(it.m, it.s)}">
        <span class="wsym"><span class="dotm ${it.m}"></span>${esc(it.s.replace(/\.NS$/, ""))}</span></a>`).join("")}</div>`;
  }
  /** the chosen backtest run's trades in this symbol — click one to zoom the chart to it and
   *  light up its anatomy (the rest of the overlay dims to context) */
  // a trade with no stop (rotation / allocation runs) has no R: its result is its return, as a percentage
  function tradeResult(t) {
    const rm = t.r_multiple;
    if (rm == null) return "?";
    const noStop = !(t.shapes || []).some((s) => s.role === "stop");
    return noStop ? `${rm > 0 ? "+" : ""}${(rm * 100).toFixed(1)}%` : `${rm > 0 ? "+" : ""}${rm}R`;
  }
  function tradesPanelHtml() {
    // looked up from the DOM, not the `sel` binding: the panel can render (restored tab) before
    // the select's const is initialized further down the page build
    const run = tradeRuns.find((r) => String(r.id) === String(($("#trades") || {}).value || ""));
    const rows = anatomy.map((t, i) => `<div class="btr ${i === selTrade ? "cur" : ""}" data-i="${i}">
        <div class="btr-h"><b>${prettyDate(t.entry_date)} → ${t.exit_date ? prettyDate(t.exit_date) : "open"}</b>
          <span class="${(t.r_multiple ?? 0) >= 0 ? "pos" : "neg"}">${tradeResult(t)}</span></div>
        ${t.setup_name ? `<div class="small">Pattern: <b>${esc(t.setup_name)}</b></div>` : ""}
        <div class="muted small">${esc([t.setup, t.exit_reason, t.holding_days != null ? `${t.holding_days}d` : ""].filter(Boolean).join(" · "))}</div>
        ${t.note ? `<div class="btr-note small">${esc(t.note)}</div>` : ""}</div>`).join("");
    return `<section><h3>Backtest trades</h3><div class="muted small">${run ? esc(`${run.strategy} · ${run.run}`) : ""}</div>
      <div class="muted small">Click a trade to zoom to it and highlight what the strategy saw; click again to show every trade.</div></section>
      <div class="btrs">${rows || '<div class="muted small">This run has no trades in this symbol.</div>'}</div>`;
  }
  /** The Trade setups panel: every setup the active layer found, newest first, filterable by verdict —
   *  the backtest-trades panel's shape, so finding a setup is a click rather than a scroll. */
  function setupsPanelHtml() {
    const name = Studies.setupName() || "Trade setups";
    if (!setupFeed) return `<section><h3>${esc(name)}</h3><div class="muted small">Finding the setups…</div></section>`;
    // by what the rules would DO, judged on the ENTRY zone, not the frame's colour: a complete VCP whose
    // entry fails (a skipped trade) is refused, while a cheat entry on a base that is no VCP would trade
    const entryOf = (s) => s.zones.find((z) => z.key === "entry" || z.key === "cheat");
    const kindOf = (s) => s.kind === "young" ? "young" : s.kind === "watch" ? "trigger" : s.kind === "pass" ? "trade"
      : ["vcp", "cheat"].includes(s.kind) && entryOf(s)?.state === "pass" ? "trade" : "refused";
    const counts = { all: setupFeed.list.length, trade: 0, trigger: 0, refused: 0 };
    setupFeed.list.forEach((s) => { const k = kindOf(s); if (k in counts) counts[k]++; });
    const chips = [["all", "All"], ["trade", "Would trade"], ["trigger", "On trigger"], ["refused", "Refused"]]
      .map(([k, t]) => `<a class="sp-chip ${setupFilter === k ? "on" : ""}" data-f="${k}">${t} <span>${counts[k]}</span></a>`).join("");
    const rows = setupFeed.list.map((s, i) => ({ s, i })).reverse()
      .filter(({ s }) => setupFilter === "all" || kindOf(s) === setupFilter)
      .map(({ s, i }) => `<div class="btr sp-row sp-${kindOf(s)} ${i === setupFeed.focus ? "cur" : ""}" data-si="${i}">
        <div class="btr-h"><b>${prettyDate(s.base_from)}</b><span class="muted small">${s.live ? "today" : prettyDate(s.to)}</span></div>
        <div class="small sp-title">${esc(s.title)}</div>
        <div class="muted small">${esc(s.summary)}</div></div>`).join("");
    return `<section><h3>${esc(name)} · setups</h3>
      <div class="muted small">What the strategy's rules would set up on — not trades. Click one to go to it on the chart.</div>
      <div class="sp-chips">${chips}</div></section>
      <div class="btrs">${rows || `<div class="muted small">${setupFeed.list.length ? "None of this kind." : "No setups in this window."}</div>`}</div>`;
  }
  /** The Chart patterns panel: every pattern the strategy's detectors found over five years, newest
   *  first, filterable; a click draws that pattern and goes to it. */
  function patternsPanelHtml() {
    if (!patternFeed) return `<section><h3>Chart patterns</h3><div class="muted small">Scanning five years of bars…</div></section>`;
    const L = patternFeed.list;
    const kindOf = (x) => (x.direction === "bearish" ? "top" : "bull");
    const counts = { all: L.length, bull: L.filter((x) => kindOf(x) === "bull").length, top: L.filter((x) => kindOf(x) === "top").length,
      crossed: L.filter((x) => x.crossed).length };
    const chips = [["all", "All"], ["bull", "Bullish"], ["top", "Topping"], ["crossed", "Crossed its trigger"]]
      .map(([k, t]) => `<a class="sp-chip ${patternFilter === k ? "on" : ""}" data-pf="${k}">${t} <span>${counts[k]}</span></a>`).join("");
    const keep = (x) => patternFilter === "all" || (patternFilter === "crossed" ? !!x.crossed : kindOf(x) === patternFilter);
    const rows = L.map((x, i) => ({ x, i })).filter(({ x }) => keep(x)).map(({ x, i }) => `<div class="btr sp-row ${kindOf(x) === "top" ? "sp-refused" : "sp-trade"} ${i === patternFeed.focus ? "cur" : ""}" data-pi="${i}">
        <div class="btr-h"><b>${esc(x.name)}</b><span class="muted small">${prettyDate(x.start)} → ${prettyDate(x.last_seen)}</span></div>
        <div class="small sp-title">${esc(x.direction === "bearish" ? "Topping" : "Bullish")} · ${esc(x.states.join(" → "))}${x.tradeable ? " · tradeable" : ""}</div>
        <div class="muted small">trigger ${(+x.trigger).toFixed(2)} · invalidation ${(+x.invalidation).toFixed(2)}${x.crossed ? ` · crossed ${prettyDate(x.crossed)}` : ""}${x.invalidated ? ` · invalidated ${prettyDate(x.invalidated)}` : ""}</div></div>`).join("");
    return `<section><h3>Chart patterns</h3>
      <div class="muted small">Every pattern the chart-pattern strategy's own detectors saw in five years — exploration, not trades. Click one to draw it on the chart.${patternFeed.focus != null ? ` <a data-plive>Back to live detection</a>` : ""}</div>
      <div class="sp-chips">${chips}</div></section>
      <div class="btrs">${rows || `<div class="muted small">${L.length ? "None of this kind." : "No pattern in five years."}</div>`}</div>`;
  }
  /** The Supply & demand zones panel: every zone core/sd_zones.py found, newest first, filterable; a
   *  click goes to it and brings it forward (the rest faint), with its quality checklist — a record of what was examined,
   *  not a score that predicts anything. */
  function zonesPanelHtml() {
    if (!zoneFeed) return `<section><h3>Supply & demand zones</h3><div class="muted small">Finding zones…</div></section>`;
    const L = zoneFeed.list, f2 = (v) => (+v).toFixed(2);
    const counts = { active: L.filter((z) => z.status !== "failed").length, fresh: L.filter((z) => z.status === "fresh").length,
      demand: L.filter((z) => z.kind === "demand").length, supply: L.filter((z) => z.kind === "supply").length, all: L.length };
    const keep = (z) => zoneFilter === "all" || (zoneFilter === "active" ? z.status !== "failed" : zoneFilter === "fresh" ? z.status === "fresh" : z.kind === zoneFilter);
    const chips = [["active", "Active"], ["fresh", "Fresh"], ["demand", "Demand"], ["supply", "Supply"], ["all", "All"]]
      .map(([k, t]) => `<a class="sp-chip ${zoneFilter === k ? "on" : ""}" data-zf="${k}">${t} <span>${counts[k]}</span></a>`).join("");
    const check = (v) => (v == null ? "–" : v ? "✓" : "✗");
    const rows = L.map((z, i) => ({ z, i })).reverse().filter(({ z }) => keep(z)).map(({ z, i }) => {
      const cur = i === zoneFeed.focus;
      const life = z.status === "failed" ? `failed ${prettyDate(z.failed)} (closed through the distal edge)`
        : z.tests.length ? `tested ${z.tests.length}× — last ${prettyDate(z.tests.at(-1).date)}${z.worn ? ` · worn: its orders are spent, it acts as plain ${z.kind === "demand" ? "support" : "resistance"} now` : ""}` : "fresh — not revisited";
      const detail = cur ? `<div class="small" style="margin-top:4px">${Object.entries(zoneFeed.checks).map(([k, t]) =>
          `<div>${check(z.checks[k])} ${esc(t)}</div>`).join("")}
        ${z.tests.length ? `<div class="muted" style="margin-top:4px">${z.tests.map((t, k) => `${k + 1}. ${prettyDate(t.date)} — reached ${f2(t.price)}, closed ${f2(t.close)}${t.wick_through ? " · wick through the distal edge, closed back" : ""}${t.rvol != null ? ` · ${t.rvol.toFixed(1)}× vol` : ""}`).join("<br>")}</div>` : ""}
        ${z.gap ? `<div class="muted" style="margin-top:4px">The departure gapped away from the base — check what news or earnings moved it.</div>` : ""}
        ${z.merged?.length ? `<div class="muted" style="margin-top:4px">One area: also the base${z.merged.length > 1 ? "s" : ""} of ${z.merged.map(prettyDate).join(", ")}, built inside this zone during a retest — merged, its tests counted once.</div>` : ""}</div>` : "";
      return `<div class="btr sp-row ${z.kind === "supply" ? "sp-refused" : "sp-trade"} ${cur ? "cur" : ""}" data-zi="${i}">
        <div class="btr-h"><b>${z.kind === "demand" ? "Demand" : "Supply"} · ${esc(z.name)}</b><span class="muted small">${prettyDate(z.base_from)}</span></div>
        <div class="small sp-title">${f2(z.proximal)} proximal · ${f2(z.distal)} distal · ${z.width_atr.toFixed(1)} ATR wide · ${z.passed}/${z.of} checks</div>
        <div class="muted small">${z.base_bars}-bar base, left ${z.departure_atr.toFixed(1)} ATR${z.rvol != null ? ` on ${z.rvol.toFixed(1)}× volume` : ""} · ${life}</div>${detail}</div>`;
    }).join("");
    return `<section><h3>Supply & demand zones · ${zoneFeed.tf === "W" ? "weekly" : "daily"}</h3>
      <div class="muted small">The compact base each decisive move left from. Proximal edge = the base's furthest body, distal = its furthest wick; a close beyond the distal edge ends it. A zone is a place to watch, not a signal. Click one to go to it.${zoneFeed.focus != null ? ` <a data-zall>Show all again</a>` : ""}</div>
      <div class="sp-chips">${chips}</div></section>
      <div class="btrs">${rows || `<div class="muted small">${L.length ? "None of this kind." : "No zone found."}</div>`}</div>`;
  }
  function renderSide() {
    if (!sideReady || !prefs.tab) return;
    const body = $("#side .side-body");
    body.innerHTML = prefs.tab === "wl" ? wlPanelHtml() : prefs.tab === "list" ? `<div class="wlpanel">${listPanelHtml()}</div>`
      : prefs.tab === "trades" ? `<div class="wlpanel">${tradesPanelHtml()}</div>`
      : prefs.tab === "setups" ? `<div class="wlpanel">${setupsPanelHtml()}</div>`
      : prefs.tab === "patterns" ? `<div class="wlpanel">${patternsPanelHtml()}</div>`
      : prefs.tab === "zones" ? `<div class="wlpanel">${zonesPanelHtml()}</div>`
      : prefs.tab === "news" ? `<div class="wlpanel nwpanel">${newsHtml(null)}</div>` : infoHtml();
    if (prefs.tab === "news") {
      loadNews().then((d) => {
        const host = body.querySelector(".nwpanel"); if (!host || !alive()) return;
        host.innerHTML = newsHtml(d);
        host.querySelector("[data-nwrefresh]")?.addEventListener("click", (e) => { e.preventDefault(); loadNews(true).then(onNews); });
      });
      return;
    }
    body.querySelectorAll(".wlr.cur").forEach((c) => c.scrollIntoView({ block: "nearest" }));
    const $notes = body.querySelector("#wlnotes");
    if ($notes) {  // this stock's notes (fetched once per chart)
      symNotes = symNotes || api(`/api/notes?market=${market}&symbol=${encodeURIComponent(symbol)}`).then((r) => r.notes).catch(() => []);
      symNotes.then((ns) => { if (!$notes.isConnected) return;
        $notes.innerHTML = `<div class="wld-nh"><span class="muted small">Notes</span><span class="spacer"></span>
            ${ns.length ? `<a class="small" href="#/notes/sym/${market}/${encodeURIComponent(symbol)}">all ${ns.length}</a>` : ""}<a class="small" href="#/notes/new/${market}/${encodeURIComponent(symbol)}">+ note</a></div>
          ${ns.slice(0, 3).map((n) => `<a class="wld-note" href="#/notes/${n.id}"><b>${esc(n.title || "Untitled")}</b><span class="muted small">${ago(n.updated_at)}</span></a>`).join("")}`; });
    }
    if (prefs.tab === "patterns") {
      body.querySelectorAll("[data-pf]").forEach((el) => el.onclick = () => { patternFilter = el.dataset.pf; store.set("patternFilter", patternFilter); renderSide(); });
      body.querySelectorAll("[data-pi]").forEach((el) => el.onclick = () => patternFeed?.select(+el.dataset.pi));
      body.querySelector("[data-plive]")?.addEventListener("click", () => patternFeed?.clear());
      body.querySelector("[data-pi].cur")?.scrollIntoView({ block: "nearest" });
      return;
    }
    if (prefs.tab === "zones") {
      body.querySelectorAll("[data-zf]").forEach((el) => el.onclick = () => { zoneFilter = el.dataset.zf; store.set("zoneFilter", zoneFilter); renderSide(); });
      body.querySelectorAll("[data-zi]").forEach((el) => el.onclick = () => zoneFeed?.select(+el.dataset.zi));
      body.querySelector("[data-zall]")?.addEventListener("click", () => zoneFeed?.clear());
      body.querySelector("[data-zi].cur")?.scrollIntoView({ block: "nearest" });
      return;
    }
    if (prefs.tab === "setups") {
      body.querySelectorAll(".sp-chip").forEach((el) => el.onclick = () => { setupFilter = el.dataset.f; store.set("setupFilter", setupFilter); renderSide(); });
      body.querySelectorAll(".sp-row").forEach((el) => el.onclick = () => setupFeed?.select(+el.dataset.si));
      body.querySelector(".sp-row.cur")?.scrollIntoView({ block: "nearest" });
      return;
    }
    if (prefs.tab === "trades") {
      body.querySelectorAll(".btr").forEach((el) => el.onclick = () => {
        const i = +el.dataset.i;
        selTrade = selTrade === i ? -1 : i;
        applyAnnotations();
        if (selTrade >= 0) zoomToTrade(anatomy[selTrade]);
        focusHooks.forEach((f) => f(selTrade >= 0 ? anatomy[selTrade] : null));   // a setups layer selects that trade's setup
        renderSide();
      });
      return;
    }
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
    body.querySelector(".wl-empty-add")?.addEventListener("click", () => { box.hidden = false; box.querySelector("input").focus(); });
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
  $view.innerHTML = `<div class="page-head"><h1>Watchlists</h1>${freshBadges()}<span class="spacer"></span>
      ${cur && !screener ? `<form class="wl-add" autocomplete="off">
        <div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input id="wls" placeholder="Add symbol — any market" spellcheck="false"><ul hidden></ul></div>
        <input id="wln" placeholder="Note (optional)"><button class="primary" type="submit">Add</button></form>` : ""}</div>
    <div class="wl-layout">
      <aside class="wl-lists">${lists.map((l) => `<a href="#/watchlist/${l.id}" class="${l === cur ? "cur" : ""}">
          <span>${l.builtin ? "⚡ " : ""}${esc(l.name)}</span><span class="muted">${l.count ?? ""}</span></a>`).join("")}
        <button class="ghost" id="wlnew">+ New list</button></aside>
      <div class="wl-main">
        ${cur ? `<div class="wl-title"><h2>${esc(cur.name)}</h2>${screener ? "" : '<button class="ibtn" id="wlmenu" title="List menu">⋯</button>'}</div>` : ""}
        ${screener ? `<p class="sd-lead">Filled automatically after each strategy run: every stock a strategy marked <b>tradeable or on watch</b>, kept until you hide it.
          Today's verdicts are in <a href="#/strategies">Today's setups</a>; the lists they are drawn from are the <a href="#/screens">Screens</a>.</p>` : ""}
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
      <div class="muted">${screener ? "Stocks a strategy marks tradeable or on watch appear here after the daily run." : "Type a symbol or company in the box above to add it — or press ☆ next to the name on any chart."}</div>
      ${screener ? '<a class="btn" href="#/strategies">See today\'s setups →</a>' : ""}</div>`;
    return;
  }
  const cols = screener
    ? ["symbol", "name", "market", "peer_group", "group_rs", "last", "chg %", "strategies", "decision", "entry", "to entry %", "stop", "target R", "added"]
    : ["symbol", "name", "market", "peer_group", "group_rs", "last", "chg %", "note", "added"];
  const rows = items.map((e) => {
    const base = [e.symbol, e.name || "", MKT_BADGE[e.market] || e.market, e.peer_group || e.sector || "", e.peer_rs ?? null, e.last, e.change_pct];
    if (!screener) return [...base, e.note || "", e.added_at];
    const p = bestPlan(e);
    return [...base, e.strategies.map((x) => x.strategy).join(" · "), p.decision || "", p.entry ?? null,
      p.entry && e.last ? (p.entry / e.last - 1) * 100 : null, p.stop ?? null, p.target_r ?? null, e.added_at];
  });
  const find = (row) => items.find((x) => x.symbol === row[0] && (MKT_BADGE[x.market] || x.market) === row[2]);
  dataTable(host, cols, rows, {
    name: screener ? "watchlist_screener" : "watchlist_list", sort: ["added", -1],
    // lists mix markets, so every price carries its currency
    format: { added: prettyDate, ...Object.fromEntries(["last", "entry", "stop"].map((c) => [c, (v, row) => v == null ? "" : `${(MKTS.find((m) => m.badge === row[2]) || {}).currency || ""}${fmt(v)}`])) },
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
/** One money amount, the app-wide way: the currency first, then a short scale — $4.9T, $20.2B, $703M;
 *  ₹1,23,456 Cr in India, where crores are how amounts are read (grouped the Indian way). Tables of
 *  figures (financial statements) keep one unit for the whole table instead. */
function moneyShort(v, market) {
  if (v == null) return "";
  const neg = v < 0 ? "−" : "", a = Math.abs(v);
  if (market === "india") { const cr = a / 1e7; return `${neg}₹${cr >= 100 ? Math.round(cr).toLocaleString("en-IN") : cr.toFixed(1)} Cr`; }
  return `${neg}$` + (a >= 1e12 ? `${(a / 1e12).toFixed(1)}T` : a >= 1e9 ? `${(a / 1e9).toFixed(1)}B` : `${(a / 1e6).toFixed(a >= 1e8 ? 0 : 1)}M`);
}
/** a statement table's unit in words: "$ M" -> "$ millions", "₹ Cr" -> "₹ crore" */
const unitWords = (u) => String(u || "").replace(/\s*M$/, " millions").replace(/\s*Cr$/, " crore").replace(/\s*B$/, " billions");

async function moversPage(alive, mkt) {
  const prefs = { period: "1D", universe: "liquid", ...store.get("moversPrefs", {}) };
  mkt = pageMarket(mkt, ["both"]);
  document.title = "Movers · Trading";
  $view.innerHTML = `<div class="page-head"><h1>Top movers</h1>
      ${marketSeg(mkt, [["both", "US + India"]])}
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
    return `<table class="mvt"><thead><tr><th>#</th><th>Symbol</th><th class="mv-g" title="${esc(COL_HELP.group_rs)}">Group · RS</th><th class="num">Last</th><th class="num">Chg%</th>
        <th class="num" title="Volume on the last day ÷ its 50-day average">Rel vol</th><th class="num" title="Traded value on the last day">Value</th></tr></thead>
      <tbody>${rows.map((r, i) => `<tr data-k="${kind}" data-i="${i}">
        <td class="muted">${i + 1}</td>
        <td title="${esc([r.name, r.sector].filter(Boolean).join(" · "))}"><b>${esc(r.symbol.replace(/\.NS$/, ""))}</b><span class="muted small mv-sec">${esc(r.name || r.sector || "")}</span></td>
        <td class="mv-g" title="${esc(r.peer_group || "")}">${r.peer_rs != null ? rsBadge(r.peer_rs) : ""} <span class="small">${esc((r.peer_group || r.sector || "").split(" › ").at(-1))}</span></td>
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

// ------------------------------------------------------------- post-market page

const TONE_CLS = { Strong: "t-strong", Positive: "t-pos", Mixed: "t-mixed", Weak: "t-weak", Negative: "t-neg" };
const WEEKDAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const longDate = (iso) => { const d = new Date(iso + "T00:00:00"); return `${WEEKDAY[d.getDay()]} ${prettyDate(iso)}`; };

/** "3 of 6" in context: how many of the sessions on record scored this low or lower (or this high or higher),
 *  using only sessions up to the one shown — the Breadth page's base-rate framing applied to the tone score. */
function toneBaseRate(history, date, score) {
  const past = (history || []).filter((h) => h.date <= date && h.score != null);
  if (past.length < 20 || score == null) return "";
  const low = score <= 3, n = past.filter((h) => (low ? h.score <= score : h.score >= score)).length;
  return `${n} of the last ${past.length} sessions scored ${score} or ${low ? "lower" : "higher"}`;
}
const PM_TABS = [["summary", "Summary"], ["sectors", "Sectors"], ["stocks", "Stocks"], ["yours", "Your lists"]];
const PM_TAB_HELP = {
  summary: "The day's verdict: the six market-tone signals, indexes, breadth and what stood out",
  sectors: "How sectors and industry groups did today, and whose RS rating moved",
  stocks: "The day's biggest gainers and losers, volume surges and new 52-week highs and lows",
  yours: "Every stock on your watchlists and in Screener picks, with how it did today — biggest moves first",
};
async function postmarketPage(alive, mkt, date, tab) {
  mkt = pageMarket(mkt);
  if (date === "latest") date = null;
  tab = PM_TABS.some(([k]) => k === tab) ? tab : store.get("pmTab", "summary");
  document.title = "Post-market · Trading";
  $view.innerHTML = LOADING;
  const r = await api(`/api/postmarket?market=${mkt}${date ? `&date=${date}` : ""}`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  const head = (context = "") => pageHead("Post-market", { context, extra: marketSeg(mkt) });
  const pmInfo = (p, r) => info([p.doc.tone, p.doc.liquid, p.doc.volume, p.doc.highs_lows].map((t) => `<p>${esc(t)}</p>`).join("")
    + `<p>Watchlist and earnings sections reflect your lists and known dates at the time of analysis (generated ${clock(r.generated_at)}), so a backfilled day shows today's lists.</p>`, "How this is built");
  if (r.error || r.empty) {
    $view.innerHTML = head() + `<div class="empty"><b>${r.empty ? "No post-market analysis yet" : "Could not load it"}</b>
      <div class="muted">${r.empty ? "It is written by the daily pipeline after each close. To build it now (from scripts/, PYTHONPATH=.):" : esc(r.error)}</div>${r.command ? `<code>${esc(r.command)}</code>` : ""}</div>`;
    $view.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(`#/postmarket/${b.dataset.v}`));
    return;
  }
  const p = r.payload, H = r.history, i = H.findIndex((h) => h.date === p.date);
  const pmHref = (d, t = tab) => `#/postmarket/${mkt}/${d || "latest"}${t !== "summary" ? "/" + t : ""}`;
  const pc = (v, d = 2) => (v == null ? "" : `${v > 0 ? "+" : ""}${v.toFixed(d)}%`);
  const sym = (s) => esc(s.replace(/\.NS$/, ""));
  const stockTable = (rows, key, cols = "pct") => !rows.length ? '<div class="muted small mv-none">None.</div>' : `<table class="mvt pmt"><thead><tr><th>Symbol</th>
      <th class="num">Close</th><th class="num">Chg%</th><th class="num" title="Volume ÷ 50-day average">Rel vol</th></tr></thead><tbody>
      ${rows.map((x, j) => `<tr data-k="${key}" data-i="${j}" title="${esc([x.name, x.sector].filter(Boolean).join(" · "))}"><td><b>${sym(x.symbol)}</b><span class="muted small mv-sec">${esc(x.name || x.sector || "")}</span></td>
        <td class="num">${fmt(x.close)}</td><td class="num"><span class="mv-pct ${x.pct >= 0 ? "up" : "dn"}">${pc(x.pct)}</span></td>
        <td class="num ${x.rvol >= 2 ? "strong" : "muted"}">${x.rvol != null ? x.rvol.toFixed(1) + "×" : ""}</td></tr>`).join("")}</tbody></table>`;
  const lists = { gainers: p.movers.gainers, losers: p.movers.losers, vup: p.volume.up, vdn: p.volume.down, hi: p.highs_lows.highs, lo: p.highs_lows.lows, wl: p.watchlists };
  const B = p.breadth, bt = B?.today, bp = B?.prev, ba = B?.avg10;
  const brow = (label, k, pct = false) => {
    const f = (o) => (o && o[k] != null ? (pct ? `${((o[k] / o.n) * 100).toFixed(0)}%` : Math.round(o[k]).toLocaleString()) : "—");
    return `<tr><td>${label}</td><td class="num"><b>${f(bt)}</b></td><td class="num muted">${f(bp)}</td><td class="num muted">${f(ba)}</td></tr>`;
  };
  const sectorBars = (rows) => { const mx = Math.max(0.005, ...rows.map((x) => Math.abs(x.pct)));
    return rows.map((x) => `<div class="dbar"><span class="dl" title="${x.n} stocks · ${(x.up * 100).toFixed(0)}% rose">${esc(x.group)}</span>
      <span class="dt"><i class="${x.pct >= 0 ? "up" : "dn"}" style="width:${(Math.abs(x.pct) / mx) * 50}%;${x.pct >= 0 ? "left:50%" : `right:50%`}"></i></span>
      <span class="dv ${x.pct >= 0 ? "pos" : "neg"}">${pc(x.pct * 100)}</span></div>`).join(""); };
  const ind = p.sectors.industry, rs = p.sector_rs;
  const timeline = H.slice(0, 60).reverse().map((h) => `<a href="${pmHref(h.date)}" class="tl ${TONE_CLS[h.tone] || ""} ${h.date === p.date ? "cur" : ""}" title="${longDate(h.date)} — ${h.tone} (${h.score}/6) · ${h.up?.toLocaleString()} up / ${h.down?.toLocaleString()} down"></a>`).join("");
  const pmDates = H.map((h) => ({ value: h.date, label: `${longDate(h.date)} · ${h.tone}` }));
  const wireTimeline = () => {
    const strip = $view.querySelector(".pm-tl"), read = $view.querySelector(".pm-tl-read");
    if (!strip || !read) return;
    const idle = read.textContent;
    strip.onmouseover = (e) => { const a = e.target.closest(".tl"); if (a) read.textContent = a.title; };
    strip.onmouseleave = () => { read.textContent = idle; };
  };
  $view.innerHTML = head(datePicker(pmDates, p.date) + pmInfo(p, r)) + `
    <div class="pm-tl" title="Market tone, last ${Math.min(60, H.length)} sessions (oldest left) — click a day">${timeline}</div>
    <div class="pm-tl-legend muted small"><span class="pm-tl-read">Market tone, last ${Math.min(60, H.length)} sessions, oldest on the left — hover a day for its numbers, click it to open that session.</span>
      <span class="spacer"></span>${Object.entries(TONE_CLS).map(([t, c]) => `<span class="pm-key"><i class="tl ${c}"></i>${t}</span>`).join("")}</div>
    <nav class="ptabs pm-tabs">${PM_TABS.map(([k, t]) => `<a data-t="${k}" class="${k === tab ? "active" : ""}" title="${esc(PM_TAB_HELP[k] || "")}">${t}${
      k === "stocks" ? ` <span class="n">${p.movers.gainers.length + p.movers.losers.length}</span>` : k === "yours" ? ` <span class="n">${p.watchlists.length}</span>` : ""}</a>`).join("")}</nav>
    <div class="pmtab" data-t="summary">
    <div class="pm-hero sec-card">
      <div><div class="muted small">${esc(p.market_name)} · ${longDate(p.date)} <span class="muted">(vs ${prettyDate(p.prev_date)})</span></div>
        <div class="pm-tone ${TONE_CLS[p.tone.label]}">${p.tone.label}<span>${p.tone.score} of ${p.tone.of} signals bullish</span></div>
        ${toneBaseRate(H, p.date, p.tone.score) ? `<div class="muted small">${toneBaseRate(H, p.date, p.tone.score)}.</div>` : ""}
        <div class="pm-ad"><span class="pos">${p.counts.up.toLocaleString()} up</span><span class="adbar"><i class="up" style="width:${(p.counts.up / Math.max(1, p.counts.up + p.counts.down)) * 100}%"></i><i class="dn" style="width:${(p.counts.down / Math.max(1, p.counts.up + p.counts.down)) * 100}%"></i></span><span class="neg">${p.counts.down.toLocaleString()} down</span>
          <span class="muted small">· ${p.counts.new_highs} new highs / ${p.counts.new_lows} new lows among ${p.counts.liquid.toLocaleString()} liquid stocks</span></div></div>
      <div class="pm-sigw"><div class="sa-k">The six signals · ${p.tone.score} bullish</div>
      <ul class="pm-sig">${p.tone.signals.map((x) => x.ok == null
        ? `<li class="na"><span class="sgl">n/a</span>${esc(x.text)} — no data</li>`
        : `<li class="${x.ok ? "ok" : "no"}"><span class="sgl">${x.ok ? "▲ bullish" : "▼ bearish"}</span>${esc(x.ok ? x.text : x.text_not)}</li>`).join("")}</ul></div>
    </div>
    <div class="pm-idx">${p.indexes.map((x) => `<div class="sec-card pm-i"><div class="muted small">${esc(x.label)}</div>
        <div class="pm-ic"><b>${fmt(+x.close.toFixed(2))}</b><span class="${(x.vol ? -x.pct : x.pct) >= 0 ? "pos" : "neg"}">${pc(x.pct)}</span></div>
        ${x.vol ? `<div class="muted small">${x.pct >= 0 ? "Fear rising" : "Fear easing"}</div>` : `<div class="pm-chips"><span class="${x.above50 ? "pos" : "neg"}">${x.above50 ? "above" : "below"} 50D</span><span class="${x.above200 ? "pos" : "neg"}">${x.above200 ? "above" : "below"} 200D</span><span class="muted">${x.from_high > -0.5 ? "at 52w high" : pc(x.from_high, 1) + " from high"}</span></div>`}</div>`).join("")}</div>
    <div class="sec-top">
      <section class="sec-card"><h3>Breadth</h3>${bt ? `<table class="stt"><thead><tr><th></th><th class="num">${prettyDate(p.date)}</th><th class="num">Previous</th><th class="num">10-day avg</th></tr></thead><tbody>
          ${brow("Advancers", "adv")}${brow("Decliners", "dec")}${brow("Up 4%+", "up4")}${brow("Down 4%+", "dn4")}${brow("New 52-week highs", "highs")}${brow("New 52-week lows", "lows")}${brow("Above 50-day average", "above50", true)}${brow("Above 5-day average", "above5", true)}</tbody></table>
          <p class="muted small">The ${Math.round(bt.n).toLocaleString()} most-traded stocks. <a href="#/breadth/${mkt}">Breadth page →</a></p>` : '<div class="muted small">No breadth row for this day.</div>'}</section>
      <section class="sec-card"><h3>Sectors today</h3><div class="dbars">${sectorBars(p.sectors.sector)}</div>
        <p class="muted small"><a href="#/sectors/${mkt}">Sectors page →</a> ${info(`<p>${esc(p.doc.sectors)}</p>`)}</p></section>
    </div>
    </div><div class="pmtab" data-t="sectors">
    <div class="sec-top">
      <section class="sec-card"><h3>Strongest industries</h3><div class="dbars">${sectorBars(ind.slice(0, 8))}</div></section>
      <section class="sec-card"><h3>Weakest industries</h3><div class="dbars">${sectorBars(ind.slice(-8).reverse())}</div></section>
    </div>
    ${rs && (rs.rs_up.length || rs.quadrant_changes.length) ? `<section class="sec-card"><div class="sec-card-h"><h3>Group leadership changes</h3><span class="muted small">RS rating vs ${prettyDate(rs.compared_with)} · rotation changes vs the previous day</span></div>
      <div class="pm-3">
        <div><div class="muted small">RS rating rising</div>${rs.rs_up.map((x) => `<div class="pm-li"><a href="#/sectors/${mkt}/industry/${encodeURIComponent(x.group)}">${esc(x.group)}</a>${rsBadge(x.rs)}<span class="pos">▲${x.delta}</span></div>`).join("") || '<div class="muted small">—</div>'}</div>
        <div><div class="muted small">RS rating falling</div>${rs.rs_down.map((x) => `<div class="pm-li"><a href="#/sectors/${mkt}/industry/${encodeURIComponent(x.group)}">${esc(x.group)}</a>${rsBadge(x.rs)}<span class="neg">▼${-x.delta}</span></div>`).join("") || '<div class="muted small">—</div>'}</div>
        <div><div class="muted small">Rotation changes</div>${rs.quadrant_changes.slice(0, 10).map((x) => `<div class="pm-li"><a href="#/sectors/${mkt}/${x.level}/${encodeURIComponent(x.group)}">${esc(x.group)}</a><span class="qtag ${QUAD_CLS[x.from]}">${x.from}</span>→<span class="qtag ${QUAD_CLS[x.to]}">${x.to}</span></div>`).join("") || '<div class="muted small">—</div>'}</div>
      </div></section>` : ""}
    </div><div class="pmtab" data-t="stocks">
    <div class="sec-top"><section class="sec-card"><h3>Top gainers</h3>${stockTable(p.movers.gainers, "gainers")}</section><section class="sec-card"><h3>Top losers</h3>${stockTable(p.movers.losers, "losers")}</section></div>
    <div class="sec-top"><section class="sec-card"><h3>Unusual volume — up</h3>${stockTable(p.volume.up, "vup")}</section><section class="sec-card"><h3>Unusual volume — down</h3>${stockTable(p.volume.down, "vdn")}</section></div>
    <div class="sec-top"><section class="sec-card"><h3>New 52-week highs <span class="muted">${p.counts.new_highs}</span></h3>${stockTable(p.highs_lows.highs, "hi")}</section><section class="sec-card"><h3>New 52-week lows <span class="muted">${p.counts.new_lows}</span></h3>${stockTable(p.highs_lows.lows, "lo")}</section></div>
    </div><div class="pmtab" data-t="yours">
    <section class="sec-card"><div class="sec-card-h"><h3>Your watchlists</h3><span class="muted small">${p.watchlists.length} names on your lists and Screener picks, biggest moves first</span></div>
      ${p.watchlists.length ? `<table class="mvt pmt pm-wl"><thead><tr><th>Symbol</th><th>Lists</th><th class="num">Close</th><th class="num">Chg%</th><th class="num">Rel vol</th><th>Signals</th></tr></thead><tbody>
        ${p.watchlists.map((x, j) => `<tr data-k="wl" data-i="${j}"><td><b>${sym(x.symbol)}</b><span class="muted small mv-sec">${esc(x.name || "")}</span></td><td class="muted small">${esc(x.lists.join(", "))}</td>
          <td class="num">${fmt(x.close)}</td><td class="num"><span class="mv-pct ${x.pct >= 0 ? "up" : "dn"}">${pc(x.pct)}</span></td><td class="num ${x.rvol >= 2 ? "strong" : "muted"}">${x.rvol != null ? x.rvol.toFixed(1) + "×" : ""}</td>
          <td class="pm-flags">${x.cross50 === "up" ? '<span class="pos">crossed above 50D</span>' : x.cross50 === "down" ? '<span class="neg">fell below 50D</span>' : ""}${x.new_high ? '<span class="pos">new 52w high</span>' : ""}${x.new_low ? '<span class="neg">new 52w low</span>' : ""}${x.rvol >= 2 ? `<span>${x.pct >= 0 ? "heavy buying" : "heavy selling"}</span>` : ""}${x.earnings ? `<span class="warn">earnings ${prettyDate(x.earnings)}</span>` : ""}</td></tr>`).join("")}</tbody></table>` : '<div class="muted small">Your watchlists are empty for this market.</div>'}</section>
    <section class="sec-card"><h3>Screener changes</h3>${p.screener.length ? `<div class="pm-scr">${p.screener.map((x) => `<div class="pm-s"><div class="pm-sh"><b>${esc(x.strategy)}</b><span class="muted small">${x.tradeable} tradeable · ${x.watch} on watch · run ${prettyDate(x.run)}${x.prev_run ? ` vs ${prettyDate(x.prev_run)}` : ""}</span></div>
        <div class="pm-ch">${x.new_tradeable.length ? `<span class="muted small">New tradeable</span>${x.new_tradeable.map((t) => `<a class="chip-s up" href="#/chart/${mkt}/${encodeURIComponent(t.symbol)}" title="${esc([t.decision, t.setup, t.entry ? "entry " + fmt(t.entry) : "", t.stop ? "stop " + fmt(t.stop) : ""].filter(Boolean).join(" · "))}">${sym(t.symbol)}</a>`).join("")}` : '<span class="muted small">No new tradeable names</span>'}</div>
        ${x.dropped_tradeable.length ? `<div class="pm-ch"><span class="muted small">No longer tradeable</span>${x.dropped_tradeable.map((t) => `<a class="chip-s dn" href="#/chart/${mkt}/${encodeURIComponent(t)}">${sym(t)}</a>`).join("")}</div>` : ""}
        ${x.new_watch.length ? `<div class="pm-ch"><span class="muted small">New on watch</span>${x.new_watch.slice(0, 30).map((t) => `<a class="chip-s" href="#/chart/${mkt}/${encodeURIComponent(t)}">${sym(t)}</a>`).join("")}${x.new_watch.length > 30 ? `<span class="muted small">+${x.new_watch.length - 30}</span>` : ""}</div>` : ""}</div>`).join("")}</div>` : '<div class="muted small">No screening run for this day.</div>'}</section>
    <section class="sec-card"><h3>Earnings in the next 10 days</h3>${p.earnings.length ? p.earnings.map((x) => `<div class="pm-li"><a href="#/chart/${mkt}/${encodeURIComponent(x.symbol)}"><b>${sym(x.symbol)}</b></a><span class="muted">${esc(x.name || "")}</span><span>${longDate(x.date)}</span><span class="muted small">${x.days}d${x.watched ? " · on your watchlist" : ""}</span></div>`).join("") : '<div class="muted small">None among watched or screened names.</div>'}</section>
    </div>
    `;
  $view.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(`#/postmarket/${b.dataset.v}`));
  wireDatePicker($view, pmDates, p.date, (d, latest) => go(pmHref(latest ? null : d)));
  wireTimeline();
  // tabs switch in place (no reload); the URL keeps the tab so a date change or a reload returns to it
  const showTab = (t) => {
    tab = t; store.set("pmTab", t);
    $view.querySelectorAll(".pmtab").forEach((x) => { x.hidden = x.dataset.t !== t; });
    $view.querySelectorAll(".pm-tabs a").forEach((a) => a.classList.toggle("active", a.dataset.t === t));
    history.replaceState(null, "", pmHref(date ? p.date : null));
    $view.querySelectorAll(".pm-tl a").forEach((a, k) => { a.href = pmHref(H.slice(0, 60).reverse()[k].date); });
  };
  $view.querySelector(".pm-tabs").onclick = (e) => { const a = e.target.closest("[data-t]"); if (a) showTab(a.dataset.t); };
  showTab(tab);
  $view.querySelectorAll("tr[data-k]").forEach((tr) => tr.onclick = () => {
    const rows = lists[tr.dataset.k], x = rows[+tr.dataset.i];
    const label = { gainers: "Top gainers", losers: "Top losers", vup: "Unusual volume up", vdn: "Unusual volume down", hi: "New highs", lo: "New lows", wl: "Watchlists" }[tr.dataset.k];
    openChartFromList(mkt, x.symbol, rows.map((y) => y.symbol), `${label} · ${prettyDate(p.date)}`, location.hash);
  });
}

// ------------------------------------------------------------- sectors page

const LEVEL_NAME = { sector: "sectors", industry: "industry groups", sub: "sub-industries" };
/** a sub-industry key is "Industry › Sub"; show the sub part, with the industry as context */
const groupParts = (g) => { const i = g.indexOf(" › "); return i < 0 ? [g, null] : [g.slice(i + 3), g.slice(0, i)]; };
const QUADS = ["Leading", "Improving", "Weakening", "Lagging"];
const QUAD_CLS = { Leading: "q-lead", Improving: "q-impr", Weakening: "q-weak", Lagging: "q-lag" };
const SEC_H = ["1W", "1M", "3M", "6M", "12M"];
const pct1 = (v, d = 1) => (v == null ? "" : `${v > 0 ? "+" : ""}${(v * 100).toFixed(d)}%`);
const pctCls = (v) => (v == null ? "" : v >= 0 ? "pos" : "neg");
const secHref = (m, level, g) => `#/sectors/${m}/${level}${g ? "/" + encodeURIComponent(g) : ""}`;
const RS_WORDS = (rs) => `${rs >= 80 ? "a leading" : rs >= 50 ? "a middling" : "a lagging"} group: its RS rating (1–99) against every other group; 80+ leading, under 50 lagging`;
const rsBadge = (rs, what = "Group RS") => (rs == null ? "" : `<span class="rsb ${rs >= 80 ? "hi" : rs >= 50 ? "mid" : "lo"}" title="${esc(what)} ${rs} — ${esc(RS_WORDS(rs))}">${rs}</span>`);

/** The Breadth page's macro strip (/api/macro): rates, the dollar, oil, metals and credit for this market —
 *  value, 1-day and 1-month change (points for a yield), a 3-month sparkline, and why it matters on hover. */
async function macroStrip(el, mkt) {
  const d = await api(`/api/macro?market=${mkt}`).catch(() => null);
  if (!el.isConnected) return;
  if (!d?.series?.length) { el.remove(); return; }
  el.innerHTML = macroTiles(d.series);
}
/** the strip's tiles, shared by the Breadth page and Today's macro section */
function macroTiles(series) {
  const num = (v, dp = 2) => v.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
  const chg = (v, u) => (v == null ? "—" : `<span class="${v >= 0 ? "pos" : "neg"}">${v > 0 ? "+" : ""}${u === "bp" ? `${num(v, Math.abs(v) < 10 ? 1 : 0)}bp` : `${num(v, Math.abs(v) < 10 ? 2 : 1)}%`}</span>`);
  const val = (x) => (x.unit === "%" ? `${num(x.close)}%` : x.unit === "₹" ? `₹${num(x.close)}` : `${num(x.close)}${x.unit === "index" ? "" : ` <span class="muted small">${esc(x.unit)}</span>`}`);
  return series.map((x) => `<div class="mtile" title="${esc(x.label)} — ${esc(x.why)} Last close ${esc(x.date)}.">
      <div class="mt-l">${esc(x.short)}</div>
      <div class="mt-v">${val(x)}</div>
      <div class="mt-c"><span class="muted">1D</span> ${chg(x.d1, x.change_unit)} <span class="muted">1M</span> ${chg(x.m1, x.change_unit)}</div>
      ${sparkSvg(x.spark, 120, 24)}</div>`).join("");
}

/** Today's macro card (/api/macro/analysis): the rule-based read of rates, the dollar, oil, credit, growth and
 *  fear for this market (marketdata/macro.py `analysis`), laid out like the market card beside it — verdict,
 *  signals with the numbers behind them, where levels stand against history — and the strip's tiles below. */
const MACRO_CLS = { Supportive: "t-strong", "Mostly supportive": "t-pos", Mixed: "t-mixed", Cautious: "t-weak", Hostile: "t-neg" };
async function macroSection(card, tiles, mkt) {
  const d = await api(`/api/macro/analysis?market=${mkt}`).catch(() => null);
  if (!card.isConnected) return;
  const a = d?.analysis;
  tiles.innerHTML = macroTiles(d?.series || []);
  if (!a) {
    card.innerHTML = tdHead(`Macro · ${esc(mktInfo(mkt).name)}`) + `<div class="muted small">${d ? "No macro series stored yet — they load with the daily <code>indexes</code> job." : "Could not load the macro read."}</div>`;
    return;
  }
  const sig = a.signals.map((x) => tdSignal(x.ok, x.ok ? x.text : x.text_not, x.detail, x.why)).join("");
  const hist = [...a.unusual.map((x) => `<li title="${esc(x.why)}"><b>${esc(x.name)}</b> <span class="muted">— ${esc(x.text)}</span> <span class="tag watch">unusual</span></li>`),
    ...a.extremes.map((x) => `<li><b>${esc(x.name)}</b> <span class="muted">— ${esc(x.text)}</span></li>`)].join("");
  card.innerHTML = tdHead(`Macro · ${esc(mktInfo(mkt).name)}`, `<span class="muted small">${prettyDate(a.date)}</span>${info(`<p>${esc(a.doc)}</p><p>Macro moves slowly and sets the backdrop, not the trade: a headwind argues for smaller size and tighter selection, not for selling a working setup. Hover a signal or a tile for why it matters.</p>`)}`)
    + tdVerdict(MACRO_CLS[a.label], a.label, `${a.score} of ${a.of} signals supportive`)
    + `<ul class="td-sig">${sig}</ul>`
    + (hist ? `<div class="td-sub">Levels, against history since 2015</div><ul class="td-rates">${hist}</ul>` : "")
    + `<div class="td-foot"><a class="small" href="#/learn/macro-rates">Macro guides →</a></div>`;
}

/** Today's rates card (/api/rates): the market's policy rate and bill / bond yields over the long run —
 *  a chart with a range picker and a legend that toggles each line (set rates drawn as steps), beside a
 *  table of each rate's latest value, its 1-month / 1-year / 5-year change and when a set rate last moved. */
const RATE_COLORS = ["#f59e0b", "#a855f7", "#64748b", "#14b8a6", "#3b82f6", "#ec4899", "#ef4444"];
const RATE_RANGES = [["1Y", 1], ["5Y", 5], ["10Y", 10], ["20Y", 20], ["Max", 0]];
async function ratesSection(card, mkt) {
  const d = await api(`/api/rates?market=${mkt}`).catch(() => null);
  if (!card.isConnected) return;
  const rs = d?.rates || [];
  const title = `Rates & yields · ${esc(mktInfo(mkt).name)}`;
  if (!rs.length) { card.innerHTML = tdHead(title) + `<div class="muted small">${d ? "No rates stored yet — they load with the daily <code>rates</code> job." : "Could not load the rates."}</div>`; return; }
  const bp = (v) => (v == null ? '<span class="muted">—</span>' : `<span class="${v > 0 ? "pos" : v < 0 ? "neg" : "muted"}">${v > 0 ? "+" : ""}${Math.round(v)}bp</span>`);
  const color = Object.fromEntries(rs.map((x, i) => [x.key, RATE_COLORS[i % RATE_COLORS.length]]));
  const shown = new Set(store.get(`ratesShown_${mkt}`, null) || rs.filter((x) => x.show).map((x) => x.key));
  const range = store.get("ratesRange", "10Y");
  const sources = [...new Set(rs.map((x) => x.source))].join(" · ");
  const rows = rs.map((x) => `<tr title="${esc(x.label)} — ${esc(x.source)}, stored from ${prettyDate(x.first)}">
      <td><i class="rt-sw" style="background:${color[x.key]}"></i>${esc(x.short)}${x.since ? `<div class="muted small">since ${prettyDate(x.since.date)} (${bp((x.since.to - x.since.from) * 100)})</div>` : ""}</td>
      <td class="num"><b>${x.value.toFixed(2)}%</b><div class="muted small">${prettyDate(x.date)}</div></td>
      <td class="num">${bp(x.m1)}</td><td class="num">${bp(x.y1)}</td><td class="num">${bp(x.y5)}</td></tr>`).join("");
  card.innerHTML = tdHead(title, `<span class="muted small">${esc(sources)}</span>${info(`<p>Each market's policy rate and its bill and bond yields, with as much history as is stored. Set rates (the Fed's target, RBI's repo rate) are drawn as steps; the table says when each last moved.</p><p>US: FRED, back to the 1950s–80s by series, refreshed daily (a day behind). India: RBI's daily published rates; the repo rate's history before that is a list of RBI's announced changes, and the 10-year yield's is monthly (OECD) from 2011. T-bill and other G-sec history builds up from the first daily read.</p><p>Click a legend entry to show or hide its line.</p>`)}`)
    + `<div class="rt-wrap"><div class="rt-chart-col">
        <div class="rt-bar"><div class="rt-legend">${rs.map((x) => `<button data-k="${x.key}" class="${shown.has(x.key) ? "on" : ""}"><i class="rt-sw" style="background:${color[x.key]}"></i>${esc(x.short)}</button>`).join("")}</div>
          ${segmented(RATE_RANGES.map(([k]) => [k, k]), range, "rt-range")}</div>
        <div class="rt-chart"></div></div>
      <table class="rt-tbl"><thead><tr><th>Rate</th><th class="num">Latest</th><th class="num">1M</th><th class="num">1Y</th><th class="num">5Y</th></tr></thead><tbody>${rows}</tbody></table></div>`;

  const el_ = card.querySelector(".rt-chart");
  const chart = LC.createChart(el_, { autoSize: true, ...chartTheme(), crosshair: { mode: LC.CrosshairMode.Normal },
    localization: { priceFormatter: (v) => `${v.toFixed(2)}%` } });
  const series = {};
  for (const x of rs) {
    series[x.key] = chart.addSeries(LC.LineSeries, { color: color[x.key], lineWidth: x.kind === "policy" ? 2 : 1.5, lineType: x.step ? LC.LineType.WithSteps : LC.LineType.Simple,
      priceLineVisible: false, lastValueVisible: shown.has(x.key), visible: shown.has(x.key), title: "" });
    series[x.key].setData(x.points.map(([t, v]) => ({ time: t, value: v })));
  }
  const last = rs.map((x) => x.date).sort().at(-1);
  const applyRange = (r) => {
    const yrs = Object.fromEntries(RATE_RANGES)[r];
    if (!yrs) { chart.timeScale().fitContent(); return; }
    const from = new Date(last); from.setFullYear(from.getFullYear() - yrs);
    chart.timeScale().setVisibleRange({ from: from.toISOString().slice(0, 10), to: last });
  };
  applyRange(range);
  card.querySelectorAll(".rt-range button").forEach((b) => b.onclick = () => {
    card.querySelectorAll(".rt-range button").forEach((o) => o.classList.toggle("on", o === b));
    store.set("ratesRange", b.dataset.v); applyRange(b.dataset.v);
  });
  card.querySelectorAll(".rt-legend button").forEach((b) => b.onclick = () => {
    const k = b.dataset.k, on = !shown.has(k);
    on ? shown.add(k) : shown.delete(k);
    b.classList.toggle("on", on);
    series[k].applyOptions({ visible: on, lastValueVisible: on });
    store.set(`ratesShown_${mkt}`, [...shown]);
  });
  { const prev = cleanup; cleanup = () => { chart.remove(); prev(); }; }
}

/** a sparkline of a group's RS line (values relative to its first point) */
function sparkSvg(vals, w = 90, h = 22) {
  if (!vals || vals.length < 2) return "";
  const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * w},${h - 2 - ((v - lo) / span) * (h - 4)}`).join(" ");
  const up = vals.at(-1) >= vals[0];
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}"><polyline points="${pts}" fill="none" stroke="${up ? "#26a69a" : "#ef5350"}" stroke-width="1.5"/></svg>`;
}

/** Relative Rotation Graph: RS-Ratio (x) vs RS-Momentum (y), each group's last weeks as a tail */
function rrgSvg(groups, hot, pinned, width = 560) {
  // drawn at the container's pixel size (1 viewBox unit = 1px), so text stays readable however wide the card is
  const W = Math.max(360, Math.round(width)), H = Math.round(Math.max(380, Math.min(680, W * 0.5))), P = 40;
  const pts = groups.flatMap((g) => g.rrg || []);
  if (!pts.length) return '<div class="muted small">Not enough history for a rotation graph.</div>';
  // each axis fits the data (always keeping the 100 crosshair in view), so the trails fill the plot
  const span = (vs) => { let lo = Math.min(100, ...vs), hi = Math.max(100, ...vs); if (hi - lo < 3) { const m = (hi + lo) / 2; lo = m - 1.5; hi = m + 1.5; }
    const pad = (hi - lo) * 0.06; return [lo - pad, hi + pad]; };
  const [x0, x1] = span(pts.map((p) => p.ratio)), [y0, y1] = span(pts.map((p) => p.mom));
  const X = (v) => P + ((v - x0) / (x1 - x0)) * (W - 2 * P), Y = (v) => H - P - ((v - y0) / (y1 - y0)) * (H - 2 * P);
  const cx = X(100), cy = Y(100);
  const ticks = (lo, hi, n) => { const raw = (hi - lo) / n, mag = 10 ** Math.floor(Math.log10(raw)), step = [1, 2, 5, 10].map((k) => k * mag).find((s) => s >= raw);
    const out = []; for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6)); return out; };
  const grid = ticks(x0, x1, Math.max(4, Math.round(W / 140))).map((v) => `<line x1="${X(v).toFixed(1)}" y1="${P}" x2="${X(v).toFixed(1)}" y2="${H - P}" class="rqg"/><text x="${X(v).toFixed(1)}" y="${H - P + 13}" class="rqt" text-anchor="middle">${v}</text>`).join("")
    + ticks(y0, y1, Math.max(4, Math.round(H / 90))).map((v) => `<line x1="${P}" y1="${Y(v).toFixed(1)}" x2="${W - P}" y2="${Y(v).toFixed(1)}" class="rqg"/><text x="${P - 5}" y="${(Y(v) + 3.5).toFixed(1)}" class="rqt" text-anchor="end">${v}</text>`).join("");
  // mid-tone colours that read on both the dark and the light themes
  const palette = ["#3b82f6", "#f97316", "#14b8a6", "#ec4899", "#a855f7", "#06b6d4", "#65a30d", "#ef4444", "#6366f1", "#10b981", "#d946ef", "#0ea5e9", "#f43f5e", "#8b5cf6", "#22c55e", "#e11d48"];
  // label placement: each name tries right of its head, left, above, below, then further out; the first
  // spot that overlaps no placed label and no head wins. A label that had to move gets a leader line.
  const name = (g) => (n => n.length > 30 ? n.slice(0, 29) + "…" : n)(groupParts(g.group)[0]);
  const heads = groups.map((g) => g.rrg?.length ? [X(g.rrg.at(-1).ratio), Y(g.rrg.at(-1).mom)] : null);
  const boxes = [], lab = {};
  const hits = (b) => boxes.some((o) => b.x < o.x + o.w && b.x + b.w > o.x && b.y < o.y + o.h && b.y + b.h > o.y)
    || heads.some((h) => h && h[0] > b.x - 4 && h[0] < b.x + b.w + 4 && h[1] > b.y - 4 && h[1] < b.y + b.h + 4);
  groups.map((g, i) => i).filter((i) => heads[i]).sort((a, b) => (groups[b].rs ?? 0) - (groups[a].rs ?? 0)).forEach((i) => {
    const [hx, hy] = heads[i], w = name(groups[i]).length * 6.6 + 4, h = 14;
    const spots = [];
    for (const r of [0, 15, 30, 45, 60]) spots.push([hx + 7, hy - 8 - r], [hx + 7, hy - 8 + r], [hx - 7 - w, hy - 8 - r], [hx - 7 - w, hy - 8 + r], [hx - w / 2, hy - 22 - r], [hx - w / 2, hy + 7 + r]);
    let pick = spots.map(([x, y]) => ({ x: Math.max(P, Math.min(W - P - w, x)), y: Math.max(P, Math.min(H - P - h, y)), w, h })).find((b) => !hits(b));
    if (!pick) pick = { x: Math.max(P, Math.min(W - P - w, hx + 7)), y: Math.max(P, Math.min(H - P - h, hy - 8)), w, h };
    boxes.push(pick);
    lab[i] = { x: pick.x + 2, y: pick.y + 11, moved: Math.hypot(pick.x - (hx + 7), pick.y - (hy - 8)) > 3, ax: pick.x + (pick.x > hx ? 0 : w), ay: pick.y + 6 };
  });
  const series = groups.map((g, i) => {
    const t = g.rrg || []; if (!t.length) return "";
    const c = palette[i % palette.length], head = t.at(-1), on = hot === g.group || pinned === g.group, L = lab[i];
    const line = t.map((p) => `${X(p.ratio).toFixed(1)},${Y(p.mom).toFixed(1)}`).join(" ");
    return `<g class="rrg-g ${on ? "on" : ""} ${pinned === g.group ? "pin" : ""}" data-g="${esc(g.group)}"><title>${esc(g.group)} — ${g.quadrant || ""}\nRS-Ratio ${head.ratio.toFixed(1)} · RS-Momentum ${head.mom.toFixed(1)}</title>
      <polyline points="${line}" fill="none" stroke="${c}" stroke-width="${on ? 2.5 : 1.3}" stroke-opacity="${on ? 1 : .75}"/>
      ${t.slice(0, -1).map((p) => `<circle cx="${X(p.ratio).toFixed(1)}" cy="${Y(p.mom).toFixed(1)}" r="1.8" fill="${c}"/>`).join("")}
      <circle cx="${X(head.ratio).toFixed(1)}" cy="${Y(head.mom).toFixed(1)}" r="${on ? 6 : 4.5}" fill="${c}" stroke="var(--panel)" stroke-width="1"/>
      ${L.moved ? `<line x1="${X(head.ratio).toFixed(1)}" y1="${Y(head.mom).toFixed(1)}" x2="${L.ax.toFixed(1)}" y2="${L.ay.toFixed(1)}" stroke="${c}" stroke-width=".7" stroke-opacity=".6"/>` : ""}
      <text class="lbl" x="${L.x.toFixed(1)}" y="${L.y.toFixed(1)}" fill="${c}">${esc(name(g))}</text></g>`;
  }).join("");
  return `<svg class="rrg ${pinned && groups.some((g) => g.group === pinned) ? "pinned" : ""}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
    <rect x="${cx}" y="${P}" width="${W - P - cx}" height="${cy - P}" class="rq lead"/><rect x="${cx}" y="${cy}" width="${W - P - cx}" height="${H - P - cy}" class="rq weak"/>
    <rect x="${P}" y="${cy}" width="${cx - P}" height="${H - P - cy}" class="rq lag"/><rect x="${P}" y="${P}" width="${cx - P}" height="${cy - P}" class="rq impr"/>
    ${grid}
    <text x="${W - P - 6}" y="${P + 14}" class="rql" text-anchor="end">LEADING</text><text x="${W - P - 6}" y="${H - P - 6}" class="rql" text-anchor="end">WEAKENING</text>
    <text x="${P + 6}" y="${H - P - 6}" class="rql">LAGGING</text><text x="${P + 6}" y="${P + 14}" class="rql">IMPROVING</text>
    <line x1="${cx}" y1="${P}" x2="${cx}" y2="${H - P}" class="rqx"/><line x1="${P}" y1="${cy}" x2="${W - P}" y2="${cy}" class="rqx"/>
    <text x="${W / 2}" y="${H - 6}" class="rqa" text-anchor="middle">RS-Ratio → (relative strength trend)</text>
    <text x="12" y="${H / 2}" class="rqa" text-anchor="middle" transform="rotate(-90 12 ${H / 2})">RS-Momentum →</text>
    ${series}</svg>`;
}

async function sectorsPage(alive, mkt, level, group) {
  mkt = pageMarket(mkt);
  level = ["industry", "sector", "sub"].includes(level) ? level : store.get("secLevel", "industry");
  store.set("secLevel", level);
  if (group) return sectorGroupPage(alive, mkt, level, group);
  document.title = "Sectors · Trading";
  const prefs = { sort: "rs", dir: -1, rel: false, quad: "all", sector: "", rrgN: 8, ...store.get("secPrefs", {}) };
  if (![6, 8, 12, 20].includes(prefs.rrgN)) prefs.rrgN = 8;
  const save = () => store.set("secPrefs", prefs);
  $view.innerHTML = `<div class="page-head"><h1>Sectors</h1>
      ${marketSeg(mkt)}
      ${segmented([["sector", "Sectors"], ["industry", "Industry groups"], ["sub", "Sub-industries"]], level, "lv")}</div><div id="sec">${LOADING}</div>`;
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
    <div class="sec-sub muted">${prettyDate(d.date)} · ${d.stocks.toLocaleString()} liquid stocks in ${d.groups.length} ${LEVEL_NAME[level]}${level === "sub" ? " (large, mixed industry groups split further — data/sub_industries.csv)" : ""}
      · typical stock ${SEC_H.map((h) => `${h} <b class="${pctCls(mret[h])}">${pct1(mret[h])}</b>`).join(" ")}
      ${bench ? ` · ${esc(bench.label)} 3M <b class="${pctCls(bench["3M"])}">${pct1(bench["3M"])}</b> 12M <b class="${pctCls(bench["12M"])}">${pct1(bench["12M"])}</b>` : ""}
      ${d.updating ? ' <span class="tag watch">updating…</span>' : ""}
      · ${info(["rs", "returns", "relative", "breadth", "rrg", "universe", "caveats"].map((k) => `<p>${esc(d.doc[k])}</p>`).join("") + '<p><a href="#/playbook">Read the sector-analysis playbook →</a></p>', "How to read this page")}</div>
    <div class="sec-top one">
      <section class="sec-card"><div class="sec-card-h"><h3>Rotation</h3><span class="muted small" id="rrg-note"></span><span class="spacer"></span>
        ${level !== "sector" ? `<label class="small muted">show <select id="rrgn">${[6, 8, 12, 20].map((n) => `<option ${n === prefs.rrgN ? "selected" : ""}>${n}</option>`).join("")}</select></label>` : ""}</div>
        <div id="rrg"></div></section>
    </div>
    <div class="sec-filters">
      <label class="filter"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input id="sf" placeholder="Filter groups" spellcheck="false"></label>
      ${level !== "sector" ? `<select id="ssec"><option value="">All sectors</option>${sectorsList.map((x) => `<option ${x === prefs.sector ? "selected" : ""}>${esc(x)}</option>`).join("")}</select>` : ""}
      <div class="chips" id="squad">${["all", ...QUADS].map((q) => `<button class="chip ${q === prefs.quad ? "on" : ""}" data-q="${q}">${q === "all" ? "All" : q}<span>${q === "all" ? d.groups.length : d.groups.filter((g) => g.quadrant === q).length}</span></button>`).join("")}</div>
      <span class="spacer"></span>
      <label class="check"><input type="checkbox" id="srel" ${prefs.rel ? "checked" : ""}> Returns vs the typical stock</label>
    </div>
    <div id="stbl"></div>`;
  let text = "", hot = null, pinned = null;
  const shown = () => {
    let gs = d.groups.filter((g) => (prefs.quad === "all" || g.quadrant === prefs.quad) && (!prefs.sector || level === "sector" || g.sector === prefs.sector)
      && (!text || g.group.toLowerCase().includes(text) || g.sector.toLowerCase().includes(text) || g.leaders.some((l) => l.symbol.toLowerCase().includes(text))));
    const v = (g) => prefs.sort === "rs" ? g.rs : prefs.sort === "drs" ? (g.rs ?? 0) - (g.rs_prev ?? g.rs ?? 0) : prefs.sort === "group" ? g.group
      : prefs.sort === "n" ? g.n : prefs.sort === "above50" ? g.above50 : prefs.sort === "above200" ? g.above200 : prefs.sort === "hl" ? g.highs - g.lows
      : (prefs.rel ? g.rel : g.ew)[prefs.sort];
    return gs.sort((a, b) => { const x = v(a), y = v(b); if (x == null) return 1; if (y == null) return -1; return (typeof x === "string" ? x.localeCompare(y) : x - y) * prefs.dir; });
  };
  const drawRrg = () => {
    const gs = shown(), n = level === "sector" ? gs.length : Math.min(prefs.rrgN, gs.length);
    const el = $view.querySelector("#rrg");
    el.innerHTML = rrgSvg(gs.slice(0, n), hot, pinned, el.clientWidth || 560);
    $view.querySelector("#rrg-note").textContent = (level === "sector" ? "weekly, last 8 weeks" : `top ${n} rows of the table · weekly, last 8 weeks`)
      + (pinned ? ` · pinned: ${groupParts(pinned)[0]} (click again to unpin)` : " · click a trail to pin it, double-click to open");
    $view.querySelectorAll(".rrg-g").forEach((g) => {
      g.onclick = () => { pinned = pinned === g.dataset.g ? null : g.dataset.g; drawRrg(); };
      g.ondblclick = () => go(secHref(mkt, level, g.dataset.g));
    });
  };
  const bar = (v) => v == null ? "" : `<span class="pbar"><i style="width:${(v * 100).toFixed(0)}%" class="${v >= 0.6 ? "hi" : v >= 0.4 ? "mid" : "lo"}"></i></span><span class="pnum">${(v * 100).toFixed(0)}%</span>`;
  const drawTable = () => {
    const gs = shown();
    const th = (k, t, cls = "num", title = "") => `<th class="${cls} ${prefs.sort === k ? "on" : ""}" data-k="${k}" title="${esc(title)}">${t}${prefs.sort === k ? (prefs.dir > 0 ? " ↑" : " ↓") : ""}</th>`;
    $view.querySelector("#stbl").innerHTML = `<div class="sect-wrap"><table class="sect"><thead><tr>
        ${th("rs", "RS", "num", "RS rating 1–99 across groups")}${th("drs", "Δ 1M", "num", "Change in RS rating over the last month")}
        ${th("group", { industry: "Industry group", sector: "Sector", sub: "Sub-industry" }[level], "")}${th("n", "Stocks")}
        ${SEC_H.map((h) => th(h, h, "num", prefs.rel ? "Equal-weight return minus the typical stock's" : "Equal-weight return")).join("")}
        ${th("above50", "> 50D", "", "% of members above their 50-day average")}${th("above200", "> 200D", "", "% of members above their 200-day average")}
        ${th("hl", "Highs / lows", "num", "Members at a new 52-week closing high / low")}<th>Rotation</th><th>RS line 6M</th><th>Leaders</th></tr></thead>
      <tbody>${gs.map((g) => {
        const dr = g.rs != null && g.rs_prev != null ? g.rs - g.rs_prev : null, r = prefs.rel ? g.rel : g.ew;
        return `<tr data-g="${esc(g.group)}"><td class="num">${rsBadge(g.rs)}</td>
          <td class="num ${dr == null ? "" : dr >= 10 ? "pos" : dr <= -10 ? "neg" : "muted"}">${dr == null ? "" : (dr > 0 ? "▲" : dr < 0 ? "▼" : "") + Math.abs(dr)}</td>
          <td class="gname"><b>${esc(groupParts(g.group)[0])}</b>${level === "industry" ? `<span class="muted sec-of">${esc(g.sector)}</span>` : level === "sub" ? `<span class="muted sec-of">${esc(g.industry)} · ${esc(g.sector)}</span>` : ""}</td>
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
  // the graph is laid out in pixels, so redraw it when the card changes width
  let rrgW = 0;
  const ro = new ResizeObserver(([e]) => { if (!alive()) return ro.disconnect(); const w = Math.round(e.contentRect.width); if (w && Math.abs(w - rrgW) > 4) { rrgW = w; drawRrg(); } });
  ro.observe($view.querySelector("#rrg"));
  redraw();
}

async function sectorGroupPage(alive, mkt, level, group) {
  document.title = `${groupParts(group)[0]} · Sectors · Trading`;
  $view.innerHTML = LOADING;
  const d = await api(`/api/sectors/group?market=${mkt}&level=${level}&group=${encodeURIComponent(group)}`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  if (d.error) { $view.innerHTML = `<div class="empty"><b>${esc(group)}</b><div class="muted">${esc(d.error)}</div><a href="${secHref(mkt, level)}">Back to sectors</a></div>`; return; }
  const g = d.group, dr = g.rs != null && g.rs_prev != null ? g.rs - g.rs_prev : null;
  const ret = (o, h) => `<td class="num ${pctCls(o[h])}">${pct1(o[h])}</td>`;
  $view.innerHTML = backLink(secHref(mkt, level), "Sectors") + `<div class="page-head">
      <h1>${esc(groupParts(g.group)[0])}</h1>
      ${level === "industry" ? `<a class="muted" href="${secHref(mkt, "sector", g.sector)}">${esc(g.sector)}</a>` : ""}
      ${level === "sub" ? `<a class="muted" href="${secHref(mkt, "sector", g.sector)}">${esc(g.sector)}</a><span class="muted">›</span><a class="muted" href="${secHref(mkt, "industry", g.industry)}">${esc(g.industry)}</a>` : ""}
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
    ${d.children.length ? `<section class="sec-card"><h3>${d.child_level === "sub" ? "Sub-industries" : "Industry groups"} in ${esc(groupParts(g.group)[0])}</h3><table class="sect mini"><thead><tr><th class="num">RS</th><th>${d.child_level === "sub" ? "Sub-industry" : "Industry"}</th><th class="num">Stocks</th>${SEC_H.map((h) => `<th class="num">${h}</th>`).join("")}<th>Rotation</th></tr></thead>
      <tbody>${d.children.map((x) => `<tr data-g="${esc(x.group)}"><td class="num">${rsBadge(x.rs)}</td><td><b>${esc(groupParts(x.group)[0])}</b></td><td class="num muted">${x.n}</td>${SEC_H.map((h) => ret(x.ew, h)).join("")}
        <td>${x.quadrant ? `<span class="qtag ${QUAD_CLS[x.quadrant]}">${x.quadrant}</span>` : ""}</td></tr>`).join("")}</tbody></table></section>` : ""}
    <section class="sec-card"><div class="sec-card-h"><h3>Members, strongest first</h3><span class="muted small">ranked by the RS composite across all ${d.members.length ? "" : ""}stocks · click a row for its chart</span></div><div id="gmem"></div></section>`;
  $view.querySelectorAll(".sect.mini tr[data-g]").forEach((tr) => tr.onclick = () => go(secHref(mkt, d.child_level, tr.dataset.g)));

  // chart: group vs market (rebased) and the RS line
  const el_ = $view.querySelector("#gchart");
  const chart = LC.createChart(el_, { autoSize: true, ...chartTheme(), handleScroll: false, handleScale: false, crosshair: { mode: LC.CrosshairMode.Normal } });
  const s0 = g.series[0];
  chart.addSeries(LC.LineSeries, { color: cssVar("--series"), lineWidth: 2, priceLineVisible: false, title: g.group.slice(0, 24) })
    .setData(g.series.map((p) => ({ time: p.time, value: (100 * p.group) / s0.group })));
  chart.addSeries(LC.LineSeries, { color: cssVar("--muted"), lineWidth: 1.5, priceLineVisible: false, title: "Typical stock" })
    .setData(g.series.map((p) => ({ time: p.time, value: (100 * p.market) / s0.market })));
  chart.addSeries(LC.LineSeries, { color: "#ff9800", lineWidth: 1.5, priceLineVisible: false, title: "RS line" }, 1)
    .setData(g.series.map((p) => ({ time: p.time, value: (100 * p.group / p.market) / (s0.group / s0.market) })));
  chart.panes()[1]?.setHeight(110);
  chart.timeScale().fitContent();
  { const prev = cleanup; cleanup = () => { chart.remove(); prev(); }; }

  // members
  const extra = level === "sector" ? "industry" : level === "industry" && d.members.some((m) => m.sub) ? "sub-industry" : null;
  const cols = ["rank", "symbol", "name", ...(extra ? [extra] : []), "rs", "1M %", "3M %", "6M %", "12M %", "off 52w high", "> 50D", "> 200D", "quality", "last"];
  const p100 = (v) => (v == null ? null : +(v * 100).toFixed(1));
  const rows = d.members.map((m, i) => [i + 1, m.symbol, m.name || "", ...(extra ? [extra === "industry" ? m.industry : m.sub || ""] : []), m.rs,
    p100(m["1M"]), p100(m["3M"]), p100(m["6M"]), p100(m["12M"]), p100(m.from_high), m.above50, m.above200, m.quality != null ? Math.round(m.quality) : null, m.last]);
  dataTable($view.querySelector("#gmem"), cols, rows, {
    name: "sector_members", sort: ["rank", 1],
    rowClick: (row, visible) => openChartFromList(mkt, row[1], visible.map((r) => r[1]), `${groupParts(g.group)[0]} · members`, location.hash),
  });

  $view.querySelector("#towl").onclick = async () => {
    const name = await askText("Add the top 10 members to a watchlist", `${groupParts(g.group)[0]} (${MKT_BADGE[mkt]})`, "Watchlist name");
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
  mkt = pageMarket(mkt);
  document.title = "Breadth · Trading";
  $view.innerHTML = LOADING;
  const b = await api(`/api/breadth?market=${mkt}`);
  if (!alive()) return;
  const head = `<div class="page-head"><h1>Market breadth</h1>${marketSeg(mkt)}
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

  $view.innerHTML = head + `<div class="bsub">Today · ${idxLine} · ${info("<p>Each reading is ranked against every trading day since 2015 and compared with a week, a month and three months ago.</p><p>Slow changes matter most: markets rarely turn in a day.</p>", "How to read this page")}</div>
    <div class="mstrip" id="mstrip"></div>
    <div class="bcards">${b.cards.map(card).join("")}</div>
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
  const mk = (id) => { const c = LC.createChart($view.querySelector(id), { autoSize: true, ...chartTheme(), handleScroll: false, handleScale: false,
    crosshair: { mode: LC.CrosshairMode.Normal }, rightPriceScale: { borderColor: cssVar("--line-2") }, leftPriceScale: { visible: false, borderColor: cssVar("--line-2") } }); charts.push(c); return c; };
  const k0 = b.index_keys[0], k1 = b.index_keys[b.index_keys.length - 1];
  const ci = mk("#bc-idx");
  ci.addSeries(LC.LineSeries, { color: cssVar("--series"), lineWidth: 2, priceLineVisible: false, title: b.indexes[k0].label }).setData(b.charts[k0]);
  if (k1 !== k0) { ci.applyOptions({ leftPriceScale: { visible: true } }); ci.addSeries(LC.LineSeries, { color: "#ff9800", lineWidth: 1, priceLineVisible: false, priceScaleId: "left", title: b.indexes[k1].label }).setData(b.charts[k1]); }
  const ch = mk("#bc-hl");
  ch.addSeries(LC.HistogramSeries, { priceLineVisible: false, lastValueVisible: false }).setData(b.charts.hl.map((p) => ({ ...p, color: p.value >= 0 ? "rgba(38,166,154,.45)" : "rgba(239,83,80,.45)" })));
  ch.addSeries(LC.LineSeries, { color: cssVar("--strong"), lineWidth: 1.5, priceLineVisible: false, title: "10d" }).setData(b.charts.hl10);
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
  macroStrip($view.querySelector("#mstrip"), mkt);   // its own request: the page never waits on it
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
  mkt = pageMarket(mkt, ["all"]);
  document.title = "Quality · Trading";
  $view.innerHTML = LOADING;
  const [rows, crit] = await Promise.all([api(`/api/quality${mkt === "all" ? "" : `?market=${mkt}`}`), api("/api/quality/criteria")]);
  if (!alive()) return;
  let view = store.get("qView", "tracked");
  if (view === "tracked" && !rows.some((r) => r.tracked)) view = "all";
  // Quality is one of the screens: the same way back to the others, and to building your own
  $view.innerHTML = backLink("#/screens", "All screens", `<span class="muted">·</span><a href="#/screens/new/${mkt === "all" ? pageMarket() : mkt}">+ New screen</a>`) + `
    <div class="page-head"><h1>Quality companies</h1>${marketSeg(mkt, [["all", "US + India"]])}
      <span class="spacer"></span>
      <form class="wl-add" autocomplete="off">
        ${mkt === "all" ? `<select id="qm" title="Market">${MKTS.map((m) => `<option value="${m.key}">${esc(m.name)}</option>`).join("")}</select>` : ""}
        <div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input id="qs" placeholder="Track a company" spellcheck="false"><ul hidden></ul></div>
        <input id="qt" type="number" step="any" placeholder="Buy below (optional)" title="Your own buy-below price: the row is flagged AT YOUR PRICE once the close reaches it">
        <input id="qn" placeholder="Note (optional)"><button class="primary" type="submit">Track</button>
      </form></div>
    <div class="chips" id="qchips"></div>
    <div class="qgroup-bar"><span class="muted small">Group by</span>${segmented([["none", "None"], ["sector", "Sector"], ["industry", "Industry group"], ["sub", "Sub-sector"]], store.get("qGroup", "none"), "qgb")}
      <span class="muted small">Quality at least</span>${segmented([["0", "Any"], ["50", "50"], ["60", "60"], ["70", "70"], ["80", "80"]], String(store.get("qMinQ", 0)), "qmq")}
      <span id="qcrumb"></span></div>
    <div id="qpending"></div><div id="qt-host"></div>
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
  // grouping for long-term research: sector -> industry group -> sub-sector (the sub-industry where the
  // group is split into businesses, else the industry group itself)
  const subSector = (r) => (r.sub_industry ? `${r.industry} › ${r.sub_industry}` : r.industry || "Unclassified");
  const GROUP = { sector: (r) => r.sector || "Unclassified", industry: (r) => r.industry || "Unclassified", sub: subSector };
  let group = store.get("qGroup", "none"), minQ = +store.get("qMinQ", 0), picked = store.get("qPicked", null);
  const median = (xs) => { const v = xs.filter((x) => x != null).sort((a, b) => a - b); return v.length ? v[Math.floor((v.length - 1) / 2)] : null; };
  const groupTable = (host, rowsIn) => {
    const by = new Map();
    for (const r of rowsIn) { const k = GROUP[group](r); if (!by.has(k)) by.set(k, []); by.get(k).push(r); }
    const cols = ["group", "sector", "companies", "high quality", "best", "median", "buy zone", "accumulate", "median mkt cap $B", "top companies"];
    const data = [...by.entries()].map(([k, xs]) => {
      const top = [...xs].sort((a, b) => (b.quality ?? -1) - (a.quality ?? -1)).slice(0, 3).map((x) => x.symbol.replace(/\.NS$/, ""));
      return [k, group === "sector" ? "" : (xs[0].sector || ""), xs.length, xs.filter(high).length,
        Math.max(...xs.map((x) => x.quality ?? -1)), median(xs.map((x) => x.quality)),
        xs.filter((x) => x.zone === "BUY ZONE").length, xs.filter((x) => x.zone === "ACCUMULATE").length,
        median(xs.map((x) => x.market_cap_usd)), top.join(" · ")];
    });
    dataTable(host, cols, data, {
      name: `quality_groups_${group}`, sort: ["high quality", -1], noStack: true, hidden: group === "sector" ? ["sector"] : [],
      format: { best: (v) => (v < 0 ? "" : String(v)), median: (v) => (v == null ? "" : String(Math.round(v))),
        "median mkt cap $B": (v) => (v == null ? "" : v >= 10 ? v.toFixed(0) : v.toFixed(1)) },
      rowClick: (row) => { picked = row[0]; store.set("qPicked", picked); draw(); }, rowHint: "Click a group to see its companies",
    });
  };
  const draw = () => {
    $view.querySelector("#qchips").innerHTML = views.map(([k, t, xs]) => `<button class="chip ${k === view ? "on" : ""} ${k === "buy" || k === "yourprice" ? "trade" : k === "accumulate" ? "watch" : ""}" data-v="${k}">${t}<span>${xs.length}</span></button>`).join("");
    const inView = views.find((v) => v[0] === view)[2];
    const passQ = (r) => !minQ || (r.quality != null && r.quality >= minQ);
    const grouped = group !== "none";
    if (grouped && picked && !inView.some((r) => GROUP[group](r) === picked)) picked = null;
    const shown = inView.filter((r) => passQ(r) && (!grouped || !picked || GROUP[group](r) === picked));
    const crumb = $view.querySelector("#qcrumb");
    crumb.innerHTML = grouped && picked ? `<span class="qpick">${esc(picked)} <button class="ghost sm" title="Back to all groups">✕</button></span>` : "";
    if (grouped && picked) crumb.querySelector("button").onclick = () => { picked = null; store.set("qPicked", null); draw(); };
    const pending = shown.filter((r) => r.tracked && r.quality == null);
    $view.querySelector("#qpending").innerHTML = pending.length ? `<div class="qpend"><b>${pending.length} tracked compan${pending.length > 1 ? "ies have" : "y has"} no fundamentals yet</b> —
      price signals are shown; to score ${pending.length > 1 ? "them" : "it"}, run from <code>scripts/</code>: <code>${esc(QCMD())}</code>
      <button class="ghost copy" data-c="PYTHONPATH=. ${esc(QCMD())}">Copy</button></div>` : "";
    const host = $view.querySelector("#qt-host");
    if (grouped && !picked && shown.length) { groupTable(host, shown); return; }
    if (!shown.length) {
      host.innerHTML = `<div class="empty"><b>${view === "tracked" ? "You're not tracking any companies yet" : "No companies in this view"}</b>
        <div class="muted">${view === "tracked" ? "Add one with “Track a company” above, or ★ any row under High quality / All scored." : rows.some((r) => r.quality != null) ? "Try another view." : "Run the fundamentals script to score companies (see “How the signals work”)."}</div></div>`;
      return;
    }
    const cols = ["symbol", "name", "market", "sector", "industry", "sub-sector", "mkt cap $B", "quality", "f", "roic / roe", "rev growth", "eps growth", "op margin", "fcf conv", "net debt/ebitda",
      "last", "p/e", "p/e vs own", "fcf yield", "peg", "off 52w high", "vs 200d", "rsi", "value", "zone", "buy below", "signals", "note"];
    const data = shown.map((r) => [r.symbol, r.name || "", r.market.toUpperCase(), r.sector || "", r.industry || "",
      r.sub_industry || "", r.market_cap_usd ?? null, r.quality, r.f_score ?? null,
      r.financial ? r.roe_avg : r.roic_avg, r.rev_cagr, r.eps_cagr, r.financial ? null : r.op_margin, r.financial ? null : r.fcf_conversion,
      r.net_cash ? -0.0001 : r.net_debt_ebitda, r.close, r.pe, r.pe_vs_own, r.fcf_yield, r.peg, r.drawdown, r.vs_200dma, r.rsi,
      r.value || (r.quality == null ? "pending" : ""), r.at_your_price ? "AT YOUR PRICE" : r.zone || "", r.target,
      [...(r.timing || []), ...(r.flags || [])].join(" · "), r.note || ""]);
    const P = (c) => [c, pct];
    dataTable(host, cols, data, {
      name: `quality_${mkt}_${view}`, sort: ["quality", -1], hidden: ["industry"],
      format: Object.fromEntries([...["roic / roe", "rev growth", "eps growth", "op margin", "fcf conv", "p/e vs own", "fcf yield", "off 52w high", "vs 200d"].map(P),
        ["net debt/ebitda", (v) => (v === -0.0001 ? "net cash" : num(v))], ["p/e", num], ["peg", num], ["rsi", (v) => (v == null ? "" : v.toFixed(0))],
        ["quality", (v) => (v == null ? "pending" : String(v))],
        ["mkt cap $B", (v) => (v == null ? "" : v >= 10 ? v.toFixed(0) : v.toFixed(1))]]),
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
  const onSeg = (sel, fn) => $view.querySelector(sel).onclick = (e) => {
    const b = e.target.closest("button[data-v]"); if (!b) return;
    $view.querySelectorAll(`${sel} button`).forEach((x) => x.classList.toggle("on", x === b)); fn(b.dataset.v); draw();
  };
  onSeg(".qgb", (v) => { group = v; picked = null; store.set("qGroup", v); store.set("qPicked", null); });
  onSeg(".qmq", (v) => { minQ = +v; store.set("qMinQ", minQ); });
  $view.querySelector("#qpending").onclick = (e) => { const b = e.target.closest(".copy"); if (b) navigator.clipboard.writeText(b.dataset.c).then(() => toast("Command copied", "ok"), () => {}); };
  draw();
}

// ------------------------------------------------------------ fundamentals: one company's financials (screener.in style)

const sepaClass = (v) => (v === "LEADER" ? "trade" : v === "ACCEPTABLE" ? "watch" : v === "WEAK" ? "avoid" : "");
const sepaPct = (v, d = 0) => (v == null ? "" : `${v > 0 ? "+" : ""}${(v * 100).toFixed(d)}%`);
const FUND_SOURCE = { sec_edgar: "SEC filings", nse: "NSE filings", yfinance: "Yahoo (fallback)" };
const bareSymbol = (x) => { const m = MKTS.find((k) => k.suffix && String(x).endsWith(k.suffix)); return m ? String(x).slice(0, -m.suffix.length) : String(x); };
const companyHref = (m, s) => `#/company/${m}/${encodeURIComponent(s)}`;

/** one strategy view's tests for one company */
function viewTestsHtml(res, vc) {
  const lbl = Object.fromEntries(vc.tests.map((t) => [t.key, t]));
  return `<table class="dtab sepa-tests"><tbody>${Object.entries(res.tests || {}).map(([k, t]) => `<tr>
      <td><span class="tag ${t.status === "pass" ? "trade" : t.status === "fail" ? "avoid" : ""}">${t.status === "na" ? "n/a" : t.status}</span></td>
      <td><b>${k}</b> ${esc(lbl[k]?.label || "")}<div class="muted small">${esc(lbl[k]?.text || "")}</div></td>
      <td class="num">${typeof t.value !== "number" ? "" : k === "F2" ? String(t.value)
        : k === "F4" || k === "F8" ? `${t.value > 0 ? "+" : ""}${(t.value * 100).toFixed(1)} pt` : esc(sepaPct(t.value, 1))}
        ${t.detail ? `<div class="muted small">${esc(t.detail)}</div>` : ""}</td></tr>`).join("")}</tbody></table>`;
}

/** News & events for one stock (/api/news; marketdata/news.py fills it): what is coming (earnings,
 *  ex-dates, results meetings), the headlines and exchange announcements, the key events behind them
 *  (filings, dividends, splits) and analyst rating changes. The chart's side panel stacks it; `page`
 *  (the company page) sets headlines beside the events and leaves the title to the page's own heading. */
function newsHtml(d, { page = false } = {}) {
  const EV_LABEL = { earnings: "Earnings", results: "Results", dividend: "Dividend", split: "Split", bonus: "Bonus",
    board_meeting: "Board meeting", filing: "Filing", rating: "Rating", action: "Corporate action" };
  const title = page ? "" : "<h3>News & events</h3>";
  if (!d || d.error) return `<section>${title}<div class="muted small">${esc(d?.error || "Loading…")}</div></section>`;
  const today = new Date().toISOString().slice(0, 10);
  const link = (u, t) => (u ? `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(t)}</a>` : esc(t));
  const ev = (e) => `<div class="nw-ev"><span class="nw-d">${prettyDate(e.date)}</span><span class="tag nw-k ${e.kind}">${EV_LABEL[e.kind] || e.kind}</span>
      <span class="nw-t">${link(e.url, e.title)}${e.kind === "earnings" && e.detail?.eps_estimate != null ? ` <span class="muted">· EPS est. ${(+e.detail.eps_estimate).toFixed(2)}</span>` : ""}</span></div>`;
  const upcoming = d.events.filter((e) => e.date >= today).sort((a, b) => (a.date < b.date ? -1 : 1));
  const past = d.events.filter((e) => e.date < today && e.kind !== "rating").slice(0, page ? 25 : 15);
  const ratings = d.events.filter((e) => e.kind === "rating").slice(0, page ? 10 : 6);
  const items = d.news.slice(0, page ? 40 : 30).map((n) => `<div class="nw-it">${link(n.url, n.title)}
      <div class="muted small">${esc(n.kind === "announcement" ? "NSE announcement" : n.source || "")}${n.published_at ? ` · ${ago(n.published_at)}` : ""}</div></div>`).join("");
  const status = d.pending ? `<span class="spin"></span> Fetching the latest${d.pending === "now" ? "" : ` (queue #${d.pending})`}…`
    : d.fetched_at ? `Updated ${ago(d.fetched_at)}` : "Not fetched yet";
  const top = `<section><div class="wld-nh">${title}${page ? `<span class="muted small" title="${esc(d.note || "")}">${status}</span>` : ""}<span class="spacer"></span>
      ${d.pending ? "" : '<a class="small" href="#" data-nwrefresh title="Fetch the latest now">Refresh</a>'}</div>
      ${page ? "" : `<div class="muted small" title="${esc(d.note || "")}">${status}</div>`}</section>`;
  const up = upcoming.length ? `<section><h3>Upcoming</h3>${upcoming.map(ev).join("")}</section>` : "";
  const heads = `<section><h3>Headlines</h3>${items || `<div class="muted small">${d.pending ? "Coming shortly." : "No headlines in the last month."}</div>`}</section>`;
  const keyEv = past.length ? `<section><h3>Key events</h3>${past.map(ev).join("")}</section>` : "";
  const rat = ratings.length ? `<section><h3>Analyst ratings</h3>${ratings.map(ev).join("")}</section>` : "";
  const src = `<p class="muted small nw-src">Sources: ${esc(d.sources || "")}. Refreshed each morning for watchlists and
      strategy picks, on demand for any other stock.</p>`;
  return page ? `${top}<div class="nw-page"><div>${heads}</div><div>${up}${keyEv}${rat}</div></div>${src}`
    : `${top}${up}${heads}${keyEv}${rat}${src}`;
}

/** Put a stock's news & events into `host` and keep it current: render when it loads, wire Refresh,
 *  and check back every few seconds while a fetch is pending (the server asks for one when nothing
 *  is stored or it is a day old). */
function mountNews(host, market, symbol, alive, { onData, ...opts } = {}) {
  let poll = null;
  const url = (refresh) => `/api/news/${market}/${encodeURIComponent(symbol)}${refresh ? "?refresh=1" : ""}`;
  const show = (d) => {
    if (!alive() || !host.isConnected) { clearInterval(poll); return; }
    host.innerHTML = newsHtml(d, opts);
    if (onData && d && !d.error) onData(d);
    host.querySelector("[data-nwrefresh]")?.addEventListener("click", (e) => { e.preventDefault(); load(true); });
    if (d && d.pending && !poll) {
      let tries = 0;
      poll = setInterval(async () => {
        if (!alive() || !host.isConnected || ++tries > 50) { clearInterval(poll); poll = null; return; }
        const x = await api(url(false)).catch(() => null);
        if (x && !x.pending) { clearInterval(poll); poll = null; show(x); }
      }, 6000);
    }
  };
  const load = (refresh) => api(url(refresh)).catch((e) => ({ error: e.message })).then(show);
  load(false);
  const prev = cleanup; cleanup = () => { clearInterval(poll); prev(); };
}

/** Chart › News: one stock's headlines and key events, a view beside Chart and Fundamentals. */
async function stockNewsPage(alive, market, symbol) {
  market = pageMarket(market);
  symbol = symbol || store.get("lastSymbol:" + market, market === "us" ? "AAPL" : "RELIANCE.NS");
  store.set("lastMarket", market); store.set("lastSymbol:" + market, symbol);
  document.title = `${bareSymbol(symbol)} news · Trading`;
  $view.innerHTML = `
    <div class="page-head co-head"><h1 id="nwname">${esc(bareSymbol(symbol))}</h1><span class="mkt">${MKT_BADGE[market] || market}</span><span class="muted">${esc(bareSymbol(symbol))}</span>
      <span class="spacer"></span>
      <form class="wl-add" autocomplete="off" id="nwsearch"><div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input placeholder="Search a company" spellcheck="false"><ul hidden></ul></div></form>
      </div>
    <section class="co-sec"><div class="nwpage">${newsHtml(null, { page: true })}</div></section>`;
  const f = $view.querySelector("#nwsearch");
  symbolSearch(f.querySelector("input"), f.querySelector("ul"), market, (s) => go(`#/news/${market}/${encodeURIComponent(s)}`));
  f.onsubmit = (e) => { e.preventDefault(); const v = f.querySelector("input").value.trim().toUpperCase(); if (v) go(`#/news/${market}/${encodeURIComponent(v)}`); };
  mountNews($view.querySelector(".nwpage"), market, symbol, alive, { page: true,
    onData: (d) => { const h = $view.querySelector("#nwname"); if (h && d.name) h.textContent = d.name; } });   // the name arrives with the news
}

async function companyPage(alive, market, symbol) {
  market = pageMarket(market);
  symbol = symbol || store.get("lastSymbol:" + market, market === "us" ? "AAPL" : "RELIANCE.NS");
  store.set("lastMarket", market); store.set("lastSymbol:" + market, symbol);
  document.title = `${bareSymbol(symbol)} fundamentals · Trading`;
  $view.innerHTML = LOADING;
  const d = await api(`/api/company?market=${market}&symbol=${encodeURIComponent(symbol)}`);
  if (!alive()) return;
  const loc = d.currency === "₹" ? "en-IN" : "en-US";       // ₹ figures grouped the Indian way (1,23,456)
  const money = (v) => (v == null ? "" : (v / d.divisor).toLocaleString(loc, { maximumFractionDigits: Math.abs(v / d.divisor) < 10 ? 1 : 0 }));
  const fmtv = (kind, v) => (v == null ? "" : kind === "money" ? money(v) : kind === "pct" ? `${(v * 100).toFixed(0)}%`
    : kind === "per_share" ? v.toLocaleString(loc, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : Math.round(v).toLocaleString(loc));
  // a growth row (year-on-year, from the server): a signed percentage, green up / red down; where the
  // year-ago quarter was a loss the server sends words instead ("turned profit", "loss narrowed / widened")
  const cell = (r, v, i) => {
    if (!String(r.kind).startsWith("growth")) return `<td class="${v < 0 ? "neg" : ""}">${fmtv(r.kind, v)}</td>`;
    const words = r.text?.[i];
    if (words) return `<td class="${words === "turned profit" ? "pos" : words === "loss widened" ? "neg" : "muted"} small">${esc(words)}</td>`;
    if (v == null) return "<td></td>";
    const pct = v * 100, txt = `${pct > 0 ? "+" : pct < 0 ? "−" : ""}${Math.abs(pct) >= 100 ? Math.round(Math.abs(pct)) : Math.abs(pct).toFixed(1)}%`;
    return `<td class="${pct > 0 ? "pos" : pct < 0 ? "neg" : ""}">${txt}</td>`;
  };
  const colLabel = (c) => { const m = String(c).match(/^(\d{4})-(\d{2})/); return m ? `${MONTHS[+m[2] - 1]} ${m[1]}` : c; };
  const BOLD = new Set(["sales", "operating_profit", "net_profit", "total_liabilities", "total_assets", "cfo", "fcf", "eps"]);
  const table = (t, note = "") => !t || !t.rows?.length ? `<div class="muted small">Not in the filings stored for this company.</div>`
    : `<div class="fin-wrap"><table class="fin"><thead><tr><th></th>${t.columns.map((c) => `<th>${esc(colLabel(c))}</th>`).join("")}</tr></thead>
       <tbody>${t.rows.map((r) => `<tr class="${BOLD.has(r.key) ? "strong" : ""} ${r.kind === "pct" ? "pctrow" : ""} ${r.kind === "growth" ? "growthrow yoy" : r.kind === "growth_qoq" ? "growthrow qoq" : ""}"><th>${esc(r.label)}</th>${r.values.map((v, i) => cell(r, v, i)).join("")}</tr>`).join("")}</tbody></table></div>
       ${note ? `<div class="muted small fin-note">${note}</div>` : ""}`;
  // which growth rows show: both YoY and QoQ (default), one of them (QoQ only in the quarterly table; the
  // annual one is always YoY) or none
  let growthMode = store.get("finGrowth", "both");
  const st = d.status || {};
  const unitNote = `Figures in ${esc(unitWords(d.unit))} · ${esc(FUND_SOURCE[st.source] || st.source || "")}${st.basis && st.basis !== "as reported" ? ` · ${esc(st.basis)}` : ""}`;
  const fetchBtn = d.fetch_pending ? `<button class="btn" disabled>Fetch queued (#${d.fetch_pending})…</button>`
    : `<button class="btn" id="cfetch" title="Fetch this company's filings now (a queue item, ahead of long jobs)">${st.status ? "Refresh from filings" : "Fetch now"}</button>`;
  // no Chart / News buttons or back link: the Chart · Fundamentals · News tabs above open this stock
  const head = `
    <div class="page-head co-head"><h1>${esc(d.name || bareSymbol(symbol))}</h1><span class="mkt">${MKT_BADGE[market] || market}</span><span class="muted">${esc(bareSymbol(symbol))}</span>
      <span class="spacer"></span>
      <form class="wl-add" autocomplete="off" id="cosearch"><div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input placeholder="Search a company" spellcheck="false"><ul hidden></ul></div></form>
      ${fetchBtn}</div>
    <div class="muted small co-sub">${[d.sector, d.industry].filter(Boolean).map(esc).join(" › ")}${d.profile?.website ? ` · <a href="${esc(d.profile.website)}" target="_blank" rel="noopener">${esc(d.profile.website.replace(/^https?:\/\/(www\.)?/, ""))}</a>` : ""}
      ${st.fetched_at ? ` · fetched ${esc(prettyDate(st.fetched_at))}` : ""}${d.latest?.end ? ` · latest results ${esc(colLabel(d.latest.end))}${d.latest.filed ? ` (filed ${esc(prettyDate(d.latest.filed))})` : ""}` : ""}${d.latest?.stale ? ` · <b>stale</b>` : ""}</div>`;
  if (!d.quarters) {
    $view.innerHTML = head + `<div class="empty"><b>${st.status === "none" ? "Nothing filed for this symbol" : st.status === "error" ? "The last fetch failed" : "Not fetched yet"}</b>
      <div class="muted">${st.status === "none" ? "No results filings at the source (a fund or ETF?)." : st.error ? esc(st.error) : "The weekly job fetches the most liquid stocks and every Stage-2 stock; this one has not been fetched yet. Fetch it now — it takes a few seconds to a minute once the queue reaches it."}</div></div>`;
    wire();
    return;
  }
  const r = d.ratios_top || {};
  const pc = (v, dp = 1) => (v == null ? "—" : `${(v * 100).toFixed(dp)}%`);
  const cur = (v) => (v == null ? "—" : `${d.currency} ${v.toLocaleString(loc, { maximumFractionDigits: 2 })}`);
  // statements in another currency than the price (a foreign company's US listing, from Yahoo): label them in
  // that currency, and leave the price-based ratios out — they would need exchange rates
  const sc = d.statement_currency;
  const stmtCur = (v) => (v == null ? "—" : sc ? `${sc} ${v.toLocaleString(loc, { maximumFractionDigits: 2 })}` : cur(v));
  const stmtMoney = (v) => (v == null ? "—" : !sc ? moneyShort(v, market)
    : `${v < 0 ? "−" : ""}${sc} ${Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(Math.abs(v))}`);
  const ratio = [["Market cap", r.market_cap == null ? "—" : moneyShort(r.market_cap, market)],
    ["Current price", cur(r.price)], ["High / Low", r.high_52w ? `${cur(r.high_52w)} / ${r.low_52w?.toLocaleString(loc, { maximumFractionDigits: 2 })}` : "—"],
    ["Stock P/E", r.pe == null ? "—" : r.pe.toFixed(1)], ["Book value", cur(r.book_value)], ["Dividend yield", pc(r.dividend_yield, 2)],
    ["ROCE", pc(r.roce)], ["ROE", pc(r.roe)], ...(r.face_value ? [["Face value", cur(r.face_value)]] : []),
    ...(r.debt_to_equity != null ? [["Debt to equity", r.debt_to_equity.toFixed(2)]] : []),
    ["Sales (TTM)", stmtMoney(r.sales_ttm)], ["Profit (TTM)", stmtMoney(r.profit_ttm)],
    ["EPS (TTM)", stmtCur(r.eps_ttm)], ["RS rank", r.rs_rank == null ? "—" : Math.round(r.rs_rank)]];
  const g = d.growth || {};
  const gbox = (title, rows) => `<div class="cg-box"><b>${title}</b><table>${(rows || []).map(([k, v]) => `<tr><td>${esc(k)}:</td><td class="${v < 0 ? "neg" : ""}">${v == null ? "—" : `${(v * 100).toFixed(0)}%`}</td></tr>`).join("")}</table></div>`;
  const shp = d.shareholding || [];
  const shpRows = [["promoters", "Promoters"], ["fii", "FIIs"], ["dii", "DIIs"], ["government", "Government"], ["public", "Public"]]
    .filter(([k]) => shp.some((x) => x[k] != null));
  const shpHtml = shp.length ? `<div class="fin-wrap"><table class="fin"><thead><tr><th></th>${shp.map((x) => `<th>${esc(colLabel(x.period_end))}</th>`).join("")}</tr></thead><tbody>
      ${shpRows.map(([k, l]) => `<tr><th>${l}</th>${shp.map((x) => `<td>${x[k] == null ? "" : `${(x[k] * 100).toFixed(2)}%`}</td>`).join("")}</tr>`).join("")}
      ${shp.some((x) => x.shareholders) ? `<tr><th>No. of shareholders</th>${shp.map((x) => `<td>${x.shareholders ? x.shareholders.toLocaleString(loc) : ""}</td>`).join("")}</tr>` : ""}</tbody></table></div>
      <div class="muted small fin-note">From the quarterly shareholding-pattern filings on NSE; FII / DII from the detailed filing (read for the latest quarters).</div>`
    : d.holders && Object.keys(d.holders).length ? `<div class="kv co-holders">${d.holders.heldPercentInstitutions != null ? `<span>Institutions <b>${pc(d.holders.heldPercentInstitutions)}</b></span>` : ""}
        ${d.holders.heldPercentInsiders != null ? `<span>Insiders <b>${pc(d.holders.heldPercentInsiders)}</b></span>` : ""}</div><div class="muted small fin-note">Current only (Yahoo); US filers report no quarterly shareholding pattern.</div>`
    : `<div class="muted small">No shareholding data.</div>`;
  const peers = d.peers || [];
  const peerHtml = peers.length > 1 ? `<div class="fin-wrap"><table class="fin peers"><thead><tr><th>Name</th><th>Price</th><th>P/E</th><th>Mkt cap</th><th>Sales growth (Q)</th><th>EPS growth (Q)</th><th>ROE</th><th>RS</th></tr></thead><tbody>
      ${peers.map((p) => `<tr class="${p.self ? "self" : ""}"><th><a href="${companyHref(market, p.symbol)}">${esc(bareSymbol(p.symbol))}</a></th><td>${p.close?.toLocaleString(loc, { maximumFractionDigits: 2 }) ?? ""}</td>
        <td>${p.pe == null ? "" : p.pe.toFixed(1)}</td><td>${p.market_cap == null ? "" : moneyShort(p.market_cap, market)}</td><td class="${p.sales_g < 0 ? "neg" : ""}">${sepaPct(p.sales_g)}</td>
        <td class="${p.eps_g < 0 ? "neg" : ""}">${sepaPct(p.eps_g)}</td><td>${p.roe == null ? "" : `${(p.roe * 100).toFixed(0)}%`}</td><td>${p.rs_rank == null ? "" : Math.round(p.rs_rank)}</td></tr>`).join("")}</tbody></table></div>
      <div class="muted small fin-note">Peer group: ${esc(String(d.peer_group || "").split(" › ").at(-1))} (Sectors page). P/E and growth only where a company's filings are stored.</div>`
    : `<div class="muted small">No peer group for this stock.</div>`;
  const viewsHtml = (d.views || []).map((v) => {
    const res = v.result;
    return `<section class="co-sec" id="co-view-${esc(v.key)}"><h2>${esc(v.name)} ${res ? `<span class="tag ${sepaClass(res.verdict)}">${esc(res.verdict)}</span>${res.code33 ? ' <span class="tag trade">CODE 33</span>' : ""} <span class="muted small">${res.passed}/${res.scored} tests pass</span>` : ""}
        ${v.strategy ? `<a class="muted small" href="#/strategies/${encodeURIComponent(v.strategy)}">the strategy →</a>` : ""}</h2>
      <p class="muted small">${esc(v.description)} ${esc(v.thesis || "")}</p>
      ${res ? viewTestsHtml(res, v) : '<div class="muted small">Not scored yet.</div>'}
      <details class="qhow"><summary>Verdicts and caveats</summary><ul class="sd-list">${v.verdicts.map((x) => `<li>${esc(x)}</li>`).join("")}${v.caveats.map((x) => `<li class="muted">${esc(x)}</li>`).join("")}</ul></details></section>`;
  }).join("");
  const SECS = [["overview", "Overview"], ["quarters", "Quarters"], ["pl", "Profit & Loss"], ["bs", "Balance Sheet"], ["cf", "Cash Flows"],
    ["ratios", "Ratios"], ["shp", "Shareholding"], ["peers", "Peers"], ...(d.views || []).map((v) => [`view-${v.key}`, v.name])];
  $view.innerHTML = head + `<nav class="co-nav">${SECS.map(([k, t]) => `<a href="#co-${k}" data-sec="co-${k}">${esc(t)}</a>`).join("")}</nav>
    <section class="co-sec" id="co-overview"><div class="co-ratios">${ratio.map(([k, v]) => `<div><span class="muted">${k}</span><b>${v}</b></div>`).join("")}</div>
      ${sc ? `<div class="muted small fin-note">Statements are in ${esc(sc)}; the share price is in ${esc(d.currency_code || d.currency)}. P/E, book value and dividend yield are not shown, because they would need exchange rates — the same rule as the Quality screen.</div>` : ""}
      ${d.profile?.about ? `<details class="co-about"><summary>About</summary><p>${esc(d.profile.about)}</p></details>` : ""}</section>
    <section class="co-sec" id="co-quarters"><h2>Quarterly results <span class="seg growth-seg" title="Growth rows under sales, operating profit, net profit and EPS. YoY: against the same quarter a year earlier (what earnings tests use; no seasonal effect). QoQ: against the quarter before (sooner, but partly the season).">
      <span class="muted small">Growth</span>${[["both", "YoY + QoQ"], ["yoy", "YoY"], ["qoq", "QoQ"], ["off", "Off"]].map(([k, t]) => `<button data-growth="${k}" class="${growthMode === k ? "on" : ""}">${t}</button>`).join("")}</span>
      <span class="muted small">${unitNote}</span></h2>${table(d.quarters,
      `${d.latest?.split_adjusted ? "EPS on today's share basis (adjusted for splits / bonus issues). " : ""}${d.layout === "us" ? "Q4 is the 10-K's year less the first nine months." : ""}`)}</section>
    <section class="co-sec" id="co-pl"><h2>Profit &amp; Loss <span class="muted small">${unitNote}</span></h2>${table(d.profit_loss,
      d.layout === "bank" ? "Banks: revenue is interest earned; financing profit = revenue − interest − expenses (incl. provisions), before other income." : "")}
      <div class="cg">${gbox("Compounded sales growth", g.sales)}${gbox("Compounded profit growth", g.profit)}${gbox("Stock price CAGR", g.price)}${gbox("Return on equity", g.roe)}</div></section>
    <section class="co-sec" id="co-bs"><h2>Balance Sheet <span class="muted small">${unitNote}</span></h2>${table(d.balance_sheet, "Year ends, and the latest half-year / quarter end where filed.")}</section>
    <section class="co-sec" id="co-cf"><h2>Cash Flows <span class="muted small">${unitNote}</span></h2>${table(d.cash_flow, d.layout !== "us" ? "Indian results filings carry the cash flow from about FY2020." : "")}</section>
    <section class="co-sec" id="co-ratios"><h2>Ratios</h2>${table(d.ratios, "Debtor and inventory days on sales; ROCE = (profit before tax + interest) / (equity + borrowings) at the year end.")}</section>
    <section class="co-sec" id="co-shp"><h2>Shareholding pattern</h2>${shpHtml}</section>
    <section class="co-sec" id="co-peers"><h2>Peer comparison</h2>${peerHtml}</section>
    ${viewsHtml}`;
  const applyGrowth = () => {
    $view.dataset.growth = growthMode;
    $view.querySelectorAll(".growth-seg button").forEach((b) => b.classList.toggle("on", b.dataset.growth === growthMode));
  };
  $view.querySelectorAll(".growth-seg button").forEach((b) => b.onclick = () => { growthMode = b.dataset.growth; store.set("finGrowth", growthMode); applyGrowth(); });
  applyGrowth();
  $view.querySelector(".co-nav").onclick = (e) => {
    const a = e.target.closest("[data-sec]"); if (!a) return;
    e.preventDefault(); document.getElementById(a.dataset.sec)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  wire();

  function wire() {
    const f = $view.querySelector("#cosearch");
    if (f) symbolSearch(f.querySelector("input"), f.querySelector("ul"), market, (s) => go(companyHref(market, s)));
    if (f) f.onsubmit = (e) => { e.preventDefault(); const v = f.querySelector("input").value.trim().toUpperCase(); if (v) go(companyHref(market, v)); };
    const b = $view.querySelector("#cfetch");
    if (b) b.onclick = async () => {
      b.disabled = true;
      try {
        const res = await api("/api/company/fetch", jsonReq("POST", { market, symbol }));
        toast(res.duplicate ? `Already queued (#${res.item})` : `Queued #${res.item} — the page refreshes when it is done`, "ok");
        route();
      } catch (err) { b.disabled = false; toast(err.message.replace(/^\d+ /, ""), "err"); }
    };
    if (d.fetch_pending) {   // check back until the queue item is done, then show the new figures
      const t = setInterval(async () => {
        const x = await api(`/api/company?market=${market}&symbol=${encodeURIComponent(symbol)}`).catch(() => null);
        if (x && !x.fetch_pending) { clearInterval(t); if (alive()) route(); }
      }, 10000);
      const prev = cleanup; cleanup = () => { clearInterval(t); prev(); };
    }
  }
}

// ------------------------------------------------------------ strategies

// the strategy prose uses light markdown (**bold**, `code`, *italic*); escape first, then format
const mdInline = (t) => esc(t).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/(^|[^*])\*([^*\s][^*]*?)\*/g, "$1<i>$2</i>");
/** a strategy's status in a few words — the sentence up to its first colon or full stop ("No demonstrated edge") */
const shortStatus = (t) => { const x = String(t || "").split(/[:.;]/)[0].replace(/\s*—.*$/, "").trim(); return x.length > 42 ? x.slice(0, 40) + "…" : x; };
/** The verdict sentence at the head of a `status`: what the strategy's own record concludes,
 *  before the evidence for it. These open with the finding by convention ("MEASURED AND IT
 *  FAILS…", "THE CONTROL, AND IT EARNS ITS KEEP BY HAVING NO EDGE…"), which is the one line
 *  worth showing uncollapsed. Longer than shortStatus' 42-char badge trim, because this has a
 *  line to itself rather than sitting inside a tag. */
const statusVerdict = (t) => {
  const x = String(t || "").trim();
  const m = x.match(/^.{0,200}?[.:](\s|$)/);
  const head = (m ? m[0] : x.slice(0, 200)).replace(/[.:]\s*$/, "").trim();
  return head.length < x.length ? head : x;
};
const statusClass = (t) => (/no demonstrated edge|not validated|no edge|untested|does not beat|did not beat|losing|negative/i.test(t) ? "watch" : /beats|edge confirmed/i.test(t) ? "trade" : "");

// --------------------------------------------------------- screens

const pctf = (v, d = 1) => (v == null ? "" : `${v > 0 ? "+" : ""}${(v * 100).toFixed(d)}%`);
const tabsHtml = (tabs, cur) => `<nav class="ptabs">${tabs.map(([k, t, href]) => `<a href="${href}" class="${k === cur ? "active" : ""}">${t}</a>`).join("")}</nav>`;

const _fields = {};
const screenFields = async (mkt) => (_fields[mkt] = _fields[mkt] || await api(`/api/screen-fields?market=${mkt}`));
const fieldLabel = (fs, k) => (fs.fields.find((f) => f.key === k) || {}).label || k;
function condText(c, fs) {
  const f = fieldLabel(fs, c.field), op = { ">=": "≥", "<=": "≤", "!=": "≠" }[c.op] || c.op;
  if (c.op === "is") return c.value === false ? `not ${f}` : f;
  if (c.op === "in") return `${f} in ${(c.value || []).join(", ")}`;
  if (c.ref) return `${f} ${op} ${fieldLabel(fs, c.ref)}${c.mult != null && +c.mult !== 1 ? ` × ${c.mult}` : ""}`;
  return `${f} ${op} ${c.value}`;
}

/** The condition editor shared by the screen builder and every screen's own page: rows of
 *  field / op / value (or field × factor), with add and remove; mutates `conds` in place and
 *  calls onChange() after every edit. Returns {draw} so a caller can re-render after a reset. */
function condEditor(hostEl, fs, conds, onChange) {
  const groups = [...new Set(fs.fields.map((f) => f.group))];
  const fieldOpts = (sel, kinds) => groups.map((g) => { const fl = fs.fields.filter((f) => f.group === g && (!kinds || kinds.includes(f.kind)));
    return fl.length ? `<optgroup label="${esc(g)}">${fl.map((f) => `<option value="${f.key}" ${f.key === sel ? "selected" : ""}>${esc(f.label)}</option>`).join("")}</optgroup>` : ""; }).join("");
  const kindOf = (k) => (fs.fields.find((f) => f.key === k) || {}).kind;
  const draw = () => {
    hostEl.innerHTML = (conds.map((c, i) => {
      const k = kindOf(c.field);
      const ops = k === "bool" ? [["is", "is"]] : k === "text" ? [["in", "is one of"]] : [[">", ">"], [">=", "≥"], ["<", "<"], ["<=", "≤"], ["=", "="], ["!=", "≠"]];
      const right = k === "bool" ? `<select data-i="${i}" data-k="value"><option value="true" ${c.value !== false ? "selected" : ""}>yes</option><option value="false" ${c.value === false ? "selected" : ""}>no</option></select>`
        : k === "text" ? `<span class="b-vals">${(c.value || []).map((v, j) => `<span class="b-chip">${esc(v)}<button data-i="${i}" data-rm="${j}" title="Remove">×</button></span>`).join("")}
            <select data-i="${i}" data-k="add"><option value="">+ add ${esc(fieldLabel(fs, c.field).toLowerCase())}…</option>${(fs.values?.[c.field] || []).filter((v) => !(c.value || []).includes(v)).map((v) => `<option>${esc(v)}</option>`).join("")}</select></span>`
        : `<select data-i="${i}" data-k="mode"><option value="value" ${!c.ref ? "selected" : ""}>value</option><option value="ref" ${c.ref ? "selected" : ""}>field</option></select>
           ${c.ref ? `<select data-i="${i}" data-k="ref">${fieldOpts(c.ref, ["price", "pct", "num", "money"])}</select><span class="muted">×</span><input class="mult" data-i="${i}" data-k="mult" type="number" step="any" value="${c.mult ?? 1}">`
             : `<input class="num" data-i="${i}" data-k="value" type="number" step="any" value="${c.value ?? ""}">`}`;
      return `<div class="b-row"><select data-i="${i}" data-k="field" title="${esc((fs.fields.find((f) => f.key === c.field) || {}).description || "")}">${fieldOpts(c.field)}</select>
        <select data-i="${i}" data-k="op">${ops.map(([v, t]) => `<option value="${v}" ${v === c.op ? "selected" : ""}>${t}</option>`).join("")}</select>${right}
        <button class="ibtn" data-del="${i}" title="Remove">×</button></div>`;
    }).join("") || '<div class="muted small">No conditions — every stock passes. Add one.</div>')
      + `<button class="ghost" data-addcond>+ Add condition</button>`;
  };
  hostEl.addEventListener("change", (e) => {
    const el_ = e.target, i = +el_.dataset.i, k = el_.dataset.k; if (isNaN(i)) return;
    const c = conds[i];
    if (k === "field") {
      const kd = kindOf(el_.value);
      conds[i] = kd === "bool" ? { field: el_.value, op: "is", value: true } : kd === "text" ? { field: el_.value, op: "in", value: [] } : { field: el_.value, op: ">", value: 0 };
    } else if (k === "op") c.op = el_.value;
    else if (k === "mode") { if (el_.value === "ref") { c.ref = "sma200"; c.mult = 1; delete c.value; } else { delete c.ref; delete c.mult; c.value = 0; } }
    else if (k === "ref") c.ref = el_.value;
    else if (k === "add") { if (el_.value) c.value = [...(c.value || []), el_.value]; }
    else if (k === "mult") c.mult = el_.value === "" ? 1 : +el_.value;
    else if (k === "value") c.value = kindOf(c.field) === "bool" ? el_.value === "true" : kindOf(c.field) === "text" ? el_.value.split(",").map((x) => x.trim()).filter(Boolean) : el_.value === "" ? null : +el_.value;
    draw(); onChange();
  });
  hostEl.addEventListener("click", (e) => {
    if (e.target.closest("[data-addcond]")) { conds.push({ field: "rs_rank", op: ">=", value: 80 }); draw(); onChange(); return; }
    const b = e.target.closest("[data-del]"); if (b) { conds.splice(+b.dataset.del, 1); draw(); onChange(); return; }
    const r = e.target.closest("[data-rm]"); if (r) { conds[+r.dataset.i].value.splice(+r.dataset.rm, 1); draw(); onChange(); }
  });
  draw();
  return { draw };
}

/** Screens: one page — the list of built-in and your screens on the left, the chosen one (or the builder) on the right. */
async function screensPage(alive, key, mkt, tab, date) {
  mkt = pageMarket(mkt);
  if (key && key !== "new") store.set("scrKey", key);
  document.title = "Screens · Trading";
  $view.innerHTML = LOADING;
  const [list, fs] = await Promise.all([api(`/api/screens?market=${mkt}`).catch((e) => ({ error: e.message, screens: [] })), screenFields(mkt)]);
  if (!alive()) return;
  const item = (x) => `<a class="nav-item ${x.key === key ? "active" : ""}" href="#/screens/${x.key}/${mkt}" title="${esc(x.description || "")}">
      <span><b class="sn">${esc(x.name)}</b></span>${x.count != null ? `<span class="n">${x.count}</span>` : ""}</a>`;
  const builtins = list.screens.filter((x) => x.builtin), mine = list.screens.filter((x) => !x.builtin);
  $view.innerHTML = `<div class="rep-layout"><aside class="rep-nav strat-nav">
      <a class="nav-item ${key ? "" : "active"}" href="#/screens"><span><b class="sn">All screens</b></span></a>
      <a class="nav-item new ${key === "new" ? "active" : ""}" href="#/screens/new/${mkt}"><span><b class="sn">+ New screen</b></span></a>
      <div class="nav-h">Built-in</div>${builtins.map(item).join("")}
      <a class="nav-item" href="#/quality" title="Long-term: fundamentals, and when the price is right"><span><b class="sn">Quality</b></span></a>
      <div class="nav-h">My screens</div>${mine.map(item).join("") || `<a class="nav-empty small" href="#/screens/new/${mkt}">None yet — build one from ~50 fields →</a>`}
    </aside><section id="scrmain" class="scr-main">${LOADING}</section></div>`;
  const main = $view.querySelector("#scrmain");
  if (list.error || !list.date) {
    main.innerHTML = `<div class="empty"><b>${list.error ? "Could not load screens" : "No snapshot yet"}</b><div class="muted">${esc(list.error || "Build today's stock snapshot (from scripts/, PYTHONPATH=.):")}</div>${list.command ? `<code>${esc(list.command)}</code>` : ""}</div>`;
    return;
  }
  if (!key) return screensOverview(main, list, mkt, alive, fs);
  if (key === "new" || tab === "edit") {
    let base = { name: "", description: "", conditions: [{ field: "tradable", op: "is", value: true }] };
    const from = store.get("scrDraftFrom", null);
    if (tab === "edit") base = (await api(`/api/screens/${key}?market=${mkt}`)).def;
    else if (from) { const d = (await api(`/api/screens/${from}?market=${mkt}`)).def; base = { name: `${d.name} (my copy)`, description: d.description, conditions: d.conditions }; store.set("scrDraftFrom", null); }
    if (!alive()) return;
    return screenBuilder(main, alive, mkt, fs, base, tab === "edit" ? key : null);
  }
  tab = ["results", "study"].includes(tab) ? tab : "results";   // the old criteria tab is folded into this view; a date in old URLs is ignored (the screen always shows the latest data)
  const r = await api(`/api/screens/${encodeURIComponent(key)}?market=${mkt}`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  if (r.error || r.empty) { main.innerHTML = `<div class="empty"><b>${r.empty ? "No snapshot for this market yet" : "Screen not found"}</b><div class="muted">${esc(r.error || "Build it (from scripts/, PYTHONPATH=.):")}</div>${r.command ? `<code>${esc(r.command)}</code>` : ""}</div>`; return; }
  const d = r.def;
  const href = (t, m = mkt) => `#/screens/${key}/${m}/${t}`;
  const conds = JSON.parse(JSON.stringify(d.conditions || []));
  const orig = JSON.stringify(conds);
  const modified = () => JSON.stringify(conds) !== orig;
  const builtAt = r.built_at ? `${prettyDate(r.built_at.slice(0, 10))} · ${r.built_at.slice(11, 16)}` : null;
  const rulesInfo = info(`${d.thesis ? `<p><b>Why.</b> ${esc(d.thesis)}</p>` : ""}
      ${d.criteria?.length ? `<p><b>In plain words:</b></p>${d.criteria.map((c) => `<p><code>${c.code}</code> ${esc(c.text)}</p>`).join("")}` : ""}
      <p>“Tradable” is the market's floor — minimum price and 20-day traded value, a year of history, a valid ATR — the same floor the strategies use.</p>
      ${d.used_by?.length ? `<p>Strategies drawing from this screen evaluate the same criteria with the same code, then add their own trade rules.</p>` : ""}`);
  main.innerHTML = backLink("#/screens", "All screens") + pageHead(esc(d.name), { extra: marketSeg(mkt),
      context: `<span class="muted small" title="The web app only views offline data: the prices job syncs the bars after each close, and the screens job derives the ~50 fields every screen queries. This page always shows the newest build and asks for a rebuild by itself when the data moves.">
        offline data · fields computed ${builtAt || "—"} · prices through ${prettyDate(r.date)}</span>`,
      actions: (d.builtin ? "" : `<a class="btn" href="#/screens/${key}/${mkt}/edit" title="Rename, re-describe or edit in the full builder">Edit…</a><button class="danger" id="sdel">Delete</button>`)
        + `<a class="btn primary" href="#/screens/new/${mkt}">+ New screen</a>` }) + `
    <p class="sd-lead">${esc(d.description || "")}</p>
    ${staleBanner(r.stale_inputs, mkt, r.updating)}
    <div class="sec-card builder"><div class="sec-card-h"><h3>Rules — every condition must hold</h3>${rulesInfo}
        <span class="spacer"></span><span id="smod" hidden><span class="muted small">edited · results below are live</span>
          <button class="sm" id="sreset">Reset</button><button class="primary sm" id="ssave">${d.builtin ? "Save as my screen…" : "Save changes"}</button></span></div>
      <div id="sconds"></div>
      ${d.builtin ? `<p class="muted small">A built-in screen is generated from the strategy code, so edits preview live here but save as a screen of your own — the original stays as coded.</p>` : ""}
      ${d.used_by?.length ? `<p class="muted small">Used by: ${d.used_by.map((u) => `<a href="#/strategies/${u.key}/rules">${esc(u.name)}</a>`).join(" · ")}</p>` : ""}</div>
    ${tabsHtml([["results", `Results <span class="n" id="scount">${r.count}</span>`, href("results")], ["study", "Study", href("study")]], tab)}
    <div id="stab"></div>`;
  main.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(href(tab, b.dataset.v)));
  wireStale(main, mkt);
  if (r.updating) watchRefresh(alive, mkt, "screens", modified);   // refresh when the rebuild lands — never over an edit in progress
  main.querySelector("#sdel")?.addEventListener("click", async () => {
    if (!confirm(`Delete the screen “${d.name}”?`)) return;
    await api(`/api/screens/${key}`, { method: "DELETE" }); store.set("scrKey", "stage2"); toast(`Deleted “${d.name}”`, "ok"); go(`#/screens/stage2/${mkt}`);
  });
  const host = main.querySelector("#stab");
  const renderTab = (rr) => {
    if (tab === "study") return screenStudy(host, alive, modified() ? null : key, mkt, d, modified() ? conds : undefined);
    screenResults(host, rr, mkt, { ...d, conditions: conds }, fs);
  };
  renderTab(r);
  // the rules ARE the page, not a separate tab — edits re-query the latest snapshot live
  let qt, qseq = 0;
  const requery = () => { clearTimeout(qt); qt = setTimeout(async () => {
    const my = ++qseq;
    if (tab === "study") return renderTab();
    const rr = await api("/api/screens/query", jsonReq("POST", { market: mkt, conditions: conds, sort_by: d.sort_by })).catch((e) => ({ error: e.message }));
    if (!alive() || my !== qseq) return;
    if (rr.error || rr.empty) { host.innerHTML = `<div class="empty"><b>Can't run this yet</b><div class="muted">${esc((rr.error || "").replace(/^\d+ /, ""))}</div></div>`; return; }
    renderTab(rr);
    const n = main.querySelector("#scount"); if (n) n.textContent = rr.count;
  }, 300); };
  const syncMod = () => { main.querySelector("#smod").hidden = !modified(); };
  const ed = condEditor(main.querySelector("#sconds"), fs, conds, () => { syncMod(); requery(); });
  main.querySelector("#sreset").onclick = () => { conds.length = 0; conds.push(...JSON.parse(orig)); ed.draw(); syncMod(); requery(); };
  main.querySelector("#ssave").onclick = async () => {
    try {
      if (d.builtin) {
        const name = await askText("Save as my screen", `${d.name} (mine)`, "Name for your copy");
        if (!name || !name.trim()) return;
        const res = await api("/api/screens", jsonReq("POST", { name: name.trim(), description: d.description || "", conditions: conds }));
        toast(`Saved “${res.name}” — the built-in stays as coded`, "ok"); store.set("scrKey", res.key); go(`#/screens/${res.key}/${mkt}`);
      } else {
        await api("/api/screens", jsonReq("POST", { id: d.id, name: d.name, description: d.description || "", conditions: conds, sort_by: d.sort_by, columns: d.columns }));
        toast("Screen updated", "ok"); route();
      }
    } catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
  };
}

/** "Clusters": the peer groups that several stocks of a list share — a theme, not separate ideas. Each chip
 *  filters the table below to that group. `groups`: peer group per row. */
function clusterChips(groups, min = 2) {
  const c = {}; groups.forEach((g) => { if (g) c[g] = (c[g] || 0) + 1; });
  const top = Object.entries(c).filter(([, n]) => n >= min).sort((a, b) => b[1] - a[1]).slice(0, 10);
  return top.length ? `<div class="clusters"><span class="muted small">Clusters</span>${top.map(([g, n]) => `<button class="chip" data-cluster="${esc(g)}" title="${esc(g)}">${esc(g.split(" › ").at(-1))}<span>${n}</span></button>`).join("")}</div>` : "";
}
function wireClusters(root, tableHost) {
  root.querySelectorAll("[data-cluster]").forEach((b) => b.onclick = () => {
    const inp = tableHost.querySelector(".tbar input"), on = b.classList.toggle("on");
    root.querySelectorAll("[data-cluster]").forEach((x) => { if (x !== b) x.classList.remove("on"); });
    inp.value = on ? b.dataset.cluster : ""; inp.dispatchEvent(new Event("input"));
  });
}

function screenResults(host, r, mkt, d, fs) {
  const used = [...new Set(d.conditions.flatMap((c) => [c.field, c.ref]).filter(Boolean))];
  const base = ["symbol", "name", "peer_group", "peer_rs", "peer_rank", "market_cap_usd", "rs_rank", "close", "pct_below_high", "r1m", "r3m", "industry", "peer_count", "atr_pct", "value20"];
  const extra = used.filter((k) => !base.includes(k) && (fs.fields.find((f) => f.key === k) || {}).kind !== "bool" && k !== "tradable");
  const keys = [...base, ...extra];
  const lbl = (k) => k === "name" ? "name" : k === "value20" ? `value (${mkt === "india" ? "₹ Cr" : "$M"})` : fieldLabel(fs, k);
  const val = (k, v) => v == null ? null : k === "value20" ? +(v / (mkt === "india" ? 1e7 : 1e6)).toFixed(1)
    : typeof v === "number" ? +v.toFixed(Math.abs(v) >= 100 ? 1 : 2) : v;
  host.innerHTML = `${clusterChips(r.rows.map((x) => x.peer_group))}<div class="muted small scr-sum">${r.count} of ${r.universe.toLocaleString()} stocks (${r.tradable.toLocaleString()} tradable) on ${prettyDate(r.date)}
      ${r.prev_date ? ` · ${r.rows.filter((x) => x.new).length} new since ${prettyDate(r.prev_date)}${r.dropped.length ? ` · ${r.dropped.length} dropped out` : ""}` : ""}</div><div id="stbl"></div>`;
  const cols = [...keys.map(lbl), "setups", "new"];
  const rows = r.rows.map((x) => [...keys.map((k) => val(k, x[k])), x.setups.map((u) => `${u.strategy} · ${u.tradeable ? "TRADE" : "watch"}`).join(", "), x.new ? "new" : ""]);
  dataTable(host.querySelector("#stbl"), cols, rows, {
    name: `screen_${d.key || "draft"}_${mkt}`, tags: { new: () => "trade" }, hidden: [lbl("industry"), lbl("peer_count"), lbl("atr_pct"), lbl("value20"), ...(d.builtin ? extra.map(lbl) : [])],
    format: { [lbl("peer_rank")]: (v, row) => (v == null ? "" : `${v} of ${row[keys.indexOf("peer_count")] ?? "?"}`) },
    rowClick: (row, visible) => openChartFromList(mkt, row[0], visible.map((x) => x[0]), `${d.name || "Screen"} · ${prettyDate(r.date)}`, location.hash),
  });
  wireClusters(host, host.querySelector("#stbl"));
}

/** Screens home: every screen as a card — today's count, the change since the previous session, the top
 *  names by RS — your own screens beside the built-in ones, and a card to create a new one. */
function staleBanner(stale, mkt, updating) {
  if (!stale?.length) return "";
  const fields = [...new Set(stale.flatMap((x) => x.fields))];
  const what = stale.map((x) => esc(x.label)).join(", ");
  const pricesStale = stale.some((x) => x.key === "prices");
  return `<div class="scr-stale" id="scrstale"><b>${what} changed after this snapshot was built.</b>
    <span class="sx">${fields.length} field${fields.length === 1 ? "" : "s"} may be out of date: ${fields.map(esc).join(", ")}.${pricesStale ? "" : " Prices and the counts above are unaffected."}</span>
    ${updating ? `<span class="sx refresh-wait"><span class="spin"></span> A rebuild is queued — this page refreshes itself when the new snapshot lands.</span>`
      : `<button id="scrrebuild" title="Queue the screens job for this market; it rebuilds the snapshot (about a minute)">Rebuild snapshot</button>`}</div>`;
}
/** A page that asked the queue for fresher data (a screens snapshot, a strategies re-run): check /api/wait
 *  quietly and re-render ONCE, when the work has landed — its completion signature moved, or the job it saw
 *  pending is no longer pending — never on a timer. Meanwhile the `.refresh-wait` line says what the job is
 *  queued behind, since one worker runs one job at a time and a backtest ahead of it can take hours.
 *  `busy()` holds the re-render while you are editing. */
function watchRefresh(alive, mkt, target, busy = () => false, every = 15000) {
  let first, seenPending = false, t = null;
  const since = (iso) => {
    if (!iso) return "";
    const h = (Date.now() - new Date(iso).getTime()) / 3.6e6;
    return h < 1 ? `${Math.max(1, Math.round(h * 60))} min` : h < 48 ? `${Math.round(h)} h` : `${Math.round(h / 24)} days`;
  };
  const say = (w) => {
    const el = $view.querySelector(".refresh-wait");
    if (!el) return;
    el.innerHTML = w.running ? `<span class="spin"></span> Updating now — this page refreshes itself when it lands.`
      : w.fast_lane ? `<span class="spin"></span> Queued for the fast lane — starts within moments; this page refreshes itself when it lands.`
      : w.behind ? `<span class="spin"></span> Queued, #${w.behind.position} in line — waiting for <b>${esc(w.behind.what)}</b> (running ${since(w.behind.started_at)}) to finish. The page refreshes itself when the update lands; meanwhile you are seeing the stored data. <a href="#/status">Queue</a>`
      : !w.worker_alive ? `The job worker is not running, so the update will not start. <a href="#/status">Start it</a>`
      : w.pending ? `<span class="spin"></span> Queued — starts next.` : `<span class="spin"></span> Updating…`;
  };
  const tick = async () => {
    if (!alive()) return;
    const w = await api(`/api/wait?market=${encodeURIComponent(mkt)}&target=${target}`).catch(() => null);
    if (!alive()) return;
    if (w) {
      if (first === undefined) first = w.sig;
      seenPending = seenPending || w.pending;
      say(w);
      if ((w.sig !== first || (seenPending && !w.pending)) && !busy()) { route(); return; }
    }
    t = setTimeout(tick, every);
  };
  tick();
  const prev = cleanup; cleanup = () => { clearTimeout(t); prev(); };
}

function wireStale(root, mkt) {
  const b = root.querySelector("#scrrebuild");
  if (!b) return;
  b.onclick = async () => {
    b.disabled = true;
    try {
      const r = await api(`/api/screens/rebuild?market=${mkt}`, { method: "POST" });
      toast(r.duplicate ? "A snapshot rebuild is already queued" : "Snapshot rebuild queued — the Data status page tracks it", "ok");
    } catch (e) { b.disabled = false; toast(`Could not queue the rebuild: ${e.message}`, "err"); }
  };
}

/** the Quality screen's card: the same shape as the others, but its list is long-term — scored on demand
 *  from financial statements, not rebuilt every session — so it says so instead of a daily change */
function qualityCard(qs, mkt) {
  const desc = "Long-term: companies with durable fundamentals, and when their price is right.";
  if (!qs || !qs.scored) return `<a class="sec-card scr-card" href="#/quality/${mkt}"><div class="scr-h"><b>Quality</b><span class="tag info">long-term</span></div>
      <div><span class="scr-n">—</span> <span class="muted small">no companies scored yet</span></div><div class="muted small scr-desc">${desc}</div>
      <div class="muted small">Scores come from financial statements: run the <code>quality</code> job (System → Schedules, or <code>python -m jobs enqueue quality</code>).</div></a>`;
  return `<a class="sec-card scr-card" href="#/quality/${mkt}" title="Open the Quality screen">
      <div class="scr-h"><b>Quality</b><span class="tag info" title="Scored from financial statements and refreshed on demand, not every session">long-term</span></div>
      <div><span class="scr-n">${qs.high}</span> <span class="muted small">high quality (score ${qs.threshold}+, no red flag) of ${qs.scored.toLocaleString()} scored</span></div>
      <div class="muted small scr-desc">${desc}</div>
      ${qs.top.length ? `<div class="scr-top">${qs.top.map((t) => `<span class="chip-s" title="${esc(t.name || "")} — quality ${t.quality}">${esc(t.symbol.replace(/\.NS$/, ""))}</span>`).join("")}</div>` : ""}
      <div class="muted small">Scores refreshed ${prettyDate(qs.refreshed)} — a long-term list, so no daily change</div></a>`;
}
function screensOverview(main, list, mkt, alive, fs) {
  const card = (x) => {
    const ch = x.prev_count != null ? x.count - x.prev_count : null;
    const rules = (x.conditions || []).map((c) => condText(c, fs)).join("  ·  ");
    return `<div class="sec-card scr-card" data-key="${esc(x.key)}">
      <a class="scr-link" href="#/screens/${x.key}/${mkt}" title="Open this screen">
      <div class="scr-h"><b>${esc(x.name)}</b>${x.builtin ? "" : '<span class="tag info">yours</span>'}</div>
      <div><span class="scr-n" data-count>${x.count ?? "—"}</span> <span class="muted small">stocks qualify<span data-ch>${ch ? ` · <span class="${ch > 0 ? "pos" : "neg"}">${ch > 0 ? "+" : ""}${ch}</span> since the previous session` : ""}</span></span></div>
      <div class="muted small scr-desc">${esc(x.description || "")}</div>
      ${x.top?.length ? `<div class="scr-top">${x.top.slice(0, 8).map((t) => `<span class="chip-s" title="${esc(t.name || "")}">${esc(t.symbol.replace(/\.NS$/, ""))}</span>`).join("")}</div>` : ""}
      ${x.used_by?.length ? `<div class="muted small">Used by: ${x.used_by.map((u) => esc(u.name)).join(", ")}</div>` : ""}</a>
      <div class="muted small scr-conds" title="${esc(rules)}">${esc(rules)}</div>
      <div class="scr-rfoot"><button class="ghost sm" data-edit title="Edit the rules right here — results preview live">Edit rules</button></div>
      <div class="scr-rules" hidden></div></div>`;
  };
  const builtins = list.screens.filter((x) => x.builtin), mine = list.screens.filter((x) => !x.builtin);
  main.innerHTML = pageHead("Screens", { extra: marketSeg(mkt),
      context: `<span class="muted small">${prettyDate(list.date)} · ${list.tradable?.toLocaleString()} tradable stocks</span>${info(`<p>Which stocks are worth a look today. A screen is a set of conditions over every stock's daily snapshot (about 50 fields) — it only qualifies stocks; a strategy adds the trade.</p><p>${list.tradable?.toLocaleString()} of ${list.universe?.toLocaleString()} stocks clear the tradable floor (price, liquidity, a year of history).</p>`)}`,
      actions: `<a class="btn primary" href="#/screens/new/${mkt}">+ New screen</a>` })
    + `<p class="sd-lead">A screen only says <b>which stocks qualify</b> today — conditions over every stock's daily snapshot, no entry or stop.
        Each strategy draws its candidates from one screen and adds the trade: that is <a href="#/strategies">Today's setups</a>;
        the names a strategy marks tradeable or on watch also collect in <a href="#/watchlist/screener">Screener picks</a>.</p>`
    + staleBanner(list.stale_inputs, mkt, list.updating)
    + `
    <h3 class="ov-h">Built-in screens</h3><div class="scr-cards">${builtins.map(card).join("")}
      ${qualityCard(list.quality, mkt)}</div>
    <h3 class="ov-h">Your screens</h3><div class="scr-cards">${mine.map(card).join("")}
      <a class="sec-card scr-card scr-new" href="#/screens/new/${mkt}"><div class="scr-h"><b>+ New screen</b></div>
        <div class="muted small">Pick conditions from ~50 fields — returns, RS rank, moving averages, 52-week range, volume, trend, sector — and see the matching stocks as you build. Then study how it did over five years.</div></a></div>`;
  main.querySelectorAll(".mk button").forEach((b) => b.onclick = () => { pageMarket(b.dataset.v); route(); });
  wireStale(main, mkt);
  let editing = null;   // only one card's editor open at a time; while open, the updating-poll keeps hands off
  if (list.updating) watchRefresh(alive, mkt, "screens", () => !!editing);
  // inline rule editing on a card: the same editor as a screen's own page, with live counts
  main.querySelectorAll(".scr-card[data-key] [data-edit]").forEach((btn) => btn.onclick = (e) => {
    e.preventDefault(); e.stopPropagation();
    const cardEl = btn.closest(".scr-card"), key = cardEl.dataset.key;
    const open = !cardEl.querySelector(".scr-rules").hidden;
    main.querySelectorAll(".scr-rules").forEach((el_) => { el_.hidden = true; el_.innerHTML = ""; });
    main.querySelectorAll("[data-edit]").forEach((b) => { b.textContent = "Edit rules"; });
    if (open) { editing = null; return; }
    editing = key;
    const x = list.screens.find((s) => s.key === key);
    const conds = JSON.parse(JSON.stringify(x.conditions || []));
    const orig = JSON.stringify(conds);
    const modified = () => JSON.stringify(conds) !== orig;
    const host = cardEl.querySelector(".scr-rules");
    host.hidden = false; btn.textContent = "Close";
    host.innerHTML = `<div data-conds></div>
      <div class="scr-rfoot"><span class="muted small" data-note>${x.builtin ? "edits save as a screen of your own — the built-in stays as coded" : ""}</span>
        <span class="spacer"></span><button class="sm" data-reset hidden>Reset</button>
        <button class="primary sm" data-save hidden>${x.builtin ? "Save as my screen…" : "Save changes"}</button></div>`;
    const countEl = cardEl.querySelector("[data-count]"), chEl = cardEl.querySelector("[data-ch]"), rulesEl = cardEl.querySelector(".scr-conds");
    let qt, qseq = 0;
    const sync = () => { const m = modified();
      host.querySelector("[data-reset]").hidden = host.querySelector("[data-save]").hidden = !m;
      rulesEl.textContent = conds.map((c) => condText(c, fs)).join("  ·  "); };
    const requery = () => { clearTimeout(qt); qt = setTimeout(async () => {
      const my = ++qseq;
      const rr = await api("/api/screens/query", jsonReq("POST", { market: mkt, conditions: conds, limit: 1 })).catch(() => null);
      if (!alive() || my !== qseq || !rr || rr.error || rr.empty) return;
      countEl.textContent = rr.count; chEl.innerHTML = modified() ? ' <span class="muted">· edited, live</span>' : "";
    }, 300); };
    const ed = condEditor(host.querySelector("[data-conds]"), fs, conds, () => { sync(); requery(); });
    host.querySelector("[data-reset]").onclick = () => { conds.length = 0; conds.push(...JSON.parse(orig)); ed.draw(); sync(); requery(); };
    host.querySelector("[data-save]").onclick = async () => {
      try {
        if (x.builtin) {
          const name = await askText("Save as my screen", `${x.name} (mine)`, "Name for your copy");
          if (!name || !name.trim()) return;
          const res = await api("/api/screens", jsonReq("POST", { name: name.trim(), description: x.description || "", conditions: conds }));
          toast(`Saved “${res.name}”`, "ok"); store.set("scrKey", res.key); go(`#/screens/${res.key}/${mkt}`);
        } else {
          await api("/api/screens", jsonReq("POST", { id: x.id, name: x.name, description: x.description || "", conditions: conds, sort_by: x.sort_by, columns: x.columns }));
          toast("Screen updated", "ok"); editing = null; route();
        }
      } catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
    };
  });
}

/** The screen builder: conditions with a live preview; save as one of your screens. */
function screenBuilder(main, alive, mkt, fs, base, editKey) {
  let conds = JSON.parse(JSON.stringify(base.conditions || []));
  main.innerHTML = `<div class="page-head"><h1>${editKey ? "Edit screen" : "New screen"}</h1>${marketSeg(mkt)}<span class="spacer"></span>
      <a class="ghost btn" href="#/screens/${editKey || store.get("scrKey", "stage2")}/${mkt}">Cancel</a><button class="primary" id="bsave">Save screen</button></div>
    <div class="sec-card builder">
      <div class="b-meta"><input id="bname" placeholder="Name, e.g. Strong leaders near highs" value="${esc(base.name || "")}"><input id="bdesc" placeholder="Description (optional)" value="${esc(base.description || "")}"></div>
      <h3>Stocks where every condition holds</h3><div id="bconds"></div>
      <p class="muted small">Compare a field with a number, or with another field (× a factor, e.g. Close ≥ 52-week high × 0.9). Percent fields are in % (enter 20 for 20%). Hover a field for its meaning.</p>
    </div>${segmented([["results", "Results"], ["study", "Study (5 years of month-ends)"]], "results", "bview")}<div id="bres">${LOADING}</div>`;
  let view = "results";
  main.querySelectorAll(".bview button").forEach((b) => b.onclick = () => { view = b.dataset.v;
    main.querySelectorAll(".bview button").forEach((x) => x.classList.toggle("on", x === b)); preview(); });
  main.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(`#/screens/${editKey ? editKey + "/" + b.dataset.v + "/edit" : "new/" + b.dataset.v}`));
  let qt, seq = 0;
  const preview = () => { clearTimeout(qt); qt = setTimeout(async () => {
    const my = ++seq;
    if (view === "study") return screenStudy(main.querySelector("#bres"), () => alive() && my === seq, null, mkt, { name: main.querySelector("#bname").value || "Draft" }, conds);
    const r = await api("/api/screens/query", jsonReq("POST", { market: mkt, conditions: conds })).catch((e) => ({ error: e.message }));
    if (!alive() || my !== seq) return;
    const host = main.querySelector("#bres");
    if (r.empty) r.error = "No snapshot for this market yet — run: " + r.command;
    if (r.error) { host.innerHTML = `<div class="empty"><b>Can't run this yet</b><div class="muted">${esc(r.error.replace(/^\d+ /, ""))}</div></div>`; return; }
    screenResults(host, r, mkt, { name: main.querySelector("#bname").value || "Draft", conditions: conds }, fs);
  }, 250); };
  condEditor(main.querySelector("#bconds"), fs, conds, preview);
  main.querySelector("#bsave").onclick = async () => {
    const name = main.querySelector("#bname").value.trim();
    if (!name) { toast("Give the screen a name", "err"); main.querySelector("#bname").focus(); return; }
    try {
      const r = await api("/api/screens", jsonReq("POST", { id: editKey ? +editKey.slice(1) : null, name, description: main.querySelector("#bdesc").value.trim(), conditions: conds }));
      toast(`Saved “${r.name}”`, "ok"); store.set("scrKey", r.key); go(`#/screens/${r.key}/${mkt}`);
    } catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
  };
  main.querySelectorAll(".b-meta input").forEach((x) => x.onkeydown = (e) => e.stopPropagation());
  preview();
}

/** Study: forward returns of a screen's qualifiers on each month-end vs all tradable stocks (screens/study.py).
 *  `key` is a saved screen; with `conds` (the builder) the unsaved conditions are studied. */
async function screenStudy(host, alive, key, mkt, d, conds) {
  host.innerHTML = LOADING;
  const r = await (conds ? api("/api/screens/study", jsonReq("POST", { market: mkt, conditions: conds })) : api(`/api/screens/${key}/study?market=${mkt}`))
    .catch((e) => ({ error: e.message.replace(/^\d+ /, "") }));
  if (!alive() || !host.isConnected) return;
  if (r.error || r.empty) {
    host.innerHTML = `<div class="empty"><b>${r.empty ? "Not enough history to study yet" : "Can't study this screen"}</b>
      <div class="muted">${r.empty ? `The study needs month-end snapshots (${r.month_ends} so far). Build five years of them (a few minutes, from scripts/, PYTHONPATH=.):` : esc(r.error)}</div>${r.command ? `<code>${esc(r.command)}</code>` : ""}</div>`;
    return;
  }
  const pp = (v, dg = 1) => pctf(v == null ? null : v / 100, dg);
  const s0 = r.summary[0];
  const cmp = (r.compare || []).slice().sort((a, b) => b.excess - a.excess);
  const mine = r.summary.find((x) => x.horizon === "6M");
  if (mine && !d.builtin) cmp.push({ screen: key || "draft", name: `${d.name || "This screen"} (this)`, excess: mine.excess }), cmp.sort((a, b) => b.excess - a.excess);
  const mx = Math.max(0.5, ...cmp.map((x) => Math.abs(x.excess)));
  const small = s0.avg_qualifiers < 10 ? `<div class="sd-status watch"><b>Small sample</b> About ${Math.round(s0.avg_qualifiers)} qualifiers per month-end — a few big winners or losers dominate these averages; treat them as anecdote, not evidence.</div>` : "";
  host.innerHTML = `${small}<div class="sec-top">
      <section class="sec-card"><h3>Did qualifiers beat the field?</h3>
        <table class="stt"><thead><tr><th>Held for</th><th class="num">Qualifiers</th><th class="num">All tradable</th><th class="num">Excess</th><th class="num" title="Share of qualifiers that beat the median tradable stock">Hit rate</th><th class="num" title="Share of month-ends on which qualifiers beat all tradable stocks on average">Dates won</th></tr></thead><tbody>
        ${r.summary.map((x) => `<tr><td><b>${x.horizon}</b></td><td class="num">${pp(x.mean)}</td><td class="num muted">${pp(x.universe)}</td>
          <td class="num"><b class="${x.excess >= 0 ? "pos" : "neg"}">${pp(x.excess, 2)}</b></td><td class="num">${(x.hit_rate * 100).toFixed(0)}%</td><td class="num">${(x.pct_dates_beating * 100).toFixed(0)}%</td></tr>`).join("")}</tbody></table>
        <p class="muted small">${s0.dates} month-ends from ${prettyDate(s0.first)} to ${prettyDate(s0.last)} · about ${Math.round(s0.avg_qualifiers)} qualifiers each ${info(`<p>On each month-end the conditions were applied to that day's snapshot only; returns run to the month-end 1, 3 and 6 months later, close to close, equal-weight, no costs.</p>
          <p><b>Hit rate</b>: share of qualifiers that beat the median tradable stock. <b>Dates won</b>: share of month-ends on which qualifiers beat all tradable stocks on average.</p>
          <p>Caveats: delisted stocks are missing (survivorship), which flatters every group but most the weakest; 3- and 6-month windows overlap, so the dates are not independent; sector and industry use today's classification. This measures the screen alone — a strategy adds setups, entries and exits, judged by its backtests.</p>`)}</p></section>
      <section class="sec-card"><h3>Against the built-in screens <span class="muted small">— 6-month excess</span></h3>
        <div class="dbars">${cmp.map((x) => `<div class="dbar ${x.screen === (key || "draft") ? "me" : ""}"><span class="dl">${esc(x.name)}</span>
          <span class="dt"><i class="${x.excess >= 0 ? "up" : "dn"}" style="width:${(Math.abs(x.excess) / mx) * 50}%;${x.excess >= 0 ? "left:50%" : "right:50%"}"></i></span>
          <span class="dv ${x.excess >= 0 ? "pos" : "neg"}">${pp(x.excess, 2)}</span></div>`).join("")}</div>
        <p class="muted small">A stricter screen should beat a looser one.</p></section></div>
    <section class="sec-card"><div class="sec-card-h"><h3>Each month-end</h3><span class="muted small">qualifiers' 3-month return minus all tradable stocks' (bars) · number of qualifiers (line, right axis)</span></div><div id="stchart" class="gchart" style="height:300px"></div></section>
    `;
  const el_ = host.querySelector("#stchart");
  const chart = LC.createChart(el_, { autoSize: true, ...chartTheme(), handleScroll: false, handleScale: false, rightPriceScale: { borderColor: cssVar("--line-2") }, leftPriceScale: { visible: true, borderColor: cssVar("--line-2") } });
  const pts = r.series.filter((x) => x["3M"] && x["3M"].q != null);
  chart.addSeries(LC.HistogramSeries, { priceScaleId: "left", priceLineVisible: false, lastValueVisible: false, priceFormat: { type: "percent" } })
    .setData(pts.map((x) => { const e = x["3M"].q - x["3M"].u; return { time: x.date, value: +e.toFixed(2), color: e >= 0 ? "rgba(38,166,154,.7)" : "rgba(239,83,80,.7)" }; }));
  chart.addSeries(LC.LineSeries, { color: cssVar("--series"), lineWidth: 1.5, priceLineVisible: false, title: "qualifiers" }).setData(r.series.map((x) => ({ time: x.date, value: x.qualifiers })));
  chart.timeScale().fitContent();
  { const prev = cleanup; cleanup = () => { chart.remove(); prev(); }; }
}

// --------------------------------------------------------- strategies

/** Strategies: one page — Today's setups and every strategy on the left, the chosen one on the right. */
async function strategiesPage(alive, key, tab, mkt, runKey) {
  key = key && key !== "setups" ? key : "";
  $view.innerHTML = LOADING;
  const [list, tax] = await Promise.all([
    api("/api/strategies").catch(() => []),
    api("/api/taxonomy").catch(() => ({ behaviours: [] })),
  ]);
  if (!alive()) return;
  const dot = (x) => (x.kind === "screener" ? `<i class="st-dot ${statusClass(x.status) || "neutral"}" title="${esc(shortStatus(x.status))}"></i>` : "");
  const ver = (x) => (x.version && x.version !== "1.0") || !x.is_current ? `<span class="st-ver" title="${esc(x.spec_id || "")}">v${esc(x.version || "1.0")}</span>` : "";
  const item = (x, sub) => `<a class="nav-item${sub ? " sub" : ""} ${x.key === key ? "active" : ""}" href="#/strategies/${x.key}" title="${esc(x.description || "")}">
      <span><b class="sn">${dot(x)}${esc(x.name)}${ver(x)}</b><span class="muted small sk">${esc(x.screen_name || "")}</span></span>${x.backtests ? `<span class="n" title="backtests">${x.backtests}</span>` : ""}</a>`;
  // Trading strategies group by style (server order). Within a style they group
  // by FAMILY: the current version heads the group, with older versions and
  // sibling variants nested under it. Listing every version flat made five
  // families read as eight unrelated strategies.
  const scr = list.filter((x) => x.kind === "screener");
  const famOf = (x) => x.family || x.key;
  const heads = new Set(scr.filter((x) => x.is_current).map((x) => x.key));
  const topLevel = (x) => (x.is_current ? true : !scr.some((p) => p.is_current && famOf(p) === famOf(x)));
  const vnum = (x) => String(x.version || "1.0").split(".").map(Number);
  const byVersionDesc = (a, b) => (vnum(b)[0] - vnum(a)[0]) || ((vnum(b)[1] || 0) - (vnum(a)[1] || 0));
  const withVariants = (p) => item(p) + scr
    .filter((v) => v.key !== p.key && famOf(v) === famOf(p) && !heads.has(v.key))
    .sort(byVersionDesc)
    .map((v) => item(v, true)).join("");
  // Group by HOW CANDIDATES ARE SELECTED, not by entry style. Entry style put
  // six of eight strategies in one bucket and said nothing about results;
  // selection is the axis that separated them — ranking the universe beat a
  // random control by +7.78pp, and it is the only approach here that has
  // beaten an index. Benchmark and long-term entries join the same grouping
  // rather than sitting in separate trailing sections, so momentum_baseline
  // appears next to what it should be compared with.
  const all = list.filter((x) => x.behaviour_label);
  // Group by market behaviour, then by selection within it. Behaviours with no strategy yet are still
  // listed — every strategy here is a trend/momentum bet, and hiding the blanks would imply the space has
  // been explored when one idea has been tried several ways — but folded into one "not yet explored"
  // entry, so they map what is untested without taking the sidebar's room.
  const untried = (tax.behaviours || []).filter((b) => !all.some((x) => x.behaviour === b.key));
  const stratNav = (tax.behaviours || []).map((b) => {
    const mine = all.filter((x) => x.behaviour === b.key);
    if (!mine.length) return "";
    const subs = [...new Map(mine.map((x) => [x.selection_label, x.selection_rank ?? 99]))].sort((a, b2) => a[1] - b2[1]);
    const body = subs.map(([slabel]) => (subs.length > 1 ? `<div class="nav-sub-h">${esc(slabel)}</div>` : "") +
      mine.filter((x) => x.selection_label === slabel && (x.kind !== "screener" || topLevel(x)))
          .map((x) => (x.kind === "screener" ? withVariants(x) : item(x))).join("")).join("");
    return `<div class="nav-h">${esc(b.label)}</div>${body}`;
  }).join("");
  const ungrouped = list.filter((x) => !x.behaviour_label);
  const rest = ungrouped.length ? `<div class="nav-h">Other</div>${ungrouped.map((x) => item(x)).join("")}` : "";
  $view.innerHTML = `<div class="rep-layout"><aside class="rep-nav strat-nav">
      <a class="nav-item ${key ? "" : "active"}" href="#/strategies"><span><b class="sn">Today's setups</b><span class="muted small sk">every strategy's trades and watch names</span></span></a>
      ${stratNav}${rest}
      ${untried.length ? `<details class="nav-untried"><summary class="nav-h">Not yet explored (${untried.length})</summary>
        <div class="nav-empty muted small">Kinds of market behaviour no strategy here trades yet: ${untried.map((b) => esc(b.label)).join(" · ")}.</div></details>` : ""}
    </aside><section id="stmain" class="scr-main">${LOADING}</section></div>`;
  const main = $view.querySelector("#stmain");
  if (!key) return setupsPage(alive, main);
  if (key === "quality" && !tab) tab = "rules";
  return strategyPage(alive, main, key, tab, mkt, runKey);
}


async function setupsPage(alive, root) {
  const mkt = pageMarket();
  document.title = "Today's setups · Trading";
  root.innerHTML = LOADING;
  const r = await api(`/api/setups?market=${mkt}`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  let show = store.get("setupsShow", "all");
  const newest = r.runs?.length ? r.runs.map((x) => x.run).sort().at(-1) : null;
  root.innerHTML = pageHead("Today's setups", {
      extra: marketSeg(mkt),
      context: `<span class="muted small">${newest ? `latest run ${prettyDate(newest)}` : "not run yet"}</span>${info("<p>Every strategy's trades and watch names from its latest run. Strategies run on demand — <b>Run strategies…</b> adds a run to the job queue.</p>")}`,
      actions: `<button class="primary" id="runstrat" title="Run the strategies on today's data (adds a run to the job queue)">Run strategies…</button>` }) + `
    <p class="sd-lead">Each strategy's <b>verdict for today</b> — entry, stop, target and decision — on the stocks its
      <a href="#/screens">screen</a> qualified (each strategy's page names its screen). The names marked tradeable or on watch
      also collect in <a href="#/watchlist/screener">Screener picks</a>, so they stay on hand after today.</p>
    ${r.behind ? `<div class="scr-stale"><b>Newer prices have loaded since these runs — the setups below were decided on older bars.</b>
      <span class="sx refresh-wait">${r.behind.updating ? '<span class="spin"></span> A re-run of every strategy is queued — this page refreshes itself when the new runs land.'
        : "A refresh could not be queued automatically — use <b>Run strategies…</b>"}</span></div>` : ""}
    ${r.error ? `<div class="empty"><b>Could not load setups</b><div class="muted">${esc(r.error)}</div></div>` : `
    <div class="setup-runs">${r.runs.map((x) => `<a class="sec-card setup-run" href="#/strategies/${x.strategy}/setups/${mkt}">
        <b>${esc(x.name)}</b><div class="small"><span class="${x.tradeable ? "pos" : "muted"}">${x.tradeable} tradeable</span> · ${x.watch} on watch</div>
        <div class="muted small">${x.screened} from ${esc(x.screen || "its screen")} · ${prettyDate(x.run)}</div></a>`).join("")}</div>
    <div class="chips" id="sshow">${[["all", "All", r.rows.length], ["trade", "Tradeable", r.rows.filter((x) => x.tradeable).length], ["watch", "On watch", r.rows.filter((x) => !x.tradeable).length]]
      .map(([k, t, n]) => `<button class="chip ${k === show ? "on" : ""}" data-s="${k}">${t}<span>${n}</span></button>`).join("")}</div><div id="sclus"></div><div id="stbl"></div>`}`;
  root.querySelectorAll(".mk button").forEach((b) => b.onclick = () => { pageMarket(b.dataset.v); route(); });
  root.querySelector("#runstrat").onclick = () => startJob({ title: `Run strategies · ${mktInfo(mkt).name}`, targets: ["strategies"], market: mkt, screens: true });
  if (r.behind?.updating) watchRefresh(alive, mkt, "strategies");
  if (r.error) return;
  const draw = () => {
    const xs = r.rows.filter((x) => show === "all" || (show === "trade" ? x.tradeable : !x.tradeable));
    const cols = ["symbol", "name", "peer_group", "group_rs", "strategy", "decision", "setup", "price", "entry", "stop", "risk_pct", "target_r", "setup_quality", "wait_for"];
    const hide = ["target_r", "setup_quality", "wait_for"];
    dataTable(root.querySelector("#stbl"), cols, xs.map((x) => [x.symbol, x.name || "", x.peer_group || "", x.peer_rs ?? null, x.strategy_name, x.decision, x.setup, x.price, x.entry, x.stop, x.risk_pct, x.target_r, x.quality, x.wait_for || ""]), {
      name: `setups_${mkt}`, sort: ["setup_quality", -1], hidden: hide,
      rowClick: (row, visible) => openChartFromList(mkt, row[0], visible.map((y) => y[0]), "Today's setups", location.hash),
    });
    root.querySelector("#sclus").innerHTML = clusterChips(xs.map((x) => x.peer_group));
    wireClusters(root.querySelector("#sclus"), root.querySelector("#stbl"));
  };
  root.querySelector("#sshow").onclick = (e) => { const b = e.target.closest("[data-s]"); if (!b) return; show = b.dataset.s; store.set("setupsShow", show);
    root.querySelectorAll("#sshow .chip").forEach((c) => c.classList.toggle("on", c === b)); draw(); };
  draw();
}

const SCREEN_COLS = ["symbol", "name", "peer_group", "group_rs", "decision", "strategy_setup", "price", "entry", "stop", "risk_pct", "target_r", "sector", "setup_quality",
  "pattern", "rs_vs_benchmark", "rsi", "earnings_in", "wait_for", "reason"];

/** One strategy: How it works (thesis, rules, entry/exit, parameters, measured outcome) ·
 *  Candidates (what it points at, from its latest run) · Backtests. */
async function strategyPage(alive, root, key, tab, mkt, runKey) {
  root.innerHTML = LOADING;
  const d = await api(`/api/strategies/${encodeURIComponent(key)}`).catch(() => null);
  if (!alive()) return;
  if (!d) { root.innerHTML = `<div class="empty"><b>Strategy not found</b><div class="muted"><a href="#/strategies">Today's setups</a></div></div>`; return; }
  const trades = d.kind === "screener";
  // A portfolio strategy has no per-symbol setups to screen for -- it holds a ranked book. Its
  // equivalent of "Candidates" is what it HOLDS, taken from the latest run's still-open
  // positions, which are produced by the strategy's own rules rather than recomputed here.
  const holds = d.kind === "benchmark";
  // Same tab name as a screener's, because it answers the same question -- what does this strategy
  // point at right now -- and a reader should not learn two vocabularies to compare two strategies.
  // Rules FIRST, and the landing tab. Someone opening a strategy wants to know what it does and
  // whether it worked; "Setups today" answers neither and is only useful once you have decided to
  // trade it. Rules carries the measured outcome at its head (see perfGlance), so the landing page
  // answers both questions without a tab change -- and the tab order now matches that, instead of
  // leading with a tab nobody lands on.
  // Tab LABELS only -- the keys stay "rules"/"setups"/"holdings" so existing links keep working.
  //
  // "Rules" named one of the tab's nine sections (it also carries the measured outcome, the
  // thesis, how it works, entry and exit, decisions, parameters, commands and caveats), and
  // "Setups today" promised something the page cannot give: a screener shows its LATEST RUN,
  // which may be days old or may never have run, and a portfolio strategy shows a ranking as of
  // the last complete session, which the page itself says is "not a rebalance" and "not a buy
  // list". "Candidates" is true of both and promises neither freshness nor a decision.
  const tabs = [["rules", "How it works"],
    ...(trades ? [["setups", "Candidates"]] : []), ...(holds ? [["holdings", "Candidates"]] : []),
    // The tab's count is what the tab SHOWS. Counting archived runs here put "Backtests 47" above
    // a table of 4, which is the same mismatch the chips had.
    ["backtests", (() => { const n = d.backtests.filter((b) => !b.archived).length;
      return `Backtests${n ? ` <span class="n">${n}</span>` : ""}`; })()]];
  tab = tabs.some(([k]) => k === tab) ? tab : "rules";
  document.title = `${d.name} · Strategies · Trading`;
  const kind = { benchmark: "Benchmark", "long-term": "Long-term investing", screener: "Trading strategy" }[d.kind] || "Strategy";
  root.innerHTML = `<div class="crumbs">${kind}</div>
    <div class="page-head"><h1>${esc(d.name)}</h1><code>${esc(d.key)}</code>
      ${d.kind === "long-term" ? `<span class="spacer"></span><a class="btn" href="#/quality">Open the Quality page →</a>` : ""}</div>
    ${d.status ? `<div class="sd-badge"><span class="tag ${statusClass(d.status) === "watch" ? "warn" : statusClass(d.status) === "trade" ? "pos" : "neutral"}" title="${esc(statusVerdict(d.status))}">${esc(shortStatus(d.status))}</span></div>` : ""}
    <p class="sd-lead">${mdInline(d.description)}${d.variant_of ? ` A variant of <a href="#/strategies/${d.variant_of.key}/rules">${esc(d.variant_of.name)}</a>.` : ""}${d.screen ? ` Draws its candidates from the <a href="#/screens/${d.screen.key}/${pageMarket()}/criteria">${esc(d.screen.name)}</a> screen.` : ""}</p>
    ${tabsHtml(tabs.map(([k, t]) => [k, t, `#/strategies/${key}/${k}`]), tab)}<div id="stab"></div>`;
  const host = root.querySelector("#stab");
  if (tab === "setups") return strategySetups(host, alive, key, mkt, runKey);
  if (tab === "holdings") return strategyHoldings(host, alive, d, key);
  if (tab === "backtests") return strategyBacktests(host, d, key);
  strategyRules(host, d, key);
}

/** The measured outcome, per market, at the head of the Rules tab.
 *
 *  A strategy's page used to require opening Backtests and reading a table to learn whether the
 *  thing worked. This answers it in one row per market: the LATEST run (what it does as the rules
 *  now stand) and the BEST excess CAGR ever recorded (what it has managed at its best). Both are
 *  shown because they differ for a reason worth seeing -- a strategy whose best run is three
 *  versions old has been tuned downwards, and one whose latest IS its best has not been cherry
 *  picked.
 *
 *  Excess CAGR orders "best" because that is the number the rest of the app decides on. It is
 *  deliberately NOT selection: the decomposition needs the equity curve's cash column, which the
 *  run summary does not carry, and inventing a different ranking here from the one the Backtests
 *  table shows would make the two disagree.
 *
 *  A run from a superseded spec id is marked, the same way the Backtests tab marks it. Without
 *  that, the headline figure on the landing page could describe rules that no longer exist.
 */
function perfGlance(d, key) {
  const runs = (d.backtests || []).filter((b) => b.summary && b.summary.cagr);
  const vers = d.versions || [];
  const isOld = (sid) => { const v = vers.find((x) => x.spec_id === sid); return v ? !v.is_current : false; };
  const num = (x) => { const v = parseFloat(String(x ?? "").replace(/[^-\d.]/g, "")); return Number.isFinite(v) ? v : null; };
  const sign = (x) => (/^-/.test(String(x || "")) ? "neg" : x ? "pos" : "");
  const stale = (sid) => (isOld(sid) ? '<i class="old" title="produced by rules that have since changed">\u25b2</i>' : "");

  if (!runs.length) {
    const none = (d.backtests || []).length
      ? `${d.backtests.length} run${d.backtests.length === 1 ? "" : "s"} recorded, none with trades to report`
      : "No backtest has been run yet";
    return `<section class="sd-sec sd-glance" id="sd-glance"><h2>Measured outcome</h2>
      <p class="muted">${none}. ${d.kind === "long-term" ? "This tracker is not backtested." :
        `Queue one from <a href="#/strategies/${esc(key)}/backtests">Backtests</a>.`}</p></section>`;
  }

  // `d.backtests` arrives newest-first, so the first match per market IS the latest.
  const mkts = [...new Set(runs.map((b) => b.market))].sort();
  const rows = mkts.map((m) => {
    const mine = runs.filter((b) => b.market === m);
    const latest = mine[0];
    const best = mine.reduce((a, b) => (num(b.summary.excess_cagr) > num(a.summary.excess_cagr) ? b : a), mine[0]);
    const s = latest.summary;
    const same = best.id === latest.id;
    const mi = mktInfo(m);
    return `<tr data-href="#/reports/${latest.id}" title="Open the latest ${esc(mi.name || m)} run">
      <td>${mi.flag || ""} ${esc(mi.name || m.toUpperCase())}</td>
      <td class="num">${esc(s.cagr || "")}</td>
      <td class="num ${sign(s.excess_cagr)}"><b>${esc(s.excess_cagr || "")}</b>${stale(latest.spec_id)}</td>
      <td class="num">${esc(s.max_drawdown || "")}</td>
      <td class="num">${esc(s.sharpe || "")}</td>
      <td class="muted small">${prettyDate(latest.generated_at)}${mine.length > 1 ? ` · ${mine.length} runs` : ""}</td>
      <td class="num ${same ? "muted" : sign(best.summary.excess_cagr)}">${same ? "this one"
        : `<a href="#/reports/${best.id}" title="${esc(best.run)}">${esc(best.summary.excess_cagr || "")}</a>${stale(best.spec_id)}`}</td></tr>`;
  }).join("");

  const anyStale = runs.some((b) => isOld(b.spec_id));
  return `<section class="sd-sec sd-glance" id="sd-glance">
    <h2>Measured outcome</h2>
    <table class="dtab click"><thead><tr><th>Market</th>
      <th class="num">CAGR</th>
      <th class="num" title="The strategy's CAGR minus its benchmark's. Positive means it beat buying and holding the index.">Excess CAGR</th>
      <th class="num">Max DD</th><th class="num">Sharpe</th><th>Latest run</th>
      <th class="num" title="The best excess CAGR this strategy has recorded in this market, across every run.">Best ever</th></tr></thead>
    <tbody>${rows}</tbody></table>
    <p class="muted small">The latest run per market, with the best excess CAGR ever recorded beside it.
      ${anyStale ? "\u25b2 marks a run produced by rules that have since changed. " : ""}Click a row for the full report, or see
      <a href="#/strategies/${esc(key)}/backtests">Backtests</a> for every run.
      Excess CAGR answers "did it beat doing nothing"; it does not separate a good signal from idle cash
      \u2014 the report's SELECTION line does that.</p></section>`;
}

function strategyRules(host, d, key) {
  const codeTable = (rows, head, extra) => rows.length ? `<table class="dtab"><thead><tr><th>${head}</th>${extra ? `<th>${extra[0]}</th>` : ""}<th>Rule</th></tr></thead><tbody>${rows.map((r) =>
    `<tr><td><code>${esc(r.code)}</code></td>${extra ? `<td>${extra[1](r)}</td>` : ""}<td>${mdInline(r.text) || '<span class="neg">Not documented</span>'}</td></tr>`).join("")}</tbody></table>` : "";
  const ol = (xs) => (xs.length ? `<ol class="sd-list">${xs.map((x) => `<li>${mdInline(x)}</li>`).join("")}</ol>` : "");
  const ul = (xs) => (xs.length ? `<ul class="sd-list">${xs.map((x) => `<li>${mdInline(x)}</li>`).join("")}</ul>` : "");
  const sec = (id, title, body) => (body ? `<section class="sd-sec" id="sd-${id}"><h2>${title}</h2>${body}</section>` : "");
  const sameAcross = d.params.every((p) => p.values.us === p.values.india);
  const params = d.params.length ? `<table class="dtab"><thead><tr><th>Parameter</th>${sameAcross ? "<th class='num'>Value</th>" : "<th class='num'>US</th><th class='num'>India</th>"}<th>Meaning</th></tr></thead><tbody>${
    d.params.map((p) => `<tr><td>${esc(p.label)}<div class="muted small"><code>${esc(p.source)}</code></div></td>${
      sameAcross ? `<td class="num">${esc(p.values.us)}</td>` : `<td class="num">${esc(p.values.us)}</td><td class="num">${esc(p.values.india)}</td>`}<td>${mdInline(p.meaning)}</td></tr>`).join("")}</tbody></table>
    <p class="muted small">Values are read live from the code and the market configs.</p>` : "";
  const fromScreen = d.gates.filter((g) => g.screen), own = d.gates.filter((g) => !g.screen);
  let step = 0;
  const num = () => (fromScreen.length ? `${++step} · ` : "");
  const cmds = Object.entries(d.commands).map(([k, c]) => `<div class="cmd"><div class="muted small">${esc(k)}</div><pre><code>${esc(c)}</code></pre><button class="ghost copy" data-c="${esc(c)}">Copy</button></div>`).join("");
  // Numbers BEFORE the status prose. A `status` runs to several hundred words on a strategy that
  // has been measured properly, which pushed the figures below the fold -- and being able to see
  // the outcome without scrolling is the whole reason this is the landing tab.
  host.innerHTML = `<section class="sdoc sdoc-tab">
    ${perfGlance(d, key)}
    ${sec("overview", "Overview", `${d.thesis ? `<p><b>Thesis.</b> ${mdInline(d.thesis)}</p>` : ""}<h3>How it works</h3>${ol(d.how_it_works)}`)}
    ${d.kind === "long-term" && d.gates.length ? sec("rules", "Quality tests", `<p class="muted small">Points out of 100.</p>${codeTable(d.gates, "Worth")}`) : ""}
    ${d.kind !== "long-term" && (d.gates.length || d.watch.length || d.setups.length) ? `<section class="sd-sec" id="sd-rules"><h2>Rules</h2>
      ${fromScreen.length ? `<h3>${num()}Qualify — from the <a href="#/screens/${d.screen.key}/${pageMarket()}/criteria">${esc(d.screen.name)}</a> screen</h3>
        ${codeTable(fromScreen, "Gate", ["Screen", (r) => `<code>${r.screen}</code>`])}` : ""}
      ${own.length ? `<h3>${fromScreen.length ? `${num()}Trade rules — this strategy's own` : "Hard gates"} <span class="muted small">— all must pass, or the stock is AVOID</span></h3>${codeTable(own, "Gate")}` : ""}
      ${d.setups.length ? `<h3>${num()}Setups <span class="muted small">— the patterns that make a stock entry-eligible</span></h3>${codeTable(d.setups, "Setup")}` : ""}
      ${d.watch.length ? `<h3>Warning flags <span class="muted small">— don't disqualify, but cap or downgrade the decision</span></h3>${codeTable(d.watch, "Flag")}` : ""}
      </section>` : ""}
    ${sec("entry", d.kind === "long-term" ? "Is the price right?" : "Entry & exit", `${d.entry_rules.length ? (d.kind === "long-term" ? ul(d.entry_rules) : `<h3>${d.kind === "benchmark" ? "Entry" : "Entry, stop and target"}</h3>${ol(d.entry_rules)}`) : ""}${d.exit_rules.length ? `<h3>Exit</h3>${ol(d.exit_rules)}` : ""}`)}
    ${sec("decisions", "Decisions", d.decisions.length ? `<table class="dtab"><tbody>${d.decisions.map((x) => `<tr><td><span class="tag ${decisionClass(x.label)}">${esc(x.label)}</span></td><td>${esc(x.text)}</td></tr>`).join("")}</tbody></table>
      <p class="muted small">${esc(d.regime_note)}</p>` : "")}
    ${sec("params", "Parameters", params)}
    ${sec("commands", "Commands", `${cmds}<p class="muted small">Run from <code>scripts/</code> with <code>PYTHONPATH=.</code>.</p>`)}
    ${sec("caveats", "Known caveats", ul(d.caveats))}
    <p class="muted small sd-src">Generated from <code>${esc(d.source.file)}</code> · code last changed ${prettyDate(d.source.modified)} — built from the strategy's own code, so it describes what actually runs.</p></section>`;
  host.querySelectorAll(".copy").forEach((b) => b.onclick = async () => {
    try { await navigator.clipboard.writeText(b.dataset.c); toast("Command copied", "ok"); } catch { toast("Copy failed — select the text instead", "err"); }
  });
  // The glance rows are clickable like the Backtests table's, which wires this inside its own
  // tab. The guard matters: the "Best ever" cell holds its own link to a DIFFERENT run, and
  // without it a click there would fire both and land on the latest run instead.
  host.querySelectorAll(".sd-glance tr[data-href]").forEach((tr) => tr.onclick = (e) => {
    if (e.target.closest("a")) return;
    go(tr.dataset.href);
  });
}

/** A portfolio strategy's "setups today": what its rules point at on the latest stored bar.
 *
 *  Computed by the strategy's own selection (backtesting/baseline.eligible_scores, the same code
 *  the backtest ranks with) rather than restated here, so the page and the measured strategy
 *  cannot disagree. It is a RANKING as of the last complete session, not a rebalance -- the
 *  strategy only acts on its rebalance date, which the note says so nobody reads it as a buy list.
 */
async function strategyHoldings(host, alive, d, key) {
  let mkt = store.get("setupMkt:" + key, null) || pageMarket();
  let show = store.get("selShow:" + key, "held");
  // A paint takes ~18s (it ranks the whole universe), so switching market starts a second one
  // while the first is still in flight. alive() only guards against leaving the PAGE, so without
  // a sequence token the slower reply writes its header into the newer market's head -- which it
  // did: two "Ranked ..." labels, for two different markets, side by side.
  let seq = 0;
  const paint = async () => {
    const my = ++seq;
    host.innerHTML = `<div class="page-head sub">${marketSeg(mkt)}<span class="spacer"></span>
        <button id="run1" title="Re-rank this strategy on the latest stored prices">Re-rank…</button></div>
      <div class="chips" id="dec"></div><div id="tbl">${LOADING}</div>`;
    wireHead();
    const r = await api(`/api/portfolio-selection/${encodeURIComponent(key)}/${mkt}?limit=200`).catch(() => null);
    if (!alive() || my !== seq) return;   // a newer paint owns the page
    const tbl = host.querySelector("#tbl");
    if (!r || !r.rows?.length) {
      tbl.innerHTML = `<div class="empty"><b>Nothing ranks in ${esc(mktInfo(mkt).name)}</b><div class="muted">${
        r ? "No name clears this strategy's liquidity floor and trend filter on the latest bar." : "The ranking could not be computed."}</div></div>`;
      return;
    }
    host.querySelector(".page-head.sub").insertAdjacentHTML("afterbegin",
      `<span class="run-label">Ranked ${esc(prettyDate(r.as_of))} — ${r.rows.filter((x) => x.held).length} held of ${r.eligible} eligible</span>`);
    const nHeld = r.rows.filter((x) => x.held).length;
    const dec = host.querySelector("#dec");
    const drawChips = () => {
      dec.innerHTML = [["held", "Held", nHeld, "trade"], ["all", "All ranked", r.rows.length, ""]]
        .map(([v, t, n, cls]) => `<button class="chip ${cls} ${v === show ? "on" : ""}" data-d="${v}">${t}<span>${n}</span></button>`).join("");
      dec.querySelectorAll(".chip").forEach((b) => b.onclick = () => {
        show = b.dataset.d; store.set("selShow:" + key, show); draw();
      });
    };
    const cols = ["rank", "symbol", "weight_pct", "score", "price", "turnover_20d"];
    const draw = () => {
      drawChips();
      const rows = (show === "held" ? r.rows.filter((x) => x.held) : r.rows)
        .map((x) => [x.rank, x.symbol, x.weight_pct, x.score, x.close, x.turnover]);
      if (!rows.length) { tbl.innerHTML = `<div class="empty"><b>Nothing held</b></div>`; return; }
      dataTable(tbl, cols, rows, {
        name: `selection_${key}`, sort: [0, 1], noStack: true,
        rowHint: "Click a row to open its chart",
        rowClick: (row) => go(`#/chart/${mkt}/${encodeURIComponent(row[1])}`),
      });
    };
    draw();
  };
  const wireHead = () => {
    host.querySelectorAll(".mk button").forEach((b) => b.onclick = () => {
      mkt = b.dataset.v; store.set("setupMkt:" + key, mkt); paint();
    });
    host.querySelector("#run1").onclick = () => paint();
  };
  paint();
}


function strategyBacktests(host, d, key) {
  const pv = (x) => (x == null ? "" : x);
  // Portfolio strategies run too -- the backtest job dispatches them to the baseline runner
  // (jobs/registry._backtest_steps). Only the quality tracker has no backtest to queue.
  const canRun = d.kind === "screener" || d.kind === "benchmark";
  const runBtn = () => canRun ? `<div class="bt-run"><button class="primary sm" id="btrun" title="Queue a full-history backtest of this strategy (its documented exit policy) — slow; follow it on System → Runs">Backtest <span id="btrunmkt">${esc(mktInfo(runMarket()).name)}</span>…</button>
      <span class="muted small">runs in the job queue — follow it on <a href="#/runs">System → Runs</a></span></div>` : "";
  const vers = d.versions || [];
  // A run's spec_id is version + the fingerprint of the rules behind it. Show the bare
  // version when it is unambiguous, and the whole spec_id when the same version number
  // covers more than one rule set — then the number alone does not identify the run.
  const vlabel = (v) => (v.ambiguous ? v.spec_id : "v" + v.version);
  let sel = store.get("btVer:" + key, null);
  if (sel && !vers.some((v) => v.spec_id === sel)) sel = null;   // a filter from before a reload

  // Market, alongside Version. The page's market picker lives on "Setups today", which only a
  // screener has — so a benchmark strategy had no way to express market at all, and a screener's
  // runs from both markets sat interleaved in one table with only a column to tell them apart.
  // Starts at All, every visit, and deliberately does NOT restore a previous choice.
  //
  // It also no longer shares one stored key with the Setups tab's market picker. Both used to
  // read and write `btMkt:<key>`, so choosing a country on Setups silently pre-filtered this
  // table to the same country -- two different questions ("what does it hold today" and "every
  // run ever") answered through one setting, with nothing on screen to say why half the runs had
  // vanished. The Setups picker still persists, now under `setupMkt:<key>`.
  // Archived runs are hidden by default and counted on their own chip. A strategy under active
  // development accumulates superseded runs worth keeping but not worth scrolling past --
  // minervini has 47 against every other strategy's 4 or fewer.
  let showArchived = false;
  let msel = null;
  // the chip IS the country toggle for this tab: with one chosen, Backtest runs that market
  const runMarket = () => msel || pageMarket();
  // every market, not just the ones already run: with no runs there is nothing to choose from,
  // and choosing is how you say which market the Backtest button should queue
  const mkts = [...new Set([...d.backtests.map((b) => b.market), ...MKTS.map((m) => m.key)])].sort();
  if (msel && !mkts.includes(msel)) msel = null;
  const achip = () => { const n = d.backtests.filter((b) => b.archived).length;
    if (!n && !showArchived) return "";
    return `<button class="chip ${showArchived ? "on" : ""}" data-arch="1"
      title="Archived runs are kept in full — report, figures and trades — and only hidden from this list">
      Archived <span class="n">${n}</span></button>`; };

  const mchips = () => mkts.length <= 1 ? "" : `<div class="bt-vers"><span class="muted small">Market</span>
    <button class="chip ${msel ? "" : "on"}" data-m="">All <span class="n">${d.backtests.filter((b) => !b.archived).length}</span></button>
    ${mkts.map((m) => `<button class="chip ${msel === m ? "on" : ""}" data-m="${esc(m)}">${mktInfo(m).flag || ""} ${esc(mktInfo(m).name || m.toUpperCase())}
        <span class="n">${d.backtests.filter((b) => b.market === m && !b.archived).length}</span></button>`).join("")}${achip()}</div>`;

  const chips = () => vers.length <= 1 ? "" : `<div class="bt-vers"><span class="muted small">Version</span>
    <button class="chip ${sel ? "" : "on"}" data-v="">All <span class="n">${d.backtests.filter((b) => !b.archived).length}</span></button>
    ${vers.map((v) => `<button class="chip ${sel === v.spec_id ? "on" : ""}" data-v="${esc(v.spec_id)}" title="${esc(v.spec_id)}${v.is_current ? " — the rules as they stand now" : ""}">
        ${esc(vlabel(v))}${v.is_current ? '<i class="cur" title="current">●</i>' : ""} <span class="n">${v.runs}</span></button>`).join("")}</div>`;

  const detail = () => {
    const v = vers.find((x) => x.spec_id === sel);
    if (!v) return "";
    const since = v.since || [];
    return `<div class="bt-vdet">
      <div class="vh"><b>${esc(v.spec_id)}</b>${v.is_current ? '<span class="tag pos">current</span>' : `<span class="tag">superseded</span>`}
        ${v.date ? `<span class="muted small">${prettyDate(v.date)}</span>` : ""}
        <span class="muted small">${v.runs} backtest${v.runs === 1 ? "" : "s"}</span></div>
      ${v.changed ? `<p class="vc"><b>What v${esc(v.version)} changed:</b> ${mdInline(v.changed)}</p>` : ""}
      ${v.ambiguous ? `<p class="vc warn-t">Another rule set also calls itself v${esc(v.version)} — same version number, different fingerprint. Compare these runs by the full spec id, not the number.</p>` : ""}
      ${since.length ? `<div class="vsince"><b>${since.length} change${since.length === 1 ? "" : "s"} since, so these runs do not reflect the current rules:</b>
        <ul>${since.map((c) => `<li><b>v${esc(c.version)}</b> ${mdInline(c.change)}</li>`).join("")}</ul></div>`
        : v.is_current ? `<p class="muted small">Nothing has changed since — these runs reflect the strategy as it stands.</p>` : ""}
    </div>`;
  };

  // computed per paint, not once: `sel` changes when a chip is clicked
  const table = () => { const shown = d.backtests.filter((b) => (!sel || b.spec_id === sel) && (!msel || b.market === msel)
                                                                 && (showArchived ? b.archived : !b.archived));
    // The options list runs to six items on a minervini run ("ranked by RS · spec rules · mktg ·
    // rb14 · progressive exposure (10 trades, pilot 0.5) · entries: high-confidence + on-trigger"),
    // which is a paragraph per row in a table meant to be scanned down. Two, then a count; the
    // whole list is in the cell's tooltip beside the run's full name.
    const OPTS_SHOWN = 2;
    const runCell = (b) => { const rp = runParts(b.run);
      if (!rp) return `<td>${esc(b.run)}</td>`;
      const o = rp.options, more = o.length - OPTS_SHOWN;
      const opts = o.length
        ? `<div class="muted small">${esc(o.slice(0, OPTS_SHOWN).join(" · "))}${more > 0 ? ` <span class="bt-more">+${more}</span>` : ""}</div>`
        : "";
      const tip = [b.run, o.length > OPTS_SHOWN ? o.join(" · ") : ""].filter(Boolean).join("\n");
      return `<td title="${esc(tip)}">${prettyDate(rp.start)} · ${esc(rp.exit)}${opts}</td>`; };
    return shown.length ? `<table class="dtab click"><thead><tr><th>Market</th><th title="Start date and exit policy; options below. Hover for the run's full name.">Run</th><th>Version</th><th class="num">CAGR</th><th class="num">Excess CAGR</th><th class="num">Max DD</th><th class="num">Sharpe</th><th>Generated</th><th></th></tr></thead><tbody>${
      shown.map((b) => { const s = b.summary || {};
        const v = vers.find((x) => x.spec_id === b.spec_id);
        const vcell = b.spec_id
          ? `<td><span class="st-ver" title="${esc(b.spec_id)}${v && !v.is_current ? " — superseded" : ""}">${esc(v ? vlabel(v) : "v" + b.version)}</span>${v && !v.is_current ? '<i class="old" title="not the current rules">▲</i>' : ""}</td>`
          : `<td class="muted" title="this run predates version stamping">—</td>`;
        // A run that found nothing has no CAGR to show. Four blank cells read as a
        // broken row, so say what happened — the funnel in the report says where
        // the candidates stopped.
        if (!s.cagr) {
          return `<tr data-href="#/reports/${b.id}"><td>${b.market.toUpperCase()}</td>${runCell(b)}${vcell}
            <td class="num muted" colspan="4">no trades — open for the funnel</td>
            <td class="muted">${prettyDate(b.generated_at)}</td><td class="bt-arch"><button class="ghost sm" data-arch-id="${b.id}" data-arch-to="${b.archived ? "0" : "1"}" title="${b.archived ? "Restore this run to the list" : "Archive: keep the run, hide it from this list"}">${b.archived ? "Restore" : "Archive"}</button></td></tr>`;
        }
        return `<tr data-href="#/reports/${b.id}"><td>${b.market.toUpperCase()}</td>${runCell(b)}${vcell}<td class="num">${esc(pv(s.cagr))}</td>
          <td class="num ${/^-/.test(s.excess_cagr || "") ? "neg" : s.excess_cagr ? "pos" : ""}">${esc(pv(s.excess_cagr))}</td><td class="num">${esc(pv(s.max_drawdown))}</td>
          <td class="num">${esc(pv(s.sharpe))}</td><td class="muted">${prettyDate(b.generated_at)}</td><td class="bt-arch"><button class="ghost sm" data-arch-id="${b.id}" data-arch-to="${b.archived ? "0" : "1"}" title="${b.archived ? "Restore this run to the list" : "Archive: keep the run, hide it from this list"}">${b.archived ? "Restore" : "Archive"}</button></td></tr>`; }).join("")}</tbody></table>
      <p class="muted small">A backtest runs the whole strategy — screen, setups, entry, stop, exits, costs and position sizing — day by day. The command is under Rules › Commands.
      Each run is stamped with the spec id of the rules that produced it, so a result always maps to a version.</p>`
    : `<div class="empty"><b>No backtests match</b><div class="muted">Nothing has been run for
        ${esc([sel, msel && (mktInfo(msel).name || msel)].filter(Boolean).join(" in ") || "this filter")} yet.</div></div>`; };

  const paint = () => {
    // chips render even with no runs: picking the market is how you tell the button what to queue
    // Filters together, action to the side. The Backtest button used to render BETWEEN the Market
    // row and the Version row, splitting one group of filters in half with an unrelated action --
    // and because the button and an active chip share the accent fill, the three rows read as one
    // undifferentiated stack of orange controls rather than "two filters, one button".
    host.innerHTML = `<div class="bt-bar"><div class="bt-filters">${mchips()}${d.backtests.length ? chips() : ""}</div>${runBtn()}</div>`
      + (d.backtests.length ? detail() + table()
      : `<div class="empty"><b>No backtests loaded for this strategy</b><div class="muted">${canRun ? "Queue one with the button above, or run" : "Run"} the command under Rules › Commands; reports load into the app automatically.</div></div>`);
    host.querySelectorAll(".bt-vers .chip[data-v]").forEach((b) => b.onclick = () => {
      sel = b.dataset.v || null;
      store.set("btVer:" + key, sel);
      paint();
      wireBtRun();
    });
    host.querySelectorAll(".bt-vers .chip[data-m]").forEach((b) => b.onclick = () => {
      msel = b.dataset.m || null;
      paint();
      wireBtRun();
    });
    host.querySelectorAll("tr[data-href]").forEach((tr) => tr.onclick = (e) => {
      if (e.target.closest("button")) return;      // the row's Archive control is not a link
      go(tr.dataset.href);
    });
    host.querySelector("[data-arch]")?.addEventListener("click", () => { showArchived = !showArchived; paint(); wireBtRun(); });
    host.querySelectorAll("[data-arch-id]").forEach((b) => b.onclick = async (e) => {
      e.stopPropagation();
      const id = Number(b.dataset.archId), to = b.dataset.archTo === "1";
      b.disabled = true;
      try {
        await api(`/api/reports/${id}/archive`, jsonReq("POST", {archived: to}));
        // Patch the loaded payload rather than refetching: the strategy document is expensive to
        // rebuild and nothing else about it changed.
        const row = d.backtests.find((x) => x.id === id);
        if (row) row.archived = to;
        toast(to ? "Run archived" : "Run restored", "ok");
        paint();
        wireBtRun();
      } catch (err) {
        b.disabled = false;
        toast("Could not change the run: " + err, "err");
      }
    });
  };
  const wireBtRun = () =>
    host.querySelector("#btrun")?.addEventListener("click", () =>
      startJob({ title: `Backtest · ${mktInfo(runMarket()).name}`, targets: ["backtest"],
                 market: runMarket(), screens: d.kind === "screener", pick: key }));
  paint();
  wireBtRun();
}

/** a strategy's latest (or chosen) run: every screened stock with its decision, plan and gates */
async function strategySetups(host, alive, strat, mkt, runKey) {
  mkt = pageMarket(mkt);
  host.innerHTML = LOADING;
  const all = await api(`/api/screening/runs?market=${mkt}`);
  if (!alive()) return;
  const hist = all.filter((r) => r.source === "history");
  const runs = all.filter((r) => (r.source === "history" || !hist.some((h) => h.strategy === r.strategy && String(h.run).startsWith(r.run))) && r.strategy === strat);
  const run = runs.find((r) => r.run === runKey) || runs[0];
  const nav = (m, r) => go(`#/strategies/${strat}/setups/${m}${r ? "/" + encodeURIComponent(r) : ""}`);
  // The latest run only. A picker over every past run listed ~50 entries per
  // strategy, which is screening history rather than anything to act on today;
  // a run's own page is still reachable by URL (.../setups/<market>/<run>).
  const label = run ? `Run ${prettyDate(run.run)}${run.tradeable != null ? ` — ${run.tradeable} tradeable of ${run.rows}` : ""}` : "";
  host.innerHTML = `<div class="page-head sub">${marketSeg(mkt)}${run ? `<span class="run-label">${esc(label)}</span>` : ""}<span class="spacer"></span>
      <button id="run1" title="Run this strategy on today's data (adds a run to the job queue)">Run this strategy…</button></div>
    <div class="chips" id="dec"></div><div id="tbl">${LOADING}</div>`;
  host.querySelectorAll(".mk button").forEach((b) => b.onclick = () => nav(b.dataset.v));
  host.querySelector("#run1").onclick = () => startJob({ title: `Run ${strat} · ${mktInfo(mkt).name}`, targets: ["strategies"], market: mkt, screens: true, pick: strat });
  if (!run) { host.querySelector("#tbl").innerHTML = `<div class="empty"><b>No runs for ${MKT_BADGE[mkt]} yet</b><div class="muted">Run the strategies job, then refresh.</div></div>`; return; }
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
  if (!["all", "tradeable", "watch"].includes(activeDec) && !counts[activeDec]) activeDec = "tradeable";
  const dec = host.querySelector("#dec");
  const isWatch = (r) => /^WATCH/i.test(r[di] || "");
  const nWatch = t.rows.filter(isWatch).length;
  // three chips (Tradeable · Watch · All); the exact decision is a select beside them
  const drawChips = () => {
    const main = ["tradeable", "watch", "all"].includes(activeDec);
    dec.innerHTML = [["tradeable", "Tradeable", nTrade, "trade"], ["watch", "Watch", nWatch, "watch"], ["all", "All", t.rows.length]]
      .map(([v, txt, n, cls]) => `<button class="chip ${cls || ""} ${v === activeDec ? "on" : ""}" data-d="${esc(v)}">${esc(txt)}<span>${n}</span></button>`).join("") +
      `<select id="decsel" title="Filter by the exact decision" class="${main ? "" : "on"}"><option value="">Any decision</option>${decisions.map((d) => `<option value="${esc(d)}" ${d === activeDec ? "selected" : ""}>${esc(d)} (${counts[d]})</option>`).join("")}</select>`;
  };
  // the essentials first; the other ~40 columns are one click away under Columns
  const order = [...SCREEN_COLS.map((c) => t.columns.indexOf(c)).filter((i) => i >= 0)];
  const keep = [...order, ...t.columns.map((_, i) => i).filter((i) => !order.includes(i))];
  const DEFAULT_SHOWN = new Set(["symbol", "name", "peer_group", "group_rs", "decision", "strategy_setup", "price", "entry", "stop", "risk_pct", "target_r"]);
  const draw = () => {
    drawChips();
    const rows = t.rows.filter((r) => activeDec === "all" || (activeDec === "tradeable" ? r[ti] === true : activeDec === "watch" ? isWatch(r) : r[di] === activeDec));
    const tbl = host.querySelector("#tbl");
    if (!rows.length) { tbl.innerHTML = `<div class="empty"><b>Nothing ${activeDec === "tradeable" ? "tradeable" : "here"} in this run</b><div class="muted">Try “All” to see every stock the screen passed to this strategy.</div></div>`; return; }
    dataTable(tbl, keep.map((i) => t.columns[i]), rows.map((r) => keep.map((i) => r[i])), {
      name: `setups_${strat}`, hidden: keep.map((i) => t.columns[i]).filter((c) => !DEFAULT_SHOWN.has(c)),
      rowClick: (row, visible) => {
        const ki = keep.indexOf(si), pi = keep.indexOf(t.columns.indexOf("pattern_name"));
        const setup = pi >= 0 ? { strategy: strat, date: String(run.run).slice(0, 10),
          patterns: Object.fromEntries(visible.filter((r) => r[pi]).map((r) => [r[ki], r[pi]])) } : null;
        openChartFromList(mkt, row[ki], visible.map((r) => r[ki]), `${strat} · ${activeDec === "all" ? "all" : activeDec.toLowerCase()}`,
          location.hash, setup);
      },
    });
  };
  dec.onclick = (e) => { const b = e.target.closest("button[data-d]"); if (b) { activeDec = b.dataset.d; store.set("scrDec", activeDec); draw(); } };
  dec.onchange = (e) => { if (e.target.id === "decsel") { activeDec = e.target.value || "all"; store.set("scrDec", activeDec); draw(); } };
  draw();
}

// ------------------------------------------------------------ reports page

/** A backtest run directory name -> its parts in words. Names are `<start>_<exit policy>[_<option>…][_v<version>-<fp>]`
 *  (backtesting/backtest.py builds them); an unknown token is kept as it is. Not a backtest name -> null. */
function runParts(run) {
  const t = String(run || "").split("_");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(t[0] || "")) return null;
  const out = { start: t[0], exit: "", options: [], version: "", raw: run };
  const exitWords = (x) => {
    const [mode, ...rest] = x.split("-");
    const base = { minervini: "Minervini exits", ma: "moving-average exit", bracket: "stop + target", donchian: "Donchian exit", trail_atr: "ATR trailing stop" }[mode] || mode;
    const bits = rest.map((y) => (/^sma(\d+)$/.test(y) ? `SMA${y.slice(3)}` : y === "noTarget" ? "no target" : y === "withTarget" ? "" : y === "noFail" ? "no failed-breakout exit"
      : /^fail(\d+)$/.test(y) ? `fail ${y.slice(4)}d` : /^(\d+)d$/.test(y) ? `${y.slice(0, -1)} days` : /^([\d.]+)ATR$/.test(y) ? `${y.slice(0, -3)}×ATR` : y)).filter(Boolean);
    return bits.length ? `${base} (${bits.join(", ")})` : base;
  };
  out.exit = t[1] ? exitWords(t[1]) : "";
  const LABEL = { THC: "high-confidence", TOT: "on-trigger" };
  for (const x of t.slice(2)) {
    let m;
    if ((m = x.match(/^v(\d[\d.]*)-([0-9a-f]+)$/))) out.version = `v${m[1]}`;
    else if (x === "spec") out.options.push("spec rules");
    else if (x === "rankrs") out.options.push("ranked by RS");
    else if ((m = x.match(/^rank(\w+)$/))) out.options.push(`ranked by ${m[1]}`);
    else if (x === "mkt") out.options.push("market filter");
    else if ((m = x.match(/^mktc(\d+)$/))) out.options.push(`market filter, ${m[1]}-day confirm`);
    else if ((m = x.match(/^fund(\w+)$/))) out.options.push(`fundamentals: ${m[1]}`);
    else if ((m = x.match(/^grp(\d+)$/))) out.options.push(`group RS ≥ ${m[1]}`);
    else if ((m = x.match(/^rs(\d+)$/))) out.options.push(`RS ≥ ${m[1]}`);
    else if ((m = x.match(/^dv([\d.]+)m$/))) out.options.push(`liquidity ≥ ${m[1]}M/day`);
    else if ((m = x.match(/^pyr([\d.]+)at([\d.]+)pct$/))) out.options.push(`pyramid ${m[1]} at +${m[2]}%`);
    else if ((m = x.match(/^pe(\d+)w([\d.]+)(?:press([\d.]+))?$/))) out.options.push(`progressive exposure (${m[1]} trades, pilot ${m[2]}${m[3] ? `, press at ${m[3]}R` : ""})`);
    else if ((m = x.match(/^risk([\d.]+)pct$/))) out.options.push(`risk ${m[1]}%`);
    else if ((m = x.match(/^cap([\d.]+)pct$/))) out.options.push(`position cap ${m[1]}%`);
    else if ((m = x.match(/^sample(\d+)$/))) out.options.push(`sample of ${m[1]}`);
    else if ((m = x.match(/^only-(\d+)syms$/))) out.options.push(`${m[1]} symbols only`);
    else if (x === "NO-SIGNALS") out.options.push("no signals");
    else if (/^[A-Z]+([-+][A-Z]+)*$/.test(x) && x.split(/[-+]/).every((y) => LABEL[y])) out.options.push(`entries: ${x.split(/[-+]/).map((y) => LABEL[y]).join(" + ")}`);
    else out.options.push(x);
  }
  return out;
}
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
  if (!list.length) { main.innerHTML = `<div class="empty"><b>No reports loaded yet</b><div class="muted">Press <b>Load reports</b> (top right) after a backtest or screening run.</div></div>`; return; }

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
    const cols = ["id", "market", "strategy", ...(isBt ? ["from", "exit", "options", "version", "run"] : ["run"]),
      ...(isBt ? ["cagr %", "excess cagr %", "max dd %", "sharpe"] : ["title"]), "generated"];
    const data = rows.map((r) => {
      const s = r.summary || {}, rp = isBt ? runParts(r.run) : null;
      return [r.id, r.market === "all" ? "—" : r.market.toUpperCase(), r.strategy,
        ...(isBt ? (rp ? [prettyDate(rp.start), rp.exit, rp.options.join(" · "), rp.version] : ["", "", "", ""]) : []), r.run,
        ...(isBt ? [pct(s.cagr), pct(s.excess_cagr), pct(s.max_drawdown), pct(s.sharpe)] : [r.title]), r.generated_at || ""];
    });
    const best = isBt ? rows.reduce((b, r) => (pct(r.summary?.excess_cagr) > pct(b?.summary?.excess_cagr ?? "-1e9") ? r : b), null) : null;
    main.innerHTML = `<div class="page-head"><h1>${KIND_LABEL[st.kind]}</h1><span class="muted">${st.market === "all" ? "Both markets" : st.market.toUpperCase()}${st.strategy === "all" ? "" : " · " + esc(st.strategy)} · ${rows.length} report${rows.length === 1 ? "" : "s"}</span>
      ${best ? `<span class="spacer"></span><span class="muted small">Best excess CAGR: <a href="#/reports/${best.id}">${esc(best.strategy)} · ${esc(best.run)}</a> <b class="${pct(best.summary.excess_cagr) >= 0 ? "pos" : "neg"}">${esc(best.summary.excess_cagr)}</b></span>` : ""}</div><div id="rt"></div>`;
    dataTable(main.querySelector("#rt"), cols, data, {
      hidden: ["id", ...(isBt ? ["run"] : [])], name: `reports_${st.kind}`, sort: ["generated", -1],
      format: { generated: prettyDate },  // sorting still uses the raw ISO value
      rowClick: (row) => go(`#/reports/${row[0]}`), rowHint: "Click a run to open its report",
    });
  }
  draw();
}

/** The funnel, stage by stage, with the stocks at each one.
 *
 * The report's own Funnel table is a flat record of counts. This reads the same run's
 * funnel.json through the API and lets a stage be opened: which stocks were still alive
 * after it, and the names behind each reason the rest stopped. A stage's symbol count is
 * NOT its bar count — a stock is listed once if it reached the stage on any bar, while
 * the funnel counts bars — so the two are labelled separately rather than set side by side.
 */
async function funnelTab(body, id, r, alive) {
  body.innerHTML = LOADING;
  const f = await api(`/api/reports/${id}/funnel`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  if (f.error) { body.innerHTML = `<div class="empty"><b>No funnel for this run</b><div class="muted">${esc(f.error)}</div></div>`; return; }
  const open = new Set();
  const nf = (n) => Number(n).toLocaleString();

  const chip = (sym) => `<button class="sym-chip" data-sym="${esc(sym)}" title="Open ${esc(sym)} on the chart">${esc(sym.replace(/\.NS$/, ""))}</button>`;

  const stageBody = (st, detail) => {
    if (!detail) return `<div class="fn-detail muted small">Loading the names…</div>`;
    if (!detail.recorded) {
      return `<div class="fn-detail muted small">This run recorded counts but not names — it predates per-stage symbols. Re-run the backtest to get them.</div>`;
    }
    const names = detail.symbols || [];
    return `<div class="fn-detail">
      ${names.length ? `<div class="fn-grp"><b>${nf(names.length)} stock${names.length === 1 ? "" : "s"} reached this stage</b>${detail.symbols_truncated ? ` <span class="muted small">— a sample spread across the list, not all of them</span>` : ""}
        <div class="syms">${names.map(chip).join("")}</div></div>` : ""}
      ${(detail.drops || []).filter((d) => d.symbols.length).map((d) => `<div class="fn-grp">
        <b>Stopped here — ${esc(d.reason)}</b> <span class="muted small">${nf(d.count)} ${esc(st.unit)}${d.truncated ? `, showing ${nf(d.symbols.length)} name${d.symbols.length === 1 ? "" : "s"}` : ""}</span>
        <div class="syms">${d.symbols.map(chip).join("")}</div></div>`).join("")}
    </div>`;
  };

  const cache = {};
  const paint = () => {
    body.innerHTML = `<p class="muted small">Every stage counts what reached it. The unit changes down the table — symbols, then bars, then signals — so a drop is only meaningful between two rows counting the same thing. Open a stage for the stocks behind it.</p>
      <div class="fn-list">${f.stages.map((st) => {
        const isOpen = open.has(st.stage);
        return `<div class="fn-stage ${isOpen ? "open" : ""}" data-st="${esc(st.stage)}">
          <button class="fn-head">
            <i class="tw">${isOpen ? "▾" : "▸"}</i>
            <span class="fn-lab">${esc(st.label)}</span>
            <span class="fn-n">${nf(st.count)} <em>${esc(st.unit)}</em></span>
            ${st.symbol_count ? `<span class="fn-sym">${nf(st.symbol_count)} stocks</span>` : ""}
            <span class="fn-why muted small">${(st.drops || []).slice(0, 3).map((d) => `${esc(d.reason)} (${nf(d.count)})`).join(" · ")}${(st.drops || []).length > 3 ? ` · +${(st.drops || []).length - 3} more` : ""}</span>
          </button>
          ${isOpen ? stageBody(st, cache[st.stage]) : ""}</div>`;
      }).join("")}</div>`;
    body.querySelectorAll(".fn-head").forEach((b) => b.onclick = async () => {
      const key = b.parentElement.dataset.st;
      if (open.has(key)) { open.delete(key); paint(); return; }
      open.add(key); paint();
      if (!cache[key]) {
        cache[key] = await api(`/api/reports/${id}/funnel/${key}`).catch((e) => ({ recorded: false, error: e.message, symbols: [], drops: [] }));
        if (!alive()) return;
        paint();
      }
    });
    body.querySelectorAll(".sym-chip").forEach((b) => b.onclick = () => {
      const all = [...b.closest(".syms").querySelectorAll(".sym-chip")].map((x) => x.dataset.sym);
      openChartFromList(r.market, b.dataset.sym, all, `${r.strategy} funnel`, location.hash);
    });
  };
  paint();
}


/** A research document's markdown into `host`: ```pattern fences drawn with real candles (learn.js),
 *  ```series fences charted from stored data (below),
 *  wide tables wrapped, links to sibling *.md files opened as their ingested document. Returns the article. */
function renderResearchMd(host, markdown) {
  host.innerHTML = `<article class="md">${marked.parse(markdown)}</article>`;
  host.querySelectorAll(".md pre > code.language-pattern").forEach((c) => {
    const p = Learn.get(c.textContent.trim());
    if (p) c.parentElement.outerHTML = `<figure class="lp-md">${Learn.svg(p)}<figcaption><a href="#/learn/${p.key}">${esc(p.name)}</a> — open it in Learn</figcaption></figure>`;
  });
  renderSeriesFigures(host);
  renderPayoffFigures(host);
  host.querySelectorAll(".md table").forEach((t) => t.outerHTML = `<div class="md-table">${t.outerHTML}</div>`);
  // Plain-language definitions on the first use of each glossary term. The
  // guides are entered from the hub in any order, so a term explained in one
  // cannot be assumed known in another — see static/glossary.js.
  // `const Glossary` is a script-scope binding, not a window property — test the name itself
  if (typeof Glossary !== "undefined") { Glossary.annotate(host.querySelector("article")); Glossary.bind(); }
  // links between documents are written as filenames ("learn-chart-patterns.md"); show the document's title
  const named = [...host.querySelectorAll('.md a[href$=".md"]')].filter((a) => /\.md$/i.test(a.textContent.trim()));
  if (named.length) api("/api/reports?kind=research").then((runs) => named.forEach((a) => {
    const t = runs.find((x) => x.run === a.getAttribute("href").replace(/\.md$/, ""));
    if (t) { a.title = a.textContent; a.textContent = t.run.startsWith("learn-") ? `the ${guideLabel(t).replace(/: field guide$/, " field guide").replace(/^The /, "")} guide`.replace(/ guide guide$/, " guide") : guideTitle(t); }
  })).catch(() => {});
  host.querySelectorAll('.md a[href$=".md"]').forEach((a) => {
    const f = a.getAttribute("href");
    if (/^(https?:)?\/\//.test(f) || f.includes("/")) return;
    a.onclick = async (e) => {
      e.preventDefault();
      const runs = await api("/api/reports?kind=research").catch(() => []);
      const t = runs.find((x) => x.run === f.replace(/\.md$/, ""));
      if (t) go(t.run.startsWith("learn-") ? `#/learn/${t.run.replace(/^learn-/, "")}` : t.kind === "research" ? `#/research/${t.run}` : `#/reports/${t.id}`);
      else toast("That document is not loaded — click Load reports on the Reports archive", "err");
    };
  });
  return host.querySelector("article");
}

/** ```series fences: a chart of STORED data (index_series, prices) inside a guide, so a claim like "the
 *  10-year doubled while the Nasdaq fell a third" is drawn from the database rather than from memory.
 *  One `key: value` per line:
 *    title:  the figure's heading
 *    from:   / to:   the date range (YYYY-MM-DD; `to` defaults to the latest stored day)
 *    tf:     D | W | M — bar size (default: by span — monthly past 12 years, weekly past 2)
 *    rebase: 100 — every line restated as 100 at `from`, on one scale (compare growth, not levels)
 *    line:   <expr> | <label> | <flags>   (repeat; flags: right, pane2, log, zero, bars — columns, e.g. volume)
 *            expr = a ref, or two joined by " - " (a spread) or " / " (a ratio). A ref is market:SERIES
 *            (index_series or prices) or market:breadth.FIELD (breadth_daily: pct50, pct5, highs, lows, hl,
 *            adv, dec, ad, adline, up4, dn4, up25m, dn25m) or market:grs.LEVEL.Group_Name (a peer group's 1–99 RS
 *            rating; LEVEL industry | sub, underscores for spaces) or market:fund.SYMBOL.FIELD (a company's quarters,
 *            dated when filed: eps, eps_ttm, eps_g, rev_g, revenue, margin; pe is daily close / trailing EPS),
 *            optionally with one transform on the daily data:
 *            @sma50 (any N: its N-day average), @dd (% below its running high), @dist25 (O'Neil distribution
 *            days in the last 25 sessions: down 0.2%+ on higher volume — needs a series with volume), and the
 *            indicators as core/indicators.py computes them: @ema21, @rsi14 (Wilder), @atr14 (Wilder; needs
 *            high/low), @atrp14 (ATR as % of close), @macd / @macdsig / @macdhist (12-26-9), @bbup20 / @bblo20
 *            (2 standard deviations), @chg63 (% change over N sessions), @vol (daily volume), @rvol50 (volume ÷
 *            its N-day average)
 *    band:   <from> <to> | <label>   a shaded period (repeat)
 *    mark:   <date> | <label>         an arrow on the first line (repeat)
 *    caption: what to look at
 *  The data's actual first and last dates are printed under the chart. */
const SERIES_COLORS = ["--series", "--accent", "--info", "--mkt-in", "--up"];
const seriesCache = new Map();
function parseSeriesSpec(text) {
  const s = { lines: [], bands: [], marks: [] };
  for (const raw of text.split("\n")) {
    const m = raw.match(/^\s*([a-z]+)\s*:\s*(.*)$/); if (!m) continue;
    const [, k, v] = m, parts = v.split("|").map((x) => x.trim());
    if (k === "line") s.lines.push({ expr: parts[0], label: parts[1] || parts[0], flags: new Set((parts[2] || "").split(/\s+/).filter(Boolean)) });
    else if (k === "band") { const [a, b] = parts[0].split(/\s+/); s.bands.push({ from: a, to: b, label: parts[1] || "" }); }
    else if (k === "mark") s.marks.push({ date: parts[0], label: parts[1] || "" });
    else s[k] = v.trim();
  }
  return s;
}
/** one stored series' daily values -> [[date, value, volume?]], then its @transform if any */
async function seriesDaily(ref) {
  if (!seriesCache.has(ref)) {
    const [base, mod] = ref.split("@"), [market, symbol] = base.split(":");
    const grs = symbol.match(/^grs\.(industry|sub)\.(.+)$/);
    const raw = symbol.startsWith("breadth.")
      ? api(`/api/breadth-series?market=${encodeURIComponent(market)}&field=${encodeURIComponent(symbol.slice(8))}`).then((r) => r.line.map((c) => [c.time, c.value]))
      : symbol.startsWith("fund.") ? (([, sym, fld]) => api(`/api/fund-series?market=${encodeURIComponent(market)}&symbol=${encodeURIComponent(sym)}&field=${encodeURIComponent(fld)}`)
        .then((r) => r.line.map((c) => [c.time, c.value])))(symbol.match(/^fund\.(.+)\.([a-z_]+)$/))
      : grs ? api(`/api/group-rs-series?market=${encodeURIComponent(market)}&level=${grs[1]}&grp=${encodeURIComponent(grs[2])}`).then((r) => r.line.map((c) => [c.time, c.value]))
      : api(`/api/prices?market=${encodeURIComponent(market)}&symbol=${encodeURIComponent(symbol)}&tf=D&bars=${ALL_BARS}`)
        .then((r) => (r.candles ? r.candles.map((c, i) => [c.time, c.close, r.volume?.[i]?.value, c.high, c.low]) : (r.line || []).map((c) => [c.time, c.value])));
    seriesCache.set(ref, raw.then((xs) => (mod ? seriesTransform(xs, mod, ref) : xs)));
  }
  return seriesCache.get(ref);
}
/** an exponential average as core/indicators.py: alpha 2/(n+1) (ema) or 1/n (Wilder), first n-1 values blank */
function expAvg(vals, n, alpha) {
  let e = null, k = 0;
  return vals.map((v) => { if (v == null || Number.isNaN(v)) return null; e = e == null ? v : alpha * v + (1 - alpha) * e; k++; return k >= n ? e : null; });
}
/** @smaN, @dd, @dist25 and the indicators on daily [[date, value, volume?, high?, low?]] (see the fence grammar above) */
function seriesTransform(xs, mod, ref) {
  const m = mod.match(/^([a-z]+?)(\d*)$/), kind = m?.[1], n = m?.[2] ? +m[2] : null;
  const dates = xs.map((x) => x[0]), close = xs.map((x) => x[1]);
  const keep = (vals) => vals.map((v, i) => (v == null || !Number.isFinite(v) ? null : [dates[i], v])).filter(Boolean);
  const needN = () => { if (!n) throw new Error(`@${mod}: give a length, e.g. @${kind}14`); return n; };
  const smaOf = (vals, k) => { let sum = 0, cnt = 0; return vals.map((v, i) => { sum += v; cnt++; if (i >= k) { sum -= vals[i - k]; cnt--; } return i >= k - 1 ? sum / k : null; }); };
  const sdOf = (vals, k) => vals.map((_, i) => { if (i < k - 1) return null; const w = vals.slice(i - k + 1, i + 1), mu = w.reduce((a, b) => a + b, 0) / k;
    return Math.sqrt(w.reduce((a, b) => a + (b - mu) ** 2, 0) / (k - 1)); });
  if (kind === "ema") return keep(expAvg(close, needN(), 2 / (needN() + 1)));
  if (kind === "rsi") { const k = needN(), g = close.map((v, i) => (i ? Math.max(v - close[i - 1], 0) : null)), l = close.map((v, i) => (i ? Math.max(close[i - 1] - v, 0) : null));
    const ag = expAvg(g, k, 1 / k), al = expAvg(l, k, 1 / k);
    return keep(ag.map((a, i) => (a == null || al[i] == null ? null : al[i] === 0 ? 100 : 100 - 100 / (1 + a / al[i])))); }
  if (kind === "atr" || kind === "atrp") { const k = needN();
    if (!xs.some((x) => x[3] != null)) throw new Error(`${ref}: ATR needs daily highs and lows (a stock or ETF, not an index series)`);
    const tr = xs.map((x, i) => (i ? Math.max(x[3] - x[4], Math.abs(x[3] - xs[i - 1][1]), Math.abs(x[4] - xs[i - 1][1])) : x[3] - x[4]));
    const a = expAvg(tr, k, 1 / k); return keep(kind === "atr" ? a : a.map((v, i) => (v == null ? null : (v / close[i]) * 100))); }
  if (kind === "macd" || kind === "macdsig" || kind === "macdhist") {
    const f = expAvg(close, 12, 2 / 13), sl = expAvg(close, 26, 2 / 27), line = f.map((v, i) => (v == null || sl[i] == null ? null : v - sl[i]));
    const sig = expAvg(line, 9, 2 / 10);
    return keep(kind === "macd" ? line : kind === "macdsig" ? sig : line.map((v, i) => (v == null || sig[i] == null ? null : v - sig[i]))); }
  if (kind === "bbup" || kind === "bblo") { const k = needN(), mid = smaOf(close, k), sd = sdOf(close, k);
    return keep(mid.map((v, i) => (v == null ? null : v + (kind === "bbup" ? 2 : -2) * sd[i]))); }
  if (kind === "chg") { const k = needN(); return keep(close.map((v, i) => (i >= k ? (v / close[i - k] - 1) * 100 : null))); }
  if (kind === "vol" || kind === "rvol") {
    if (!xs.some((x) => x[2])) throw new Error(`${ref}: no volume stored for this series`);
    const vol = xs.map((x) => x[2] ?? 0);
    if (kind === "vol") return keep(vol);
    const avg = smaOf(vol, needN()); return keep(vol.map((v, i) => (avg[i] ? v / avg[i] : null))); }
  const sma = mod.match(/^sma(\d+)$/), dist = mod.match(/^dist(\d+)$/);
  if (sma) { const n = +sma[1]; let sum = 0;
    return xs.map(([d, v], i) => { sum += v; if (i >= n) sum -= xs[i - n][1]; return i >= n - 1 ? [d, sum / n] : null; }).filter(Boolean); }
  if (mod === "dd") { let hi = -Infinity; return xs.map(([d, v]) => { hi = Math.max(hi, v); return [d, (v / hi - 1) * 100]; }); }
  if (dist) {
    if (!xs.some((x) => x[2])) throw new Error(`${ref}: no volume stored for this series`);
    const n = +dist[1], flag = xs.map((x, i) => (i && x[2] && xs[i - 1][2] && x[1] <= xs[i - 1][1] * 0.998 && x[2] > xs[i - 1][2] ? 1 : 0));
    let c = 0; return xs.map(([d], i) => { c += flag[i]; if (i >= n) c -= flag[i - n]; return [d, c]; });
  }
  throw new Error(`unknown transform @${mod}`);
}
/** the period a day falls in, so series on different calendars line up: the week's Friday, the month's end */
function periodKey(d, tf) {
  if (tf === "D") return d;
  const t = new Date(d + "T00:00:00Z");
  if (tf === "W") t.setUTCDate(t.getUTCDate() + ((5 - t.getUTCDay() + 7) % 7));
  else t.setUTCDate(1), t.setUTCMonth(t.getUTCMonth() + 1), t.setUTCDate(0);
  return t.toISOString().slice(0, 10);
}
/** an expression's values, last close per period: Map(periodKey -> value), with .first / .last the actual
 *  first and last trading days used (a period key can be a Friday or month-end after the data stops) */
async function seriesExpr(expr, tf, from, to) {
  const m = expr.match(/^(\S+)\s+([-/])\s+(\S+)$/);
  const per = async (ref) => { const out = new Map();
    for (const [d, v] of await seriesDaily(ref)) if (d >= from && d <= to && v != null) {
      out.set(periodKey(d, tf), v); out.first ??= d; out.last = d; }
    return out; };
  if (!m) return per(expr);
  const [a, b] = await Promise.all([per(m[1]), per(m[3])]), out = new Map();
  for (const [k, va] of a) { const vb = b.get(k); if (vb != null) out.set(k, m[2] === "-" ? va - vb : vb ? va / vb : null); }
  out.first = a.first > b.first ? a.first : b.first; out.last = a.last < b.last ? a.last : b.last;
  return out;
}
/** ```payoff fences: an option or futures position's profit and loss against the underlying's price, at expiry
 *  and optionally some days before it (Black-Scholes, European, no dividends). One `key: value` per line:
 *    title:      the figure's heading
 *    underlying: the current price (a dashed marker)
 *    lot:        units per contract (P&L is per lot); default 1
 *    range:      <low> <high> — the price axis
 *    leg:        buy|sell [<n>x] call|put <strike> @ <premium>   ·   buy|sell [<n>x] future|stock @ <price>  (repeat)
 *    before:     <days>d <iv>% [r <rate>%] — also draw the value that many days before expiry
 *    caption:    what to look at
 *  Breakevens and the maximum profit and loss inside the range are printed under the chart. */
function parsePayoffSpec(text) {
  const s = { legs: [], lot: 1 };
  for (const raw of text.split("\n")) {
    const m = raw.match(/^\s*([a-z]+)\s*:\s*(.*)$/); if (!m) continue;
    const [, k, v] = m;
    if (k === "leg") {
      const L = v.trim().toLowerCase().match(/^(buy|sell)\s+(?:(\d+)x\s+)?(call|put|future|stock)\s+(?:([\d.]+)\s+)?@\s*([\d.]+)$/);
      if (!L) throw new Error(`cannot read leg "${v}"`);
      s.legs.push({ side: L[1] === "buy" ? 1 : -1, n: +(L[2] || 1), kind: L[3], strike: L[4] != null ? +L[4] : null, price: +L[5] });
    } else if (k === "range") { const [a, b] = v.trim().split(/\s+/).map(Number); s.lo = a; s.hi = b; }
    else if (k === "before") { const m2 = v.match(/(\d+)\s*d\s+([\d.]+)\s*%(?:\s+r\s+([\d.]+)\s*%)?/); if (m2) s.before = { days: +m2[1], iv: +m2[2] / 100, r: +(m2[3] ?? 6.5) / 100 }; }
    else if (k === "underlying" || k === "lot") s[k] = +v.trim();
    else s[k] = v.trim();
  }
  if (!s.legs.length) throw new Error("no leg: in the fence");
  return s;
}
function normCdf(x) { const t = 1 / (1 + 0.2316419 * Math.abs(x)), d = 0.3989423 * Math.exp(-x * x / 2);
  const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274)))); return x > 0 ? 1 - p : p; }
function bsPrice(kind, S, K, T, r, v) {
  if (T <= 0 || v <= 0) return Math.max(kind === "call" ? S - K : K - S, 0);
  const d1 = (Math.log(S / K) + (r + v * v / 2) * T) / (v * Math.sqrt(T)), d2 = d1 - v * Math.sqrt(T);
  return kind === "call" ? S * normCdf(d1) - K * Math.exp(-r * T) * normCdf(d2) : K * Math.exp(-r * T) * normCdf(-d2) - S * normCdf(-d1);
}
function payoffAt(spec, S, before) {
  return spec.legs.reduce((sum, l) => {
    let v;
    if (l.kind === "future" || l.kind === "stock") v = S - l.price;
    else v = (before ? bsPrice(l.kind, S, l.strike, before.days / 365, before.r, before.iv)
                     : Math.max(l.kind === "call" ? S - l.strike : l.strike - S, 0)) - l.price;
    return sum + l.side * l.n * v;
  }, 0) * spec.lot;
}
function renderPayoffFigures(host) {
  host.querySelectorAll(".md pre > code.language-payoff").forEach((c) => {
    const fig = document.createElement("figure");
    fig.className = "lp-md lps lpo";
    try {
      const spec = parsePayoffSpec(c.textContent);
      const strikes = spec.legs.map((l) => l.strike ?? l.price), mid = spec.underlying ?? strikes.reduce((a, b) => a + b, 0) / strikes.length;
      const lo = spec.lo ?? Math.min(...strikes) * 0.9, hi = spec.hi ?? Math.max(...strikes) * 1.1, N = 240;
      const xs = Array.from({ length: N + 1 }, (_, i) => lo + (hi - lo) * i / N);
      const exp = xs.map((x) => payoffAt(spec, x)), pre = spec.before ? xs.map((x) => payoffAt(spec, x, spec.before)) : null;
      const all = exp.concat(pre || []), ymin = Math.min(0, ...all), ymax = Math.max(0, ...all), pad = (ymax - ymin) * 0.08 || 1;
      const W = 720, H = 300, L = 70, R = 16, T = 12, B = 34;
      const X = (x) => L + (x - lo) / (hi - lo) * (W - L - R), Y = (y) => T + (ymax + pad - y) / (ymax - ymin + 2 * pad) * (H - T - B);
      const path = (ys) => ys.map((y, i) => `${i ? "L" : "M"}${X(xs[i]).toFixed(1)},${Y(y).toFixed(1)}`).join("");
      const fmtN = (v) => Math.abs(v) >= 1000 ? Math.round(v).toLocaleString("en-IN") : (+v.toFixed(1)).toLocaleString("en-IN");
      const ticks = Array.from({ length: 6 }, (_, i) => lo + (hi - lo) * i / 5);
      const yt = Array.from({ length: 5 }, (_, i) => ymin - pad + (ymax - ymin + 2 * pad) * i / 4);
      // breakevens: where the expiry line crosses zero
      const be = [];
      for (let i = 1; i <= N; i++) if ((exp[i - 1] < 0) !== (exp[i] < 0)) be.push(xs[i - 1] + (xs[i] - xs[i - 1]) * (0 - exp[i - 1]) / (exp[i] - exp[i - 1]));
      const svg = `<svg class="lpo-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(spec.title || "payoff")}">
        ${yt.map((v) => `<line class="lpo-grid" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}"/><text class="lpo-t" x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${fmtN(v)}</text>`).join("")}
        ${ticks.map((v) => `<text class="lpo-t" x="${X(v)}" y="${H - 12}" text-anchor="middle">${fmtN(v)}</text>`).join("")}
        <path class="lpo-gain" d="${path(exp.map((y) => Math.max(y, 0)))}L${X(hi)},${Y(0)}L${X(lo)},${Y(0)}Z"/>
        <path class="lpo-loss" d="${path(exp.map((y) => Math.min(y, 0)))}L${X(hi)},${Y(0)}L${X(lo)},${Y(0)}Z"/>
        <line class="lpo-zero" x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}"/>
        ${pre ? `<path class="lpo-pre" d="${path(pre)}"/>` : ""}
        <path class="lpo-exp" d="${path(exp)}"/>
        ${spec.underlying ? `<line class="lpo-spot" x1="${X(spec.underlying)}" x2="${X(spec.underlying)}" y1="${T}" y2="${H - B}"/><text class="lpo-t" x="${X(spec.underlying) + 4}" y="${T + 10}">now ${fmtN(spec.underlying)}</text>` : ""}
        ${be.map((b) => `<circle class="lpo-be" cx="${X(b)}" cy="${Y(0)}" r="3.5"/>`).join("")}
      </svg>`;
      const maxP = Math.max(...exp), maxL = Math.min(...exp);
      // unlimited when the extreme sits at an edge of the axis and the line is still sloping there (a capped
      // spread is flat at the edge: its maximum is its maximum)
      const edge = (arr, v) => (Math.abs(arr[0] - v) < 1e-9 && Math.abs(arr[1] - arr[0]) > 1e-9) || (Math.abs(arr[N] - v) < 1e-9 && Math.abs(arr[N] - arr[N - 1]) > 1e-9);
      fig.innerHTML = `${spec.title ? `<div class="lps-t">${esc(spec.title)}</div>` : ""}
        <div class="lps-leg small"><span><i style="background:${cssVar("--accent")}"></i>At expiry</span>${pre ? `<span><i style="background:${cssVar("--info")}"></i>${spec.before.days} days before expiry (implied volatility ${(spec.before.iv * 100).toFixed(0)}%)</span>` : ""}
          <span>Profit / loss per ${spec.lot > 1 ? `lot of ${spec.lot}` : "unit"}</span></div>${svg}
        <div class="small muted lpo-sum">${spec.legs.map((l) => `${l.side > 0 ? "Buy" : "Sell"} ${l.n > 1 ? l.n + "× " : ""}${l.kind}${l.strike != null ? " " + fmtN(l.strike) : ""} @ ${fmtN(l.price)}`).join(" · ")}
          <br>Breakeven${be.length === 1 ? "" : "s"}: ${be.length ? be.map(fmtN).join(", ") : "none in this range"} · Max profit: ${edge(exp, maxP) && maxP > 0 ? "keeps growing beyond this range" : fmtN(maxP)} · Max loss: ${edge(exp, maxL) && maxL < 0 ? "keeps growing beyond this range" : fmtN(maxL)}</div>
        ${spec.caption ? `<figcaption>${esc(spec.caption)}</figcaption>` : ""}`;
    } catch (e) {
      fig.innerHTML = `<div class="muted small">Payoff diagram unavailable: ${esc(e.message)}</div>`;
    }
    c.parentElement.replaceWith(fig);
  });
}

function renderSeriesFigures(host) {
  host.querySelectorAll(".md pre > code.language-series").forEach((c) => {
    const spec = parseSeriesSpec(c.textContent);
    const fig = document.createElement("figure");
    fig.className = "lp-md lps";
    fig.innerHTML = `${spec.title ? `<div class="lps-t">${esc(spec.title)}</div>` : ""}<div class="lps-leg small"></div>
      <div class="lps-chart" style="height:${spec.lines.some((l) => l.flags.has("pane2")) ? 400 : 300}px"></div>
      <figcaption>${spec.caption ? `${esc(spec.caption)} ` : ""}<span class="lps-src"></span></figcaption>`;
    c.parentElement.replaceWith(fig);
    drawSeriesFigure(fig, spec).catch((e) => { fig.querySelector(".lps-chart").outerHTML = `<div class="muted small">Chart unavailable: ${esc(e.message)}</div>`; });
  });
}
async function drawSeriesFigure(fig, spec) {
  if (!spec.lines.length) throw new Error("no line: in the fence");
  const from = spec.from || "1900-01-01", to = spec.to || "9999-12-31";
  const spanYears = ((to < "9999" ? Date.parse(to) : Date.now()) - Date.parse(from)) / 3.156e10;
  const tf = spec.tf || (spanYears > 12 ? "M" : spanYears > 2 ? "W" : "D");
  const data = await Promise.all(spec.lines.map((l) => seriesExpr(l.expr, tf, from, to)));
  const missing = spec.lines.filter((l, i) => !data[i].size).map((l) => l.expr);
  if (missing.length) throw new Error(`no stored data for ${missing.join(", ")} in this range`);
  const el_ = fig.querySelector(".lps-chart");
  const chart = LC.createChart(el_, { autoSize: true, ...chartTheme(), handleScroll: false, handleScale: false,
    leftPriceScale: { visible: spec.lines.some((l) => !l.flags.has("right") && !l.flags.has("pane2")) && spec.lines.some((l) => l.flags.has("right")), borderColor: cssVar("--line-2") } });
  { const prev = cleanup; cleanup = () => { chart.remove(); prev(); }; }
  const times = [...new Set(data.flatMap((d) => [...d.keys()]))].sort();
  const series = spec.lines.map((l, i) => {
    let pts = [...data[i]].sort((a, b) => (a[0] < b[0] ? -1 : 1));
    if (spec.rebase) { const base = pts[0][1]; pts = pts.map(([t, v]) => [t, (v / base) * +spec.rebase]); }
    const pane = l.flags.has("pane2") ? 1 : 0;
    const scale = pane ? "right" : spec.lines.some((x) => x.flags.has("right")) && !l.flags.has("right") ? "left" : "right";
    const s = l.flags.has("bars")
      ? chart.addSeries(LC.HistogramSeries, { color: cssVar(SERIES_COLORS[i % SERIES_COLORS.length]), priceScaleId: scale, priceLineVisible: false, lastValueVisible: false,
        priceFormat: { type: "custom", minMove: 1, formatter: (v) => Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(v) } }, pane)
      : chart.addSeries(LC.LineSeries, { color: cssVar(SERIES_COLORS[i % SERIES_COLORS.length]), lineWidth: i ? 1.5 : 2,
        priceScaleId: scale, priceLineVisible: false, lastValueVisible: true, title: "" }, pane);
    s.setData(pts.map(([t, v]) => ({ time: t, value: +v.toFixed(4) })));
    if (l.flags.has("zero")) s.createPriceLine({ price: 0, color: cssVar("--line-3"), lineWidth: 1, lineStyle: 2, axisLabelVisible: false });
    s.lps = { scale, pane };
    return s;
  });
  // scale modes only once every pane exists: a pane created later copies the first pane's scale options
  series.forEach((s, i) => { const l = spec.lines[i];
    chart.priceScale(s.lps.scale, s.lps.pane).applyOptions({ mode: l.flags.has("log") ? LC.PriceScaleMode.Logarithmic : LC.PriceScaleMode.Normal }); });
  if (spec.lines.some((l) => l.flags.has("pane2"))) chart.panes()[1]?.setHeight(130);
  // shaded periods: a full-height area on a hidden scale, one series per period and pane (an area series
  // joins across gaps, so two periods in one series would shade everything between them)
  const panes = [...new Set(spec.lines.map((l) => (l.flags.has("pane2") ? 1 : 0)))];
  for (const band of spec.bands) {
    const lo = periodKey(band.from, tf), hi = periodKey(band.to || "9999-12-31", tf);
    const pts = times.filter((t) => t >= lo && t <= hi);
    if (!pts.length) continue;
    for (const pane of panes) {
      const h = chart.addSeries(LC.AreaSeries, { priceScaleId: `band${pane}`, lineVisible: false, topColor: cssVar("--warn-soft"), bottomColor: cssVar("--warn-soft"),
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
        autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 1 } }) }, pane);
      h.priceScale().applyOptions({ visible: false, scaleMargins: { top: 0, bottom: 0 } });
      h.setData(pts.map((t) => ({ time: t, value: 1 })));
    }
  }
  if (spec.marks.length) {
    const ts = [...data[0].keys()].sort();
    LC.createSeriesMarkers(series[0], spec.marks.map((m) => ({ time: ts.find((t) => t >= periodKey(m.date, tf)) || ts[ts.length - 1],
      position: "aboveBar", shape: "arrowDown", color: cssVar("--accent"), text: m.label })).sort((a, b) => (a.time < b.time ? -1 : 1)));
  }
  chart.timeScale().fitContent();
  // fit again whenever the plot's width changes: a chart drawn while its page is hidden starts at zero width,
  // and the price axes only take their width once their labels are drawn, after this first fit — the box
  // itself does not resize then, so watch the time scale, not the box (the user cannot zoom these charts,
  // so re-fitting never undoes anything)
  const refit = () => chart.timeScale().fitContent();
  chart.timeScale().subscribeSizeChange(refit);
  { const prev = cleanup; cleanup = () => { chart.timeScale().unsubscribeSizeChange(refit); prev(); }; }
  const fmtD = (d) => new Date(d + "T00:00:00Z").toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
  fig.querySelector(".lps-leg").innerHTML = spec.lines.map((l, i) => `<span><i style="background:${cssVar(SERIES_COLORS[i % SERIES_COLORS.length])}"></i>${esc(l.label)}${l.flags.has("right") && !l.flags.has("pane2") ? " (right axis)" : ""}${l.flags.has("log") ? " · log scale" : ""}</span>`).join("")
    + [...new Set(spec.bands.map((b) => b.label).filter(Boolean))].map((x) => `<span><i class="band"></i>${esc(x)}</span>`).join("");
  const first = data.map((d) => d.first).sort()[0], last = data.map((d) => d.last).sort().pop();
  fig.querySelector(".lps-src").textContent = `Stored data, ${fmtD(first)} – ${fmtD(last)}, ${{ D: "daily", W: "weekly", M: "monthly" }[tf]} closes${spec.rebase ? `, rebased to ${spec.rebase}` : ""}.`;
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
  const tabs = [["report", "Report"], ...(r.kind === "backtest" ? [["funnel", "Funnel"]] : []),
    ...(has("equity") ? [["equity", "Equity curve"]] : []), ...(has("trades") ? [["trades", `Trades (${r.tables.find((t) => t.name === "trades").rows})`]] : []),
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
          openChartFromList(r.market, row[si], visible.map((x) => x[si]), `${r.strategy} trades`, location.hash, null,
            name === "trades" ? { run: id, strategy: r.strategy } : null);
        },
      } : {}),
    };
  };
  if (tab === "report") {
    renderResearchMd(body, r.markdown);
  } else if (tab === "funnel") {
    await funnelTab(body, id, r, alive);
  } else if (tab === "equity") {
    body.innerHTML = `<div id="eqchart"></div><div id="eqt"></div>`;
    const t = await api(`/api/reports/${id}/tables/equity`);
    if (!alive()) return;
    const chart = LC.createChart(body.querySelector("#eqchart"), { autoSize: true, ...chartTheme() });
    const ci = (n) => t.columns.indexOf(n), ei = ci("equity") >= 0 ? ci("equity") : 1, di = ci("drawdown_pct");
    const series = (idx) => t.rows.filter((x) => x[idx] != null).map((x) => ({ time: String(x[0]).slice(0, 10), value: x[idx] }));
    chart.addSeries(LC.AreaSeries, { lineColor: cssVar("--series"), topColor: alpha(cssVar("--series"), .2), bottomColor: alpha(cssVar("--series"), 0), lineWidth: 2, title: "Equity" }, 0).setData(series(ei));
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
// ------------------------------------------------------------- notes page

/** Today in the READER'S timezone, as YYYY-MM-DD.
 *
 *  `new Date().toISOString()` is UTC, so for anyone east of Greenwich it returns YESTERDAY
 *  between midnight and the offset -- a journal opened at 00:19 IST was titled for the previous
 *  day, and the Insert-date button agreed with it. A note's date is a local-calendar fact.
 */
const todayLocal = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

const NOTE_TEMPLATES = {
  blank: { label: "Blank note", make: (sym) => ({ title: sym ? `${sym.symbol.replace(/\.NS$/, "")} — notes` : "", body: "", tags: [] }) },
  journal: { label: "Daily journal", make: () => { const d = todayLocal(); return { title: `Journal — ${longDate(d)}`, tags: ["journal"],
    body: "## Market — India\n- **Regime:** advance / distribution / correction / basing / recovery — and why\n- **Breadth vs price:** confirming or diverging, which way\n- **Character:** broad or concentrated · washout or grind\n- **Leadership:** offensive or defensive · rotating toward what\n- **Volatility:** expanding or draining · what that permits\n- **Call:**\n- **Changes my mind:**\n\n## Market — US\n- **Regime:**\n- **Breadth vs price:**\n- **Character:**\n- **Leadership:**\n- **Volatility:**\n- **Call:**\n- **Changes my mind:**\n\n## Cross-market\n- **Stronger, and why:**\n\n## Positions\n| Stock | Plan | Action |\n|---|---|---|\n|  |  |  |\n\n## Watching\n- \n\n## Lessons\n- \n" }; } },
  plan: { label: "Trade plan", make: (sym) => ({ title: `Plan — ${sym ? sym.symbol.replace(/\.NS$/, "") : ""}`, tags: ["plan"],
    body: "## Setup\n\n## Entry / stop / target\n- Entry:\n- Stop:\n- Target:\n- Size / risk:\n\n## Why now\n\n## What would prove me wrong\n" }) },
  review: { label: "Trade review", make: (sym) => ({ title: `Review — ${sym ? sym.symbol.replace(/\.NS$/, "") : ""}`, tags: ["review"],
    body: "## What happened\n\n## What I did well\n\n## What I'd do differently\n\n## Lesson\n" }) },
};

/** Notes: list + search on the left, a Markdown editor with live preview on the right; saves as you type. */
/** The rich editor's HTML back to Markdown (notes are stored as Markdown: search, the chart's notes panel
 *  and "Copy as Markdown" read it). Covers what the editor produces: paragraphs, headings, bold / italic /
 *  strikethrough / code, links, bullet / numbered / check lists (nested), quotes, code blocks, rules, tables. */
function htmlToMd(root) {
  const inline = (n) => [...n.childNodes].map((c) => {
    if (c.nodeType === 3) return c.textContent.replace(/\u00a0/g, " ");
    if (c.nodeType !== 1) return "";
    const t = c.tagName.toLowerCase(), x = inline(c);
    if (t === "br") return "\n";
    if ((t === "strong" || t === "b") && x.trim()) return `**${x}**`;
    if ((t === "em" || t === "i") && x.trim()) return `_${x}_`;
    if ((t === "s" || t === "strike" || t === "del") && x.trim()) return `~~${x}~~`;
    if (t === "code") return "`" + c.textContent + "`";
    if (t === "a") return `[${x || c.getAttribute("href")}](${c.getAttribute("href") || ""})`;
    if (t === "img") return `![${c.getAttribute("alt") || ""}](${c.getAttribute("src") || ""})`;
    if (t === "input") return "";
    if (BLOCK.has(t)) return "\n\n" + blockOf(c).trim() + "\n\n";
    return x;
  }).join("");
  const list = (n, ind) => [...n.children].filter((li) => li.tagName === "LI").map((li, i) => {
    const box = li.querySelector(":scope > input[type=checkbox]") || li.querySelector(":scope > p > input[type=checkbox]");
    const mark = n.tagName === "OL" ? `${i + 1}. ` : "- ";
    const own = document.createElement("div");
    [...li.childNodes].forEach((c) => { if (!(c.nodeType === 1 && /^(UL|OL)$/.test(c.tagName))) own.append(c.cloneNode(true)); });
    const text = inline(own).replace(/\n+/g, " ").trim();
    const sub = [...li.children].filter((c) => /^(UL|OL)$/.test(c.tagName)).map((c) => list(c, ind + (n.tagName === "OL" ? "   " : "  "))).join("\n");
    return `${ind}${mark}${box ? (box.checked ? "[x] " : "[ ] ") : ""}${text}` + (sub ? "\n" + sub : "");
  }).join("\n");
  const BLOCK = new Set(["ul", "ol", "p", "div", "blockquote", "pre", "table", "h1", "h2", "h3", "h4", "h5", "h6", "hr"]);
  const block = (n) => [...n.childNodes].map((c) => {
    if (c.nodeType === 3) return c.textContent.trim() ? c.textContent.replace(/\u00a0/g, " ") + "\n\n" : "";
    return c.nodeType === 1 ? blockOf(c) : "";
  }).join("");
  // one element as Markdown block(s); a paragraph or div holding block elements (a list the browser put
  // inside a <p>) is treated as a container
  const blockOf = (c) => {
    const t = c.tagName.toLowerCase();
    if ((t === "p" || t === "div") && [...c.children].some((k) => BLOCK.has(k.tagName.toLowerCase()))) return block(c);
    if (/^h[1-6]$/.test(t)) return "#".repeat(+t[1]) + " " + inline(c).trim() + "\n\n";
    if (t === "ul" || t === "ol") return list(c, "") + "\n\n";
    if (t === "blockquote") return block(c).trim().split("\n").map((l) => "> " + l).join("\n") + "\n\n";
    if (t === "pre") return "```\n" + c.textContent.replace(/\n$/, "") + "\n```\n\n";
    if (t === "hr") return "---\n\n";
    if (t === "table") {
      const rows = [...c.querySelectorAll("tr")].map((tr) => [...tr.children].map((td) => inline(td).replace(/\|/g, "\\|").replace(/\n/g, " ").trim()));
      if (!rows.length) return "";
      const w = Math.max(...rows.map((r) => r.length)), pad = (r) => [...r, ...Array(w - r.length).fill("")];
      return [pad(rows[0]), Array(w).fill("---"), ...rows.slice(1).map(pad)].map((r) => `| ${r.join(" | ")} |`).join("\n") + "\n\n";
    }
    if (t === "br") return "\n";
    const x = inline(c).trim();
    return x ? x + "\n\n" : "";
  };
  return block(root).replace(/\n{3,}/g, "\n\n").trim() + "\n";
}

async function notesPage(alive, args) {
  document.title = "Notes · Trading";
  let filter = { q: store.get("notesQ", ""), tag: store.get("notesTag", null), market: null, symbol: null };
  let openId = null, pendingNew = null;
  if (args[0] === "sym") { filter.market = args[1]; filter.symbol = args[2]; }
  else if (args[0] === "new") pendingNew = args[1] && args[2] ? { market: args[1], symbol: args[2] } : {};
  else if (args[0]) openId = +args[0];
  if (pendingNew) {  // create, then open it (an untouched new note is deleted again on leaving)
    const sym = pendingNew.symbol ? pendingNew : null;
    const n = await api("/api/notes", jsonReq("POST", { ...NOTE_TEMPLATES.blank.make(sym), symbols: sym ? [sym] : [] }));
    store.set("notesFresh", n.id);
    return go(`#/notes/${n.id}`);
  }
  const mode = () => (store.get("notesEditor", "rich") === "markdown" ? "markdown" : "rich");
  $view.innerHTML = `<div class="notes">
      <aside class="notes-list">
        <div class="nl-head"><label class="filter"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input id="nq" placeholder="Search notes" spellcheck="false"></label>
          <button class="primary" id="nnew" title="New note">New</button></div>
        <div class="nl-filter" id="nfilter"></div>
        <div class="nl-items" id="nitems">${LOADING}</div>
      </aside>
      <section class="notes-ed" id="ned"><div class="empty"><b>Select a note, or create one</b><div class="muted">Notes are saved as you type. Format with the toolbar, or type # for a heading, - for a list, [] for a checklist.</div></div></section>
    </div>`;
  const $q = $view.querySelector("#nq");
  $q.value = filter.q;
  let list = [];
  const sym = (x) => `<span class="mkt">${MKT_BADGE[x.market]}</span>${esc(x.symbol.replace(/\.NS$/, ""))}`;
  async function loadList() {
    const p = new URLSearchParams();
    if (filter.q) p.set("q", filter.q);
    if (filter.tag) p.set("tag", filter.tag);
    if (filter.symbol) { p.set("market", filter.market); p.set("symbol", filter.symbol); }
    const r = await api(`/api/notes?${p}`).catch(() => ({ notes: [], tags: [] }));
    if (!alive()) return;
    list = r.notes;
    $view.querySelector("#nfilter").innerHTML = `${filter.symbol ? `<span class="chip on">${sym(filter)} <a href="#/notes" title="Clear">×</a></span>` : ""}
      ${r.tags.map((t) => `<button class="chip ${t.tag === filter.tag ? "on" : ""}" data-t="${esc(t.tag)}">#${esc(t.tag)}<span>${t.count}</span></button>`).join("")}`;
    $view.querySelectorAll("#nfilter [data-t]").forEach((b) => b.onclick = () => { filter.tag = filter.tag === b.dataset.t ? null : b.dataset.t; store.set("notesTag", filter.tag); loadList(); });
    $view.querySelector("#nitems").innerHTML = list.length ? list.map((n) => `<a class="nl-item ${n.id === openId ? "cur" : ""}" href="#/notes/${n.id}">
        <div class="nl-t">${n.pinned ? '<span class="pin" title="Pinned">●</span>' : ""}<b>${esc(n.title || "Untitled")}</b><span class="muted small">${ago(n.updated_at)}</span></div>
        ${n.snippet ? `<div class="muted small nl-s">${esc(n.snippet)}</div>` : ""}
        ${n.tags.length || n.symbols.length ? `<div class="nl-m">${n.symbols.map((x) => `<span class="nl-sym">${sym(x)}</span>`).join("")}${n.tags.map((t) => `<span class="nl-tag">#${esc(t)}</span>`).join("")}</div>` : ""}</a>`).join("")
      : `<div class="muted small nl-none">${filter.q || filter.tag || filter.symbol ? "No notes match." : "No notes yet — click New."}</div>`;
  }
  let qt;
  $q.oninput = () => { clearTimeout(qt); qt = setTimeout(() => { filter.q = $q.value.trim(); store.set("notesQ", filter.q); loadList(); }, 250); };
  $view.querySelector("#nnew").onclick = (e) => {
    const r = e.currentTarget.getBoundingClientRect(), s0 = filter.symbol ? { market: filter.market, symbol: filter.symbol } : null;
    contextMenu(r.left, r.bottom + 4, s0 ? `New note for ${s0.symbol.replace(/\.NS$/, "")}` : "New note", Object.entries(NOTE_TEMPLATES).map(([k, t]) => ({ label: t.label, fn: async () => {
      const n = await api("/api/notes", jsonReq("POST", { ...t.make(s0), symbols: s0 ? [s0] : [] }));
      if (k === "blank") store.set("notesFresh", n.id);
      go(`#/notes/${n.id}`);
    } })));
  };
  await loadList();
  if (!openId) return;

  // ---- editor
  const n = await api(`/api/notes/${openId}`).catch(() => null);
  if (!alive()) return;
  const ed = $view.querySelector("#ned");
  if (!n) { ed.innerHTML = '<div class="empty"><b>Note not found</b><div class="muted">It may have been deleted.</div></div>'; return; }
  let note = { ...n }, dirty = false, saving = false, timer;
  ed.innerHTML = `<div class="ne-head">
      <input class="ne-title" id="nt" placeholder="Title" value="${esc(note.title)}">
      <span class="muted small ne-status" id="nst">Saved</span>
      <button class="ibtn ${note.pinned ? "on" : ""}" id="npin" title="Pin to the top">${note.pinned ? "●" : "○"}</button>
      <button class="ibtn" id="nmore" title="More">⋯</button></div>
    <div class="ne-meta">
      <div class="ne-syms" id="nsyms"></div>
      <div class="search ne-symadd"><input id="nsymin" placeholder="+ link a stock" spellcheck="false"><ul hidden></ul></div>
      <input class="ne-tags" id="ntags" placeholder="tags, comma separated" value="${esc(note.tags.join(", "))}">
    </div>
    <div class="ne-bar">
      <div class="ne-tools rich-tools">
        <select data-t="block" title="Text style"><option value="p">Text</option><option value="h1">Heading 1</option><option value="h2">Heading 2</option><option value="h3">Heading 3</option></select>
        ${[["bold", "<b>B</b>", "Bold (⌘B)"], ["italic", "<i>I</i>", "Italic (⌘I)"], ["strike", "<s>S</s>", "Strikethrough"], ["sep"], ["ul", "•≡", "Bullet list"], ["ol", "1≡", "Numbered list"], ["task", "☑", "Checklist"], ["sep"],
           ["quote", "❝", "Quote"], ["code", "&lt;/&gt;", "Code"], ["link", "🔗", "Link (⌘K)"], ["table", "⊞", "Table"], ["hr", "―", "Divider"], ["date", "📅", "Insert today's date"], ["sep"], ["clear", "T̸", "Clear formatting"]]
          .map(([k, t, title]) => k === "sep" ? '<span class="tsep"></span>' : `<button data-t="${k}" title="${title}">${t}</button>`).join("")}</div>
      <div class="ne-tools md-tools">${[["b", "B", "Bold (⌘B)"], ["i", "I", "Italic (⌘I)"], ["h", "H", "Heading"], ["ul", "•", "Bullet list"], ["task", "☐", "Checklist item"], ["q", "❝", "Quote"], ["code", "</>", "Code"], ["link", "🔗", "Link"], ["table", "⊞", "Table"], ["date", "📅", "Insert today's date"]]
        .map(([k, t, title]) => `<button data-t="${k}" title="${title}">${t}</button>`).join("")}</div>
      <span class="spacer"></span>${segmented([["rich", "Rich"], ["markdown", "Markdown"]], mode(), "nmode")}</div>
    <div class="ne-body mode-${mode()}"><div class="ne-rich md" id="nrich" contenteditable="true" spellcheck="true" data-ph="Start writing…"></div>
      <textarea id="nbody" spellcheck="true" placeholder="Write in Markdown…">${esc(note.body)}</textarea><div class="ne-preview md" id="nprev"></div></div>
    <div class="muted small ne-foot">Created ${clock(note.created_at)} · <span id="nupd">updated ${clock(note.updated_at)}</span></div>`;
  const $t = ed.querySelector("#nt"), $b = ed.querySelector("#nbody"), $prev = ed.querySelector("#nprev"), $st = ed.querySelector("#nst");
  const renderPrev = () => { $prev.innerHTML = $b.value.trim() ? marked.parse($b.value) : '<div class="muted small">Nothing to preview.</div>'; };
  const renderSyms = () => {
    ed.querySelector("#nsyms").innerHTML = note.symbols.map((x, i) => `<span class="ne-sym"><a href="#/chart/${x.market}/${encodeURIComponent(x.symbol)}" title="Open chart">${sym(x)}</a><button data-i="${i}" title="Unlink">×</button></span>`).join("");
    ed.querySelectorAll(".ne-sym button").forEach((b) => b.onclick = () => { note.symbols.splice(+b.dataset.i, 1); renderSyms(); changed(); });
  };
  async function save() {
    if (!dirty || saving) return;
    saving = true; dirty = false; $st.textContent = "Saving…";
    const tags = ed.querySelector("#ntags").value.split(",").map((x) => x.trim()).filter(Boolean);
    try {
      const r = await api(`/api/notes/${note.id}`, jsonReq("PUT", { title: $t.value, body: $b.value, tags, symbols: note.symbols, pinned: note.pinned }));
      note = { ...note, ...r }; $st.textContent = "Saved"; store.set("notesFresh", null);
      ed.querySelector("#nupd").textContent = `updated ${clock(r.updated_at)}`;
      loadList();
    } catch (err) { dirty = true; $st.textContent = "Not saved — retrying"; toast(err.message, "err"); }
    finally { saving = false; if (dirty) { clearTimeout(timer); timer = setTimeout(save, 1500); } }
  }
  function changed() { dirty = true; $st.textContent = "Editing…"; clearTimeout(timer); timer = setTimeout(save, 800); }
  renderPrev(); renderSyms();
  $t.oninput = changed; ed.querySelector("#ntags").oninput = changed;
  $b.oninput = () => { renderPrev(); changed(); };
  // formatting helpers: wrap the selection, or prefix the current line(s)
  const wrap = (a, b = a, ph = "text") => { const s0 = $b.selectionStart, s1 = $b.selectionEnd, sel = $b.value.slice(s0, s1) || ph;
    $b.setRangeText(a + sel + b, s0, s1, "end"); $b.selectionStart = s0 + a.length; $b.selectionEnd = s0 + a.length + sel.length; $b.focus(); $b.oninput(); };
  const prefix = (p) => { const s0 = $b.value.lastIndexOf("\n", $b.selectionStart - 1) + 1, s1 = $b.selectionEnd;
    const block = $b.value.slice(s0, s1).split("\n").map((l) => p + l).join("\n"); $b.setRangeText(block, s0, s1, "end"); $b.focus(); $b.oninput(); };
  const insert = (t) => { $b.setRangeText(t, $b.selectionStart, $b.selectionEnd, "end"); $b.focus(); $b.oninput(); };
  ed.querySelector(".md-tools").onclick = (e) => {
    const k = e.target.closest("[data-t]")?.dataset.t; if (!k) return;
    ({ b: () => wrap("**"), i: () => wrap("_"), h: () => prefix("## "), ul: () => prefix("- "), task: () => prefix("- [ ] "), q: () => prefix("> "),
       code: () => wrap("`"), link: () => wrap("[", "](https://)", "link text"),
       table: () => insert("\n| Column | Column |\n|---|---|\n|  |  |\n"), date: () => insert(longDate(todayLocal())) })[k]();
  };
  $b.onkeydown = (e) => {
    const mod = e.metaKey || e.ctrlKey;
    if (mod && e.key === "b") { e.preventDefault(); wrap("**"); }
    else if (mod && e.key === "i") { e.preventDefault(); wrap("_"); }
    else if (mod && e.key === "s") { e.preventDefault(); dirty = true; save(); }
    else if (e.key === "Tab") { e.preventDefault(); insert("  "); }
    e.stopPropagation();  // keep the app's single-key shortcuts out of the editor
  };
  $t.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); (mode() === "rich" ? $r : $b).focus(); } e.stopPropagation(); };
  // ---- the rich editor: edits HTML (rendered from the Markdown), saves Markdown
  const $r = ed.querySelector("#nrich");
  const loadRich = () => {
    $r.innerHTML = $b.value.trim() ? marked.parse($b.value) : "<p><br></p>";
    $r.querySelectorAll("input[type=checkbox]").forEach((c) => { c.removeAttribute("disabled"); c.closest("li")?.classList.add("task"); });
  };
  const richChanged = () => { $b.value = htmlToMd($r); renderPrev(); changed(); };
  document.execCommand("defaultParagraphSeparator", false, "p");
  const cmd = (c, v = null) => { $r.focus(); document.execCommand(c, false, v); richChanged(); syncTools(); };
  /** execCommand("indent") emits a nested list as a SIBLING of the item it belongs to --
   *  `<ul><li>a</li><ul><li>b</li></ul></ul>` -- which is malformed: a list may only contain
   *  `<li>`. htmlToMd walks `li` children only, so the nested items are skipped and the text is
   *  LOST on save. Moving the list inside the preceding `<li>` gives the standard shape
   *  `<li>a<ul><li>b</li></ul></li>`, which htmlToMd already serialises with its indent level.
   */
  const fixNesting = () => {
    let changed = false;
    for (const sub of $r.querySelectorAll("ul > ul, ul > ol, ol > ul, ol > ol")) {
      const host = sub.previousElementSibling;
      if (host && host.tagName === "LI") { host.appendChild(sub); changed = true; }
    }
    // OUTDENT is malformed the other way: lifting an item out of a nested list leaves
    // `<li>A<ul>..</ul><li>C</li></li>` -- an <li> inside an <li>, which is invalid and which
    // htmlToMd reads as one item, merging the text into "- AC". The lifted item belongs after
    // its host, in the host's own list.
    for (const inner of $r.querySelectorAll("li > li")) {
      const host = inner.parentElement;
      host.after(inner);
      changed = true;
    }
    // Indenting a second item in a row leaves TWO adjacent lists inside one <li> rather than one
    // list of two items. Both serialise to the same Markdown, but they are separate blocks to a
    // renderer -- and to the next indent -- so they are merged.
    for (const l of $r.querySelectorAll("li > ul, li > ol")) {
      const prev = l.previousElementSibling;
      if (prev && prev.tagName === l.tagName) {
        while (l.firstChild) prev.appendChild(l.firstChild);
        l.remove();
        changed = true;
      }
    }
    if (changed) richChanged();
  };

  /** Is the caret inside a list item of THIS editor? Tab only indents there. */
  const inListItem = () => {
    const n = getSelection()?.anchorNode;
    if (!n) return false;
    const el = n.nodeType === 3 ? n.parentElement : n;
    const li = el?.closest?.("li");
    return !!(li && $r.contains(li));
  };
  const selText = () => String(getSelection() || "");
  const esch = (x) => x.replace(/[&<>]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[ch]));
  const RICH = {
    bold: () => cmd("bold"), italic: () => cmd("italic"), strike: () => cmd("strikeThrough"),
    ul: () => cmd("insertUnorderedList"), ol: () => cmd("insertOrderedList"),
    task: () => cmd("insertHTML", `<ul><li class="task"><input type="checkbox">&nbsp;${esch(selText())}</li></ul>`),
    quote: () => cmd("formatBlock", document.queryCommandValue("formatBlock") === "blockquote" ? "p" : "blockquote"),
    code: () => { const t = selText(); cmd("insertHTML", t.includes("\n") ? `<pre>${esch(t)}</pre><p><br></p>` : `<code>${esch(t || "code")}</code>&nbsp;`); },
    link: async () => { const range = getSelection().rangeCount ? getSelection().getRangeAt(0).cloneRange() : null;
      const url = await askText("Link", "https://", "https://…"); if (!url) return;
      $r.focus(); if (range) { getSelection().removeAllRanges(); getSelection().addRange(range); }
      if (range && !range.collapsed) cmd("createLink", url); else cmd("insertHTML", `<a href="${esc(url)}">${esch(url)}</a>&nbsp;`); },
    table: () => cmd("insertHTML", `<table><thead><tr><th>Column</th><th>Column</th></tr></thead><tbody><tr><td>&nbsp;</td><td>&nbsp;</td></tr><tr><td>&nbsp;</td><td>&nbsp;</td></tr></tbody></table><p><br></p>`),
    hr: () => cmd("insertHorizontalRule"),
    date: () => cmd("insertText", longDate(todayLocal())),
    clear: () => { cmd("removeFormat"); cmd("formatBlock", "p"); },
  };
  const syncTools = () => {
    if (mode() !== "rich") return;
    const sel = ed.querySelector('.rich-tools [data-t="block"]'), fb = (document.queryCommandValue("formatBlock") || "p").toLowerCase();
    sel.value = ["h1", "h2", "h3"].includes(fb) ? fb : "p";
    [["bold", "bold"], ["italic", "italic"], ["strike", "strikeThrough"], ["ul", "insertUnorderedList"], ["ol", "insertOrderedList"]]
      .forEach(([k, c]) => ed.querySelector(`.rich-tools [data-t="${k}"]`).classList.toggle("on", document.queryCommandState(c)));
  };
  ed.querySelector(".rich-tools").addEventListener("mousedown", (e) => { if (e.target.closest("button")) e.preventDefault(); });  // keep the selection
  ed.querySelector(".rich-tools").onclick = (e) => { const k = e.target.closest("button[data-t]")?.dataset.t; if (k) RICH[k](); };
  ed.querySelector('.rich-tools [data-t="block"]').onchange = (e) => cmd("formatBlock", e.target.value);
  $r.oninput = richChanged;
  document.addEventListener("selectionchange", () => { if ($r.contains(getSelection().anchorNode)) syncTools(); });
  // checkboxes tick in place
  $r.addEventListener("click", (e) => { if (e.target.matches("input[type=checkbox]")) { e.target.toggleAttribute("checked", e.target.checked); richChanged(); } });
  // paste as plain text (formatting from web pages would come along otherwise)
  $r.addEventListener("paste", (e) => { e.preventDefault(); document.execCommand("insertText", false, e.clipboardData.getData("text/plain")); });
  // Markdown-style shortcuts at the start of a line: "# " heading, "- " list, "1. " numbered, "[] " checklist, "> " quote
  $r.onkeydown = (e) => {
    const mod = e.metaKey || e.ctrlKey;
    if (mod && e.key === "s") { e.preventDefault(); dirty = true; save(); }
    else if (mod && e.key.toLowerCase() === "k") { e.preventDefault(); RICH.link(); }
    // Tab nests a list item, Shift+Tab lifts it back out. htmlToMd already serialises nested
    // lists -- its `list(n, ind)` carries an indent level -- so the only thing missing was a way
    // to PRODUCE the nesting in rich mode; the markdown pane has had Tab since it was written.
    //
    // Only inside a list: elsewhere Tab belongs to the browser, moving focus out of the editor,
    // and swallowing it would trap keyboard users in the note body with no way forward.
    else if (e.key === "Tab" && inListItem()) {
      e.preventDefault();
      cmd(e.shiftKey ? "outdent" : "indent");
      fixNesting();   // BOTH directions emit malformed HTML; see fixNesting
    }
    else if (e.key === " ") {
      const sel = getSelection(), node = sel.anchorNode;
      const blockEl = node && (node.nodeType === 3 ? node.parentElement : node).closest("p, div, h1, h2, h3, li");
      const before = node && node.nodeType === 3 ? node.textContent.slice(0, sel.anchorOffset) : "";
      const rules = { "#": ["formatBlock", "h1"], "##": ["formatBlock", "h2"], "###": ["formatBlock", "h3"], "-": ["insertUnorderedList"], "*": ["insertUnorderedList"],
        "1.": ["insertOrderedList"], ">": ["formatBlock", "blockquote"], "[]": "task" };
      if (blockEl && blockEl !== $r && node.textContent.trim() === before.trim() && rules[before.trim()] && blockEl.tagName !== "LI") {
        e.preventDefault();
        node.textContent = node.textContent.slice(sel.anchorOffset);
        const r = rules[before.trim()];
        if (r === "task") RICH.task(); else cmd(r[0], r[1] || null);
      }
    }
    e.stopPropagation();   // keep the app's single-key shortcuts out of the editor
  };
  const setMode = (m) => {
    store.set("notesEditor", m);
    if (m === "rich") loadRich();   // pick up edits made in Markdown
    ed.querySelector(".ne-body").className = `ne-body mode-${m}`;
    ed.querySelector(".ne-bar").className = `ne-bar bar-${m}`;
    ed.querySelectorAll(".nmode button").forEach((x) => x.classList.toggle("on", x.dataset.v === m));
  };
  ed.querySelectorAll(".nmode button").forEach((b) => b.onclick = () => setMode(b.dataset.v));
  setMode(mode());
  ed.querySelector("#npin").onclick = (e) => { note.pinned = !note.pinned; e.currentTarget.classList.toggle("on", note.pinned); e.currentTarget.textContent = note.pinned ? "●" : "○"; dirty = true; save(); };
  symbolSearch(ed.querySelector("#nsymin"), ed.querySelector(".ne-symadd ul"), null, (s1, m1) => {
    if (!note.symbols.some((x) => x.market === m1 && x.symbol === s1)) note.symbols.push({ market: m1, symbol: s1 });
    ed.querySelector("#nsymin").value = ""; ed.querySelector(".ne-symadd ul").hidden = true; renderSyms(); changed();
  });
  ed.querySelector("#nmore").onclick = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    contextMenu(r.right - 210, r.bottom + 4, null, [
      { label: "Duplicate", fn: async () => { const c = await api("/api/notes", jsonReq("POST", { title: `${$t.value} (copy)`, body: $b.value, tags: note.tags, symbols: note.symbols })); go(`#/notes/${c.id}`); } },
      { label: "Copy as Markdown", fn: () => navigator.clipboard?.writeText(`# ${$t.value}\n\n${$b.value}`).then(() => toast("Copied", "ok")) },
      { sep: true },
      { label: "Delete note", danger: true, fn: async () => {
        clearTimeout(timer); dirty = false;
        const gone = await api(`/api/notes/${note.id}`, { method: "DELETE" });
        toast(`Deleted “${gone.title || "Untitled"}”`, "ok", { label: "Undo", fn: async () => {
          const back = await api("/api/notes", jsonReq("POST", { title: gone.title, body: gone.body, tags: gone.tags, symbols: gone.symbols, pinned: gone.pinned }));
          go(`#/notes/${back.id}`);
        } });
        go("#/notes");
      } },
    ]);
  };
  if (!note.title && !note.body) $t.focus(); else if (store.get("notesFresh", null) === note.id) (mode() === "rich" ? $r : $b).focus();
  // leaving the page: save pending edits; drop a new note that was never written in
  const prev = cleanup;
  cleanup = () => {
    clearTimeout(timer);
    if (dirty) save();
    else if (store.get("notesFresh", null) === note.id && !$b.value.trim()) { store.set("notesFresh", null); api(`/api/notes/${note.id}`, { method: "DELETE" }).catch(() => {}); }
    prev();
  };
}

// ------------------------------------------------------------- TODO page

/** TODO.md (repository root), rendered live: tick items here or in an editor; "Add" appends to Inbox. */
async function todoPage(alive) {
  document.title = "TODO · Trading";
  $view.innerHTML = LOADING;
  const t = await api("/api/todo").catch((e) => ({ error: e.message }));
  if (!alive()) return;
  if (t.error) { $view.innerHTML = `<div class="empty"><b>Could not read TODO.md</b><div class="muted">${esc(t.error)}</div></div>`; return; }
  const taskLines = t.markdown.split("\n").filter((l) => /^\s*[-*] \[[ xX]\]/.test(l));
  const open_ = taskLines.filter((l) => /\[ \]/.test(l)).length;
  $view.innerHTML = `<div class="page-head"><h1>TODO</h1><span class="muted small">${open_} open · ${taskLines.length - open_} done · edit <code>${esc(t.path)}</code> directly, or add here</span></div>
    <form class="todo-add" autocomplete="off"><input id="todoin" placeholder="Add an item to the Inbox… (Enter)" maxlength="500"><button class="primary" type="submit">Add</button></form>
    <section class="sec-card md todo-md">${marked.parse(t.markdown)}</section>`;
  // marked renders task lists as disabled checkboxes, in document order — the same order as taskLines
  $view.querySelectorAll(".todo-md input[type=checkbox]").forEach((cb, i) => {
    cb.disabled = false;
    cb.closest("li")?.classList.toggle("done", cb.checked);
    cb.onchange = async () => {
      try { await api("/api/todo/toggle", jsonReq("POST", { index: i, line: taskLines[i] })); route(); }
      catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); route(); }
    };
  });
  const inp = $view.querySelector("#todoin");
  $view.querySelector(".todo-add").onsubmit = async (e) => {
    e.preventDefault();
    if (!inp.value.trim()) return inp.focus();
    try { await api("/api/todo", jsonReq("POST", { text: inp.value })); toast("Added to the Inbox", "ok"); route(); }
    catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
  };
}

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
function eta(sec) {
  // a rough, self-refining estimate: see status.py's _estimate_remaining
  if (sec == null) return "";
  return ` · ~${dur(sec)} left`;
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
    FRESH = s.freshness; paintFresh(); LAST_STATUS = s;
    const st = s.running.length ? "running" : s.overall;
    a.className = `dstatus st-${st}`;
    // say what the dot means, not just "Data": current / behind / stale / missing / updating
    const word = { ok: "Data current", warn: "Data behind", stale: "Data stale", missing: "Data missing", partial: "Data partly failed", failed: "Data update failed" };
    const waiting = s.queue?.queued.length || 0, stalled = waiting && !s.worker?.alive;
    if (stalled) a.className = "dstatus st-warn";
    // compact: a dot and the current market's price date; words only when something is happening
    const m = store.get("market", MKTS[0].key), pd = s.freshness[m]?.items.find((i) => i.key === "prices")?.date;
    a.querySelector(".ds-l").textContent = stalled ? `Worker stopped · ${waiting} waiting` : s.running.length ? `Updating…${waiting ? ` +${waiting}` : ""}`
      : pd ? prettyDate(pd).replace(/ \d{4}$/, "") : "No data";
    const line = (m) => { const f = s.freshness[m]; const p = f.items.find((i) => i.key === "prices"); return `${f.name}: prices ${p.date ? prettyDate(p.date) : "none"} (${ST_TEXT[p.status]})`; };
    a.title = `${word[st] || "Data status"} — ${MKTS.filter((x) => s.freshness[x.key]).map((x) => line(x.key)).join(" · ")}${s.latest_daily ? ` · last daily run ${clock(s.latest_daily.started_at)}: ${ST_TEXT[s.latest_daily.status]}` : ""} · checked ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}. Click for details.`;
    return s;
  } catch { a.className = "dstatus"; return null; }
}
refreshStatusDot();
setInterval(refreshStatusDot, 120000);

/* The header's status pill opens a small panel instead of leaving the page: what each lane is running,
 * what the "+N" counts (the jobs waiting), how current each market's data is — and the way to System. */
let LAST_STATUS = null;
function statusPopover(s) {
  const q = s.queue || {}, running = q.running_all || (q.running ? [q.running] : []), waiting = q.queued || [];
  const job = (x) => `${(x.targets || []).join(" + ")}${x.market && x.market !== "all" ? ` · ${mktInfo(x.market).name}` : ""}`;
  const lane = (x) => (x.lane && x.lane !== "main" ? ` <span class="tag">${esc(x.lane)} lane</span>` : "");
  const fresh = MKTS.filter((m) => s.freshness?.[m.key]).map((m) => {
    const p = s.freshness[m.key].items.find((i) => i.key === "prices");
    return `<li class="${p?.status && p.status !== "ok" ? "warn" : ""}">${m.flag} ${esc(m.name)}: prices ${p?.date ? prettyDate(p.date) : "none"} — ${esc((p?.text || "").split(" · ")[0])}</li>`;
  }).join("");
  const lanes = s.lanes ? Object.entries(s.lanes).map(([k, w]) => `<span class="wk ${w.alive ? "ok" : "off"}"><i></i>${esc(k)}</span>`).join("") : "";
  return `<div class="stpop" role="dialog" aria-label="What is running">
    <div class="stpop-h"><b>Jobs</b>${lanes}</div>
    ${running.length ? `<ul>${running.map((x) => `<li><span class="spin"></span> ${esc(job(x))}${lane(x)} <span class="muted small">since ${clock(x.started_at)}</span></li>`).join("")}</ul>` : '<div class="muted small">Nothing running.</div>'}
    ${waiting.length ? `<div class="muted small">+${waiting.length} waiting in the queue${waiting.length ? `: ${waiting.slice(0, 3).map((x) => esc(job(x))).join(", ")}${waiting.length > 3 ? "…" : ""}` : ""}</div>` : ""}
    <div class="stpop-h"><b>Data</b></div><ul class="small">${fresh}</ul>
    <a class="small" href="#/status">System → Status for every dataset and the queue →</a></div>`;
}
document.getElementById("dstatus").addEventListener("click", (e) => {
  if (!LAST_STATUS || e.metaKey || e.ctrlKey) return;     // no status yet, or opening Status in a new tab
  e.preventDefault();
  const open = document.querySelector(".stpop");
  if (open) { open.remove(); return; }
  const pill = e.currentTarget, box = pill.getBoundingClientRect();
  const pop = el(statusPopover(LAST_STATUS));
  pop.style.top = `${box.bottom + 6}px`; pop.style.right = `${Math.max(8, window.innerWidth - box.right)}px`;
  document.body.append(pop);
  const close = (ev) => { if (!pop.contains(ev.target) && ev.target !== pill && !pill.contains(ev.target)) { pop.remove(); document.removeEventListener("click", close); } };
  setTimeout(() => document.addEventListener("click", close));
  pop.querySelector('a[href="#/status"]').onclick = () => pop.remove();
  refreshStatusDot().then((fresh) => { if (fresh && document.body.contains(pop)) pop.innerHTML = el(statusPopover(fresh)).innerHTML; });
});

/** Confirm and start a job / pipeline (the server runs `python -m jobs run ...` in the background). */
let _stratList = null;
const strategyList = async () => (_stratList = _stratList || (await api("/api/strategies").catch(() => [])).filter((x) => x.kind === "screener"));

/** Confirm a run and choose its options; it then joins the job queue (the worker runs one at a time). */
async function runDialog({ title, targets, market, screens, resumeFrom, pick }) {
  const strats = screens ? await strategyList() : [];
  return new Promise((resolve) => {
    const m = el(`<div class="smodal"><div class="smodal-card settings rundlg"><div class="sm-head"><b>${esc(title)}</b></div>
      <div class="sm-form">
        ${resumeFrom ? `<label class="rd-opt"><input type="radio" name="rmode" value="resume" checked><span>Resume from <b>${esc(resumeFrom)}</b> — where the last run failed</span></label>
          <label class="rd-opt"><input type="radio" name="rmode" value="all"><span>Run every step again</span></label>` : ""}
        ${screens ? `<h4>Strategies</h4><label class="rd-opt"><input type="checkbox" id="rd-all" ${pick ? "" : "checked"}><span><b>All strategies</b></span></label>
          <div class="rd-strats">${strats.map((x) => `<label class="rd-opt"><input type="checkbox" class="rd-s" value="${x.key}" ${!pick || pick === x.key ? "checked" : ""} ${pick ? "" : "disabled"}><span>${esc(x.name)}</span></label>`).join("")}</div>` : ""}
        <label class="rd-opt"><input type="checkbox" id="rd-force"><span>Force refresh — re-fetch data even where it looks current (slower)</span></label>
        <div class="muted small">Same as running, from scripts/:</div><code class="rd-cmd"></code>
        <div class="muted small">It joins the queue: the worker runs one job at a time, and this page follows it step by step.</div>
      </div>
      <div class="sm-foot"><span class="spacer"></span><button class="ghost" data-a="cancel">Cancel</button><button class="primary" data-a="ok">Add to queue</button></div></div></div>`);
    document.body.append(m);
    const all = m.querySelector("#rd-all");
    if (all) all.onchange = () => m.querySelectorAll(".rd-s").forEach((c) => { c.disabled = all.checked; if (all.checked) c.checked = true; });
    const spec = () => {
      const resume = resumeFrom && m.querySelector('input[name="rmode"]:checked')?.value === "resume";
      const picked = [...m.querySelectorAll(".rd-s:checked")].map((c) => c.value);
      // `screens` shows the strategy PICKER; it must not also decide whether a pick is sent. A
      // portfolio strategy has no picker (there is one choice, named in the title) and passing
      // screens:false silently dropped its key, so the job ran the DEFAULT strategy and reported
      // success -- a US backtest queued from its page produced a run for another strategy.
      return { targets, market,
               strategies: screens ? (all.checked ? "all" : picked) : (pick ? [pick] : null),
               from: resume ? resumeFrom : null, force: m.querySelector("#rd-force").checked };
    };
    const showCmd = () => { const x = spec(); const st = Array.isArray(x.strategies) ? x.strategies.join(",") : x.strategies;
      m.querySelector(".rd-cmd").textContent = `python -m jobs enqueue ${x.targets.join(" ")} --market ${x.market}${st ? ` --strategies ${st}` : ""}${x.from ? ` --from ${x.from}` : ""}${x.force ? " --force" : ""}`;
      m.querySelector('[data-a="ok"]').disabled = Array.isArray(x.strategies) && !x.strategies.length; };
    m.onchange = showCmd; showCmd();
    const done = (v) => { m.remove(); resolve(v); };
    m.onclick = (e) => { const a = e.target.closest("button")?.dataset.a; if (a === "ok") done(spec()); if (a === "cancel" || e.target === m) done(null); };
    m.onkeydown = (e) => { e.stopPropagation(); if (e.key === "Escape") done(null); };
  });
}
async function startWorker() {
  try { await api("/api/worker/start", { method: "POST" }); toast("Worker started", "ok"); setTimeout(() => route(), 2500); }
  catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
}
/** add a run to the queue (after the Run dialog), and say where it stands */
async function startJob(opts) {
  const spec = await runDialog(opts);
  if (!spec) return;
  try {
    const r = await api("/api/jobs/run", jsonReq("POST", spec));
    const where = r.position === 0 ? "running now" : r.position === 1 ? "next in the queue" : `#${r.position} in the queue`;
    if (!r.worker.alive) toast(`Queued, but the worker is not running — nothing will run until it starts`, "err", { label: "Start worker", fn: startWorker });
    else toast(`${r.duplicate ? "Already queued" : "Queued"} — ${where}`, "ok");
    refreshStatusDot();
    if (location.hash.startsWith("#/status")) setTimeout(() => route(), 800);
  } catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
}
/** the job a failed / partial run should resume from: its first step that did not finish */
async function resumePoint(run) {
  if (!run || !["partial", "failed", "interrupted"].includes(run.status)) return null;
  const d = await api(`/api/status/run/${run.id}`).catch(() => null);
  const st = d?.steps.find((x) => ["failed", "interrupted"].includes(x.status));
  return st ? st.step.split(":")[0] : null;
}

const DAYS = [["mon", "Mon"], ["tue", "Tue"], ["wed", "Wed"], ["thu", "Thu"], ["fri", "Fri"], ["sat", "Sat"], ["sun", "Sun"]];
// a schedule with its own clock (a market's time zone) says so: "Mon–Fri · 08:00 New York"
const tzCity = (tz) => tz ? " " + tz.split("/").pop().replace(/_/g, " ") : "";
const whenText = (x) => x.monthday ? `Monthly, day ${x.monthday} · ${x.at_time}${tzCity(x.tz)}`
  : `${x.days === "mon,tue,wed,thu,fri" ? "Mon–Fri" : x.days === "tue,wed,thu,fri,sat" ? "Tue–Sat" : x.days.split(",").map((d) => d[0].toUpperCase() + d.slice(1)).join(", ")} · ${x.at_time}${tzCity(x.tz)}`;
// the next run in THIS machine's time, whatever clock the schedule keeps
const whenNext = (iso) => { if (!iso) return "—"; const d = new Date(iso), p2 = (n) => String(n).padStart(2, "0");
  const ymd = `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
  return `${WEEKDAY[d.getDay()]} ${prettyDate(ymd)} · ${p2(d.getHours())}:${p2(d.getMinutes())}`; };

/** System → Schedules: when each pipeline runs on its own. The worker enqueues a schedule when it is due. */
async function schedulesPage(alive) {
  document.title = "Schedules · Trading";
  $view.innerHTML = LOADING;
  const d = await api("/api/schedules").catch((e) => ({ error: e.message }));
  if (!alive()) return;
  if (d.error) { $view.innerHTML = `<div class="empty"><b>Could not load schedules</b><div class="muted">${esc(d.error)}</div></div>`; return; }
  const w = d.worker;
  const mk = (m) => m === "all" ? "both markets" : (MKT_BADGE[m] || m);
  $view.innerHTML = pageHead("Schedules", { context: info(`<p>Each schedule adds its run to the <a href="#/status">job queue</a> when it is due; the worker runs the queue one job at a time.</p>
      <p>Times are this machine's local time (${esc(d.tz)}) unless a schedule names a market's clock: the market open and close routines follow that market's time zone, so they stay put through daylight saving. <b>Next run</b> is always local time. Scheduled runs go ahead of runs queued by hand, but wait for whatever is already running. A slot missed while the computer was asleep or the worker was stopped runs once, when the worker next looks.</p>
      <p><b>close</b> runs the day's data and every strategy's setups after each market's close; <b>open</b> catches up anything the close missed, refreshes earnings dates and checks everything is ready before the bell. On demand only: <b>quality</b>.</p>
      <p>From a terminal: <code>python -m jobs schedules</code> · <code>python -m jobs queue</code></p>`),
      actions: `<button class="primary" id="snew">+ New schedule</button>` }) + `
    ${w.alive ? "" : `<div class="sd-status watch"><b>Worker stopped</b> Nothing below will run until the worker is running. <button class="primary sm" id="wkstart">Start worker</button></div>`}
    <section class="sec-card runnow"><div class="sec-card-h"><h3>Run now</h3>${marketSeg(pageMarket())}<span class="muted small">adds the run to the queue · per-market pipelines use the chosen market</span></div>
      <div class="runbtns">${d.targets.pipelines.map((p) => { const perM = !["weekly", "monthly"].includes(p.name);
        return `<button data-pipe="${p.name}" data-m="${perM ? pageMarket() : "all"}" title="${esc(p.summary)}"><svg viewBox="0 0 20 20" class="play"><path d="M7 5l8 5-8 5z"/></svg>${esc(p.name[0].toUpperCase() + p.name.slice(1))}${perM ? ` · ${esc(mktInfo(pageMarket()).name)}` : ""}</button>`; }).join("")}</div></section>
    <section class="sec-card"><table class="stt sched"><thead><tr><th>On</th><th>Schedule</th><th>When</th><th>Next run</th><th>Last run</th><th></th></tr></thead><tbody>
      ${d.schedules.map((x) => `<tr class="${x.enabled ? "" : "off"}" data-id="${x.id}">
        <td><label class="switch" title="${x.enabled ? "On — click to pause" : "Paused — click to turn on"}"><input type="checkbox" data-on ${x.enabled ? "checked" : ""}><i></i></label></td>
        <td><b>${esc(x.name)}</b><div class="muted small"><code>${esc(x.command.replace(/^python -m jobs /, ""))}</code> · ${esc(mk(x.market))}</div></td>
        <td>${esc(whenText(x))}</td>
        <td>${x.enabled ? esc(whenNext(x.next_slot)) : '<span class="muted">paused</span>'}</td>
        <td>${x.last ? `${stBadge(x.last.status === "ok" ? "ok" : x.last.status === "queued" ? "pending" : x.last.status === "running" ? "running" : x.last.status === "cancelled" ? "skipped" : "failed")}
            ${x.last.run_id ? `<a class="small" href="#/runs/${x.last.run_id}">${x.last.finished_at ? clock(x.last.finished_at) : "steps"}</a>` : ""}` : '<span class="muted small">not yet</span>'}</td>
        <td class="sacts"><button class="sm" data-run title="Add this run to the queue now">Run now</button><button class="sm" data-edit>Edit</button>
          <button class="ibtn" data-del title="Delete this schedule">×</button></td></tr>`).join("") || `<tr><td colspan="6" class="muted">No schedules — add one.</td></tr>`}
    </tbody></table></section>
    `;
  $view.querySelector("#wkstart")?.addEventListener("click", startWorker);
  $view.querySelector("#snew").onclick = () => scheduleDialog(d, null);
  $view.querySelectorAll(".mk button").forEach((b) => b.onclick = () => { pageMarket(b.dataset.v); route(); });
  $view.querySelectorAll("[data-pipe]").forEach((b) => b.onclick = () => startJob({ title: `Run ${b.dataset.pipe}${b.dataset.m === "all" ? "" : " · " + mktInfo(b.dataset.m).name}`,
    targets: [b.dataset.pipe], market: b.dataset.m, screens: ["strategies", "backtest"].includes(b.dataset.pipe) }));
  $view.querySelectorAll("tr[data-id]").forEach((tr) => {
    const x = d.schedules.find((y) => y.id === +tr.dataset.id);
    tr.querySelector("[data-on]").onchange = async (e) => { await api(`/api/schedules/${x.id}/enabled`, jsonReq("POST", { enabled: e.target.checked })); toast(e.target.checked ? `“${x.name}” is on` : `“${x.name}” paused`, "ok"); route(); };
    tr.querySelector("[data-run]").onclick = async () => {
      const r = await api(`/api/schedules/${x.id}/run`, { method: "POST" });
      toast(`${r.duplicate ? "Already queued" : "Queued"} — ${r.position === 0 ? "running now" : r.position === 1 ? "next" : "#" + r.position + " in the queue"}`, "ok");
      if (!d.worker.alive) toast("The worker is not running — start it to run the queue", "err", { label: "Start worker", fn: startWorker });
      route();
    };
    tr.querySelector("[data-edit]").onclick = () => scheduleDialog(d, x);
    tr.querySelector("[data-del]").onclick = async () => { if (!confirm(`Delete the schedule “${x.name}”?`)) return; await api(`/api/schedules/${x.id}`, { method: "DELETE" }); toast("Deleted", "ok"); route(); };
  });
}

/** create / edit a schedule */
async function scheduleDialog(d, x) {
  const strats = await strategyList();
  x = x || { name: "", targets: ["daily"], market: "india", opts: {}, days: "mon,tue,wed,thu,fri", monthday: null, at_time: "18:30", enabled: true };
  const target = x.targets[0], days = new Set(x.days.split(","));
  const stSel = x.opts?.strategies;
  const m = el(`<div class="smodal"><div class="smodal-card settings rundlg"><div class="sm-head"><b>${x.id ? "Edit schedule" : "New schedule"}</b></div>
    <div class="sm-form">
      <label>Name <input id="sd-name" value="${esc(x.name)}" placeholder="e.g. Strategies · India after the close"></label>
      <label>Run <select id="sd-target">
        <optgroup label="Pipelines">${d.targets.pipelines.map((p) => `<option value="${p.name}" ${p.name === target ? "selected" : ""} title="${esc(p.summary)}">${p.name} — ${esc(p.jobs.join(" → "))}</option>`).join("")}</optgroup>
        <optgroup label="Single jobs">${d.targets.jobs.map((j) => `<option value="${j.name}" ${j.name === target ? "selected" : ""}>${j.name}</option>`).join("")}</optgroup></select></label>
      <label>Market <select id="sd-market"><option value="all" ${x.market === "all" ? "selected" : ""}>Both markets</option>${MKTS.map((k) => `<option value="${k.key}" ${k.key === x.market ? "selected" : ""}>${esc(k.name)}</option>`).join("")}</select></label>
      <div id="sd-strats" hidden><h4>Strategies</h4><label class="rd-opt"><input type="checkbox" id="sd-all" ${!stSel || stSel.includes?.("all") ? "checked" : ""}><span><b>All strategies</b></span></label>
        <div class="rd-strats">${strats.map((k) => `<label class="rd-opt"><input type="checkbox" class="sd-s" value="${k.key}" ${!stSel || stSel.includes?.("all") || stSel.includes?.(k.key) ? "checked" : ""}><span>${esc(k.name)}</span></label>`).join("")}</div></div>
      <h4>When</h4>
      <label class="rd-opt"><input type="radio" name="sd-mode" value="week" ${x.monthday ? "" : "checked"}><span>On these days</span></label>
      <div class="sd-days">${DAYS.map(([k, t]) => `<label class="chip ${days.has(k) ? "on" : ""}"><input type="checkbox" value="${k}" ${days.has(k) ? "checked" : ""}>${t}</label>`).join("")}</div>
      <label class="rd-opt"><input type="radio" name="sd-mode" value="month" ${x.monthday ? "checked" : ""}><span>Monthly, on day <input id="sd-md" type="number" min="1" max="28" value="${x.monthday || 1}" style="width:64px"></span></label>
      <label>At <input id="sd-time" type="time" value="${esc(x.at_time)}"></label>
      <label>Clock <select id="sd-tz"><option value="" ${x.tz ? "" : "selected"}>This machine (${esc(d.tz)})</option>
        ${[...new Set(MKTS.map((k) => k.tz).filter(Boolean).concat(x.tz ? [x.tz] : []))].map((z) => `<option value="${esc(z)}" ${z === x.tz ? "selected" : ""}>${esc(MKTS.filter((k) => k.tz === z).map((k) => k.name).join(" / ") || z)} — ${esc(z)}</option>`).join("")}</select></label>
      <label class="rd-opt"><input type="checkbox" id="sd-force" ${x.opts?.force ? "checked" : ""}><span>Force refresh — re-fetch even where data looks current</span></label>
      <label class="rd-opt"><input type="checkbox" id="sd-on" ${x.enabled ? "checked" : ""}><span>On</span></label>
    </div>
    <div class="sm-foot"><span class="spacer"></span><button class="ghost" data-a="cancel">Cancel</button><button class="primary" data-a="ok">Save</button></div></div></div>`);
  document.body.append(m);
  const $ = (q) => m.querySelector(q);
  const usesStrats = () => { const t = $("#sd-target").value; const picks = (j) => ["strategies", "backtest"].includes(j);
    return picks(t) || (d.targets.pipelines.find((p) => p.name === t)?.jobs || []).some(picks); };
  const sync = () => {
    $("#sd-strats").hidden = !usesStrats();
    m.querySelectorAll(".sd-s").forEach((c) => { c.disabled = $("#sd-all").checked; if ($("#sd-all").checked) c.checked = true; });
    m.querySelectorAll(".sd-days label").forEach((l) => l.classList.toggle("on", l.querySelector("input").checked));
  };
  m.onchange = sync; sync();
  const close = () => m.remove();
  m.onkeydown = (e) => { e.stopPropagation(); if (e.key === "Escape") close(); };
  m.onclick = async (e) => {
    const a = e.target.closest("button")?.dataset.a;
    if (a === "cancel" || e.target === m) return close();
    if (a !== "ok") return;
    const month = m.querySelector('input[name="sd-mode"]:checked').value === "month";
    const t = $("#sd-target").value, mkt = $("#sd-market").value;
    const st = usesStrats() ? ($("#sd-all").checked ? ["all"] : [...m.querySelectorAll(".sd-s:checked")].map((c) => c.value)) : null;
    const spec = { id: x.id, targets: [t], market: mkt, enabled: $("#sd-on").checked, at_time: $("#sd-time").value, tz: $("#sd-tz").value || null,
      days: month ? "" : [...m.querySelectorAll(".sd-days input:checked")].map((c) => c.value).join(","), monthday: month ? +$("#sd-md").value : null,
      opts: { strategies: st, force: $("#sd-force").checked },
      name: $("#sd-name").value.trim() || `${t[0].toUpperCase() + t.slice(1)} · ${mkt === "all" ? "both markets" : (MKTS.find((k) => k.key === mkt) || {}).name}` };
    try { await api("/api/schedules", jsonReq("POST", spec)); close(); toast("Schedule saved", "ok"); route(); }
    catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
  };
}

const Q_BY = { you: "you", schedule: "schedule", "command line": "command line", "breadth page": "Breadth page" };
/** The job queue: worker health, what is running (Stop), what is waiting (cancel / run next), what just finished. */
function queuePanel(s) {
  const Q = s.queue, w = s.worker;
  const what = (x) => `<code>${esc(x.command.replace(/^python -m jobs run /, ""))}</code>`;
  const by = (x) => `<span class="muted small">${esc(Q_BY[x.requested_by] || x.requested_by)} · ${clock(x.created_at)}</span>`;
  const fast = s.lanes?.fast;
  const worker = w.alive
    ? `<span class="wk ok"><i></i>Worker running</span><span class="muted small">pid ${w.pid} · since ${clock(w.started_at)}</span>
       ${fast ? `<span class="wk ${fast.alive ? "ok" : "off"}" title="The fast lane runs short jobs on stored data — screens, breadth, setups, reports — beside the other lanes, so they never wait behind a backtest"><i></i>Fast lane ${fast.alive ? "running" : "stopped"}</span>` : ""}
       ${s.lanes?.backtest ? `<span class="wk ${s.lanes.backtest.alive ? "ok" : "off"}" title="The backtest lane runs backtests and other long research, so the market routines in the main lane never wait behind them"><i></i>Backtest lane ${s.lanes.backtest.alive ? "running" : "stopped"}</span>` : ""}`
    : `<span class="wk off"><i></i>Worker stopped</span><span class="muted small">queued runs and schedules wait until it runs.</span>
       <button class="primary sm" id="wkstart">Start worker</button><span class="muted small">To keep it running across restarts: <code>${esc(s.worker_command)}</code></span>`;
  return `<section class="sec-card qpanel"><div class="sec-card-h"><h3>Job queue</h3>${worker}</div>
    ${(Q.running_all || (Q.running ? [Q.running] : [])).length ? (Q.running_all || [Q.running]).map((x) => `<div class="qrow run"><i class="spin"></i><b>Running</b>${x.lane && x.lane !== "main" ? `<span class="tag">${esc(x.lane)} lane</span>` : ""}${what(x)}${by(x)}<span class="muted small">started ${clock(x.started_at)} · running for ${dur((Date.now() - new Date(x.started_at)) / 1000)}${eta(x.eta_s)}</span>
        ${x.run_id ? `<a class="small" href="#/runs/${x.run_id}">steps →</a>` : ""}<span class="spacer"></span>
        ${x.cancel_requested ? '<span class="muted small">stopping…</span>' : `<button class="danger sm" data-qstop="${x.id}">Stop</button>`}</div>`).join("")
      : s.job_running && !s.job_running.from_queue
        ? `<div class="qrow run"><i class="spin"></i><b>Running outside the queue</b><code>${esc(s.job_running.cmd)}</code><span class="muted small">started ${clock(s.job_running.started)} from a terminal — the worker waits for it to finish</span>
            <a class="small" href="#/runs/${s.job_running.run_id}">steps →</a></div>`
        : `<div class="qrow muted small">Nothing running.</div>`}
    ${Q.queued.map((x, i) => `<div class="qrow"><span class="qn">${i + 1}</span><b>Waiting</b>${what(x)}${by(x)}<span class="spacer"></span>
        ${i ? `<button class="sm" data-qfront="${x.id}" title="Run this next">Run next</button>` : ""}<button class="sm" data-qcancel="${x.id}">Cancel</button></div>`).join("")}
    ${Q.recent.length ? `<details class="qrecent"><summary class="muted small">Recently finished (${Q.recent.length})</summary>
      ${Q.recent.map((x) => `<div class="qrow">${stBadge(x.status === "ok" ? "ok" : x.status === "cancelled" ? "skipped" : x.status === "stopped" ? "interrupted" : "failed")}${what(x)}${by(x)}
        <span class="muted small">${x.finished_at ? "finished " + clock(x.finished_at) : ""}</span>${x.run_id ? `<a class="small" href="#/runs/${x.run_id}">steps →</a>` : ""}${x.note ? `<span class="muted small">${esc(x.note)}</span>` : ""}</div>`).join("")}</details>` : ""}
  </section>`;
}
function wireQueuePanel(root) {
  const post = async (url, msg) => { try { await api(url, { method: "POST" }); toast(msg, "ok"); setTimeout(() => route(), 800); } catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); } };
  root.querySelector("#wkstart")?.addEventListener("click", startWorker);
  root.querySelectorAll("[data-qstop]").forEach((b) => b.onclick = () => {
    if (confirm("Stop the running job? The step in progress is marked as stopped; you can resume it later.")) post(`/api/queue/${b.dataset.qstop}/cancel`, "Stopping…");
  });
  root.querySelectorAll("[data-qcancel]").forEach((b) => b.onclick = () => post(`/api/queue/${b.dataset.qcancel}/cancel`, "Removed from the queue"));
  root.querySelectorAll("[data-qfront]").forEach((b) => b.onclick = () => post(`/api/queue/${b.dataset.qfront}/front`, "Moved to the front"));
}

const SRC_LABEL = { you: ["you", "pos"], curated: ["curated", "neutral"], rule: ["rule", "neutral"], suggested: ["suggested", "info"],
  code: ["code", "neutral"], bse: ["BSE", "neutral"], other: ["unassigned", "warn"] };
/** Library → Sub-industries: review and edit which sub-industry each tradable company belongs to. */
async function subindustriesPage(alive, mkt, group) {
  mkt = pageMarket(mkt);
  document.title = "Sub-industries · Trading";
  $view.innerHTML = LOADING;
  const d = await api(`/api/subindustries?market=${mkt}`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  if (d.error) { $view.innerHTML = `<div class="empty"><b>Could not load sub-industries</b><div class="muted">${esc(d.error)}</div></div>`; return; }
  const show = store.get("subShow", "review");
  const list = d.groups.filter((g) => show === "all" || (show === "split" ? g.split : g.open > 0));
  group = group ? decodeURIComponent(group) : (list[0] || d.groups[0])?.industry;
  const g = d.groups.find((x) => x.industry === group) || list[0];
  const c = d.coverage;
  const href = (x) => `#/subindustries/${mkt}/${encodeURIComponent(x)}`;
  $view.innerHTML = pageHead("Sub-industries", {
      extra: marketSeg(mkt),
      context: `<span class="muted small">${c.labelled.toLocaleString()} of ${c.in_split_groups.toLocaleString()} tradable stocks in split groups labelled · ${c.suggested} suggested · ${c.other} unassigned</span>${info(`
        <p>A sub-industry splits an industry group that mixes businesses (Semiconductors → AI &amp; compute, Analog, Memory…). Coherent groups (Restaurants, Homebuilding) are not split.</p>
        <p>Each label shows where it came from: <b>you</b> (your edits — always win) · <b>curated</b> (data/sub_industries.csv) · <b>rule</b> (US banks by size, asset managers vs BDCs) · <b>suggested</b> (proposed, awaiting your review) · <b>code</b> (an official code mapped in data/sub_industry_codes.csv) · <b>BSE</b> (India: BSE's own industry, where a group spans several) · <b>unassigned</b>.</p>
        <p>Official codes: ${esc(d.scheme)}. Labelling a stock in an unsplit group splits that group. <code>python -m swing_screener.marketdata.subindustries --export</code> writes your labels into the curated CSV (for git).</p>`)}` })
    + `<div class="rep-layout"><aside class="rep-nav strat-nav sub-nav">
        ${segmented([["review", "Needs review"], ["split", "Split"], ["all", "All"]], show, "subshow")}
        ${list.map((x) => `<a class="nav-item ${g && x.industry === g.industry ? "active" : ""}" href="${href(x.industry)}" title="${esc(x.sector || "")}">
          <span><b class="sn">${esc(x.industry)}</b></span><span class="n" title="${x.open ? x.open + " to review" : x.members.length + " tradable stocks"}">${x.open || x.members.length}</span></a>`).join("") || '<div class="nav-empty muted small">Nothing to review.</div>'}
      </aside><section id="submain" class="scr-main"></section></div>`;
  $view.querySelectorAll(".subshow button").forEach((b) => b.onclick = () => { store.set("subShow", b.dataset.v); route(); });
  $view.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(`#/subindustries/${b.dataset.v}`));
  const main = $view.querySelector("#submain");
  if (!g) { main.innerHTML = '<div class="empty"><b>No groups</b></div>'; return; }
  const counts = {}; g.members.forEach((m) => { if (m.sub) counts[m.sub] = (counts[m.sub] || 0) + 1; });
  const subOpts = (cur) => `<option value="">— automatic —</option>${g.subs.map((x) => `<option ${x === cur ? "selected" : ""}>${esc(x)}</option>`).join("")}<option value="__new">+ New sub-industry…</option>`;
  main.innerHTML = `<div class="page-head sub"><h2 class="sub-title">${esc(g.industry)}</h2><span class="muted small">${esc(g.sector || "")} · ${g.members.length} tradable stocks${g.split ? ` · ${g.subs.length} sub-industries` : " · not split"}</span>
      <span class="spacer"></span>${g.members.some((m) => m.source === "suggested") ? `<button class="primary sm" id="acceptall">Accept all suggestions</button>` : ""}</div>
    ${g.split ? `<div class="sub-chips">${Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => `<span class="chip-s ${k === "other" ? "dn" : ""}">${esc(k === "other" ? "unassigned" : k)} <b>${n}</b></span>`).join("")}</div>` : ""}
    <div class="sub-bulk" hidden><span id="nsel"></span><select id="bulksub">${subOpts(null)}</select><button class="sm" id="bulkset">Set</button><button class="sm" id="bulkrevert">Revert to automatic</button></div>
    <table class="stt subtab"><thead><tr><th><input type="checkbox" id="selall"></th><th>Company</th><th class="num">Mkt cap ($B)</th><th>Official code</th><th>Sub-industry</th><th>Source</th></tr></thead><tbody>
      ${g.members.map((m, i) => `<tr data-i="${i}" class="${m.source === "other" ? "open" : ""}"><td><input type="checkbox" class="rs"></td>
        <td class="symcell"><div><b><a href="#/chart/${mkt}/${encodeURIComponent(m.symbol)}">${esc(m.symbol.replace(/\.NS$/, ""))}</a></b><span>${esc(m.name || "")}</span></div></td>
        <td class="num">${m.cap != null ? fmt(m.cap) : ""}</td><td class="muted small">${esc(m.code || "—")}</td>
        <td><select class="rsub">${subOpts(m.source === "you" || m.source === "curated" || m.source === "suggested" || m.source === "rule" || m.source === "code" || m.source === "bse" ? m.sub : null).replace('<option value="">— automatic —</option>', `<option value="">${m.source === "you" ? "— revert to automatic —" : "— " + esc(m.sub && m.sub !== "other" ? m.sub : "unassigned") + " —"}</option>`)}</select></td>
        <td><span class="tag ${(SRC_LABEL[m.source] || ["", "neutral"])[1]}">${(SRC_LABEL[m.source] || [m.source || "—"])[0]}</span></td></tr>`).join("")}</tbody></table>`;
  const post = async (symbols, sub) => {
    try { const r = await api("/api/subindustries", jsonReq("POST", { market: mkt, symbols, sub })); toast(`${r.changed} updated`, "ok"); route(); }
    catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
  };
  const askNew = async () => { const v = await askText("New sub-industry", "", "e.g. Data-centre power & cooling"); return v && v.trim(); };
  main.querySelectorAll("tr[data-i] .rsub").forEach((sel) => sel.onchange = async () => {
    const m = g.members[+sel.closest("tr").dataset.i];
    let v = sel.value;
    if (v === "__new") { v = await askNew(); if (!v) { route(); return; } }
    post([m.symbol], v || null);
  });
  const selected = () => [...main.querySelectorAll("tr[data-i]")].filter((tr) => tr.querySelector(".rs").checked).map((tr) => g.members[+tr.dataset.i].symbol);
  const syncBulk = () => { const n = selected().length; main.querySelector(".sub-bulk").hidden = !n; main.querySelector("#nsel").textContent = `${n} selected`; };
  main.querySelectorAll(".rs").forEach((c) => c.onchange = syncBulk);
  main.querySelector("#selall").onchange = (e) => { main.querySelectorAll(".rs").forEach((c) => { c.checked = e.target.checked; }); syncBulk(); };
  main.querySelector("#bulkset").onclick = async () => { let v = main.querySelector("#bulksub").value; if (v === "__new") v = await askNew(); if (v) post(selected(), v); };
  main.querySelector("#bulkrevert").onclick = () => post(selected(), null);
  main.querySelector("#acceptall")?.addEventListener("click", async () => {
    const sug = g.members.filter((m) => m.source === "suggested");
    const by = {}; sug.forEach((m) => { (by[m.sub] = by[m.sub] || []).push(m.symbol); });
    for (const [sub, syms] of Object.entries(by)) await api("/api/subindustries", jsonReq("POST", { market: mkt, symbols: syms, sub }));
    toast(`${sug.length} suggestions accepted`, "ok"); route();
  });
}

/** System → Status: is my data current (per market), and the job queue. */
async function statusPage(alive, runId) {
  if (runId) return go(`#/runs/${runId}`);   // old links
  document.title = "Status · Trading";
  $view.innerHTML = LOADING;
  const s = await refreshStatusDot() || await api("/api/status");
  if (!alive()) return;
  const live = s.running.length || s.job_running || s.queue.queued.length;
  const fresh = (m) => {
    const f = s.freshness[m];
    return `<section class="sec-card"><div class="sec-card-h"><h3>${esc(f.name)}</h3><span class="muted small">should have ${prettyDate(f.expected)}</span></div>
      <table class="stt fresh">${f.items.map((i) => `<tr><td>${stBadge(i.status)}</td><td><b>${esc(i.label)}</b></td>
        <td class="num">${i.kind === "session" ? (i.date ? prettyDate(i.date) : "—") : (i.date ? clock(i.date) : "—")}</td><td class="muted small">${esc(i.text)}</td></tr>`).join("")}</table></section>`;
  };
  $view.innerHTML = pageHead("Status", { context: `${stBadge(s.running.length ? "running" : s.overall)}<span class="muted small">checked ${clock(s.now)}</span>`,
      actions: `<button class="ghost" id="strefresh" title="Re-read the run log and data freshness (does not run anything)">Re-check</button>` })
    + `${queuePanel(s)}<div class="sec-top">${MKTS.filter((x) => s.freshness[x.key]).map((x) => fresh(x.key)).join("")}</div>
    <p class="muted small">Web viewer: ${s.freshness.viewer.reports} reports loaded, last ${clock(s.freshness.viewer.reports_loaded_at)}.</p>`;
  $view.querySelector("#strefresh").onclick = () => route();
  wireQueuePanel($view);
  if (live) { const t = setTimeout(() => { if (alive()) route(); }, 5000); const prev = cleanup; cleanup = () => { clearTimeout(t); prev(); }; }
}

/** System → Runs: one run's steps and log (Resume when it failed part-way), the run history, and every job. */
async function runsPage(alive, runId) {
  document.title = "Runs · Trading";
  $view.innerHTML = LOADING;
  const s = await api("/api/status");
  const run = runId ? await api(`/api/status/run/${runId}`).catch(() => null) : s.latest_daily;
  if (!alive()) return;
  const steps = run?.steps || [];
  const done = steps.filter((x) => ["ok", "failed", "skipped", "interrupted"].includes(x.status)).length;
  const resumable = run && ["partial", "failed", "interrupted"].includes(run.status) && run.args?.targets;
  const stepRows = steps.map((x) => `<tr class="srow-${x.status}">
      <td>${stBadge(x.status)}</td><td><b>${esc(x.label || x.step)}</b>${x.market ? ` <span class="mkt">${MKT_BADGE[x.market] || x.market}</span>` : ""}</td>
      <td class="num muted">${x.started_at ? new Date(x.started_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : ""}</td>
      <td class="num">${x.status === "running" ? dur((Date.now() - new Date(x.started_at)) / 1000) + eta(x.eta_s) : dur(x.duration_s)}</td>
      <td class="sdetail">${esc(x.detail || "")}${x.error ? `<details><summary class="neg">${esc(x.error.split("\n")[0])}</summary><pre>${esc(x.error)}</pre></details>` : ""}</td></tr>`).join("");
  $view.innerHTML = pageHead("Runs") + `
    <section class="sec-card">
      ${run ? `<div class="sec-card-h"><h3>${runId ? `Run #${run.id}` : run.status === "running" ? "Running now" : "Latest run"}</h3>${stBadge(run.status)}
          <span class="muted small">${esc(run.job)}${run.args?.markets ? " · " + esc(run.args.markets.map((m) => MKT_BADGE[m] || m).join(" + ")) : ""} · started ${clock(run.started_at)} (${ago(run.started_at)})
          ${run.finished_at ? ` · took ${dur(run.duration_s)}` : run.status === "running" ? ` · running for ${dur((Date.now() - new Date(run.started_at)) / 1000)}${eta(run.eta_s)}` : ""}</span>
          <span class="spacer"></span>${resumable ? `<button class="primary sm" id="resume">↻ Resume</button>` : ""}${runId ? `<a class="small" href="#/runs">latest run</a>` : ""}</div>
        <div class="stprog"><i style="width:${steps.length ? (done / steps.length) * 100 : 0}%"></i></div>
        <div class="muted small" style="margin:4px 0 8px">${done} of ${steps.length} steps done${run.summary ? ` · ${esc(run.summary)}` : ""}${run.args?.strategies ? ` · strategies: ${esc(run.args.strategies.join(", "))}` : ""}</div>
        <table class="stt steps"><thead><tr><th></th><th>Step</th><th class="num">Started</th><th class="num">Took</th><th>Result</th></tr></thead><tbody>${stepRows}</tbody></table>
        ${run.log_tail ? `<details class="stlog"><summary>Log — last ${run.log_tail.length} lines of ${esc(run.log_path.split("/").slice(-1)[0])}</summary><pre>${esc(run.log_tail.join("\n"))}</pre></details>` : ""}`
      : `<div class="empty"><b>No run recorded yet</b><div class="muted">Run a pipeline from <a href="#/schedules">Schedules</a>.</div></div>`}
    </section>
    <section class="sec-card"><div class="sec-card-h"><h3>History</h3><span class="muted small">click a run for its steps and log</span></div>
      ${s.runs.length ? `<table class="stt hist"><thead><tr><th></th><th>Started</th><th>Job</th><th class="num">Took</th><th>Steps</th><th>Notes</th></tr></thead><tbody>
        ${s.runs.map((r) => `<tr data-id="${r.id}" class="${run && r.id === run.id ? "cur" : ""}"><td>${stBadge(r.status)}</td><td>${clock(r.started_at)} <span class="muted small">${ago(r.started_at)}</span></td>
          <td><b>${esc(r.job)}</b>${r.args?.markets ? ` <span class="muted small">${esc(r.args.markets.map((m) => MKT_BADGE[m] || m).join(" + "))}</span>` : ""}</td>
          <td class="num">${dur(r.duration_s)}</td>
          <td class="small">${r.steps ? `<span class="pos">${r.steps.ok} ok</span>${r.steps.failed ? ` · <span class="neg">${r.steps.failed} failed</span>` : ""}${r.steps.skipped ? ` · <span class="muted">${r.steps.skipped} skipped</span>` : ""}` : ""}</td>
          <td class="muted small">${esc(r.summary || "")}</td></tr>`).join("")}</tbody></table>` : '<div class="muted small">Nothing recorded yet.</div>'}</section>
    <details class="sec-card alljobs"><summary><h3>All jobs</h3><span class="muted small">each job's latest run per market — run a single job</span></summary>
      <table class="stt jobs"><thead><tr><th>Job</th><th>Layer</th><th>Cadence</th>${MKTS.map((m) => `<th>${esc(m.name)}</th>`).join("")}<th>What it does</th></tr></thead><tbody>
      ${s.jobs.map((j) => { const rb = (m) => `<button class="ibtn jrun" data-job="${j.name}" data-m="${m}" title="Run ${esc(j.name)}${m === "all" ? "" : " for " + MKT_BADGE[m]}"><svg viewBox="0 0 20 20" class="play"><path d="M7 5l8 5-8 5z"/></svg></button>`;
        const c = (x, m) => (x ? `<span title="${esc(x.detail || "")}">${stBadge(x.status)} <span class="muted small">${clock(x.at)}</span></span>` : '<span class="muted small">never</span>') + rb(m);
        return `<tr><td><b>${esc(j.name)}</b></td><td><span class="layer l-${j.layer}">${j.layer}</span></td><td class="muted">${j.cadence}${j.network ? "" : " · offline"}</td>
          ${j.per_market ? MKTS.map((m) => `<td>${c(j.last[m.key], m.key)}</td>`).join("") : `<td colspan="${MKTS.length}">${c(j.last.all, "all")}</td>`}<td class="muted small">${esc(j.summary.split(": ").slice(1).join(": ") || j.summary)}</td></tr>`; }).join("")}
      </tbody></table></details>`;
  $view.querySelectorAll(".stt.hist tbody tr").forEach((tr) => tr.onclick = () => go(`#/runs/${tr.dataset.id}`));
  $view.querySelectorAll(".jrun").forEach((b) => b.onclick = () => startJob({ title: `Run ${b.dataset.job}${b.dataset.m === "all" ? "" : " · " + MKT_BADGE[b.dataset.m]}`,
    targets: [b.dataset.job], market: b.dataset.m, screens: ["strategies", "backtest"].includes(b.dataset.job) }));
  $view.querySelector("#resume")?.addEventListener("click", async () => {
    const t = run.args.targets, m = run.args.markets?.length === 1 ? run.args.markets[0] : "all";
    startJob({ title: `Resume ${t.join(" + ")}`, targets: t, market: m, screens: t.some((x) => ["strategies", "backtest"].includes(x)), resumeFrom: await resumePoint(run) });
  });
  if (run?.status === "running") { const t = setTimeout(() => { if (alive()) route(); }, 5000); const prev = cleanup; cleanup = () => { clearTimeout(t); prev(); }; }
}

// ------------------------------------------------------------- navigation

/** Top-level sections in the order of a review — market, ideas, the stock, what I track, does it work —
 *  each with its pages (shown inline in the header, next to the open section, when there is more than one). */
const SECTIONS = [
  { key: "today", label: "Today", pages: [["today", "Today", "Your daily starting point: the market, the macro backdrop, today's setups, new picks and data health"]] },
  { key: "markets", label: "Markets", pages: [["postmarket", "Post-market", "The day's recap after the close"], ["breadth", "Breadth", "How healthy is the market — risk, not direction"],
    ["sectors", "Sectors", "Leading sectors, industry groups and their leaders"], ["movers", "Movers", "Top gainers and losers"]] },
  { key: "screens", label: "Screens", pages: [["screens", "Screens", "Built-in and your own screens: which stocks qualify"]] },
  { key: "strategies", label: "Strategies", pages: [["strategies", "Strategies", "Today's setups, and each strategy's rules and backtests"]] },
  { key: "chart", label: "Chart", pages: [["chart", "Chart", "Price chart, indicators and drawings"],
    ["company", "Fundamentals", "The company's financials: quarterly results, profit & loss, balance sheet, cash flows, ratios, shareholding, peers"],
    ["news", "News", "Headlines, filings and exchange announcements, and key events — earnings, dividends, splits, analyst ratings"]] },
  { key: "watchlists", label: "Watchlists", pages: [["watchlist", "Watchlists", "Your lists and the screener's picks"]] },
  // Library is reading material; the data-maintenance tools (TODO, sub-industry labels) live under System
  { key: "library", label: "Library", pages: [["notes", "Notes", "Your notes and trading journal"],
    ["research", "Research", "The research notes: findings, studies, specifications and the sector playbook"],
    ["learn", "Learn", "Learning material: candlesticks, chart patterns, bases and the VCP"]] },
  { key: "system", label: "System", pages: [["status", "Status", "Is the data current? And the job queue"], ["runs", "Runs", "Every run, its steps and log"],
    ["schedules", "Schedules", "When each pipeline runs — and run one now"], ["reports", "Reports archive", "Every backtest and screening report the scripts wrote"],
    ["subindustries", "Sub-industries", "Which sub-industry each company belongs to — review and edit"], ["todo", "TODO", "Ideas and follow-ups"]] },
];
/** the nav entry a URL belongs to: screens and strategies have one entry per screen / strategy */
function pageIdOf(parts) {
  const p = parts[0] || "today";
  return p === "screening" ? "strategies" : p === "quality" ? "screens" : p === "fundamentals" || p === "sepa" ? "company" : p;
}
const PAGE_SECTION = Object.fromEntries(SECTIONS.flatMap((s) => s.pages.map(([p]) => [p, s])));
const sectionOf = (id) => PAGE_SECTION[id] || PAGE_SECTION[id.split("/")[0]] || null;
const $nav = document.getElementById("nav"),
  $navbtn = document.getElementById("navbtn"), $navpanel = document.getElementById("navpanel");

/** The root page of a tab, in the market you are on. Clicking a tab always lands here — never on a
 *  drill-down remembered from an earlier visit (Back / Forward still restore those). */
const tabRoot = (p) => withMarket(`#/${p}`);
/** Top bar: one link per section (a section opens its first page — Markets opens Post-market). A section
 *  with several pages shows them as a tab row under the header, the same tabs pattern pages use inside. */
function renderNav(page) {
  const sec = sectionOf(page);
  // Chart, Fundamentals and News are views of one stock: each tab opens the stock on screen — read from the URL,
  // since the nav is drawn before the page stores it — else the stock you were last looking at
  const stockHref = (p) => {
    const [cur, um, us] = location.hash.replace(/^#\//, "").split("/").map(decodeURIComponent);
    const onStock = ["chart", "company", "news"].includes(cur) && isMarket(um) && us;
    const m = onStock ? um : store.get("lastMarket", MKTS[0]?.key || "us"), s = onStock ? us : store.get("lastSymbol:" + m, null);
    return s ? `#/${p}/${m}/${encodeURIComponent(s)}` : `#/${p}`;
  };
  const pageHref = (p) => esc(["chart", "company", "news"].includes(p) ? stockHref(p) : tabRoot(p));
  const secHref_ = (s) => esc(`#/${s.pages[0][0]}`);   // a section link always opens its home page
  $nav.innerHTML = SECTIONS.map((s, i) => `<a href="${secHref_(s)}" data-sec="${s.key}" data-href="${secHref_(s)}" class="sec ${s === sec ? "active" : ""}"
      title="${esc(s.pages.map((x) => x[1]).join(" · "))} (Alt+${i + 1})">${s.label}</a>`).join("");
  const sub = document.getElementById("subnav");
  sub.hidden = !(sec && sec.pages.length > 1);
  sub.innerHTML = sub.hidden ? "" : `<nav class="ptabs subtabs">${sec.pages.map(([p, t, d]) => `<a href="${pageHref(p)}" class="${p === page ? "active" : ""}" title="${esc(d)} — Alt+[ / Alt+] for the previous / next tab">${t}</a>`).join("")}</nav>`;
  const cur = sec && sec.pages.find(([p]) => p === page);
  $navbtn.innerHTML = `<svg viewBox="0 0 20 20"><path d="M3 5h14M3 10h14M3 15h14"/></svg><b>${sec ? sec.label : "Menu"}</b>${cur && sec.pages.length > 1 ? `<span>› ${cur[1]}</span>` : ""}`;
  $navpanel.innerHTML = SECTIONS.map((s, i) => `<div class="np-sec ${s === sec ? "cur" : ""}"><a class="np-h" href="${secHref_(s)}">${s.label}<kbd>Alt+${i + 1}</kbd></a>
    ${s.pages.length > 1 ? `<div class="np-pages">${s.pages.map(([p, t]) => `<a href="${pageHref(p)}" class="${p === page ? "active" : ""}">${t}</a>`).join("")}</div>` : ""}</div>`).join("");
  closeNavPanel();
}
function closeNavPanel() { $navpanel.hidden = true; $navbtn.setAttribute("aria-expanded", "false"); }
$navbtn.onclick = (e) => { e.stopPropagation(); $navpanel.hidden = !$navpanel.hidden; $navbtn.setAttribute("aria-expanded", String(!$navpanel.hidden)); };
document.addEventListener("click", (e) => { if (!$navpanel.hidden && !$navpanel.contains(e.target)) closeNavPanel(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeNavPanel(); });
// Alt+1…N: jump to a section (N = number of SECTIONS; the ? help lists them from SECTIONS); Alt+[ / Alt+]: previous / next tab in the section
document.addEventListener("keydown", (e) => {
  if (!e.altKey || e.metaKey || e.ctrlKey || e.target.closest?.("input, select, textarea")) return;
  const n = /^Digit([1-9])$/.exec(e.code)?.[1];
  if (n && SECTIONS[n - 1]) { e.preventDefault(); go($nav.querySelector(`[data-sec="${SECTIONS[n - 1].key}"]`).dataset.href); return; }
  if (e.code === "Digit0") { e.preventDefault(); go("#/status"); return; }
  if (e.code === "BracketLeft" || e.code === "BracketRight") {
    const page = pageIdOf(location.hash.replace(/^#\//, "").split("/").map(decodeURIComponent)), sec = sectionOf(page);
    if (!sec || sec.pages.length < 2) return;
    const i = sec.pages.findIndex(([p]) => p === page), j = (i + (e.code === "BracketRight" ? 1 : -1) + sec.pages.length) % sec.pages.length;
    e.preventDefault(); go(tabRoot(sec.pages[j][0]));
  }
});

// ⌘K / Ctrl+K: go anywhere — a page by name, or a stock by symbol or company name
function openPalette() {
  if (document.querySelector(".palette")) return;
  const pages = [...SECTIONS.flatMap((s) => s.pages.map(([p, t, d]) => ({ kind: "page", label: t, sub: `${s.label} · ${d}`, href: tabRoot(p) }))),
    ...THEMES.map(([k, t]) => ({ kind: "page", label: `Theme: ${t}`, sub: "Change the colour theme", theme: k }))];
  const m = el(`<div class="smodal palette"><div class="pal-card"><input placeholder="Go to a page, or a stock (symbol or company)…" spellcheck="false"><div class="pal-list"></div>
    <div class="pal-foot muted small">↑ ↓ to move · Enter to open · Esc to close</div></div></div>`);
  document.body.append(m);
  const inp = m.querySelector("input"), host = m.querySelector(".pal-list");
  let items = [], cur = 0, timer, seq = 0, state = "";   // state: "" | "searching" | "failed"
  const draw = () => {
    host.innerHTML = items.map((x, i) => `<div class="pal-it ${i === cur ? "sel" : ""}" data-i="${i}"><span class="pal-k">${x.kind === "page" ? "Page" : x.kind === "recent" ? "Recent" : x.kind === "learn" ? "Learn" : MKT_BADGE[x.market]}</span>
      <b>${esc(x.label)}</b><span class="muted small">${esc(x.sub || "")}</span></div>`).join("")
      + (state === "searching" ? '<div class="muted small pal-none"><span class="spin"></span> Searching stocks…</div>'
        : state === "failed" ? '<div class="small pal-none neg">Stock search failed — is the web server running?</div>'
        : items.length ? "" : `<div class="muted small pal-none">No page, pattern or stock matches “${esc(inp.value.trim())}”. Try a ticker (AAPL, RELIANCE) or part of a company name.</div>`);
    host.querySelector(".sel")?.scrollIntoView({ block: "nearest" });
  };
  const learnItems = Learn.PATTERNS.filter((x) => x.group !== "basics").map((x) => ({ kind: "learn", label: x.name,
    sub: `${Learn.FAMILY_LABEL[Learn.familyOf(x)]} · ${(Learn.GROUPS.find((g) => g[0] === x.group) || [])[1] || ""}`, href: `#/learn/${x.key}` }));
  api("/api/reports?kind=research").then((runs) => { runs.filter((x) => x.run.startsWith("learn-")).forEach((x) =>
    learnItems.push({ kind: "learn", label: guideLabel(x), sub: "Learn · guide", href: `#/learn/${x.run.replace(/^learn-/, "")}` })); }).catch(() => {});
  const recent = (store.get("recentVisits", []) || []).filter((x) => x.hash !== location.hash)
    .map((x) => ({ kind: "recent", label: x.label, sub: x.hash.replace(/^#\//, "").split("/")[0], href: x.hash }));
  const update = async () => {
    const q = inp.value.trim().toLowerCase(), my = ++seq;
    const pg = pages.filter((p) => !q || p.label.toLowerCase().includes(q) || p.sub.toLowerCase().includes(q));
    const lr = q ? learnItems.filter((x) => x.label.toLowerCase().includes(q)).slice(0, 5) : [];
    items = q ? [...pg.slice(0, 6), ...lr] : [...recent, ...pg].slice(0, 24); cur = 0; state = q ? "searching" : ""; draw();
    if (q.length < 1) return;
    const syms = await api(`/api/symbols?q=${encodeURIComponent(q)}&limit=8`).catch(() => null);
    if (my !== seq) return;
    state = syms ? "" : "failed";
    items = [...pg.slice(0, 5), ...lr, ...(syms || []).map((r) => ({ kind: "symbol", market: r.market, label: r.symbol.replace(/\.NS$/, ""), sub: r.name || r.sector || "",
      href: `#/chart/${r.market}/${encodeURIComponent(r.symbol)}` }))];
    cur = 0; draw();
  };
  const close = () => { m.remove(); };
  const pick = (i) => { const x = items[i]; if (!x) return; close(); if (x.theme) applyTheme(x.theme); else go(x.href); };
  inp.oninput = () => { clearTimeout(timer); timer = setTimeout(update, 90); };
  inp.onkeydown = (e) => {
    e.stopPropagation();
    if (e.key === "ArrowDown") { cur = Math.min(cur + 1, items.length - 1); draw(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { cur = Math.max(cur - 1, 0); draw(); e.preventDefault(); }
    else if (e.key === "Enter") { e.preventDefault(); pick(cur); }
    else if (e.key === "Escape") close();
  };
  host.onclick = (e) => { const it = e.target.closest("[data-i]"); if (it) pick(+it.dataset.i); };
  m.onclick = (e) => { if (e.target === m) close(); };
  inp.focus(); update();
}
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); e.stopImmediatePropagation(); openPalette(); }
}, true);

/** Learn is organised by TOPIC — Macro, Market health, Sectors & groups, Fundamentals, Risk & trade management, Process & psychology, Price & volume, Testing ideas, Candlesticks, Chart patterns, Levels & zones — and each topic holds both its guides
 *  (long-form reading, research/learn-*.md) and its patterns (every pattern drawn, learn.js), so a subject
 *  appears in the menu once. #/learn is the hub; #/learn/candles, /charts, /levels a topic's pattern grid;
 *  #/learn/<pattern> a pattern; #/learn/<guide> a guide. */
const GUIDE_ORDER = ["learn-start-here", "learn-macro-rates", "learn-macro-yield-curve", "learn-macro-inflation", "learn-macro-cycle", "learn-macro-currencies", "learn-macro-liquidity-credit", "learn-macro-commodities", "learn-macro-calendar",
  "learn-health-trend", "learn-health-breadth", "learn-health-volatility", "learn-health-distribution",
  "learn-sectors-groups",
  "learn-fund-earnings", "learn-fund-valuation", "learn-fund-quality",
  "learn-risk-expectancy", "learn-risk-sizing", "learn-risk-stops-exits", "learn-risk-portfolio",
  "learn-process-plan", "learn-process-journal", "learn-process-biases",
  "learn-price-stages", "learn-price-volume", "learn-price-rs", "learn-price-indicators", "learn-price-oscillators",
  "learn-strat-overview", "learn-strat-ma-trend", "learn-strat-channel-breakout", "learn-strat-stage-analysis", "learn-strat-livermore", "learn-strat-canslim-breakout", "learn-strat-vcp-sepa", "learn-strat-kullamagi", "learn-strat-zanger", "learn-strat-morales-kacher", "learn-strat-darvas", "learn-strat-flags", "learn-strat-pullback-ma", "learn-strat-pullback-support", "learn-strat-retracements", "learn-strat-xs-momentum", "learn-strat-vol-scaled-momentum", "learn-strat-dual-momentum", "learn-strat-sector-rotation", "learn-strat-rs-leaders", "learn-strat-earnings-gaps", "learn-strat-pead", "learn-strat-index-news-events", "learn-strat-rsi2", "learn-strat-bollinger-reversion", "learn-strat-gap-fills", "learn-strat-failed-breakouts", "learn-strat-stage4-shorts", "learn-strat-squeezes-bear-rallies", "learn-strat-orb", "learn-strat-vwap", "learn-strat-intraday-momentum", "learn-strat-spec", "learn-strat-combining", "learn-strat-regime-filters",
  "learn-fno-overview", "learn-fno-futures-basics", "learn-fno-futures-basis", "learn-fno-futures-trading", "learn-fno-options-basics", "learn-fno-pricing-greeks", "learn-fno-volatility", "learn-fno-option-chain", "learn-fno-expiry", "learn-fno-directional", "learn-fno-income", "learn-fno-vol-strategies", "learn-fno-hedging", "learn-fno-event-trades", "learn-fno-india-rules", "learn-fno-risk-sizing", "learn-system-filters",
  "learn-test-backtesting",
  "learn-candlestick-patterns", "learn-chart-patterns", "learn-bases", "learn-vcp", "learn-support-resistance", "learn-supply-demand", "learn-order-flow-smc"];
/** the topic a guide belongs to; a guide not listed here goes under "More guides" */
const GUIDE_TOPIC = {"learn-start-here": "start", "learn-macro-rates": "macro", "learn-macro-yield-curve": "macro", "learn-macro-inflation": "macro", "learn-macro-cycle": "macro", "learn-macro-currencies": "macro", "learn-macro-liquidity-credit": "macro", "learn-macro-commodities": "macro", "learn-macro-calendar": "macro",
  "learn-health-trend": "health", "learn-health-breadth": "health", "learn-health-volatility": "health", "learn-health-distribution": "health",
  "learn-sectors-groups": "sectors",
  "learn-fund-earnings": "fundamentals", "learn-fund-valuation": "fundamentals", "learn-fund-quality": "fundamentals",
  "learn-risk-expectancy": "risk", "learn-risk-sizing": "risk", "learn-risk-stops-exits": "risk", "learn-risk-portfolio": "risk",
  "learn-process-plan": "process", "learn-process-journal": "process", "learn-process-biases": "process",
  "learn-price-stages": "price", "learn-price-volume": "price", "learn-price-rs": "price", "learn-price-indicators": "price", "learn-price-oscillators": "price",
  "learn-strat-overview": "strategies", "learn-strat-ma-trend": "strategies", "learn-strat-channel-breakout": "strategies", "learn-strat-stage-analysis": "strategies", "learn-strat-livermore": "strategies", "learn-strat-canslim-breakout": "strategies", "learn-strat-vcp-sepa": "strategies", "learn-strat-kullamagi": "strategies", "learn-strat-zanger": "strategies", "learn-strat-morales-kacher": "strategies", "learn-strat-darvas": "strategies", "learn-strat-flags": "strategies", "learn-strat-pullback-ma": "strategies", "learn-strat-pullback-support": "strategies", "learn-strat-retracements": "strategies", "learn-strat-xs-momentum": "strategies", "learn-strat-vol-scaled-momentum": "strategies", "learn-strat-dual-momentum": "strategies", "learn-strat-sector-rotation": "strategies", "learn-strat-rs-leaders": "strategies", "learn-strat-earnings-gaps": "strategies", "learn-strat-pead": "strategies", "learn-strat-index-news-events": "strategies", "learn-strat-rsi2": "strategies", "learn-strat-bollinger-reversion": "strategies", "learn-strat-gap-fills": "strategies", "learn-strat-failed-breakouts": "strategies", "learn-strat-stage4-shorts": "strategies", "learn-strat-squeezes-bear-rallies": "strategies", "learn-strat-orb": "strategies", "learn-strat-vwap": "strategies", "learn-strat-intraday-momentum": "strategies", "learn-strat-spec": "strategies", "learn-strat-combining": "strategies", "learn-strat-regime-filters": "strategies",
  "learn-fno-overview": "fno", "learn-fno-futures-basics": "fno", "learn-fno-futures-basis": "fno", "learn-fno-futures-trading": "fno", "learn-fno-options-basics": "fno", "learn-fno-pricing-greeks": "fno", "learn-fno-volatility": "fno", "learn-fno-option-chain": "fno", "learn-fno-expiry": "fno", "learn-fno-directional": "fno", "learn-fno-income": "fno", "learn-fno-vol-strategies": "fno", "learn-fno-hedging": "fno", "learn-fno-event-trades": "fno", "learn-fno-india-rules": "fno", "learn-fno-risk-sizing": "fno", "learn-system-filters": "system",
  "learn-test-backtesting": "system",
   "learn-candlestick-patterns": "candles", "learn-chart-patterns": "charts", "learn-bases": "charts",
  "learn-vcp": "charts", "learn-support-resistance": "levels", "learn-supply-demand": "levels", "learn-order-flow-smc": "levels" };
/** a sub-heading for a guide inside its topic's menu — for a topic large enough to need categories
 *  (Strategies: "Trend following", "Breakouts from a base", ...). Guides without one sit under "Guides". */
const GUIDE_GROUP = {
  "learn-strat-overview": "Start here",
  "learn-strat-ma-trend": "Trend following",
  "learn-strat-channel-breakout": "Trend following",
  "learn-strat-stage-analysis": "Trend following",
  "learn-strat-livermore": "Trend following",
  "learn-strat-canslim-breakout": "Breakouts from a base",
  "learn-strat-vcp-sepa": "Breakouts from a base",
  "learn-strat-kullamagi": "Breakouts from a base",
  "learn-strat-zanger": "Breakouts from a base",
  "learn-strat-morales-kacher": "Breakouts from a base",
  "learn-strat-darvas": "Breakouts from a base",
  "learn-strat-flags": "Breakouts from a base",
  "learn-strat-pullback-ma": "Pullbacks in a trend",
  "learn-strat-pullback-support": "Pullbacks in a trend",
  "learn-strat-retracements": "Pullbacks in a trend",
  "learn-strat-xs-momentum": "Momentum and relative strength",
  "learn-strat-vol-scaled-momentum": "Momentum and relative strength",
  "learn-strat-dual-momentum": "Momentum and relative strength",
  "learn-strat-sector-rotation": "Momentum and relative strength",
  "learn-strat-rs-leaders": "Momentum and relative strength",
  "learn-strat-earnings-gaps": "Event-driven",
  "learn-strat-pead": "Event-driven",
  "learn-strat-index-news-events": "Event-driven",
  "learn-strat-rsi2": "Mean reversion",
  "learn-strat-bollinger-reversion": "Mean reversion",
  "learn-strat-gap-fills": "Mean reversion",
  "learn-strat-failed-breakouts": "Reversals and the short side",
  "learn-strat-stage4-shorts": "Reversals and the short side",
  "learn-strat-squeezes-bear-rallies": "Reversals and the short side",
  "learn-strat-orb": "Intraday",
  "learn-strat-vwap": "Intraday",
  "learn-strat-intraday-momentum": "Intraday",
  "learn-strat-spec": "Building your own",
  "learn-strat-combining": "Building your own",
  "learn-strat-regime-filters": "Building your own",
  "learn-fno-overview": "Start here",
  "learn-fno-futures-basics": "Futures",
  "learn-fno-futures-basis": "Futures",
  "learn-fno-futures-trading": "Futures",
  "learn-fno-options-basics": "Options basics",
  "learn-fno-pricing-greeks": "Options basics",
  "learn-fno-volatility": "Options basics",
  "learn-fno-option-chain": "Options basics",
  "learn-fno-expiry": "Options basics",
  "learn-fno-directional": "Option strategies",
  "learn-fno-income": "Option strategies",
  "learn-fno-vol-strategies": "Option strategies",
  "learn-fno-hedging": "Option strategies",
  "learn-fno-event-trades": "Option strategies",
  "learn-fno-india-rules": "Rules, costs and risk",
  "learn-fno-risk-sizing": "Rules, costs and risk",
};
const GUIDE_BLURB = {
  "learn-strat-overview": "The map of trading strategies: what a complete strategy is, the categories, and how to choose one that fits you.",
  "learn-strat-ma-trend": "Own a stock or index while it is above a moving average and step aside below it — rules, parameters and whipsaws.",
  "learn-strat-channel-breakout": "Donchian and Turtle-style trend following: buy the new high, exit on the new low, size by volatility.",
  "learn-strat-stage-analysis": "Weinstein's method: buy the Stage 2 breakout above a rising 30-week line and hold until the stage turns.",
  "learn-strat-canslim-breakout": "O'Neil's CAN SLIM: buying a leader as it clears a cup, double bottom or flat base, with his selling rules.",
  "learn-strat-livermore": "Livermore's pivotal points: buying new high ground, pyramiding into a winner, sister stocks, and sitting tight.",
  "learn-strat-vcp-sepa": "Minervini's SEPA: the Trend Template, the volatility contraction, the pivot, and how he manages a trade.",
  "learn-strat-kullamagi": "Kullamägi's momentum breakouts: the fastest stocks, a tight rest, an opening-range entry, and selling in stages.",
  "learn-strat-zanger": "Zanger's chart breakouts: trendlines and flat tops in liquid leaders, heavy volume, quick exits and selling the climax.",
  "learn-strat-morales-kacher": "Morales and Kacher: pocket pivots inside a base, buyable gap-ups on news, and the 7-week rule for selling.",
  "learn-strat-darvas": "Darvas boxes: buying a breakout from a tight range at new highs and trailing the stop box by box.",
  "learn-strat-flags": "Flags, pennants and high tight flags: buying the brief pause inside a fast move, and why they fail.",
  "learn-strat-pullback-ma": "Buying a dip to the 21-day or 50-day average inside an uptrend, entering as it turns back up.",
  "learn-strat-pullback-support": "Buying the retest of a breakout level or demand zone, with the stop just beyond it.",
  "learn-strat-retracements": "Fibonacci retracements and measured moves, tested honestly: common reference levels, not magic ones.",
  "learn-strat-xs-momentum": "Rank the market by its past year's return, hold the strongest, rotate monthly — and survive momentum crashes.",
  "learn-strat-vol-scaled-momentum": "Rank by the past year's return per unit of volatility, hold the steadiest 20, size each inversely to its risk.",
  "learn-strat-dual-momentum": "Antonacci's dual momentum: own the strongest asset, and step aside to bonds or cash when nothing beats cash.",
  "learn-strat-sector-rotation": "Holding the strongest sectors and moving as leadership changes — by relative strength or the business cycle.",
  "learn-strat-rs-leaders": "Buying the strongest stocks in the strongest groups as a correction ends, and when that works.",
  "learn-strat-earnings-gaps": "Buying a big results-day gap on heavy volume — the episodic pivot — with its entry, stop and hold rules.",
  "learn-strat-pead": "Post-earnings drift: trading the slow reaction to strong results, and where the effect is still alive.",
  "learn-strat-index-news-events": "Index additions, splits and bonus issues, buybacks and block deals: trading the event calendar.",
  "learn-strat-rsi2": "Connors' RSI(2): buying short, sharp dips in an uptrend and selling the bounce — on indices and stocks.",
  "learn-strat-bollinger-reversion": "Buying the lower Bollinger band in a range, and recognising the trend that walks the band instead.",
  "learn-strat-gap-fills": "Do gaps always fill? Measured, plus when to fade a gap and when to ride it.",
  "learn-strat-failed-breakouts": "When a breakout fails: recognising the bull trap, exiting a long, and shorting it.",
  "learn-strat-stage4-shorts": "Shorting a stock already in Stage 4: breakdowns, failed rallies to a falling line, and the risks of shorting.",
  "learn-strat-squeezes-bear-rallies": "Short squeezes and bear-market rallies: why they happen, how to survive them, and whether to trade them.",
  "learn-strat-orb": "The opening-range breakout: trading the first decisive move of the day, and the days it works best.",
  "learn-strat-vwap": "VWAP pullbacks, VWAP reversion and anchored VWAP from an event — trading around the day's average price.",
  "learn-strat-intraday-momentum": "Trend days and range days, and whether the morning predicts the afternoon — after realistic costs.",
  "learn-strat-spec": "Turning an idea into a testable strategy: universe, setup, entry, stop, exits and sizing, every number named.",
  "learn-strat-combining": "Choosing and combining strategies: matching them to market regimes, correlation, and splitting capital.",
  "learn-strat-regime-filters": "Market trend, breadth and volatility filters on top of any strategy — how to choose one and what it costs.",
  "learn-fno-overview": "What futures and options are for, how they differ, the honest odds for retail traders, and the order to read these guides in.",
  "learn-fno-futures-basics": "Lots, contract value, margin, daily mark-to-market, expiry and settlement — how an Indian futures contract actually works.",
  "learn-fno-futures-basis": "Why a future trades above the index, what rolling costs, and what open interest with price can and cannot tell you.",
  "learn-fno-futures-trading": "Leverage done carefully, swing-shorting a stock through futures, hedging a portfolio with Nifty futures, and pair trades.",
  "learn-fno-options-basics": "Calls and puts, moneyness, intrinsic and time value, buyer and seller payoffs, exercise, and physical settlement.",
  "learn-fno-pricing-greeks": "What moves an option's price — the underlying, time, volatility — and delta, gamma, theta and vega with real Nifty examples.",
  "learn-fno-volatility": "Implied against realised volatility, India VIX's history, IV rank and percentile, the skew, and the crush after events.",
  "learn-fno-option-chain": "Reading a real Nifty chain: open interest and its change, the put/call ratio, max pain, and liquidity — and their limits.",
  "learn-fno-expiry": "What happens in an option's last days: faster time decay, gamma risk, weekly expiries, pinning, and India's expiry-day rules.",
  "learn-fno-directional": "Long calls and puts and debit spreads: trading a view with defined risk, and choosing the strike and the expiry.",
  "learn-fno-income": "Covered calls, cash-secured puts, credit spreads and iron condors — why selling options wins often and loses big.",
  "learn-fno-vol-strategies": "Straddles, strangles, butterflies, calendars and ratio spreads: trading volatility itself rather than direction.",
  "learn-fno-hedging": "Protective puts, collars and index hedges for a stock portfolio, and what insurance costs over the years.",
  "learn-fno-event-trades": "Results, RBI policy, the Budget and elections: the move options price in, the volatility crush, and what actually happened.",
  "learn-fno-india-rules": "India's F&O rules, costs and tax in one place: lot sizes, margins, upfront premium, expiries, STT and a full round-trip cost.",
  "learn-fno-risk-sizing": "Notional against margin, sizing by the maximum loss, gap risk, margin calls and assignment — and how F&O accounts blow up.",
  "learn-start-here": "What a share, an index and a chart are; how a trade happens and what it costs; percent, annualised and R. The floor every other guide stands on.",
  "learn-macro-rates": "What the Fed and the RBI do, why the price of money sets every valuation, and which sectors feel it first.",
  "learn-macro-yield-curve": "Bond yields, the shape of the curve, inversions and recessions, and why the 10-year moves growth stocks.",
  "learn-macro-inflation": "CPI, core and India's food-heavy basket: how inflation reaches rates, margins and sector leadership.",
  "learn-macro-cycle": "Jobs, PMIs and GDP, the four phases of the cycle, and the ratios that show rotation as it happens.",
  "learn-macro-currencies": "The dollar, the rupee and foreign flows: who wins and loses when currencies move.",
  "learn-macro-liquidity-credit": "QE and QT, credit spreads and volatility: the plumbing that warns before stocks do.",
  "learn-macro-commodities": "Oil, gold and copper as reads on inflation, fear and growth, and what they mean for India.",
  "learn-macro-calendar": "The US and India events that move markets, and how a swing trader plans around them.",
  "learn-health-trend": "Is the market in an uptrend? Index averages, stages, drawdowns, and the regime the app's strategies obey.",
  "learn-health-breadth": "How many stocks are taking part: % above averages, new highs vs lows, the A/D line, and narrow rallies.",
  "learn-health-volatility": "VIX, India VIX and sentiment: what fear prices, when extremes matter, and how the app sizes for it.",
  "learn-health-distribution": "O'Neil's distribution days and follow-through days: spotting tops and new uptrends from index volume.",
  "learn-sectors-groups": "Why leaders cluster in leading groups, how the Sectors page rates them, and how money rotates between them.",
  "learn-fund-earnings": "EPS and sales growth, acceleration, surprises and guidance — what earnings do to a stock, and when.",
  "learn-fund-valuation": "P/E, PEG and EV/EBITDA for traders: why leaders look expensive, and when valuation does matter.",
  "learn-fund-quality": "Margins, returns, debt and cash flow; CAN SLIM and SEPA's fundamentals; the app's Quality and Fundamentals pages.",
  "learn-risk-expectancy": "Win rate times average win against loss rate times average loss — measured on this app's own backtest trades.",
  "learn-risk-sizing": "Risk per trade, R, stop distance and position size: how much to buy, and how the app sizes it.",
  "learn-risk-stops-exits": "Initial stops, gaps through them, breakeven and trailing stops, targets, and selling into strength or weakness.",
  "learn-system-filters": "How thousands of stocks become one trade: the six stages between a universe and a position, and why each must answer a different question.",
  "learn-test-backtesting": "Overfitting, look-ahead, survivorship and costs — how a backtest fools you, with this app's own examples.",
  "learn-price-stages": "A stock's four stages, the trend template, and how to tell an uptrend that is starting from one that is ending.",
  "learn-price-volume": "What volume says about who is buying: breakouts on volume, dry-ups in bases, climaxes and distribution in a stock.",
  "learn-price-rs": "Relative strength: the RS line and RS rating, why leaders show strength first, and how the app ranks it.",
  "learn-price-indicators": "Moving averages, ATR and ADX — what an indicator is, and what each trend and volatility measure adds beyond price.",
  "learn-price-oscillators": "RSI, MACD and Bollinger Bands, the Chart page's studies, and how much indicators repeat each other — measured.",
  "learn-process-plan": "A written plan and a daily and weekly routine — what to check, in what order, using this app's pages.",
  "learn-process-journal": "What to record on every trade, and how to review it to find what actually works — and what doesn't.",
  "learn-process-biases": "Loss aversion, FOMO, revenge trading, anchoring and overconfidence — what each costs, measured on the app's trades.",
  "learn-risk-portfolio": "Open risk across positions, correlation and sector clusters, drawdowns and the arithmetic of recovering.",
  "learn-candlestick-patterns": "Reading candles: anatomy, the one-, two- and three-bar patterns, context, and how the screener's candle notes use them.",
  "learn-chart-patterns": "The bases this app detects, topping structures, how to judge a breakout — and what the backtests found.",
  "learn-bases": "What a base is, Stage 2 and base counts, the common base types, and how to spot one while it is still forming.",
  "learn-vcp": "Minervini's volatility contraction pattern: reading one step by step, entries, stops, mistakes and the evidence.",
  "learn-support-resistance": "Drawing support and resistance: zones not lines, higher timeframes first, grading a level, and what to do at breakouts, retests and new highs.",
  "learn-supply-demand": "Why price levels exist: demand and supply zones, role reversal, scoring a zone, and how the strategies use them.",
  "learn-order-flow-smc": "Order flow, smart money concepts and liquidity: what the terms mean, the older ideas they rename, and what the evidence supports.",
};
/** a guide's name in links and titles: "Candlestick patterns: field guide", "Bases", "VCP" */
const guideTitle = (x) => String(x.title || x.run);
const guideLabel = (x) => { const t = guideTitle(x); return / — a field guide$/.test(t) ? t.replace(/ — a field guide$/, ": field guide") : t.split(" — ")[0]; };
/** inside its topic the topic is already named, so "Candlestick patterns: field guide" (or a guide named
 *  for the topic, "Supply and demand") is just "Field guide" */
const guideShort = (x, t) => { const l = guideLabel(x), norm = (s) => s.toLowerCase().replace(/&/g, "and");
  if (/: field guide$/.test(l)) return "Field guide";
  if (norm(l) !== norm(Learn.FAMILY_LABEL[t] || "")) return l;
  const sub = guideTitle(x).split(" — ")[1];
  return sub ? sub[0].toUpperCase() + sub.slice(1) : "Field guide"; };
// the learning path: context (macro, the market) -> reading a stock (price, candles, patterns, levels, fundamentals)
// -> trading it (risk, process) -> building and testing a system of your own
const LEARN_TOPICS = ["start", "macro", "health", "sectors", "price", "candles", "charts", "levels", "fundamentals", "strategies", "fno", "risk", "process", "system"];
/** a topic with more patterns than this gets an "All N patterns" grid to compare their shapes; a smaller one
 *  lists its patterns directly (its guide already covers them), and gains the grid once it grows */
const TOPIC_GRID_MIN = 6;
const TOPIC_BLURB = { candles: "single candles to three-bar reversals", charts: "bases and topping structures",
  levels: "support and resistance, demand and supply zones, and role reversal" };

async function learnPage(alive, topic, sub) {
  $view.innerHTML = LOADING;
  const rank = (x) => (GUIDE_ORDER.includes(x.run) ? GUIDE_ORDER.indexOf(x.run) : GUIDE_ORDER.length);
  const runs = (await api("/api/reports?kind=research").catch(() => [])).filter((x) => x.run.startsWith("learn-"))
    .sort((a, b) => rank(a) - rank(b) || a.run.localeCompare(b.run));
  if (!alive()) return;
  const guide = runs.find((x) => x.run === `learn-${topic}`);
  const p = !guide && topic && Learn.get(topic);
  const catView = LEARN_TOPICS.includes(topic) ? topic : null;
  const topicOf = (g) => GUIDE_TOPIC[g.run] || "more";
  const guidesIn = (t) => runs.filter((x) => topicOf(x) === t);
  const hasGrid = (t) => Learn.countOf(t) > TOPIC_GRID_MIN;
  const guideHref = (x) => `#/learn/${esc(x.run.replace(/^learn-/, ""))}`;
  /** where a topic's links lead: its pattern grid, or (without one) its first guide */
  const topicHome = (t) => (hasGrid(t) ? `#/learn/${t}` : guidesIn(t)[0] ? guideHref(guidesIn(t)[0]) : "#/learn");
  if (catView && !hasGrid(catView)) { location.replace(topicHome(catView)); return; }
  const fam = p ? Learn.familyOf(p) : catView || (guide && topicOf(guide)) || store.get("learnFam", "candles");
  if (LEARN_TOPICS.includes(fam)) store.set("learnFam", fam);
  document.title = `${topic === "glossary" ? "Glossary · " : p ? p.name + " · " : guide ? guideLabel(guide) + " · " : catView ? Learn.FAMILY_LABEL[catView] + " · " : ""}Learn · Trading`;

  // ---- sidebar: one sub-menu per topic, each with its guides first and then its patterns.
  // The topic holding the page you are on is open; the others are closed until you open them.
  const openSec = topic ? fam : null;
  const sec = (key, title, count, body) => `<details class="lp-sec" data-sec="${key}" ${key === openSec ? "open" : ""}>
      <summary><span>${esc(title)}</span>${count != null ? `<span class="n">${count}</span>` : ""}</summary><div class="lp-sub">${body}</div></details>`;
  const groupHead = (x, i, list) => (GUIDE_GROUP[x.run] || "") !== (i ? GUIDE_GROUP[list[i - 1].run] || "" : null)
    ? `<div class="nav-h">${esc(GUIDE_GROUP[x.run] || (list.length > 1 ? "Guides" : "Guide"))}</div>` : "";
  const guideItems = (list, t) => list.length ? list.map((x, i) => groupHead(x, i, list) + `<a class="nav-item ${guide && x.id === guide.id ? "active" : ""}" href="${guideHref(x)}" title="${esc(guideTitle(x))}" data-k="${esc((guideLabel(x) + " guide").toLowerCase())}"><span><b class="sn">${esc(t ? guideShort(x, t) : guideLabel(x))}</b></span></a>`).join("") : "";
  const topicItems = (t) => guideItems(guidesIn(t), t) + (hasGrid(t) ? `<div class="nav-h">Patterns</div>`
    + `<a class="nav-item lp-allp ${catView === t ? "active" : ""}" href="#/learn/${t}"><span><b class="sn">All ${Learn.countOf(t)} patterns</b></span></a>` : "") + Learn.nav(p?.key, t);
  const more = guidesIn("more");
  const menu = `<a class="nav-item ${!topic ? "active" : ""}" href="#/learn"><span><b class="sn">Learn — start here</b></span></a>
    <a class="nav-item ${topic === "glossary" ? "active" : ""}" href="#/learn/glossary" data-k="glossary terms definitions"><span><b class="sn">Glossary</b></span></a>
    <label class="filter lp-search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input id="lpf" placeholder="Find a guide or pattern" spellcheck="false"></label>
    ${LEARN_TOPICS.map((t) => sec(t, Learn.FAMILY_LABEL[t], null, topicItems(t))).join("")}
    ${more.length ? sec("more", "More guides", more.length, guideItems(more, null)) : ""}
    <div class="nav-empty muted small lp-none" hidden></div>`;

  // ---- main pane
  const guideCard = (x) => `<a class="sec-card lp-hubc" href="${guideHref(x)}">
      <b>${esc(guideLabel(x))}</b><span class="muted small">${esc(GUIDE_BLURB[x.run] || guideTitle(x))}</span></a>`;
  const patternsCard = (f) => {
    const sample = Learn.PATTERNS.filter((x) => Learn.familyOf(x) === f && x.group !== "basics").slice(0, 3);
    return `<a class="sec-card lp-hubc lp-hubcat" href="#/learn/${f}"><b>All ${Learn.countOf(f)} patterns</b><span class="muted small">Each drawn with real candles: ${TOPIC_BLURB[f]}.</span>
        <div class="lp-hubthumbs">${sample.map((x) => Learn.svg(x, { thumb: true })).join("")}</div></a>`; };
  /** a small topic's patterns, one card each, in place of its grid */
  const patternCards = (f) => Learn.PATTERNS.filter((x) => Learn.familyOf(x) === f).map((x) => `<a class="sec-card lp-hubc" href="#/learn/${x.key}">
      <b>${esc(x.name)}</b><div class="lp-hubthumbs one">${Learn.svg(x, { thumb: true })}</div></a>`).join("");
  /** Every defined term, A-Z. The hover definitions inside a guide are for a
   *  reader mid-sentence; this is for one who wants to look a word up, or to
   *  see what vocabulary the guides assume before starting. */
  const glossaryView = () => {
    const terms = typeof Glossary === "undefined" ? [] : Glossary.all();
    let letter = "";
    const body = terms.map((e) => {
      const L = e.t[0].toUpperCase(), head = L === letter ? "" : `<div class="gl-letter" id="gl-${L}">${L}</div>`;
      letter = L;
      const aka = (e.aka || []).filter((a) => a.toLowerCase() !== e.t.toLowerCase());
      return head + `<div class="gl-item"><b>${esc(e.t)}</b>${aka.length ? `<span class="gl-aka">also: ${esc(aka.slice(0, 4).join(", "))}</span>` : ""}
        <p>${esc(e.d)}</p>${e.eg ? `<p class="gl-eg">${esc(e.eg)}</p>` : ""}
        ${e.more && runs.some((r) => r.run === e.more) ? `<p class="gl-more"><a href="#/learn/${esc(e.more.replace(/^learn-/, ""))}">Explained in full in ${esc(guideLabel(runs.find((r) => r.run === e.more)))}</a></p>` : ""}</div>`;
    }).join("");
    return pageHead("Glossary", { context: info("<p>Every term the guides define, in one place. Inside a guide these same definitions appear on the word itself — hover it, or tap on a phone — so you rarely need this page while reading.</p><p>A term is marked once per guide, at its first use.</p>") })
      + `<p class="sd-lead">${terms.length} terms. In a guide, a <span style="text-decoration:underline dotted">dotted underline</span> means a definition is available on the word.</p>
         <div class="gl-page">${body}</div>`;
  };

  const hub = () => pageHead("Learn", { context: info("<p>Organised by topic. Each has <b>guides</b> to read start to finish; the chart topics also have their <b>patterns</b> to look up, every one drawn with real candles, with how to read it. The macro, market-health, sector and fundamentals guides chart stored data.</p><p>Findings and studies (backtests, research logs, specifications) are under Library → Research.</p>") })
    + `<p class="sd-lead">Read a topic's guides, then look its patterns up. Findings and studies are under <a href="#/research">Research</a>.</p>
    ${LEARN_TOPICS.map((t) => `<h3 class="ov-h">${esc(Learn.FAMILY_LABEL[t])}</h3><div class="lp-hub">${guidesIn(t).map(guideCard).join("")}${hasGrid(t) ? patternsCard(t) : patternCards(t)}</div>`).join("")}
    ${more.length ? `<h3 class="ov-h">More guides</h3><div class="lp-hub">${more.map(guideCard).join("")}</div>` : ""}
    ${runs.length ? "" : '<div class="muted small">No guides loaded — System → Reports archive → Load reports.</div>'}`;
  const patternsHead = (f) => pageHead(`${Learn.FAMILY_LABEL[f]}: all patterns`, { context: info("<p>Every pattern drawn with real candles. Candlestick patterns show the context they form in (faded) and the bar that confirms them; chart patterns show the pivot that triggers them and the level that invalidates them, with volume.</p><p>For the reasoning behind them, read this topic's guides — at the top of its menu.</p>") })
    + `<div class="muted small lp-gridnone" hidden></div>`;
  $view.innerHTML = `<div class="rep-layout"><aside class="rep-nav strat-nav lp-nav">${menu}</aside>
    <section class="scr-main lp-main">${topic === "glossary" ? glossaryView() : guide ? `<div class="lp-guide"><div id="lpg-body">${LOADING}</div><nav class="lp-toc" hidden></nav></div>`
      : p ? Learn.detail(p, { topicHref: hasGrid(fam) ? null : topicHome(fam) }) : catView ? patternsHead(catView) + Learn.overview(catView) : hub()}</section></div>`;

  // ---- search: every sub-menu at once (each opens while you search, and closes again when you clear it),
  // the pattern grid with it, and an explicit "nothing matches"
  const f = $view.querySelector("#lpf");
  const secs = [...$view.querySelectorAll(".lp-sec")];
  const wasOpen = new Map(secs.map((d) => [d, d.open]));
  const filter = () => {
    const q = f.value.trim().toLowerCase(), searching = !!q;
    const counts = {};
    for (const d of secs) {
      let n = 0;
      d.querySelectorAll(".nav-item[data-k]").forEach((a) => { const hit = !q || a.dataset.k.includes(q); a.hidden = !hit; if (hit) n++; });
      d.querySelectorAll(".lp-allp").forEach((a) => { a.hidden = searching; });
      d.querySelectorAll(".nav-h").forEach((h) => { let e = h.nextElementSibling, any = false; while (e && !e.classList.contains("nav-h")) { if (e.dataset.k && !e.hidden) any = true; e = e.nextElementSibling; } h.hidden = searching && !any; });
      counts[d.dataset.sec] = n;
      d.hidden = searching && n === 0;
      d.open = searching ? n > 0 : wasOpen.get(d);
    }
    const none = $view.querySelector(".lp-none"), total = Object.values(counts).reduce((x, y) => x + y, 0);
    none.hidden = !searching || total > 0;
    none.textContent = `Nothing matches “${f.value.trim()}”. Try a name like hammer, doji, cup, flag or VCP.`;
    if (catView) {
      const grid = $view.querySelector(".lp-main");
      let shown = 0;
      grid.querySelectorAll(".lp-card[data-k]").forEach((c) => { const hit = !q || c.dataset.k.includes(q); c.hidden = !hit; if (hit) shown++; });
      grid.querySelectorAll(".lp-gh").forEach((h) => { const g = h.nextElementSibling; h.hidden = g.hidden = searching && ![...g.querySelectorAll(".lp-card")].some((c) => !c.hidden); });
      const msg = grid.querySelector(".lp-gridnone"), others = LEARN_TOPICS.filter((t) => t !== catView && counts[t]);
      msg.hidden = !searching || shown > 0;
      msg.innerHTML = others.length ? `Nothing in ${esc(Learn.FAMILY_LABEL[catView].toLowerCase())} matches “${esc(f.value.trim())}” — ${others.map((t) => `${counts[t]} in <a href="${topicHome(t)}">${esc(Learn.FAMILY_LABEL[t].toLowerCase())}</a>`).join(", ")} match (shown in the menu).`
        : `Nothing matches “${esc(f.value.trim())}”.`;
    }
  };
  // remember the open/closed state you choose (until you search)
  secs.forEach((d) => d.addEventListener("toggle", () => { if (!f.value.trim()) wasOpen.set(d, d.open); }));
  f.oninput = filter;
  f.onkeydown = (e) => { if (e.key === "Enter") { const a = [...$view.querySelectorAll(".lp-sec .nav-item[data-k]")].find((x) => !x.hidden); if (a) go(a.getAttribute("href")); } };
  $view.querySelector(".lp-nav .nav-item.active")?.scrollIntoView({ block: "nearest" });
  if (p) window.scrollTo(0, 0);
  if (catView && sub) document.getElementById(`g-${sub}`)?.scrollIntoView({ block: "start" });
  if (guide) await learnGuide(alive, guide);
}

/** In a guide, link the first mention of each drawn pattern to its page, so guides and patterns
 *  connect. Names match whole words, longest first ("Gravestone doji" before "Doji"); headings, code,
 *  figures and existing links are left alone. */
function linkPatternMentions(root) {
  const reEsc = (x) => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pats = Learn.PATTERNS.filter((x) => x.group !== "basics")
    .map((x) => ({ key: x.key, name: x.name, word: x.name.split(/ \(| \/ | — /)[0] }))
    .sort((a, b) => b.word.length - a.word.length);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (n.parentElement.closest("a, code, pre, h1, h2, h3, h4, figure, th") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) });
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  const done = new Set();
  for (let node of nodes) {
    for (const pt of pats) {
      if (done.has(pt.key) || !node.nodeValue) continue;
      const m = node.nodeValue.match(new RegExp(`\\b${reEsc(pt.word)}s?\\b`, "i"));
      if (!m) continue;
      const hit = node.splitText(m.index), rest = hit.splitText(m[0].length);
      const a = document.createElement("a");
      a.href = `#/learn/${pt.key}`; a.className = "lp-mention"; a.title = `${pt.name} — open the pattern`; a.textContent = hit.nodeValue;
      hit.replaceWith(a); done.add(pt.key); node = rest;
    }
  }
}

/** Library → Research: every research note (research/*.md, except the learn-* guides) in a sidebar, the
 *  chosen one beside its "On this page" contents. Opens on the sector playbook. */
async function researchPage(alive, slug) {
  $view.innerHTML = LOADING;
  const runs = (await api("/api/reports?kind=research").catch(() => [])).filter((x) => !x.run.startsWith("learn-"))
    .sort((a, b) => String(a.title || a.run).localeCompare(String(b.title || b.run)));
  if (!alive()) return;
  if (!runs.length) { $view.innerHTML = `<div class="empty"><b>No research notes loaded</b><div class="muted">Load them from System → Reports archive (Load reports).</div></div>`; return; }
  const doc = runs.find((x) => x.run === slug) || runs.find((x) => x.run === "sector-analysis-playbook") || runs[0];
  const title = (x) => (x.title || x.run).replace(/ — a field guide$/, "");
  // the menu shows the short name (before the "—"), unless two notes would then read the same
  const head = (x) => title(x).split(" — ")[0];
  const short = (x) => (runs.filter((y) => head(y) === head(x)).length > 1 ? title(x) : head(x));
  document.title = `${title(doc)} · Research · Trading`;
  $view.innerHTML = `<div class="rep-layout"><aside class="rep-nav strat-nav lp-nav">
      <div class="nav-h">Research notes (${runs.length})</div>
      ${runs.map((x) => `<a class="nav-item ${x.id === doc.id ? "active" : ""}" href="#/research/${esc(x.run)}" title="${esc(title(x))}"><span><b class="sn">${esc(short(x))}</b></span></a>`).join("")}
      <div class="nav-empty muted small">Learning guides are under <a href="#/learn">Learn</a>; backtest and screening reports under System → <a href="#/reports">Reports archive</a>.</div>
    </aside><section class="scr-main lp-main"><div class="lp-guide"><div id="lpg-body">${LOADING}</div><nav class="lp-toc" hidden></nav></div></section></div>`;
  $view.querySelector(".lp-nav .nav-item.active")?.scrollIntoView({ block: "nearest" });
  await learnGuide(alive, doc);
}

/** One long-form guide inside the Learn layout, with an "On this page" list of its sections. */
async function learnGuide(alive, guide) {
  const r = await api(`/api/reports/${guide.id}`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  const body = $view.querySelector("#lpg-body"), toc = $view.querySelector(".lp-toc");
  if (r.error) { body.innerHTML = `<div class="empty"><b>Guide not found</b><div class="muted">Reload the documents from the Reports archive (Load reports).</div></div>`; return; }
  const art = renderResearchMd(body, r.markdown);
  if (String(guide.run).startsWith("learn-")) linkPatternMentions(art);
  // anchors for every section, so the contents can jump to them (and a section can be linked)
  const slug = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const heads = [...art.querySelectorAll("h2, h3")];
  heads.forEach((h) => { h.id = "s-" + slug(h.textContent); });
  if (heads.length > 2) {
    toc.hidden = false;
    toc.innerHTML = `<div class="nav-h">On this page</div>` + heads.map((h) =>
      `<a href="#" data-s="${h.id}" class="${h.tagName === "H3" ? "sub" : ""}">${esc(h.textContent)}</a>`).join("");
    toc.onclick = (e) => {
      const a = e.target.closest("a[data-s]"); if (!a) return;
      e.preventDefault();
      document.getElementById(a.dataset.s)?.scrollIntoView({ behavior: "smooth", block: "start" });
    };
    // highlight the section being read
    const links = new Map([...toc.querySelectorAll("a[data-s]")].map((a) => [a.dataset.s, a]));
    const obs = new IntersectionObserver((es) => {
      const vis = es.filter((x) => x.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (vis) { links.forEach((a) => a.classList.remove("on")); links.get(vis.target.id)?.classList.add("on"); }
    }, { rootMargin: "-60px 0px -70% 0px" });
    heads.forEach((h) => obs.observe(h));
  }
  window.scrollTo(0, 0);
}


// ------------------------------------------------------------ Today: the daily starting point

/** Today's cards share one shape: a header (title left; date, counts and links right), a verdict line, ✓/✗
 *  signals with the number behind each, then "against history" notes and links at the foot. */
const tdHead = (title, right = "") => `<div class="td-hh"><h3>${title}</h3><span class="spacer"></span>${right}</div>`;
const tdVerdict = (cls, label, sub, note = "") => `<div class="td-tone"><span class="td-tl tl ${cls || ""}"></span><b>${esc(label)}</b><span class="muted small">${esc(sub)}</span></div>${note ? `<div class="muted small td-note">${esc(note)}</div>` : ""}`;
const tdSignal = (ok, text, detail = "", why = "") => `<li class="${ok ? "pos" : "neg"}"${why ? ` title="${esc(why)}"` : ""}><span>${ok ? "✓" : "✗"} ${esc(text)}</span>${detail ? `<span class="muted">${esc(detail)}</span>` : ""}</li>`;

/** Today: one page to start the day on, for the market chosen in the toggle — its verdict, whether its data
 *  can be trusted, the macro read, today's tradeable setups and the new screener picks — each linking to its
 *  full page. Everything here is read from the pages' own endpoints, so it says exactly what they say. */
async function todayPage(alive, mkt) {
  mkt = pageMarket(mkt);
  document.title = "Today · Trading";
  $view.innerHTML = LOADING;
  const get = (u) => api(u).catch(() => null);
  const [status, setups, picks, pm, bd] = await Promise.all([get("/api/status"), get(`/api/setups?market=${mkt}`),
    get("/api/watchlists/screener/items"), get(`/api/postmarket?market=${mkt}`), get(`/api/breadth?market=${mkt}`)]);
  if (!alive()) return;
  const post = { [mkt]: pm }, breadth = { [mkt]: bd };
  if (status) { FRESH = status.freshness; }

  // ---- 1. the market: post-market tone, its six signals, and breadth's base rates
  const marketCard = (m) => {
    const p = post[m.key]?.payload, h = post[m.key]?.history?.[0], b = breadth[m.key];
    if (!p) return `<div class="sec-card td-card">${tdHead(`Market · ${esc(m.name)}`)}<div class="muted small">No post-market analysis yet — it runs with the market close routine.</div></div>`;
    const t = p.tone || {};
    const base = toneBaseRate(post[m.key]?.history, p.date, t.score);
    const sig = (t.signals || []).map((x) => tdSignal(x.ok, x.ok ? x.text : x.text_not || x.text)).join("");
    const rates = (b?.cards || []).filter((c) => c.text).slice(0, 2).map((c) => `<li><b>${esc(c.title)}</b> ${esc(c.value ?? "")} <span class="muted">— ${esc(c.text)}</span></li>`).join("");
    return `<div class="sec-card td-card">
      ${tdHead(`Market · ${esc(m.name)}`, `<span class="muted small">${prettyDate(p.date)}</span>`)}
      ${tdVerdict(TONE_CLS[t.label], t.label || "—", `${t.score ?? "?"} of ${t.of ?? 6} signals${h ? ` · ${h.up?.toLocaleString()} up / ${h.down?.toLocaleString()} down` : ""}`, base ? `${base}.` : "")}
      <ul class="td-sig">${sig}</ul>
      ${rates ? `<div class="td-sub">Breadth, against history since 2009</div><ul class="td-rates">${rates}</ul>` : ""}
      <div class="td-foot"><a class="small" href="#/postmarket/${m.key}">Post-market recap →</a><a class="small" href="#/breadth/${m.key}">Breadth →</a></div></div>`;
  };

  // ---- 2. data health: can today's numbers be trusted? A one-line banner; a list only when something is wrong
  // jobs and runs for this market (or for every market) — another market's work is not this page's business
  const ours = (x) => !x.market || x.market === "all" || x.market === mkt;
  const issues = [];
  if (status) {
    for (const it of (status.freshness?.[mkt]?.items || [])) if (it.status && it.status !== "ok" && ["prices", "breadth", "screening"].includes(it.key))
      issues.push(`${esc(it.label)}: ${esc(it.text || it.status)}`);
    const lanes = status.lanes || {};
    if (!status.worker?.alive) issues.push(`The job worker is stopped — nothing queued or scheduled will run. <a href="#/status">Start it</a>`);
    else if (lanes.fast && !lanes.fast.alive) issues.push("The fast lane is stopped — screen and setup refreshes will wait behind longer jobs.");
    const dayAgo = Date.now() - 864e5;
    const failed = (status.runs || []).filter((x) => x.status === "failed" && new Date(x.started_at).getTime() > dayAgo && ours(x));
    if (failed.length) issues.push(`${failed.length} run${failed.length > 1 ? "s" : ""} failed in the last 24 h: ${failed.slice(0, 3).map((x) => `<a href="#/runs/${x.id}">${esc(x.job)}</a>`).join(", ")}`);
  } else issues.push("Could not reach the status check.");
  const running = (status?.queue?.running_all || (status?.queue?.running ? [status.queue.running] : [])).filter(ours);
  const waiting = (status?.queue?.queued || []).filter(ours).length;
  const queueLine = running.length || waiting ? `${running.length ? `Running: ${running.map((x) => esc(`${(x.targets || []).join(" + ")}${x.market && x.market !== "all" ? ` · ${mktInfo(x.market).name}` : ""}${x.lane && x.lane !== "main" ? ` (${x.lane} lane)` : ""}`)).join(", ")}` : ""}${waiting ? `${running.length ? " · " : ""}${waiting} waiting in the queue` : ""}` : "";
  const health = `<div class="td-health ${issues.length ? "warn" : "ok"}">
      <div class="td-hl"><b>${issues.length ? "Data health — check before trading" : "Data current"}</b>
        <span class="muted small">${issues.length ? "" : "prices, breadth and the screens are up to date"}${queueLine ? `${issues.length ? "" : " · "}${queueLine}` : ""}</span>
        <span class="spacer"></span><a class="small" href="#/status">System status →</a></div>
      ${issues.length ? `<ul class="td-issues">${issues.map((x) => `<li>${x}</li>`).join("")}</ul>` : ""}</div>`;

  // ---- 3. today's setups for the chosen market: what can be traded now
  const rows = setups?.rows || [];
  const trade = rows.filter((x) => x.tradeable).sort((a, b) => (/HIGH/.test(b.decision) - /HIGH/.test(a.decision)) || ((b.quality ?? 0) - (a.quality ?? 0)));
  const watchN = rows.length - trade.length;
  const runChips = (setups?.runs || []).map((x) => `<a class="chip-s" href="#/strategies/${x.strategy}/setups/${mkt}" title="${esc(x.name)}: ${x.tradeable} tradeable, ${x.watch} on watch — run ${prettyDate(x.run)}">${esc(x.name)} <b>${x.tradeable}</b></a>`).join("");

  // ---- 4. screener picks: what is new on the list since the last session
  const mine = (picks || []).filter((x) => x.market === mkt);
  const newest = mine.length ? mine.map((x) => x.added_at).sort().at(-1) : null;
  const fresh = newest ? mine.filter((x) => new Date(newest) - new Date(x.added_at) < 20 * 3600e3) : [];
  const pickChip = (x) => `<a class="chip-s" href="#/chart/${x.market}/${encodeURIComponent(x.symbol)}" title="${esc(x.name || "")} — ${esc((x.strategies || []).map((s) => `${s.strategy}: ${s.decision}`).join(" · "))}">${esc(bareSymbol(x.symbol))}</a>`;

  $view.innerHTML = pageHead("Today", { extra: marketSeg(mkt),
      context: `<span class="muted small">${new Date().toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" })}</span>${info("<p>Your starting point each day: how each market closed, whether the data behind everything is current, the macro backdrop, what can be traded today, and what is new on the screener list. Each part opens its full page.</p><p>The market toggle chooses the market for the whole page.</p>")}` })
    + `${health}<div class="td-grid">${marketCard(mktInfo(mkt))}
      <div class="sec-card td-card" id="td-macro">${tdHead(`Macro · ${esc(mktInfo(mkt).name)}`)}<div class="muted small">Loading…</div></div></div>
    <div class="mstrip td-tiles" id="td-tiles"></div>
    <div class="sec-card td-rates-card" id="td-rates">${tdHead(`Rates & yields · ${esc(mktInfo(mkt).name)}`)}<div class="muted small">Loading…</div></div>
    <div class="sec-card td-setups">${tdHead(`Today's setups · ${esc(mktInfo(mkt).name)}`, `<span class="muted small">${trade.length} tradeable · ${watchN} on watch</span><a class="small" href="#/strategies">All setups →</a>`)}
      ${setups?.behind ? `<div class="muted small td-warn">Newer prices have loaded since these runs — the decisions below were made on older bars.</div>` : ""}
      <div class="scr-top td-runs">${runChips || '<span class="muted small">No strategy runs yet for this market.</span>'}</div>
      <div id="td-tbl"></div></div>
    <div class="sec-card td-picks">${tdHead(`Screener picks · ${esc(mktInfo(mkt).name)}`, `<span class="muted small">${mine.length} on the list${fresh.length ? ` · ${fresh.length} added in the latest run` : ""}</span><a class="small" href="#/watchlist/screener">Open the list →</a>`)}
      ${fresh.length ? `<div class="muted small">New:</div><div class="scr-top">${fresh.slice(0, 40).map(pickChip).join("")}</div>`
        : `<div class="muted small">${mine.length ? "Nothing new in the latest run." : "Stocks a strategy marks tradeable or on watch collect here after each run."}</div>`}</div>`;
  $view.querySelectorAll(".mk button").forEach((b) => b.onclick = () => { pageMarket(b.dataset.v); go(`#/today/${b.dataset.v}`); });
  macroSection($view.querySelector("#td-macro"), $view.querySelector("#td-tiles"), mkt);   // its own request: the page never waits on it
  ratesSection($view.querySelector("#td-rates"), mkt);
  const host = $view.querySelector("#td-tbl");
  if (!trade.length) { host.innerHTML = `<div class="muted small">${rows.length ? "No tradeable setups today — the names above are on watch." : ""}</div>`; return; }
  const cols = ["symbol", "name", "peer_group", "group_rs", "strategy", "decision", "setup", "price", "entry", "stop", "risk_pct", "target_r"];
  dataTable(host, cols, trade.map((x) => [x.symbol, x.name || "", x.peer_group || "", x.peer_rs ?? null, x.strategy_name, x.decision, x.setup, x.price, x.entry, x.stop, x.risk_pct, x.target_r]), {
    name: "today_setups", limit: 15,
    rowClick: (row, visible) => openChartFromList(mkt, row[0], visible.map((x) => x[0]), "Today's setups", location.hash),
  });
}

async function route() {
  cleanup(); cleanup = () => {};
  // a new page opens at the top; re-rendering the same page (indicator change, refresh) keeps the scroll
  if (location.hash !== lastRoute) { window.scrollTo(0, 0); lastRoute = location.hash; }
  const seq = ++navSeq, alive = () => seq === navSeq;
  const parts = location.hash.replace(/^#\//, "").split("/").map(decodeURIComponent);
  const page = parts[0] || "today";
  renderNav(pageIdOf(parts));
  document.body.dataset.page = page;
  try {
    if (page === "today") await todayPage(alive, parts[1]);
    else if (page === "chart") await chartPage(alive, parts[1], parts[2], parts[3]);
    else if (page === "screening") go(`#/strategies/${encodeURIComponent(parts[2] || "trend_pullback")}/setups/${parts[1] || ""}`);
    else if (page === "screens") await screensPage(alive, parts[1], parts[2], parts[3], parts[4]);
    else if (page === "watchlist") await watchlistPage(alive, parts[1]);
    else if (page === "strategies") await strategiesPage(alive, parts[1], parts[2], parts[3], parts[4]);
    else if (page === "quality") await qualityPage(alive, parts[1]);
    else if (page === "company") await companyPage(alive, parts[1], parts[2]);
    else if (page === "news") await stockNewsPage(alive, parts[1], parts[2]);
    else if (page === "fundamentals" || page === "sepa") go(`#/company/${parts[1] || ""}`);   // the page's earlier names
    else if (page === "breadth") await breadthPage(alive, parts[1]);
    else if (page === "movers") await moversPage(alive, parts[1]);
    else if (page === "postmarket") await postmarketPage(alive, parts[1], parts[2], parts[3]);
    else if (page === "sectors") await sectorsPage(alive, parts[1], parts[2], parts[3]);
    else if (page === "reports") await (parts[1] ? reportPage(alive, parts[1], parts[2]) : reportsPage(alive));
    else if (page === "playbook") go("#/research/sector-analysis-playbook");   // its own tab, before Research listed every note
    else if (page === "research") await researchPage(alive, parts[1]);
    else if (page === "learn") await learnPage(alive, parts[1], parts[2]);
    else if (page === "status") await statusPage(alive, parts[1]);
    else if (page === "schedules") await schedulesPage(alive);
    else if (page === "runs") await runsPage(alive, parts[1]);
    else if (page === "subindustries") await subindustriesPage(alive, parts[1], parts[2]);
    else if (page === "todo") await todoPage(alive);
    else if (page === "notes") await notesPage(alive, parts.slice(1));
    else go("#/today");
    if (alive()) rememberVisit();
  } catch (e) {
    if (alive()) $view.innerHTML = `<div class="empty"><b>Something went wrong</b><div class="muted">${esc(e.message)}</div></div>`;
  }
}
/** the pages you opened recently, newest first — ⌘K lists them before you type */
function rememberVisit() {
  const label = document.title.replace(/ · Trading$/, "").trim();
  if (!label || label === "Trading") return;
  const hash = location.hash || "#/today";
  const xs = (store.get("recentVisits", []) || []).filter((x) => x.hash !== hash && x.label !== label);
  store.set("recentVisits", [{ hash, label }, ...xs].slice(0, 8));
}
window.addEventListener("hashchange", route);

/** Load report files the offline scripts wrote (backtests, screening reports, research notes) into the app. */
async function loadReports() {
  toast("Loading reports…");
  try {
    const before = (await api("/api/reports")).length;
    const r = await api("/api/ingest", { method: "POST" });
    const d = r.runs - before;
    toast(d > 0 ? `${d} new report${d > 1 ? "s" : ""} loaded` : d < 0 ? `${-d} removed — ${r.runs} reports` : `Up to date — ${r.runs} reports`, "ok");
    route();
  } catch (err) { toast("Loading reports failed: " + err.message, "err"); }
}

// ------------------------------------------------------------- tooltips
/** Icon-only buttons (chart tools, the right rail, ⋯, ×) get a tooltip after 250 ms — the browser's own
 *  takes a second or more and is easy to miss. The title moves to data-tip while shown (no double tooltip). */
{
  const tip = el(`<div class="tip" hidden></div>`); document.body.append(tip);
  let timer, cur = null;
  const iconOnly = (b) => b.matches(".icon, .ibtn, .tools button, .rbar button, .sbtns button, .dtb button, .tmore, .star") || !b.textContent.trim() || b.textContent.trim().length <= 2;
  const hide = () => { clearTimeout(timer); tip.hidden = true; if (cur && cur.dataset.tip != null) { cur.title = cur.dataset.tip; delete cur.dataset.tip; } cur = null; };
  document.addEventListener("mouseover", (e) => {
    const b = e.target.closest?.("button[title], a.ibtn[title], button[data-tip]");
    if (b === cur) return;
    hide();
    if (!b || !iconOnly(b)) return;
    cur = b;
    timer = setTimeout(() => {
      if (!cur || !cur.isConnected) return;
      cur.dataset.tip = cur.title; cur.removeAttribute("title");
      tip.textContent = cur.dataset.tip; tip.hidden = false;
      const r = cur.getBoundingClientRect(), t = tip.getBoundingClientRect();
      const side = r.left < 80 ? "right" : r.right > innerWidth - 80 ? "left" : "below";
      const x = side === "right" ? r.right + 8 : side === "left" ? r.left - t.width - 8 : Math.min(innerWidth - t.width - 6, Math.max(6, r.left + r.width / 2 - t.width / 2));
      const y = side === "below" ? r.bottom + 6 : r.top + r.height / 2 - t.height / 2;
      tip.style.left = `${x}px`; tip.style.top = `${y}px`;
    }, 250);
  });
  document.addEventListener("mousedown", hide, true);
  addEventListener("scroll", hide, true);
}

// ------------------------------------------------------------- theme
const THEMES = [["black", "Black", "#000"], ["graphite", "Graphite", "#1e1e21"], ["light", "Light", "#fff"], ["system", "Match system (Black / Light)", "linear-gradient(90deg,#000 50%,#fff 50%)"]];
function applyTheme(t) {
  store.set("theme", t);
  const eff = t === "system" ? (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "black") : t;
  if (document.documentElement.dataset.theme !== eff) { document.documentElement.dataset.theme = eff; route(); }   // re-render so charts pick up the colours
}
matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => { if (store.get("theme", "black") === "system") applyTheme("system"); });
{
  const btn = document.getElementById("thmbtn"), pop = document.getElementById("thmpop");
  const draw = () => { const cur = store.get("theme", "black"), dens = store.get("density", "comfortable");
    pop.innerHTML = `<div class="tfly-h">Theme</div>` + THEMES.map(([k, t, sw]) => `<button data-t="${k}" class="${k === cur ? "cur" : ""}"><span class="thm-sw" style="background:${sw}"></span>${t}${k === cur ? " ✓" : ""}</button>`).join("")
      + `<div class="tfly-h">Density</div>` + [["comfortable", "Comfortable — for reading"], ["compact", "Compact — more rows on screen"]]
        .map(([k, t]) => `<button data-d="${k}" class="${k === dens ? "cur" : ""}">${t}${k === dens ? " ✓" : ""}</button>`).join("")
      + `<div class="cm-sep"></div><button data-act="help">Keyboard shortcuts<kbd>?</kbd></button>
         <button data-act="load" title="Load report files written by the offline scripts (backtests, screening reports, research notes). Market data comes from the daily jobs.">Load reports from disk</button>`; };
  btn.onclick = (e) => { e.stopPropagation(); draw(); pop.hidden = !pop.hidden; };
  pop.onclick = (e) => {
    const b = e.target.closest("[data-t]"); if (b) { applyTheme(b.dataset.t); pop.hidden = true; return; }
    const d = e.target.closest("[data-d]"); if (d) { store.set("density", d.dataset.d); document.documentElement.dataset.density = d.dataset.d; pop.hidden = true; route(); return; }
    const a = e.target.closest("[data-act]"); if (!a) return;
    pop.hidden = true;
    if (a.dataset.act === "help") HELP.hidden = false; else loadReports();
  };
  document.addEventListener("click", (e) => { if (!pop.hidden && !e.target.closest(".thm")) pop.hidden = true; });
}

// keyboard help
const HELP = el(`<div class="help" hidden><div class="help-card"><h3>Keyboard shortcuts</h3>
  <h4>Anywhere</h4>
  <dl><dt>⌘ / Ctrl + K</dt><dd>Go anywhere: a page, or a stock by symbol or company name</dd>
  <dt>Alt + 1 … ${SECTIONS.length}</dt><dd>${SECTIONS.map((x) => x.label).join(" / ")}</dd>
  <dt>Alt + 0</dt><dd>Data status</dd>
  <dt>Alt + [ / ]</dt><dd>Previous / next tab in the section</dd>
  <dt>?</dt><dd>Show this help</dd></dl>
  <h4>On the chart</h4>
  <dl><dt>Type a letter</dt><dd>Search symbols</dd>
  <dt>↑ / ↓</dt><dd>Previous / next symbol in the list you opened it from</dd>
  <dt>Alt + T / H / J</dt><dd>Trend line / horizontal line / horizontal ray</dd>
  <dt>Alt + V / C / F</dt><dd>Vertical line / cross line / Fib retracement</dd>
  <dt>Alt + R</dt><dd>Reset the chart view</dd>
  <dt>Esc</dt><dd>Cancel drawing / deselect</dd>
  <dt>Del</dt><dd>Delete the selected drawing</dd>
  <dt>⌘ / Ctrl + Z</dt><dd>Undo the last drawing change</dd></dl>
  <h4>Mouse, on the chart</h4>
  <dl class="mouse"><dt>Drag the chart</dt><dd>Pan left/right and up/down (up/down turns auto-scale off; click “auto” to restore)</dd>
  <dt>Drag the price axis</dt><dd>Stretch / squeeze the price scale</dd>
  <dt>Shift + drag</dt><dd>Measure</dd></dl>
  <button class="ghost">Close</button></div></div>`);
document.body.append(HELP);
HELP.onclick = (e) => { if (e.target === HELP || e.target.tagName === "BUTTON") HELP.hidden = true; };
document.addEventListener("keydown", (e) => {
  if ((e.key === "?" || (e.key === "/" && e.shiftKey)) && !e.target.closest?.("input, select, textarea")) { HELP.hidden = !HELP.hidden; e.preventDefault(); e.stopImmediatePropagation(); }
  else if (e.key === "Escape") HELP.hidden = true;
}, true);
route();
document.getElementById("palbtn").onclick = () => openPalette();
