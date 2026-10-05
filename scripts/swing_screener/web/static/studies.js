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
  const CATALOG = {
    sma: { name: "Moving Average", short: "MA", cat: "Moving averages", overlay: true, params: { length: 20, source: SRC }, plots: [{ k: "ma", c: "#f5a623" }],
      calc: (b, p) => ({ ma: sma(source(b, p.source), p.length) }) },
    ema: { name: "Moving Average Exponential", short: "EMA", cat: "Moving averages", overlay: true, params: { length: 20, source: SRC }, plots: [{ k: "ma", c: "#ffeb3b" }],
      calc: (b, p) => ({ ma: ema(source(b, p.source), p.length) }) },
    wma: { name: "Moving Average Weighted", short: "WMA", cat: "Moving averages", overlay: true, params: { length: 20, source: SRC }, plots: [{ k: "ma", c: "#00bcd4" }],
      calc: (b, p) => ({ ma: wma(source(b, p.source), p.length) }) },
    ribbon: ribbon("Moving Average Ribbon (SMA)", "MA Ribbon", "SMA"),
    ribbon_ema: ribbon("Moving Average Ribbon (EMA)", "MA Ribbon", "EMA"),  // label shows the type: "MA Ribbon EMA 20 50 ..."
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
    sr: { name: "Support & Resistance (swing levels)", short: "S/R", cat: "Support & resistance", overlay: true, custom: true,
      label: (p) => `S/R ${p.lookback} bars`,
      params: { left: 5, right: 5, lookback: 250, tolerance: 0.5, minTouches: 2, maxLevels: 6 },
      plots: [{ k: "res", t: "Resistance", c: "#f23645" }, { k: "sup", t: "Support", c: "#089981" }],
      draw({ main, bars, p, col }) {
        // Key levels = prices the market has turned at repeatedly: swing pivots in the lookback whose
        // prices lie within `tolerance` x ATR(14) of each other are merged; a level needs `minTouches`.
        const n = bars.C.length, atr = rma(trueRange(bars.H, bars.L, bars.C), 14).at(-1) || 0, tol = Math.max(p.tolerance * atr, bars.C.at(-1) * 0.001);
        const piv = swingPivots(bars.H, bars.L, p.left, p.right, Math.max(0, n - p.lookback)).sort((a, b) => a.price - b.price);
        const clusters = [];
        for (const v of piv) {
          const c = clusters.at(-1);
          if (c && v.price - c.mean <= tol) { c.items.push(v); c.mean = c.items.reduce((x, y) => x + y.price, 0) / c.items.length; }
          else clusters.push({ items: [v], mean: v.price });
        }
        const close = bars.C.at(-1);
        const cands = clusters.filter((c) => c.items.length >= p.minTouches)
          .map((c) => ({ price: c.mean, touches: c.items.length, dist: Math.abs(c.mean - close) / close }));
        // half the slots above price (resistance) and half below (support): within each side the most-touched
        // levels win, nearer ones breaking ties; a side with too few levels gives its slots to the other
        const rank = (xs) => xs.sort((a, b) => b.touches - a.touches || a.dist - b.dist);
        const above = rank(cands.filter((c) => c.price > close)), below = rank(cands.filter((c) => c.price <= close));
        const half = Math.ceil(p.maxLevels / 2);
        let nA = Math.min(above.length, half), nB = Math.min(below.length, p.maxLevels - nA);
        nA = Math.min(above.length, p.maxLevels - nB);
        const levels = [...above.slice(0, nA), ...below.slice(0, nB)].sort((a, b) => b.price - a.price);
        const specs = levels.map((l) => {
          const res = l.price > close;
          return { price: l.price, color: col(res ? "res" : "sup"), lineWidth: l.touches >= 4 ? 2 : 1, lineStyle: 0, axisLabelVisible: true,
            title: `${res ? "R" : "S"} ×${l.touches}` };
        });
        let lines = specs.map((o) => main.createPriceLine(o));
        const nr = specs.filter((o) => o.title.startsWith("R")).length;
        return { series: [], note: levels.length ? `${nr} resistance · ${levels.length - nr} support` : "no level with enough touches",
          setVisible: (on) => { lines.forEach((l) => main.removePriceLine(l)); lines = on ? specs.map((o) => main.createPriceLine(o)) : []; } };
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
    atr: { name: "Average True Range", short: "ATR", cat: "Volatility", params: { length: 14 }, plots: [{ k: "atr", c: "#f23645" }],
      calc: (b, p) => ({ atr: rma(trueRange(b.H, b.L, b.C), p.length) }) },
    atrp: { name: "ATR % of price", short: "ATR%", cat: "Volatility", params: { length: 14 }, plots: [{ k: "atrp", c: "#f23645" }],
      calc: (b, p) => ({ atrp: zip((a, c) => (100 * a) / c, rma(trueRange(b.H, b.L, b.C), p.length), b.C) }) },
    bbw: { name: "Bollinger BandWidth", short: "BBW", cat: "Volatility", params: { length: 20, mult: 2 }, plots: [{ k: "bbw", c: "#2962ff" }],
      calc: (b, p) => { const m = sma(b.C, p.length), sd = stdev(b.C, p.length); return { bbw: zip((x, d) => (x ? (2 * p.mult * d) / x : null), m, sd) }; } },
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
    conversion: "Conversion line length", base: "Base line length", spanB: "Leading span B length" };
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
      if (old.sma200 !== false) list.push(make("sma", { length: 200 }, { ma: "#e040fb" }));
      if (old.ema20) list.push(make("ema", { length: 20 }));
      if (old.volume !== false) list.push(make("vol"));
      if (old.rsi !== false) list.push(make("rsi"));
      store.set("chartStudies", list);
    }
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
  const label = (s) => {
    if (CATALOG[s.type].label) return CATALOG[s.type].label(s.params);
    const d = CATALOG[s.type], vals = Object.entries(s.params).filter(([k]) => k !== "source" || s.params.source !== "close").map(([, v]) => v);
    return `${d.short}${vals.length ? " " + vals.join(" ") : ""}`;
  };

  // ------------------------------------------------------------- rendering
  /** Add every active study to `chart`. Returns entries for the legend. */
  function render({ chart, times, bars, ctx }) {
    const out = [];
    let pane = 1;
    const fmtV = (s, v) => (v == null ? "" : CATALOG[s.type].volumeFormat || CATALOG[s.type].volume ? compact(v) : Math.abs(v) >= 1000 ? v.toFixed(0) : Math.abs(v) >= 1 ? v.toFixed(2) : v.toPrecision(3));
    for (const s of load()) {
      const def = CATALOG[s.type];
      if ((def.needsVolume && !hasVolume(bars)) || (def.needsBench && !ctx.bench)) { out.push({ s, def, skipped: true, pane: def.overlay ? 0 : null }); continue; }
      if (def.custom) {
        const col = (k) => s.colors[k] || def.plots.find((x) => x.k === k).c;
        const r = def.draw({ chart, main: ctx.main, times, bars, p: s.params, col, tf: ctx.tf, plans: ctx.plans });
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
    return out;
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
      : e.note ? `<span class="muted">${esc(e.note)}</span>` : "";
    return `<div class="srow ${s.hidden || e.skipped ? "off" : ""}" data-id="${s.id}"><span class="sname" title="Click to select, double-click for settings">${esc(label(s))}</span>${note}<span class="svals"></span>${btns(s)}</div>`;
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
        list.innerHTML = active.length ? active.map((s) => `<div class="sm-item act"><span>${esc(CATALOG[s.type].name)} <span class="muted">${esc(label(s))}</span></span><button data-rm="${s.id}" title="Remove">${BTN.x}</button></div>`).join("")
          : `<div class="muted sm-empty">No indicators on the chart.</div>`;
        return;
      }
      const f = q.value.trim().toLowerCase();
      const items = Object.entries(CATALOG).filter(([, d]) => (cat === "All" || d.cat === cat) && (!f || (d.name + " " + d.short).toLowerCase().includes(f)));
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
    const { el, close } = modal(`<div class="sm-head"><b>${esc(def.name)}</b><button class="sm-x" title="Close">${BTN.x}</button></div>
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

  return { setStrategies: (keys) => STRATEGY_CHOICES.splice(1, STRATEGY_CHOICES.length, ...keys), restore: save, CATALOG, load, render, legendRow, legendValues, openPicker, openSettings, toggleHidden, remove, label, needsBench: () => load().some((s) => CATALOG[s.type].needsBench) };
})();
