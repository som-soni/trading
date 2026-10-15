# Chart patterns — a field guide

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

---

## 1. What a pattern is — and is not

A chart pattern is a **consolidation that tells a story about supply and
demand**. After an advance, some holders take profits. The price pulls back
until buyers who missed the move have bought up the shares being sold. If
large investors are steadily buying the stock (accumulation), each wave of
selling is smaller than the last. The pattern "tightens". Eventually few
sellers are left, and a small amount of buying pushes the price through the
old high. That is the whole theory. Every bullish continuation pattern below
is a variation of it.

Three consequences follow:

1. **Context decides meaning.** After an advance, a shape is a
   *continuation* pattern: a pause before the uptrend carries on. The same
   shape after a decline is a *bear rally*: a short bounce inside a
   downtrend. This is why the `chart_pattern` strategy only looks at stocks
   from the "Near highs, rising 200-day" screen. It is also why its FLAT and
   FLAG detectors require a prior advance (≥ 20%) before the base.
2. **A pattern is only complete at its trigger.** Until the price breaks the
   pivot, a cup-with-handle is just a stock that went down and came back up.
   Most of the information is in *how* the breakout happens — the volume,
   where the bar closes in its range, and whether the price keeps going —
   not in the shape alone.
3. **Every pattern needs an invalidation level.** This is the low in the
   pattern that, if broken, proves the story wrong — the handle low, the
   second bottom, the flag low. That level is where the stop belongs. If the
   stop is too far away to size a position sensibly, the pattern is not a
   trade. (The strategy downgrades exactly these.)

### The shared anatomy

Each pattern below answers the same five questions, in the same order as the
spec: key points → context → geometry → volume → trigger / invalidation /
target. For targets, the classical rule is the **measured move**: add the
pattern's height (or the height of the prior advance, the "pole") to the
pivot. Treat it as a first estimate, not a promise. The strategy caps it at
the real resistance above.

---

## 2. Bullish continuation patterns (the ones detected here)

### Cup with handle — `CUP`

The classic base described by William O'Neil. First an advance. Then a
rounded correction (not a sharp V). Then a recovery to the old high. Then a
small, quiet pullback — the handle — while the last sellers near the rim (the
old high) sell their shares to new buyers.

```pattern
cup-with-handle
```

What makes a *good* cup:

- a rounded bottom — the stock spends time down there, because the nervous
  holders need time to sell and leave;
- a handle in the **upper half** of the cup that drifts down on
  **below-average volume**;
- a rim at or near the 52-week high.

Red flags: V-shaped cups, handles that form in the lower half or drop fast,
and wide, choppy price swings throughout.

Trigger: a close above the right rim on rising volume. Invalidation: the
handle low. Measured move: the cup's depth. The app also detects the
**cup without a handle** (`CUPNH`). The cup is the same, but the price is
still sitting right at the rim, and the pivot is the rim itself.

### Double bottom — `DBOT`

A "W" shape. The price sells off to the same area twice. The second time, no
new sellers appear. Ideally the second low dips slightly *below* the first
low and then recovers at once. That dip is a shakeout: it triggers the last
stop orders sitting under the first low, and once those shares are sold the
selling is done.

```pattern
double-bottom
```

Trigger: the middle peak between the two lows. Invalidation: the second low.
Measured move: the middle peak minus the low. The mirror image at highs — the
**double top** — is detected here as a topping warning, not a setup.

### Flat base / Darvas box — `FLAT`

The strongest stocks barely pull back at all. After an advance, the price
moves sideways in a tight box (≤ 15% deep here). The stock works off its
gain through time spent going sideways, rather than through a fall in price.
Boxes stack: a breakout from one box becomes the floor of the next. That was
Nicolas Darvas's original observation.

```pattern
flat-base
```

Trigger: the box high. Invalidation: the box low. Measured move: here it adds
the **prior advance**, not the box height. A tight box's own height is too
small to be a useful target.

### Bull flag — `FLAG`

A near-vertical advance (the pole), then a short, shallow drift downward (the
flag). In the textbook case the flag gives back less than half the pole, over
a few weeks. The rare, famous variant is the **high tight flag**: a gain of
80%+, of which 25% or less is given back. The detector scores it higher,
because almost only a leading stock that big investors are buying heavily
can produce it.

```pattern
bull-flag
```

Trigger: the pole high. Invalidation: the flag low. Measured move: the pole
height. The old saying is that "flags fly at half mast": the flag sits
halfway up, and the move after it repeats the pole.

### Ascending triangle — `ATRI`

A flat resistance line that the price tests again and again from below,
while the lows keep **rising**. The price gets squeezed into the corner.
Sellers wait at one fixed price. Buyers are willing to pay more on every dip.

```pattern
ascending-triangle
```

Trigger: the resistance line. Invalidation: the last rising low. Measured
move: the triangle's height at its left edge. Descending and symmetrical
triangles exist in the classical catalog (see the spec), but they are not
setups in this app. The ascending form has the clearest bullish logic.

