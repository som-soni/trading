"use strict";
/* Technical indicators ("studies"), TradingView-style.
 *
 * Everything is computed in the browser from the OHLCV the chart already has,
 * so any indicator works on daily / weekly / monthly bars and its settings can
 * change without a server round-trip. Formulas follow TradingView's built-ins
 * (Wilder smoothing for RSI / ATR / ADX, population stdev for Bollinger, ...).
 *
 * A study instance is {id, type, params, colors, hidden}; the active list is
 * kept in localStorage and shared by every symbol, like a TradingView layout.
 */
const Studies = (() => {
  const LC = LightweightCharts;
  const store = {
    get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  };
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  /** a custom study whose result arrives later (a server request) rewrites its legend note in place */
  const setNote = (id, text) => document.querySelectorAll(`.srow[data-id="${id}"] .snote`).forEach((el) => { el.textContent = text; el.title = text; });

  // ------------------------------------------------------------- math
  const nul = (n) => new Array(n).fill(null);
  function sma(a, n) {
    const o = nul(a.length); let s = 0, bad = 0;
    for (let i = 0; i < a.length; i++) {
      if (a[i] == null) bad++; else s += a[i];
      if (i >= n) { if (a[i - n] == null) bad--; else s -= a[i - n]; }
      if (i >= n - 1 && bad === 0) o[i] = s / n;
    }
    return o;
  }
  /** recursive average seeded with the SMA of the first n values (EMA: k=2/(n+1), RMA: k=1/n) */
  function smooth(a, n, k) {
    const o = nul(a.length); let prev = null, seed = [], i0 = a.findIndex((v) => v != null);
    if (i0 < 0) return o;
    for (let i = i0; i < a.length; i++) {
      const v = a[i]; if (v == null) { prev = null; seed = []; continue; }
      if (prev == null) { seed.push(v); if (seed.length === n) { prev = seed.reduce((x, y) => x + y, 0) / n; o[i] = prev; } continue; }
      prev = prev + k * (v - prev); o[i] = prev;
    }
    return o;
  }
  const ema = (a, n) => smooth(a, n, 2 / (n + 1));
  const rma = (a, n) => smooth(a, n, 1 / n);
  function wma(a, n) {
    const o = nul(a.length), d = (n * (n + 1)) / 2;
    for (let i = n - 1; i < a.length; i++) {
      let s = 0, ok = true;
      for (let j = 0; j < n; j++) { const v = a[i - j]; if (v == null) { ok = false; break; } s += v * (n - j); }
      if (ok) o[i] = s / d;
    }
    return o;
  }
  function win(a, n, f) {
    const o = nul(a.length);
    for (let i = n - 1; i < a.length; i++) {
      const w = a.slice(i - n + 1, i + 1);
      if (w.every((v) => v != null)) o[i] = f(w);
    }
    return o;
  }
  const highest = (a, n) => win(a, n, (w) => Math.max(...w));
  const lowest = (a, n) => win(a, n, (w) => Math.min(...w));
  const stdev = (a, n) => win(a, n, (w) => { const m = w.reduce((x, y) => x + y, 0) / n; return Math.sqrt(w.reduce((x, y) => x + (y - m) ** 2, 0) / n); });
  const sum = (a, n) => win(a, n, (w) => w.reduce((x, y) => x + y, 0));
  const zip = (f, ...arrs) => arrs[0].map((_, i) => (arrs.some((a) => a[i] == null) ? null : f(...arrs.map((a) => a[i]), i)));
  function trueRange(H, L, C) { return H.map((h, i) => (i === 0 ? h - L[i] : Math.max(h - L[i], Math.abs(h - C[i - 1]), Math.abs(L[i] - C[i - 1])))); }
  function rsi(src, n) {
    const ch = src.map((v, i) => (i === 0 || v == null || src[i - 1] == null ? null : v - src[i - 1]));
    const up = rma(ch.map((c) => (c == null ? null : Math.max(c, 0))), n), dn = rma(ch.map((c) => (c == null ? null : Math.max(-c, 0))), n);
    return zip((u, d) => (d === 0 ? 100 : u === 0 ? 0 : 100 - 100 / (1 + u / d)), up, dn);
  }
  const source = (b, s) => ({ open: b.O, high: b.H, low: b.L, close: b.C,
    hl2: zip((h, l) => (h + l) / 2, b.H, b.L), hlc3: zip((h, l, c) => (h + l + c) / 3, b.H, b.L, b.C),
    ohlc4: zip((o, h, l, c) => (o + h + l + c) / 4, b.O, b.H, b.L, b.C) }[s] || b.C);
  const hasVolume = (b) => b.V.some((v) => v > 0);
  /** % change over n bars */
  const roc = (a, n) => a.map((v, i) => (i < n || v == null || !a[i - n] ? null : (100 * (v - a[i - n])) / a[i - n]));
  /** Pring's KST family: the sum of weighted simple averages of rates of change, terms [[roc, sma, weight], ...] */
  const rocSum = (a, terms) => terms.map(([r, s, w]) => sma(roc(a, r), s).map((v) => (v == null ? null : v * w)))
    .reduce((acc, x) => zip((u, v) => u + v, acc, x));
  /** least-squares line through the last n values, read at the latest bar (TradingView's ta.linreg(src, n, 0)) */
  const linreg = (a, n) => win(a, n, (w) => {
    const mx = (n - 1) / 2, my = w.reduce((x, y) => x + y, 0) / n; let num = 0, den = 0;
    w.forEach((y, x) => { num += (x - mx) * (y - my); den += (x - mx) ** 2; });
    return my + (num / den) * (n - 1 - mx);
  });
  /** Accumulation/Distribution line: volume weighted by where the close sits in the bar's range, summed */
  const adLine = (b) => { let s = 0; return b.C.map((c, i) => (s += b.H[i] === b.L[i] ? 0 : (((c - b.L[i]) - (b.H[i] - c)) / (b.H[i] - b.L[i])) * (b.V[i] || 0))); };

  /** Swing pivots, standard (fractal) definition — TradingView's ta.pivothigh/pivotlow: a bar is a
   *  pivot high when its high is above the `left` bars before it and not exceeded by the `right`
   *  bars after it (ties go to the earlier bar); pivot lows mirror that. A pivot can only be
   *  confirmed `right` bars later, so the last `right` bars never show one — no look-ahead. */
  function swingPivots(H, L, left, right, from = 0) {
    const out = [], n = H.length;
    for (let i = Math.max(left, from); i < n - right; i++) {
      let hi = true, lo = true;
      for (let j = i - left; j <= i + right && (hi || lo); j++) {
        if (j === i) continue;
        if (j < i ? H[j] >= H[i] : H[j] > H[i]) hi = false;
        if (j < i ? L[j] <= L[i] : L[j] < L[i]) lo = false;
      }
      if (hi) out.push({ i, type: "H", price: H[i] });
      if (lo) out.push({ i, type: "L", price: L[i] });
    }
    return out;
  }
  /** calendar period of a "YYYY-MM-DD" bar for pivot points: W (ISO week), M, Q, Y */
  function periodKey(day, unit) {
    const [y, m] = day.split("-").map(Number);
    if (unit === "Y") return String(y);
    if (unit === "Q") return `${y}-Q${Math.floor((m - 1) / 3)}`;
    if (unit === "M") return day.slice(0, 7);
    const d = new Date(day + "T00:00:00Z"), dow = (d.getUTCDay() + 6) % 7;  // Monday = 0
    d.setUTCDate(d.getUTCDate() - dow);
    return d.toISOString().slice(0, 10);  // the week's Monday
  }
  const fmtPx = (v) => (Math.abs(v) >= 1000 ? v.toFixed(0) : Math.abs(v) >= 1 ? v.toFixed(2) : v.toPrecision(3));

  // ------------------------------------------------------------- catalogue
  // plot: {k: key, t: title, c: default colour, s: "line" | "hist" | "dots" | "area", w: width}
  const SRC = { type: "select", def: "close", options: ["close", "open", "high", "low", "hl2", "hlc3", "ohlc4"] };
  // strategy key -> display name, filled from /api/strategies: a setups layer is named for its
  // strategy, so adding one never means writing its name here
  const STRATEGY_NAMES = {};
  const stratName = (k) => STRATEGY_NAMES[k] || k;
  const MA_TYPES = ["SMA", "EMA", "WMA", "RMA"];
  const maOf = (type) => ({ SMA: sma, EMA: ema, WMA: wma, RMA: rma }[type] || sma);
  /** TradingView's Moving Average Ribbon: four MAs of one type, coloured yellow -> red */
  const ribbon = (name, short, type) => ({
    name, short, cat: "Moving averages", overlay: true,
    params: { type: { type: "select", def: type, options: MA_TYPES }, source: SRC, length1: 20, length2: 50, length3: 100, length4: 200 },
    plots: [{ k: "m1", t: "MA #1", c: "#f6c309" }, { k: "m2", t: "MA #2", c: "#fb9800" }, { k: "m3", t: "MA #3", c: "#fb6500" }, { k: "m4", t: "MA #4", c: "#f60c0c" }],
    calc: (b, p) => { const f = maOf(p.type), s = source(b, p.source);
      return { m1: f(s, p.length1), m2: f(s, p.length2), m3: f(s, p.length3), m4: f(s, p.length4) }; },
  });
  // strategy keys for the "Screener levels" indicator, set by the app once it knows them
  const STRATEGY_CHOICES = ["All"];
  const SHORT = { trend_pullback: "TP", chart_pattern: "CP", chart_pattern_cup: "CUP", breakout: "BO", donchian: "DC", minervini: "MV" };
  /** The Trade setups machinery every strategy's layer shares: one frame per setup with numbered zones,
   *  the lane of pills to pick one, the card with each zone's writeup and checklist, and a selected
   *  backtest run's own trade standing in for the illustrated entry. It knows nothing of any strategy:
   *  `load()` resolves to { setups (the bases_live / live_setups schema), background (shapes drawn
   *  behind, e.g. Stage 2), note }, `keyRows` is the colour key, `roles` adds role colours. */
  /** Bring the bars from `d0` to `d1` into view for something picked from a side-panel list: the stretch
   *  fills `fill` of the plot width, starting `lead` of the way in, and the price axis returns to
   *  auto-scale — after a manual vertical drag the picked thing could otherwise sit off-screen. */
  // `price` ({top, bottom}, a setup's frame): the price axis also takes that in -- its target and stop are
  // drawn as lines, which the candles' autoscale cannot see
  const frameDates = (chart, times, ctx, d0, d1, { fill = 0.6, lead = 0.06, min = 40, price = null } = {}) => {
    const idx = (d) => { const i = times.findIndex((t) => t >= d); return i < 0 ? times.length - 1 : i; };
    const a = idx(d0), b = Math.max(a, idx(d1));
    const span = Math.max(min, (b - a + 1) / fill), from = a - span * lead;
    chart.timeScale().setVisibleLogicalRange({ from, to: from + span });
    ctx.fitPrice?.(price);
  };

  /** How many years a Trade setups layer scans: its own setting, stretched back to the start of the
   *  selected backtest run (ctx.runStart) so every trade that run made here has its setup to sit on.
   *  0 = all history. */
  const scanYears = (years, ctx) => {
    if (!years || !ctx.runStart) return years;
    const back = Math.ceil((Date.now() - Date.parse(ctx.runStart)) / (365.25 * 864e5));
    return Math.max(years, back || 0);
  };

  function setupLayer({ chart, times, p, col, ctx, id, keyRows, roles: extraRoles = {}, load }) {
        let on = true, stage = [], setups = [], all = [], focus = null, hovered = null, pinned = null;
        const DIM = "#5d6170", YOUNG = "#9ca3af", NUM = ["①", "②", "③", "④"];
        // a setup's colour: a VCP, a cheat entry on a base that is not (yet) a VCP, or a failed base
        // (a listing too new for the template is neither: neutral grey, so it never reads as a failure)
        // (the generic layer's kinds — pass / watch / fail — share the same three colours)
        const kindKey = (s) => ({ vcp: "vcp", pass: "vcp", cheat: "cheat", watch: "cheat", young: "young" })[s.kind] || "miss";
        const kindCol = (s) => (s.kind === "young" ? YOUNG : col(kindKey(s)));
        const store = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch {} return null; };
        let open = store("ttCardOpen") !== "0", keyOpen = store("ttKeyOpen") === "1", zoneOpen = store("ttZone") || "";   // zones start closed: a compact card
        const esc = (x) => String(x ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
        const ICON = { pass: "✓", fail: "✗", skip: "·", warn: "!", young: "?" };
        // the selected run's trade on a setup, if it traded one: its record replaces the illustrated entry
        // Each trade belongs to ONE setup: of the setups whose window holds its entry, the one the rules
        // passed, else the latest to start — so an overlapping refused setup never claims it too.
        let owners = new Map(), ownersOf = null;
        const ownerMap = () => {
          const ts = ctx.trades?.() || [];
          if (ownersOf === ts && owners.size) return owners;
          owners = new Map(); ownersOf = ts;
          for (const t of ts) {
            const cover = all.filter((s) => t.entry_date >= s.base_from && t.entry_date <= s.to);
            // the setup judged on the bar the run traded (anchored by the selected run) wins over any other
            // that happens to span the fill
            const best = cover.find((s) => s.anchored) || cover.filter((s) => s.kind !== "fail").at(-1) || cover.at(-1);
            if (best && !owners.has(best)) owners.set(best, t);
          }
          return owners;
        };
        const tradeOf = (s) => ownerMap().get(s) || null;
        const isEntry = (z) => z.key === "entry" || z.key === "cheat";

        // ---- the card: the focused setup's verdict, one row per zone, the open zone's writeup and checks
        const card = document.createElement("div"); card.className = "tt-card"; card.hidden = true;
        ctx.chartEl?.append(card);
        // Where the card goes: wherever the viewer dragged it (remembered), else the side of the setup with
        // more room, so it covers as little of the setup as it can.
        let moved = null; try { moved = JSON.parse(store("ttCardPos") || "null"); } catch {}
        const place = (s) => {
          const el = ctx.chartEl, W = el.clientWidth, H = el.clientHeight;
          if (moved) {
            card.style.right = ""; card.style.left = `${Math.max(0, Math.min(W - card.offsetWidth, moved.x * W))}px`;
            card.style.top = `${Math.max(0, Math.min(H - card.offsetHeight, moved.y * H))}px`; return;
          }
          const ts = chart.timeScale(), w = ts.width();
          const px = (d) => ts.timeToCoordinate(times.find((t) => t >= d) || times.at(-1));
          const x0 = s ? px(s.from) ?? 0 : 0, x1 = s ? px(s.to) ?? w : w;
          // away from the entry zone when there is one (it is what matters most); else the roomier side
          // beside the setup when there is room for the card on either side (the roomier one), so it
          // covers none of it; otherwise away from the entry zone, which is what matters most
          const ez = s && s.zones.find(isEntry), ex = ez ? px(ez.from) : null;
          const cw = (card.offsetWidth || 300) + 16, roomL = Math.max(0, x0), roomR = w - Math.min(w, x1);
          const left = roomL >= cw || roomR >= cw ? roomL > roomR : ex != null ? ex > w / 2 : x0 > w - x1;
          card.style.right = left ? "" : `${chart.priceScale("right").width() + 8}px`;
          card.style.left = left ? `${(chart.priceScale("left").width() || 0) + 8}px` : "";
          card.style.top = left ? `${(el.querySelector(".legend")?.offsetHeight || 0) + 12}px` : "8px";
        };
        let drag = null;
        card.addEventListener("mousedown", (e) => {
          e.stopPropagation();   // not a chart drag or a drawing click
          if (!e.target.closest(".tt-h") || e.target.closest("button")) return;
          const r = card.getBoundingClientRect();
          drag = { dx: e.clientX - r.left, dy: e.clientY - r.top, x: e.clientX, y: e.clientY, moved: false };
        });
        const onMove = (e) => {
          if (!drag) return;
          if (!drag.moved && Math.hypot(e.clientX - drag.x, e.clientY - drag.y) < 4) return;
          drag.moved = true;
          const host = ctx.chartEl.getBoundingClientRect();
          moved = { x: (e.clientX - drag.dx - host.left) / host.width, y: (e.clientY - drag.dy - host.top) / host.height };
          place(focus);
        };
        const onUp = () => {
          if (!drag) return;
          if (drag.moved) { store("ttCardPos", JSON.stringify(moved)); card.dataset.dragged = "1"; }
          drag = null;
        };
        window.addEventListener("mousemove", onMove); window.addEventListener("mouseup", onUp);
        new MutationObserver(() => { if (!card.isConnected) { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); } })
          .observe(ctx.chartEl, { childList: true });
        card.onclick = (e) => {
          const z = e.target.closest("[data-z]"), act = e.target.closest("[data-a]");
          if (card.dataset.dragged) { delete card.dataset.dragged; return; }   // the end of a drag, not a click
          if (act?.dataset.a === "prev" || act?.dataset.a === "next") {
            const k = setups.indexOf(focus) + (act.dataset.a === "next" ? 1 : -1);
            if (setups[k]) { pinned = setups[k]; reveal(pinned); paint(); }
            return;
          }
          if (act?.dataset.a === "dock") { moved = null; store("ttCardPos", "null"); place(focus); return; }
          if (z) { zoneOpen = zoneOpen === z.dataset.z ? "" : z.dataset.z; store("ttZone", zoneOpen); renderCard(); return; }
          if (e.target.closest(".tt-kh")) { keyOpen = !keyOpen; store("ttKeyOpen", keyOpen ? "1" : "0"); renderCard(); return; }
          if (e.target.closest(".tt-h")) { open = !open; store("ttCardOpen", open ? "1" : "0"); renderCard(); }
        };
        const key = () => keyRows(YOUNG, DIM).map(([kind, c, name, what]) => `<div class="tt-k"><i class="mk ${kind}" style="--c:${c}"></i><span><b>${name}</b> — ${what}</span></div>`).join("");
        const checksHtml = (cs) => `<table class="tt-checks">${cs.map((c) => `<tr class="${c.state}" title="${esc(c.code)}">
          <td class="ic">${ICON[c.state]}</td><td>${esc(c.name)}</td><td class="val">${c.state === "skip" ? "not reached" : esc(c.value)}</td></tr>
          ${c.state === "fail" ? `<tr class="lim"><td></td><td colspan="2">needs ${esc(c.limit)}</td></tr>` : ""}`).join("")}</table>`;
        const zoneHtml = (s, z, n) => {
          const t = isEntry(z) ? tradeOf(s) : null;
          const line = t ? `traded: ${t.r_multiple != null ? `${(+t.r_multiple).toFixed(1)}R` : "open"}` : z.line;
          const state = t ? "pass" : z.warn && z.state === "pass" ? "warn" : z.state;
          let body = "";
          if (zoneOpen === z.key) {
            body = t
              ? `<p class="tt-x">The selected backtest run traded this setup: bought at ${esc((+t.entry_price).toFixed(2))} on ${esc(t.entry_date)}`
                + (t.exit_date ? `, sold at ${esc((+t.exit_price).toFixed(2))} on ${esc(t.exit_date)} (${esc(t.exit_reason || "exit")})` : ", still open")
                + `${t.r_multiple != null ? `, ${(+t.r_multiple).toFixed(2)}R` : ""}. Its own levels are drawn from the run's record.</p>`
              : `${z.illustration ? `<div class="tt-tag">Illustration of the rules — not a trade</div>` : ""}<p class="tt-x">${esc(z.text)}</p>${checksHtml(z.checks)}`;
          }
          return `<div class="tt-z ${zoneOpen === z.key ? "on" : ""}"><div class="tt-zh" data-z="${z.key}"><span class="n">${NUM[n]}</span>
            <b>${esc(z.title)}</b><span class="st ${state}">${ICON[state]}</span><span class="ln">${esc(line)}</span></div>${body}</div>`;
        };
        const renderCard = () => {
          card.hidden = !on || p.card === "Hide" || !setups.length;
          if (card.hidden) return;
          const s = focus;
          place(s);
          const keyHtml = `<div class="tt-kh">${keyOpen ? "▾" : "▸"} How to read the chart</div>${keyOpen ? `<div class="tt-key">${key()}</div>` : ""}`;
          if (!s) { card.innerHTML = `<div class="tt-h"><b>No setup in view</b><i>${open ? "▾" : "▸"}</i></div>${open ? keyHtml : ""}`; return; }
          const cls = s.kind === "fail" ? "no" : "ok", k = setups.indexOf(s);
          const tr = tradeOf(s);
          card.innerHTML = `<div class="tt-h"><span class="tt-title ${cls}" style="--c:${kindCol(s)}">${esc(s.title)}</span>
              ${tr ? `<span class="tt-traded" title="The selected backtest run bought this setup — these are its own levels, not an illustration">● traded${tr.r_multiple != null ? ` ${(+tr.r_multiple).toFixed(1)}R` : ""}</span>` : ""}
              <span class="tt-nav"><button data-a="prev" title="Previous setup" ${k <= 0 ? "disabled" : ""}>‹</button><span>${k + 1} of ${setups.length}</span><button data-a="next" title="Next setup" ${k >= setups.length - 1 ? "disabled" : ""}>›</button></span>
              <i>${open ? "▾" : "▸"}</i></div>`
            + (open ? `<div class="tt-date">${esc(s.from)} → ${esc(s.to)}${s.live ? ` <span class="tt-live">forming · judged today</span>` : ""}</div><div class="tt-sum">${esc(s.summary)}</div>${s.zones.map((z, n) => zoneHtml(s, z, n)).join("")}
              <div class="tt-sub">Pick a setup from the lane at the bottom of the chart, or step with ‹ ›. Drag this header to move the card${moved ? ` · <a data-a="dock">put it back</a>` : ""}.</div>${keyHtml}` : "");
        };

        // ---- which setup: pinned, else under the mouse, else the latest one in view
        const edge = () => {
          const r = chart.timeScale().getVisibleLogicalRange();
          return r ? times[Math.min(times.length - 1, Math.max(0, Math.floor(r.to)))] : times.at(-1);
        };
        // with a backtest run selected, the setup it traded is the one the card opens on
        const latest = () => {
          const shown = [...setups].reverse().filter((s) => s.from <= edge());
          const r = chart.timeScale().getVisibleLogicalRange(), lo = r ? times[Math.max(0, Math.floor(r.from))] : times[0];
          return shown.find((s) => s.to >= lo && tradeOf(s)) || shown[0] || null;
        };
        const setupAt = (t) => setups.filter((s) => s.from <= t && t <= s.to)
          .sort((a, b) => (Date.parse(a.to) - Date.parse(a.from)) - (Date.parse(b.to) - Date.parse(b.from)))[0] || null;
        const timeOf = (q) => (typeof q.time === "string" ? q.time
          : q.point && q.logical != null ? times[Math.min(times.length - 1, Math.max(0, Math.round(q.logical)))] : null);

        const paint = () => {
          focus = hovered || pinned || latest();
          const shapes = [];
          // Only the selected setup is drawn: overlapping frames cannot be told apart, so every other
          // setup lives in the lane instead, where each has its own row and its own click target.
          for (const s of setups) {
            const f = s.frame;
            if (s !== focus) continue;
            const role = kindKey(s);
            const traded = tradeOf(s);
            // a traded setup says so on the frame itself: with the layer and a run both on, the one
            // thing you cannot read off the drawing is which of these the run actually bought
            shapes.push({ shape: "box", frame: true, dash: s.kind === "fail" || s.kind === "young", role, from: f.from, to: f.to, top: f.top, bottom: f.bottom,
              label: traded ? `${s.title} · ● traded${traded.r_multiple != null ? ` ${(+traded.r_multiple).toFixed(1)}R` : ""}` : s.title });
            s.zones.forEach((z, n) => {
              if (n > 0)   // a faint divider where each zone starts
                shapes.push({ shape: "line", from: z.from, to: z.from, p0: f.top, p1: f.bottom, role: "dim", dash: true });
              const st = traded && isEntry(z) ? "pass" : z.warn && z.state === "pass" ? "warn" : z.state;
              // captions just inside the frame's top edge: below it, the setup lane would cover them
              shapes.push({ shape: "text", at: z.from, price: f.top, role: st === "fail" ? "stop" : st === "warn" ? "flag" : "dim",
                label: `${NUM[n]} ${z.title} ${ICON[st]}` });
              if (isEntry(z) && traded) {
                // The run's own record, drawn HERE and in this indicator's vocabulary, so an
                // illustrated setup and a traded one look the same and differ only in where the
                // numbers came from. Its levels come straight from the record (never recomputed);
                // its base and shelf boxes and its note are dropped, because this frame and the
                // card already say both, and saying them twice is what made the chart look doubled.
                shapes.push({ shape: "level", role: "buy", from: traded.entry_date, to: traded.exit_date || f.to,
                  price: +traded.entry_price, label: `bought ${(+traded.entry_price).toFixed(2)}` });
                // the record's own stop and target only: every strategy's traded setup looks the same (its
                // other levels -- resistance, swing lows -- vary by strategy and the zones already say them)
                shapes.push(...(traded.shapes || []).filter((x) => x.shape === "level" && (x.role === "stop" || x.role === "target")));
                return;
              }
              // a failed setup's contraction line takes its grey, so a real VCP stands out
              shapes.push(...z.shapes.map((x) => (!s.complete && x.role === "contraction" ? { ...x, role: "failpath" } : x)));
            });
          }
          // tell the chart which of the run's trades this layer draws: any trade no current setup covers
          // (today's rules may no longer see it) keeps the run's own drawing, so no trade goes missing
          ctx.claimTrades?.(new Set(setups.map(tradeOf).filter(Boolean).map((t) => t.entry_date)));
          const c = (k) => { try { return col(k); } catch { return undefined; } };   // a layer may not declare every colour
          ctx.annotate(id, on ? stage.concat(shapes) : [], { uptrend: c("uptrend"), base: c("base"), contraction: c("base"),
            vcp: c("vcp"), cheat: c("cheat"), miss: c("miss"), flag: c("flag"), failpath: DIM, young: YOUNG, tight: c("tight"),
            pivot: c("pivot") || c("tight"), buy: c("buy"), stop: c("stop"), breakeven: DIM, target: c("target"), dim: DIM, ...extraRoles });
          renderCard();
          lane.mark();
          publish();
        };
        // the side panel's Trade setups tab (app.js) lists these: hand it the list, the selection, and a way to pick one
        const publish = () => ctx.onSetups?.({ list: setups, focus: setups.indexOf(focus),
          select: (k) => { if (!setups[k]) return; pinned = setups[k]; hovered = null; reveal(pinned); paint(); } });
        let timer = null, raf = 0;
        chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
          clearTimeout(timer);
          timer = setTimeout(() => { if (setups.length && !pinned && !hovered && latest() !== focus) paint(); }, 150);
        });
        // A click on the chart selects a setup covering that bar; clicking again where several overlap steps
        // to the next of them. Inside the selected setup it opens the zone clicked. Empty space changes nothing.
        chart.subscribeClick((q) => {
          if (!setups.length) return;
          const t = timeOf(q); if (!t) return;
          const here = setups.filter((s) => s.from <= t && t <= s.to);
          if (!here.length) return;
          const k = here.indexOf(focus);
          const s = k >= 0 && pinned === focus ? (here.length > 1 ? here[(k + 1) % here.length] : focus) : here[0];
          pinned = s;
          const z = [...s.zones].reverse().find((x) => x.from <= t);
          if (z) { zoneOpen = z.key; store("ttZone", zoneOpen); }
          paint();
        });
        // frame a setup stepped to from the card in the left ~60% of the chart, so the card (which goes to
        // the roomier side) sits clear of it on the right
        const reveal = (s) => frameDates(chart, times, ctx, s.from, s.to, { fill: 0.58, lead: 0.04, price: s.frame });

        // ---- the setup lane: one pill per setup along the bottom of the price pane, stacked where they overlap
        const lane = (() => {
          const el = document.createElement("div"); el.className = "tt-lane";
          ctx.chartEl?.append(el);
          // select on press, not click: hovering re-renders the lane, and a click needs the same element
          // under the mouse at press and release
          el.addEventListener("mousedown", (e) => {
            e.stopPropagation();
            const b = e.target.closest(".tt-pill"); if (!b || e.button !== 0) return;
            e.preventDefault();
            pinned = setups[+b.dataset.i]; hovered = null; paint();
          });
          el.addEventListener("mouseover", (e) => {
            const b = e.target.closest(".tt-pill"); const s = b ? setups[+b.dataset.i] : null;
            if (s && s !== hovered) { hovered = s; paint(); }
          });
          el.addEventListener("mouseleave", () => { if (hovered) { hovered = null; paint(); } });
          const render = () => {
            el.hidden = !on || !setups.length;
            if (el.hidden) return;
            const ts = chart.timeScale(), w = ts.width(), left = chart.priceScale("left").width() || 0;
            const pane = chart.panes()[0], H = pane ? pane.getHeight() : ctx.chartEl.clientHeight;
            const xOf = (d) => { const i = times.findIndex((t) => t >= d); return ts.logicalToCoordinate(i < 0 ? times.length - 1 : i); };
            const rows = [];   // each row's right edge, for stacking
            const pills = [];
            setups.forEach((s, i) => {
              let x0 = xOf(s.from), x1 = xOf(s.to);
              if (x0 == null || x1 == null || x1 < 0 || x0 > w) return;
              x0 = Math.max(0, x0); x1 = Math.min(w, Math.max(x1, x0 + 8));
              let r = rows.findIndex((edge) => edge < x0 - 2); if (r < 0) { r = rows.length; rows.push(0); }
              rows[r] = x1;
              const sel = s === focus, txt = x1 - x0 > 46 ? s.title : "";
              const tr = tradeOf(s);
              pills.push(`<button class="tt-pill ${s.kind === "fail" || s.kind === "young" ? "no" : "ok"} ${sel ? "sel" : ""} ${tr ? "traded" : ""}" data-i="${i}" title="${esc(s.title)} · ${esc(s.from)} → ${esc(s.to)}${tr ? ` · traded by the selected run${tr.r_multiple != null ? `, ${(+tr.r_multiple).toFixed(2)}R` : ""}` : ""}"
                style="left:${left + x0}px;width:${x1 - x0}px;bottom:${ctx.chartEl.clientHeight - H + 30 + r * 17}px;--c:${kindCol(s)}">${tr ? "● " : ""}${esc(txt)}</button>`);
            });
            el.innerHTML = pills.join("");
          };
          // the selection changed, not the view: restyle the pills in place, never rebuild them — a pill
          // replaced under the mouse loses the press that was meant for it
          const mark = () => el.querySelectorAll(".tt-pill").forEach((b) => b.classList.toggle("sel", setups[+b.dataset.i] === focus));
          chart.timeScale().subscribeVisibleLogicalRangeChange(() => requestAnimationFrame(() => { render(); if (!card.hidden) place(focus); }));
          chart.timeScale().subscribeSizeChange(() => requestAnimationFrame(render));
          return { render, mark, el };
        })();
        // p.tradedOnly (the chart's backtest view): only the setups the selected run traded, so the chart
        // shows that run's trades and nothing it did not buy; re-filtered when the run's trades arrive
        let arrived = false;
        const refresh = () => {
          ownersOf = null;
          setups = p.tradedOnly ? all.filter(tradeOf) : all;
          if (!setups.includes(pinned)) pinned = null;
          // the backtest view opens on the run's latest trade here, not on today's bars
          // (a frame later: after the chart's own opening view, which would otherwise win the race)
          if (p.tradedOnly && !arrived && setups.length) {
            arrived = true; pinned = setups.at(-1);
            ctx.claimView?.();   // the chart must not then apply its usual "recent bars" opening view
            const s0 = pinned; reveal(s0); requestAnimationFrame(() => { if (pinned === s0) { reveal(s0); paint(); } });
          }
        };
        ctx.onTrades?.(() => { refresh(); if (all.length) { paint(); lane.render(); } });
        // a trade picked in the Backtest trades panel selects the setup it was bought from
        ctx.onFocusTrade?.((t) => {
          const s = t ? [...ownerMap()].find(([, x]) => x.entry_date === t.entry_date)?.[0] : null;
          if (s || !t) { pinned = s || null; hovered = null; paint(); }
          // go to it: the setup's frame through the trade's exit, the price axis back on auto
          if (s) frameDates(chart, times, ctx, s.from, t.exit_date && t.exit_date > s.to ? t.exit_date : s.to, { fill: 0.7, lead: 0.05, price: s.frame });
        });
        (async () => {
          setNote(id, "testing each bar…");
          const r = await load().catch(() => null);
          if (!r || r.error) { setups = []; publish(); return setNote(id, r?.error || "could not load the setups"); }
          stage = r.background || [];
          all = r.setups || [];
          refresh();
          setNote(id, p.tradedOnly ? `the selected run's trades, drawn as ${r.note.split(":")[0].toLowerCase()} — backtest view` : r.note);
          paint(); lane.render();
        })();
        return { series: [], note: "testing each bar…", setVisible: (v) => { on = v; paint(); lane.render(); } };
  }

  /** A generic Trade setups layer for `strategy` (any strategy without its own bases_live): the server's
   *  live_setups scan, the shared machinery, and a colour key in the generic vocabulary. `structure`
   *  names the roles the strategy's own drawing uses ({ role: [title, colour] }). */
  function genericSetups(strategy, learnGuide, structure = {}) {
    return { setupsFor: strategy, learnGuide, short: "Setups", cat: "Screener", overlay: true, custom: true,
      label: (p) => `${stratName(strategy)} · setups${p.years === "All" ? " · all history" : ` · ${p.years}y`}`,
      params: { show: { type: "select", def: "All setups", options: ["All setups", "Traded or on trigger", "None"] },
        years: { type: "select", def: "5", options: ["5", "10", "All"] },
        card: { type: "select", def: "Show", options: ["Show", "Hide"] } },
      plots: [{ k: "vcp", t: "Would trade", c: "#22c55e" }, { k: "cheat", t: "On trigger", c: "#38bdf8" },
        { k: "miss", t: "Refused", c: "#f43f5e" }, { k: "uptrend", t: "Trend", c: "#ab47bc" },
        ...Object.entries(structure).map(([k, [t, c]]) => ({ k, t, c })),
        { k: "flag", t: "Flag", c: "#f59e0b" },
        { k: "buy", t: "Buy", c: "#26a69a" }, { k: "stop", t: "Stop", c: "#ef5350" }, { k: "target", t: "Target", c: "#4caf50" }],
      draw(args) {
        const { p, col, tf, ctx } = args;
        if (tf !== "D" || !ctx.annotate) return { series: [], note: "daily charts only", setVisible() {} };
        const years = scanYears(p.years === "All" ? 0 : +p.years || 5, ctx);
        const load = async () => {
          // with a backtest run selected, the server judges each setup that run traded on the bar it traded
          const x = await fetch(`/api/setups/${strategy}/${ctx.market}/${encodeURIComponent(ctx.symbol)}?years=${years}${ctx.runId ? `&run=${ctx.runId}` : ""}`);
          // a 404 here is a server started before this layer existed: say so rather than draw nothing
          if (x.status === 404) return { error: `the server has no ${stratName(strategy)} setups yet — restart it to load this layer` };
          if (!x.ok) return { error: `the setups could not be computed (HTTP ${x.status})` };
          const r = await x.json();
          const all = r.bases || [];
          return { background: [], setups: p.show === "None" ? [] : p.show === "Traded or on trigger" ? all.filter((b) => b.kind !== "fail") : all,
            note: `${r.note} · pick one from the lane at the bottom` };
        };
        const keyRows = () => [
          ["frame", col("vcp"), "Green frame", "the strategy would trade this setup: every gate passed, a valid plan, decided TRADE - HIGH CONFIDENCE, and the entry fired."],
          ["frame", col("cheat"), "Blue frame", "a valid plan the strategy stops short of buying today (TRADE ON TRIGGER), such as a coil not yet through its pivot."],
          ["dashframe", col("miss"), "Rose dashed frame", "refused: a gate failed, the plan was refused, or the decision said WATCH. The header names it."],
          ["frame", col("buy"), "● traded", "a backtest run is selected AND it bought this setup: its levels are the run's own record."],
          ["pill", col("vcp"), "Lane at the bottom", "every setup, one pill each. Click one to select it."],
          ["arrow", col("uptrend"), "① Gates", "the trend into the setup, and every hard gate in the strategy's own words."],
          ...Object.entries(structure).map(([k, [t]]) => ["box", col(k), `② ${t}`, "the structure the setup was judged on, drawn by the strategy itself."]),
          ["line", col("buy"), "③ Entry", "the strategy's own buy, stop and target for the judged bar. An illustration of the rules."],
        ];
        return setupLayer({ ...args, keyRows, load });
      } };
  }

  const CATALOG = {
    sma: { name: "Moving Average", short: "MA", cat: "Moving averages", overlay: true, params: { length: 20, source: SRC }, plots: [{ k: "ma", c: "#f5a623" }],
      calc: (b, p) => ({ ma: sma(source(b, p.source), p.length) }) },
    ema: { name: "Moving Average Exponential", short: "EMA", cat: "Moving averages", overlay: true, params: { length: 20, source: SRC }, plots: [{ k: "ma", c: "#ffeb3b" }],
      calc: (b, p) => ({ ma: ema(source(b, p.source), p.length) }) },
    wma: { name: "Moving Average Weighted", short: "WMA", cat: "Moving averages", overlay: true, params: { length: 20, source: SRC }, plots: [{ k: "ma", c: "#00bcd4" }],
      calc: (b, p) => ({ ma: wma(source(b, p.source), p.length) }) },
    ribbon: ribbon("Moving Average Ribbon (SMA)", "MA Ribbon", "SMA"),
    ribbon_ema: ribbon("Moving Average Ribbon (EMA)", "MA Ribbon", "EMA"),  // label shows the type: "MA Ribbon EMA 20 50 ..."
    dema: { name: "Double Exponential Moving Average (DEMA)", short: "DEMA", cat: "Moving averages", overlay: true, params: { length: 20, source: SRC }, plots: [{ k: "ma", c: "#43a047" }],
      calc: (b, p) => { const e1 = ema(source(b, p.source), p.length), e2 = ema(e1, p.length); return { ma: zip((x, y) => 2 * x - y, e1, e2) }; } },
    hma: { name: "Hull Moving Average", short: "HMA", cat: "Moving averages", overlay: true, params: { length: 9, source: SRC }, plots: [{ k: "ma", c: "#ab47bc" }],
      calc: (b, p) => { const s = source(b, p.source), half = Math.max(1, Math.floor(p.length / 2)), sq = Math.max(1, Math.round(Math.sqrt(p.length)));
        return { ma: wma(zip((x, y) => 2 * x - y, wma(s, half), wma(s, p.length)), sq) }; } },
    kama: { name: "Kaufman Adaptive Moving Average (KAMA)", short: "KAMA", cat: "Moving averages", overlay: true, params: { length: 10, fast: 2, slow: 30, source: SRC },
      plots: [{ k: "ma", c: "#00897b" }],
      calc: (b, p) => {
        // efficiency ratio = net move ÷ the sum of every bar's move; it slides the smoothing between the fast and slow EMA speeds
        const s = source(b, p.source), n = s.length, o = nul(n), fsc = 2 / (p.fast + 1), ssc = 2 / (p.slow + 1);
        let k = null;
        for (let i = p.length; i < n; i++) {
          if (s[i] == null || s[i - p.length] == null) { k = null; continue; }
          let noise = 0; for (let j = i - p.length + 1; j <= i; j++) noise += Math.abs(s[j] - s[j - 1]);
          const er = noise ? Math.abs(s[i] - s[i - p.length]) / noise : 0, sc = (er * (fsc - ssc) + ssc) ** 2;
          k = k == null ? s[i - 1] : k;
          k += sc * (s[i] - k); o[i] = k;
        }
        return { ma: o };
      } },
    alligator: { name: "Williams Alligator", short: "Alligator", cat: "Moving averages", overlay: true,
      params: { jaw: 13, jawShift: 8, teeth: 8, teethShift: 5, lips: 5, lipsShift: 3 },
      plots: [{ k: "jaw", t: "Jaw", c: "#2962ff" }, { k: "teeth", t: "Teeth", c: "#f23645" }, { k: "lips", t: "Lips", c: "#43a047" }],
      // three Wilder-smoothed averages of the bar's midpoint, each drawn `shift` bars later (Williams draws them
      // forward into the future; here each bar shows the value from `shift` bars before, so the future part is omitted)
      calc: (b, p) => { const m = source(b, "hl2"), sh = (a, k) => a.map((_, i) => (i >= k ? a[i - k] : null));
        return { jaw: sh(rma(m, p.jaw), p.jawShift), teeth: sh(rma(m, p.teeth), p.teethShift), lips: sh(rma(m, p.lips), p.lipsShift) }; } },
    bb: { name: "Bollinger Bands", short: "BB", cat: "Bands & channels", overlay: true, params: { length: 20, mult: 2, source: SRC },
      plots: [{ k: "basis", t: "Basis", c: "#ff9800" }, { k: "upper", t: "Upper", c: "#2962ff" }, { k: "lower", t: "Lower", c: "#2962ff" }],
      calc: (b, p) => { const s = source(b, p.source), m = sma(s, p.length), sd = stdev(s, p.length);
        return { basis: m, upper: zip((x, d) => x + p.mult * d, m, sd), lower: zip((x, d) => x - p.mult * d, m, sd) }; } },
    kc: { name: "Keltner Channels", short: "KC", cat: "Bands & channels", overlay: true, params: { length: 20, mult: 2, atrLength: 10 },
      plots: [{ k: "basis", t: "Basis", c: "#2962ff" }, { k: "upper", t: "Upper", c: "#2962ff" }, { k: "lower", t: "Lower", c: "#2962ff" }],
      calc: (b, p) => { const m = ema(b.C, p.length), a = rma(trueRange(b.H, b.L, b.C), p.atrLength);
        return { basis: m, upper: zip((x, r) => x + p.mult * r, m, a), lower: zip((x, r) => x - p.mult * r, m, a) }; } },
    dc: { name: "Donchian Channels", short: "DC", cat: "Bands & channels", overlay: true, params: { length: 20 },
      plots: [{ k: "upper", t: "Upper", c: "#2962ff" }, { k: "basis", t: "Basis", c: "#ff6d00" }, { k: "lower", t: "Lower", c: "#2962ff" }],
      calc: (b, p) => { const u = highest(b.H, p.length), l = lowest(b.L, p.length); return { upper: u, lower: l, basis: zip((x, y) => (x + y) / 2, u, l) }; } },
    env: { name: "Moving Average Envelopes", short: "Env", cat: "Bands & channels", overlay: true, params: { length: 20, percent: 2.5 },
      plots: [{ k: "basis", t: "Basis", c: "#ff9800" }, { k: "upper", t: "Upper", c: "#2962ff" }, { k: "lower", t: "Lower", c: "#2962ff" }],
      calc: (b, p) => { const m = sma(b.C, p.length), f = p.percent / 100;
        return { basis: m, upper: m.map((x) => (x == null ? null : x * (1 + f))), lower: m.map((x) => (x == null ? null : x * (1 - f))) }; } },
    atrbands: { name: "ATR Bands", short: "ATR Bands", cat: "Bands & channels", overlay: true, params: { length: 20, atrLength: 14, mult: 2 },
      plots: [{ k: "basis", t: "Basis", c: "#ff9800" }, { k: "upper", t: "Upper", c: "#2962ff" }, { k: "lower", t: "Lower", c: "#2962ff" }],
      calc: (b, p) => { const m = sma(b.C, p.length), a = rma(trueRange(b.H, b.L, b.C), p.atrLength);
        return { basis: m, upper: zip((x, r) => x + p.mult * r, m, a), lower: zip((x, r) => x - p.mult * r, m, a) }; } },
    vwap: { name: "Rolling VWAP", short: "VWAP", cat: "Volume", overlay: true, needsVolume: true, params: { length: 20 }, plots: [{ k: "vwap", c: "#e040fb" }],
      calc: (b, p) => { const tp = source(b, "hlc3"); return { vwap: zip((x, y) => (y ? x / y : null), sum(zip((t, v) => t * v, tp, b.V), p.length), sum(b.V, p.length)) }; } },
    sar: { name: "Parabolic SAR", short: "SAR", cat: "Trend", overlay: true, params: { start: 0.02, increment: 0.02, maximum: 0.2 }, plots: [{ k: "sar", c: "#2962ff", s: "dots" }],
      calc: (b, p) => {
        const n = b.C.length, o = nul(n); if (n < 2) return { sar: o };
        let up = b.C[1] >= b.C[0], af = p.start, ep = up ? b.H[0] : b.L[0], s = up ? b.L[0] : b.H[0];
        for (let i = 1; i < n; i++) {
          s = s + af * (ep - s);
          if (up) {
            s = Math.min(s, b.L[i - 1], i > 1 ? b.L[i - 2] : b.L[i - 1]);
            if (b.L[i] < s) { up = false; s = ep; ep = b.L[i]; af = p.start; }
            else if (b.H[i] > ep) { ep = b.H[i]; af = Math.min(af + p.increment, p.maximum); }
          } else {
            s = Math.max(s, b.H[i - 1], i > 1 ? b.H[i - 2] : b.H[i - 1]);
            if (b.H[i] > s) { up = true; s = ep; ep = b.H[i]; af = p.start; }
            else if (b.L[i] < ep) { ep = b.L[i]; af = Math.min(af + p.increment, p.maximum); }
          }
          o[i] = s;
        }
        return { sar: o };
      } },
    st: { name: "Supertrend", short: "Supertrend", cat: "Trend", overlay: true, params: { atrLength: 10, factor: 3 }, plots: [{ k: "up", t: "Up trend", c: "#089981" }, { k: "down", t: "Down trend", c: "#f23645" }],
      calc: (b, p) => {
        const n = b.C.length, atr = rma(trueRange(b.H, b.L, b.C), p.atrLength), up = nul(n), dn = nul(n);
        let fu = null, fl = null, dir = 1;
        for (let i = 0; i < n; i++) {
          if (atr[i] == null) continue;
          const hl2 = (b.H[i] + b.L[i]) / 2, bu = hl2 + p.factor * atr[i], bl = hl2 - p.factor * atr[i];
          const pu = fu, pl = fl;
          fu = pu == null || bu < pu || b.C[i - 1] > pu ? bu : pu;
          fl = pl == null || bl > pl || b.C[i - 1] < pl ? bl : pl;
          if (pu != null) dir = dir === -1 ? (b.C[i] > pu ? 1 : -1) : (b.C[i] < pl ? -1 : 1);
          if (dir === 1) up[i] = fl; else dn[i] = fu;
        }
        return { up, down: dn };
      } },
    ichimoku: { name: "Ichimoku Cloud (lines)", short: "Ichimoku", cat: "Trend", overlay: true, params: { conversion: 9, base: 26, spanB: 52 },
      plots: [{ k: "conv", t: "Conversion", c: "#2962ff" }, { k: "base", t: "Base", c: "#b71c1c" }, { k: "spanA", t: "Lead A (unshifted)", c: "#43a047" }, { k: "spanB", t: "Lead B (unshifted)", c: "#f23645" }],
      calc: (b, p) => {
        const mid = (n) => zip((h, l) => (h + l) / 2, highest(b.H, n), lowest(b.L, n));
        const conv = mid(p.conversion), base = mid(p.base);
        return { conv, base, spanA: zip((x, y) => (x + y) / 2, conv, base), spanB: mid(p.spanB) };
      } },
    vortex: { name: "Vortex Indicator", short: "VI", cat: "Trend", params: { length: 14 }, levels: [1],
      plots: [{ k: "vip", t: "VI+", c: "#2962ff" }, { k: "vim", t: "VI−", c: "#f23645" }],
      calc: (b, p) => {
        // VI+ sums how far each high reached above the previous low, VI− how far each low reached below the previous high, both ÷ the true range
        const n = b.C.length, vp = nul(n), vm = nul(n);
        for (let i = 1; i < n; i++) { vp[i] = Math.abs(b.H[i] - b.L[i - 1]); vm[i] = Math.abs(b.L[i] - b.H[i - 1]); }
        const tr = trueRange(b.H, b.L, b.C); tr[0] = null;
        const st = sum(tr, p.length);
        return { vip: zip((x, t) => (t ? x / t : null), sum(vp, p.length), st), vim: zip((x, t) => (t ? x / t : null), sum(vm, p.length), st) };
      } },
    chandelier: { name: "Chandelier Exit", short: "Chandelier", cat: "Trend", overlay: true, params: { length: 22, mult: 3 },
      plots: [{ k: "long", t: "Long exit", c: "#089981" }, { k: "short", t: "Short exit", c: "#f23645" }],
      calc: (b, p) => { const a = rma(trueRange(b.H, b.L, b.C), p.length);
        return { long: zip((h, r) => h - p.mult * r, highest(b.H, p.length), a), short: zip((l, r) => l + p.mult * r, lowest(b.L, p.length), a) }; } },
    // ---- support & resistance (drawn on the price series itself: markers, step lines, price lines)
    pivots_hl: { name: "Pivot Points High Low (swing pivots)", short: "Pivots HL", cat: "Support & resistance", overlay: true, custom: true,
      label: (p) => `Pivots HL ${p.left}/${p.right}`,
      params: { left: 10, right: 10, labels: { type: "select", def: "Price", options: ["Price", "Structure (HH/HL/LH/LL)", "None"] },
        zigzag: { type: "select", def: "No", options: ["No", "Yes"] } },
      plots: [{ k: "hi", t: "Pivot high", c: "#f23645" }, { k: "lo", t: "Pivot low", c: "#089981" }, { k: "zz", t: "Zig-zag", c: "#ff9800" }],
      draw({ chart, main, times, bars, p, col }) {
        const piv = swingPivots(bars.H, bars.L, p.left, p.right);
        let lastH = null, lastL = null;
        const markers = piv.map((v) => {
          let text = p.labels === "Price" ? fmtPx(v.price) : "";
          if (p.labels.startsWith("Structure")) {
            const prev = v.type === "H" ? lastH : lastL;
            text = prev == null ? v.type : v.type === "H" ? (v.price > prev ? "HH" : "LH") : (v.price > prev ? "HL" : "LL");
          }
          if (v.type === "H") lastH = v.price; else lastL = v.price;
          return v.type === "H"
            ? { time: times[v.i], position: "aboveBar", shape: "arrowDown", color: col("hi"), text, size: 0.6 }
            : { time: times[v.i], position: "belowBar", shape: "arrowUp", color: col("lo"), text, size: 0.6 };
        });
        const plugin = LC.createSeriesMarkers(main, markers);
        const series = [];
        if (p.zigzag === "Yes") {  // alternate highs and lows, keeping the more extreme of two in a row
          const zz = [];
          for (const v of piv) {
            const last = zz.at(-1);
            if (last && last.type === v.type) { if (v.type === "H" ? v.price > last.price : v.price < last.price) zz[zz.length - 1] = v; }
            else if (!last || last.i !== v.i) zz.push(v);
          }
          const z = chart.addSeries(LC.LineSeries, { color: col("zz"), lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false }, 0);
          z.setData(zz.map((v) => ({ time: times[v.i], value: v.price })));
          series.push(z);
        }
        const nH = piv.filter((v) => v.type === "H").length;
        return { series, note: `${nH} highs · ${piv.length - nH} lows`,
          setVisible: (on) => { plugin.setMarkers(on ? markers : []); series.forEach((x) => x.applyOptions({ visible: on })); } };
      } },
    pivots_std: { name: "Pivot Points Standard", short: "Pivots", cat: "Support & resistance", overlay: true, custom: true,
      label: (p) => `Pivots ${p.method} ${p.timeframe}`,
      params: { method: { type: "select", def: "Traditional", options: ["Traditional", "Fibonacci", "Camarilla"] },
        timeframe: { type: "select", def: "Auto", options: ["Auto", "Week", "Month", "Quarter", "Year"] }, back: 12 },
      plots: [{ k: "P", t: "P", c: "#ff9800" }, { k: "R1", t: "R1", c: "#f23645" }, { k: "R2", t: "R2", c: "#f23645" }, { k: "R3", t: "R3", c: "#f23645" },
        { k: "S1", t: "S1", c: "#089981" }, { k: "S2", t: "S2", c: "#089981" }, { k: "S3", t: "S3", c: "#089981" }],
      draw({ chart, times, bars, p, col, tf }) {
        // TradingView's "Auto": monthly pivots on a daily chart, yearly on weekly/monthly charts
        const unit = { Week: "W", Month: "M", Quarter: "Q", Year: "Y" }[p.timeframe] || (tf === "D" ? "M" : "Y");
        const periods = [];
        times.forEach((t, i) => {
          const k = periodKey(t, unit), cur = periods.at(-1);
          if (!cur || cur.k !== k) periods.push({ k, start: i, end: i, H: bars.H[i], L: bars.L[i], C: bars.C[i] });
          else { cur.end = i; cur.H = Math.max(cur.H, bars.H[i]); cur.L = Math.min(cur.L, bars.L[i]); cur.C = bars.C[i]; }
        });
        const levels = (H, L, C) => {
          const P = (H + L + C) / 3, r = H - L;
          if (p.method === "Fibonacci") return { P, R1: P + 0.382 * r, R2: P + 0.618 * r, R3: P + r, S1: P - 0.382 * r, S2: P - 0.618 * r, S3: P - r };
          if (p.method === "Camarilla") return { P, R1: C + 1.1 * r / 12, R2: C + 1.1 * r / 6, R3: C + 1.1 * r / 4, S1: C - 1.1 * r / 12, S2: C - 1.1 * r / 6, S3: C - 1.1 * r / 4 };
          return { P, R1: 2 * P - L, R2: P + r, R3: H + 2 * (P - L), S1: 2 * P - H, S2: P - r, S3: L - 2 * (H - P) };  // Traditional (floor)
        };
        // each period's levels come from the PREVIOUS complete period; the current period is included
        const shown = periods.slice(1).map((pd, k) => ({ pd, lv: levels(periods[k].H, periods[k].L, periods[k].C) })).slice(-Math.max(1, p.back));
        // one short flat segment per level per period (separate series, so periods are not joined
        // by connecting lines); only the current period's segments label the price axis
        const series = [];
        shown.forEach(({ pd, lv }, k) => {
          const current = k === shown.length - 1;
          for (const key of ["P", "R1", "R2", "R3", "S1", "S2", "S3"]) {
            const x = chart.addSeries(LC.LineSeries, { color: col(key), lineWidth: key === "P" ? 2 : 1, priceLineVisible: false,
              lastValueVisible: current, title: current ? key : "", crosshairMarkerVisible: false }, 0);
            const data = [];
            for (let i = pd.start; i <= pd.end; i++) data.push({ time: times[i], value: lv[key] });
            x.setData(data);
            series.push(x);
          }
        });
        const last = shown.at(-1);
        return { series, note: last ? `${p.method} · ${{ W: "weekly", M: "monthly", Q: "quarterly", Y: "yearly" }[unit]} · P ${fmtPx(last.lv.P)}` : "",
          setVisible: (on) => series.forEach((x) => x.applyOptions({ visible: on })) };
      } },
    zigzag: { name: "Zig Zag", short: "ZigZag", cat: "Support & resistance", overlay: true, params: { deviation: 5 }, plots: [{ k: "zz", c: "#ff9800", w: 2 }],
      calc: (b, p) => {
        // swing points where price reversed by at least `deviation` % (highs and lows), joined by straight
        // lines. The last leg runs to the latest extreme and is redrawn as new bars arrive — it repaints.
        const n = b.C.length, o = nul(n), piv = [], d = p.deviation / 100;
        if (n < 2) return { zz: o };
        // A bar is checked for a reversal against the extreme of EARLIER bars before it can set a new
        // extreme itself: a daily bar does not say whether its high or its low came first, so one wide
        // bar never becomes both a swing high and a swing low.
        let dir = 0, hi = 0, lo = 0;
        for (let i = 1; i < n; i++) {
          if (b.H[i] == null || b.L[i] == null) continue;
          if (dir === 1) {
            if (b.L[i] <= b.H[hi] * (1 - d)) { piv.push({ i: hi, v: b.H[hi] }); dir = -1; lo = i; }
            else if (b.H[i] > b.H[hi]) hi = i;
          } else if (dir === -1) {
            if (b.H[i] >= b.L[lo] * (1 + d)) { piv.push({ i: lo, v: b.L[lo] }); dir = 1; hi = i; }
            else if (b.L[i] < b.L[lo]) lo = i;
          } else {
            if (b.H[i] > b.H[hi]) hi = i;
            if (b.L[i] < b.L[lo]) lo = i;
            if (hi > lo && b.H[hi] >= b.L[lo] * (1 + d)) { piv.push({ i: lo, v: b.L[lo] }); dir = 1; }
            else if (lo > hi && b.L[lo] <= b.H[hi] * (1 - d)) { piv.push({ i: hi, v: b.H[hi] }); dir = -1; }
          }
        }
        if (dir === 1) piv.push({ i: hi, v: b.H[hi] }); else if (dir === -1) piv.push({ i: lo, v: b.L[lo] });
        for (let k = 0; k + 1 < piv.length; k++) {
          const a = piv[k], c = piv[k + 1];
          for (let i = a.i; i <= c.i; i++) o[i] = c.i === a.i ? c.v : a.v + ((c.v - a.v) * (i - a.i)) / (c.i - a.i);
        }
        return { zz: o };
      } },
    // ---- support & resistance ZONES from core/sr_levels.py (/api/sr-levels). Every rule is there; this
    // only draws, with one visual channel per kind of information:
    //   hue = role (support teal, resistance red, pivot amber, congestion grey, references mid grey);
    //   line weight + dash = timeframe (monthly heavy solid, weekly dashed, daily dotted);
    //   fill = the zone's extent (a soft tint, a faint outline — the key line is the strongest element);
    //   opacity = reliability (levels near price fade when earnings are close);
    //   text = the price-axis tag; in-chart labels are optional.
    sr: { name: "Support & Resistance (zones)", short: "S/R", cat: "Support & resistance", overlay: true, custom: true,
      // key levels only by default: the few nearest graded zones each side (up to 4, 7 in all); "All
      // graded levels" adds every other zone that passed the grade as a thin dashed outline. A copy saved
      // under the old option name ("Key levels (3 each side)") still reads as key levels.
      label: (p) => `S/R zones${p.levels === "All graded levels" ? " · all graded" : ""}`,
      params: { levels: { type: "select", def: "Key levels", options: ["Key levels", "All graded levels"] },
        labels: { type: "select", def: "Axis only", options: ["Axis only", "Short", "Full"] },
        periods: { type: "select", def: "Hide", options: ["Hide", "Show"] },
        palette: { type: "select", def: "Standard", options: ["Standard", "Colour-blind (blue / orange)"] },
        axis: { type: "select", def: "Show", options: ["Show", "Hide"] } },
      plots: [{ k: "res", t: "Resistance", c: "#d64545" }, { k: "sup", t: "Support", c: "#1f9d7a" }, { k: "piv", t: "Pivot / at price", c: "#e0a030" },
        { k: "cong", t: "Congestion band (context, not a level)", c: "#8a8f98" },
        { k: "per", t: "Previous period high / low", c: "#6b7280" }],
      draw({ main, times, p, col, tf, ctx, id }) {
        if (!["D", "W", "M"].includes(tf) || !ctx.annotate) return { series: [], note: "daily, weekly or monthly charts only", setVisible() {} };
        let on = true, shapes = [], specs = [], lines = [];
        const NAME = { M: "monthly", W: "weekly", D: "daily" };
        // the colour-blind palette swaps red / green for orange / blue; position and the axis tag still say the role
        const CB = { sup: "#2b7bd6", res: "#e8833a", piv: "#8e5bc4" };
        const C = (k) => (p.palette?.startsWith("Colour-blind") && CB[k]) || col(k);
        const rgba = (hex, a) => { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };
        const roleKey = (z) => (z.role === "resistance" ? "res" : z.role === "pivot" ? "piv" : "sup");
        // timeframe -> weight and dash, on the zone's key line and its axis line alike
        const STYLE = { M: { w: 3, dash: false, ls: 0 }, W: { w: 2, dash: true, ls: 2 }, D: { w: 1, dash: "dot", ls: 1 } };
        const paint = () => {
          ctx.annotate(id, on ? shapes : [], { support: C("sup"), resistance: C("res"), pivot: C("piv"), congestion: col("cong"), period: col("per") });
          lines.forEach((l) => main.removePriceLine(l));
          lines = on && p.axis !== "Hide" ? specs.map((o) => main.createPriceLine(o)) : [];
        };
        fetch(`/api/sr-levels/${ctx.market}/${encodeURIComponent(ctx.symbol)}?tf=${tf}`).then((x) => (x.ok ? x.json() : null)).then((r) => {
          if (!r) return setNote(id, "could not load the levels");
          const n = times.length, last = times.at(-1);
          const idx = (d) => { const i = times.findIndex((t) => t >= d); return i < 0 ? n - 1 : i; };
          const roleWord = (z) => (z.role === "pivot" ? (z.at_price ? "At price" : "Pivot — price inside")
            : `${z.role === "resistance" ? "Resistance" : "Support"}${z.flipped ? ` (was ${z.role === "resistance" ? "support" : "resistance"})` : ""}`);
          const inline = p.labels === "Short" || p.labels === "Full";
          const tagsOf = (z) => p.labels !== "Full" ? [roleWord(z), NAME[z.tf], ...(z.congestion ? ["congestion"] : []), ...(z.wide ? ["wide"] : [])] : [roleWord(z),
            NAME[z.tf], `scores ${z.score}/${z.of}`, `${z.touches.length} visit${z.touches.length > 1 ? "s" : ""}`,
            ...(z.height_atr != null ? [`${z.height_atr.toFixed(1)} × ${NAME[z.atr_tf || z.tf]} ATR tall${z.wide ? " (wide)" : ""}`] : []),
            ...(z.congestion ? [`congestion: price closed inside on ${Math.round(z.time_inside * 100)}% of bars`] : []),
            ...(z.worn ? ["worn"] : []), ...(z.promoted ? ["promoted to fill a gap near price"] : []), ...(z.capped ? ["cut back to its body side"] : [])];
          // earnings close: levels within 3% of price fade (opacity carries reliability)
          const fades = (z) => r.earnings_sessions != null && Math.abs(z.line - r.close) / r.close < 0.03;
          // in-chart labels (optional) sit toward the left of the zone, where there are fewer recent
          // candles, and step right when another label is within ~1.5% of price
          const labelX = new Map();
          { let prev = null, step = 0;
            for (const z of [...r.zones].sort((a, b) => b.top - a.top)) {
              step = prev != null && prev - z.top < r.close * 0.015 ? step + 1 : 0;
              labelX.set(z, times[Math.min(n - 1, Math.max(idx(z.from), n - 170) + step * 35)]);
              prev = z.top;
            } }
          // the other graded zones: a thin dashed outline only — context when the view scrolls back
          const extra = p.levels !== "All graded levels" ? [] : (r.others || []).map((z) => (
            { shape: "box", frame: true, dash: true, faint: true, from: z.from, to: last, top: z.top, bottom: z.bottom, role: z.role, label: "" }));
          // congestion bands under everything: a grey tint, no border, no lines (a break out is the event)
          const bands = (r.congestion || []).flatMap((c) => [
            { shape: "box", shade: true, from: c.from, to: last, top: c.top, bottom: c.bottom, role: "congestion" },
            ...(inline ? [{ shape: "text", at: times[Math.max(idx(c.from), n - 170)], price: c.top, role: "congestion", label: "Congestion" }] : [])]);
          // key zones: a soft fill with a faint outline, and the key line at full strength in the timeframe's style
          const keys = r.zones.flatMap((z) => {
            const st = STYLE[z.tf] || STYLE.D;
            return [
              { shape: "box", shade: true, edge: true, from: z.from, to: last, top: z.top, bottom: z.bottom, role: z.role },
              { shape: "level", from: z.from, to: last, price: z.line, role: z.role, width: st.w, dash: st.dash, label: "", ...(fades(z) ? { alpha: "70" } : {}) },
              ...(inline ? [{ shape: "text", at: labelX.get(z), price: z.top, role: z.role, label: tagsOf(z).join(" · ") }] : []),
            ];
          });
          // reference markers: grey, thin, a short segment near the right edge only; hidden inside a key zone
          // or within 0.3% of a key line. Always shown: the provisional extremes (52-week / all-time high and
          // low — a fresh one has no confirmed swing yet) and a round number standing in for a missing level
          const near = (x) => r.zones.some((z) => (x >= z.bottom && x <= z.top) || Math.abs(x - z.line) / r.close < 0.003);
          const always = new Set(["round_above", "round", "extreme"]);
          const refs = r.lines.filter((l) => (p.periods === "Show" && !near(l.price)) || always.has(l.kind))
            .map((l) => ({ shape: "level", from: times[Math.max(0, n - 15)], to: last, price: l.price, role: "period", width: 1, dash: true, label: l.label }));
          // long-term levels: a ceiling or floor price has reacted at over years, beyond the key levels' reach —
          // a muted band and a muted axis tag, seen when the view widens out to them
          const longs = (r.longterm || []).map((z) => ({ shape: "box", shade: true, edge: true, from: z.from, to: last, top: z.top, bottom: z.bottom, role: z.role }));
          shapes = [...bands, ...extra, ...longs, ...keys, ...refs];
          // the price-axis tags carry the words; their lines span the chart in the timeframe's style
          specs = r.zones.map((z) => {
            const st = STYLE[z.tf] || STYLE.D, c = C(roleKey(z));
            return { price: z.line, color: fades(z) ? rgba(c, 0.45) : c, lineWidth: st.w, lineStyle: st.ls, axisLabelVisible: true,
              // the tag carries the zone's far edge too ("… · to 1,377"): the line marks where price meets the
              // zone first, but for a tall zone the far edge is the next ceiling or floor, and only the shading showed it
              title: `${z.role === "pivot" ? (z.at_price ? "At price" : "Pivot") : z.role === "resistance" ? "Resistance" : "Support"}${z.flipped ? " (was " + (z.role === "resistance" ? "S)" : "R)") : ""} · ${NAME[z.tf]}`
                + (z.role === "pivot" ? ` · ${fmtPx(z.bottom)}–${fmtPx(z.top)}` : ` · to ${fmtPx(z.role === "resistance" ? z.top : z.bottom)}`) };
          });
          specs.push(...(r.longterm || []).map((z) => ({ price: z.line, color: rgba(C(roleKey(z)), 0.5), lineWidth: 1, lineStyle: 3, axisLabelVisible: true,
            title: `Long-term ${z.role} · ${NAME[z.tf]} · ${fmtPx(z.bottom)}–${fmtPx(z.top)} · ${z.touches[0].date.slice(0, 4)}–${z.touches.at(-1).date.slice(0, 4)}` })));
          const nS = r.zones.filter((z) => z.role === "support").length;
          const nR = r.zones.filter((z) => z.role === "resistance").length, nP = r.zones.length - nS - nR;
          const cong = (r.congestion || []).map((c) => `congestion band ${c.bottom.toFixed(2)}–${c.top.toFixed(2)} (price closed inside on ${Math.round(c.time_inside * 100)}% of bars)`);
          setNote(id, `${r.stack.filter(Boolean).map((t) => NAME[t]).join(" + ")} · ${nS} support, ${nR} resistance${nP ? `, ${nP} at price / pivot` : ""} (key)`
            + `${(r.longterm || []).length ? ` + ${r.longterm.length} long-term` : ""}${extra.length ? ` + ${extra.length} more graded, outlined` : ""}${cong.length ? " · " + cong.join(" · ") : ""}${r.note ? " · " + r.note : ""}`
            + `${r.earnings_sessions != null ? ` · ⚠ earnings in ${r.earnings_sessions} session${r.earnings_sessions === 1 ? "" : "s"}: levels within 3% of price are faded — less reliable through the report` : ""}`);
          paint();
        }).catch(() => setNote(id, "could not load the levels"));
        return { series: [], note: "finding levels…", setVisible: (v) => { on = v; paint(); } };
      } },
    // ---- supply & demand zones: the base each decisive move left from, found by core/sd_zones.py
    // (/api/sd-zones) — departure first, then the compact base, body-to-wick edges, a close beyond the
    // distal edge as failure. Every rule is there; this only picks which zones to show and draws them.
    sdz: { name: "Supply & Demand Zones (base → departure)", short: "S/D zones", cat: "Support & resistance", overlay: true, custom: true,
      label: (p) => `S/D zones · ${p.show === "Nearest to price" ? `${p.perSide} each side` : p.show.toLowerCase()}`,
      params: { show: { type: "select", def: "Nearest to price", options: ["Nearest to price", "All active", "All, with failed"] },
        perSide: 3, years: 10 },
      plots: [{ k: "demand", t: "Demand zone", c: "#089981" }, { k: "supply", t: "Supply zone", c: "#f23645" }],
      draw({ chart, times, p, col, tf, ctx, id }) {
        if (!["D", "W"].includes(tf) || !ctx.annotate) return { series: [], note: "daily or weekly charts only", setVisible() {} };
        let on = true, zones = [], shown = [], focus = null, checks = {};
        const roles = { demand: col("demand"), supply: col("supply") };
        const px = (v) => (+v).toFixed(2);
        // which zones to show is presentation: the active ones nearest the last close on each side,
        // or every active one, or the whole record including the failed (faint)
        const pick = (close, reach) => {
          const live = zones.map((z, i) => ({ z, i })).filter(({ z }) => z.status !== "failed");
          if (p.show === "All, with failed") return zones.map((_, i) => i);
          if (p.show === "All active") return live.map(({ i }) => i);
          // nearest to price, and only within reach (RELEVANCE_ATR of price, from the server): a zone
          // 40% away cannot matter to a trade now, so a side may show fewer than perSide, or none
          const near = live.filter(({ z }) => reach == null || Math.abs(close - z.proximal) <= reach);
          const dem = near.filter(({ z }) => z.kind === "demand").sort((a, b) => Math.abs(close - a.z.proximal) - Math.abs(close - b.z.proximal));
          const sup = near.filter(({ z }) => z.kind === "supply").sort((a, b) => Math.abs(close - a.z.proximal) - Math.abs(close - b.z.proximal));
          return [...dem.slice(0, p.perSide), ...sup.slice(0, p.perSide)].map(({ i }) => i);
        };
        const shapesOf = (z, i) => {
          const top = Math.max(z.proximal, z.distal), bottom = Math.min(z.proximal, z.distal);
          const faint = (focus != null && focus !== i) || (focus == null && z.status === "failed");
          // a worn zone (tested WORN_TESTS+ times) has spent its orders: it reads as a plain level now
          const tag = `${z.kind === "demand" ? "Demand" : "Supply"} · ${z.code} · ${z.passed}/${z.of} · ${z.status === "fresh" ? "fresh" : z.status === "tested" ? `tested ${z.tests.length}×` : "failed"}`
            + (z.worn && z.status !== "failed" ? ` · worn — now ${z.kind === "demand" ? "support" : "resistance"}` : "");
          const out = [
            { shape: "box", from: z.base_from, to: z.base_to, top, bottom, role: z.kind, label: tag, faint },   // the base itself
            { shape: "box", shade: true, from: z.base_to, to: z.until, top, bottom, role: z.kind, faint },        // extended right while valid
            { shape: "level", from: z.base_to, to: z.until, price: z.proximal, role: z.kind, dash: true, label: "", faint },
          ];
          if (!faint) out.push({ shape: "dots", role: z.kind, points: z.tests.map((t, k) => ({ at: t.date, price: t.price, label: `${k + 1}` })) });
          if (!faint && z.failed) out.push({ shape: "text", at: z.failed, price: z.distal, role: z.kind, label: "✕ closed through" });
          return out;
        };
        const paint = () => ctx.annotate(id, on ? (focus != null && !shown.includes(focus) ? [...shown, focus] : shown).flatMap((i) => shapesOf(zones[i], i)) : [], roles);
        // the base, the departure and what happened next: through the first retest (or the failure)
        // when that came within ~a year, else the 80 bars after the departure — an untested zone
        // stretched to today would shrink the base to a sliver
        const reveal = (z) => {
          const idx = (d) => { const i = times.findIndex((t) => t >= d); return i < 0 ? times.length - 1 : i; };
          const a = idx(z.base_from), dep = idx(z.depart_to);
          const ev = z.tests[0]?.date || z.failed, e = ev ? idx(ev) : null;
          const b = e != null && e - a <= 250 ? Math.max(e + 10, dep + 20) : dep + 80;
          frameDates(chart, times, ctx, z.base_from, times[Math.min(times.length - 1, b)] || z.until, { fill: 0.6, lead: 0.32 });   // a third in: clear of a setup card at the left
        };
        const publish = () => ctx.onZones?.({ list: zones, focus, checks, tf,
          select: (k) => { if (!zones[k]) return; focus = focus === k ? null : k; if (focus != null) reveal(zones[k]); paint(); publish(); },
          clear: () => { focus = null; paint(); publish(); } });
        fetch(`/api/sd-zones/${ctx.market}/${encodeURIComponent(ctx.symbol)}?tf=${tf}&years=${p.years}`)
          .then((x) => (x.ok ? x.json() : null)).then((r) => {
            if (!r) return setNote(id, "could not load zones");
            zones = r.zones || []; checks = r.checks || {};
            shown = pick(r.close, r.reach);
            const nd = shown.filter((i) => zones[i].kind === "demand").length;
            setNote(id, `${r.note} · showing ${nd} demand, ${shown.length - nd} supply${p.show === "Nearest to price" && r.reach_atr ? ` within ${r.reach_atr} ATR of price` : ""} · close ${px(r.close)}`);
            paint(); publish();
          }).catch(() => setNote(id, "could not load zones"));
        return { series: [], note: "finding zones…", setVisible: (v) => { on = v; paint(); } };
      } },
    // ---- the screener's own trade plan for this symbol (opt-in; nothing is drawn unless added)
    plan: { name: "Screener levels (entry / stop / target)", short: "Plan", cat: "Screener", overlay: true, custom: true,
      label: (p) => `Plan ${p.strategy === "All" ? "all strategies" : p.strategy}`,
      params: { strategy: { type: "select", def: "All", options: STRATEGY_CHOICES }, target: { type: "select", def: "Yes", options: ["Yes", "No"] } },
      plots: [{ k: "entry", t: "Entry", c: "#2962ff" }, { k: "stop", t: "Stop", c: "#ef5350" }, { k: "tgt", t: "Target", c: "#26a69a" }],
      draw({ main, p, col, plans }) {
        // the latest screening run's plan per strategy; only strategies that produced a priced plan draw
        const specs = [];
        for (const l of plans || []) {
          if (p.strategy !== "All" && l.strategy !== p.strategy) continue;
          if (!(l.entry > 0 && l.stop > 0)) continue;
          const tag = SHORT[l.strategy] || l.strategy;
          specs.push({ price: l.entry, color: col("entry"), lineStyle: 0, lineWidth: 1, title: `${tag} entry` });
          specs.push({ price: l.stop, color: col("stop"), lineStyle: 2, lineWidth: 1, title: `${tag} stop` });
          if (p.target === "Yes" && l.target_r > 0)
            specs.push({ price: l.entry + l.target_r * (l.entry - l.stop), color: col("tgt"), lineStyle: 2, lineWidth: 1, title: `${tag} ${(+l.target_r).toFixed(1)}R` });
        }
        let lines = specs.map((o) => main.createPriceLine({ ...o, axisLabelVisible: true }));
        const n = specs.filter((o) => o.title.endsWith("entry")).length;
        return { series: [], note: n ? `${n} plan${n > 1 ? "s" : ""}` : "no screener plan for this symbol",
          setVisible: (on) => { lines.forEach((x) => main.removePriceLine(x)); lines = on ? specs.map((o) => main.createPriceLine({ ...o, axisLabelVisible: true })) : []; } };
      } },
    // ---- chart patterns, detected ON DEMAND by the chart_pattern strategy's own detectors (server side,
    // /api/patterns): one implementation of the rules, drawn exactly as a backtest trade's pattern is.
    // As of the bar at the right edge of the view, so scrolling back shows what was live on that day.
    patterns: { name: "Chart patterns (live detection)", short: "Patterns", cat: "Screener", overlay: true, custom: true,
      label: (p) => `Patterns${p.show === "Best match" ? " · best" : ""}${p.asOf === "Last bar" ? " · last bar" : ""}`,
      params: { show: { type: "select", def: "All live", options: ["All live", "Best match"] },
        asOf: { type: "select", def: "Right edge of the view", options: ["Right edge of the view", "Last bar"] },
        topping: { type: "select", def: "Yes", options: ["Yes", "No"] } },
      plots: [{ k: "bull", t: "Bullish pattern", c: "#ab47bc" }, { k: "bear", t: "Topping pattern", c: "#ef5350" }],  // purple: not the blue of a backtest trade's pattern
      draw({ chart, times, p, col, tf, ctx, id }) {
        if (tf !== "D" || !ctx.annotate) return { series: [], note: "daily charts only", setVisible() {} };
        let on = true, seq = 0, asked, timer = null, shapes = [], history = [], pinned = null, liveNote = "";
        // a pattern picked from the side panel's list replaces the live drawing until it is released
        const paint = () => ctx.annotate(id, on ? (pinned != null ? history[pinned].shapes : shapes) : [], { base: col("bull"), stop: col("bear") });
        // the side panel's Chart patterns tab lists every pattern the detectors saw (patterns_history)
        const publish = () => ctx.onPatterns?.({ list: history, focus: pinned,
          select: (k) => {
            if (!history[k]) return;
            pinned = k; reveal(history[k]); paint(); publish();
            const h = history[k];
            setNote(id, `${h.name} (${h.state}), ${h.start} → ${h.last_seen} · picked from the list`);
          },
          clear: () => { pinned = null; asked = undefined; paint(); publish(); setNote(id, liveNote || "live detection"); kick(); } });
        // frame a picked pattern in the left ~60% of the chart, clear of the panel
        const reveal = (h) => frameDates(chart, times, ctx, h.start, h.last_seen, { fill: 0.6, lead: 0.05 });
        fetch(`/api/patterns-history/${ctx.market}/${encodeURIComponent(ctx.symbol)}?years=5`)
          .then((x) => (x.ok ? x.json() : null)).then((r) => { history = r?.patterns || []; publish(); }).catch(() => {});
        let kick = () => {};
        const load = async (date) => {
          if (pinned != null) return;   // a picked pattern holds the drawing; moving the view does not replace it
          if (date === asked) return;
          asked = date;
          const my = ++seq;
          setNote(id, "detecting…");
          const q = `show=${p.show === "Best match" ? "best" : "all"}&topping=${p.topping === "Yes" ? 1 : 0}${date ? `&date=${date}` : ""}`;
          const r = await fetch(`/api/patterns/${ctx.market}/${encodeURIComponent(ctx.symbol)}?${q}`)
            .then((x) => (x.ok ? x.json() : null)).catch(() => null);
          if (my !== seq) return;   // a newer request (the view moved) owns the drawing
          shapes = (r?.matches || []).flatMap((m) => m.shapes);
          const names = (r?.matches || []).map((m) => `${m.name} (${m.state}${m.tradeable ? ", tradeable" : ""})`);
          liveNote = !r ? "detection failed" : `${r.as_of}: ${names.length ? names.join(" · ") : r.note || "no live pattern"}`;
          setNote(id, liveNote);
          paint();
        };
        if (p.asOf === "Last bar") { kick = () => load(null); load(null); }
        else {
          const edge = () => {
            const r = chart.timeScale().getVisibleLogicalRange();
            return r ? times[Math.min(times.length - 1, Math.max(0, Math.floor(r.to)))] : null;
          };
          kick = () => load(edge());
          chart.timeScale().subscribeVisibleLogicalRangeChange(() => { clearTimeout(timer); timer = setTimeout(() => load(edge()), 250); });
          timer = setTimeout(() => load(edge()), 0);
        }
        return { series: [], note: "detecting…", setVisible: (v) => { on = v; paint(); } };
      } },
    // ---- Weinstein's stages on the TRUE weekly 30-week line, classified ON DEMAND by the
    // stage_analysis strategy's own state machine (server side, /api/stage-analysis): one
    // implementation of the rule, shared with the strategy's gates. Distinct from the Minervini
    // layer's stage bands, which read the daily 150-day as a stand-in — different clocks, and
    // they may disagree. As of the bar at the right edge of the view, like Chart patterns.
    stageweekly: { name: "Stage analysis (Weinstein, 30-week line)", short: "Stages", cat: "Screener", overlay: true, custom: true,
      label: (p) => `Stages · 30-wk${p.asOf === "Last bar" ? " · last bar" : ""}`,
      params: { asOf: { type: "select", def: "Right edge of the view", options: ["Right edge of the view", "Last bar"] },
        line: { type: "select", def: "Show", options: ["Show", "Hide"] } },
      plots: [{ k: "stage1", t: "Stage 1 · basing", c: "#90a4ae" }, { k: "stage2", t: "Stage 2 · advancing", c: "#26a69a" },
        { k: "stage3", t: "Stage 3 · topping", c: "#f59e0b" }, { k: "stage4", t: "Stage 4 · declining", c: "#ef5350" },
        { k: "line", t: "30-week line", c: "#7e57c2" }],
      draw({ chart, times, p, col, tf, ctx, id }) {
        if (tf !== "D" || !ctx.annotate) return { series: [], note: "daily charts only", setVisible() {} };
        let on = true, seq = 0, asked, timer = null, shapes = [], pts = [];
        const NAMES = { 1: "Stage 1 · basing", 2: "Stage 2 · advancing", 3: "Stage 3 · topping", 4: "Stage 4 · declining" };
        const line = chart.addSeries(LC.LineSeries, { color: col("line"), lineWidth: 1, priceLineVisible: false,
          lastValueVisible: false, crosshairMarkerVisible: false }, 0);
        const paint = () => {
          ctx.annotate(id, on ? shapes : [], { stage1: col("stage1"), stage2: col("stage2"), stage3: col("stage3"), stage4: col("stage4") });
          line.setData(on && p.line === "Show" ? pts : []);
        };
        const load = async (date) => {
          if (date === asked) return;
          asked = date;
          const my = ++seq;
          setNote(id, "classifying…");
          const r = await fetch(`/api/stage-analysis/${ctx.market}/${encodeURIComponent(ctx.symbol)}?years=${scanYears(5, ctx)}${date ? `&date=${date}` : ""}`)
            .then((x) => (x.ok ? x.json() : null)).catch(() => null);
          if (my !== seq) return;   // a newer request (the view moved) owns the drawing
          shapes = (r?.stages || []).flatMap((x) => [
            { shape: "box", role: `stage${x.stage}`, bg: true, from: x.from, to: x.to, top: x.high, bottom: x.low, label: "" },
            ...(x.weeks >= 6 ? [{ shape: "text", role: `stage${x.stage}`, at: x.from, price: x.high,
              label: NAMES[x.stage] + (x.ongoing && r?.current?.provisional ? " (forming)" : "") }] : []),
          ]);
          pts = r?.line || [];
          const cur = r?.current;
          setNote(id, !r ? "classification failed"
            : cur?.stage ? `${r.as_of}: Stage ${cur.stage}${cur.provisional ? " · week in progress" : ""} · 30-week line ${cur.line_state} (${cur.line_slope_pct > 0 ? "+" : ""}${cur.line_slope_pct}% / 4 wk)`
              + (r.confirm_weeks ? ` · a stage is confirmed after ${r.confirm_weeks} weeks, so a breakout entry leads this band` : "")
            : r.note || "not enough history");
          paint();
        };
        let kick = () => {};
        if (p.asOf === "Last bar") { kick = () => load(null); load(null); }
        else {
          const edge = () => {
            const r = chart.timeScale().getVisibleLogicalRange();
            return r ? times[Math.min(times.length - 1, Math.max(0, Math.floor(r.to)))] : null;
          };
          kick = () => load(edge());
          chart.timeScale().subscribeVisibleLogicalRangeChange(() => { clearTimeout(timer); timer = setTimeout(() => load(edge()), 250); });
          timer = setTimeout(() => load(edge()), 0);
        }
        return { series: [line], note: "classifying…", setVisible: (v) => { on = v; paint(); } };
      } },
    // Stage 2 stretches from the trend template, and the VCP setups inside them (/api/trend-template:
    // minervini_spec's trend_template_row and bases_live — the strategy's own code, levels and words,
    // never a second copy here). Each setup is one frame with three zones: the uptrend, the base, and
    // for a completed VCP the entry its rules would place (an illustration, replaced by the selected
    // backtest run's real trade when there is one).
    // A TRADE SETUPS layer, not an indicator: `setupsFor` names the strategy whose setups it draws,
    // and that one field does three things — it keys the Trade setups control, it keeps the layer out
    // of the Indicators picker (an indicator is a function of these bars; this runs a strategy), and
    // it tells app.js to stand down that strategy's run layers, since this draws the same setups from
    // the same code in the same words. One per strategy: `setups_<key>`, named from the registry.
    // learnGuide: the Learn guide that teaches this strategy, so the Trade setups picker files the layer
    // under that guide's Strategies category (GUIDE_GROUP in app.js) — the same grouping as Learn.
    setups_minervini: { setupsFor: "minervini", learnGuide: "learn-strat-vcp-sepa", short: "Setups", cat: "Screener", overlay: true, custom: true,
      label: (p) => `${stratName("minervini")}${p.bases === "None" ? "" : p.bases === "Completed VCPs" ? " · VCPs" : " · setups"}`,
      // Stage bands OFF by default. They tint the whole price range of every stage, so on a chart
      // whose subject is the SETUPS they are the loudest thing on it and compete with the frames,
      // levels and labels the study exists to show. Still one click away in the study's settings.
      params: { stages: { type: "select", def: "Hide", options: ["All four", "Stage 2 only", "Hide"] },
        bases: { type: "select", def: "All bases", options: ["All bases", "Completed VCPs", "None"] },
        card: { type: "select", def: "Show", options: ["Show", "Hide"] },
        gaps: { type: "select", def: "None", options: ["None", "After long stretches", "All"] }, minBars: 10 },
      // uptrend is purple, not green: green is already Stage 2, and the two must never be mistaken
      plots: [{ k: "stage1", t: "Stage 1 · basing", c: "#90a4ae" }, { k: "pass", t: "Stage 2 · advancing", c: "#26a69a" },
        { k: "stage3", t: "Stage 3 · topping", c: "#f59e0b" }, { k: "stage4", t: "Stage 4 · declining", c: "#ef5350" },
        { k: "broke", t: "What ended it", c: "#ef5350" },
        { k: "uptrend", t: "Uptrend", c: "#ab47bc" }, { k: "base", t: "Base · VCP", c: "#2962ff" },
        { k: "vcp", t: "VCP setup", c: "#22c55e" }, { k: "cheat", t: "Cheat entry setup", c: "#38bdf8" },
        { k: "miss", t: "Failed setup", c: "#f43f5e" }, { k: "flag", t: "Flag", c: "#f59e0b" },
        { k: "tight", t: "Tight area", c: "#ff9800" },
        { k: "buy", t: "Buy", c: "#26a69a" }, { k: "stop", t: "Stop", c: "#ef5350" }, { k: "target", t: "Target", c: "#4caf50" }],
      draw(args) {
        const { p, col, tf, ctx, def } = args;
        if (tf !== "D" || !ctx.annotate) return { series: [], note: "daily charts only", setVisible() {} };
        const load = async () => {
          const r = await fetch(`/api/setups/${def.setupsFor}/${ctx.market}/${encodeURIComponent(ctx.symbol)}?years=${scanYears(5, ctx)}${ctx.runId ? `&run=${ctx.runId}` : ""}`)
            .then((x) => (x.ok ? x.json() : null));
          if (!r) return null;
          // Weinstein's four stages as background bands (minervini_spec.stage_cycle: the 150-day's slope,
          // the price against it, the swings, and the Trend Template to confirm Stage 2). Each holds until
          // something moves it on, so a dip under the 50-day no longer chops a Stage 2 into pieces.
          const stages = r.stages || [];
          const showOf = (x) => p.stages === "Hide" ? false : p.stages === "Stage 2 only" ? x.stage === 2 : true;
          const NAMES = { 1: "Stage 1 · basing", 2: "Stage 2 · advancing", 3: "Stage 3 · topping", 4: "Stage 4 · declining" };
          // a run's traded setups (the backtest view, or a run picked from the menu) are drawn exactly like every
          // other strategy's: no stage tints behind them -- the bands are this layer's own exploration aid
          let stage = (p.tradedOnly ? [] : stages.filter(showOf)).flatMap((x) => [
            { shape: "box", role: `stage${x.stage}`, bg: true, from: x.from, to: x.to, top: x.high, bottom: x.low, label: "" },
            // a name on any band long enough to read, at its top
            ...(x.bars >= 20 ? [{ shape: "text", role: `stage${x.stage}`, at: x.from, price: x.high, label: NAMES[x.stage] }] : []),
          ]);
          // What ended each Stage 2: the rule that broke it, marked where it broke. Off unless asked for;
          // "After long stretches" keeps those that followed a Stage 2 of minBars sessions or more.
          const ends = stages.map((x, k) => ({ x, prev: stages[k - 1] })).filter(({ x, prev }) => prev && prev.stage === 2 && x.began.startsWith("Stage 2 ended"));
          const shown = p.gaps === "All" ? ends : p.gaps === "After long stretches" ? ends.filter(({ prev }) => prev.bars >= p.minBars) : [];
          stage = stage.concat(shown.map(({ x, prev }) => ({
            shape: "dots", role: "broke", points: [{ at: x.from, price: x.low,
              label: `${x.began.replace("Stage 2 ended: ", "Stage 2 ended — ")} · after ${prev.bars} sessions, ${prev.gain_pct >= 0 ? "+" : ""}${prev.gain_pct}%` }] })));
          const all = r.bases || [];
          return { background: stage, setups: p.bases === "None" ? [] : p.bases === "Completed VCPs" ? all.filter((b) => b.complete) : all,
            note: `${r.note} · ${all.length} setups, ${all.filter((b) => b.complete).length} VCPs · pick one from the lane at the bottom` };
        };
        const keyRows = (YOUNG) => [
          ["frame", col("vcp"), "Green frame", "the selected setup is a VCP (✓)."],
          ["frame", col("cheat"), "Blue frame", "not a VCP, but it triggered a cheat entry: a close through a tight shelf low in the base."],
          ["dashframe", YOUNG, "Grey dashed frame", "too new to judge (?): the stock lacks the history for a 200-day average."],
          ["dashframe", col("miss"), "Rose dashed frame", "the selected setup failed (✗); its header says why."],
          ["frame", col("buy"), "● traded", "a backtest run is selected AND it bought this setup. Its levels are the run's own record; every other setup here is what the rules would have set up on, not a trade."],
          ["pill", col("vcp"), "Lane at the bottom", "every setup, one pill each. Click one to select it."],
          ["arrow", col("uptrend"), "① Uptrend", "the advance into the base. It needs to be strong."],
          ["shade", col("base"), "② Base", "the pullbacks, numbered, with their depths; a VCP's get smaller. ✗ marks the one that broke the rule."],
          ["box", col("tight"), "Tight area", "the quiet end of the base. Its high is the pivot."],
          ["line", col("buy"), "Entry", "buy above the pivot (or at a cheat's close), stop (red), +2R and target (dotted). An illustration of the rules."],
          ["dot", col("flag"), "! Amber", "something the rules pass but worth a look, such as a deep dip inside the uptrend."],
          ["tint", col("stage1"), "Grey-blue band", "Stage 1, basing: after a decline, the price is back above the 150-day (30-week) line or the line has stopped falling. It ends on a breakout above the base, or a breakdown below it."],
          ["tint", col("pass"), "Green band", "Stage 2, advancing: a breakout with the price above a rising 150-day. It lasts until a lower swing low or the 150-day stops rising — not a dip under the 50-day. The Trend Template confirms it, often weeks later."],
          ["tint", col("stage3"), "Amber band", "Stage 3, topping: Stage 2 has ended but the line is not yet falling. Only a breakout above the top returns it to Stage 2."],
          ["tint", col("stage4"), "Red band", "Stage 4, declining: the 150-day is falling and the price is below it."],
        ];
        return setupLayer({ ...args, keyRows, load,
          roles: { stage1: col("stage1"), stage2: col("pass"), stage3: col("stage3"), stage4: col("stage4"), broke: col("broke") } });
      } },
    // Generic Trade setups layers: the strategy's own evaluate / build_plans / classify run bar by bar on
    // the server (strategies/live_setups.py) and drawn by the same machinery as Minervini's. One entry per
    // strategy, as the registry names them; `learnGuide` files it under Learn's category for it.
    setups_breakout: genericSetups("breakout", "learn-strat-darvas", { base: ["Consolidation", "#2962ff"], pivot: ["Pivot", "#ff9800"] }),
    setups_donchian: genericSetups("donchian", "learn-strat-channel-breakout", { base: ["Channel", "#2962ff"], tight: ["Coil zone", "#ff9800"],
      pivot: ["Channel high", "#26a69a"], support: ["Exit channel", "#ef5350"] }),
    setups_trend_pullback: genericSetups("trend_pullback", "learn-strat-pullback-ma", { contraction: ["Pullback", "#2962ff"],
      tight: ["30-60% retracement", "#ff9800"], pivot: ["H, the resumption level", "#26a69a"], support: ["Prior swing low", "#ef5350"],
      base: ["Tight base", "#7e57c2"] }),
    // chart patterns: the strategy's own chart_anatomy draws each pattern (its points, touches and trigger)
    setups_stage_analysis: genericSetups("stage_analysis", "learn-strat-stage-analysis", { uptrend: ["30-week line", "#ff9800"],
      base: ["Stage 1 base", "#2962ff"], pivot: ["Resistance", "#26a69a"] }),
    setups_rs_leaders: genericSetups("rs_leaders", "learn-strat-rs-leaders", { base: ["Flat base", "#2962ff"], pivot: ["Pivot", "#ff9800"] }),
    setups_chart_pattern: genericSetups("chart_pattern", "learn-strat-flags", { base: ["Pattern", "#ab47bc"],
      pivot: ["Trigger", "#26a69a"], support: ["Support", "#ef5350"] }),
    vol: { name: "Volume", short: "Vol", cat: "Volume", overlay: true, volume: true, needsVolume: true, params: { maLength: 20 },
      plots: [{ k: "vol", t: "Volume", c: "#26a69a", s: "hist" }, { k: "ma", t: "Volume MA", c: "#2196f3" }],
      calc: (b, p) => ({ vol: b.V, ma: sma(b.V, p.maLength), _colors: { vol: b.C.map((c, i) => (c >= b.O[i] ? "rgba(38,166,154,.45)" : "rgba(239,83,80,.45)")) } }) },
    rsi: { name: "Relative Strength Index", short: "RSI", cat: "Momentum", params: { length: 14, source: SRC }, levels: [70, 50, 30], plots: [{ k: "rsi", c: "#7e57c2" }],
      calc: (b, p) => ({ rsi: rsi(source(b, p.source), p.length) }) },
    macd: { name: "MACD", short: "MACD", cat: "Momentum", params: { fast: 12, slow: 26, signal: 9, source: SRC }, levels: [0],
      plots: [{ k: "hist", t: "Histogram", c: "#26a69a", s: "hist" }, { k: "macd", t: "MACD", c: "#2962ff" }, { k: "signal", t: "Signal", c: "#ff6d00" }],
      calc: (b, p) => {
        const s = source(b, p.source), m = zip((f, l) => f - l, ema(s, p.fast), ema(s, p.slow)), sig = ema(m, p.signal), h = zip((x, y) => x - y, m, sig);
        const colors = h.map((v, i) => (v == null ? null : v >= 0 ? (h[i - 1] != null && v < h[i - 1] ? "#b2dfdb" : "#26a69a") : (h[i - 1] != null && v > h[i - 1] ? "#ffcdd2" : "#ff5252")));
        return { macd: m, signal: sig, hist: h, _colors: { hist: colors } };
      } },
    stoch: { name: "Stochastic", short: "Stoch", cat: "Momentum", params: { kLength: 14, kSmoothing: 3, dSmoothing: 3 }, levels: [80, 20],
      plots: [{ k: "k", t: "%K", c: "#2962ff" }, { k: "d", t: "%D", c: "#ff6d00" }],
      calc: (b, p) => { const hh = highest(b.H, p.kLength), ll = lowest(b.L, p.kLength);
        const k = sma(zip((c, h, l) => (h === l ? 50 : (100 * (c - l)) / (h - l)), b.C, hh, ll), p.kSmoothing); return { k, d: sma(k, p.dSmoothing) }; } },
    stochrsi: { name: "Stochastic RSI", short: "Stoch RSI", cat: "Momentum", params: { rsiLength: 14, stochLength: 14, k: 3, d: 3 }, levels: [80, 20],
      plots: [{ k: "k", t: "K", c: "#2962ff" }, { k: "d", t: "D", c: "#ff6d00" }],
      calc: (b, p) => { const r = rsi(b.C, p.rsiLength), hh = highest(r, p.stochLength), ll = lowest(r, p.stochLength);
        const k = sma(zip((x, h, l) => (h === l ? 50 : (100 * (x - l)) / (h - l)), r, hh, ll), p.k); return { k, d: sma(k, p.d) }; } },
    cci: { name: "Commodity Channel Index", short: "CCI", cat: "Momentum", params: { length: 20 }, levels: [100, 0, -100], plots: [{ k: "cci", c: "#2962ff" }],
      calc: (b, p) => { const tp = source(b, "hlc3"), m = sma(tp, p.length), md = win(tp, p.length, (w) => { const a = w.reduce((x, y) => x + y, 0) / w.length; return w.reduce((x, y) => x + Math.abs(y - a), 0) / w.length; });
        return { cci: zip((t, mm, d) => (d ? (t - mm) / (0.015 * d) : 0), tp, m, md) }; } },
    wpr: { name: "Williams %R", short: "%R", cat: "Momentum", params: { length: 14 }, levels: [-20, -50, -80], plots: [{ k: "r", c: "#7e57c2" }],
      calc: (b, p) => ({ r: zip((c, h, l) => (h === l ? -50 : (-100 * (h - c)) / (h - l)), b.C, highest(b.H, p.length), lowest(b.L, p.length)) }) },
    roc: { name: "Rate of Change", short: "ROC", cat: "Momentum", params: { length: 9 }, levels: [0], plots: [{ k: "roc", c: "#2962ff" }],
      calc: (b, p) => ({ roc: b.C.map((c, i) => (i < p.length ? null : (100 * (c - b.C[i - p.length])) / b.C[i - p.length])) }) },
    mom: { name: "Momentum", short: "Mom", cat: "Momentum", params: { length: 10 }, levels: [0], plots: [{ k: "mom", c: "#2962ff" }],
      calc: (b, p) => ({ mom: b.C.map((c, i) => (i < p.length ? null : c - b.C[i - p.length])) }) },
    // -- where the close sits in a recent range or band
    bbpct: { name: "Bollinger %B", short: "%B", cat: "Momentum", params: { length: 20, mult: 2 }, levels: [1, 0.5, 0], plots: [{ k: "pb", c: "#2962ff" }],
      calc: (b, p) => { const m = sma(b.C, p.length), sd = stdev(b.C, p.length);
        return { pb: zip((c, x, d) => (d ? (c - (x - p.mult * d)) / (2 * p.mult * d) : null), b.C, m, sd) }; } },
    uo: { name: "Ultimate Oscillator", short: "UO", cat: "Momentum", params: { fast: 7, middle: 14, slow: 28 }, levels: [70, 50, 30], plots: [{ k: "uo", c: "#7e57c2" }],
      calc: (b, p) => {
        // buying pressure = close − the lower of (low, previous close), over the true range, on three lengths weighted 4:2:1
        const lo = b.L.map((l, i) => (i ? Math.min(l, b.C[i - 1]) : null)), hi = b.H.map((h, i) => (i ? Math.max(h, b.C[i - 1]) : null));
        const bp = zip((c, l) => c - l, b.C, lo), tr = zip((h, l) => h - l, hi, lo), avg = (n) => zip((x, y) => (y ? x / y : null), sum(bp, n), sum(tr, n));
        return { uo: zip((a, m, s) => (100 * (4 * a + 2 * m + s)) / 7, avg(p.fast), avg(p.middle), avg(p.slow)) };
      } },
    crsi: { name: "Connors RSI", short: "CRSI", cat: "Momentum", params: { rsiLength: 3, streakLength: 2, rankLength: 100 }, levels: [90, 50, 10], plots: [{ k: "crsi", c: "#7e57c2" }],
      calc: (b, p) => {
        // the average of: a 3-day RSI; a 2-day RSI of the up/down streak; the % of the last 100 one-day changes below today's
        const n = b.C.length, streak = nul(n), rank = nul(n), chg = roc(b.C, 1);
        let s = 0;
        for (let i = 1; i < n; i++) { const d = b.C[i] - b.C[i - 1]; s = d > 0 ? (s > 0 ? s + 1 : 1) : d < 0 ? (s < 0 ? s - 1 : -1) : 0; streak[i] = s; }
        for (let i = p.rankLength; i < n; i++) {
          if (chg[i] == null) continue;
          let below = 0; for (let j = i - p.rankLength; j < i; j++) if (chg[j] != null && chg[j] < chg[i]) below++;
          rank[i] = (100 * below) / p.rankLength;
        }
        return { crsi: zip((a, c, r) => (a + c + r) / 3, rsi(b.C, p.rsiLength), rsi(streak, p.streakLength), rank) };
      } },
    bop: { name: "Balance of Power", short: "BOP", cat: "Momentum", params: { length: 14 }, levels: [0], plots: [{ k: "bop", c: "#2962ff" }],
      calc: (b, p) => ({ bop: sma(b.C.map((c, i) => (b.O[i] == null || b.H[i] === b.L[i] ? 0 : (c - b.O[i]) / (b.H[i] - b.L[i]))), p.length) }) },
    // -- how fast the price is changing
    distma: { name: "Distance from Moving Average", short: "Dist MA", cat: "Momentum", levels: [0], plots: [{ k: "d", c: "#2962ff" }],
      params: { length: 50, unit: { type: "select", def: "%", options: ["%", "ATR"] }, atrLength: 14 },
      calc: (b, p) => { const m = sma(b.C, p.length);
        if (p.unit === "ATR") { const a = rma(trueRange(b.H, b.L, b.C), p.atrLength); return { d: zip((c, x, r) => (r ? (c - x) / r : null), b.C, m, a) }; }
        return { d: zip((c, x) => 100 * (c / x - 1), b.C, m) }; } },
    ppo: { name: "Percentage Price Oscillator", short: "PPO", cat: "Momentum", params: { fast: 12, slow: 26, signal: 9 }, levels: [0],
      plots: [{ k: "hist", t: "Histogram", c: "#26a69a", s: "hist" }, { k: "ppo", t: "PPO", c: "#2962ff" }, { k: "signal", t: "Signal", c: "#ff6d00" }],
      calc: (b, p) => { const v = zip((f, s) => (s ? (100 * (f - s)) / s : null), ema(b.C, p.fast), ema(b.C, p.slow)), sig = ema(v, p.signal);
        return { ppo: v, signal: sig, hist: zip((x, y) => x - y, v, sig) }; } },
    trix: { name: "TRIX", short: "TRIX", cat: "Momentum", params: { length: 15, signal: 9 }, levels: [0],
      plots: [{ k: "trix", t: "TRIX", c: "#2962ff" }, { k: "signal", t: "Signal", c: "#ff6d00" }],
      calc: (b, p) => { const t = roc(ema(ema(ema(b.C, p.length), p.length), p.length), 1); return { trix: t, signal: ema(t, p.signal) }; } },
    tsi: { name: "True Strength Index", short: "TSI", cat: "Momentum", params: { long: 25, short: 13, signal: 13 }, levels: [0],
      plots: [{ k: "tsi", t: "TSI", c: "#2962ff" }, { k: "signal", t: "Signal", c: "#ff6d00" }],
      calc: (b, p) => {
        const ch = b.C.map((c, i) => (i ? c - b.C[i - 1] : null));
        const num = ema(ema(ch, p.long), p.short), den = ema(ema(ch.map((x) => (x == null ? null : Math.abs(x))), p.long), p.short);
        const t = zip((x, y) => (y ? (100 * x) / y : null), num, den);
        return { tsi: t, signal: ema(t, p.signal) };
      } },
    kst: { name: "Know Sure Thing (KST)", short: "KST", cat: "Momentum", params: { signal: 9 }, levels: [0],
      plots: [{ k: "kst", t: "KST", c: "#2962ff" }, { k: "signal", t: "Signal", c: "#ff6d00" }],
      calc: (b, p) => { const k = rocSum(b.C, [[10, 10, 1], [15, 10, 2], [20, 10, 3], [30, 15, 4]]); return { kst: k, signal: sma(k, p.signal) }; } },
    specialk: { name: "Pring's Special K", short: "Special K", cat: "Momentum", params: {}, levels: [0], plots: [{ k: "sk", c: "#2962ff" }],
      // twelve smoothed rates of change, from two weeks to about two years — the daily formula as Pring published it
      calc: (b) => ({ sk: rocSum(b.C, [[10, 10, 1], [15, 10, 2], [20, 10, 3], [30, 15, 4], [40, 50, 1], [65, 65, 2], [75, 75, 3], [100, 100, 4],
        [195, 130, 1], [265, 130, 2], [390, 130, 3], [530, 195, 4]]) }) },
    pmo: { name: "Price Momentum Oscillator (DecisionPoint)", short: "PMO", cat: "Momentum", params: { first: 35, second: 20, signal: 10 }, levels: [0],
      plots: [{ k: "pmo", t: "PMO", c: "#2962ff" }, { k: "signal", t: "Signal", c: "#ff6d00" }],
      // the 1-day % change, smoothed twice with DecisionPoint's "custom" average (multiplier 2/n, not 2/(n+1)), times 10 in between
      calc: (b, p) => { const s1 = smooth(roc(b.C, 1), p.first, 2 / p.first).map((v) => (v == null ? null : 10 * v)), pm = smooth(s1, p.second, 2 / p.second);
        return { pmo: pm, signal: ema(pm, p.signal) }; } },
    dpo: { name: "Detrended Price Oscillator", short: "DPO", cat: "Momentum", params: { length: 20 }, levels: [0], plots: [{ k: "dpo", c: "#2962ff" }],
      // the close (n/2 + 1) bars ago less today's n-bar average: the average is centred on that old close, so the trend drops out
      calc: (b, p) => { const m = sma(b.C, p.length), back = Math.floor(p.length / 2) + 1;
        return { dpo: m.map((x, i) => (x == null || i < back ? null : b.C[i - back] - x)) }; } },
    mfi: { name: "Money Flow Index", short: "MFI", cat: "Volume", needsVolume: true, params: { length: 14 }, levels: [80, 20], plots: [{ k: "mfi", c: "#7e57c2" }],
      calc: (b, p) => {
        const tp = source(b, "hlc3"), pos = tp.map((t, i) => (i && t > tp[i - 1] ? t * b.V[i] : 0)), neg = tp.map((t, i) => (i && t < tp[i - 1] ? t * b.V[i] : 0));
        return { mfi: zip((ps, ng) => (ng === 0 ? 100 : 100 - 100 / (1 + ps / ng)), sum(pos, p.length), sum(neg, p.length)) };
      } },
    obv: { name: "On Balance Volume", short: "OBV", cat: "Volume", needsVolume: true, volumeFormat: true, params: {}, plots: [{ k: "obv", c: "#2962ff" }],
      calc: (b) => { let s = 0; return { obv: b.C.map((c, i) => (s += i === 0 ? 0 : c > b.C[i - 1] ? b.V[i] : c < b.C[i - 1] ? -b.V[i] : 0)) }; } },
    cmf: { name: "Chaikin Money Flow", short: "CMF", cat: "Volume", needsVolume: true, params: { length: 20 }, levels: [0], plots: [{ k: "cmf", c: "#43a047" }],
      calc: (b, p) => { const mfv = b.C.map((c, i) => (b.H[i] === b.L[i] ? 0 : (((c - b.L[i]) - (b.H[i] - c)) / (b.H[i] - b.L[i])) * b.V[i]));
        return { cmf: zip((x, y) => (y ? x / y : 0), sum(mfv, p.length), sum(b.V, p.length)) }; } },
    adl: { name: "Accumulation/Distribution Line", short: "A/D", cat: "Volume", needsVolume: true, volumeFormat: true, params: {}, plots: [{ k: "ad", c: "#2962ff" }],
      calc: (b) => ({ ad: adLine(b) }) },
    chosc: { name: "Chaikin Oscillator", short: "Chaikin Osc", cat: "Volume", needsVolume: true, volumeFormat: true, params: { fast: 3, slow: 10 }, levels: [0],
      plots: [{ k: "co", c: "#43a047" }],
      calc: (b, p) => { const ad = adLine(b); return { co: zip((x, y) => x - y, ema(ad, p.fast), ema(ad, p.slow)) }; } },
    force: { name: "Force Index", short: "Force", cat: "Volume", needsVolume: true, volumeFormat: true, params: { length: 13 }, levels: [0], plots: [{ k: "fi", c: "#f23645" }],
      calc: (b, p) => ({ fi: ema(b.C.map((c, i) => (i ? (c - b.C[i - 1]) * (b.V[i] || 0) : null)), p.length) }) },
    eom: { name: "Ease of Movement", short: "EOM", cat: "Volume", needsVolume: true, params: { length: 14, divisor: 10000 }, levels: [0], plots: [{ k: "eom", c: "#2962ff" }],
      // how far the bar's midpoint moved, times its range, per unit of volume: a big move on light volume scores high
      calc: (b, p) => ({ eom: sma(b.C.map((_, i) => (i && b.V[i] ? (p.divisor * ((b.H[i] + b.L[i]) / 2 - (b.H[i - 1] + b.L[i - 1]) / 2) * (b.H[i] - b.L[i])) / b.V[i] : null)), p.length) }) },
    atr: { name: "Average True Range", short: "ATR", cat: "Volatility", params: { length: 14 }, plots: [{ k: "atr", c: "#f23645" }],
      calc: (b, p) => ({ atr: rma(trueRange(b.H, b.L, b.C), p.length) }) },
    atrp: { name: "ATR % of price", short: "ATR%", cat: "Volatility", params: { length: 14 }, plots: [{ k: "atrp", c: "#f23645" }],
      calc: (b, p) => ({ atrp: zip((a, c) => (100 * a) / c, rma(trueRange(b.H, b.L, b.C), p.length), b.C) }) },
    bbw: { name: "Bollinger BandWidth", short: "BBW", cat: "Volatility", params: { length: 20, mult: 2 }, plots: [{ k: "bbw", c: "#2962ff" }],
      calc: (b, p) => { const m = sma(b.C, p.length), sd = stdev(b.C, p.length); return { bbw: zip((x, d) => (x ? (2 * p.mult * d) / x : null), m, sd) }; } },
    stdev: { name: "Standard Deviation", short: "StDev", cat: "Volatility", params: { length: 20 }, plots: [{ k: "sd", c: "#2962ff" }],
      calc: (b, p) => ({ sd: stdev(b.C, p.length) }) },
    hv: { name: "Historical Volatility (annualised %)", short: "HV", cat: "Volatility", params: { length: 20, periods: 252 }, plots: [{ k: "hv", c: "#f23645" }],
      calc: (b, p) => ({ hv: stdev(b.C.map((c, i) => (i && c > 0 && b.C[i - 1] > 0 ? Math.log(c / b.C[i - 1]) : null)), p.length)
        .map((v) => (v == null ? null : 100 * v * Math.sqrt(p.periods))) }) },
    mass: { name: "Mass Index", short: "Mass", cat: "Volatility", params: { length: 9, sum: 25 }, levels: [27, 26.5], plots: [{ k: "mi", c: "#2962ff" }],
      // the day's range smoothed once ÷ smoothed twice, summed over 25 bars: it rises when ranges widen fast
      calc: (b, p) => { const e1 = ema(zip((h, l) => h - l, b.H, b.L), p.length), e2 = ema(e1, p.length);
        return { mi: sum(zip((x, y) => (y ? x / y : null), e1, e2), p.sum) }; } },
    ulcer: { name: "Ulcer Index", short: "UI", cat: "Volatility", params: { length: 14 }, plots: [{ k: "ui", c: "#f23645" }],
      // the root-mean-square of the % drop below the highest close of the last n bars: only declines count
      calc: (b, p) => { const dd = zip((c, h) => (100 * (c - h)) / h, b.C, highest(b.C, p.length));
        return { ui: win(dd, p.length, (w) => Math.sqrt(w.reduce((x, y) => x + y * y, 0) / w.length)) }; } },
    squeeze: { name: "TTM Squeeze", short: "Squeeze", cat: "Volatility", params: { length: 20, bbMult: 2, kcMult: 1.5 }, levels: [0],
      plots: [{ k: "mom", t: "Momentum", c: "#26a69a", s: "hist" }, { k: "on", t: "Squeeze on", c: "#f23645", s: "dots" }, { k: "off", t: "Squeeze off", c: "#089981", s: "dots" }],
      calc: (b, p) => {
        // on while the Bollinger Bands (2 sd) sit inside a Keltner channel (1.5 ATR) around the same average;
        // the histogram is the linear-regression value of the close's distance from the range midpoint
        const n = p.length, m = sma(b.C, n), sd = stdev(b.C, n), a = rma(trueRange(b.H, b.L, b.C), n);
        const sq = zip((x, d, r) => p.bbMult * d < p.kcMult * r, m, sd, a);
        const mid = zip((h, l, x) => ((h + l) / 2 + x) / 2, highest(b.H, n), lowest(b.L, n), m);
        const mom = linreg(zip((c, x) => c - x, b.C, mid), n);
        const colors = mom.map((v, i) => (v == null ? null : v >= 0 ? (mom[i - 1] != null && v < mom[i - 1] ? "#b2dfdb" : "#26a69a") : (mom[i - 1] != null && v > mom[i - 1] ? "#ffcdd2" : "#ff5252")));
        return { mom, on: sq.map((s) => (s === true ? 0 : null)), off: sq.map((s) => (s === false ? 0 : null)), _colors: { mom: colors } };
      } },
    adx: { name: "Directional Movement Index (ADX)", short: "DMI", cat: "Trend", params: { length: 14 }, levels: [25],
      plots: [{ k: "adx", t: "ADX", c: "#ff6d00", w: 2 }, { k: "pdi", t: "+DI", c: "#2962ff" }, { k: "mdi", t: "−DI", c: "#f23645" }],
      calc: (b, p) => {
        const n = b.C.length, pdm = nul(n), mdm = nul(n);
        for (let i = 1; i < n; i++) { const u = b.H[i] - b.H[i - 1], d = b.L[i - 1] - b.L[i]; pdm[i] = u > d && u > 0 ? u : 0; mdm[i] = d > u && d > 0 ? d : 0; }
        const tr = trueRange(b.H, b.L, b.C); tr[0] = null;
        const atr = rma(tr, p.length), pdi = zip((x, a) => (a ? (100 * x) / a : 0), rma(pdm, p.length), atr), mdi = zip((x, a) => (a ? (100 * x) / a : 0), rma(mdm, p.length), atr);
        return { pdi, mdi, adx: rma(zip((x, y) => (x + y ? (100 * Math.abs(x - y)) / (x + y) : 0), pdi, mdi), p.length) };
      } },
    aroon: { name: "Aroon", short: "Aroon", cat: "Trend", params: { length: 14 }, plots: [{ k: "up", t: "Up", c: "#ff6d00" }, { k: "down", t: "Down", c: "#2962ff" }],
      calc: (b, p) => {
        const n = p.length, f = (a, cmp) => a.map((_, i) => { if (i < n) return null; let best = i - n; for (let j = i - n; j <= i; j++) if (cmp(a[j], a[best])) best = j; return (100 * (n - (i - best))) / n; });
        return { up: f(b.H, (x, y) => x >= y), down: f(b.L, (x, y) => x <= y) };
      } },
    aroonosc: { name: "Aroon Oscillator", short: "Aroon Osc", cat: "Trend", params: { length: 14 }, levels: [50, 0, -50], plots: [{ k: "osc", c: "#ff6d00" }],
      calc: (b, p) => { const a = CATALOG.aroon.calc(b, p); return { osc: zip((u, d) => u - d, a.up, a.down) }; } },
    rs: { name: "Relative Strength vs index", short: "RS", cat: "Trend", needsBench: true, params: { maLength: 50 }, levels: [100],
      plots: [{ k: "rs", t: "RS", c: "#2962ff", w: 2 }, { k: "ma", t: "RS MA", c: "#ff9800" }],
      calc: (b, p, ctx) => {
        if (!ctx.bench) return { rs: nul(b.C.length), ma: nul(b.C.length) };
        // carry the last index close over dates the index didn't trade, so one calendar
        // mismatch doesn't knock out the moving average for the next maLength bars
        let last = null;
        const raw = b.C.map((c, i) => { const x = ctx.bench.get(ctx.times[i]); if (x) last = x; return last ? c / last : null; });
        const base = raw.find((v) => v != null), rs = raw.map((v) => (v == null ? null : (100 * v) / base));
        return { rs, ma: sma(rs, p.maLength) };
      } },
  };
  const PARAM_LABELS = { length: "Length", source: "Source", mult: "StdDev / multiplier", atrLength: "ATR length", maLength: "MA length",
    fast: "Fast length", slow: "Slow length", signal: "Signal smoothing", kLength: "%K length", kSmoothing: "%K smoothing", dSmoothing: "%D smoothing",
    rsiLength: "RSI length", stochLength: "Stochastic length", k: "K smoothing", d: "D smoothing", factor: "Factor", start: "Start", increment: "Increment",
    maximum: "Maximum", left: "Left bars", right: "Right bars", labels: "Labels", zigzag: "Zig-zag line", timeframe: "Pivots timeframe",
    back: "Number of periods back", lookback: "Lookback (bars)", tolerance: "Merge tolerance (× ATR)", minTouches: "Minimum touches",
    maxLevels: "Maximum levels", method: "Type", strategy: "Strategy", target: "Show target", type: "MA type", length1: "MA #1 length", length2: "MA #2 length", length3: "MA #3 length", length4: "MA #4 length",
    conversion: "Conversion line length", base: "Base line length", spanB: "Leading span B length",
    percent: "Envelope %", jaw: "Jaw length", jawShift: "Jaw offset", teeth: "Teeth length", teethShift: "Teeth offset", lips: "Lips length",
    lipsShift: "Lips offset", unit: "Measure in", middle: "Middle length", long: "Long length", short: "Short length", streakLength: "Streak RSI length",
    rankLength: "Percent-rank length", first: "First smoothing", second: "Second smoothing", periods: "Bars per year", sum: "Sum length",
    bbMult: "Bollinger multiplier", kcMult: "Keltner multiplier", deviation: "Reversal %", divisor: "Volume divisor",
    minBars: "Label stretches of at least (bars)", label: "Label", gaps: "Label gaps" };
  const CATS = ["Screener", "Moving averages", "Bands & channels", "Support & resistance", "Trend", "Momentum", "Volatility", "Volume"];
  const MA_COLORS = ["#f5a623", "#2196f3", "#e040fb", "#ffeb3b", "#00bcd4", "#ff5252", "#8bc34a"];

  // ------------------------------------------------------------- active list
  const uid = () => Math.random().toString(36).slice(2, 8);
  function make(type, params = {}, colors = {}) {
    const def = CATALOG[type], p = {};
    for (const [k, v] of Object.entries(def.params)) p[k] = typeof v === "object" ? v.def : v;
    return { id: uid(), type, params: { ...p, ...params }, colors, hidden: false };
  }
  function load() {
    let list = store.get("chartStudies", null);
    if (!list) {  // first run: carry over the old fixed toggles
      const old = store.get("chartPrefs", { sma20: true, sma50: true, sma200: true, volume: true, rsi: true });
      list = [];
      if (old.sma20 !== false) list.push(make("sma", { length: 20 }, { ma: "#f5a623" }));
      if (old.sma50 !== false) list.push(make("sma", { length: 50 }, { ma: "#2196f3" }));
      list.push(make("sma", { length: 150 }, { ma: "#8bc34a" }));
      if (old.sma200 !== false) list.push(make("sma", { length: 200 }, { ma: "#e040fb" }));
      if (old.ema20) list.push(make("ema", { length: 20 }));
      if (old.volume !== false) list.push(make("vol"));
      if (old.rsi !== false) list.push(make("rsi"));
      store.set("chartStudies", list);
    }
    // the S/R indicator's default moved to key levels only (2026-10-21): a copy saved while "All graded
    // levels" was the default follows the new default once; a choice made after that is kept
    let srMoved = false;
    for (const s of list) {
      if (s.type === "sr" && !s.srKeyDefault) { s.params.levels = "Key levels"; s.srKeyDefault = 1; srMoved = true; }
    }
    if (srMoved) store.set("chartStudies", list);
    // the 150-day joined the defaults (2026-10-29): the Trend Template reads the 50, 150 and 200, and a
    // chart without the 150 leaves two of its conditions to guesswork. Added ONCE, among the saved
    // moving averages in length order, behind a marker, so removing it afterwards sticks
    if (!store.get("sma150Added2026", false)) {
      if (!list.some((s) => s.type === "sma" && Number(s.params.length) === 150)) {
        const smas = list.map((s, i) => [s, i]).filter(([s]) => s.type === "sma");
        const longer = smas.find(([s]) => Number(s.params.length) > 150);
        const at = longer ? longer[1] : smas.length ? smas[smas.length - 1][1] + 1 : list.length;
        list.splice(at, 0, make("sma", { length: 150 }, { ma: "#8bc34a" }));
      }
      store.set("sma150Added2026", true);
      store.set("chartStudies", list);
    }
    // the layer moved out of Indicators and was rekeyed by strategy (2026-10-17); carry the saved
    // instance across rather than silently dropping it, since load() discards unknown types
    let moved = false;
    for (const s of list) if (s.type === "trend_template") { s.type = "setups_minervini"; moved = true; }
    // Stage bands became off-by-default (2026-10-19), but a study already on someone's chart keeps
    // the value `make()` snapshotted when it was added, so the new default would never reach it.
    // Flipped ONCE, behind a marker: without the marker this would re-hide the bands every reload
    // and there would be no way to turn them back on.
    if (!store.get("stageBandsHidden2026", false)) {
      for (const s of list) if (s.type === "setups_minervini" && s.params?.stages === "All four") {
        s.params.stages = "Hide"; moved = true;
      }
      store.set("stageBandsHidden2026", true);
    }
    if (moved) save(list);
    return list.filter((s) => CATALOG[s.type]);
  }
  const save = (list) => store.set("chartStudies", list);
  function add(type) {
    const list = load(), s = make(type);
    if (CATALOG[type].cat === "Moving averages") {  // give each new MA its own colour
      const used = list.map((x) => x.colors.ma).filter(Boolean);
      s.colors.ma = MA_COLORS.find((c) => !used.includes(c)) || MA_COLORS[list.length % MA_COLORS.length];
    }
    list.push(s); save(list); return s;
  }
  const catName = (type) => (CATALOG[type].setupsFor ? stratName(CATALOG[type].setupsFor) : CATALOG[type].name);
  const label = (s) => {
    if (CATALOG[s.type].label) return CATALOG[s.type].label(s.params);
    const d = CATALOG[s.type], vals = Object.entries(s.params).filter(([k]) => k !== "source" || s.params.source !== "close").map(([, v]) => v);
    return `${d.short}${vals.length ? " " + vals.join(" ") : ""}`;
  };

  // ------------------------------------------------------------- rendering
  /** Add every active study to `chart`. Returns entries for the legend. */
  function render({ chart, times, bars, ctx, skip = () => false, extra = [] }) {
    const out = [];
    let pane = 1;
    const fmtV = (s, v) => (v == null ? "" : CATALOG[s.type].volumeFormat || CATALOG[s.type].volume ? compact(v) : Math.abs(v) >= 1000 ? v.toFixed(0) : Math.abs(v) >= 1 ? v.toFixed(2) : v.toPrecision(3));
    for (const s of [...load().filter((x) => !skip(x, CATALOG[x.type])), ...extra]) {
      const def = CATALOG[s.type];
      if ((def.needsVolume && !hasVolume(bars)) || (def.needsBench && !ctx.bench)) { out.push({ s, def, skipped: true, pane: def.overlay ? 0 : null }); continue; }
      if (def.custom) {
        const col = (k) => s.colors[k] || def.plots.find((x) => x.k === k).c;
        const r = def.draw({ chart, main: ctx.main, times, bars, p: s.params, col, tf: ctx.tf, plans: ctx.plans, ctx, id: s.id, def });
        if (s.hidden) r.setVisible(false);
        out.push({ s, def, pane: 0, series: r.series || [], vals: {}, fmt: () => "", note: r.note, setVisible: r.setVisible });
        continue;
      }
      const p = def.overlay ? 0 : pane++;
      const vals = def.calc(bars, s.params, { ...ctx, times });
      const series = [];
      def.plots.forEach((pl, j) => {
        const color = s.colors[pl.k] || pl.c;
        const common = { priceLineVisible: false, lastValueVisible: !def.overlay || def.volume, visible: !s.hidden, title: "" };
        let ser;
        if (pl.s === "hist") {
          ser = chart.addSeries(LC.HistogramSeries, { ...common, color, ...(def.volume ? { priceScaleId: "vol", priceFormat: { type: "volume" }, lastValueVisible: false } : {}) }, p);
        } else {
          ser = chart.addSeries(LC.LineSeries, { ...common, color, lineWidth: pl.w || (def.overlay ? 1 : 1.5), crosshairMarkerVisible: !def.overlay,
            ...(pl.s === "dots" ? { lineVisible: false, pointMarkersVisible: true, pointMarkersRadius: 1.6 } : {}),
            ...(def.volume ? { priceScaleId: "vol", lastValueVisible: false } : {}),
            ...(def.volumeFormat ? { priceFormat: { type: "volume" } } : {}) }, p);
        }
        const cols = vals._colors && vals._colors[pl.k];
        const arr = vals[pl.k] || [];
        ser.setData(times.map((t, i) => (arr[i] == null ? { time: t } : cols && cols[i] ? { time: t, value: arr[i], color: cols[i] } : { time: t, value: arr[i] })));
        if (j === 0 && def.levels) def.levels.forEach((lv) => ser.createPriceLine({ price: lv, color: "#4a4f5e", lineStyle: 2, lineWidth: 1, axisLabelVisible: false }));
        series.push(ser);
      });
      if (def.volume) chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
      out.push({ s, def, pane: p, series, vals, fmt: (v) => fmtV(s, v) });
    }
    fitPriceScale(out);
    return out;
  }

  /** How much of the price pane the candles may use.
   *
   *  Lightweight Charts defaults to `{top: 0.2, bottom: 0.1}` -- 30% of the pane spent on empty
   *  margin -- and nothing here ever overrode it for the main scale, so a chart gave away almost
   *  a third of its height. 6% above and below is enough to keep a wick off the frame.
   *
   *  A volume overlay draws in the bottom 20% on its own scale, independent of this one, so when
   *  one is on the bottom margin opens up to clear it. That is not a loss: today the default 10%
   *  already let candles run INTO the volume band.
   */
  function fitPriceScale(rendered) {
    const hasVolume = rendered.some((r) => r.def.volume && !r.s.hidden);
    try {
      chart.priceScale("right").applyOptions({
        scaleMargins: { top: 0.06, bottom: hasVolume ? 0.22 : 0.06 },
      });
    } catch {}
  }
  const compact = (v) => { const a = Math.abs(v); return (a >= 1e9 ? (v / 1e9).toFixed(2) + "B" : a >= 1e6 ? (v / 1e6).toFixed(2) + "M" : a >= 1e3 ? (v / 1e3).toFixed(1) + "K" : v.toFixed(0)); };

  const BTN = {
    eye: '<svg viewBox="0 0 20 20"><path d="M1.5 10S5 4.2 10 4.2 18.5 10 18.5 10 15 15.8 10 15.8 1.5 10 1.5 10z"/><circle cx="10" cy="10" r="2.6"/></svg>',
    eyeOff: '<svg viewBox="0 0 20 20"><path d="M3 3l14 14M8 4.5A8 8 0 0 1 10 4.2c5 0 8.5 5.8 8.5 5.8a15 15 0 0 1-2.6 3.2M5 6.2A15 15 0 0 0 1.5 10S5 15.8 10 15.8c1.4 0 2.7-.4 3.8-1"/></svg>',
    gear: '<svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="2.8"/><path d="M10 1.8v2.4M10 15.8v2.4M1.8 10h2.4M15.8 10h2.4M4.2 4.2l1.7 1.7M14.1 14.1l1.7 1.7M4.2 15.8l1.7-1.7M14.1 5.9l1.7-1.7"/></svg>',
    x: '<svg viewBox="0 0 20 20"><path d="M5 5l10 10M15 5L5 15"/></svg>',
  };
  /** One legend row: name, a values slot, and the hover buttons. Built once per chart
   *  render — only the values slot changes as the cursor moves, so a button is never
   *  replaced between mouse-down and mouse-up (which would swallow the click). */
  function legendRow(e) {
    const { s, def } = e;
    const note = e.skipped ? `<span class="muted">${def.needsBench ? "no index data" : "no volume data"}</span>`
      : e.note ? `<span class="muted snote">${esc(e.note)}</span>` : "";
    return `<div class="srow ${s.hidden || e.skipped ? "off" : ""}" data-id="${s.id}"><span class="sname" title="Click to select, double-click for settings">${esc(label(s))}</span>${note}<span class="svals"></span>${s.transient ? "" : btns(s)}</div>`;
  }
  function legendValues(e, i) {
    const { s, def } = e;
    if (e.skipped || s.hidden) return "";
    return def.plots.map((pl) => {
      const v = e.vals[pl.k]?.[i]; if (v == null) return "";
      const c = (e.vals._colors?.[pl.k]?.[i]) || s.colors[pl.k] || pl.c;
      return `<span style="color:${c}">${e.fmt(v)}</span>`;
    }).join(" ");
  }
  // both eye icons are rendered; CSS shows the one matching the row's .off state
  const btns = (s) => `<span class="sbtns"><button data-a="eye" title="Show / hide"><i class="i-shown">${BTN.eye}</i><i class="i-hidden">${BTN.eyeOff}</i></button><button data-a="gear" title="Settings">${BTN.gear}</button><button data-a="x" title="Remove">${BTN.x}</button></span>`;

  // ------------------------------------------------------------- dialogs
  function modal(html, cls = "") {
    const m = document.createElement("div");
    m.className = "smodal"; m.innerHTML = `<div class="smodal-card ${cls}">${html}</div>`;
    document.body.append(m);
    const close = () => { m.remove(); document.removeEventListener("keydown", onEsc, true); };
    const onEsc = (e) => { if (e.key === "Escape") { e.stopPropagation(); close(); } };
    document.addEventListener("keydown", onEsc, true);
    m.addEventListener("mousedown", (e) => { if (e.target === m) close(); });
    return { el: m, close };
  }
  /** The "Indicators" picker: search + categories, click to add (stays open, like TV). */
  function openPicker({ onChange, extra }) {
    const { el, close } = modal(`<div class="sm-head"><b>Indicators</b><button class="sm-x" title="Close">${BTN.x}</button></div>
      <div class="sm-search"><input placeholder="Search" spellcheck="false"></div>
      <div class="sm-body"><nav class="sm-cats"></nav><div class="sm-list"></div></div>
      <div class="sm-foot">${extra || ""}</div>`, "picker");
    let cat = "All";
    const q = el.querySelector(".sm-search input"), list = el.querySelector(".sm-list"), cats = el.querySelector(".sm-cats");
    const draw = () => {
      const active = load();
      cats.innerHTML = ["All", ...CATS, "Active"].map((c) => `<a data-c="${c}" class="${c === cat ? "on" : ""}">${c}${c === "Active" ? ` <span>${active.length}</span>` : ""}</a>`).join("");
      if (cat === "Active") {
        list.innerHTML = active.length ? active.map((s) => `<div class="sm-item act"><span>${esc(catName(s.type))} <span class="muted">${esc(label(s))}</span></span><button data-rm="${s.id}" title="Remove">${BTN.x}</button></div>`).join("")
          : `<div class="muted sm-empty">No indicators on the chart.</div>`;
        return;
      }
      const f = q.value.trim().toLowerCase();
      const items = Object.entries(CATALOG).filter(([, d]) => !d.setupsFor
        && (cat === "All" || d.cat === cat) && (!f || (d.name + " " + d.short).toLowerCase().includes(f)));
      list.innerHTML = items.map(([k, d]) => {
        const n = active.filter((s) => s.type === k).length;
        return `<div class="sm-item" data-add="${k}"><span>${esc(d.name)}</span><span class="muted">${esc(d.cat)}${n ? ` · <b>${n} on chart</b>` : ""}</span></div>`;
      }).join("") || `<div class="muted sm-empty">No indicator matches “${esc(q.value)}”.</div>`;
    };
    q.oninput = () => { if (cat === "Active") cat = "All"; draw(); };
    cats.onclick = (e) => { const a = e.target.closest("a"); if (a) { cat = a.dataset.c; draw(); } };
    list.onclick = (e) => {
      const it = e.target.closest("[data-add]"), rm = e.target.closest("[data-rm]");
      if (it) { add(it.dataset.add); onChange(); draw(); it.classList.add("flash"); }
      if (rm) { save(load().filter((s) => s.id !== rm.dataset.rm)); onChange(); draw(); }
    };
    el.querySelector(".sm-x").onclick = close;
    draw(); q.focus();
    return el;
  }
  /** Settings for one study: inputs + colours, applied live. */
  function openSettings(id, onChange) {
    const s = load().find((x) => x.id === id); if (!s) return;
    const def = CATALOG[s.type];
    const inputs = Object.entries(def.params).map(([k, d]) => {
      const name = PARAM_LABELS[k] || k.replace(/([A-Z])/g, " $1").replace(/^./, (c) => c.toUpperCase());
      if (typeof d === "object" && d.type === "select")
        return `<label><span>${name}</span><select data-p="${k}">${d.options.map((o) => `<option ${s.params[k] === o ? "selected" : ""}>${o}</option>`).join("")}</select></label>`;
      return `<label><span>${name}</span><input type="number" step="${Number.isInteger(d) ? 1 : 0.01}" min="${Number.isInteger(d) ? 1 : 0}" data-p="${k}" value="${s.params[k]}"></label>`;
    }).join("");
    const colors = def.plots.map((pl) => `<label><span>${pl.t || def.short}</span><input type="color" data-c="${pl.k}" value="${(s.colors[pl.k] || pl.c).slice(0, 7)}"></label>`).join("");
    const { el, close } = modal(`<div class="sm-head"><b>${esc(catName(s.type))}</b><button class="sm-x" title="Close">${BTN.x}</button></div>
      <div class="sm-form">${inputs ? `<h4>Inputs</h4>${inputs}` : ""}<h4>Style</h4>${colors}</div>
      <div class="sm-foot"><button class="ghost" data-a="reset">Defaults</button><span class="spacer"></span><button class="ghost" data-a="cancel">Cancel</button><button class="primary" data-a="ok">OK</button></div>`, "settings");
    const before = JSON.stringify(s);
    const apply = () => {
      const list = load(), t = list.find((x) => x.id === id); if (!t) return;
      el.querySelectorAll("[data-p]").forEach((i) => { t.params[i.dataset.p] = i.tagName === "SELECT" ? i.value : Math.max(+i.min || 0, +i.value || 0); });
      el.querySelectorAll("[data-c]").forEach((i) => { t.colors[i.dataset.c] = i.value; });
      save(list); onChange();
    };
    el.querySelector(".sm-form").addEventListener("change", apply);
    el.querySelector(".sm-x").onclick = close;
    el.querySelector(".sm-foot").onclick = (e) => {
      const a = e.target.closest("button")?.dataset.a;
      if (a === "ok") close();
      if (a === "cancel") { const list = load().map((x) => (x.id === id ? JSON.parse(before) : x)); save(list); onChange(); close(); }
      if (a === "reset") { const list = load().map((x) => (x.id === id ? { ...make(x.type), id } : x)); save(list); onChange(); close(); }
    };
  }
  function toggleHidden(id) { const list = load(), s = list.find((x) => x.id === id); if (s) { s.hidden = !s.hidden; save(list); } return s; }
  function remove(id) { save(load().filter((s) => s.id !== id)); }

  // ---- Trade setups: one strategy's setups at a time, chosen from its own control rather than
  // added like an indicator. Single-select because the layer is a singleton in practice — its card
  // and lane are one element each, keyed on one set of saved preferences — and because two
  // strategies' setups on one chart would be read as one picture of the stock.
  const setupLayers = () => Object.entries(CATALOG).filter(([, d]) => d.setupsFor)
    .map(([type, d]) => ({ type, strategy: d.setupsFor, name: stratName(d.setupsFor) }));
  const activeSetup = () => load().find((s) => CATALOG[s.type].setupsFor)?.type ?? null;

  /** The Trade setups picker: the Indicators picker's shape, deliberately — the same modal, search and
   *  category rail, so one thing is learned once — but SINGLE-select, because only one strategy's
   *  setups can be on a chart. Clicking the layer already on toggles it off, so there is no "None" row
   *  pretending to be a setup. Categories are the Strategies section of Learn: each layer names its
   *  guide (`learnGuide`) and the category is that guide's group in app.js's GUIDE_GROUP ("Breakouts
   *  from a base", "Trend following"...), so the two can never disagree. Resolved here, not at module
   *  scope, because app.js loads after this file. */
  /** badge(strategyKey) → HTML before each name (the Chart page passes the strategy's edge dot for the chart's market) */
  function openSetupPicker({ onChange, badge } = {}) {
    const { el, close } = modal(`<div class="sm-head"><b>Trade setups</b><button class="sm-x" title="Close">${BTN.x}</button></div>
      <div class="sm-search"><input placeholder="Search" spellcheck="false"></div>
      <div class="sm-body"><nav class="sm-cats"></nav><div class="sm-list"></div></div>
      <div class="sm-foot"><span class="muted small">What a strategy's rules would set up on, run over the whole history — not trades. Pick a backtest run to see what was actually bought.</span></div>`, "picker");
    let cat = "All";
    const q = el.querySelector(".sm-search input"), list = el.querySelector(".sm-list"), cats = el.querySelector(".sm-cats");
    const group = (t) => (typeof GUIDE_GROUP !== "undefined" && GUIDE_GROUP[CATALOG[t].learnGuide]) || "Strategies";
    const draw = () => {
      const layers = setupLayers(), cur = activeSetup();
      const used = [...new Set(layers.map((l) => group(l.type)))];
      cats.innerHTML = ["All", ...used].map((c) => `<a data-c="${esc(c)}" class="${c === cat ? "on" : ""}">${esc(c)}</a>`).join("");
      const f = q.value.trim().toLowerCase();
      const items = layers.filter((l) => (cat === "All" || group(l.type) === cat)
        && (!f || l.name.toLowerCase().includes(f) || group(l.type).toLowerCase().includes(f)));
      list.innerHTML = items.map((l) => `<div class="sm-item${l.type === cur ? " act" : ""}" data-set="${l.type}">
          <span>${badge ? badge(l.strategy) : ""}${esc(l.name)}</span><span class="muted">${esc(group(l.type))}${l.type === cur ? " · <b>on chart</b>" : ""}</span></div>`).join("")
        || `<div class="muted sm-empty">${layers.length ? `No setups match “${esc(q.value)}”.` : "No strategy has a trade-setups layer yet."}</div>`;
    };
    q.oninput = draw;
    cats.onclick = (e) => { const a = e.target.closest("a"); if (a) { cat = a.dataset.c; draw(); } };
    list.onclick = (e) => {
      const it = e.target.closest("[data-set]"); if (!it) return;
      const type = it.dataset.set;
      setSetup(type === activeSetup() ? null : type);   // clicking the one already on takes it off
      draw(); onChange?.();
    };
    el.querySelector(".sm-x").onclick = close;
    draw(); q.focus();
    return { close };
  }
  const setSetup = (type) => {
    const list = load().filter((s) => !CATALOG[s.type].setupsFor);
    save(list);
    if (type && CATALOG[type]?.setupsFor) add(type);
  };

  return { setStrategies: (keys) => STRATEGY_CHOICES.splice(1, STRATEGY_CHOICES.length, ...keys),
    setStrategyNames: (m) => Object.assign(STRATEGY_NAMES, m),
    setupLayers, activeSetup, setSetup, openSetupPicker,
    transient: (type, params = {}) => ({ ...make(type, params), transient: true }),   // drawn this visit, never saved
    setupName: () => { const t = activeSetup(); return t ? stratName(CATALOG[t].setupsFor) : null; },
    restore: save, CATALOG, load, render, legendRow, legendValues, openPicker, openSettings, toggleHidden, remove, label, needsBench: () => load().some((s) => CATALOG[s.type].needsBench) };
})();
