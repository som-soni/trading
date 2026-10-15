# Candlestick patterns — a field guide

Learning material: how to read daily and weekly candles, which patterns are
worth knowing, and how this project uses them. It is a companion to
[learn-chart-patterns.md](learn-chart-patterns.md). A candle describes a
single bar (one day or one week). A chart pattern describes the shape of
several weeks of bars.

**Where this shows up in the app.** The screener writes a one-line summary of
the recent candles for every candidate. It goes in the `candles` column and is
built by `scripts/swing_screener/core/patterns.py`. The command
`python3 -m swing_screener.screening.inspect --symbol XYZ` prints the stats of
the last five bars, with the patterns it detected. The chart page draws plain
candles. No strategy buys or sells because of a candlestick pattern — see
"How candles are used here" at the end for why.

---

## 1. Anatomy of a candle

A candle sums up one trading session in four prices: the open, the high, the
low and the close. The **body** spans the open and the close. The **wicks**
(thin lines above and below the body) reach the high and the low. The
**range** is the distance from the low to the high.

```pattern
anatomy
```

Three questions tell you most of what one candle can say:

1. **How big is the body compared with the range?** A large body means one
   side controlled the session. A tiny body means neither side won.
2. **Where in the range did it close?** A close in the top third means buyers
   were in control at the end of the day. A close in the bottom third means
   sellers were.
3. **Which wick is long?** A long wick marks prices the stock traded at during
   the session but could not hold. A long lower wick means buyers stepped in
   on the dip and bought up the selling.

The app's candle commentary measures these with numbers. The rules live in
`core/patterns.py`:

| Measure | Definition | Thresholds used |
|---|---|---|
| Body % | \|close − open\| / (high − low) | doji when ≤ 10% |
| Close location | (close − low) / (high − low) | top ≥ 0.66, bottom ≤ 0.34 |
| Wick ratio | wick length / body length | "long" when ≥ 2× the body |
| Gap % | open vs the prior close | a gap when beyond ±0.3% |
| Volume ratio | volume / 50-day average volume | notable above 1.2 or below 0.8 |

**Volume matters as much as the shape.** A reversal candle on 2× average
volume shows many traders acting. The same shape on 0.6× volume is noise.
Read every pattern below together with its volume ratio.

---

## 2. Context first, pattern second

A candlestick pattern is not a signal by itself. The same hammer means:

- at the 50-day average after a 3-week pullback in an uptrend → the uptrend
  *may be resuming*, so it is worth attention;
- in the middle of a range, away from any level → nothing;
- after a 40% collapse in a downtrend → usually just the first bounce, and
  sellers push the price down again.

Rules of thumb that hold up on real charts:

1. **Only read reversal candles at a level** — a prior low, a moving average
   the stock has bounced from before, a pattern pivot, the edge of a gap. At a
   level, buyers and sellers are both active, and the candle shows which side
   won there. Away from a level, there is no contest to read.
2. **The trend matters more than the candle.** A bearish candle in a strong
   uptrend is usually just a pause. Do not bet against an uptrend because of
   one shooting star. At most, tighten your stop.
3. **A longer timeframe carries more meaning.** A weekly hammer at support
   counts for more than five daily candles. That is why the screener also
   prints a note on the weekly candle (`weekly_candle_note`).
4. **Wait for the confirming close** when the candle is your only reason to
   act. A hammer is only "confirmed" when the next bar closes above its body.

---

## 3. Single-candle patterns

### Doji — neither side wins

The body is ≤ ~10% of the range: the open and the close are nearly equal.

```pattern
doji
```

After a long advance, a doji on high volume is a warning. The buyers who
drove the move met as much selling as buying for the first time. In a quiet
range, a doji says nothing at all.

Variants:

- **Gravestone**: a long upper wick and a close near the low. A rally during
  the day failed. It is bearish at highs.
- **Dragonfly**: a long lower wick and a close near the high. A sell-off
  during the day was bought back. It is bullish at support.
- **Spinning top**: a small body with wicks on both sides. It shows
  indecision, a slightly weaker message than a doji.

