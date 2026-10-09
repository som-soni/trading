# Chart patterns — a field guide

Learning material: what chart patterns are, how to read the ones that matter
for swing trading, and what the evidence — including this project's own
backtests — says about them. Companion to
[learn-candlestick-patterns.md](learn-candlestick-patterns.md) (the
single-bar vocabulary) and to
[chart-pattern-spec.md](chart-pattern-spec.md), which pins every pattern
below to computer-checkable rules.

**Where this shows up in the app.** The `chart_pattern` strategy detects
seven bullish bases on daily data (`scripts/swing_screener/core/chart_patterns.py`)
and reports the best-scoring one per stock; its rules, pivots and stops are
on the Strategies page. The VCP is also the entry pattern of both Minervini
strategies. Topping structures (double top, head-and-shoulders) are detected
as warnings. The chart page is where you practice seeing them yourself.

---

## 1. What a pattern is — and is not

A chart pattern is a **consolidation with a story about supply and demand**.
After an advance, some holders take profits; price pulls back until buyers
who missed the move absorb the selling. If the stock is under accumulation,
each wave of selling is shallower — the pattern "tightens" — until sellers
are exhausted and a small amount of demand pushes price through the old high.
That is the whole theory, and every bullish continuation pattern below is a
variation of it.

Three consequences follow:

1. **Context decides meaning.** The same shape is a *continuation* pattern
   after an advance and a *bear rally* after a decline. This is why the
   `chart_pattern` strategy only looks at stocks from the
   "Near highs, rising 200-day" screen, and why its FLAT and FLAG detectors
   demand a prior advance (≥ 20%) before the base.
2. **A pattern is only complete at its trigger.** Until price breaks the
   pivot, a cup-with-handle is just a stock that went down and came back up.
   Most of the information is in *how* the breakout happens (volume, close
   location, follow-through), not in the shape alone.
3. **Every pattern needs an invalidation level.** The structural low that,
   if broken, proves the story wrong — the handle low, the second bottom,
   the flag low. That level is where the stop belongs, and a pattern whose
   stop is too far away to size is not a trade (the strategy downgrades
   exactly these).

### The shared anatomy

Every pattern entry here answers the same five questions, in the same order
as the spec: key points → context → geometry → volume → trigger /
invalidation / target. For targets, the classical convention is the
**measured move**: project the pattern's height (or prior pole) above the
pivot. Treat it as a first estimate, not a promise — the strategy caps it at
real overhead resistance.

---

## 2. Bullish continuation patterns (the ones detected here)

### Cup with handle — `CUP`

The classic O'Neil base. An advance, a rounded correction (not a V), a
recovery to the old high, then a small, quiet pullback — the handle — as the
last sellers near the rim are absorbed.

```pattern
cup-with-handle
```

What makes a *good* cup: a rounded bottom (time spent down there — the weak
holders need time to leave), a handle in the **upper half** of the cup that
drifts down on **below-average volume**, and a rim at or near the 52-week
high. Red flags: V-shaped cups, handles that form in the lower half or slice
down fast, wide-and-loose structure throughout.

Trigger: close above the right rim on expanding volume. Invalidation: the
handle low. Measured move: the cup's depth. The app also detects the
**cup without a handle** (`CUPNH`) — same body, but price is still pinned to
the rim; the pivot is the rim itself.

### Double bottom — `DBOT`

A "W". Two sell-offs to the same area; the second finds no new sellers
(ideally it *undercuts* the first low slightly — the shakeout that clears
the last stops — and recovers immediately).

```pattern
double-bottom
```

Trigger: the middle peak between the lows. Invalidation: the second low.
Measured move: middle peak minus the low. The mirror image at highs — the
**double top** — is detected here as a topping warning, not a setup.

### Flat base / Darvas box — `FLAT`

