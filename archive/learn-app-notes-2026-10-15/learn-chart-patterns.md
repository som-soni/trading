# App notes moved out of learn-chart-patterns

## Intro

Learning material: what chart patterns are, how to read the ones that matter
for swing trading, and what the evidence says about them — including this
project's own backtests. It is a companion to
[learn-candlestick-patterns.md](learn-candlestick-patterns.md), which covers
single bars, and to [chart-pattern-spec.md](chart-pattern-spec.md), which
turns every pattern below into exact rules a computer can check.

**Where this shows up in the app.** The `chart_pattern` strategy detects
seven bullish bases on daily data (the code is in
`scripts/swing_screener/core/chart_patterns.py`). For each stock it reports
the one with the best score. Its rules, pivots and stops are on the
Strategies page. The VCP (volatility contraction pattern, described below) is also the
entry pattern of both Minervini strategies. Topping patterns (double top,
head-and-shoulders) are detected as warnings. The chart page is where you
practice spotting them yourself.

## §1 Context decides meaning

This is why the `chart_pattern` strategy only looks at stocks
from the "Near highs, rising 200-day" screen. It is also why its FLAT and
FLAG detectors require a prior advance (≥ 20%) before the base.

## §1 Invalidation

If the
stop is too far away to size a position sensibly, the pattern is not a
trade. (The strategy downgrades exactly these.)

## §1 Shared anatomy

Each pattern below answers the same five questions, in the same order as the
spec: key points → context → geometry → volume → trigger / invalidation /
target. ... The strategy caps it at the real resistance above.

## §2 headings carried detector codes

"Bullish continuation patterns (the ones detected here)"; headings: Cup with handle — `CUP`; Double bottom — `DBOT`;
Flat base / Darvas box — `FLAT`; Bull flag — `FLAG`; Ascending triangle — `ATRI`; Volatility contraction pattern — `VCP`.

- Cup: "The app also detects the **cup without a handle** (`CUPNH`). The cup is the same, but the price is
  still sitting right at the rim, and the pivot is the rim itself."
- Double bottom: "The mirror image at highs — the **double top** — is detected here as a topping warning, not a setup."
- Flat base: "the price moves sideways in a tight box (≤ 15% deep here)." "Measured move: here it adds
  the **prior advance**, not the box height."
- Flag: "The detector scores it higher, because almost only a leading stock ... can produce it."
- Ascending triangle: "Descending and symmetrical triangles exist in the classical catalog (see the spec), but they are not
  setups in this app."
- VCP: "here each is ≤ 0.8× the prior one, and the final one is ≤ 12%." "This is the entry pattern
  of the `minervini` strategy; [minervini-backtest-spec.md](minervini-backtest-spec.md) defines it precisely."

## §3 Topping structures

The app detects these as warnings (in `core/chart_patterns.py`,
`detect_topping`). ... The
`minervini` exit rules include a climax exit for exactly this.

## §4 Reading a breakout

1. ... The `chart_pattern` strategy requires a close above the pivot on at least
   1.4× the 50-day average volume. (The setting is `VOL_CONFIRM`; the
   Strategies page always shows its current value.)
4. ... (The `minervini` strategy exits on exactly that.)
5. ... That is why the strategies downgrade setups when
   the app's market-regime check is negative, and why the app tracks group
   relative strength at all.

## §5 Evidence — the project's own backtests (removed from the guide; work in progress)

- **This project's own backtest** tested all seven detectors together
  (`chart_pattern`, US 2020–2026, a sample of 300 symbols, exits at a fixed
  stop or a fixed target). It **lost money**: −4.08% CAGR against the
  benchmark's +13.63%, and −0.213R per trade over 146 trades. Finding
  textbook shapes and buying at their pivots, exactly as written, had no
  edge in that sample.
- A **random-data check** found that most of the detectors fire regularly on
  random price series. So the shapes alone carry little information. The two
  that are rare in random data (CUP and CUPNH) were split into their own
  strategy (`chart_pattern_cup`). Its backtest came out **inconclusive**
  (−0.019R over 32 trades, t ≈ 0 — the result is statistically
  indistinguishable from zero). That is better than the full set, but not
  shown to be positive.
- ... The
  backtests here test the shapes alone, which is the weaker claim. The
  combined claim is harder to test and is still open (see
  [momentum-trend-research.md](momentum-trend-research.md) for the record of
  what has been tested).

The working conclusion for this project: **patterns are a way to read
structure, stops and triggers — not an edge on their own.**

## §6 Practicing in the app

1. Open a leading stock's chart and find last year's bases yourself
   *before* checking what the detector says. Then run
   `python3 -m swing_screener.screening.inspect --market
   us --symbol NVDA --strategy chart_pattern`. It prints the detected
   pattern, its pivot, stop and score for any symbol.
2. On the Strategies page, open *Classical chart-pattern breakout* → Rules.
   It shows every detector's exact geometry, filled in with the current
   thresholds.
3. Draw the patterns yourself on the chart page: trend lines, horizontal
   pivot lines and measured moves (Alt+T / Alt+H; Shift+drag measures).
4. Read [chart-pattern-spec.md](chart-pattern-spec.md) when the text here
   seems ambiguous. Every rule above has an exact, computer-checkable version
   there.