### Hammer — a sell-off that was bought back

A long lower wick (≥ 2× the body) and a close in the top third, appearing
**after a decline or pullback**. Sellers pushed the price down during the
session. Buyers then bought it all the way back up.

```pattern
hammer
```

It is bullish at support. The low of the hammer is the natural place for a
stop. If the price trades back below that low, the buying that made the
hammer has failed.

The same shape after an *advance* is called a **hanging man**. It is a
warning, not a sell signal, and much weaker evidence than a hammer.

### Shooting star — a rally that failed

This is the mirror image of the hammer: a long upper wick (≥ 2× the body) and
a close in the bottom third, after an advance. Buyers pushed the price to new
highs during the day, then sellers took over and drove it back down. It means
something at resistance or after a fast, steep run-up. Inside a base it is an
ordinary candle. The **inverted hammer** is the same shape after a decline.
It is mildly bullish and needs the next bar to confirm it.

### Marubozu — one side in full control

The body is (nearly) the whole range, with no wicks. A green marubozu through
a pivot on heavy volume is exactly the breakout bar you want. A red one
through support is a sign of distribution — large holders selling. The
commentary calls these "plain top-range close" / "plain bottom-range close"
when no other pattern applies.

### NR7 — a quiet bar before a move

It is not a classical candlestick, but the commentary reports it: the bar
with the narrowest range of the last 7 bars. Volatility tends to shrink
before it expands. A cluster of NR7 or inside bars near a pivot is the
daily-chart version of what the VCP strategies look for (VCP: volatility
contraction pattern, where each pullback in a base is smaller than the last).
The direction of the next move comes from which way the price breaks, not
from the NR7 itself.

---

## 4. Two-candle patterns

### Bullish engulfing

A down candle, then an up candle. The up candle's body opens at or below the
prior close and closes at or above the prior open. The second session wipes
out the whole first session and then reverses it.

```pattern
bullish-engulfing
```

It is strong at support after a pullback, on rising volume. Put the stop
below the engulfing bar's low.

**Bearish engulfing** is the mirror image, at highs. Both are among the few
candle patterns with some modest statistical support. Both still fail often
when they go against the main trend.

### Harami / inside bar

The second bar's range sits entirely inside the first bar's range. The
commentary flags this as an **inside bar**. The range is shrinking: the
market is pausing. Like the NR7, it does not point up or down. Trade the
break of the inside bar's range, in the direction of the trend, rather than
the bar itself. The **outside bar** is the opposite: its range covers the
prior bar's range on both sides. The range is expanding, and where it closes
in its range shows which side won.

### Piercing line / dark cloud cover

These are weaker versions of the engulfing pair. The second body takes back
more than half of the first body but does not engulf it.

- Piercing line (bullish, at lows): a gap down, then a close above the
  midpoint of the prior red body.
- Dark cloud cover (bearish, at highs): a gap up, then a close below the
  midpoint of the prior green body.

Read them the same way as an engulfing pattern, with less confidence.

### Tweezers

Two bars in a row with (nearly) equal lows (tweezer bottom) or equal highs
(tweezer top). The same price level held twice in a row. They are mostly
useful as evidence *that the level matters*, not as a pattern on their own.

---

## 5. Three-candle patterns

### Morning star / evening star

The classic reversal in three steps. A morning star forms at a low:

- first, a strong red bar (sellers in control);
- then a small-bodied bar, the "star", that gaps or drifts lower (the selling
  is running out);
- last, a strong green bar that closes well into the first bar's body (buyers
  take over).

```pattern
morning-star
```

The evening star is the mirror image, at highs. The project's **3-bar
reversal** flag is a loose version of this. The bullish version is a close
down, then a close back up through the first bar's open. The bearish version
is the mirror.

### Three white soldiers / three black crows

Three full-bodied candles in a row in the same direction, each closing near
its high (or, for crows, its low). After a long decline, three white soldiers
mark a real change in how the stock trades. *Late* in an advance, three
ever-larger white soldiers on rising volume start to look like a climax — a
final burst of buying before a top. See the climax-top discussion in
[learn-chart-patterns.md](learn-chart-patterns.md).