### Volatility contraction pattern — `VCP`

Mark Minervini's general version of all of the above. What matters is not
the shape's name. What matters is that **each pullback is shallower than the
one before** — here each is ≤ 0.8× the prior one, and the final one is
≤ 12%. Volume shrinks as this happens. The pattern ends in a tight, flat
stretch near the highs. A cup-with-handle *is* a VCP with two contractions
(the cup, then the smaller handle). A high tight flag is a VCP with one.

```pattern
vcp
```

Trigger: the final contraction's high. Invalidation: the final contraction's
low. That is what makes VCPs attractive: the stop is *close*, so even a
modest move pays a lot compared with what you risk. This is the entry pattern
of the `minervini` strategy;
[minervini-backtest-spec.md](minervini-backtest-spec.md) defines it
precisely.

---

## 3. Topping structures — patterns that say get out

The app detects these as warnings (in `core/chart_patterns.py`,
`detect_topping`). A bullish base should never be bought while a topping
pattern is in force above it.

- **Double top.** Two rallies to the same area, the second on weaker volume.
  It is confirmed when the price breaks below the low point between them. The
  logic is the mirror of the double bottom.
- **Head and shoulders top.** Three rallies, with the middle one the highest.
  The third rally fails below the second. That is the first *lower high*
  after an advance — which is the definition of an uptrend starting to break
  down. It is confirmed when the price breaks the neckline (the line through
  the lows between the rallies). The measured move then points downward.
- **Climax run.** This is not a geometric pattern. After a long advance, the
  price makes the steepest rally of the whole move: the biggest weekly gains,
  the widest bars, gaps that the price soon falls back into (exhaustion
  gaps), often on record volume. It marks the moment the last buyers arrive.
  Minervini and O'Neil both sell *while the price is still rising* here. The
  `minervini` exit rules include a climax exit for exactly this.

---

## 4. Reading a breakout

The pattern makes the stock worth watching. The breakout is the actual trade.
Here is what separates a real breakout from a false one, roughly in order of
importance:

1. **Volume.** On the breakout day, volume should be clearly above average.
   The `chart_pattern` strategy requires a close above the pivot on at least
   1.4× the 50-day average volume. (The setting is `VOL_CONFIRM`; the
   Strategies page always shows its current value.) A pivot cleared on low
   volume is more likely to fail.
2. **Where it closes.** You want a full-bodied close above the pivot, near
   the day's high (see the candlestick guide). Not a move above the pivot
   during the day that closes back inside the base.
3. **Tightness just before.** The best breakouts come after the quietest
   final stretch — inside bars, NR7s (the narrowest bar of the last seven) at
   the pivot. Wide, choppy trading at the pivot means big holders are
   selling into the base (distribution), not buying (accumulation).
4. **Follow-through.** Real breakouts usually keep going without falling back
   much. A close back below the pivot within days is the single most useful
   sign that a breakout has failed. (The `minervini` strategy exits on
   exactly that.) A *shallow, quiet* first pullback to the pivot that holds
   is normal. It is often a second chance to buy — the "retest".
5. **Market and group.** In weak markets and weak industry groups, breakouts
   fail in large numbers. That is why the strategies downgrade setups when
   the app's market-regime check is negative, and why the app tracks group
   relative strength at all.

---

## 5. What the evidence says

Be honest about this, because the pictures are convincing:

- **Bulkowski's statistics** come from the largest public catalog of
  patterns. They show that most patterns' "success rates" fall apart once you
  look closely at how success was measured. His best performers are the
  rarer, stricter shapes (high tight flag), not the common loose ones.
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
- Practitioners (O'Neil, Minervini) claim that patterns work only as the
  *last step for timing the entry*, on top of everything else: a leading
  stock, a leading group, a supportive market, strong fundamentals. The
  backtests here test the shapes alone, which is the weaker claim. The
  combined claim is harder to test and is still open (see
  [momentum-trend-research.md](momentum-trend-research.md) for the record of
  what has been tested).

The working conclusion for this project: **patterns are a way to read
structure, stops and triggers — not an edge on their own.** Use them to know
where a trade is proven wrong (invalidation), where it triggers (the pivot),
and what would be abnormal (volume, failure signals). Do not expect the shape
itself to make money.

## 6. Practicing in the app

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

## Further reading

- William O'Neil, *How to Make Money in Stocks* — cup-with-handle, flat
  base, double bottom, and CAN SLIM, his checklist of conditions to have in
  place before buying.
- Mark Minervini, *Trade Like a Stock Market Wizard* — VCP, pivots, and the
  logic of tightness and volume behind every pattern above.
- Thomas Bulkowski, *Encyclopedia of Chart Patterns* — the statistics, and a
  cure for believing too much in patterns.
- Nicolas Darvas, *How I Made $2,000,000 in the Stock Market* — the box
  theory that became the flat base.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — stage
  analysis: when in a stock's life cycle patterns are worth trading at all.
