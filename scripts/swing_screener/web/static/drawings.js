"use strict";
/* TradingView-style drawing tools for lightweight-charts.
 *
 * Shapes are painted by a series primitive on the chart's own canvas, so they
 * follow zoom, scroll and price-scale changes without any bookkeeping. Points
 * are stored as {t: epoch ms, p: price} rather than bar indices, so a drawing
 * made on the daily chart lands in the right place on weekly/monthly too.
 * Drawings persist per symbol on the server when a `remote` store is supplied
 * (localStorage is kept as a cache and as the fallback when the server is
 * unreachable); the ruler (measure) is transient.
 *
 * The toolbar mirrors TradingView's left panel: tool *families* behind one
 * button each (the button shows the last tool used from that family, the
 * small arrow opens the rest), then the ruler, magnet, stay-in-drawing-mode,
 * lock, hide and remove.
 */
const Drawings = (() => {
  const DAY = 86400000;
  const PALETTE = ["#2962ff", "#f23645", "#089981", "#ff9800", "#9c27b0", "#00bcd4", "#ffeb3b", "#d1d4dc"];
  const FIB = [[0, "#787b86"], [0.236, "#f23645"], [0.382, "#ff9800"], [0.5, "#4caf50"], [0.618, "#089981"], [0.786, "#00bcd4"], [1, "#787b86"]];

  // pts = clicks needed; cursor = a pointer mode rather than a shape
  const TOOLS = {
    cross: { label: "Cross", cursor: true }, dot: { label: "Dot", cursor: true },
    arrow: { label: "Arrow", cursor: true }, eraser: { label: "Eraser", cursor: true },
    trend: { label: "Trend line", pts: 2, key: "Alt + T" }, ray: { label: "Ray", pts: 2 },
    extline: { label: "Extended line", pts: 2 }, hline: { label: "Horizontal line", pts: 1, key: "Alt + H" },
    hray: { label: "Horizontal ray", pts: 1, key: "Alt + J" }, vline: { label: "Vertical line", pts: 1, key: "Alt + V" },
    crossline: { label: "Cross line", pts: 1, key: "Alt + C" },
    fib: { label: "Fib retracement", pts: 2, key: "Alt + F" },
    rect: { label: "Rectangle", pts: 2, key: "Alt + Shift + R" },
    text: { label: "Text", pts: 1 },
    callout: { label: "Callout", pts: 2 },
    long: { label: "Long position", pts: 1 }, short: { label: "Short position", pts: 1 },
    measure: { label: "Measure", pts: 2, key: "Shift + drag" },
  };
  const GROUPS = [
    ["cursors", "Cursors", ["cross", "dot", "arrow", "eraser"]],
    ["lines", "Trend line tools", ["trend", "ray", "extline", "hline", "hray", "vline", "crossline"]],
    ["fibs", "Fibonacci tools", ["fib"]],
    ["shapes", "Geometric shapes", ["rect"]],
    ["notes", "Annotation tools", ["text", "callout"]],
    ["forecast", "Prediction and measurement tools", ["long", "short"]],
  ];
  const HOTKEYS = { KeyT: "trend", KeyH: "hline", KeyJ: "hray", KeyV: "vline", KeyC: "crossline", KeyF: "fib" };
  const LINE_TYPES = new Set(["trend", "ray", "extline", "hline", "hray", "vline", "crossline", "rect", "callout"]);
  const TEXT_WRAP = 320;  // px: longest line before a text / callout wraps

  const ICON = {
    cross: '<path d="M10 2v16M2 10h16"/>',
    dot: '<circle cx="10" cy="10" r="2.4" fill="currentColor"/>',
    arrow: '<path d="M6 2.5l9.5 7.5-4.2.9 2.6 4.6-1.9 1.1-2.6-4.6L6 15.2z"/>',
    eraser: '<path d="M8 17h9M3.6 12.6l7.5-7.5 4.6 4.6-7.4 7.3H7.9z"/><path d="M7.6 8.6l4.6 4.6"/>',
    trend: '<path d="M4.5 15.5l11-11"/><circle cx="4" cy="16" r="1.8"/><circle cx="16" cy="4" r="1.8"/>',
    ray: '<path d="M5 15L18.5 1.5"/><circle cx="4" cy="16" r="1.8"/><circle cx="10" cy="10" r="1.8"/>',
    extline: '<path d="M1 19L19 1"/><circle cx="7" cy="13" r="1.8"/><circle cx="13" cy="7" r="1.8"/>',
    hline: '<path d="M1 10h7M12 10h7"/><circle cx="10" cy="10" r="1.8"/>',
    hray: '<path d="M7 10h12"/><circle cx="5" cy="10" r="1.8"/>',
    vline: '<path d="M10 1v7M10 12v7"/><circle cx="10" cy="10" r="1.8"/>',
    crossline: '<path d="M10 1v7M10 12v7M1 10h7M12 10h7"/><circle cx="10" cy="10" r="1.8"/>',
    fib: '<path d="M2 3.5h16M2 7.5h16M2 12.5h16M2 16.5h16" stroke-dasharray="2 1.5"/><circle cx="4" cy="16.5" r="1.6"/><circle cx="16" cy="3.5" r="1.6"/>',
    rect: '<rect x="3" y="5" width="14" height="10" rx="1"/><circle cx="3" cy="5" r="1.5"/><circle cx="17" cy="15" r="1.5"/>',
    text: '<path d="M4 5.5V3h12v2.5M10 3v14M7.5 17h5"/>',
    callout: '<rect x="6" y="2.5" width="12" height="8.5" rx="1.5"/><path d="M9.5 11l-6 5.5"/><circle cx="3" cy="17" r="1.4" fill="currentColor"/>',
    long: '<path d="M3 3h14v7H3z" fill="rgba(8,153,129,.45)" stroke="none"/><path d="M3 10h14v6H3z" fill="rgba(242,54,69,.45)" stroke="none"/><path d="M3 10h14"/>',
    short: '<path d="M3 4h14v6H3z" fill="rgba(242,54,69,.45)" stroke="none"/><path d="M3 10h14v7H3z" fill="rgba(8,153,129,.45)" stroke="none"/><path d="M3 10h14"/>',
    measure: '<path d="M2.5 14.5L14.5 2.5l3 3-12 12z"/><path d="M5.5 11.5l1.6 1.6M8.5 8.5l2 2M11.5 5.5l1.6 1.6"/>',
    magnet: '<path d="M4.5 3v7.2a5.5 5.5 0 0 0 11 0V3h-3.4v7.2a2.1 2.1 0 0 1-4.2 0V3z"/><path d="M4.5 6.4h3.4M12.1 6.4h3.4"/>',
    stay: '<path d="M3 17l1.2-4.2L13 4l3 3-8.8 8.8z"/><path d="M11.5 5.5l3 3"/><circle cx="15.5" cy="15.5" r="2" fill="currentColor"/>',
    lock: '<rect x="4" y="9" width="12" height="9" rx="1.5"/><path d="M7 9V6.2a3 3 0 0 1 6 0V9"/>',
    hide: '<path d="M1.5 10S5 4.2 10 4.2 18.5 10 18.5 10 15 15.8 10 15.8 1.5 10 1.5 10z"/><circle cx="10" cy="10" r="2.6"/>',
    trash: '<path d="M4 6h12M8 6V3.8h4V6M5.6 6l.9 11h7l.9-11"/>',
    more: '<path d="M7 4l5 5-5 5"/>',
  };
  const svg = (k) => `<svg viewBox="0 0 20 20">${ICON[k]}</svg>`;
  const store = {
    get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  };
  const fmtP = (v) => (Math.abs(v) >= 1 ? v.toFixed(2) : v.toPrecision(3));

  /** `remote` (optional): {exists, items, save(items), flush()} — the server-side store for this symbol.
   *  When it exists its items win; a browser's old localStorage drawings are migrated up only when the
   *  server has no row yet, so clearing on one machine cannot be undone by another machine's stale copy. */
  function create({ chart, series, chartEl, times, bars, key, remote }) {
    const LC = LightweightCharts;
    const ts = chart.timeScale();
    const T = times.map((s) => Date.parse(s + "T00:00:00Z"));
    const n = T.length;
    const step = n > 1 ? (T[n - 1] - T[Math.max(0, n - 21)]) / Math.min(20, n - 1) : DAY;
    const storeKey = "draw:" + key;

    let items = remote && remote.exists ? remote.items : store.get(storeKey, []);
    if (remote && !remote.exists && items.length) remote.save(items);
    if (remote) store.set(storeKey, items);
    let draft = null, measure = null, selected = null, drag = null, downPx = null, hist = [];
    let tool = store.get("drawCursor", "cross"), cursorMode = tool;
    let color = store.get("drawColor", PALETTE[0]);
    const opts = store.get("drawOpts", { magnet: false, stay: false, lock: false, hide: false });
    let req = () => {}, listeners = [];
    const emit = () => listeners.forEach((f) => f());
    const save = () => { store.set(storeKey, items); remote && remote.save(items); };
    const snap = () => { hist.push(JSON.stringify(items)); if (hist.length > 60) hist.shift(); };
    const bboxes = new Map();  // text extents from the last paint, for hit testing

    // ---- time <-> logical bar index (interpolated inside the data, extrapolated beyond)
    const msToLogical = (ms) => {
      if (ms <= T[0]) return (ms - T[0]) / step;
      if (ms >= T[n - 1]) return n - 1 + (ms - T[n - 1]) / step;
      let lo = 0, hi = n - 1;
      while (hi - lo > 1) { const m = (lo + hi) >> 1; T[m] <= ms ? (lo = m) : (hi = m); }
      return lo + (ms - T[lo]) / (T[hi] - T[lo]);
    };
    const logicalToMs = (l) => {
      if (l <= 0) return T[0] + l * step;
      if (l >= n - 1) return T[n - 1] + (l - (n - 1)) * step;
      const i = Math.floor(l);
      return T[i] + (T[i + 1] - T[i]) * (l - i);
    };
    const toPx = (pt) => {
      const x = ts.logicalToCoordinate(msToLogical(pt.t)), y = series.priceToCoordinate(pt.p);
      return x == null || y == null ? null : { x, y };
    };
    /** pixel -> point, snapped to the bar; with the magnet on, also to that bar's nearest O/H/L/C */
    const fromPx = (x, y, magnet = opts.magnet) => {
      const l = ts.coordinateToLogical(x); let p = series.coordinateToPrice(y);
      if (l == null || p == null) return null;
      const i = Math.round(l);
      if (magnet && i >= 0 && i < n && bars[i]) {
        const b = bars[i];
        let best = null, bd = 28;
        for (const v of [b.open, b.high, b.low, b.close]) {
          const d = Math.abs(series.priceToCoordinate(v) - y);
          if (d < bd) { bd = d; best = v; }
        }
        if (best != null) p = best;
      }
      return { t: logicalToMs(i), p };
    };
    const area = () => ({ w: ts.width(), h: chart.panes()[0].getHeight() });

    // ---- geometry shared by painting and hit testing
    const farPoint = (a, b, w) => {
      const dx = b.x - a.x, dy = b.y - a.y, f = (w + 4000) / (Math.hypot(dx, dy) || 1);
      return { x: a.x + dx * f, y: a.y + dy * f };
    };
    const fibLevels = (it) => FIB.map(([lv, c]) => ({ lv, c, p: it.pts[1].p + (it.pts[0].p - it.pts[1].p) * lv }));
    function position(it) {  // long/short: entry, target, stop -> pixel box
      const e = toPx(it.pts[0]), tg = toPx(it.pts[1]), st = toPx(it.pts[2]);
      return e && tg && st ? { e, tg, st, x0: Math.min(e.x, tg.x), x1: Math.max(e.x, tg.x) } : null;
    }
    function handles(it) {
      const P = it.pts;
      if (it.type === "long" || it.type === "short") {
        const b = position(it); if (!b) return [];
        return [
          { x: b.e.x, y: b.e.y, set: (pt) => { P[0] = pt; } },
          { x: b.e.x, y: b.tg.y, set: (pt) => { P[1] = { t: P[1].t, p: pt.p }; } },
          { x: b.e.x, y: b.st.y, set: (pt) => { P[2] = { t: P[2].t, p: pt.p }; } },
          { x: b.tg.x, y: b.e.y, set: (pt) => { P[1] = { t: pt.t, p: P[1].p }; P[2] = { t: pt.t, p: P[2].p }; } },
        ];
      }
      return P.map((q, i) => { const a = toPx(q); return a && { x: a.x, y: a.y, set: (pt) => { P[i] = pt; } }; }).filter(Boolean);
    }

    // ---- painting
    /** split on newlines, then word-wrap each line to maxw with the current ctx.font */
    function wrapText(ctx, text, maxw = TEXT_WRAP) {
      const out = [];
      for (const raw of String(text || "").split("\n")) {
        let line = "";
        for (const word of raw.split(/\s+/).filter(Boolean)) {
          const cand = line ? line + " " + word : word;
          if (line && ctx.measureText(cand).width > maxw) { out.push(line); line = word; }
          else line = cand;
        }
        out.push(line);
      }
      return out;
    }
    function label(ctx, text, x, y, bg, align = "center") {
      ctx.font = "11px -apple-system, Segoe UI, sans-serif";
      const w = ctx.measureText(text).width + 10, h = 17;
      const left = align === "right" ? x - w : align === "left" ? x : x - w / 2;
      ctx.fillStyle = bg; ctx.beginPath(); ctx.roundRect(left, y - h / 2, w, h, 3); ctx.fill();
      ctx.fillStyle = "#fff"; ctx.textBaseline = "middle"; ctx.textAlign = "left"; ctx.fillText(text, left + 5, y + 0.5);
    }
    function paintItem(ctx, it, w, h, isSel) {
      const a = toPx(it.pts[0]); if (!a) return;
      const b = it.pts[1] ? toPx(it.pts[1]) : a; if (!b) return;
      ctx.strokeStyle = it.color; ctx.lineWidth = it.width || 2; ctx.setLineDash(it.dash ? [5, 4] : []);
      ctx.beginPath();
      switch (it.type) {
        case "trend": ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); break;
        case "ray": { const f = farPoint(a, b, w); ctx.moveTo(a.x, a.y); ctx.lineTo(f.x, f.y); ctx.stroke(); break; }
        case "extline": { const f = farPoint(a, b, w), g = farPoint(b, a, w); ctx.moveTo(g.x, g.y); ctx.lineTo(f.x, f.y); ctx.stroke(); break; }
        case "hline": ctx.moveTo(0, a.y); ctx.lineTo(w, a.y); ctx.stroke(); label(ctx, fmtP(it.pts[0].p), w - 4, a.y, it.color, "right"); break;
        case "hray": ctx.moveTo(a.x, a.y); ctx.lineTo(w, a.y); ctx.stroke(); label(ctx, fmtP(it.pts[0].p), w - 4, a.y, it.color, "right"); break;
        case "vline": ctx.moveTo(a.x, 0); ctx.lineTo(a.x, h); ctx.stroke(); break;
        case "crossline": ctx.moveTo(a.x, 0); ctx.lineTo(a.x, h); ctx.moveTo(0, a.y); ctx.lineTo(w, a.y); ctx.stroke();
          label(ctx, fmtP(it.pts[0].p), w - 4, a.y, it.color, "right"); break;
        case "rect": {
          const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y), rw = Math.abs(a.x - b.x), rh = Math.abs(a.y - b.y);
          // a lighter wash for an annotation than for a user's own box, so the chart
          // reads as price-with-notes rather than price-under-paint
          ctx.fillStyle = it.color + (it.auto ? "18" : "2e");
          ctx.fillRect(x, y, rw, rh); ctx.strokeRect(x, y, rw, rh);
          if (it.text) label(ctx, it.text, x + 2, y - 10, it.color, "left");
          break;
        }
        case "fib": {
          const x0 = Math.min(a.x, b.x), x1 = Math.max(a.x, b.x), lv = fibLevels(it);
          ctx.lineWidth = 1;
          lv.forEach((l, i) => {
            const y = series.priceToCoordinate(l.p); if (y == null) return;
            if (i > 0) { const y0 = series.priceToCoordinate(lv[i - 1].p); ctx.fillStyle = l.c + "14"; ctx.fillRect(x0, Math.min(y, y0), x1 - x0, Math.abs(y - y0)); }
            ctx.strokeStyle = l.c; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
            ctx.font = "11px -apple-system, Segoe UI, sans-serif"; ctx.fillStyle = l.c; ctx.textAlign = "right"; ctx.textBaseline = "middle";
            ctx.fillText(`${l.lv} (${fmtP(l.p)})`, x0 - 6, y);
          });
          ctx.setLineDash([4, 4]); ctx.strokeStyle = "#787b86"; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); ctx.setLineDash([]);
          break;
        }
        case "text": {
          const size = it.size || 14, lh = Math.round(size * 1.35);
          ctx.font = `${size}px -apple-system, Segoe UI, sans-serif`; ctx.textBaseline = "top"; ctx.textAlign = "left";
          ctx.fillStyle = it.color;
          const lines = wrapText(ctx, it.text);
          let tw = 0;
          lines.forEach((l, i) => { ctx.fillText(l, a.x, a.y + i * lh); tw = Math.max(tw, ctx.measureText(l).width); });
          const th = (lines.length - 1) * lh + size + 4;
          bboxes.set(it.id, { x: a.x, y: a.y, w: tw, h: th });
          if (isSel) { ctx.strokeStyle = it.color; ctx.lineWidth = 1; ctx.setLineDash([3, 3]); ctx.strokeRect(a.x - 3, a.y - 3, tw + 6, th + 6); ctx.setLineDash([]); }
          break;
        }
        case "callout": {
          const size = it.size || 13, lh = Math.round(size * 1.4), pad = 8;
          ctx.font = `${size}px -apple-system, Segoe UI, sans-serif`;
          const lines = wrapText(ctx, it.text);
          let tw = 0;
          lines.forEach((l) => { tw = Math.max(tw, ctx.measureText(l).width); });
          const bw = tw + pad * 2, bh = (lines.length - 1) * lh + size + pad * 2;
          // leader from the anchored bar to the nearest edge of the text box, dot on the bar
          const lx = Math.max(b.x, Math.min(a.x, b.x + bw)), ly = Math.max(b.y, Math.min(a.y, b.y + bh));
          ctx.lineWidth = it.width || 1.5; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(lx, ly); ctx.stroke();
          ctx.fillStyle = it.color; ctx.beginPath(); ctx.arc(a.x, a.y, 2.5, 0, 7); ctx.fill();
          const css = getComputedStyle(document.documentElement);
          ctx.fillStyle = css.getPropertyValue("--panel").trim() || "#1e222d";
          ctx.globalAlpha = 0.92; ctx.beginPath(); ctx.roundRect(b.x, b.y, bw, bh, 4); ctx.fill(); ctx.globalAlpha = 1;
          ctx.lineWidth = 1; ctx.beginPath(); ctx.roundRect(b.x, b.y, bw, bh, 4); ctx.stroke();
          ctx.fillStyle = css.getPropertyValue("--strong").trim() || "#e8e8ea"; ctx.textBaseline = "top"; ctx.textAlign = "left";
          lines.forEach((l, i) => ctx.fillText(l, b.x + pad, b.y + pad + i * lh));
          bboxes.set(it.id, { x: b.x, y: b.y, w: bw, h: bh });
          break;
        }
        case "long": case "short": {
          const bx = position(it); if (!bx) break;
          const { e, tg, st, x0, x1 } = bx, W = Math.max(x1 - x0, 1);
          ctx.fillStyle = "rgba(8,153,129,.22)"; ctx.fillRect(x0, Math.min(e.y, tg.y), W, Math.abs(tg.y - e.y));
          ctx.fillStyle = "rgba(242,54,69,.22)"; ctx.fillRect(x0, Math.min(e.y, st.y), W, Math.abs(st.y - e.y));
          ctx.strokeStyle = "#787b86"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x0, e.y); ctx.lineTo(x1, e.y); ctx.stroke();
          const ep = it.pts[0].p, tp = it.pts[1].p, sp = it.pts[2].p;
          const tPct = ((tp - ep) / ep) * 100, sPct = ((sp - ep) / ep) * 100, rr = Math.abs(tp - ep) / (Math.abs(ep - sp) || 1e-9);
          const cx = x0 + W / 2, up = tg.y < e.y;
          label(ctx, `Target: ${fmtP(tp)} (${tPct >= 0 ? "+" : ""}${tPct.toFixed(2)}%)`, cx, tg.y + (up ? -11 : 11), "#089981");
          label(ctx, `Stop: ${fmtP(sp)} (${sPct >= 0 ? "+" : ""}${sPct.toFixed(2)}%)`, cx, st.y + (up ? 11 : -11), "#f23645");
          label(ctx, `${it.type === "long" ? "Long" : "Short"} ${fmtP(ep)} · R:R ${rr.toFixed(2)}`, cx, e.y, "#4a4f5e");
          break;
        }
      }
      if (isSel && it.type !== "text") {
        const css = getComputedStyle(document.documentElement);
        ctx.fillStyle = css.getPropertyValue("--panel").trim(); ctx.strokeStyle = it.type === "long" || it.type === "short" || it.type === "fib" ? css.getPropertyValue("--accent").trim() : it.color; ctx.lineWidth = 2;
        for (const q of handles(it)) { ctx.beginPath(); ctx.arc(q.x, q.y, 4.5, 0, 7); ctx.fill(); ctx.stroke(); }
      }
    }
    function paintMeasure(ctx, m) {
      const a = toPx(m.pts[0]), b = toPx(m.pts[1]);
      if (!a || !b) return;
      const up = m.pts[1].p >= m.pts[0].p, col = up ? "41,98,255" : "242,54,69";
      const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y), rw = Math.abs(a.x - b.x), rh = Math.abs(a.y - b.y);
      ctx.fillStyle = `rgba(${col},.18)`; ctx.fillRect(x, y, rw, rh);
      ctx.strokeStyle = `rgb(${col})`; ctx.lineWidth = 1; ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(x + rw / 2, a.y); ctx.lineTo(x + rw / 2, b.y); ctx.moveTo(a.x, y + rh / 2); ctx.lineTo(b.x, y + rh / 2); ctx.stroke();
      const dir = b.y < a.y ? 1 : -1, ax = x + rw / 2;
      ctx.beginPath(); ctx.moveTo(ax, b.y); ctx.lineTo(ax - 4, b.y + 7 * dir); ctx.lineTo(ax + 4, b.y + 7 * dir); ctx.closePath(); ctx.fillStyle = `rgb(${col})`; ctx.fill();
      const dP = m.pts[1].p - m.pts[0].p, pct = (dP / m.pts[0].p) * 100;
      const nb = Math.round(msToLogical(m.pts[1].t) - msToLogical(m.pts[0].t)), days = Math.round((m.pts[1].t - m.pts[0].t) / DAY);
      const l1 = `${dP >= 0 ? "+" : ""}${fmtP(dP)} (${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%)`, l2 = `${nb} bars, ${days}d`;
      ctx.font = "12px -apple-system, Segoe UI, sans-serif";
      const bw = Math.max(ctx.measureText(l1).width, ctx.measureText(l2).width) + 16, bh = 38;
      const { h } = area();
      const bx = Math.max(2, x + rw / 2 - bw / 2), by = Math.max(2, Math.min(h - bh - 2, up ? y - bh - 8 : y + rh + 8));
      ctx.fillStyle = `rgb(${col})`; ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, 4); ctx.fill();
      ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
      ctx.fillText(l1, bx + bw / 2, by + 15); ctx.fillText(l2, bx + bw / 2, by + 30); ctx.textAlign = "left";
    }
    series.attachPrimitive({
      attached(p) { req = p.requestUpdate; },
      detached() { req = () => {}; },
      updateAllViews() {},
      paneViews: () => [{
        zOrder: () => "top",
        renderer: () => ({
          draw: (target) => target.useMediaCoordinateSpace(({ context: ctx }) => {
            const { w, h } = area();
            ctx.save(); ctx.beginPath(); ctx.rect(0, 0, w, h); ctx.clip();
            // strategy annotations first, so a user's own drawing always sits on top
            auto.forEach((it) => paintItem(ctx, it, w, h, false));
            if (!opts.hide) items.forEach((it) => paintItem(ctx, it, w, h, it.id === selected));
            if (draft && draft.type !== "measure") paintItem(ctx, { ...draft, color, width: 2 }, w, h, false);
            const m = measure || (draft && draft.type === "measure" ? draft : null);
            if (m && m.pts[1]) paintMeasure(ctx, m);
            ctx.restore();
          }),
        }),
      }],
    });

    // ---- hit testing (pixel space)
    const segDist = (p, a, b) => {
      const dx = b.x - a.x, dy = b.y - a.y, l2 = dx * dx + dy * dy;
      const t = l2 ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2)) : 0;
      return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
    };
    const inBox = (p, x0, y0, x1, y1, pad = 5) => p.x >= Math.min(x0, x1) - pad && p.x <= Math.max(x0, x1) + pad && p.y >= Math.min(y0, y1) - pad && p.y <= Math.max(y0, y1) + pad;
    function dist(it, p) {
      const { w } = area(), a = toPx(it.pts[0]); if (!a) return Infinity;
      const b = it.pts[1] ? toPx(it.pts[1]) : a; if (!b) return Infinity;
      switch (it.type) {
        case "hline": return Math.abs(p.y - a.y);
        case "hray": return p.x >= a.x - 6 ? Math.abs(p.y - a.y) : Infinity;
        case "vline": return Math.abs(p.x - a.x);
        case "crossline": return Math.min(Math.abs(p.x - a.x), Math.abs(p.y - a.y));
        case "trend": return segDist(p, a, b);
        case "ray": return segDist(p, a, farPoint(a, b, w));
        case "extline": return segDist(p, farPoint(b, a, w), farPoint(a, b, w));
        case "rect": return inBox(p, a.x, a.y, b.x, b.y) ? 0 : Infinity;
        case "fib": { const lv = fibLevels(it); return inBox(p, a.x, series.priceToCoordinate(lv[0].p), b.x, series.priceToCoordinate(lv.at(-1).p)) ? 0 : Infinity; }
        case "text": { const bb = bboxes.get(it.id); return bb && inBox(p, bb.x, bb.y, bb.x + bb.w, bb.y + bb.h) ? 0 : Infinity; }
        case "callout": {
          const bb = bboxes.get(it.id);
          if (bb && inBox(p, bb.x, bb.y, bb.x + bb.w, bb.y + bb.h)) return 0;
          const end = bb ? { x: Math.max(bb.x, Math.min(a.x, bb.x + bb.w)), y: Math.max(bb.y, Math.min(a.y, bb.y + bb.h)) } : b;
          return segDist(p, a, end);
        }
        case "long": case "short": { const bx = position(it); return bx && inBox(p, bx.x0, bx.tg.y, bx.x1, bx.st.y) ? 0 : Infinity; }
      }
      return Infinity;
    }
    function hitItem(p) {
      if (opts.hide || opts.lock) return null;
      for (let i = items.length - 1; i >= 0; i--) if (dist(items[i], p) <= 6) return items[i];
      return null;
    }
    const hitHandle = (it, p) => (it ? handles(it).findIndex((q) => Math.hypot(q.x - p.x, q.y - p.y) <= 8) : -1);

    // ---- floating toolbar for the selected drawing (colour, width, text, delete)
    const ftb = document.createElement("div");
    ftb.className = "dtb"; ftb.hidden = true;
    chartEl.append(ftb);
    function renderFtb() {
      const it = items.find((i) => i.id === selected);
      ftb.hidden = !it;
      if (!it) return;
      ftb.innerHTML = PALETTE.map((c) => `<button class="sw ${it.color === c ? "on" : ""}" data-c="${c}" style="--c:${c}" title="${c}"></button>`).join("") +
        (LINE_TYPES.has(it.type) ? `<span class="sep"></span>${[1, 2, 3].map((wd) => `<button class="wd ${(it.width || 2) === wd ? "on" : ""}" data-w="${wd}" title="${wd}px"><i style="height:${wd}px"></i></button>`).join("")}` : "") +
        (it.type === "text" || it.type === "callout" ? `<span class="sep"></span><button data-a="edit" title="Edit text">Edit</button>` : "") +
        `<span class="sep"></span><span class="name">${TOOLS[it.type].label}</span><button data-a="del" title="Remove (Del)">${svg("trash")}</button>`;
    }
    ftb.addEventListener("mousedown", (e) => e.stopPropagation());
    ftb.onclick = (e) => {
      const it = items.find((i) => i.id === selected); if (!it) return;
      const b = e.target.closest("button"); if (!b) return;
      if (b.dataset.c) { snap(); it.color = color = b.dataset.c; store.set("drawColor", color); }
      else if (b.dataset.w) { snap(); it.width = +b.dataset.w; }
      else if (b.dataset.a === "del") { removeSelected(); return; }
      else if (b.dataset.a === "edit") { editText(it); return; }
      save(); renderFtb(); req();
    };

    // ---- inline text editor (multi-line: Enter = new line, click away or ⌘/Ctrl+Enter = done)
    function editText(it, isNew = false) {
      const a = toPx(it.type === "callout" && it.pts[1] ? it.pts[1] : it.pts[0]); if (!a) return;
      const inp = document.createElement("textarea");
      inp.className = "dtext"; inp.value = it.text || ""; inp.rows = 1;
      inp.placeholder = "Text — Enter for a new line, Esc cancels";
      inp.style.left = a.x + "px"; inp.style.top = a.y - 4 + "px"; inp.style.color = it.color;
      chartEl.append(inp);
      const fit = () => { inp.style.height = "0"; inp.style.height = Math.min(inp.scrollHeight + 2, 300) + "px"; };
      inp.oninput = fit;
      fit(); inp.focus(); inp.select();
      let done = false;
      const finish = (ok) => {
        if (done) return; done = true;
        const v = inp.value.replace(/\s+$/, ""); inp.remove();
        if (ok && v.trim()) { snap(); it.text = v; if (isNew) items.push(it); selected = it.id; save(); }
        else if (isNew) selected = null;
        renderFtb(); req();
      };
      inp.addEventListener("mousedown", (e) => e.stopPropagation());
      inp.onkeydown = (e) => {
        e.stopPropagation();
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) finish(true);
        if (e.key === "Escape") finish(false);
      };
      inp.onblur = () => finish(true);
    }

    // ---- interaction
    const local = (e) => { const r = chartEl.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
    const inPlot = (p) => { const { w, h } = area(); return p.x >= 0 && p.x < w && p.y >= 0 && p.y < h; };
    const uid = () => Math.random().toString(36).slice(2, 9);
    const isCursor = (t) => !!TOOLS[t]?.cursor;

    function newItem(type, pt, p) {
      const it = { id: uid(), type, color, width: 2, pts: [pt] };
      if (type === "long" || type === "short") {
        // default box: stop 40px away, target at 2R, 25 bars wide — scale-independent
        const sgn = type === "long" ? 1 : -1, l = Math.round(ts.coordinateToLogical(p.x)) + 25, end = logicalToMs(l);
        it.pts = [pt, { t: end, p: series.coordinateToPrice(p.y - 80 * sgn) }, { t: end, p: series.coordinateToPrice(p.y + 40 * sgn) }];
      }
      return it;
    }
    function commit(type, pts) {
      if (type === "measure") measure = { type, pts };
      else if (type === "callout") {  // anchor + box placed; the item only lands once its text is confirmed
        draft = null;
        if (!opts.stay) setTool(cursorMode);
        editText({ ...newItem(type, pts[0]), pts }, true); req(); return;
      }
      else { snap(); const it = { ...newItem(type, pts[0]), pts }; items.push(it); selected = it.id; save(); }
      draft = null;
      if (!opts.stay || type === "measure") setTool(cursorMode);
      renderFtb(); req();
    }
    function removeSelected() {
      if (!selected) return;
      snap(); items = items.filter((i) => i.id !== selected); selected = null; save(); renderFtb(); req(); emit();
    }

    function onDown(e) {
      if (e.button !== 0) return;
      if (e.target.closest?.(".legend, .pane-legend, .dtb, .dtext")) return;  // legend buttons, not the plot
      const p = local(e); if (!inPlot(p)) return;
      const pt = fromPx(p.x, p.y); if (!pt) return;
      const stop = () => { e.stopPropagation(); e.preventDefault(); };
      measure = null;
      // TradingView habit: shift + drag measures from any cursor mode
      if (e.shiftKey && isCursor(tool) && !draft) { stop(); draft = { type: "measure", pts: [fromPx(p.x, p.y, false), pt] }; downPx = p; req(); return; }
      if (!isCursor(tool)) {
        stop();
        const need = TOOLS[tool].pts;
        if (draft) return commit(draft.type, [draft.pts[0], pt]);
        if (tool === "text") { const it = newItem("text", pt); setTool(cursorMode); editText(it, true); return; }
        if (tool === "long" || tool === "short") { snap(); const it = newItem(tool, pt, p); items.push(it); selected = it.id; save(); if (!opts.stay) setTool(cursorMode); renderFtb(); req(); emit(); return; }
        if (need === 1) return commit(tool, [pt]);
        draft = { type: tool, pts: [pt, pt] }; downPx = p; req(); return;
      }
      if (tool === "eraser") {
        const it = hitItem(p);
        if (it) { stop(); selected = it.id; removeSelected(); }
        return;
      }
      const sel = items.find((i) => i.id === selected);
      const hi = opts.lock ? -1 : hitHandle(sel, p);
      if (sel && hi >= 0) { snap(); drag = { item: sel, handle: handles(sel)[hi] }; }
      else {
        const it = hitItem(p);
        selected = it ? it.id : null;
        if (it) { snap(); drag = { item: it, handle: null, fromP: series.coordinateToPrice(p.y), orig: it.pts.map((q) => ({ ...q })), fromL: ts.coordinateToLogical(p.x) }; }
      }
      if (drag) stop();
      renderFtb(); req();
    }
    function onMove(e) {
      const p = local(e);
      if (draft && inPlot(p)) { const pt = fromPx(p.x, p.y, draft.type !== "measure" && opts.magnet); if (pt) { draft.pts[1] = pt; req(); } return; }
      if (drag) {
        const pt = fromPx(p.x, p.y); if (!pt) return;
        if (drag.handle) drag.handle.set(pt);
        else {  // move the whole drawing by whole bars and the raw price delta
          const dl = Math.round(ts.coordinateToLogical(p.x) - drag.fromL), dP = series.coordinateToPrice(p.y) - drag.fromP;
          drag.item.pts = drag.orig.map((q) => ({ t: logicalToMs(Math.round(msToLogical(q.t)) + dl), p: q.p + dP }));
        }
        req(); return;
      }
      if (!inPlot(p)) return;
      const over = hitItem(p);
      chartEl.style.cursor = !isCursor(tool) ? "crosshair" : tool === "eraser" ? (over ? "pointer" : "default") : over ? "pointer" : tool === "arrow" ? "default" : "crosshair";
    }
    function onUp(e) {
      if (draft && downPx) { // press-drag-release draws too, not just click-click
        const p = local(e);
        if (Math.hypot(p.x - downPx.x, p.y - downPx.y) > 6 && inPlot(p)) {
          const pt = fromPx(p.x, p.y, draft.type !== "measure" && opts.magnet); if (pt) commit(draft.type, [draft.pts[0], pt]);
        }
        downPx = null;
      }
      if (drag) { drag = null; save(); emit(); }
    }
    function onDbl(e) {
      const p = local(e); const it = hitItem(p);
      if (it && (it.type === "text" || it.type === "callout")) { e.stopPropagation(); selected = it.id; editText(it); }
    }
    function undo() {
      if (!hist.length) return;
      items = JSON.parse(hist.pop()); selected = null; save(); renderFtb(); req(); emit();
    }
    function onKey(e) {
      if (e.target.closest?.("input, select, textarea")) return;
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") { undo(); e.preventDefault(); return; }
      if (e.altKey && !e.metaKey && !e.ctrlKey) {
        const t = e.shiftKey && e.code === "KeyR" ? "rect" : !e.shiftKey && HOTKEYS[e.code];
        if (t) { setTool(t); e.preventDefault(); }
        return;
      }
      if (e.key === "Escape") { draft = null; measure = null; selected = null; setTool(cursorMode); renderFtb(); req(); }
      else if ((e.key === "Delete" || e.key === "Backspace") && selected) { removeSelected(); e.preventDefault(); }
    }
    chartEl.addEventListener("mousedown", onDown, true);
    chartEl.addEventListener("dblclick", onDbl, true);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("keydown", onKey);

    function applyCursor() {
      const ch = { mode: LC.CrosshairMode.Normal, vertLine: { visible: true, labelVisible: true }, horzLine: { visible: true, labelVisible: true } };
      if (cursorMode === "dot") { ch.vertLine.visible = false; ch.horzLine.visible = false; }
      if (cursorMode === "arrow" || cursorMode === "eraser") ch.mode = LC.CrosshairMode.Hidden;
      chart.applyOptions({ crosshair: ch });
    }
    function setTool(t) {
      if (!TOOLS[t]) return;
      tool = t; draft = null; downPx = null;
      if (isCursor(t)) { cursorMode = t; store.set("drawCursor", t); applyCursor(); }
      chartEl.style.cursor = isCursor(t) ? (t === "arrow" || t === "eraser" ? "default" : "crosshair") : "crosshair";
      req(); emit();
    }
    applyCursor();

    let auto = [];
    const api = {
      /** Read-only annotations drawn by a strategy, not by the user: never saved, never
       *  selectable, never erasable, and replaced wholesale on each call. Kept apart from
       *  `items` so "clear drawings" cannot delete them and they cannot be persisted into
       *  someone's saved chart. */
      annotate(list) { auto = (list || []).map((x, i) => ({ ...x, id: `auto-${i}`, auto: true })); req(); },
      clearAnnotations() { auto = []; req(); },
      get tool() { return tool; }, get count() { return items.length; }, opts,
      setTool, undo,
      onChange(fn) { listeners.push(fn); fn(); },
      toggle(k) {
        opts[k] = !opts[k]; store.set("drawOpts", opts);
        if (k === "hide" || k === "lock") { selected = null; renderFtb(); }
        req(); emit();
      },
      /** remove every drawing on this symbol (undoable with ⌘/Ctrl+Z or the toast) */
      clearAll() {
        if (!items.length) return 0;
        const n = items.length;
        snap(); items = []; selected = null; save(); renderFtb(); req(); emit();
        return n;
      },
      destroy() {
        remote && remote.flush && remote.flush();
        chartEl.removeEventListener("mousedown", onDown, true);
        chartEl.removeEventListener("dblclick", onDbl, true);
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
        window.removeEventListener("keydown", onKey);
      },
    };
    return api;
  }

  /** Render the TradingView-style left toolbar into `host` and wire it to `dr`.
   *  `indicators` ({count, removeAll}) lets the trash menu clear indicators too, as in TradingView. */
  function mountToolbar(host, dr, indicators = null) {
    const sel = store.get("drawGroupSel", {});
    const current = (g) => (g[2].includes(sel[g[0]]) ? sel[g[0]] : g[2][0]);
    const title = (t) => TOOLS[t].label + (TOOLS[t].key ? `  (${TOOLS[t].key})` : "");
    host.innerHTML =
      GROUPS.map((g) => `<div class="tgroup" data-g="${g[0]}"><button class="tmain" data-t="${current(g)}" title="${title(current(g))}">${svg(current(g))}</button>` +
        (g[2].length > 1 ? `<button class="tmore" title="${g[1]}">${svg("more")}</button>` : "") + "</div>").join("") +
      `<span class="sep"></span>
       <div class="tgroup"><button class="tmain" data-t="measure" title="${title("measure")}">${svg("measure")}</button></div>
       <span class="sep"></span>
       <button class="ttog" data-o="magnet" title="Magnet mode — snap to the bar's open / high / low / close">${svg("magnet")}</button>
       <button class="ttog" data-o="stay" title="Stay in drawing mode">${svg("stay")}</button>
       <button class="ttog" data-o="lock" title="Lock all drawings">${svg("lock")}</button>
       <button class="ttog" data-o="hide" title="Hide all drawings">${svg("hide")}</button>
       <span class="sep"></span>
       <button class="ttrash" title="Remove drawings">${svg("trash")}</button>
       <div class="tfly" hidden></div>`;
    const fly = host.querySelector(".tfly");
    const closeFly = () => { fly.hidden = true; host.querySelectorAll(".tgroup.open").forEach((g) => g.classList.remove("open")); };
    function openFly(gEl) {
      const g = GROUPS.find((x) => x[0] === gEl.dataset.g);
      fly.innerHTML = `<div class="tfly-h">${g[1]}</div>` + g[2].map((t) =>
        `<button data-t="${t}" class="${dr.tool === t ? "on" : ""}">${svg(t)}<span>${TOOLS[t].label}</span><kbd>${TOOLS[t].key || ""}</kbd></button>`).join("");
      fly.style.top = gEl.offsetTop + "px";
      fly.hidden = false; gEl.classList.add("open");
      fly.dataset.g = g[0];
    }
    host.onclick = (e) => {
      const more = e.target.closest(".tmore");
      if (more) { e.stopPropagation(); const gEl = more.parentElement; const was = !fly.hidden && fly.dataset.g === gEl.dataset.g; closeFly(); if (!was) openFly(gEl); return; }
      const pick = e.target.closest(".tfly button[data-t]");
      if (pick) { sel[fly.dataset.g] = pick.dataset.t; store.set("drawGroupSel", sel); dr.setTool(pick.dataset.t); closeFly(); return; }
      const main = e.target.closest(".tmain");
      if (main) { closeFly(); dr.setTool(main.dataset.t); return; }
      const tog = e.target.closest(".ttog");
      if (tog) { dr.toggle(tog.dataset.o); return; }
      const rm = e.target.closest(".tfly button[data-rm]");
      if (rm) {
        closeFly();
        const what = rm.dataset.rm;
        if (what !== "indicators") {
          const n = dr.clearAll();
          if (n && window.toast) window.toast(`Removed ${n} drawing${n > 1 ? "s" : ""}`, "ok", { label: "Undo", fn: () => { dr.undo(); if (!host.isConnected && window.route) window.route(); } });  // chart rebuilt meanwhile: redraw
        }
        if (what !== "drawings" && indicators) indicators.removeAll();
        return;
      }
      const trash = e.target.closest(".ttrash");
      if (trash) {
        e.stopPropagation();
        if (!fly.hidden && fly.dataset.g === "trash") { closeFly(); return; }
        closeFly();
        const nd = dr.count, ni = indicators ? indicators.count() : 0;
        const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
        fly.innerHTML = `<div class="tfly-h">Remove</div>
          <button data-rm="drawings" ${nd ? "" : "disabled"}>${svg("trash")}<span>Remove ${plural(nd, "drawing")}</span></button>
          ${indicators ? `<button data-rm="indicators" ${ni ? "" : "disabled"}>${svg("trash")}<span>Remove ${plural(ni, "indicator")}</span></button>
          <button data-rm="all" ${nd + ni ? "" : "disabled"}>${svg("trash")}<span>Remove drawings &amp; indicators</span></button>` : ""}`;
        fly.style.top = trash.offsetTop + "px"; fly.dataset.g = "trash"; fly.hidden = false;
      }
    };
    const outside = (e) => { if (!host.contains(e.target)) closeFly(); };
    document.addEventListener("mousedown", outside);
    dr.onChange(() => {
      const t = dr.tool;
      // a tool chosen by hotkey becomes its family's face, as in TradingView
      const g = GROUPS.find((x) => x[2].includes(t));
      if (g && sel[g[0]] !== t) { sel[g[0]] = t; store.set("drawGroupSel", sel); }
      host.querySelectorAll(".tgroup[data-g]").forEach((gEl) => {
        const gg = GROUPS.find((x) => x[0] === gEl.dataset.g), face = current(gg), b = gEl.querySelector(".tmain");
        if (b.dataset.t !== face) { b.dataset.t = face; b.innerHTML = svg(face); b.title = title(face); }
        b.classList.toggle("on", gg[2].includes(t));
      });
      host.querySelector('.tmain[data-t="measure"]').classList.toggle("on", t === "measure");
      host.querySelectorAll(".ttog").forEach((b) => b.classList.toggle("on", !!dr.opts[b.dataset.o]));
      host.querySelector(".ttrash").title = "Remove drawings / indicators";
    });
    return () => document.removeEventListener("mousedown", outside);
  }

  return { create, mountToolbar, TOOLS };
})();