---

## 6. Quick reference

| Pattern | Bars | Bias | Where it means something | Invalidation |
|---|---|---|---|---|
| Doji | 1 | neutral | after a one-way move | — (a warning, not a trade) |
| Hammer | 1 | bullish | at support after a decline | close below its low |
| Hanging man | 1 | mildly bearish | after an advance | close above its high |
| Shooting star | 1 | bearish | at resistance after an advance | close above its high |
| Inverted hammer | 1 | mildly bullish | after a decline, needs confirmation | close below its low |
| Marubozu | 1 | with its color | through a level, on volume | retrace through the level |
| NR7 / inside bar | 1–2 | neutral (contraction) | near a pivot | — (trade the break) |
| Bullish engulfing | 2 | bullish | at support, rising volume | close below pattern low |
| Bearish engulfing | 2 | bearish | at highs/resistance | close above pattern high |
| Piercing line | 2 | bullish | at lows | close below pattern low |
| Dark cloud cover | 2 | bearish | at highs | close above pattern high |
| Morning star | 3 | bullish | at lows, volume on bar 3 | close below star's low |
| Evening star | 3 | bearish | at highs | close above star's high |
| Three white soldiers | 3 | bullish | after a decline/base | — context-dependent |
| Three black crows | 3 | bearish | after an advance | — context-dependent |

---

## 7. How candles are used here — and the evidence

**In this project candles are commentary, not signals.** The screener and
`inspect` print them so that, when you review a candidate, you can see at a
glance how the last bars behaved at the levels that matter. The summary names
the nearby level explicitly: the 20-day average (SMA20), the 50-day average
(SMA50) or the pivot. The strategies enter on price levels and chart
structure — the price resuming its move through resistance, or breaking out
through a pivot. They never "buy because yesterday was a hammer".

That is deliberate, and it is the honest reading of the evidence:

- Academic tests of candlestick rules on daily stock data (e.g. Marshall,
  Young & Rose 2006 on the Dow; Horton 2009; Fock et al. on intraday data)
  find **no reliable predictive value on their own** after costs.
- Bulkowski's large pattern catalogs find that single candle patterns, on
  their own, are barely better than a coin flip. They improve only when
  filtered by trend and by confirmation — that is, by exactly the context
  rules in §2.
- Candle shapes depend on how the trading session works. A stock that gaps
  every day (around earnings, ADRs — foreign shares listed in the US, thinly
  traded names) produces "patterns" all the time. A market that trades 24
  hours a day produces different candles from one with an exchange session.
  The same price path, cut into bars differently, gives different candles.
  That is a reason to treat candles as a *description* of what happened, not
  a *prediction*.

Where they are useful in a swing-trading workflow like this one:

1. **How good the entry day looks.** On the day the price moves through your
   entry trigger, a full-bodied close near the top of the range on
   above-average volume is what a healthy breakout looks like. A
   shooting-star close back under the pivot on the same volume is the first
   sign of a failed breakout. (The `minervini` strategy's exit rules treat a
   close back below the pivot as exactly that.)
2. **Stop placement.** Reversal candles give natural points where the idea is
   proven wrong — the hammer's low, the engulfing bar's low. These are
   usually tighter, and more tied to what the price actually did, than a
   fixed percentage.
3. **Reading a pullback.** In a setup like the `trend_pullback` strategy's
   (buying a dip in an uptrend), an orderly pullback looks like small-range
   candles (inside bars, NR7, dojis) with lower wicks near the rising 50-day
   average. Distribution looks like wide red marubozus on rising volume. The
   pullback can be the same depth, and the conclusion opposite.

## Further reading

- Steve Nison, *Japanese Candlestick Charting Techniques* — the book that
  introduced candles to Western traders. Read it for the vocabulary, not for
  win rates.
- Thomas Bulkowski, *Encyclopedia of Candlestick Charts* — statistics for
  each pattern. It is the most honest source on how weak single patterns are.
- The pattern thresholds actually used here:
  `scripts/swing_screener/core/patterns.py`.
