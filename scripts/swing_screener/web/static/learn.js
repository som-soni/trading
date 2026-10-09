"use strict";
/* Learn: a visual catalog of candlestick and chart patterns.
 *
 * Every pattern is drawn with real candles. Candlestick patterns list their
 * bars by hand ([open, high, low, close]); chart patterns give a price path of
 * [bar, close] waypoints that `synth` turns into a deterministic OHLCV series
 * (seeded noise, so the picture never changes), plus annotations: pivot / stop /
 * neckline / trend lines and text marks. Levels can be read off the generated
 * candles ({ high: [a, b] } = highest high of bars a..b), so a line always sits
 * exactly on the bars it describes.
 *
 * The long-form guides stay in research/learn-*.md; a ```pattern fence there
 * (one key per block) renders the same drawing via Learn.svg.
 */
const Learn = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const fmt = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>");

  const GROUPS = [
    ["basics", "Basics"],
    ["single", "Single-candle patterns"],
    ["double", "Two-candle patterns"],
    ["triple", "Three-candle patterns"],
    ["bases", "Bullish chart patterns"],
    ["tops", "Topping structures"],
  ];

  // context bars the candlestick examples sit on
  const DOWN = [[110, 111, 107.5, 108], [108.2, 109, 105.6, 106], [106.3, 107, 103.8, 104.4], [104.6, 105.2, 101.9, 102.5], [102.2, 103, 100.4, 101]];
  const UP = [[90, 92.4, 89.5, 92], [91.8, 94.2, 91.3, 93.8], [93.9, 96, 93.2, 95.6], [95.4, 98, 95, 97.6], [97.8, 99.6, 97.2, 99]];
  const RANGE = [[100, 101.5, 99, 100.8], [100.6, 101.6, 99.4, 99.8], [99.9, 101.2, 99.2, 100.9], [100.8, 101.7, 99.8, 100.2], [100.3, 101.4, 99.6, 101]];

  const P = [
    // ------------------------------------------------------------------ basics
    {
      key: "anatomy", group: "basics", name: "Anatomy of a candle", bias: "neutral", bars: 1,
      summary: "One session's auction in four prices: open, high, low, close. The body spans open → close; the wicks mark prices the market visited and rejected.",
      candles: [[95, 107, 87, 101], [102, 105, 89, 93]], hi: [0, 1], wide: true,
      marks: [
        { i: 0, at: "high", text: "High", side: "left" }, { i: 0, y: 104, text: "Upper wick", side: "left" },
        { i: 0, y: 101, text: "Close (green: close > open)", side: "left" }, { i: 0, y: 98, text: "Body", side: "left" }, { i: 0, y: 95, text: "Open", side: "left" },
        { i: 0, y: 91, text: "Lower wick", side: "left" }, { i: 0, at: "low", text: "Low", side: "left" },
        { i: 1, y: 102, text: "Open (red: close < open)", side: "right" }, { i: 1, y: 97.5, text: "Body", side: "right" },
        { i: 1, y: 93, text: "Close", side: "right" },
      ],
      sections: [
        ["Three questions", ["**Body vs range** — a large body means one side controlled the session; a tiny body means a stand-off.",
          "**Close location** — a close in the top third means buyers had the last word; the bottom third, sellers.",
          "**Which wick is long** — a long lower wick means dip-buyers absorbed the selling; a long upper wick, that a rally was sold."]],
        ["Measures used here (`core/patterns.py`)", ["Body % = |close − open| / range — a doji when ≤ 10%.", "Close location = (close − low) / range — top ≥ 0.66, bottom ≤ 0.34.",
          "Long wick = ≥ 2× the body. Gap = open beyond ±0.3% of the prior close.", "Volume ratio = volume / 50-day average — notable above 1.2 or below 0.8."]],
        ["Context first", ["Only read reversal candles **at a level** (a prior low, a moving average, a pivot, a gap edge).",
          "**Trend beats candle** — a bearish candle in a strong uptrend is usually a pause.",
          "**Bigger timeframe, bigger meaning** — a weekly hammer at support outranks five daily candles.",
          "**Volume is half the message** — the same shape on 2× volume is a statement; on 0.6× it is noise."]],
      ],
    },
    // ------------------------------------------------------------------ single
    {
      key: "hammer", group: "single", name: "Hammer", bias: "bull", bars: 1,
      summary: "Long lower wick (≥ 2× the body), close in the top third, after a decline. Sellers drove price down intraday; buyers took it all back.",
      candles: [...DOWN, [100.6, 101.4, 96.2, 101.1], [101.3, 103.4, 101, 103]], hi: [5, 5], confirm: 6,
      lines: [{ y: { low: [5, 5] }, cls: "stop", label: "Stop: hammer low", from: 5 }],
      marks: [{ i: 5, at: "low", text: "Rejected sell-off", side: "below" }],
      sections: [
        ["Where it means something", ["At support after a pullback — the 50-day average, a prior low, a pivot.", "Mid-range it says nothing; after a collapse it is often just the first bounce."]],
        ["Trigger / invalidation", ["Confirmed by the next bar closing above the hammer's body.", "The hammer's low is the natural stop — trading back below it means the rejection failed."]],
        ["Twin", ["The same shape after an **advance** is a hanging man — a warning, and much weaker evidence."]],
      ],
    },
    {
      key: "hanging-man", group: "single", name: "Hanging man", bias: "bear", bars: 1,
      summary: "The hammer's shape — long lower wick, small body near the top — but after an advance. Sellers showed up for the first time; buyers covered it, this time.",
      candles: [...UP, [99.4, 100.2, 95.6, 99.9], [99.5, 99.8, 97.4, 97.8]], hi: [5, 5], confirm: 6,
      lines: [{ y: { high: [5, 5] }, cls: "pivot", label: "Invalid above its high", from: 5 }],
      sections: [
        ["Read it as", ["A warning, not a sell signal — weaker than the hammer is bullish.", "Needs the next bar to close lower (as here) before it means anything."]],
        ["In a swing workflow", ["At most a reason to tighten a stop on an extended position — never a reason to short an uptrend."]],
      ],
    },
    {
      key: "shooting-star", group: "single", name: "Shooting star", bias: "bear", bars: 1,
      summary: "Long upper wick (≥ 2× the body), close in the bottom third, after an advance. Buyers pushed to new highs intraday and were overwhelmed.",
      candles: [...UP, [99.3, 104.2, 99, 99.6], [99.2, 99.5, 97, 97.4]], hi: [5, 5], confirm: 6,
      lines: [{ y: { high: [5, 5] }, cls: "pivot", label: "Invalid above its high", from: 5 }],
      marks: [{ i: 5, at: "high", text: "Rejected rally", side: "above" }],
      sections: [
        ["Where it means something", ["At resistance or after a climactic run.", "Inside a base it is a routine candle."]],
        ["On a breakout day", ["A shooting-star close back under the pivot on breakout volume is the first sign of a **failed breakout**."]],
        ["Twin", ["The same shape after a **decline** is the inverted hammer — mildly bullish, needs confirmation."]],
      ],
    },
    {
      key: "inverted-hammer", group: "single", name: "Inverted hammer", bias: "bull", bars: 1,
      summary: "The shooting star's shape after a decline: buyers probed higher for the first time. Mildly bullish — it needs the next bar to confirm.",
      candles: [...DOWN, [100.8, 104.6, 100.4, 101.2], [101.4, 103.8, 101.1, 103.5]], hi: [5, 5], confirm: 6,
      lines: [{ y: { low: [5, 5] }, cls: "stop", label: "Stop: its low", from: 5 }],
      sections: [["Read it as", ["The first sign that buyers are willing to pay up after a decline.", "Weak on its own; confirmed only by a close above its body on the next bar."]]],
    },
    {
      key: "doji", group: "single", name: "Doji", bias: "neutral", bars: 1,
      summary: "Body ≤ ~10% of the range: open and close nearly equal. A stand-off between buyers and sellers.",
      candles: [...UP, [99.2, 100.8, 97.6, 99.25], [99, 99.4, 96.8, 97.1]], hi: [5, 5], confirm: 6,
      marks: [{ i: 5, at: "high", text: "Open ≈ close", side: "above" }],
      sections: [
        ["Where it means something", ["After a sustained one-way move, on high volume: the buyers who drove the move met equal selling for the first time.", "In a quiet range it says nothing at all."]],
        ["Variants", ["**Gravestone** — long upper wick, close at the low: a failed rally.", "**Dragonfly** — long lower wick, close at the high: a rejected sell-off.", "**Spinning top** — small body, wicks both sides: indecision, a weaker doji."]],
      ],
    },
    {
      key: "gravestone-doji", group: "single", name: "Gravestone doji", bias: "bear", bars: 1,
      summary: "Open, close and low at the same price with a long upper wick: the whole rally of the session was sold. Bearish at highs.",
      candles: [...UP, [99.2, 103.6, 99, 99.25], [99, 99.3, 96.9, 97.2]], hi: [5, 5], confirm: 6,
      lines: [{ y: { high: [5, 5] }, cls: "pivot", label: "Invalid above its high", from: 5 }],
      sections: [["Read it as", ["A failed rally — stronger at resistance or after a climax run, meaningless inside a base."]]],
    },
    {
      key: "dragonfly-doji", group: "single", name: "Dragonfly doji", bias: "bull", bars: 1,
      summary: "Open, close and high at the same price with a long lower wick: the whole sell-off of the session was bought. Bullish at support.",
      candles: [...DOWN, [100.8, 101, 96.6, 100.85], [101, 103.2, 100.8, 102.9]], hi: [5, 5], confirm: 6,
      lines: [{ y: { low: [5, 5] }, cls: "stop", label: "Stop: its low", from: 5 }],
      sections: [["Read it as", ["A rejected sell-off — a doji-shaped hammer. Same rules: at a level, confirmed by the next close."]]],
    },
    {
      key: "spinning-top", group: "single", name: "Spinning top", bias: "neutral", bars: 1,
      summary: "A small body with wicks on both sides: both sides tried and neither won. Indecision — a weaker message than a doji.",
      candles: [...UP, [99.1, 100.9, 97.4, 99.6]], hi: [5, 5],
      sections: [["Read it as", ["A pause. In an orderly pullback, spinning tops near a rising 50-day are what quiet profit-taking looks like."]]],
    },
    {
      key: "marubozu", group: "single", name: "Bullish marubozu", bias: "bull", bars: 1,
      summary: "A body that is (nearly) the whole range, no wicks: buyers controlled the session from the open to the close.",
      candles: [...RANGE, [101.1, 105.9, 101, 105.8]], hi: [5, 5],
      lines: [{ y: { high: [0, 4] }, cls: "pivot", label: "Range high", to: 4 }],
      marks: [{ i: 5, at: "high", text: "Open = low, close = high", side: "above" }],
      sections: [
        ["Where it means something", ["Through a pivot, on heavy volume — exactly the breakout bar you want.", "The commentary calls it a 'plain top-range close' when no other pattern applies."]],
        ["Twin", ["A **bearish marubozu** through support is distribution."]],
      ],
    },
    {
      key: "bear-marubozu", group: "single", name: "Bearish marubozu", bias: "bear", bars: 1,
      summary: "A red body that is the whole range: sellers controlled the session from the open to the close.",
      candles: [...RANGE, [100.9, 101, 96.1, 96.2]], hi: [5, 5],
      lines: [{ y: { low: [0, 4] }, cls: "neck", label: "Range low", to: 4 }],
      sections: [["Read it as", ["Through support on volume: distribution, the opposite of a breakout.", "Wide red marubozus on expanding volume inside a pullback mean the pullback is not orderly."]]],
    },
    {
      key: "nr7", group: "single", name: "NR7 — narrowest range", bias: "neutral", bars: 1,
      summary: "The narrowest high–low range of the last 7 bars. Volatility contracts before it expands — the quiet before the move.",
      candles: [[96, 99.5, 95.5, 99], [99, 101.8, 98.2, 100.6], [100.4, 102, 98.9, 99.6], [99.7, 101.4, 98.6, 100.9], [100.8, 101.9, 99.5, 100], [100.1, 101.3, 99.3, 100.7], [100.2, 100.7, 99.8, 100.4], [100.5, 103.6, 100.3, 103.4]],
      hi: [6, 6], confirm: 7, ctxFrom: 0,
      lines: [{ y: { high: [6, 6] }, cls: "pivot", label: "Trade the break", from: 6 }],
      marks: [{ i: 6, at: "low", text: "Narrowest of 7", side: "below" }],
      sections: [["Read it as", ["Direction-neutral: the direction comes from the break, not from the NR7 itself.",
        "A cluster of NR7s and inside bars near a pivot is the daily-chart version of what the VCP strategies look for."]]],
    },
    // ------------------------------------------------------------------ two-candle
    {
      key: "bullish-engulfing", group: "double", name: "Bullish engulfing", bias: "bull", bars: 2,
      summary: "A down candle, then an up candle whose body opens at or below the prior close and closes at or above the prior open — the second session wipes out the first.",
      candles: [...DOWN, [100.8, 101.2, 98.6, 99], [98.7, 102.6, 98.3, 102.3]], hi: [5, 6],
      lines: [{ y: { low: [5, 6] }, cls: "stop", label: "Stop: pattern low", from: 5 }],
      sections: [
        ["Where it means something", ["At support after a pullback, on rising volume.", "One of the few candle patterns with modest statistical support — and it still fails routinely against the trend."]],
        ["Invalidation", ["A close below the engulfing bar's low."]],
      ],
    },
    {
      key: "bearish-engulfing", group: "double", name: "Bearish engulfing", bias: "bear", bars: 2,
      summary: "An up candle, then a down candle whose body engulfs it: the second session reverses everything the first one gained.",
      candles: [...UP, [99.2, 101.2, 98.9, 100.9], [101.2, 101.6, 97.6, 97.9]], hi: [5, 6],
      lines: [{ y: { high: [5, 6] }, cls: "pivot", label: "Invalid above pattern high", from: 5 }],
      sections: [["Where it means something", ["At highs or resistance; strongest on heavy volume after an extended run.", "In a strong uptrend usually just a pause — tighten a stop, don't short."]]],
    },
    {
      key: "inside-bar", group: "double", name: "Inside bar (harami)", bias: "neutral", bars: 2,
      summary: "The second bar's range sits entirely inside the first's: contraction, the market catching its breath.",
      candles: [...UP, [99, 103, 98.6, 102.6], [102.2, 102.6, 100.4, 101.2], [101.4, 104.4, 101.2, 104.1]], hi: [5, 6], confirm: 7,
      lines: [{ y: { high: [5, 5] }, cls: "pivot", label: "Mother bar high", from: 5 }, { y: { low: [5, 5] }, cls: "stop", label: "Mother bar low", from: 5 }],
      sections: [["Read it as", ["Direction-neutral, like the NR7: trade the break of the mother bar's range, in the direction of the trend.",
        "The classical **harami** is the same idea with bodies: a small body inside the prior large body."]]],
    },
    {
      key: "outside-bar", group: "double", name: "Outside bar", bias: "neutral", bars: 2,
      summary: "The second bar's range engulfs the first's on both sides: expansion. Its close location decides who won.",
      candles: [...RANGE.slice(0, 4), [100.2, 101, 99.6, 100.4], [100.3, 102.4, 98.8, 102.1]], hi: [4, 5],
      marks: [{ i: 5, at: "high", text: "Closes at the top: buyers won", side: "above" }],
      sections: [["Read it as", ["Both sides got stopped out in one session; the close tells you which side ended in control."]]],
    },
    {
      key: "piercing-line", group: "double", name: "Piercing line", bias: "bull", bars: 2,
      summary: "After a decline: a red bar, then a green bar that gaps down and closes above the midpoint of the red body — without engulfing it.",
      candles: [...DOWN, [101.2, 101.5, 97.8, 98], [97.2, 100.4, 96.9, 100.1]], hi: [5, 6],
      lines: [{ y: 99.6, cls: "trend", label: "Midpoint of red body", from: 5 }, { y: { low: [5, 6] }, cls: "stop", label: "Stop: pattern low", from: 5 }],
      sections: [["Read it as", ["Engulfing-lite: same logic as the bullish engulfing, less conviction."]]],
    },
    {
      key: "dark-cloud", group: "double", name: "Dark cloud cover", bias: "bear", bars: 2,
      summary: "After an advance: a green bar, then a red bar that gaps up and closes below the midpoint of the green body.",
      candles: [...UP, [98.8, 102.2, 98.6, 102], [102.8, 103.1, 99.8, 100.1]], hi: [5, 6],
      lines: [{ y: 100.4, cls: "trend", label: "Midpoint of green body", from: 5 }, { y: { high: [5, 6] }, cls: "pivot", label: "Invalid above high", from: 5 }],
      sections: [["Read it as", ["The mirror of the piercing line: a weaker cousin of the bearish engulfing."]]],
    },
    {
      key: "tweezer-bottom", group: "double", name: "Tweezer bottom", bias: "bull", bars: 2,
      summary: "Two consecutive bars with (nearly) equal lows: the same level defended twice in a row.",
      candles: [...DOWN, [101, 101.4, 98.6, 99], [99.1, 101.6, 98.62, 101.3]], hi: [5, 6],
      lines: [{ y: { low: [5, 6] }, cls: "stop", label: "Same low twice", from: 4 }],
      sections: [["Read it as", ["Mostly evidence **for the level**, not a pattern on its own. The mirror at highs is the tweezer top."]]],
    },
    {
      key: "tweezer-top", group: "double", name: "Tweezer top", bias: "bear", bars: 2,
      summary: "Two consecutive bars with (nearly) equal highs: the same ceiling held twice in a row.",
      candles: [...UP, [99, 101.6, 98.8, 101.4], [101.3, 101.62, 99, 99.3]], hi: [5, 6],
      lines: [{ y: { high: [5, 6] }, cls: "pivot", label: "Same high twice", from: 4 }],
      sections: [["Read it as", ["Evidence for a resistance level; it matters when the level is already known (a prior high, a pivot)."]]],
    },
    // ------------------------------------------------------------------ three-candle
    {
      key: "morning-star", group: "triple", name: "Morning star", bias: "bull", bars: 3,
      summary: "The three-act reversal at a low: a strong red bar (sellers in control), a small star that drifts lower (exhaustion), a strong green bar closing well into the first body (buyers take over).",
      candles: [...DOWN, [101.2, 101.5, 97.4, 97.7], [97.2, 97.9, 96.2, 97.4], [97.8, 101.3, 97.6, 101.1]], hi: [5, 7],
      lines: [{ y: { low: [6, 6] }, cls: "stop", label: "Stop: star's low", from: 5 }],
      marks: [{ i: 5, at: "high", text: "1 · sellers", side: "above" }, { i: 6, at: "low", text: "2 · exhaustion", side: "below" }, { i: 7, at: "high", text: "3 · buyers", side: "above" }],
      sections: [["Where it means something", ["At lows, with volume on the third bar.", "The project's **3-bar reversal** flag is a loose version: a close down, then a close back up through the first bar's open."]]],
    },
    {
      key: "evening-star", group: "triple", name: "Evening star", bias: "bear", bars: 3,
      summary: "The mirror at highs: a strong green bar, a small star that gaps higher, then a strong red bar closing deep into the first body.",
      candles: [...UP, [99.1, 102.8, 98.9, 102.6], [103.1, 103.9, 102.6, 103.3], [102.8, 103, 99.2, 99.5]], hi: [5, 7],
      lines: [{ y: { high: [6, 6] }, cls: "pivot", label: "Invalid above star's high", from: 5 }],
      marks: [{ i: 5, at: "low", text: "1 · buyers", side: "below" }, { i: 6, at: "high", text: "2 · stall", side: "above" }, { i: 7, at: "low", text: "3 · sellers", side: "below" }],
      sections: [["Where it means something", ["At highs, after an extended advance — strongest when the third bar comes on heavy volume."]]],
    },
    {
      key: "three-white-soldiers", group: "triple", name: "Three white soldiers", bias: "bull", bars: 3,
      summary: "Three consecutive full-bodied green candles, each closing near its high, after a decline or a base: a genuine change of character.",
      candles: [[101, 101.6, 99.5, 100], [100.1, 100.8, 98.9, 99.4], [99.5, 100.4, 98.7, 100.1], [100, 100.9, 99.2, 99.6], [99.7, 100.5, 99, 100.2],
        [100.3, 102.4, 100.1, 102.2], [102, 104.5, 101.8, 104.3], [104.1, 106.6, 103.9, 106.4]], hi: [5, 7],
      sections: [["Careful late in a move", ["Three *accelerating* white soldiers on expanding volume late in an advance start to look like a **climax run** — see Topping structures."]]],
    },
    {
      key: "three-black-crows", group: "triple", name: "Three black crows", bias: "bear", bars: 3,
      summary: "Three consecutive full-bodied red candles, each closing near its low, after an advance: sellers in control for three sessions running.",
      candles: [...UP, [99.2, 99.4, 96.9, 97.1], [97.3, 97.5, 94.8, 95], [95.2, 95.3, 92.6, 92.8]], hi: [5, 7],
      sections: [["Read it as", ["After an advance, a real change of character; inside a long decline, just more of the same."]]],
    },
    // ------------------------------------------------------------------ chart patterns
    {
      key: "cup-with-handle", group: "bases", name: "Cup with handle", code: "CUP", bias: "bull",
      summary: "The classic O'Neil base: an advance, a rounded correction (not a V), a recovery to the old high, then a small, quiet pullback — the handle — as the last sellers near the rim are absorbed.",
      path: [[0, 72], [4, 78], [8, 86], [12, 100], [15, 95], [18, 89], [22, 83], [26, 79], [30, 77.5], [34, 78.5], [38, 82], [42, 88], [46, 95], [49, 99.3], [51, 97], [53, 94.5], [55, 95.5], [57, 97.5], [58, 98.6], [59, 103.5], [61, 106.5], [63, 108.5]],
      nz: [[0, 1], [12, 1.1], [30, 0.8], [49, 0.9], [51, 0.5], [58, 0.35], [59, 1], [63, 1]],
      vol: [[0, 1.2], [12, 1.4], [30, 0.7], [46, 1], [49, 1], [51, 0.6], [58, 0.45], [59, 2.6], [60, 1.8], [63, 1.2]], seed: 11,
      lines: [{ y: { high: [11, 13] }, cls: "pivot", label: "Pivot = rim", from: 10 }, { y: { low: [51, 58] }, cls: "stop", label: "Stop = handle low", from: 50 }],
      marks: [{ i: 12, at: "high", text: "Left rim", side: "above" }, { i: 30, at: "low", text: "Rounded bottom (12–50% deep)", side: "below" },
        { i: 54, at: "low", text: "Handle: shallow, quiet", side: "below" }, { i: 59, at: "high", text: "Breakout on volume", side: "above" }],
      sections: [
        ["What makes a good one", ["A **rounded** bottom — time spent down there lets weak holders leave.", "A handle in the **upper half** of the cup, drifting down on **below-average volume**.", "A rim at or near the 52-week high."]],
        ["Trigger / invalidation / target", ["Trigger: a close above the right rim on expanding volume.", "Invalidation: the handle low.", "Measured move: the cup's depth projected above the pivot."]],
        ["Red flags", ["V-shaped cups; handles in the lower half or slicing down fast; wide-and-loose structure throughout."]],
        ["In this app", ["Detected as `CUP` by the `chart_pattern` strategy (`core/chart_patterns.py`); split out on its own as `chart_pattern_cup` because, unlike most shapes, it is rare in random data."]],
      ],
    },
    {
      key: "cup-no-handle", group: "bases", name: "Cup without handle", code: "CUPNH", bias: "bull",
      summary: "The same rounded cup, but price breaks out while still pinned to the rim — no pullback handle. The pivot is the rim itself.",
      path: [[0, 72], [4, 78], [8, 86], [12, 100], [15, 95], [18, 89], [22, 83], [26, 79], [30, 77.5], [34, 78.5], [38, 82], [42, 88], [46, 95], [49, 98.6], [50, 98.1], [51, 99], [52, 98.4], [53, 103.5], [55, 106.5], [57, 108]],
      nz: [[0, 1], [12, 1.1], [30, 0.8], [46, 0.8], [49, 0.4], [52, 0.35], [53, 1], [57, 1]],
      vol: [[0, 1.2], [12, 1.4], [30, 0.7], [46, 1], [52, 0.6], [53, 2.4], [54, 1.6], [57, 1.2]], seed: 11,
      lines: [{ y: { high: [11, 13] }, cls: "pivot", label: "Pivot = rim", from: 10 }, { y: { low: [49, 52] }, cls: "stop", label: "Stop: below the shelf", from: 48 }],
      marks: [{ i: 12, at: "high", text: "Left rim", side: "above" }, { i: 30, at: "low", text: "Rounded bottom", side: "below" }, { i: 53, at: "high", text: "Breakout", side: "above" }],
      sections: [
        ["Read it as", ["Strong enough demand that the stock never needed a handle — but the stop is further away than in a handle, so size accordingly."]],
        ["In this app", ["Detected as `CUPNH`; part of `chart_pattern_cup` with the cup with handle."]],
      ],
    },
    {
      key: "double-bottom", group: "bases", name: "Double bottom", code: "DBOT", bias: "bull",
      summary: "A 'W': two sell-offs to the same area; the second finds no new sellers. Ideally it undercuts the first low slightly — the shakeout that clears the last stops — and recovers at once.",
      path: [[0, 100], [6, 92], [12, 84], [16, 80], [20, 86], [24, 91], [28, 93], [32, 88], [36, 82.5], [38, 79.2], [40, 83], [44, 88], [47, 91.5], [49, 92.4], [50, 96], [52, 98.5], [54, 100]],
      nz: [[0, 1], [49, 0.7], [50, 1]], vol: [[0, 1.1], [16, 1.4], [28, 0.9], [38, 1.3], [44, 0.8], [49, 0.7], [50, 2.3], [52, 1.4], [54, 1.1]], seed: 5,
      lines: [{ y: { high: [27, 29] }, cls: "pivot", label: "Pivot = middle peak", from: 26 }, { y: { low: [37, 39] }, cls: "stop", label: "Stop = second low", from: 36 }],
      marks: [{ i: 16, at: "low", text: "Low 1", side: "below" }, { i: 38, at: "low", text: "Low 2 undercuts: shakeout", side: "below" },
        { i: 28, at: "high", text: "Middle peak", side: "above" }, { i: 50, at: "high", text: "Breakout", side: "above" }],
      sections: [
        ["Trigger / invalidation / target", ["Trigger: the middle peak between the lows.", "Invalidation: the second low.", "Measured move: middle peak minus the low, projected up."]],
        ["In this app", ["Detected as `DBOT` (lows within 5%; an undercut scores higher). The mirror at highs — the double top — is a topping warning, not a setup."]],
      ],
    },
    {
      key: "flat-base", group: "bases", name: "Flat base / Darvas box", code: "FLAT", bias: "bull",
      summary: "The strongest stocks barely pull back at all: after an advance, price moves sideways in a tight box while time, not price, does the correcting.",
      path: [[0, 70], [5, 76], [10, 84], [14, 92], [16, 96], [18, 94.5], [21, 95.8], [24, 93.8], [27, 96.2], [30, 94.2], [33, 96], [36, 94.6], [39, 96.3], [41, 95.6], [42, 99.5], [44, 102.5], [46, 104]],
      nz: [[0, 1.2], [15, 1], [16, 0.55], [41, 0.5], [42, 1], [46, 1]], vol: [[0, 1.4], [15, 1.5], [17, 0.9], [41, 0.6], [42, 2.3], [43, 1.6], [46, 1.2]], seed: 3,
      lines: [{ y: { high: [16, 41] }, cls: "pivot", label: "Pivot = box high", from: 15 }, { y: { low: [17, 41] }, cls: "stop", label: "Stop = box low", from: 15 }],
      marks: [{ i: 4, at: "low", text: "Prior advance ≥ 20%", side: "left" }, { i: 28, at: "low", text: "Box ≤ 15% deep", side: "below" }, { i: 42, at: "high", text: "Breakout", side: "above" }],
      sections: [
        ["Read it as", ["Boxes stack — a breakout from one box becomes the floor of the next (Darvas's original observation)."]],
        ["Trigger / invalidation / target", ["Trigger: the box high. Invalidation: the box low.", "Measured move: the **prior advance**, not the box height — a tight box's own height is too small to be a target."]],
        ["In this app", ["Detected as `FLAT`; demands a prior advance of 20% or more."]],
      ],
    },
    {
      key: "bull-flag", group: "bases", name: "Bull flag", code: "FLAG", bias: "bull",
      summary: "A near-vertical advance (the pole), then a short, shallow drift against it (the flag) that retraces less than half the pole.",
      path: [[0, 80], [3, 81], [5, 84], [7, 89], [9, 95], [11, 101], [13, 106], [14, 108], [16, 106.5], [18, 104.5], [20, 105.2], [22, 103], [24, 103.8], [26, 102], [27, 103], [28, 109], [30, 112]],
      nz: [[0, 1], [14, 0.9], [15, 0.6], [27, 0.5], [28, 1], [30, 1]], vol: [[0, 1], [4, 1.8], [13, 2], [15, 0.8], [27, 0.5], [28, 2.4], [29, 1.6], [30, 1.3]], seed: 9,
      lines: [{ a: [14, { high: [14, 14] }], b: [27, { high: [26, 27] }], cls: "trend", label: "Flag" }, { a: [16, { low: [15, 17] }], b: [26, { low: [25, 26] }], cls: "trend" },
        { y: { high: [13, 15] }, cls: "pivot", label: "Pivot = pole high", from: 12 }, { y: { low: [22, 27] }, cls: "stop", label: "Stop = flag low", from: 21 }],
      marks: [{ i: 5, at: "low", text: "Pole: +20% or more, fast", side: "left" }, { i: 28, at: "high", text: "Breakout", side: "above" }],
      sections: [
        ["Trigger / invalidation / target", ["Trigger: the pole high. Invalidation: the flag low.", "Measured move: the pole height — 'flags fly at half mast'."]],
        ["In this app", ["Detected as `FLAG` (flag retraces ≤ 40% of the pole)."]],
      ],
    },
    {
      key: "high-tight-flag", group: "bases", name: "High tight flag", code: "FLAG", bias: "bull",
      summary: "The rare, famous flag: a gain of 80%+ in a few weeks, then a pullback of 25% or less. Almost nothing but a leader under heavy accumulation can draw it.",
      path: [[0, 50], [3, 52], [6, 60], [9, 70], [12, 80], [14, 88], [16, 94], [17, 95], [19, 91.5], [21, 88], [23, 90], [25, 87.5], [27, 90.5], [28, 92], [29, 99], [31, 103]],
      nz: [[0, 1], [16, 1], [18, 0.7], [28, 0.5], [29, 1]], vol: [[0, 1], [5, 2], [16, 2.2], [18, 0.9], [28, 0.5], [29, 2.6], [31, 1.5]], seed: 4,
      lines: [{ y: { high: [16, 18] }, cls: "pivot", label: "Pivot = pole high", from: 15 }, { y: { low: [24, 28] }, cls: "stop", label: "Stop = flag low", from: 18 }],
      marks: [{ i: 6, at: "low", text: "+80% pole", side: "left" }, { i: 22, at: "low", text: "Pullback ≤ 25%", side: "below" }, { i: 29, at: "high", text: "Breakout", side: "above" }],
      sections: [["Evidence", ["Bulkowski's best performer — exactly because it is rare and strict. The detector scores it above an ordinary flag."]]],
    },
    {
      key: "ascending-triangle", group: "bases", name: "Ascending triangle", code: "ATRI", bias: "bull",
      summary: "Flat resistance tested repeatedly from below, with rising lows squeezing price into the corner: sellers sit at one price, buyers get more impatient on every dip.",
      path: [[0, 82], [4, 88], [8, 95], [10, 99.6], [13, 95], [16, 90.5], [19, 95.5], [22, 99.7], [25, 96.5], [27, 94], [30, 97.5], [32, 99.7], [34, 97.7], [36, 96.4], [38, 98.4], [39, 99.4], [40, 103.5], [42, 106]],
      nz: [[0, 1], [10, 0.8], [39, 0.5], [40, 1]], vol: [[0, 1.2], [10, 1.1], [39, 0.6], [40, 2.4], [42, 1.4]], seed: 8,
      lines: [{ y: { high: [9, 39] }, cls: "pivot", label: "Resistance = pivot", from: 9 }, { a: [16, { low: [16, 16] }], b: [36, { low: [36, 36] }], cls: "trend", label: "Rising lows" },
        { y: { low: [35, 37] }, cls: "stop", label: "Stop = last rising low", from: 33 }],
      marks: [{ i: 40, at: "high", text: "Breakout", side: "above" }],
      sections: [
        ["Trigger / invalidation / target", ["Trigger: the resistance line. Invalidation: the last rising low.", "Measured move: the triangle's height at its left edge."]],
        ["In this app", ["Detected as `ATRI` (last 3 swing highs within 3%). Descending and symmetrical triangles exist but are not setups here."]],
      ],
    },
    {
      key: "vcp", group: "bases", name: "Volatility contraction (VCP)", code: "VCP", bias: "bull",
      summary: "Minervini's generalization: what matters is not the shape's name but that each pullback is shallower than the last, on drying-up volume, ending in a tight shelf near the highs.",
      path: [[0, 70], [6, 82], [11, 100], [16, 90], [20, 75], [24, 84], [28, 93], [31, 98.5], [34, 93], [37, 87], [40, 92], [43, 97.5], [45, 95], [47, 92.6], [49, 95], [51, 98], [52, 96.6], [53, 95.3], [54, 96.4], [55, 97.4], [56, 102.5], [58, 105.5]],
      nz: [[0, 1.2], [11, 1.4], [28, 1], [43, 0.7], [51, 0.4], [55, 0.25], [56, 1.1], [58, 1]], vol: [[0, 1.3], [11, 1.6], [20, 1.3], [31, 0.9], [43, 0.7], [51, 0.5], [55, 0.35], [56, 2.5], [58, 1.5]], seed: 2,
      lines: [{ y: { high: [50, 55] }, cls: "pivot", label: "Pivot", from: 41 }, { y: { low: [52, 55] }, cls: "stop", label: "Stop = last low", from: 50 }],
      marks: [{ i: 20, at: "low", text: "−25%", side: "below" }, { i: 37, at: "low", text: "−12%", side: "below" }, { i: 47, at: "low", text: "−5%", side: "below" },
        { i: 53, at: "low", text: "−3%", side: "below" }, { i: 56, at: "high", text: "Breakout", side: "above" }],
      sections: [
        ["Rules here", ["Each contraction ≤ 0.8× the prior one; the final one ≤ 12%.", "Volume dries up into the right side; the breakout comes on expansion."]],
        ["Why traders like it", ["The stop is **close** — the final contraction's low — so even a modest move pays a high reward:risk."]],
        ["In this app", ["The entry pattern of `minervini` and `minervini_spec`. A cup with handle *is* a two-contraction VCP; a high tight flag is a one-contraction VCP."]],
      ],
    },
    // ------------------------------------------------------------------ tops
    {
      key: "double-top", group: "tops", name: "Double top", bias: "bear",
      summary: "Two rallies to the same area, the second on weaker volume; confirmed when the valley between them breaks. The mirror of the double bottom.",
      path: [[0, 70], [6, 80], [12, 92], [16, 100], [20, 94], [24, 88], [28, 93], [32, 99.4], [34, 99.7], [37, 94], [40, 89.5], [42, 88.5], [43, 85.5], [45, 82], [47, 83.5], [49, 80]],
      vol: [[0, 1.2], [16, 1.7], [24, 1], [32, 0.75], [37, 1], [42, 1.1], [43, 2], [49, 1.4]], seed: 6,
      lines: [{ y: { low: [23, 25] }, cls: "neck", label: "Confirm: valley breaks", from: 18 }],
      marks: [{ i: 16, at: "high", text: "Top 1", side: "above" }, { i: 34, at: "high", text: "Top 2, weaker volume", side: "above" }, { i: 43, at: "low", text: "Breakdown", side: "below" }],
      sections: [["In this app", ["A topping warning (`detect_topping` in `core/chart_patterns.py`): a bullish base should not be bought while a topping structure is active above it."]]],
    },
    {
      key: "head-and-shoulders", group: "tops", name: "Head and shoulders", bias: "bear",
      summary: "Three rallies — the middle one highest — with the third failing below the second: the first lower high after an advance, the definition of a trend losing its structure.",
      path: [[0, 70], [6, 80], [10, 88], [13, 84], [16, 82], [20, 90], [24, 98], [26, 100], [29, 92], [32, 85.5], [34, 84], [37, 88], [40, 92], [42, 91], [45, 87], [47, 85.4], [48, 82], [50, 80], [52, 78]],
      vol: [[0, 1.1], [10, 1.4], [26, 1.3], [40, 0.8], [47, 1], [48, 2], [52, 1.3]], seed: 13,
      lines: [{ a: [16, { low: [15, 17] }], b: [34, { low: [33, 35] }], cls: "neck", label: "Neckline", extend: 52 }],
      marks: [{ i: 10, at: "high", text: "Left shoulder", side: "above" }, { i: 26, at: "high", text: "Head", side: "above" }, { i: 40, at: "high", text: "Right shoulder: lower high", side: "above" },
        { i: 48, at: "low", text: "Neckline break", side: "below" }],
      sections: [["Confirmation and target", ["Confirmed on the neckline break; the measured move (head to neckline) projects downward.", "Detected here as a topping warning."]]],
    },
    {
      key: "climax-run", group: "tops", name: "Climax run", bias: "bear",
      summary: "Not a geometric pattern: after a long advance, the steepest rally of the whole move — biggest gains, widest bars, gaps, often on record volume. It marks the moment the last buyers arrive.",
      path: [[0, 60], [10, 68], [20, 76], [30, 85], [33, 90], [35, 96], [37, 104], [38, 111], [39, 118], [40, 123], [41, 119], [43, 113], [45, 109], [47, 106], [49, 103]],
      nz: [[0, 0.8], [30, 0.8], [36, 1.6], [40, 2.2], [43, 1.4], [49, 1]], vol: [[0, 0.9], [30, 1], [35, 1.8], [39, 3], [40, 3.6], [41, 2.6], [44, 1.4], [49, 1.1]], seed: 21,
      marks: [{ i: 37, at: "low", text: "Steepest leg of the move", side: "below" }, { i: 40, at: "high", text: "Record volume, widest bars", side: "above" }, { i: 44, at: "low", text: "The reversal", side: "below" }],
      sections: [["What to do", ["Minervini and O'Neil both sell *into* strength here; the `minervini_spec` exit rules include a climax exit for exactly this."]]],
    },
  ];
  const BY = Object.fromEntries(P.map((p) => [p.key, p]));

  // ------------------------------------------------------------------ synthesis
  /** deterministic OHLCV from a chart pattern's waypoints */
  function synth(p) {
    const n = p.path.at(-1)[0] + 1;
    let s = p.seed || 7;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647) - 0.5;
    const at = (pts, x, d) => {
      if (!pts) return d;
      for (let k = 1; k < pts.length; k++) if (x <= pts[k][0]) {
        const [x0, y0] = pts[k - 1], [x1, y1] = pts[k];
        return x1 === x0 ? y1 : y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
      }
      return pts.at(-1)[1];
    };
    const way = new Set(p.path.map((w) => w[0]));
    const out = [];
    let prev = at(p.path, 0);
    for (let i = 0; i < n; i++) {
      const base = at(p.path, i), nz = 0.012 * base * at(p.nz, i, 1);
      const c = way.has(i) ? base : base + rnd() * nz * 1.2;
      const o = i === 0 ? c - nz * 0.4 : prev + rnd() * nz * 0.7;
      const h = Math.max(o, c) + (Math.abs(rnd()) + 0.15) * nz * 0.9, l = Math.min(o, c) - (Math.abs(rnd()) + 0.15) * nz * 0.9;
      const v = p.vol ? at(p.vol, i, 1) * (1 + rnd() * 0.35) * (c >= o ? 1.08 : 0.92) : null;
      out.push([o, h, l, c, v]);
      prev = c;
    }
    return out;
  }
  const cache = new Map();
  const candlesOf = (p) => { if (!cache.has(p.key)) cache.set(p.key, p.candles || synth(p)); return cache.get(p.key); };

  // ------------------------------------------------------------------ drawing
  /** an SVG drawing of pattern p; thumb = small card version (no text, no volume) */
  function svg(p, { thumb = false } = {}) {
    const cs = candlesOf(p), n = cs.length;
    const lvl = (v) => typeof v === "number" ? v : v.high ? Math.max(...cs.slice(v.high[0], v.high[1] + 1).map((c) => c[1])) : Math.min(...cs.slice(v.low[0], v.low[1] + 1).map((c) => c[2]));
    const hasVol = !thumb && cs.some((c) => c[4] != null);
    const short = !p.path;                                      // a handful of hand-written candles
    const W = thumb ? 420 : short ? 640 : 760, PH = thumb ? 260 : short ? 360 : 340, VH = hasVol ? 78 : 0, H = PH + VH;
    const L = thumb ? 10 : p.wide ? 210 : 18, R = thumb ? 10 : p.wide ? 210 : (p.lines?.some((x) => x.label) ? 150 : 18);
    const T = thumb ? 12 : 30, B = thumb ? 12 : 30;
    const prices = cs.flatMap((c) => [c[1], c[2]]).concat((p.lines || []).flatMap((x) => x.y != null ? [lvl(x.y)] : [lvl(x.a[1]), lvl(x.b[1])]));
    let lo = Math.min(...prices), hi = Math.max(...prices);
    const pad = (hi - lo) * 0.06; lo -= pad; hi += pad;
    const slot = (W - L - R) / n, bw = Math.max(2, Math.min(short ? 34 : 14, slot * 0.64));
    const X = (i) => L + slot * (i + 0.5), Y = (v) => T + ((hi - v) / (hi - lo)) * (PH - T - B);
    const f = (v) => v.toFixed(1);
    const dim = (i) => p.hi && (i < p.hi[0] || i > p.hi[1]) && i !== p.confirm;
    let g = "";
    const side = [];
    // pattern / confirmation bands
    if (p.hi && !p.wide) {
      const x0 = X(p.hi[0]) - slot / 2, x1 = X(p.hi[1]) + slot / 2;
      g += `<rect class="lp-band" x="${f(x0)}" y="${T - 18}" width="${f(x1 - x0)}" height="${PH - T + 6}" rx="6"/>`;
      if (!thumb) g += `<text class="lp-bandl" x="${f((x0 + x1) / 2)}" y="${T - 6}" text-anchor="middle">${p.hi[1] > p.hi[0] ? "pattern" : "signal"}</text>`;
      if (p.confirm != null) {
        const c0 = X(p.confirm) - slot / 2;
        g += `<rect class="lp-band conf" x="${f(c0)}" y="${T - 18}" width="${f(slot)}" height="${PH - T + 6}" rx="6"/>`;
        if (!thumb) g += `<text class="lp-bandl" x="${f(c0 + slot / 2)}" y="${T - 6}" text-anchor="middle">confirm</text>`;
      }
    }
    // lines: horizontal levels and two-point trend lines
    for (const ln of p.lines || []) {
      let x1, y1, x2, y2;
      if (ln.y != null) { const v = lvl(ln.y); x1 = X(ln.from ?? 0) - slot / 2; x2 = X(ln.to ?? n - 1) + slot / 2; y1 = y2 = Y(v); }
      else {
        const [ia, va] = ln.a, [ib, vb] = ln.b, ya = lvl(va), yb = lvl(vb), ie = ln.extend ?? ib;
        x1 = X(ia); y1 = Y(ya); x2 = X(ie); y2 = Y(ya + ((yb - ya) * (ie - ia)) / (ib - ia));
      }
      g += `<line class="lp-ln ${ln.cls}" x1="${f(x1)}" y1="${f(y1)}" x2="${f(x2)}" y2="${f(y2)}"/>`;
      if (ln.label && !thumb) {
        if (x2 >= X(n - 1) - 1) side.push({ y: y2, cls: ln.cls, text: ln.label });     // ends at the last bar: label in the right margin
        else g += `<text class="lp-lnl ${ln.cls}" x="${f(x2)}" y="${f(y2 - 6)}" text-anchor="end">${esc(ln.label)}</text>`;
      }
    }
    // right-margin labels, pushed apart so close levels (pivot just above stop) stay readable
    side.sort((a, b) => a.y - b.y).forEach((t, k) => { if (k) t.y = Math.max(t.y, side[k - 1].y + 15); });
    for (const t of side) g += `<text class="lp-lnl ${t.cls}" x="${f(W - R + 8)}" y="${f(t.y + 4)}">${esc(t.text)}</text>`;
    // candles
    cs.forEach(([o, h, l, c], i) => {
      const cls = `${c >= o ? "up" : "dn"}${dim(i) ? " ctx" : ""}`, x = X(i), yt = Y(Math.max(o, c)), yb = Y(Math.min(o, c));
      g += `<g class="lp-c ${cls}"><line x1="${f(x)}" y1="${f(Y(h))}" x2="${f(x)}" y2="${f(Y(l))}"/><rect x="${f(x - bw / 2)}" y="${f(yt)}" width="${f(bw)}" height="${f(Math.max(1, yb - yt))}" rx="${short ? 1.5 : 0.5}"/></g>`;
    });
    // text marks
    if (!thumb) for (const m of p.marks || []) {
      const c = cs[m.i], x = X(m.i);
      if (m.side === "left" || m.side === "right") {
        const v = m.at === "high" ? c[1] : m.at === "low" ? c[2] : m.y, y = Y(v), dx = m.side === "left" ? -1 : 1, x0 = x + dx * (bw / 2 + 4), x1 = x + dx * (bw / 2 + 46);
        g += `<line class="lp-ml" x1="${f(x0)}" y1="${f(y)}" x2="${f(x1)}" y2="${f(y)}"/><text class="lp-mt" x="${f(x1 + dx * 5)}" y="${f(y + 4)}" text-anchor="${dx < 0 ? "end" : "start"}">${esc(m.text)}</text>`;
      } else {
        const above = m.side === "above", y = above ? Y(c[1]) - 8 : Y(c[2]) + 8, ty = above ? y - 6 : y + 15;
        const tx = Math.max(L + 4, Math.min(W - R - 4, x)), anchor = tx < x - 1 ? "end" : tx > x + 1 ? "start" : "middle";
        g += `<line class="lp-ml" x1="${f(x)}" y1="${f(y)}" x2="${f(x)}" y2="${f(above ? y - 2 : y + 2)}"/><text class="lp-mt" x="${f(x)}" y="${f(ty)}" text-anchor="${anchor === "middle" ? (x < L + 70 ? "start" : x > W - R - 70 ? "end" : "middle") : anchor}">${esc(m.text)}</text>`;
      }
    }
    // volume pane
    if (hasVol) {
      const vmax = Math.max(...cs.map((c) => c[4] || 0)), v0 = PH + 8, vh = VH - 14;
      g += `<line class="lp-sep" x1="${L}" y1="${PH}" x2="${W - R}" y2="${PH}"/><text class="lp-vl" x="${L}" y="${PH + 14}">Volume</text>`;
      cs.forEach(([o, , , c, v], i) => { if (v == null) return; const hh = (v / vmax) * vh;
        g += `<rect class="lp-v ${c >= o ? "up" : "dn"}" x="${f(X(i) - bw / 2)}" y="${f(v0 + vh - hh)}" width="${f(bw)}" height="${f(hh)}"/>`; });
    }
    return `<svg class="lp${thumb ? " thumb" : ""}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${esc(p.name)}">${g}</svg>`;
  }

  const BIAS = { bull: ["Bullish", "up"], bear: ["Bearish", "dn"], neutral: ["Neutral", "flat"] };

  /** the detail view of one pattern */
  function detail(p) {
    const i = P.indexOf(p), prev = P[i - 1], next = P[i + 1], [bl, bc] = BIAS[p.bias];
    const meta = [`<span class="lp-bias ${bc}">${bl}</span>`, p.bars ? `<span class="chip-s">${p.bars} bar${p.bars > 1 ? "s" : ""}</span>` : "",
      p.code ? `<span class="chip-s" title="detector code in core/chart_patterns.py">${esc(p.code)}</span>` : "",
      `<span class="muted small">${esc(GROUPS.find((x) => x[0] === p.group)[1])}</span>`].join("");
    const legend = p.path ? `<div class="lp-legend small muted"><span><i class="pivot"></i>pivot / trigger</span><span><i class="stop"></i>stop / invalidation</span>${p.lines?.some((x) => x.cls === "neck") ? '<span><i class="neck"></i>breakdown level</span>' : ""}<span>Illustration — idealized, not real data</span></div>`
      : p.hi && !p.wide ? `<div class="lp-legend small muted"><span>Faded candles = the context the pattern forms in</span>${p.confirm != null ? "<span>“confirm” = the next bar that validates it</span>" : ""}</div>` : "";
    return `<div class="lp-head"><h2>${esc(p.name)}</h2>${meta}</div>
      <p class="lp-sum">${fmt(p.summary)}</p>
      <section class="sec-card lp-fig">${svg(p)}${legend}</section>
      <div class="lp-secs">${(p.sections || []).map(([h, items]) => `<section class="sec-card"><h3>${esc(h)}</h3><ul>${items.map((x) => `<li>${fmt(x)}</li>`).join("")}</ul></section>`).join("")}</div>
      <div class="lp-pn">${prev ? `<a href="#/learn/${prev.key}">← ${esc(prev.name)}</a>` : "<span></span>"}${next ? `<a href="#/learn/${next.key}">${esc(next.name)} →</a>` : ""}</div>`;
  }

  // the two families the menu switches between
  const FAMILIES = { candles: ["basics", "single", "double", "triple"], charts: ["bases", "tops"] };
  const familyOf = (p) => (FAMILIES.charts.includes(p.group) ? "charts" : "candles");
  const groupsOf = (fam) => GROUPS.filter(([g]) => !fam || FAMILIES[fam].includes(g));

  /** the overview: every pattern (or one family's) as a thumbnail card, grouped */
  function overview(fam) {
    return groupsOf(fam).map(([g, label]) => `<h3 class="lp-gh">${esc(label)}</h3><div class="lp-grid">${P.filter((p) => p.group === g).map((p) =>
      `<a class="lp-card sec-card" href="#/learn/${p.key}">${svg(p, { thumb: true })}<div><b>${esc(p.name)}</b><span class="lp-bias ${BIAS[p.bias][1]}">${BIAS[p.bias][0]}</span></div></a>`).join("")}</div>`).join("");
  }

  /** the side menu: one family's patterns by group, the active one highlighted */
  function nav(active, fam) {
    return groupsOf(fam).map(([g, label]) => `<div class="nav-h">${esc(label)}</div>` + P.filter((p) => p.group === g).map((p) =>
      `<a class="nav-item ${p.key === active ? "active" : ""}" href="#/learn/${p.key}" data-k="${esc((p.name + " " + (p.code || "")).toLowerCase())}"><span><b class="sn"><i class="lp-dot ${BIAS[p.bias][1]}"></i>${esc(p.name)}</b></span></a>`).join("")).join("");
  }

  return { GROUPS, PATTERNS: P, familyOf, get: (k) => BY[k], svg, detail, overview, nav };
})();
