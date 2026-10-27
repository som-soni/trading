"use strict";
/* Chart › Analysis: one stock read through the analysis framework (scripts/analysis).
 *
 *   #/analysis/<market>/<symbol>        the stock: today's evidence and its latest analysis (a draft autosaves)
 *   #/analysis/<market>/<symbol>/<id>   one saved analysis (a finished one shows the evidence it was made on)
 *   #/analysis/framework                the framework itself: pillars, checks with live thresholds, questions
 *   #/analysis/all                      every stock analysed, its latest analysis
 *
 * Every judgement is made by the server (scripts/analysis/framework.py); this page only formats it and
 * records your answers. Loaded before app.js; uses its helpers (api, esc, store, toast, …) at call time. */

const analysisHref = (m, s, id) => `#/analysis/${m}/${encodeURIComponent(s)}${id ? `/${id}` : ""}`;
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

async function analysisPage(alive, a1, a2, a3) {
  if (a1 === "framework") return analysisFrameworkPage(alive);
  if (a1 === "all") return analysesListPage(alive);
  const market = pageMarket(a1);
  const symbol = a2 || store.get("lastSymbol:" + market, market === "us" ? "AAPL" : "RELIANCE.NS");
  store.set("lastMarket", market); store.set("lastSymbol:" + market, symbol);
  document.title = `${bareSymbol(symbol)} analysis · Trading`;
  $view.innerHTML = LOADING;
  const [d, fw] = await Promise.all([api(`/api/analysis?market=${market}&symbol=${encodeURIComponent(symbol)}`), api("/api/analysis/framework")]);
  // the analysis open: the one in the URL, else the stock's latest; none = today's evidence, nothing recorded yet
  const openId = a3 ? +a3 : d.history[0]?.id;
  let cur = openId ? await api(`/api/analyses/${openId}`).catch(() => null) : null;
  if (!alive()) return;
  const final = cur?.status === "final";
  // a finished analysis shows the evidence it was made on (and marks what has changed since); a draft, today's
  const ev = final ? cur.evidence : d;
  const live = d.results, res = ev.results || {}, sm = ev.summary || {};
  const fmts = fw.formats, ratingOf = (k) => sm.pillars?.[k] || {};
  const answers = cur ? structuredClone(cur.answers || {}) : {}, verdict = cur ? structuredClone(cur.verdict || {}) : {};

  const hist = d.history.length ? `<select id="anhist" title="Analyses of this stock, newest first">${d.history.map((h) => `<option value="${h.id}" ${h.id === cur?.id ? "selected" : ""}>
      ${esc(anDate(h.created_at))} · ${h.status === "final" ? esc(h.verdict?.decision || "finished") : "draft"}${h.verdict?.conviction ? ` · ${"★".repeat(h.verdict.conviction)}` : ""}</option>`).join("")}</select>` : "";
  const actions = !cur ? `<span class="muted small" id="ansaved"></span><button class="btn" id="anstart" title="Record your answers and verdict for this stock (answering any question starts one too)">Start analysis</button>`
    : final ? `<button class="btn" id="anrevise" title="A new draft with today's evidence, starting from this analysis's answers">Revise</button>`
    : `<span class="muted small" id="ansaved">${cur.updated_at ? `saved ${esc(anDate(cur.updated_at))}` : ""}</span>
       <button class="btn" id="anfinish" title="Freeze today's evidence with your answers, so you can compare later">Finish</button>`;
  const head = `<div class="page-head co-head"><h1>${esc(d.name || bareSymbol(symbol))}</h1><span class="mkt">${MKT_BADGE[market] || market}</span><span class="muted">${esc(bareSymbol(symbol))}</span>
      <span class="spacer"></span>
      <form class="wl-add" autocomplete="off" id="ansearch"><div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="5.5"/><path d="M13 13l4 4"/></svg><input placeholder="Analyse a stock" spellcheck="false"><ul hidden></ul></div></form>
      ${hist}${actions}${cur ? `<button class="ghost icon" id="andel" title="Delete this analysis" aria-label="Delete">×</button>` : ""}</div>
    <div class="muted small co-sub">${final ? `Finished ${esc(anDate(cur.finished_at))} — evidence as of ${esc(anDate(ev.asof))}, framework v${esc(cur.framework_version)}${cur.framework_version !== fw.version ? ` (now v${esc(fw.version)})` : ""}. Checks that read differently today are marked.`
      : `Evidence as of ${esc(anDate(ev.asof))} · framework v${esc(fw.version)} · your answers save as you type${cur ? "" : " (the first one starts an analysis)"}`}
      · <a href="#/analysis/framework">how the framework works</a> · <a href="#/analysis/all">all analyses</a></div>`;

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
  const vsum = verdict.decision ? `<div class="an-vsum"><span class="tag ${["Buy", "Accumulate"].includes(verdict.decision) ? "pos" : ["Sell", "Avoid", "Trim"].includes(verdict.decision) ? "neg" : "warn"}">${esc(verdict.decision)}</span>
      ${verdict.conviction ? `<span title="Conviction">${"★".repeat(verdict.conviction)}<span class="muted">${"★".repeat(5 - verdict.conviction)}</span></span>` : ""}
      ${verdict.thesis ? `<span class="muted">${esc(verdict.thesis.slice(0, 220))}${verdict.thesis.length > 220 ? "…" : ""}</span>` : ""}</div>` : "";
  const summary = `<section class="co-sec an-summary"><div class="an-score"><b>${sm.score ?? "—"}</b><span class="muted small">evidence score<br>${sm.rated || 0} rated pillars</span></div>
      <div class="an-chips">${chips}</div>${flags}${vsum}</section>`;

  const editable = !final;               // no analysis yet: the first answer starts one
  const dis = editable ? "" : "disabled";
  const checkRow = (c) => { const r = res[c.code] || { status: "na" }, now = live[c.code];
    const changed = final && now && now.status !== r.status;
    return `<tr><td>${anTag(r.status)}${changed ? `<div class="an-now" title="Today: ${esc(now.detail || "")}">now ${anTag(now.status)}</div>` : ""}</td>
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
  const vf = Object.fromEntries(fw.verdict.map((v) => [v.key, v]));
  const verdictHtml = `<section class="co-sec" id="an-verdict"><h2>Verdict <span class="muted small">yours — the framework never decides</span></h2>
      <div class="an-vgrid">
        <label>${esc(vf.decision.label)}</label><div>${seg("v:decision", fw.decisions, verdict.decision)}</div>
        <label>${esc(vf.conviction.label)}</label><div>${seg("v:conviction", [1, 2, 3, 4, 5], verdict.conviction)} <span class="muted small">${esc(vf.conviction.hint)}</span></div>
        ${["thesis", "invalidation"].map((k) => `<label>${esc(vf[k].label)}</label><textarea data-name="v:${k}" rows="3" placeholder="${esc(vf[k].hint)}" ${dis}>${esc(verdict[k] || "")}</textarea>`).join("")}
        <label>${esc(vf.review_on.label)}</label><input data-name="v:review_on" value="${esc(verdict.review_on || "")}" placeholder="${esc(vf.review_on.hint)}" ${dis}>
      </div></section>`;
  const nav = `<nav class="co-nav">${fw.pillars.map((p) => `<a href="#an-${p.key}" data-sec="an-${p.key}">${esc(p.name)}</a>`).join("")}<a href="#an-verdict" data-sec="an-verdict">Verdict</a></nav>`;
  $view.innerHTML = head + summary + nav + pillars + verdictHtml;

  // ---- wiring
  $view.querySelectorAll(".an-summary, .co-nav").forEach((x) => (x.onclick = anScrollTo));
  const f = $view.querySelector("#ansearch");
  symbolSearch(f.querySelector("input"), f.querySelector("ul"), market, (s, m) => go(analysisHref(m || market, s)));
  f.onsubmit = (e) => { e.preventDefault(); const v = f.querySelector("input").value.trim().toUpperCase(); if (v) go(analysisHref(market, v)); };
  $view.querySelector("#anhist")?.addEventListener("change", (e) => go(analysisHref(market, symbol, e.target.value)));
  const create = () => api("/api/analyses", jsonReq("POST", { market, symbol }));
  $view.querySelector("#anstart")?.addEventListener("click", async (e) => {
    e.target.disabled = true;
    try { const a = await create(); go(analysisHref(market, symbol, a.id)); } catch (err) { e.target.disabled = false; toast(err.message, "err"); }
  });
  $view.querySelector("#anrevise")?.addEventListener("click", async (e) => {
    e.target.disabled = true;
    try { const a = await create(); toast("New draft — today's evidence, your last answers to revise", "ok"); go(analysisHref(market, symbol, a.id)); }
    catch (err) { e.target.disabled = false; toast(err.message, "err"); }
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
    if (!confirm(`Delete the ${cur.status === "final" ? "finished" : "draft"} analysis of ${bareSymbol(symbol)} from ${anDate(cur.created_at)}?`)) return;
    await api(`/api/analyses/${cur.id}`, { method: "DELETE" });
    toast("Analysis deleted", "ok"); go(analysisHref(market, symbol));
  });
  if (!editable) return;

  // autosave: answers and verdict, a moment after the last change
  let timer = null, dirty = false;
  const $saved = $view.querySelector("#ansaved");
  const saveNow = async () => {
    clearTimeout(timer);
    if (!dirty) return;
    dirty = false;
    try {
      if (!cur) {   // the first answer: a draft with today's evidence; the URL names it (no re-render: you are typing)
        cur = await create();
        history.replaceState(null, "", analysisHref(market, symbol, cur.id)); lastRoute = location.hash;
        const b = el(`<button class="btn" id="anfinish" title="Freeze today's evidence with your answers, so you can compare later">Finish</button>`);
        b.onclick = finish; $view.querySelector("#anstart")?.replaceWith(b);
      }
      const a = await api(`/api/analyses/${cur.id}`, jsonReq("PUT", { answers, verdict }));
      if ($saved) $saved.textContent = `saved ${new Date(a.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    } catch (err) { dirty = true; if ($saved) $saved.textContent = "not saved"; toast("Saving failed: " + err.message, "err"); }
  };
  const changed = () => { dirty = true; if ($saved) $saved.textContent = "saving…"; clearTimeout(timer); timer = setTimeout(saveNow, 800); };
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
  const flush = () => { if (dirty) saveNow(); };
  window.addEventListener("beforeunload", flush);
  const prev = cleanup; cleanup = () => { flush(); window.removeEventListener("beforeunload", flush); prev(); };
}

async function analysisFrameworkPage(alive) {
  document.title = "Analysis framework · Trading";
  $view.innerHTML = LOADING;
  const fw = await api("/api/analysis/framework");
  if (!alive()) return;
  const back = store.get("lastSymbol:" + store.get("lastMarket", "us"), null);
  $view.innerHTML = `<div class="page-head"><h1>Stock analysis framework</h1><span class="tag neutral">v${esc(fw.version)}</span><span class="spacer"></span>
      <a href="#/analysis/all">All analyses</a>${back ? ` · <a href="${analysisHref(store.get("lastMarket", "us"), back)}">Analyse ${esc(bareSymbol(back))} →</a>` : ""}</div>
    <section class="co-sec"><p>Ten pillars, each asking one question about the company. The stored data answers what it can — each <b>check</b> is graded
      ${anTag("good")} ${anTag("ok")} or ${anTag("bad")} (${anTag("na")} where the data is missing or the rule does not apply) — and the
      <b>questions</b> are yours to answer. The <b>verdict</b> is always yours.</p>
      <p class="muted small">${esc(fw.rating_rule)} Red flags — a bad reading on ${fw.red_flags.map(esc).join(", ")} — are listed on the summary whatever the pillar's rating.</p>
      <ul class="sd-list">${fw.caveats.map((c) => `<li class="muted small">${esc(c)}</li>`).join("")}</ul></section>
    <nav class="co-nav">${fw.pillars.map((p) => `<a href="#fw-${p.key}" data-sec="fw-${p.key}">${esc(p.name)}</a>`).join("")}</nav>
    ${fw.pillars.map((p) => `<section class="co-sec" id="fw-${p.key}"><h2>${esc(p.name)}</h2><p class="muted an-pq">${esc(p.question)}</p>
      <table class="dtab an-checks"><thead><tr><th>Check</th><th>Rule</th><th>Why it matters</th></tr></thead><tbody>
      ${p.checks.map((c) => `<tr><td><b>${esc(c.code)}</b> ${esc(c.label)}</td><td>${esc(c.rule)}</td><td class="muted">${esc(c.why)}</td></tr>`).join("")}</tbody></table>
      <h3 class="an-h3">Your questions</h3><ul class="sd-list">${p.questions.map((q) => `<li><b>${esc(q.code)}</b> ${esc(q.question)} <span class="muted small">${esc(q.hint)}</span></li>`).join("")}</ul></section>`).join("")}
    <section class="co-sec"><h2>Verdict</h2><ul class="sd-list">${fw.verdict.map((v) => `<li><b>${esc(v.label)}</b> <span class="muted">${esc(v.hint)}</span></li>`).join("")}</ul></section>
    <section class="co-sec"><h2>Changelog</h2><ul class="sd-list">${fw.changelog.map((c) => `<li><b>v${esc(c.version)}</b> <span class="muted">${esc(c.date)}</span> ${esc(c.text)}</li>`).join("")}</ul></section>`;
  $view.querySelector(".co-nav").onclick = anScrollTo;
}

async function analysesListPage(alive) {
  document.title = "Analyses · Trading";
  $view.innerHTML = LOADING;
  const rows = await api("/api/analyses");
  if (!alive()) return;
  $view.innerHTML = `<div class="page-head"><h1>Analyses</h1><span class="muted">${rows.length} stock${rows.length === 1 ? "" : "s"}, latest analysis of each</span>
      <span class="spacer"></span><a href="#/analysis/framework">The framework</a></div>
    ${rows.length ? `<section class="co-sec"><table class="dtab an-list"><thead><tr><th>Stock</th><th>Updated</th><th>Status</th><th>Decision</th><th>Conviction</th><th class="num">Evidence</th><th>Thesis</th><th class="num">Analyses</th></tr></thead><tbody>
      ${rows.map((r) => `<tr data-href="${analysisHref(r.market, r.symbol, r.id)}"><td><span class="mkt">${MKT_BADGE[r.market] || r.market}</span> <b>${esc(bareSymbol(r.symbol))}</b> <span class="muted small">${esc(r.name || "")}</span></td>
        <td>${esc(anDate(r.updated_at))}</td><td>${r.status === "final" ? '<span class="tag neutral">finished</span>' : '<span class="tag warn">draft</span>'}</td>
        <td>${esc(r.verdict?.decision || "")}</td><td>${r.verdict?.conviction ? "★".repeat(r.verdict.conviction) : ""}</td><td class="num">${r.score ?? ""}</td>
        <td class="muted small">${esc((r.verdict?.thesis || "").slice(0, 120))}</td><td class="num">${r.count}</td></tr>`).join("")}</tbody></table></section>`
      : `<div class="empty"><b>No analyses yet</b><div class="muted">Open a stock's Analysis tab (Chart › Analysis) and start one.</div></div>`}`;
  $view.querySelectorAll("tr[data-href]").forEach((tr) => tr.onclick = () => go(tr.dataset.href));
}
