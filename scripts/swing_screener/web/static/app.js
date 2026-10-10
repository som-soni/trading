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
      <input placeholder="Filter rows" spellcheck="false"></label><span class="muted count"></span><span class="spacer"></span>
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
  // fade the edge that has more columns behind it
  const edges = () => {
    fade.classList.toggle("more-r", wrap.scrollLeft + wrap.clientWidth < wrap.scrollWidth - 2);
    fade.classList.toggle("more-l", wrap.scrollLeft > 2);
  };
  wrap.addEventListener("scroll", edges, { passive: true });
  new ResizeObserver(() => { pin2(); edges(); }).observe(wrap);
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
  const peerFmt = (v) => (v ? String(v).split(" › ").at(-1) : "");
  const fmtFor = columns.map((c) => (opts.format && opts.format[c]) || (c === "symbol" ? bareSym : isPeer(c) ? peerFmt : fmt));
  const autoTags = Object.fromEntries(columns.filter(isGrpRs).map((c) => [c, (v) => (v >= 80 ? "pos" : v >= 50 ? "warn" : "neg")]));
  opts = { ...opts, tags: { ...autoTags, ...(opts.tags || {}) } };
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
        if (stack && i === cols[0]) return `<td class="symcell"><div title="${esc(row[1] || "")}"><b>${esc(fmtFor[i](v, row))}</b>${row[1] ? `<span>${esc(row[1])}</span>` : ""}</div></td>`;
        if (opts.tags && opts.tags[columns[i]] && v) return `<td><span class="tag ${opts.tags[columns[i]](v)}">${esc(v)}</span></td>`;
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
function openChartFromList(market, symbol, symbols, labelText, back) {
  const seen = new Set(), items = [];
  for (const x of symbols) {
    const it = typeof x === "string" ? { m: market, s: x } : { m: x.market, s: x.symbol };
    const k = it.m + ":" + it.s;
    if (!seen.has(k)) { seen.add(k); items.push(it); }
  }
  store.set("chartList", { items, label: labelText, back, fresh: true });   // fresh: open the list panel on arrival
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

/** The market is one setting for the whole app: a page opened without one in its URL shows the market you
 *  last chose anywhere, and choosing one on any page sets it everywhere. `extra` are page-specific
 *  combined views ("both", "all") — kept in the URL only, never remembered as the market. */
function pageMarket(m, extra = []) {
  if (isMarket(m)) { if (store.get("market", null) !== m) store.set("market", m); syncMarketSel(); return m; }
  const g = store.get("market", MKTS[0].key);
  return extra.includes(m) ? m : isMarket(g) ? g : MKTS[0].key;
}
/** The market is chosen once, in the header. A page with a combined view (Movers, Quality) adds a toggle
 *  between the header's market and "All markets"; other pages show nothing here. */
function marketSeg(m, extra = []) {
  if (!extra.length) return "";
  const g = pageMarket();
  return segmented([[g, mktInfo(g).name], ...extra.map(([k]) => [k, "All markets"])], m, "mk");
}
// pages where the header market does not apply (they list every market, or a single record)
const MARKETLESS = new Set(["watchlist", "notes", "todo", "playbook", "learn", "reports", "status", "runs"]);   // subindustries uses the market
function syncMarketSel(page) {
  const sel = document.getElementById("mktsel"); if (!sel) return;
  const m = store.get("market", MKTS[0].key);
  if (sel.options.length !== MKTS.length) sel.innerHTML = MKTS.map((x) => `<option value="${x.key}">${x.flag} ${esc(x.name)} · ${esc(x.exchange)}</option>`).join("");
  sel.value = isMarket(m) ? m : MKTS[0].key;
  page = page || pageIdOf(location.hash.replace(/^#\//, "").split("/").map(decodeURIComponent));
  const na = MARKETLESS.has(page);
  sel.parentElement.classList.toggle("na", na);
  sel.parentElement.title = na ? "This page covers every market" : "Market — applies to every page";
}
document.getElementById("mktsel").onchange = (e) => {
  const m = e.target.value; store.set("market", m); refreshStatusDot();
  const parts = location.hash.replace(/^#\//, "").split("/");
  if ((parts[0] || "chart") === "chart") return go(`#/chart/${m}/${encodeURIComponent(store.get("lastSymbol:" + m, m === "us" ? "AAPL" : "RELIANCE.NS"))}`);
  const h = location.hash.split("/").map((x) => (isMarket(x) || x === "both" || x === "all" ? m : x)).join("/");
  if (h !== location.hash) go(h); else route();
};
api("/api/markets").then((xs) => { if (xs?.length) { MKTS = xs; Object.assign(MKT_BADGE, Object.fromEntries(xs.map((m) => [m.key, m.badge]))); syncMarketSel(); } }).catch(() => {});
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
api("/api/strategies").then((xs) => Studies.setStrategies(xs.filter((x) => x.kind === "screener").map((x) => x.key))).catch(() => {});  // visible range to restore when the chart is rebuilt for an indicator change
const BENCH = { us: "SPY", india: "NIFTY50" };

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
  // trade-debug overlay state — declared before the first renderSide(), which can hit the
  // restored Trades tab before the chart (and its data) exists
  let dr = null, vcpAnnotations = [], anatomy = [], selTrade = -1;
  let applyAnnotations = () => { if (dr) dr.annotate(vcpAnnotations); };
  let zoomToTrade = () => {};
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
  // a backtest run is on: offer its trades as a side panel (click a trade -> its anatomy)
  if (sel.value) {
    $("#rbar").insertAdjacentHTML("beforeend", `<button data-tab="trades" title="Backtest trades — click one to zoom to it and see the structure the strategy traded on">
      <svg viewBox="0 0 20 20"><path d="M3 17V3M3 17h14"/><path d="M5 13l3.5-5 3 3L16 5"/></svg></button>`);
  } else if (prefs.tab === "trades") prefs.tab = "wl";
  syncPanel();

  // drag-panning of the plot is done by our own handler below (both axes, TradingView style), so the
  // library's horizontal-only drag is off; wheel zoom, touch and the axis drag-to-scale stay native
  chart = LC.createChart(chartEl, { autoSize: true, ...chartTheme(), crosshair: { mode: LC.CrosshairMode.Normal },
    handleScroll: { mouseWheel: true, pressedMouseMove: false, horzTouchDrag: true, vertTouchDrag: false } });
  const prevCleanup = cleanup;
  cleanup = () => { prevCleanup(); dr && dr.destroy(); chart.remove(); };
  let main, times;
  const rows = px.ohlc ? px.candles : px.line;
  if (px.ohlc) {
    main = chart.addSeries(LC.CandlestickSeries, { upColor: "#26a69a", downColor: "#ef5350", borderVisible: false, wickUpColor: "#26a69a", wickDownColor: "#ef5350" }, 0);
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
  const studies = Studies.render({ chart, times, bars: B, ctx: { bench: benchMap, main, tf, plans: px.ohlc ? ctx.latest : [] } });
  const nPanes = Math.max(0, ...studies.map((e) => e.pane || 0));

  // (the screener's entry / stop / target lines are now an opt-in indicator: Indicators -> Screener)

  // backtest trades from the chosen run
  if (sel.value && px.ohlc) {
    const t = await api(`/api/reports/${sel.value}/tables/trades?symbol=${encodeURIComponent(symbol)}`).catch(() => null);
    if (!alive()) return;
    // `snap` maps a date onto the nearest charted bar; the VCP annotation below needs it
    // too, so it is declared here rather than inside the trades block
    const snap = (d) => times.find((x) => x >= d);
    if (t) {
      const c = (n) => t.columns.indexOf(n);
      const marks = [];
      t.rows.forEach((r) => {
        const a = snap(r[c("entry_date")]), b = snap(r[c("exit_date")]), pnl = r[c("pnl")], rm = r[c("r_multiple")];
        if (a) marks.push({ time: a, position: "belowBar", shape: "arrowUp", color: "#2196f3", text: "Buy" });
        if (b) marks.push({ time: b, position: "aboveBar", shape: "arrowDown", color: pnl >= 0 ? "#26a69a" : "#ef5350", text: `${r[c("exit_reason")]} ${rm > 0 ? "+" : ""}${rm}R` });
      });
      marks.sort((x, y) => (x.time < y.time ? -1 : x.time > y.time ? 1 : 0));
      LC.createSeriesMarkers(main, marks);
    }

    // Auto-annotate the structure the strategy claimed to see, per executed trade: the base box,
    // the pivot, the contraction story, the trade's own stop/target — straight from the signal
    // record the run wrote (/api/reports/{id}/trade-anatomy), so the chart shows WHY each trade
    // fired, not just where. The old VCP layer stays for the near misses: bases the detector saw
    // that never became one of this run's trades (dashed, labelled with the rejecting rule).
    const stratKey = (tradeRuns.find((r) => String(r.id) === String(sel.value)) || {}).strategy;
    if (stratKey) {
      const [anat, boxes] = await Promise.all([
        api(`/api/reports/${sel.value}/trade-anatomy?symbol=${encodeURIComponent(symbol)}`).catch(() => []),
        api(`/api/vcp/${market}/${encodeURIComponent(symbol)}?strategy=${encodeURIComponent(stratKey)}`).catch(() => []),
      ]);
      if (!alive()) return;
      anatomy = anat || [];
      const ts = (d) => { const s = snap(d); return s ? Date.parse(s + "T00:00:00Z") : null; };
      const idxOf = (d) => { const s = snap(d); return s ? times.indexOf(s) : -1; };
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
      const ROLE = { base: "#2962ff", pivot: "#26a69a", stop: "#ef5350", target: "#26a69a", support: "#8a8a8a", level: "#ff9800" };
      const items = (t, i) => {
        const dim = selTrade >= 0 && selTrade !== i;
        const withNotes = selTrade === i || (selTrade < 0 && anatomy.length <= 3);
        return t.shapes.map((s) => {
          const col = dim ? "#4b5063" : ROLE[s.role] || ROLE.level;
          const t1 = ts(s.to || s.at || t.entry_date); if (t1 == null) return null;
          const i1 = idxOf(s.to || s.at || t.entry_date);
          const t0 = s.from ? ts(s.from) : s.bars && i1 >= 0 ? Date.parse(times[Math.max(0, i1 - s.bars)] + "T00:00:00Z") : t1;
          if (s.shape === "box") return { type: "rect", pts: [{ t: t0, p: s.top }, { t: t1, p: s.bottom }],
            color: col, width: dim ? 1 : 2, dash: !!s.dash, text: dim ? "" : s.label || "" };
          if (s.shape === "level") return { type: "trend", pts: [{ t: t0, p: s.price }, { t: t1, p: s.price }],
            color: col, width: 1, dash: s.dash !== false, text: dim ? "" : s.label || "" };
          if (s.shape === "note" && withNotes && s.text) {
            // the text box is pinned to the pane's top strip (pts[1].f = fraction of pane height),
            // so the note never covers the bars it explains; the leader still drops to the anchor
            const p = s.price ?? t.entry_price;
            const bx = Math.min(times.length - 1, (i1 < 0 ? times.length - 1 : i1) + 2);
            return { type: "callout", pts: [{ t: t1, p }, { t: Date.parse(times[bx] + "T00:00:00Z"), f: 0.05 }],
              color: col, width: 1, text: s.text };
          }
          return null;
        }).filter(Boolean);
      };
      applyAnnotations = () => { if (dr) dr.annotate([...vcpAnnotations, ...anatomy.flatMap(items)]); };
      zoomToTrade = (t) => {
        const ids = t.shapes.map((s) => (s.from ? idxOf(s.from) : s.bars ? idxOf(s.to || t.entry_date) - s.bars : -1)).filter((x) => x >= 0);
        const i0 = Math.min(...(ids.length ? ids : [idxOf(t.signal_date || t.entry_date)]).filter((x) => x >= 0), idxOf(t.entry_date));
        const i1 = Math.max(idxOf(t.exit_date || t.entry_date), i0);
        if (i0 >= 0) chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, i0 - 8), to: i1 + 14 });
      };
      if (prefs.tab === "trades") renderSide();   // the panel rendered before the trades arrived
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
    const hist = ctx.history.slice(0, 20).map((h) => `<div class="dhist"><span class="muted">${prettyDate(h.run_id)}</span><span>${esc(h.strategy)}</span>
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
      ${ctx.classification ? `<div class="wld-cls small">${[["sector", ctx.classification.sector], ["industry", ctx.classification.industry], ["sub", ctx.classification.sub_key]]
        .filter(([, v]) => v).map(([lv, v]) => `<a href="${secHref(market, lv, v)}" title="Open on the Sectors page">${esc(groupParts(v)[0])}</a>`).join('<span class="muted"> › </span>')}</div>` : ""}
      ${q ? `<div class="wld-px"><span class="big">${fmt(q.last)}</span><span class="${q.chg >= 0 ? "pos" : "neg"}">${q.chg >= 0 ? "+" : ""}${fmt(q.chg)} (${signed(q.pct)}%)</span></div>
        <div class="muted small">Close · ${prettyDate(q.date)}</div>
        <div class="wld-52"><span class="muted small">52-week range</span><div class="bar52 wide"><i style="left:${pos52.toFixed(1)}%"></i></div>
          <div class="wld-52v small"><span>${fmt(q.lo)}</span><span>${fmt(q.hi)}</span></div></div>` : ""}
      <div class="wld-notes" id="wlnotes"></div>
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
  function tradesPanelHtml() {
    // looked up from the DOM, not the `sel` binding: the panel can render (restored tab) before
    // the select's const is initialized further down the page build
    const run = tradeRuns.find((r) => String(r.id) === String(($("#trades") || {}).value || ""));
    const rows = anatomy.map((t, i) => `<div class="btr ${i === selTrade ? "cur" : ""}" data-i="${i}">
        <div class="btr-h"><b>${prettyDate(t.entry_date)} → ${t.exit_date ? prettyDate(t.exit_date) : "open"}</b>
          <span class="${(t.r_multiple ?? 0) >= 0 ? "pos" : "neg"}">${t.r_multiple > 0 ? "+" : ""}${t.r_multiple ?? "?"}R</span></div>
        <div class="muted small">${esc([t.setup, t.exit_reason, t.holding_days != null ? `${t.holding_days}d` : ""].filter(Boolean).join(" · "))}</div>
        ${t.note ? `<div class="btr-note small">${esc(t.note)}</div>` : ""}</div>`).join("");
    return `<section><h3>Backtest trades</h3><div class="muted small">${run ? esc(`${run.strategy} · ${run.run}`) : ""}</div>
      <div class="muted small">Click a trade to zoom to it and highlight what the strategy saw; click again to show every trade.</div></section>
      <div class="btrs">${rows || '<div class="muted small">This run has no trades in this symbol.</div>'}</div>`;
  }
  function renderSide() {
    if (!sideReady || !prefs.tab) return;
    const body = $("#side .side-body");
    body.innerHTML = prefs.tab === "wl" ? wlPanelHtml() : prefs.tab === "list" ? `<div class="wlpanel">${listPanelHtml()}</div>`
      : prefs.tab === "trades" ? `<div class="wlpanel">${tradesPanelHtml()}</div>` : infoHtml();
    body.querySelectorAll(".wlr.cur").forEach((c) => c.scrollIntoView({ block: "nearest" }));
    const $notes = body.querySelector("#wlnotes");
    if ($notes) {  // this stock's notes (fetched once per chart)
      symNotes = symNotes || api(`/api/notes?market=${market}&symbol=${encodeURIComponent(symbol)}`).then((r) => r.notes).catch(() => []);
      symNotes.then((ns) => { if (!$notes.isConnected) return;
        $notes.innerHTML = `<div class="wld-nh"><span class="muted small">Notes</span><span class="spacer"></span>
            ${ns.length ? `<a class="small" href="#/notes/sym/${market}/${encodeURIComponent(symbol)}">all ${ns.length}</a>` : ""}<a class="small" href="#/notes/new/${market}/${encodeURIComponent(symbol)}">+ note</a></div>
          ${ns.slice(0, 3).map((n) => `<a class="wld-note" href="#/notes/${n.id}"><b>${esc(n.title || "Untitled")}</b><span class="muted small">${ago(n.updated_at)}</span></a>`).join("")}`; });
    }
    if (prefs.tab === "trades") {
      body.querySelectorAll(".btr").forEach((el) => el.onclick = () => {
        const i = +el.dataset.i;
        selTrade = selTrade === i ? -1 : i;
        applyAnnotations();
        if (selTrade >= 0) zoomToTrade(anatomy[selTrade]);
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
/** traded value in the market's own units: $12.3M / $1.2B, ₹45 Cr */
function moneyShort(v, market) {
  if (v == null) return "";
  if (market === "india") { const cr = v / 1e7; return `₹${cr >= 100 ? Math.round(cr).toLocaleString() : cr.toFixed(1)} Cr`; }
  return v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : `$${(v / 1e6).toFixed(v >= 1e8 ? 0 : 1)}M`;
}

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
    return `<table class="mvt"><thead><tr><th>#</th><th>Symbol</th><th class="mv-g" title="Peer group (sub-industry, else industry group) and its RS rating">Group</th><th class="num">Last</th><th class="num">Chg%</th>
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

const PM_TABS = [["summary", "Summary"], ["sectors", "Sectors"], ["stocks", "Stocks"], ["yours", "Yours"]];
async function postmarketPage(alive, mkt, date, tab) {
  mkt = pageMarket(mkt);
  if (date === "latest") date = null;
  tab = PM_TABS.some(([k]) => k === tab) ? tab : store.get("pmTab", "summary");
  document.title = "Post-market · Trading";
  $view.innerHTML = LOADING;
  const r = await api(`/api/postmarket?market=${mkt}${date ? `&date=${date}` : ""}`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  const head = (context = "") => pageHead("Post-market", { context });
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
  $view.innerHTML = head(datePicker(pmDates, p.date) + pmInfo(p, r)) + `
    <div class="pm-tl" title="Market tone, last ${Math.min(60, H.length)} sessions (oldest left) — click a day">${timeline}</div>
    <nav class="ptabs pm-tabs">${PM_TABS.map(([k, t]) => `<a data-t="${k}" class="${k === tab ? "active" : ""}">${t}${
      k === "stocks" ? ` <span class="n">${p.movers.gainers.length + p.movers.losers.length}</span>` : k === "yours" ? ` <span class="n">${p.watchlists.length}</span>` : ""}</a>`).join("")}</nav>
    <div class="pmtab" data-t="summary">
    <div class="pm-hero sec-card">
      <div><div class="muted small">${esc(p.market_name)} · ${longDate(p.date)} <span class="muted">(vs ${prettyDate(p.prev_date)})</span></div>
        <div class="pm-tone ${TONE_CLS[p.tone.label]}">${p.tone.label}<span>${p.tone.score} of ${p.tone.of} signals bullish</span></div>
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
  $view.innerHTML = `<div class="page-head"><a class="muted" href="${secHref(mkt, level)}">← Sectors</a>
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
  $view.innerHTML = `<div class="crumbs scr-crumbs"><a href="#/screens">← All screens</a><span class="muted">·</span><a href="#/screens/new/${mkt === "all" ? pageMarket() : mkt}">+ New screen</a></div>
    <div class="page-head"><h1>Quality companies</h1>${marketSeg(mkt, [["all", "US + India"]])}
      <span class="spacer"></span>
      <form class="wl-add" autocomplete="off">
        ${mkt === "all" ? `<select id="qm" title="Market">${MKTS.map((m) => `<option value="${m.key}">${esc(m.name)}</option>`).join("")}</select>` : ""}
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
/** a strategy's status in a few words — the sentence up to its first colon or full stop ("No demonstrated edge") */
const shortStatus = (t) => { const x = String(t || "").split(/[:.;]/)[0].replace(/\s*—.*$/, "").trim(); return x.length > 42 ? x.slice(0, 40) + "…" : x; };
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
      <div class="nav-h">My screens</div>${mine.map(item).join("") || `<div class="nav-empty muted small">None yet</div>`}
    </aside><section id="scrmain" class="scr-main">${LOADING}</section></div>`;
  const main = $view.querySelector("#scrmain");
  if (list.error || !list.date) {
    main.innerHTML = `<div class="empty"><b>${list.error ? "Could not load screens" : "No snapshot yet"}</b><div class="muted">${esc(list.error || "Build today's stock snapshot (from scripts/, PYTHONPATH=.):")}</div>${list.command ? `<code>${esc(list.command)}</code>` : ""}</div>`;
    return;
  }
  if (!key) return screensOverview(main, list, mkt);
  if (key === "new" || tab === "edit") {
    let base = { name: "", description: "", conditions: [{ field: "tradable", op: "is", value: true }] };
    const from = store.get("scrDraftFrom", null);
    if (tab === "edit") base = (await api(`/api/screens/${key}?market=${mkt}`)).def;
    else if (from) { const d = (await api(`/api/screens/${from}?market=${mkt}`)).def; base = { name: `${d.name} (my copy)`, description: d.description, conditions: d.conditions }; store.set("scrDraftFrom", null); }
    if (!alive()) return;
    return screenBuilder(main, alive, mkt, fs, base, tab === "edit" ? key : null);
  }
  tab = ["results", "criteria", "study"].includes(tab) ? tab : "results";
  date = /^\d{4}-\d\d-\d\d$/.test(date || "") ? date : null;   // a past session is part of the URL: #/screens/<key>/<market>/<tab>/<date>
  const r = await api(`/api/screens/${encodeURIComponent(key)}?market=${mkt}${date ? `&date=${date}` : ""}`).catch((e) => ({ error: e.message }));
  if (!alive()) return;
  if (r.error || r.empty) { main.innerHTML = `<div class="empty"><b>${r.empty ? "No snapshot for this market yet" : "Screen not found"}</b><div class="muted">${esc(r.error || "Build it (from scripts/, PYTHONPATH=.):")}</div>${r.command ? `<code>${esc(r.command)}</code>` : ""}</div>`; return; }
  const d = r.def;
  const href = (t, m = mkt, dd = date) => `#/screens/${key}/${m}/${t}${dd && m === mkt ? "/" + dd : ""}`;
  const sDates = r.dates.map((x, i) => ({ value: x, label: prettyDate(x) + (i > 0 && (r.dates[i - 1] || "").slice(0, 7) !== x.slice(0, 7) ? " · month-end" : "") }));
  main.innerHTML = `<div class="crumbs"><a href="#/screens">← All screens</a></div>` + pageHead(esc(d.name), { context: datePicker(sDates, r.date),
      actions: (d.builtin ? `<button id="scust" title="Start a screen of your own from this one">Customise…</button>`
        : `<a class="btn" href="#/screens/${key}/${mkt}/edit">Edit</a><button class="danger" id="sdel">Delete</button>`)
        + `<a class="btn primary" href="#/screens/new/${mkt}">+ New screen</a>` }) + `
    <p class="sd-lead">${esc(d.description || "")}</p>
    ${tabsHtml([["results", `Results <span class="n">${r.count}</span>`, href("results")], ["criteria", "Criteria", href("criteria")], ["study", "Study", href("study")]], tab)}
    <div id="stab"></div>`;
  main.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(href(tab, b.dataset.v)));
  wireDatePicker(main, sDates, r.date, (dd, latest) => go(href(tab, mkt, latest ? null : dd)));
  main.querySelector("#scust")?.addEventListener("click", () => { store.set("scrDraftFrom", key); go(`#/screens/new/${mkt}`); });
  main.querySelector("#sdel")?.addEventListener("click", async () => {
    if (!confirm(`Delete the screen “${d.name}”?`)) return;
    await api(`/api/screens/${key}`, { method: "DELETE" }); store.set("scrKey", "stage2"); toast(`Deleted “${d.name}”`, "ok"); go(`#/screens/stage2/${mkt}`);
  });
  const host = main.querySelector("#stab");
  if (tab === "criteria") {
    host.innerHTML = `${d.thesis ? `<section class="sec-card"><p><b>Why.</b> ${esc(d.thesis)}</p></section>` : ""}
      <section class="sec-card"><h3>Every condition must hold</h3><ol class="sd-list">${d.conditions.map((c) => `<li>${esc(condText(c, fs))}</li>`).join("")}</ol>
        ${d.criteria ? `<h3>In plain words</h3><table class="dtab"><tbody>${d.criteria.map((c) => `<tr><td><code>${c.code}</code></td><td>${esc(c.text)}</td></tr>`).join("")}</tbody></table>` : ""}
        <p class="muted small">"Tradable" is the market's floor — minimum price and 20-day traded value, a year of history, a valid ATR — the same floor the strategies use.</p></section>
      ${d.used_by?.length ? `<section class="sec-card"><h3>Strategies that draw from this screen</h3><table class="dtab click"><tbody>
        ${d.used_by.map((u) => `<tr data-href="#/strategies/${u.key}/rules"><td><b>${esc(u.name)}</b></td><td>${Object.entries(u.gates).map(([g, c]) => `<code>${g}</code>=${c}`).join(" · ")}</td></tr>`).join("")}</tbody></table>
        <p class="muted small">A strategy evaluates these criteria with the same code, then adds its own trade rules, setups, entry, stop and exit.</p></section>` : ""}`;
    host.querySelectorAll("tr[data-href]").forEach((tr) => tr.onclick = () => go(tr.dataset.href));
    return;
  }
  if (tab === "study") return screenStudy(host, alive, key, mkt, d);
  screenResults(host, r, mkt, d, fs);
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
function screensOverview(main, list, mkt) {
  const card = (x) => {
    const ch = x.prev_count != null ? x.count - x.prev_count : null;
    return `<a class="sec-card scr-card" href="#/screens/${x.key}/${mkt}" title="Open this screen">
      <div class="scr-h"><b>${esc(x.name)}</b>${x.builtin ? "" : '<span class="tag info">yours</span>'}</div>
      <div><span class="scr-n">${x.count ?? "—"}</span> <span class="muted small">stocks qualify${ch ? ` · <span class="${ch > 0 ? "pos" : "neg"}">${ch > 0 ? "+" : ""}${ch}</span> since the previous session` : ""}</span></div>
      <div class="muted small scr-desc">${esc(x.description || "")}</div>
      ${x.top?.length ? `<div class="scr-top">${x.top.slice(0, 8).map((t) => `<span class="chip-s" title="${esc(t.name || "")}">${esc(t.symbol.replace(/\.NS$/, ""))}</span>`).join("")}</div>` : ""}
      ${x.used_by?.length ? `<div class="muted small">Used by: ${x.used_by.map((u) => esc(u.name)).join(", ")}</div>` : ""}</a>`;
  };
  const builtins = list.screens.filter((x) => x.builtin), mine = list.screens.filter((x) => !x.builtin);
  main.innerHTML = pageHead("Screens", { context: `<span class="muted small">${prettyDate(list.date)} · ${list.tradable?.toLocaleString()} tradable stocks</span>${info(`<p>Which stocks are worth a look today. A screen is a set of conditions over every stock's daily snapshot (about 50 fields) — it only qualifies stocks; a strategy adds the trade.</p><p>${list.tradable?.toLocaleString()} of ${list.universe?.toLocaleString()} stocks clear the tradable floor (price, liquidity, a year of history).</p>`)}`,
      actions: `<a class="btn primary" href="#/screens/new/${mkt}">+ New screen</a>` })
    + `
    <h3 class="ov-h">Built-in screens</h3><div class="scr-cards">${builtins.map(card).join("")}
      <a class="sec-card scr-card" href="#/quality"><div class="scr-h"><b>Quality</b></div><div class="muted small">Long-term: companies with durable fundamentals, and when their price is right.</div></a></div>
    <h3 class="ov-h">Your screens</h3><div class="scr-cards">${mine.map(card).join("")}
      <a class="sec-card scr-card scr-new" href="#/screens/new/${mkt}"><div class="scr-h"><b>+ New screen</b></div>
        <div class="muted small">Pick conditions from ~50 fields — returns, RS rank, moving averages, 52-week range, volume, trend, sector — and see the matching stocks as you build. Then study how it did over five years.</div></a></div>`;
}

/** The screen builder: conditions with a live preview; save as one of your screens. */
function screenBuilder(main, alive, mkt, fs, base, editKey) {
  let conds = JSON.parse(JSON.stringify(base.conditions || []));
  const groups = [...new Set(fs.fields.map((f) => f.group))];
  const fieldOpts = (sel, kinds) => groups.map((g) => { const fl = fs.fields.filter((f) => f.group === g && (!kinds || kinds.includes(f.kind)));
    return fl.length ? `<optgroup label="${esc(g)}">${fl.map((f) => `<option value="${f.key}" ${f.key === sel ? "selected" : ""}>${esc(f.label)}</option>`).join("")}</optgroup>` : ""; }).join("");
  const kindOf = (k) => (fs.fields.find((f) => f.key === k) || {}).kind;
  main.innerHTML = `<div class="page-head"><h1>${editKey ? "Edit screen" : "New screen"}</h1>${marketSeg(mkt)}<span class="spacer"></span>
      <a class="ghost btn" href="#/screens/${editKey || store.get("scrKey", "stage2")}/${mkt}">Cancel</a><button class="primary" id="bsave">Save screen</button></div>
    <div class="sec-card builder">
      <div class="b-meta"><input id="bname" placeholder="Name, e.g. Strong leaders near highs" value="${esc(base.name || "")}"><input id="bdesc" placeholder="Description (optional)" value="${esc(base.description || "")}"></div>
      <h3>Stocks where every condition holds</h3><div id="bconds"></div>
      <button class="ghost" id="badd">+ Add condition</button>
      <p class="muted small">Compare a field with a number, or with another field (× a factor, e.g. Close ≥ 52-week high × 0.9). Percent fields are in % (enter 20 for 20%). Hover a field for its meaning.</p>
    </div>${segmented([["results", "Results"], ["study", "Study (5 years of month-ends)"]], "results", "bview")}<div id="bres">${LOADING}</div>`;
  let view = "results";
  main.querySelectorAll(".bview button").forEach((b) => b.onclick = () => { view = b.dataset.v;
    main.querySelectorAll(".bview button").forEach((x) => x.classList.toggle("on", x === b)); preview(); });
  main.querySelectorAll(".mk button").forEach((b) => b.onclick = () => go(`#/screens/${editKey ? editKey + "/" + b.dataset.v + "/edit" : "new/" + b.dataset.v}`));
  const draw = () => {
    main.querySelector("#bconds").innerHTML = conds.map((c, i) => {
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
    }).join("") || '<div class="muted small">No conditions — every stock passes. Add one.</div>';
  };
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
  main.querySelector("#bconds").addEventListener("change", (e) => {
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
    draw(); preview();
  });
  main.querySelector("#bconds").addEventListener("click", (e) => {
    const b = e.target.closest("[data-del]"); if (b) { conds.splice(+b.dataset.del, 1); draw(); preview(); return; }
    const r = e.target.closest("[data-rm]"); if (r) { conds[+r.dataset.i].value.splice(+r.dataset.rm, 1); draw(); preview(); }
  });
  main.querySelector("#badd").onclick = () => { conds.push({ field: "rs_rank", op: ">=", value: 80 }); draw(); preview(); };
  main.querySelector("#bsave").onclick = async () => {
    const name = main.querySelector("#bname").value.trim();
    if (!name) { toast("Give the screen a name", "err"); main.querySelector("#bname").focus(); return; }
    try {
      const r = await api("/api/screens", jsonReq("POST", { id: editKey ? +editKey.slice(1) : null, name, description: main.querySelector("#bdesc").value.trim(), conditions: conds }));
      toast(`Saved “${r.name}”`, "ok"); store.set("scrKey", r.key); go(`#/screens/${r.key}/${mkt}`);
    } catch (err) { toast(err.message.replace(/^\d+ /, ""), "err"); }
  };
  main.querySelectorAll(".b-meta input").forEach((x) => x.onkeydown = (e) => e.stopPropagation());
  draw(); preview();
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
  // Group by market behaviour, then by selection within it. EVERY behaviour in
  // the taxonomy is rendered, including ones with no strategies: all eight
  // strategies here are trend/momentum bets, and without the empty rows the
  // sidebar would imply the space has been explored when one idea has been
  // tried eight ways. The blanks are the map of what is still untested.
  const stratNav = (tax.behaviours || []).map((b) => {
    const mine = all.filter((x) => x.behaviour === b.key);
    if (!mine.length) return `<div class="nav-h">${esc(b.label)}</div><div class="nav-empty">nothing yet</div>`;
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
      context: `<span class="muted small">${newest ? `latest run ${prettyDate(newest)}` : "not run yet"}</span>${info("<p>Every strategy's trades and watch names from its latest run. Strategies run on demand — <b>Run strategies…</b> adds a run to the job queue.</p>")}`,
      actions: `<button class="primary" id="runstrat" title="Run the strategies on today's data (adds a run to the job queue)">Run strategies…</button>` }) + `
    ${r.error ? `<div class="empty"><b>Could not load setups</b><div class="muted">${esc(r.error)}</div></div>` : `
    <div class="setup-runs">${r.runs.map((x) => `<a class="sec-card setup-run" href="#/strategies/${x.strategy}/setups/${mkt}">
        <b>${esc(x.name)}</b><div class="small"><span class="${x.tradeable ? "pos" : "muted"}">${x.tradeable} tradeable</span> · ${x.watch} on watch</div>
        <div class="muted small">${x.screened} from ${esc(x.screen || "its screen")} · ${prettyDate(x.run)}</div></a>`).join("")}</div>
    <div class="chips" id="sshow">${[["all", "All", r.rows.length], ["trade", "Tradeable", r.rows.filter((x) => x.tradeable).length], ["watch", "On watch", r.rows.filter((x) => !x.tradeable).length]]
      .map(([k, t, n]) => `<button class="chip ${k === show ? "on" : ""}" data-s="${k}">${t}<span>${n}</span></button>`).join("")}</div><div id="sclus"></div><div id="stbl"></div>`}`;
  root.querySelectorAll(".mk button").forEach((b) => b.onclick = () => { pageMarket(b.dataset.v); route(); });
  root.querySelector("#runstrat").onclick = () => startJob({ title: `Run strategies · ${mktInfo(mkt).name}`, targets: ["strategies"], market: mkt, screens: true });
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

/** One strategy: Setups today (its latest run) · Rules (its screen + its own rules, entry, exit) · Backtests. */
async function strategyPage(alive, root, key, tab, mkt, runKey) {
  root.innerHTML = LOADING;
  const d = await api(`/api/strategies/${encodeURIComponent(key)}`).catch(() => null);
  if (!alive()) return;
  if (!d) { root.innerHTML = `<div class="empty"><b>Strategy not found</b><div class="muted"><a href="#/strategies">Today's setups</a></div></div>`; return; }
  const trades = d.kind === "screener";
  const tabs = [...(trades ? [["setups", "Setups today"]] : []), ["rules", "Rules"], ["backtests", `Backtests${d.backtests.length ? ` <span class="n">${d.backtests.length}</span>` : ""}`]];
  tab = tabs.some(([k]) => k === tab) ? tab : tabs[0][0];
  document.title = `${d.name} · Strategies · Trading`;
  const kind = { benchmark: "Benchmark", "long-term": "Long-term investing", screener: "Trading strategy" }[d.kind] || "Strategy";
  root.innerHTML = `<div class="crumbs">${kind}</div>
    <div class="page-head"><h1>${esc(d.name)}</h1><code>${esc(d.key)}</code>
      ${d.kind === "long-term" ? `<span class="spacer"></span><a class="btn" href="#/quality">Open the Quality page →</a>` : ""}</div>
    ${d.status ? `<div class="sd-badge"><span class="tag ${statusClass(d.status) === "watch" ? "warn" : statusClass(d.status) === "trade" ? "pos" : "neutral"}" title="${esc(d.status)}">${esc(shortStatus(d.status))}</span>${info(`<p>${mdInline(d.status)}</p>`)}</div>` : ""}
    <p class="sd-lead">${mdInline(d.description)}${d.variant_of ? ` A variant of <a href="#/strategies/${d.variant_of.key}/rules">${esc(d.variant_of.name)}</a>.` : ""}${d.screen ? ` Draws its candidates from the <a href="#/screens/${d.screen.key}/${pageMarket()}/criteria">${esc(d.screen.name)}</a> screen.` : ""}</p>
    ${tabsHtml(tabs.map(([k, t]) => [k, t, `#/strategies/${key}/${k}`]), tab)}<div id="stab"></div>`;
  const host = root.querySelector("#stab");
  if (tab === "setups") return strategySetups(host, alive, key, mkt, runKey);
  if (tab === "backtests") return strategyBacktests(host, d, key);
  strategyRules(host, d, key);
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
  host.innerHTML = `<section class="sdoc sdoc-tab">
    ${d.status ? `<div class="sd-status ${statusClass(d.status)}"><b>Status</b> ${mdInline(d.status)}</div>` : ""}
    ${sec("overview", "Overview", `${d.thesis ? `<p><b>Thesis.</b> ${mdInline(d.thesis)}</p>` : ""}<h3>How it works</h3>${ol(d.how_it_works)}`)}
    ${d.kind === "long-term" && d.gates.length ? sec("rules", "Quality tests", `<p class="muted small">Points out of 100.</p>${codeTable(d.gates, "Worth")}`) : ""}
    ${d.kind !== "long-term" && (d.gates.length || d.watch.length || d.setups.length) ? `<section class="sd-sec" id="sd-rules"><h2>Rules</h2>
      ${fromScreen.length ? `<h3>${num()}Qualify — from the <a href="#/screens/${d.screen.key}/${pageMarket()}/criteria">${esc(d.screen.name)}</a> screen</h3>
        ${codeTable(fromScreen, "Gate", ["Screen", (r) => `<code>${r.screen}</code>`])}` : ""}
      ${own.length ? `<h3>${fromScreen.length ? `${num()}Trade rules — this strategy's own` : "Hard gates"} <span class="muted small">— all must pass, or the stock is AVOID</span></h3>${codeTable(own, "Gate")}` : ""}
      ${d.setups.length ? `<h3>${num()}Setups <span class="muted small">— the patterns that make a stock entry-eligible</span></h3>${codeTable(d.setups, "Setup")}` : ""}
      ${d.watch.length ? `<h3>Warning flags <span class="muted small">— don't disqualify, but cap or downgrade the decision</span></h3>${codeTable(d.watch, "Flag")}` : ""}
      </section>` : ""}
    ${sec("entry", d.kind === "long-term" ? "Is the price right?" : "Entry & exit", `${d.entry_rules.length ? (d.kind === "long-term" ? ul(d.entry_rules) : `<h3>Entry, stop and target</h3>${ol(d.entry_rules)}`) : ""}${d.exit_rules.length ? `<h3>Exit</h3>${ol(d.exit_rules)}` : ""}`)}
    ${sec("decisions", "Decisions", d.decisions.length ? `<table class="dtab"><tbody>${d.decisions.map((x) => `<tr><td><span class="tag ${decisionClass(x.label)}">${esc(x.label)}</span></td><td>${esc(x.text)}</td></tr>`).join("")}</tbody></table>
      <p class="muted small">${esc(d.regime_note)}</p>` : "")}
    ${sec("params", "Parameters", params)}
    ${sec("commands", "Commands", `${cmds}<p class="muted small">Run from <code>scripts/</code> with <code>PYTHONPATH=.</code>.</p>`)}
    ${sec("caveats", "Known caveats", ul(d.caveats))}
    <p class="muted small sd-src">Generated from <code>${esc(d.source.file)}</code> · code last changed ${prettyDate(d.source.modified)} — built from the strategy's own code, so it describes what actually runs.</p></section>`;
  host.querySelectorAll(".copy").forEach((b) => b.onclick = async () => {
    try { await navigator.clipboard.writeText(b.dataset.c); toast("Command copied", "ok"); } catch { toast("Copy failed — select the text instead", "err"); }
  });
}

function strategyBacktests(host, d, key) {
  const pv = (x) => (x == null ? "" : x);
  const canRun = d.kind === "screener";  // the benchmark / quality pages are measured by their own commands
  const runBtn = canRun ? `<div class="bt-run"><button class="primary sm" id="btrun" title="Queue a full-history backtest of this strategy (its documented exit policy) — slow; follow it on System → Runs">Backtest ${esc(mktInfo(pageMarket()).name)}…</button>
      <span class="muted small">runs in the job queue — follow it on <a href="#/runs">System → Runs</a></span></div>` : "";
  host.innerHTML = runBtn + (d.backtests.length ? `<table class="dtab click"><thead><tr><th>Market</th><th>Run</th><th class="num">CAGR</th><th class="num">Excess CAGR</th><th class="num">Max DD</th><th class="num">Sharpe</th><th>Generated</th></tr></thead><tbody>${
      d.backtests.map((b) => { const s = b.summary || {};
        return `<tr data-href="#/reports/${b.id}"><td>${b.market.toUpperCase()}</td><td>${esc(b.run)}</td><td class="num">${esc(pv(s.cagr))}</td>
          <td class="num ${/^-/.test(s.excess_cagr || "") ? "neg" : s.excess_cagr ? "pos" : ""}">${esc(pv(s.excess_cagr))}</td><td class="num">${esc(pv(s.max_drawdown))}</td>
          <td class="num">${esc(pv(s.sharpe))}</td><td class="muted">${prettyDate(b.generated_at)}</td></tr>`; }).join("")}</tbody></table>
      <p class="muted small">A backtest runs the whole strategy — screen, setups, entry, stop, exits, costs and position sizing — day by day. The command is under Rules › Commands.</p>`
    : `<div class="empty"><b>No backtests loaded for this strategy</b><div class="muted">${canRun ? "Queue one with the button above, or run" : "Run"} the command under Rules › Commands; reports load into the app automatically.</div></div>`);
  host.querySelector("#btrun")?.addEventListener("click", () =>
    startJob({ title: `Backtest · ${mktInfo(pageMarket()).name}`, targets: ["backtest"], market: pageMarket(), screens: true, pick: key }));
  host.querySelectorAll("tr[data-href]").forEach((tr) => tr.onclick = () => go(tr.dataset.href));
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
  host.innerHTML = `<div class="page-head sub">${run ? `<span class="run-label">${esc(label)}</span>` : ""}<span class="spacer"></span>
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
      rowClick: (row, visible) => openChartFromList(mkt, row[keep.indexOf(si)], visible.map((r) => r[keep.indexOf(si)]),
        `${strat} · ${activeDec === "all" ? "all" : activeDec.toLowerCase()}`, location.hash),
    });
  };
  dec.onclick = (e) => { const b = e.target.closest("button[data-d]"); if (b) { activeDec = b.dataset.d; store.set("scrDec", activeDec); draw(); } };
  dec.onchange = (e) => { if (e.target.id === "decsel") { activeDec = e.target.value || "all"; store.set("scrDec", activeDec); draw(); } };
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
    // ```pattern <key>``` fences in the learning guides draw that pattern with real candles (learn.js)
    body.querySelectorAll(".md pre > code.language-pattern").forEach((c) => {
      const p = Learn.get(c.textContent.trim());
      if (p) c.parentElement.outerHTML = `<figure class="lp-md">${Learn.svg(p)}<figcaption><a href="#/learn/${p.key}">${esc(p.name)}</a> — open it in Learn</figcaption></figure>`;
    });
    body.querySelectorAll(".md table").forEach((t) => t.outerHTML = `<div class="md-table">${t.outerHTML}</div>`);
    // research docs link to siblings as relative *.md files — open those as their ingested report, not as a dead URL
    body.querySelectorAll('.md a[href$=".md"]').forEach((a) => {
      const f = a.getAttribute("href");
      if (/^(https?:)?\/\//.test(f) || f.includes("/")) return;
      a.onclick = async (e) => {
        e.preventDefault();
        const runs = await api("/api/reports?kind=research").catch(() => []);
        const t = runs.find((x) => x.run === f.replace(/\.md$/, ""));
        if (t) go(t.run.startsWith("learn-") ? `#/learn/${t.run.replace(/^learn-/, "")}` : `#/reports/${t.id}`);
        else toast("That document is not loaded — click Load reports on the Reports archive", "err");
      };
    });
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

const NOTE_TEMPLATES = {
  blank: { label: "Blank note", make: (sym) => ({ title: sym ? `${sym.symbol.replace(/\.NS$/, "")} — notes` : "", body: "", tags: [] }) },
  journal: { label: "Daily journal", make: () => { const d = new Date().toISOString().slice(0, 10); return { title: `Journal — ${longDate(d)}`, tags: ["journal"],
    body: "## Market\n- Tone:\n- Breadth / leading groups:\n\n## Positions\n| Stock | Plan | Action |\n|---|---|---|\n|  |  |  |\n\n## Watching\n- \n\n## Lessons\n- \n" }; } },
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
       table: () => insert("\n| Column | Column |\n|---|---|\n|  |  |\n"), date: () => insert(longDate(new Date().toISOString().slice(0, 10))) })[k]();
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
    date: () => cmd("insertText", longDate(new Date().toISOString().slice(0, 10))),
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
      return { targets, market, strategies: screens ? (all.checked ? "all" : picked) : null,
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
const whenText = (x) => x.monthday ? `Monthly, day ${x.monthday} · ${x.at_time}`
  : `${x.days === "mon,tue,wed,thu,fri" ? "Mon–Fri" : x.days === "tue,wed,thu,fri,sat" ? "Tue–Sat" : x.days.split(",").map((d) => d[0].toUpperCase() + d.slice(1)).join(", ")} · ${x.at_time}`;
const whenNext = (iso) => { if (!iso) return "—"; const d = new Date(iso); return `${WEEKDAY[d.getDay()]} ${prettyDate(iso.slice(0, 10))} · ${iso.slice(11, 16)}`; };

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
      <p>Times are this machine's local time (${esc(d.tz)}). A slot missed while the computer was asleep or the worker was stopped runs once, when the worker next looks.</p>
      <p>On demand only (no schedule by default): <b>strategies</b> — today's setups — and <b>quality</b>. Add a schedule for either to make it automatic.</p>
      <p>From a terminal: <code>python -m jobs schedules</code> · <code>python -m jobs queue</code></p>`),
      actions: `<button class="primary" id="snew">+ New schedule</button>` }) + `
    ${w.alive ? "" : `<div class="sd-status watch"><b>Worker stopped</b> Nothing below will run until the worker is running. <button class="primary sm" id="wkstart">Start worker</button></div>`}
    <section class="sec-card runnow"><div class="sec-card-h"><h3>Run now</h3><span class="muted small">adds the run to the queue · per-market pipelines use ${esc(mktInfo(pageMarket()).name)} (header)</span></div>
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
    const spec = { id: x.id, targets: [t], market: mkt, enabled: $("#sd-on").checked, at_time: $("#sd-time").value,
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
  const worker = w.alive
    ? `<span class="wk ok"><i></i>Worker running</span><span class="muted small">pid ${w.pid} · since ${clock(w.started_at)}</span>`
    : `<span class="wk off"><i></i>Worker stopped</span><span class="muted small">queued runs and schedules wait until it runs.</span>
       <button class="primary sm" id="wkstart">Start worker</button><span class="muted small">To keep it running across restarts: <code>${esc(s.worker_command)}</code></span>`;
  return `<section class="sec-card qpanel"><div class="sec-card-h"><h3>Job queue</h3>${worker}</div>
    ${Q.running ? `<div class="qrow run"><i class="spin"></i><b>Running</b>${what(Q.running)}${by(Q.running)}<span class="muted small">started ${clock(Q.running.started_at)}</span>
        ${Q.running.run_id ? `<a class="small" href="#/runs/${Q.running.run_id}">steps →</a>` : ""}<span class="spacer"></span>
        ${Q.running.cancel_requested ? '<span class="muted small">stopping…</span>' : `<button class="danger sm" data-qstop="${Q.running.id}">Stop</button>`}</div>`
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
      <td class="num">${x.status === "running" ? dur((Date.now() - new Date(x.started_at)) / 1000) : dur(x.duration_s)}</td>
      <td class="sdetail">${esc(x.detail || "")}${x.error ? `<details><summary class="neg">${esc(x.error.split("\n")[0])}</summary><pre>${esc(x.error)}</pre></details>` : ""}</td></tr>`).join("");
  $view.innerHTML = pageHead("Runs") + `
    <section class="sec-card">
      ${run ? `<div class="sec-card-h"><h3>${runId ? `Run #${run.id}` : run.status === "running" ? "Running now" : "Latest run"}</h3>${stBadge(run.status)}
          <span class="muted small">${esc(run.job)}${run.args?.markets ? " · " + esc(run.args.markets.map((m) => MKT_BADGE[m] || m).join(" + ")) : ""} · started ${clock(run.started_at)} (${ago(run.started_at)})
          ${run.finished_at ? ` · took ${dur(run.duration_s)}` : run.status === "running" ? ` · running for ${dur((Date.now() - new Date(run.started_at)) / 1000)}` : ""}</span>
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
  { key: "markets", label: "Markets", pages: [["postmarket", "Post-market", "The day's recap after the close"], ["breadth", "Breadth", "How healthy is the market — risk, not direction"],
    ["sectors", "Sectors", "Leading sectors, industry groups and their leaders"], ["movers", "Movers", "Top gainers and losers"]] },
  { key: "screens", label: "Screens", pages: [["screens", "Screens", "Built-in and your own screens: which stocks qualify"]] },
  { key: "strategies", label: "Strategies", pages: [["strategies", "Strategies", "Today's setups, and each strategy's rules and backtests"]] },
  { key: "chart", label: "Chart", pages: [["chart", "Chart", "Price chart, indicators and drawings"]] },
  { key: "watchlists", label: "Watchlists", pages: [["watchlist", "Watchlists", "Your lists and the screener's picks"]] },
  { key: "library", label: "Library", pages: [["notes", "Notes", "Your notes and trading journal"], ["playbook", "Playbook", "Sector analysis: method and roadmap"],
    ["learn", "Learn", "Learning material: chart patterns and candlesticks"],
    ["todo", "TODO", "Ideas and follow-ups"], ["subindustries", "Sub-industries", "Which sub-industry each company belongs to — review and edit"]] },
  { key: "system", label: "System", pages: [["status", "Status", "Is the data current? And the job queue"], ["runs", "Runs", "Every run, its steps and log"],
    ["schedules", "Schedules", "When each pipeline runs — and run one now"], ["reports", "Reports archive", "Every backtest and screening report the scripts wrote"]] },
];
/** the nav entry a URL belongs to: screens and strategies have one entry per screen / strategy */
function pageIdOf(parts) {
  const p = parts[0] || "chart";
  return p === "screening" ? "strategies" : p === "quality" ? "screens" : p;
}
const PAGE_SECTION = Object.fromEntries(SECTIONS.flatMap((s) => s.pages.map(([p]) => [p, s])));
const sectionOf = (id) => PAGE_SECTION[id] || PAGE_SECTION[id.split("/")[0]] || null;
const $nav = document.getElementById("nav"),
  $navbtn = document.getElementById("navbtn"), $navpanel = document.getElementById("navpanel");

/** highlight the section and tab; each section and tab reopens the exact page you were last on */
/** Top bar: one link per section (a section opens its first page — Markets opens Post-market). A section
 *  with several pages shows them as a tab row under the header, the same tabs pattern pages use inside. */
function renderNav(page) {
  const sec = sectionOf(page);
  // remember the page you were on — but only under its own name: Quality lives in the Screens section,
  // yet "Screens" must keep opening the screens, not the last Quality view
  const first = location.hash.replace(/^#\//, "").split("/")[0] || "chart";
  if (sec && first === page) store.set(`navPage:${page}`, location.hash);
  if (store.get("navPage:screens", "").startsWith("#/quality")) store.set("navPage:screens", null);   // clean up the old value
  const pageHref = (p) => esc(p === page ? location.hash : withMarket(store.get(`navPage:${p}`, `#/${p}`)));
  const secHref_ = (s) => esc(`#/${s.pages[0][0]}`);   // a section link always opens its home page
  $nav.innerHTML = SECTIONS.map((s, i) => `<a href="${secHref_(s)}" data-sec="${s.key}" data-href="${secHref_(s)}" class="sec ${s === sec ? "active" : ""}"
      title="${esc(s.pages.map((x) => x[1]).join(" · "))} (Alt+${i + 1})">${s.label}</a>`).join("");
  const sub = document.getElementById("subnav");
  sub.hidden = !(sec && sec.pages.length > 1);
  sub.innerHTML = sub.hidden ? "" : `<nav class="ptabs subtabs">${sec.pages.map(([p, t, d]) => `<a href="${pageHref(p)}" class="${p === page ? "active" : ""}" title="${esc(d)}">${t}</a>`).join("")}
    <span class="spacer"></span><span class="muted small sub-hint">Alt+[ / ] previous / next</span></nav>`;
  const cur = sec && sec.pages.find(([p]) => p === page);
  $navbtn.innerHTML = `<svg viewBox="0 0 20 20"><path d="M3 5h14M3 10h14M3 15h14"/></svg><b>${sec ? sec.label : "Menu"}</b>${cur && sec.pages.length > 1 ? `<span>› ${cur[1]}</span>` : ""}`;
  $navpanel.innerHTML = SECTIONS.map((s, i) => `<div class="np-sec ${s === sec ? "cur" : ""}"><a class="np-h" href="${secHref_(s)}">${s.label}<kbd>Alt+${i + 1}</kbd></a>
    ${s.pages.length > 1 ? `<div class="np-pages">${s.pages.map(([p, t]) => `<a href="${pageHref(p)}" class="${p === page ? "active" : ""}">${t}</a>`).join("")}</div>` : ""}</div>`).join("");
  closeNavPanel();
  syncMarketSel(page);
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
    e.preventDefault(); go(withMarket(store.get(`navPage:${sec.pages[j][0]}`, `#/${sec.pages[j][0]}`)));
  }
});

// ⌘K / Ctrl+K: go anywhere — a page by name, or a stock by symbol or company name
function openPalette() {
  if (document.querySelector(".palette")) return;
  const pages = [...SECTIONS.flatMap((s) => s.pages.map(([p, t, d]) => ({ kind: "page", label: t, sub: `${s.label} · ${d}`, href: withMarket(store.get(`navPage:${p}`, `#/${p}`)) }))),
    ...THEMES.map(([k, t]) => ({ kind: "page", label: `Theme: ${t}`, sub: "Change the colour theme", theme: k }))];
  const m = el(`<div class="smodal palette"><div class="pal-card"><input placeholder="Go to a page, or a stock (symbol or company)…" spellcheck="false"><div class="pal-list"></div>
    <div class="pal-foot muted small">↑ ↓ to move · Enter to open · Esc to close</div></div></div>`);
  document.body.append(m);
  const inp = m.querySelector("input"), host = m.querySelector(".pal-list");
  let items = [], cur = 0, timer, seq = 0, state = "";   // state: "" | "searching" | "failed"
  const draw = () => {
    host.innerHTML = items.map((x, i) => `<div class="pal-it ${i === cur ? "sel" : ""}" data-i="${i}"><span class="pal-k">${x.kind === "page" ? "Page" : MKT_BADGE[x.market]}</span>
      <b>${esc(x.label)}</b><span class="muted small">${esc(x.sub || "")}</span></div>`).join("")
      + (state === "searching" ? '<div class="muted small pal-none"><span class="spin"></span> Searching stocks…</div>'
        : state === "failed" ? '<div class="small pal-none neg">Stock search failed — is the web server running?</div>'
        : items.length ? "" : `<div class="muted small pal-none">No page or stock matches “${esc(inp.value.trim())}”. Try a ticker (AAPL, RELIANCE) or part of a company name.</div>`);
    host.querySelector(".sel")?.scrollIntoView({ block: "nearest" });
  };
  const update = async () => {
    const q = inp.value.trim().toLowerCase(), my = ++seq;
    const pg = pages.filter((p) => !q || p.label.toLowerCase().includes(q) || p.sub.toLowerCase().includes(q));
    items = pg.slice(0, q ? 6 : 20); cur = 0; state = q ? "searching" : ""; draw();
    if (q.length < 1) return;
    const syms = await api(`/api/symbols?q=${encodeURIComponent(q)}&limit=8`).catch(() => null);
    if (my !== seq) return;
    state = syms ? "" : "failed";
    items = [...pg.slice(0, 5), ...(syms || []).map((r) => ({ kind: "symbol", market: r.market, label: r.symbol.replace(/\.NS$/, ""), sub: r.name || r.sector || "",
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

/** Learn: a menu of every candlestick and chart pattern (learn.js), each drawn with real candles;
 *  the long-form guides (research/learn-*.md) open as their ingested reports */
async function learnPage(alive, topic) {
  $view.innerHTML = LOADING;
  const runs = (await api("/api/reports?kind=research").catch(() => [])).filter((x) => x.run.startsWith("learn-")).sort((a, b) => a.run.localeCompare(b.run));
  if (!alive()) return;
  const guide = runs.find((x) => x.run === `learn-${topic}`);
  if (guide) return reportPage(alive, guide.id);
  // #/learn/candles and #/learn/charts open one family; a pattern opens in its own family's menu
  const p = topic && Learn.get(topic), famView = ["candles", "charts"].includes(topic) ? topic : null;
  const fam = p ? Learn.familyOf(p) : famView || store.get("learnFam", "candles");
  store.set("learnFam", fam);
  document.title = `${p ? p.name + " · " : ""}Learn · Trading`;
  const guides = runs.length ? `<div class="nav-h">Full guides</div>${runs.map((x) => `<a class="nav-item" href="#/learn/${esc(x.run.replace(/^learn-/, ""))}"><span><b class="sn">${esc((x.title || x.run).replace(/ — a field guide$/, ""))}</b></span></a>`).join("")}` : "";
  $view.innerHTML = `<div class="rep-layout"><aside class="rep-nav strat-nav lp-nav">
      ${segmented([["candles", "Candlesticks"], ["charts", "Chart patterns"]], fam, "lpfam")}
      <label class="filter"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input id="lpf" placeholder="Find a pattern" spellcheck="false"></label>
      <a class="nav-item ${p ? "" : "active"}" href="#/learn/${fam}"><span><b class="sn">All ${fam === "charts" ? "chart patterns" : "candlestick patterns"}</b></span></a>
      ${Learn.nav(p?.key, fam)}${guides}
    </aside><section class="scr-main lp-main">${p ? Learn.detail(p) : pageHead(famView === "charts" ? "Chart patterns" : famView === "candles" ? "Candlestick patterns" : "Learn", { context: info("<p>Every pattern drawn with real candles. Candlestick patterns show the context they form in (faded) and the bar that confirms them; chart patterns show the pivot that triggers them and the level that invalidates them, with volume. Pick one from the menu or a card below.</p><p>The long-form guides are <code>research/learn-*.md</code>.</p>") }) + Learn.overview(famView)}</section></div>`;
  $view.querySelectorAll(".lpfam button").forEach((b) => b.onclick = () => go(`#/learn/${b.dataset.v}`));
  const f = $view.querySelector("#lpf");
  f.oninput = () => { const q = f.value.trim().toLowerCase();
    $view.querySelectorAll(".lp-nav .nav-item[data-k]").forEach((a) => a.hidden = !!q && !a.dataset.k.includes(q));
    $view.querySelectorAll(".lp-nav .nav-h").forEach((h) => { let e = h.nextElementSibling, any = false; while (e && !e.classList.contains("nav-h")) { if (e.dataset.k && !e.hidden) any = true; e = e.nextElementSibling; } h.hidden = !!q && !any; }); };
  f.onkeydown = (e) => { if (e.key === "Enter") { const a = [...$view.querySelectorAll(".lp-nav .nav-item[data-k]")].find((x) => !x.hidden); if (a) go(a.getAttribute("href")); } };
  $view.querySelector(".lp-nav .nav-item.active")?.scrollIntoView({ block: "nearest" });
  if (p) window.scrollTo(0, 0);
}

/** the sector-analysis playbook (research/sector-analysis-playbook.md), shown as its ingested report */
async function playbookPage(alive) {
  $view.innerHTML = LOADING;
  const runs = await api("/api/reports?kind=research").catch(() => []);
  if (!alive()) return;
  const r = runs.find((x) => x.run === "sector-analysis-playbook");
  if (!r) {
    $view.innerHTML = `<div class="empty"><b>Playbook not loaded</b><div class="muted">Click <b>Load reports</b> (top right) to load research/sector-analysis-playbook.md.</div></div>`;
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
  renderNav(pageIdOf(parts));
  document.body.dataset.page = page;
  try {
    if (page === "chart") await chartPage(alive, parts[1], parts[2], parts[3]);
    else if (page === "screening") go(`#/strategies/${encodeURIComponent(parts[2] || "trend_pullback")}/setups/${parts[1] || ""}`);
    else if (page === "screens") await screensPage(alive, parts[1], parts[2], parts[3], parts[4]);
    else if (page === "watchlist") await watchlistPage(alive, parts[1]);
    else if (page === "strategies") await strategiesPage(alive, parts[1], parts[2], parts[3], parts[4]);
    else if (page === "quality") await qualityPage(alive, parts[1]);
    else if (page === "breadth") await breadthPage(alive, parts[1]);
    else if (page === "movers") await moversPage(alive, parts[1]);
    else if (page === "postmarket") await postmarketPage(alive, parts[1], parts[2], parts[3]);
    else if (page === "sectors") await sectorsPage(alive, parts[1], parts[2], parts[3]);
    else if (page === "reports") await (parts[1] ? reportPage(alive, parts[1], parts[2]) : reportsPage(alive));
    else if (page === "playbook") await playbookPage(alive);
    else if (page === "learn") await learnPage(alive, parts[1]);
    else if (page === "status") await statusPage(alive, parts[1]);
    else if (page === "schedules") await schedulesPage(alive);
    else if (page === "runs") await runsPage(alive, parts[1]);
    else if (page === "subindustries") await subindustriesPage(alive, parts[1], parts[2]);
    else if (page === "todo") await todoPage(alive);
    else if (page === "notes") await notesPage(alive, parts.slice(1));
    else go("#/chart");
  } catch (e) {
    if (alive()) $view.innerHTML = `<div class="empty"><b>Something went wrong</b><div class="muted">${esc(e.message)}</div></div>`;
  }
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
  <dl><dt>Type a letter</dt><dd>Search symbols (on the chart)</dd><dt>↑ / ↓</dt><dd>Previous / next symbol in the list you opened it from</dd>
  <dt>Alt + T / H / J / V / C / F</dt><dd>Trend line / horizontal line / horizontal ray / vertical line / cross line / Fib retracement</dd>
  <dt>Drag the chart</dt><dd>Pan left/right and up/down (up/down turns auto-scale off; click “auto” to restore)</dd>
  <dt>Drag the price axis</dt><dd>Stretch / squeeze the price scale</dd><dt>Alt + R</dt><dd>Reset the chart view</dd>
  <dt>Shift + drag</dt><dd>Measure</dd><dt>Esc</dt><dd>Cancel drawing / deselect</dd><dt>Del</dt><dd>Delete the selected drawing</dd>
  <dt>⌘ / Ctrl + Z</dt><dd>Undo the last drawing change</dd>
  <dt>⌘ / Ctrl + K</dt><dd>Go anywhere: a page, or a stock by symbol or company name</dd>
  <dt>Alt + 1 … ${SECTIONS.length}</dt><dd>${SECTIONS.map((x) => x.label).join(" / ")}</dd><dt>Alt + 0</dt><dd>Data status</dd><dt>Alt + [ / ]</dt><dd>Previous / next tab in the section</dd>
  <dt>?</dt><dd>Show this help</dd></dl>
  <button class="ghost">Close</button></div></div>`);
document.body.append(HELP);
HELP.onclick = (e) => { if (e.target === HELP || e.target.tagName === "BUTTON") HELP.hidden = true; };
document.addEventListener("keydown", (e) => {
  if ((e.key === "?" || (e.key === "/" && e.shiftKey)) && !e.target.closest?.("input, select, textarea")) { HELP.hidden = !HELP.hidden; e.preventDefault(); e.stopImmediatePropagation(); }
  else if (e.key === "Escape") HELP.hidden = true;
}, true);
route();
document.getElementById("palbtn").onclick = () => openPalette();