The strongest stocks barely pull back at all: after an advance, price moves
sideways in a tight box (≤ 15% deep here) while time, not price, does the
correcting. Boxes stack — a breakout from one box becomes the floor of the
next (Darvas's original observation).

```pattern
flat-base
```

Trigger: box high. Invalidation: box low. Measured move: note that here the
projection is the **prior advance**, not the box height — a tight box's own
height is too small to be a meaningful target.

### Bull flag — `FLAG`

A near-vertical advance (the pole), then a short, shallow drift against it
(the flag). The textbook case retraces less than half the pole in a few
weeks. The rare, famous variant is the **high tight flag**: a gain of 80%+
retraced 25% or less — scored higher by the detector because almost nothing
but a leader under heavy accumulation can produce it.

```pattern
bull-flag
```

Trigger: pole high. Invalidation: flag low. Measured move: the pole height
("flags fly at half mast" — the pole repeats).

### Ascending triangle — `ATRI`

Flat resistance tested repeatedly from below, with **rising lows** squeezing
price into the corner: sellers sit at one price, buyers get more impatient
on every dip.

```pattern
ascending-triangle
```

Trigger: the resistance line. Invalidation: the last rising low. Measured
move: the triangle's height at its left edge. Descending and symmetrical
triangles exist in the classical catalog (see the spec) but are not setups
in this app — the ascending form is the one with the cleanest bullish logic.

### Volatility contraction pattern — `VCP`

Minervini's generalization of all of the above: what matters is not the
shape's name but that **each successive pullback is shallower than the
last** (each ≤ 0.8× the prior one here, the final one ≤ 12%), on drying-up
volume, ending in a tight shelf near the highs. A cup-with-handle *is* a
two-contraction VCP; a high tight flag is a one-contraction VCP.

```pattern
vcp
```

Trigger: the final contraction's high. Invalidation: the final contraction's
low — which is what makes VCPs attractive: the stop is *close*, so the
reward:risk on even a modest move is high. This is the entry pattern of the
`minervini` and `minervini_spec` strategies;
[minervini-backtest-spec.md](minervini-backtest-spec.md) pins it down
formally.

---

## 3. Topping structures — patterns that say get out

Detected here as warnings (`core/chart_patterns.py: detect_topping`), because
a bullish base should never be bought while a topping structure is active
above it.

- **Double top.** Two rallies to the same area, the second on weaker volume;
  confirmed when the valley between them breaks. Mirror logic of the double
  bottom.
- **Head and shoulders top.** Three rallies — the middle one highest — with
  the third failing below the second: the first *lower high* after an
  advance, i.e. the definition of a trend losing its structure. Confirmed on
  the neckline break; the measured move projects downward.
- **Climax run.** Not a geometric pattern: after a long advance, the steepest
  rally of the whole move — biggest weekly gains, widest bars, exhaustion
  gaps, often on record volume. It marks the moment the last buyers arrive.
  Minervini and O'Neil both sell *into* strength here; the `minervini_spec`
  exit rules include a climax exit for exactly this.

---

## 4. Reading a breakout

The pattern qualifies the stock; the breakout is the trade. What separates a
real breakout from a head-fake, in rough order of importance:

1. **Volume.** The breakout day should trade meaningfully above average
   volume — the `chart_pattern` strategy demands a close above the pivot on
   at least 1.4× the 50-day average (`VOL_CONFIRM`; the Strategies page
   always shows the live value). A pivot cleared on quiet volume invites
   the failure.
2. **Close location.** A full-bodied close near the day's high above the
   pivot (see the candlestick guide) — not an intraday poke that closes back
   inside the base.
3. **Tightness just before.** The best breakouts come from the quietest
   final shelves (inside bars, NR7s at the pivot). Wide, loose churn at the
   pivot means the base is being distributed, not accumulated.
4. **Follow-through.** Real breakouts tend not to look back much: a close
   back below the pivot within days is the single most useful failure signal
   (the `minervini_spec` strategy exits on exactly that). A *shallow, quiet*
   first pullback to the pivot that holds is normal and is often the second
   chance — the "retest".
5. **Market and group.** Breakouts fail in bulk in weak markets and weak
   groups — the reason the strategies apply the market-regime downgrade and
   why group relative strength is tracked at all.

---

## 5. What the evidence says

Be honest about this, because the pictures are seductive:

- **Bulkowski's statistics** (the largest public pattern catalog) show most
  patterns' "success rates" collapse once you account for how they are
  measured — and his best performers are exactly the rarer, stricter shapes
  (high tight flag) rather than the common loose ones.
- **This project's own backtest** of all seven detectors together
  (`chart_pattern`, US 2020–2026, 300-symbol sample, bracket exits) **lost
  money**: −4.08% CAGR against the benchmark's +13.63%, −0.213R per trade
  over 146 trades. Detecting textbook shapes and buying their pivots, as
  literally specified, had no edge in that sample.
- A **random-data check** found that most of the detectors fire regularly on
  random walks — shapes alone carry little information. The two that are
  rare in random data (CUP and CUPNH) were split into their own strategy
  (`chart_pattern_cup`); its backtest came out **indecisive** (−0.019R over
  32 trades, t ≈ 0), better than the full set but not demonstrably positive.
- The practitioner claim (O'Neil, Minervini) is that patterns work only as
  the *final timing element* stacked on top of everything else — a leading
  stock, a leading group, a supportive market, strong fundamentals. The
  backtests here test the geometry alone, which is the weaker claim; the
  stacked claim is harder to test and remains open (see
  [momentum-trend-research.md](momentum-trend-research.md) for the ledger).

The working conclusion for this project: **patterns are a language for
reading structure, stops and triggers — not a stand-alone edge.** Use them
to know where a trade is wrong (invalidation), where it triggers (pivot) and
what would be abnormal (volume, failure signals); do not expect the shape
itself to pay.

## 6. Practicing in the app

1. Open a leader's chart and find last year's bases *before* checking what
   the detector says: `python3 -m swing_screener.screening.inspect --market
   us --symbol NVDA --strategy chart_pattern` prints the detected pattern,
   its pivot, stop and score for any symbol.
2. On the Strategies page, open *Classical chart-pattern breakout* → Rules:
   every detector's exact geometry, with live thresholds substituted.
3. Draw the patterns yourself: trend lines, horizontal pivots and measured
   moves on the chart page (Alt+T / Alt+H; Shift+drag measures).
4. Read [chart-pattern-spec.md](chart-pattern-spec.md) when prose feels
   ambiguous — every rule above has a computer-checkable version there.

## Further reading

- William O'Neil, *How to Make Money in Stocks* — cup-with-handle, flat
  base, double bottom, and the CAN SLIM context stack.
- Mark Minervini, *Trade Like a Stock Market Wizard* — VCP, pivots, and the
  tightness/volume logic behind every pattern above.
- Thomas Bulkowski, *Encyclopedia of Chart Patterns* — the statistics, and a
  cure for pattern romanticism.
- Nicolas Darvas, *How I Made $2,000,000 in the Stock Market* — the box
  theory that became the flat base.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — stage
  analysis: when in a stock's life cycle patterns are worth trading at all.
