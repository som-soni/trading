"use strict";
/* Chart › Analysis: one stock read through the analysis framework (scripts/analysis).
 *
 *   #/analysis/<market>/<symbol>                 the company: today's evidence and its latest analysis (a draft autosaves)
 *   #/analysis/<market>/<symbol>/<id>            one saved company analysis (a finished one shows the evidence it was made on)
 *   #/analysis/<market>/<symbol>/entry           the entry: market, sector and chart as of the latest session
 *   #/analysis/<market>/<symbol>/entry/@<date>   ... as of a past session (only what was known then, plus what came after)
 *   #/analysis/<market>/<symbol>/entry/<id>      one saved entry analysis, with its plan
 *   #/analysis/framework[/entry]                 a framework itself: pillars, checks with live thresholds, questions
 *   #/analysis/all                               every stock analysed, its latest analysis of each kind
 *
 * Every judgement is made by the server (scripts/analysis/framework.py and entry.py); this page only formats it and
 * records your answers. Loaded before app.js; uses its helpers (api, esc, store, toast, …) at call time. */

const analysisHref = (m, s, id) => `#/analysis/${m}/${encodeURIComponent(s)}${id ? `/${id}` : ""}`;
const anEntryHref = (m, s, id) => `#/analysis/${m}/${encodeURIComponent(s)}/entry${id ? `/${id}` : ""}`;
const AN_STATUS = { good: ["pos", "good"], ok: ["warn", "ok"], bad: ["neg", "bad"], na: ["neutral", "n/a"], info: ["info", "info"] };
const AN_RATING = { Strong: "pos", Mixed: "warn", Weak: "neg", Thin: "neutral", "No data": "neutral" };
const anTag = (st) => `<span class="tag ${AN_STATUS[st]?.[0] || ""}">${AN_STATUS[st]?.[1] || esc(st)}</span>`;
const anDate = (s) => (s ? prettyDate(s) : "");

/** in-page links ([data-sec]) scroll to their section instead of changing the route */
function anScrollTo(e) {
  const a = e.target.closest("[data-sec]"); if (!a) return;
  e.preventDefault(); document.getElementById(a.dataset.sec)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function anValue(v, kind) {
  if (v == null || v === "") return "";
  if (typeof v !== "number") return esc(v);
  const sg = (x, d) => `${x > 0 ? "+" : x < 0 ? "−" : ""}${Math.abs(x).toFixed(d)}`;
  switch (kind) {
    case "pct": return `${(v * 100).toFixed(Math.abs(v) >= 1 ? 0 : 1)}%`;
    case "pp": return `${sg(v * 100, 1)} pts`;
    case "pp_raw": return `${sg(v, 1)} pts`;
    case "pct_raw": return `${v.toFixed(1)}%`;
    case "x": return `${v >= 100 ? Math.round(v) : v.toFixed(2)}×`;
    case "days": return `${sg(v, 0)} days`;
    default: return Number.isInteger(v) || Math.abs(v) >= 10 ? String(Math.round(v)) : v.toFixed(1);
  }
}

async function analysisPage(alive, a1, a2, a3, a4) {
  if (a1 === "framework") return analysisFrameworkPage(alive, a2);
  if (a1 === "all") return analysesListPage(alive);
  const market = pageMarket(a1);
  const symbol = a2 || store.get("lastSymbol:" + market, market === "us" ? "AAPL" : "RELIANCE.NS");
  store.set("lastMarket", market); store.set("lastSymbol:" + market, symbol);
  // two frameworks on one page: the company (is the business worth owning?) and the entry (is this session a
  // low-risk entry?) — #/analysis/<m>/<s>[/<id>] and #/analysis/<m>/<s>/entry[/<id> | /@<date>]
  const isEntry = a3 === "entry";
  const arg = isEntry ? a4 : a3;
  const asDate = arg?.startsWith("@") ? arg.slice(1) : null;
  const savedId = arg && !asDate ? +arg : null;
  document.title = `${bareSymbol(symbol)} ${isEntry ? "entry" : "analysis"} · Trading`;
  $view.innerHTML = LOADING;
  const fwAll = await api("/api/analysis/framework");
  const fw = isEntry ? fwAll.entry : fwAll;
  const q = `market=${market}&symbol=${encodeURIComponent(symbol)}`;
  let cur = null, d;
  if (isEntry) {
    // an entry analysis is read as of its own session: a saved one re-reads that session (and what came after)
    if (savedId) cur = await api(`/api/analyses/${savedId}`).catch(() => null);
    const day = cur?.asof || asDate;
    d = await api(`/api/analysis/entry?${q}${day ? `&date=${day}` : ""}`);
    if (!cur && !asDate && d.history[0]?.status === "draft" && d.history[0].asof === d.asof) cur = await api(`/api/analyses/${d.history[0].id}`).catch(() => null);
  } else {
    d = await api(`/api/analysis?${q}`);
    const openId = savedId || d.history[0]?.id;   // the one in the URL, else the stock's latest
    cur = openId ? await api(`/api/analyses/${openId}`).catch(() => null) : null;
  }
  if (!alive()) return;
  if (cur && cur.kind !== (isEntry ? "entry" : "company")) { go(cur.kind === "entry" ? anEntryHref(market, symbol, cur.id) : analysisHref(market, symbol, cur.id)); return; }
  const final = cur?.status === "final";
  // a finished analysis shows the evidence it was made on (and marks what reads differently now); a draft, the live read
  const ev = final ? cur.evidence : d;
  const live = d.results, res = ev.results || {}, sm = ev.summary || {};
  const fmts = fw.formats || fwAll.formats, ratingOf = (k) => sm.pillars?.[k] || {};
  const answers = cur ? structuredClone(cur.answers || {}) : {}, verdict = cur ? structuredClone(cur.verdict || {}) : {};
  const hrefFor = (id) => (isEntry ? anEntryHref(market, symbol, id) : analysisHref(market, symbol, id));
  const nowWord = isEntry ? "on re-reading" : "today";

  const hist = d.history.length ? `<select id="anhist" title="${isEntry ? "Entry analyses" : "Analyses"} of this stock, newest first"><option value="">${isEntry ? "Saved entry analyses…" : "Analyses…"}</option>${d.history.map((h) => `<option value="${h.id}" ${h.id === cur?.id ? "selected" : ""}>
      ${esc(isEntry ? `as of ${anDate(h.asof)}` : anDate(h.created_at))} · ${h.status === "final" ? esc(h.verdict?.decision || "finished") : "draft"}${h.verdict?.conviction ? ` · ${"★".repeat(h.verdict.conviction)}` : ""}</option>`).join("")}</select>` : "";
  const actions = !cur ? `<span class="muted small" id="ansaved"></span><button class="btn" id="anstart" title="Record your answers and ${isEntry ? "plan" : "verdict"} (answering any question starts one too)">Start ${isEntry ? "entry analysis" : "analysis"}</button>`
    : final ? `<button class="btn" id="anrevise" title="${isEntry ? "A new entry analysis on the latest session" : "A new draft with today's evidence, starting from this analysis's answers"}">${isEntry ? "New on latest" : "Revise"}</button>`
    : `<span class="muted small" id="ansaved">${cur.updated_at ? `saved ${esc(anDate(cur.updated_at))}` : ""}</span>
       <button class="btn" id="anfinish" title="Freeze the evidence with your answers, so you can compare later">Finish</button>`;
  const kindTabs = `<span class="seg an-kind"><a class="${isEntry ? "" : "on"}" href="${analysisHref(market, symbol)}" title="Is the business worth owning?">Company</a><a class="${isEntry ? "on" : ""}" href="${anEntryHref(market, symbol)}" title="Is this a low-risk time to buy — market, sector and chart?">Entry</a></span>`;
  const dateCtl = isEntry ? `<label class="an-date" title="Read the entry as of a past session — only what was known then">as of <input type="date" id="andate" value="${esc(d.asof)}" max="${esc(d.latest)}" ${cur ? "disabled" : ""}></label>
      ${d.asof !== d.latest && !cur ? `<button class="ghost" id="anlatest" title="Back to the latest session">Latest</button>` : ""}` : "";
  const head = `<div class="page-head co-head"><h1>${esc(d.name || bareSymbol(symbol))}</h1><span class="mkt">${MKT_BADGE[market] || market}</span><span class="muted">${esc(bareSymbol(symbol))}</span>
      ${kindTabs}${dateCtl}<span class="spacer"></span>
      <form class="wl-add" autocomplete="off" id="ansearch"><div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input placeholder="Analyse a stock" spellcheck="false"><ul hidden></ul></div></form>
      ${hist}${actions}${cur ? `<button class="ghost icon" id="andel" title="Delete this analysis" aria-label="Delete">×</button>` : ""}</div>
    <div class="muted small co-sub">${final ? `Finished ${esc(anDate(cur.finished_at))} — evidence as of ${esc(anDate(ev.asof))}, framework v${esc(cur.framework_version)}${cur.framework_version !== fw.version ? ` (now v${esc(fw.version)})` : ""}. Checks that read differently ${nowWord} are marked.`
      : `Evidence as of ${esc(anDate(ev.asof))}${isEntry && d.context?.snapshot_date && d.context.snapshot_date !== d.asof ? ` (RS rank from the ${esc(anDate(d.context.snapshot_date))} snapshot)` : ""} · ${isEntry ? "entry" : ""} framework v${esc(fw.version)} · your answers save as you type${cur ? "" : " (the first one starts an analysis)"}`}
      · <a href="#/analysis/framework${isEntry ? "/entry" : ""}">how the framework works</a> · <a href="#/analysis/all">all analyses</a></div>`;

  // summary: the evidence score, each pillar's rating (and yours), red flags, the verdict
  const myRating = (k) => {   // your questions in a pillar, summed the way the checks are
    const rs = fw.pillars.find((p) => p.key === k).questions.map((q) => answers[q.code]?.rating).filter(Boolean);
    if (!rs.length) return null;
    const s = rs.reduce((a, r) => a + (r === "good" ? 1 : r === "ok" ? 0.5 : 0), 0) / rs.length;
    return s >= 0.7 ? "good" : s >= 0.4 ? "ok" : "bad";
  };
  const chips = fw.pillars.map((p) => { const r = ratingOf(p.key), mine = myRating(p.key);
    return `<a class="an-chip" href="#an-${p.key}" data-sec="an-${p.key}"><span>${esc(p.name)}</span>
      <span>${r.rating ? `<span class="tag ${AN_RATING[r.rating] || ""}">${esc(r.rating)}</span>` : '<span class="muted small">—</span>'}${mine ? ` <span class="an-mine" title="Your rating, from your answers">you: ${anTag(mine)}</span>` : ""}</span>
      <span class="an-bar" title="${r.good || 0} good · ${r.ok || 0} ok · ${r.bad || 0} bad · ${r.na || 0} n/a">${["good", "ok", "bad", "na"].map((s) => `<i class="an-${s}" style="flex:${r[s] || 0}"></i>`).join("")}</span></a>`; }).join("");
  const flags = (sm.flags || []).length ? `<div class="an-flags"><b>Red flags</b> ${sm.flags.map((f) => `<a href="#an-${fw.pillars.find((p) => p.checks.some((c) => c.code === f.code))?.key}" class="tag neg" title="${esc(f.detail)}">${esc(f.code)} ${esc(f.label)}</a>`).join(" ")}</div>` : "";
  const POS = ["Buy", "Accumulate", "Buy now", "Buy on trigger"], NEG = ["Sell", "Avoid", "Trim", "Pass"];
  const vsum = verdict.decision ? `<div class="an-vsum"><span class="tag ${POS.includes(verdict.decision) ? "pos" : NEG.includes(verdict.decision) ? "neg" : "warn"}">${esc(verdict.decision)}</span>
      ${verdict.conviction ? `<span title="Conviction">${"★".repeat(verdict.conviction)}<span class="muted">${"★".repeat(5 - verdict.conviction)}</span></span>` : ""}
      ${isEntry && verdict.entry && verdict.stop ? `<span class="muted">entry ${esc(verdict.entry)} · stop ${esc(verdict.stop)}${verdict.target ? ` · target ${esc(verdict.target)}` : ""}</span>` : ""}
      ${!isEntry && verdict.thesis ? `<span class="muted">${esc(verdict.thesis.slice(0, 220))}${verdict.thesis.length > 220 ? "…" : ""}</span>` : ""}</div>` : "";
  const summary = `<section class="co-sec an-summary"><div class="an-score"><b>${sm.score ?? "—"}</b><span class="muted small">${isEntry ? "entry" : "evidence"} score<br>${sm.rated || 0} rated pillars</span></div>
      <div class="an-chips">${chips}</div>${flags}${vsum}</section>`;

  const editable = !final;               // no analysis yet: the first answer starts one
  const dis = editable ? "" : "disabled";
  const checkRow = (c) => { const r = res[c.code] || { status: "na" }, now = live[c.code];
    const changed = final && now && now.status !== r.status;
    return `<tr><td>${anTag(r.status)}${changed ? `<div class="an-now" title="${esc(nowWord)}: ${esc(now.detail || "")}">now ${anTag(now.status)}</div>` : ""}</td>
      <td><b>${esc(c.code)}</b> ${esc(c.label)}<div class="muted small">${esc(c.rule)}</div></td>
      <td class="num">${anValue(r.value, fmts[c.code])}${r.detail ? `<div class="muted small">${esc(r.detail)}</div>` : ""}</td></tr>`; };
  const seg = (name, opts, val, labels = {}) => `<span class="seg an-seg" data-name="${esc(name)}">${opts.map((o) => `<button type="button" data-v="${esc(o)}" class="${String(val) === String(o) ? "on" : ""}" ${dis}>${esc(labels[o] ?? o)}</button>`).join("")}</span>`;
  const qBlock = (q) => `<div class="an-q"><div><b>${esc(q.code)}</b> ${esc(q.question)}<div class="muted small">${esc(q.hint)}</div></div>
      ${seg(`a:${q.code}`, fw.ratings, answers[q.code]?.rating)}
      <textarea data-name="n:${esc(q.code)}" rows="2" placeholder="${final ? "" : "Your answer…"}" ${dis}>${esc(answers[q.code]?.note || "")}</textarea></div>`;
  const pillars = fw.pillars.map((p) => { const r = ratingOf(p.key);
    return `<section class="co-sec" id="an-${p.key}"><h2>${esc(p.name)} ${r.rating ? `<span class="tag ${AN_RATING[r.rating] || ""}">${esc(r.rating)}</span>` : ""}
        ${r.score != null ? `<span class="muted small">${Math.round(r.score * 100)}% · ${r.good} good, ${r.ok} ok, ${r.bad} bad${r.na ? `, ${r.na} n/a` : ""}</span>` : ""}</h2>
      <p class="muted an-pq">${esc(p.question)}</p>
      <table class="dtab sepa-tests an-checks"><tbody>${p.checks.map(checkRow).join("")}</tbody></table>
      <div class="an-yours"><h3>Your view</h3>${p.questions.map(qBlock).join("")}
        <textarea data-name="n:${esc(p.key)}" rows="2" placeholder="${final ? "" : `Other notes on ${esc(p.name.toLowerCase())}…`}" ${dis}>${esc(answers[p.key]?.note || "")}</textarea></div></section>`; }).join("");

  let closing, navTail;
  if (isEntry) {
    const pf = Object.fromEntries(fw.plan.map((v) => [v.key, v]));
    const lv = ev.levels || [];
    const px = (v) => (v == null ? "" : Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }));
    const lvRows = lv.map((l, i) => `<tr><td><span class="tag ${l.kind === "stop" ? "neg" : l.kind === "target" ? "pos" : "info"}">${esc(l.kind)}</span></td>
        <td>${esc(l.label)}<div class="muted small">${esc(l.source)}</div></td><td class="num">${px(l.price)}<div class="muted small">${l.vs_close == null ? "" : `${l.vs_close >= 0 ? "+" : "−"}${Math.abs(l.vs_close * 100).toFixed(1)}%`}</div></td>
        <td class="num">${editable ? `<button class="ghost an-use" data-i="${i}" title="Put this price in the plan as the ${esc(l.kind)}">use as ${esc(l.kind)}</button>` : ""}</td></tr>`).join("");
    const out = d.outcome;
    const since = out ? `<section class="co-sec" id="an-since"><h2>Since ${esc(anDate(d.asof))} <span class="muted small">what the price did after — hindsight, not part of the read</span></h2>
        <div class="co-ratios">${[["1 week", out.returns["5"]], ["1 month", out.returns["21"]], ["3 months", out.returns["63"]]].map(([k, v]) => `<div><span class="muted">${k}</span><b class="${v > 0 ? "pos" : v < 0 ? "neg" : ""}">${v == null ? "—" : `${v >= 0 ? "+" : "−"}${Math.abs(v * 100).toFixed(1)}%`}</b></div>`).join("")}
          <div><span class="muted">Highest / lowest since</span><b>${px(out.high)} / ${px(out.low)}</b></div><div><span class="muted">Last close (${esc(anDate(out.last_date))})</span><b>${px(out.last)}</b></div></div>
        <div class="muted small an-plan-out" id="anplanout"></div></section>` : "";
    closing = `<section class="co-sec" id="an-levels"><h2>Reference levels <span class="muted small">prices the chart offers for a plan — not a recommendation</span></h2>
        ${lv.length ? `<table class="dtab an-checks"><tbody>${lvRows}</tbody></table>` : '<div class="muted small">No levels for this session.</div>'}
        <div class="muted small">Close ${px(ev.price)}${ev.atr ? ` · ATR(14) ${px(ev.atr)}` : ""}. Levels come from the base window, the chart-pattern detectors, support & resistance zones, the 50-day and the ATR — the same rules as the chart's indicators.</div></section>
      <section class="co-sec" id="an-verdict"><h2>Plan <span class="muted small">yours — the framework never decides</span></h2>
      <div class="an-vgrid">
        <label>${esc(pf.decision.label)}</label><div>${seg("v:decision", fw.decisions, verdict.decision)}</div>
        <label>${esc(pf.conviction.label)}</label><div>${seg("v:conviction", [1, 2, 3, 4, 5], verdict.conviction)} <span class="muted small">${esc(pf.conviction.hint)}</span></div>
        ${["entry", "stop", "target", "account", "risk_pct"].map((k) => `<label>${esc(pf[k].label)}</label><input data-name="v:${k}" inputmode="decimal" value="${esc(verdict[k] ?? "")}" placeholder="${esc(pf[k].hint)}" ${dis}>`).join("")}
        <label>Position</label><div class="an-calc" id="ancalc"></div>
        <label>${esc(pf.note.label)}</label><textarea data-name="v:note" rows="3" placeholder="${esc(pf.note.hint)}" ${dis}>${esc(verdict.note || "")}</textarea>
        <label>${esc(pf.valid_until.label)}</label><input data-name="v:valid_until" value="${esc(verdict.valid_until || "")}" placeholder="${esc(pf.valid_until.hint)}" ${dis}>
      </div></section>${since}`;
    navTail = `<a href="#an-levels" data-sec="an-levels">Levels</a><a href="#an-verdict" data-sec="an-verdict">Plan</a>${out ? '<a href="#an-since" data-sec="an-since">Since</a>' : ""}`;
  } else {
    const vf = Object.fromEntries(fw.verdict.map((v) => [v.key, v]));
    closing = `<section class="co-sec" id="an-verdict"><h2>Verdict <span class="muted small">yours — the framework never decides</span></h2>
      <div class="an-vgrid">
        <label>${esc(vf.decision.label)}</label><div>${seg("v:decision", fw.decisions, verdict.decision)}</div>
        <label>${esc(vf.conviction.label)}</label><div>${seg("v:conviction", [1, 2, 3, 4, 5], verdict.conviction)} <span class="muted small">${esc(vf.conviction.hint)}</span></div>
        ${["thesis", "invalidation"].map((k) => `<label>${esc(vf[k].label)}</label><textarea data-name="v:${k}" rows="3" placeholder="${esc(vf[k].hint)}" ${dis}>${esc(verdict[k] || "")}</textarea>`).join("")}
        <label>${esc(vf.review_on.label)}</label><input data-name="v:review_on" value="${esc(verdict.review_on || "")}" placeholder="${esc(vf.review_on.hint)}" ${dis}>
      </div></section>`;
    navTail = '<a href="#an-verdict" data-sec="an-verdict">Verdict</a>';
  }
  const nav = `<nav class="co-nav">${fw.pillars.map((p) => `<a href="#an-${p.key}" data-sec="an-${p.key}">${esc(p.name)}</a>`).join("")}${navTail}</nav>`;
  $view.innerHTML = head + summary + nav + pillars + closing;

  // ---- wiring
  $view.querySelectorAll(".an-summary, .co-nav").forEach((x) => (x.onclick = anScrollTo));
  const f = $view.querySelector("#ansearch");
  const goStock = (m, s) => go(isEntry ? anEntryHref(m, s) : analysisHref(m, s));
  symbolSearch(f.querySelector("input"), f.querySelector("ul"), market, (s, m) => goStock(m || market, s));
  f.onsubmit = (e) => { e.preventDefault(); const v = f.querySelector("input").value.trim().toUpperCase(); if (v) goStock(market, v); };
  $view.querySelector("#anhist")?.addEventListener("change", (e) => go(e.target.value ? hrefFor(e.target.value) : hrefFor()));
  $view.querySelector("#andate")?.addEventListener("change", (e) => { if (e.target.value) go(anEntryHref(market, symbol, "@" + e.target.value)); });
  $view.querySelector("#anlatest")?.addEventListener("click", () => go(anEntryHref(market, symbol)));
  const create = (date) => api("/api/analyses", jsonReq("POST", { market, symbol, kind: isEntry ? "entry" : "company", date: isEntry ? date : null }));
  $view.querySelector("#anstart")?.addEventListener("click", async (e) => {
    e.target.disabled = true;
    try { const a = await create(d.asof); go(hrefFor(a.id)); } catch (err) { e.target.disabled = false; toast(err.message, "err"); }
  });
  $view.querySelector("#anrevise")?.addEventListener("click", async (e) => {
    e.target.disabled = true;
    try {
      const a = await create(null);   // a company revision: today's evidence; an entry: the latest session
      toast(isEntry ? "New entry analysis on the latest session" : "New draft — today's evidence, your last answers to revise", "ok"); go(hrefFor(a.id));
    } catch (err) { e.target.disabled = false; toast(err.message, "err"); }
  });
  const finish = async (e) => {
    e.target.disabled = true;
    try {
      await saveNow();
      await api(`/api/analyses/${cur.id}`, jsonReq("PUT", { refresh: true, status: "final" }));
      toast("Finished — the evidence is frozen with your answers", "ok"); route();
    } catch (err) { e.target.disabled = false; toast(err.message, "err"); }
  };
  $view.querySelector("#anfinish")?.addEventListener("click", finish);
  $view.querySelector("#andel")?.addEventListener("click", async () => {
    if (!confirm(`Delete the ${cur.status === "final" ? "finished" : "draft"} ${isEntry ? "entry " : ""}analysis of ${bareSymbol(symbol)} from ${anDate(isEntry ? cur.asof : cur.created_at)}?`)) return;
    await api(`/api/analyses/${cur.id}`, { method: "DELETE" });
    toast("Analysis deleted", "ok"); go(hrefFor());
  });

  // the plan's arithmetic — on your own numbers: risk per share, reward / risk, the position for your risk per trade,
  // and (for a past session) whether the price since reached your stop or target
  const num = (v) => { const x = parseFloat(String(v ?? "").replace(/,/g, "")); return Number.isFinite(x) ? x : null; };
  const calc = () => {
    const box = $view.querySelector("#ancalc"); if (!box) return;
    const e = num(verdict.entry), s = num(verdict.stop), t = num(verdict.target), acct = num(verdict.account), rp = num(verdict.risk_pct);
    const bits = [];
    if (e && s && e > s) {
      const r = e - s;
      bits.push(`risk ${r.toLocaleString(undefined, { maximumFractionDigits: 2 })} a share (${(r / e * 100).toFixed(1)}%)`);
      if (t && t > e) bits.push(`reward / risk ${((t - e) / r).toFixed(1)}×`);
      if (acct && rp) {
        const sh = Math.floor(acct * rp / 100 / r);
        bits.push(`${sh.toLocaleString()} shares = ${(sh * e).toLocaleString(undefined, { maximumFractionDigits: 0 })} (${(sh * e / acct * 100).toFixed(0)}% of the account)`);
      }
    } else if (e && s) bits.push("the stop must be below the entry");
    box.innerHTML = bits.length ? bits.map(esc).join(" · ") : '<span class="muted small">Enter an entry and a stop (and your account and risk %) to size it.</span>';
    const po = $view.querySelector("#anplanout"), o = d.outcome;
    if (po && o) po.textContent = e && s && e > s ? anReplay(o.path || [], ev.price, e, s, t) : "Enter an entry and a stop to replay the plan against what came after.";
  };
  calc();
  if (!editable) return;

  // autosave: answers and verdict, a moment after the last change
  let timer = null, dirty = false;
  const $saved = $view.querySelector("#ansaved");
  const saveNow = async () => {
    clearTimeout(timer);
    if (!dirty) return;
    dirty = false;
    try {
      if (!cur) {   // the first answer: a draft with this evidence; the URL names it (no re-render: you are typing)
        cur = await create(d.asof);
        history.replaceState(null, "", hrefFor(cur.id)); lastRoute = location.hash;
        const b = el(`<button class="btn" id="anfinish" title="Freeze the evidence with your answers, so you can compare later">Finish</button>`);
        b.onclick = finish; $view.querySelector("#anstart")?.replaceWith(b);
        const dt = $view.querySelector("#andate"); if (dt) dt.disabled = true;
      }
      const a = await api(`/api/analyses/${cur.id}`, jsonReq("PUT", { answers, verdict }));
      if ($saved) $saved.textContent = `saved ${new Date(a.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    } catch (err) { dirty = true; if ($saved) $saved.textContent = "not saved"; toast("Saving failed: " + err.message, "err"); }
  };
  const changed = () => { dirty = true; if ($saved) $saved.textContent = "saving…"; clearTimeout(timer); timer = setTimeout(saveNow, 800); calc(); };
  const put = (name, val) => {
    const [kind, key] = name.split(":");
    if (kind === "v") { verdict[key] = val; return; }
    const a = answers[key] = { ...(answers[key] || {}) };
    if (kind === "a") a.rating = val; else a.note = val;
  };
  $view.querySelectorAll(".an-seg").forEach((sg) => sg.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const on = !b.classList.contains("on");   // clicking the chosen one clears it
    sg.querySelectorAll("button").forEach((x) => x.classList.remove("on"));
    if (on) b.classList.add("on");
    const name = sg.dataset.name, raw = on ? b.dataset.v : null;
    put(name, name === "v:conviction" && raw != null ? +raw : raw);
    changed();
  }));
  $view.querySelectorAll("textarea[data-name], input[data-name]").forEach((t) => t.addEventListener("input", () => { put(t.dataset.name, t.value); changed(); }));
  $view.querySelectorAll(".an-use").forEach((b) => b.addEventListener("click", () => {
    const l = (ev.levels || [])[+b.dataset.i], key = l.kind;   // entry / stop / target
    const inp = $view.querySelector(`input[data-name="v:${key}"]`);
    const v = String(Math.round(l.price * 100) / 100);
    if (inp) inp.value = v;
    put(`v:${key}`, v); changed();
  }));
  const flush = () => { if (dirty) saveNow(); };
  window.addEventListener("beforeunload", flush);
  const prev = cleanup; cleanup = () => { flush(); window.removeEventListener("beforeunload", flush); prev(); };
}

/** Your plan replayed on the bars after the as-of session (arithmetic on your own numbers, not a strategy): an entry
 *  at or below the as-of close fills at once, one above it fills on the first bar that trades through it; then the
 *  first bar to reach the stop or the target decides. A bar that reaches both cannot be ordered from daily bars. */
function anReplay(path, close, entry, stop, target) {
  const r = entry - stop, R = (px) => `${((px - entry) / r) >= 0 ? "+" : "−"}${Math.abs((px - entry) / r).toFixed(1)}R`;
  let i = 0;
  if (entry > close) {
    while (i < path.length && path[i][1] < entry) i++;
    if (i === path.length) return `Your entry at ${entry} has not traded in the ${path.length} sessions since.`;
  } else i = -1;   // filled on the as-of close
  const filled = i < 0 ? "at the as-of close" : `on ${prettyDate(path[i][0])}`;
  for (let j = i + 1; j < path.length; j++) {
    const [day, hi, lo] = path[j], hitS = lo <= stop, hitT = target && hi >= target;
    if (hitS && hitT) return `Filled ${filled}; on ${prettyDate(day)} the bar reached both the stop and the target — daily bars cannot say which came first.`;
    if (hitS) return `Filled ${filled}; stopped out on ${prettyDate(day)} (${R(stop)}), ${j - Math.max(i, 0)} sessions in.`;
    if (hitT) return `Filled ${filled}; target reached on ${prettyDate(day)} (${R(target)}), ${j - Math.max(i, 0)} sessions in.`;
  }
  const last = path[path.length - 1];
  return last ? `Filled ${filled}; neither stop nor target in the ${path.length} sessions since — last close ${last[3].toFixed(2)} (${R(last[3])}).` : "";
}

async function analysisFrameworkPage(alive, which) {
  const isEntry = which === "entry";
  document.title = `${isEntry ? "Entry" : "Analysis"} framework · Trading`;
  $view.innerHTML = LOADING;
  const all = await api("/api/analysis/framework");
  if (!alive()) return;
  const fw = isEntry ? all.entry : all;
  const lm = store.get("lastMarket", "us"), back = store.get("lastSymbol:" + lm, null);
  const intro = isEntry
    ? `<p>Is <b>now</b> a low-risk time to buy? Six pillars, worked down in the order a trader does — the market, the stock's sector and group,
        its trend, its setup, the entry point, and what could gap it. It is read <b>as of one session</b>: pick a past date and it reads only what was
        known then, then shows what the price did after. Each <b>check</b> is graded ${anTag("good")} ${anTag("ok")} or ${anTag("bad")}
        (${anTag("na")} where the data is missing), the <b>questions</b> are yours, and <b>reference levels</b> from the chart help you write the
        <b>plan</b> — entry, stop, target and size — which is always yours.</p>`
    : `<p>Is the business worth owning? Ten pillars, each asking one question about the company. The stored data answers what it can — each
        <b>check</b> is graded ${anTag("good")} ${anTag("ok")} or ${anTag("bad")} (${anTag("na")} where the data is missing or the rule does not
        apply) — and the <b>questions</b> are yours to answer. The <b>verdict</b> is always yours.</p>`;
  const closing = isEntry
    ? `<section class="co-sec"><h2>Plan</h2><ul class="sd-list">${fw.plan.map((v) => `<li><b>${esc(v.label)}</b> <span class="muted">${esc(v.hint)}</span></li>`).join("")}</ul></section>`
    : `<section class="co-sec"><h2>Verdict</h2><ul class="sd-list">${fw.verdict.map((v) => `<li><b>${esc(v.label)}</b> <span class="muted">${esc(v.hint)}</span></li>`).join("")}</ul></section>`;
  $view.innerHTML = `<div class="page-head"><h1>${isEntry ? "Entry" : "Company"} analysis framework</h1><span class="tag neutral">v${esc(fw.version)}</span>
      <span class="seg an-kind"><a class="${isEntry ? "" : "on"}" href="#/analysis/framework">Company</a><a class="${isEntry ? "on" : ""}" href="#/analysis/framework/entry">Entry</a></span>
      <span class="spacer"></span>
      <a href="#/analysis/all">All analyses</a>${back ? ` · <a href="${isEntry ? anEntryHref(lm, back) : analysisHref(lm, back)}">Analyse ${esc(bareSymbol(back))} →</a>` : ""}</div>
    <section class="co-sec">${intro}
      <p class="muted small">${esc(all.rating_rule)} Red flags — a bad reading on ${fw.red_flags.map(esc).join(", ")} — are listed on the summary whatever the pillar's rating.</p>
      <ul class="sd-list">${fw.caveats.map((c) => `<li class="muted small">${esc(c)}</li>`).join("")}</ul></section>
    <nav class="co-nav">${fw.pillars.map((p) => `<a href="#fw-${p.key}" data-sec="fw-${p.key}">${esc(p.name)}</a>`).join("")}</nav>
    ${fw.pillars.map((p) => `<section class="co-sec" id="fw-${p.key}"><h2>${esc(p.name)}</h2><p class="muted an-pq">${esc(p.question)}</p>
      <table class="dtab an-checks"><thead><tr><th>Check</th><th>Rule</th><th>Why it matters</th></tr></thead><tbody>
      ${p.checks.map((c) => `<tr><td><b>${esc(c.code)}</b> ${esc(c.label)}</td><td>${esc(c.rule)}</td><td class="muted">${esc(c.why)}</td></tr>`).join("")}</tbody></table>
      <h3 class="an-h3">Your questions</h3><ul class="sd-list">${p.questions.map((q) => `<li><b>${esc(q.code)}</b> ${esc(q.question)} <span class="muted small">${esc(q.hint)}</span></li>`).join("")}</ul></section>`).join("")}
    ${closing}
    <section class="co-sec"><h2>Changelog</h2><ul class="sd-list">${fw.changelog.map((c) => `<li><b>v${esc(c.version)}</b> <span class="muted">${esc(c.date)}</span> ${esc(c.text)}</li>`).join("")}</ul></section>`;
  $view.querySelector(".co-nav").onclick = anScrollTo;
}

async function analysesListPage(alive) {
  document.title = "Analyses · Trading";
  $view.innerHTML = LOADING;
  const rows = await api("/api/analyses");
  if (!alive()) return;
  const n = new Set(rows.map((r) => `${r.market}:${r.symbol}`)).size;
  const summaryOf = (r) => (r.kind === "entry"
    ? [r.verdict?.entry && `entry ${r.verdict.entry}`, r.verdict?.stop && `stop ${r.verdict.stop}`, r.verdict?.target && `target ${r.verdict.target}`, r.verdict?.note].filter(Boolean).join(" · ")
    : r.verdict?.thesis || "");
  $view.innerHTML = `<div class="page-head"><h1>Analyses</h1><span class="muted">${n} stock${n === 1 ? "" : "s"} — the latest company and entry analysis of each</span>
      <span class="spacer"></span><a href="#/analysis/framework">The frameworks</a></div>
    ${rows.length ? `<section class="co-sec"><table class="dtab an-list"><thead><tr><th>Stock</th><th>Kind</th><th>As of</th><th>Status</th><th>Decision</th><th>Conviction</th><th class="num">Score</th><th>Thesis / plan</th><th class="num">Analyses</th></tr></thead><tbody>
      ${rows.map((r) => `<tr data-href="${r.kind === "entry" ? anEntryHref(r.market, r.symbol, r.id) : analysisHref(r.market, r.symbol, r.id)}"><td><span class="mkt">${MKT_BADGE[r.market] || r.market}</span> <b>${esc(bareSymbol(r.symbol))}</b> <span class="muted small">${esc(r.name || "")}</span></td>
        <td>${r.kind === "entry" ? "Entry" : "Company"}</td><td>${esc(anDate(r.asof || r.updated_at))}</td><td>${r.status === "final" ? '<span class="tag neutral">finished</span>' : '<span class="tag warn">draft</span>'}</td>
        <td>${esc(r.verdict?.decision || "")}</td><td>${r.verdict?.conviction ? "★".repeat(r.verdict.conviction) : ""}</td><td class="num">${r.score ?? ""}</td>
        <td class="muted small">${esc(summaryOf(r).slice(0, 120))}</td><td class="num">${r.count}</td></tr>`).join("")}</tbody></table></section>`
      : `<div class="empty"><b>No analyses yet</b><div class="muted">Open a stock's Analysis tab (Chart › Analysis) and start one.</div></div>`}`;
  $view.querySelectorAll("tr[data-href]").forEach((tr) => tr.onclick = () => go(tr.dataset.href));
}
